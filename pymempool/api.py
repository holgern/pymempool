import json
import logging
import warnings
from typing import Any, Callable, Optional, Union
from urllib.parse import urlparse

import requests
import urllib3
from requests.adapters import HTTPAdapter  # type: ignore[import-untyped]

from pymempool.rate_limiter import RateLimiter
from pymempool.response_cache import _MISSING, ResponseCache

logger = logging.getLogger(__name__)


class MempoolAPIError(Exception):
    """Base exception for Mempool API errors."""

    pass


class MempoolNetworkError(MempoolAPIError):
    """Exception raised for network connectivity issues."""

    pass


class MempoolResponseError(MempoolAPIError):
    """Exception raised for API response errors."""

    pass


class MempoolRateLimitError(MempoolResponseError):
    """Exception raised when the upstream API asks the client to slow down."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 429,
        host: Optional[str] = None,
        retry_after_seconds: Optional[float] = None,
        cooldown_seconds: Optional[float] = None,
        next_allowed_at: Optional[float] = None,
        response_payload: Any = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.host = host
        self.retry_after_seconds = retry_after_seconds
        self.cooldown_seconds = cooldown_seconds
        self.next_allowed_at = next_allowed_at
        self.response_payload = response_payload


class MempoolAPI:
    __API_URL_BASE: list = [
        "https://mempool.space/api/",
        "https://mempool.emzy.de/api/",
        "https://mempool.bitcoin-21.org/api/",
    ]
    _CACHEABLE_GET_ENDPOINTS = {
        "mempool",
        "v1/fees/mempool-blocks",
        "v1/fees/recommended",
        "v1/fees/precise",
    }

    def __init__(
        self,
        api_base_url: Union[list, str] = __API_URL_BASE,
        retries: int = 3,
        request_verify: bool = True,
        proxies: Optional[dict] = None,
        rate_limit_per_sec: float = 1.0,
        rate_limit_burst: int = 5,
        respect_retry_after: bool = True,
        enable_response_cache: bool = True,
        cache_ttl_seconds: float = 3.0,
        rate_limit_notifier: Optional[Callable[[str], None]] = None,
    ):
        """Create a mempool.space API client with conservative rate-limit handling.

        Transport retries handle transient upstream failures such as ``502``, ``503``,
        and ``504``. HTTP ``429`` is handled explicitly in application logic so the
        client can slow down, honor ``Retry-After``, reuse cached snapshots for hot
        endpoints, and avoid amplifying pressure across public mirrors.
        """

        self.set_api_base_url(api_base_url)
        self.proxies = proxies
        self.connect_timeout = 1
        self.reading_timeout = 120
        self.sending_timeout = 120
        self.request_verify = request_verify
        self.respect_retry_after = respect_retry_after
        self.enable_response_cache = enable_response_cache
        self._rate_limit_notifier = rate_limit_notifier
        self._last_notice: Optional[str] = None
        if not request_verify:
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")
        self.session = requests.Session()
        # 429 used to live inside urllib3's generic retry path and then bubble into
        # host failover, which could amplify pressure across mirrors. Keep transport
        # retries for transient 5xx failures and handle 429 explicitly below.
        max_retries = urllib3.Retry(
            total=retries,
            backoff_factor=0.1,
            status_forcelist=[502, 503, 504],
            allowed_methods=frozenset({"GET", "POST"}),
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=max_retries))
        self.rate_limiter = RateLimiter(
            rate_limit_per_sec=rate_limit_per_sec,
            rate_limit_burst=rate_limit_burst,
            notifier=self._emit_notice,
        )
        self.response_cache = ResponseCache(
            ttl_seconds=cache_ttl_seconds,
            notifier=self._emit_notice,
        )

    def set_api_base_url(self, api_base_url: Union[list, str]) -> None:
        if isinstance(api_base_url, list):
            self.api_base_url = api_base_url
        else:
            self.api_base_url = api_base_url.split(",")

    def _emit_notice(self, message: str) -> None:
        if not message:
            return
        if message == self._last_notice:
            return
        self._last_notice = message
        logger.debug(message)
        if self._rate_limit_notifier is not None:
            self._rate_limit_notifier(message)

    def _reset_notice(self) -> None:
        self._last_notice = None

    def _build_url_with_params(
        self, base_url: str, params: Optional[dict] = None
    ) -> str:
        """Helper method to build URL with query parameters.

        Args:
            base_url: Base API URL
            params: Dictionary of query parameters

        Returns:
            URL string with parameters
        """
        if not params:
            return base_url

        url = base_url
        connector = "?"

        for key, value in params.items():
            if value is not None:
                if isinstance(value, bool):
                    value = str(value).lower()
                elif isinstance(value, int):
                    value = str(value)

                url += f"{connector}{key}={value}"
                connector = "&"

        return url

    def get_api_base_url(self, index: int = 0) -> str:
        if len(self.api_base_url) > index:
            return self.api_base_url[index]
        else:
            return self.api_base_url[0]

    def _request(self, url: str) -> Any:
        """Make a GET request with cooldown-aware failover and caching.

        Args:
            url: The API endpoint to request

        Returns:
            The parsed API response

        Raises:
            MempoolNetworkError: If all API endpoints fail with network errors
            MempoolResponseError: If all API endpoints fail with response errors
        """
        self._reset_notice()
        if self.enable_response_cache and self._should_cache_endpoint(url):
            cache_key = self._build_cache_key("GET", url)
            cached = self.response_cache.get(cache_key)
            if cached is not _MISSING:
                return cached

            try:
                return self.response_cache.get_or_load(
                    cache_key, lambda: self._request_uncached(url)
                )
            except MempoolRateLimitError:
                stale = self.response_cache.get_stale(cache_key)
                if stale is not _MISSING:
                    self.response_cache.notify_cached_snapshot()
                    return stale
                raise

        return self._request_uncached(url)

    def _request_uncached(self, url: str) -> Any:
        last_exception: Optional[Union[MempoolResponseError, Exception]] = None
        response_errors: list[MempoolResponseError] = []
        rate_limit_errors: list[MempoolRateLimitError] = []
        attempted_hosts: list[str] = []
        rate_limit_failovers = 0
        total_hosts = len(self._available_hosts())

        while len(attempted_hosts) < total_hosts:
            base_url, host = self._pick_api_base_url(excluded_hosts=attempted_hosts)
            attempted_hosts.append(host)
            complete_url = f"{base_url}{url}"
            try:
                return self.__request(complete_url)
            except MempoolRateLimitError as e:
                rate_limit_errors.append(e)
                last_exception = e
                if len(self.api_base_url) > 1 and rate_limit_failovers < 1:
                    remaining_hosts = [
                        self._extract_host(candidate)
                        for candidate in self.api_base_url
                        if self._extract_host(candidate) not in attempted_hosts
                    ]
                    if remaining_hosts:
                        rate_limit_failovers += 1
                        continue
                break
            except MempoolResponseError as e:
                response_errors.append(e)
                last_exception = e
            except Exception as e:
                logger.info("Timeout on %s - %s", complete_url, e)
                last_exception = e

        if response_errors:
            raise response_errors[0]
        if rate_limit_errors:
            raise rate_limit_errors[0]
        raise MempoolNetworkError(f"All API endpoints failed: {last_exception}")

    def __request(self, url: str) -> Any:
        """Execute HTTP GET request and process response.

        Args:
            url: The full URL to request

        Returns:
            Parsed response content

        Raises:
            MempoolNetworkError: For network connectivity issues
            MempoolResponseError: For API response errors
        """
        logger.info(url)
        host = self._extract_host(url)
        self.rate_limiter.wait_until_allowed(host)
        try:
            response = self.session.get(
                url,
                timeout=(self.connect_timeout, self.reading_timeout),
                verify=self.request_verify,
                proxies=self.proxies,
            )
        except requests.exceptions.RequestException as e:
            raise MempoolNetworkError(f"Network error: {str(e)}") from e

        if response.status_code == 429:
            raise self._build_rate_limit_error(response, host)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise self._build_response_error(response, e) from e

        # Process successful response
        self.rate_limiter.record_success(host)
        try:
            decoded_content = response.content.decode("utf-8")
            content = json.loads(decoded_content)
            return content
        except UnicodeDecodeError:
            # Return raw binary content if not UTF-8
            return response.content
        except json.decoder.JSONDecodeError:
            # Return string content if not JSON
            return response.content.decode("utf-8")

    def _send(self, url: str, data: Any) -> Any:
        """Make POST request to the API with cooldown-aware failover.

        Args:
            url: The API endpoint to request
            data: The data to send

        Returns:
            The parsed API response

        Raises:
            MempoolNetworkError: If all API endpoints fail with network errors
            MempoolResponseError: If all API endpoints fail with response errors
        """
        self._reset_notice()
        last_exception: Optional[Union[MempoolResponseError, Exception]] = None
        response_errors: list[MempoolResponseError] = []
        rate_limit_errors: list[MempoolRateLimitError] = []
        attempted_hosts: list[str] = []
        rate_limit_failovers = 0
        total_hosts = len(self._available_hosts())

        while len(attempted_hosts) < total_hosts:
            base_url, host = self._pick_api_base_url(excluded_hosts=attempted_hosts)
            attempted_hosts.append(host)
            complete_url = f"{base_url}{url}"
            try:
                return self.__send(complete_url, data)
            except MempoolRateLimitError as e:
                rate_limit_errors.append(e)
                last_exception = e
                if len(self.api_base_url) > 1 and rate_limit_failovers < 1:
                    remaining_hosts = [
                        self._extract_host(candidate)
                        for candidate in self.api_base_url
                        if self._extract_host(candidate) not in attempted_hosts
                    ]
                    if remaining_hosts:
                        rate_limit_failovers += 1
                        continue
                break
            except MempoolResponseError as e:
                response_errors.append(e)
                last_exception = e
            except Exception as e:
                logger.info("Timeout on %s - %s", complete_url, e)
                last_exception = e

        if response_errors:
            raise response_errors[0]
        if rate_limit_errors:
            raise rate_limit_errors[0]
        raise MempoolNetworkError(f"All API endpoints failed: {last_exception}")

    def __send(self, url: str, data: Any) -> Any:
        """Execute HTTP POST request and process response.

        Args:
            url: The full URL to request
            data: The data to send

        Returns:
            Parsed response content

        Raises:
            MempoolNetworkError: For network connectivity issues
            MempoolResponseError: For API response errors
        """
        logger.info(url)
        host = self._extract_host(url)
        self.rate_limiter.wait_until_allowed(host)
        try:
            req = requests.Request("POST", url, data=data)
            prepped = req.prepare()
            response = self.session.send(
                prepped,
                timeout=(self.connect_timeout, self.sending_timeout),
                verify=self.request_verify,
                proxies=self.proxies,
            )
        except requests.exceptions.RequestException as e:
            raise MempoolNetworkError(f"Network error: {str(e)}") from e

        if response.status_code == 429:
            raise self._build_rate_limit_error(response, host)

        try:
            response.raise_for_status()
            self.rate_limiter.record_success(host)
            content = response.content.decode("utf-8")
            return content
        except requests.exceptions.HTTPError as e:
            raise self._build_response_error(response, e) from e

    def _build_cache_key(self, method: str, url: str) -> str:
        return f"{method}:{url}"

    def _should_cache_endpoint(self, url: str) -> bool:
        return url in self._CACHEABLE_GET_ENDPOINTS

    def _extract_host(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc or url

    def _pick_api_base_url(
        self, excluded_hosts: Optional[list[str]] = None
    ) -> tuple[str, str]:
        host_lookup: dict[str, str] = {}
        for base_url in self.api_base_url:
            host = self._extract_host(base_url)
            if excluded_hosts and host in excluded_hosts:
                continue
            host_lookup.setdefault(host, base_url)

        host = self.rate_limiter.pick_host(
            list(host_lookup.keys()), excluded_hosts=excluded_hosts
        )
        return host_lookup[host], host

    def _available_hosts(self) -> list[str]:
        return list({self._extract_host(base_url) for base_url in self.api_base_url})

    def _parse_retry_after(self, response: requests.Response) -> Optional[float]:
        retry_after = response.headers.get("Retry-After")
        if not retry_after or not self.respect_retry_after:
            return None

        try:
            parsed = max(float(int(retry_after.strip())), 0.0)
            logger.debug("Parsed Retry-After=%s for %s", parsed, response.url)
            return parsed
        except (TypeError, ValueError):
            logger.debug("Could not parse Retry-After header %r", retry_after)
            return None

    def _decode_error_payload(self, response: requests.Response) -> Any:
        try:
            return json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.decoder.JSONDecodeError):
            try:
                return response.content.decode("utf-8")
            except UnicodeDecodeError:
                return response.content

    def _build_rate_limit_error(
        self, response: requests.Response, host: str
    ) -> MempoolRateLimitError:
        retry_after_seconds = self._parse_retry_after(response)
        cooldown_seconds = self.rate_limiter.punish_429(
            host,
            retry_after=retry_after_seconds,
            attempt=self._current_rate_limit_attempt(host),
        )
        next_allowed_at = self.rate_limiter.get_next_allowed_at(host)
        payload = self._decode_error_payload(response)
        message = (
            f"HTTP 429 from {host}; retry_after={retry_after_seconds}; "
            f"cooldown={cooldown_seconds:.2f}s"
        )
        return MempoolRateLimitError(
            message,
            host=host,
            retry_after_seconds=retry_after_seconds,
            cooldown_seconds=cooldown_seconds,
            next_allowed_at=next_allowed_at,
            response_payload=payload,
        )

    def _current_rate_limit_attempt(self, host: str) -> int:
        budget = self.rate_limiter.get_budget(host)
        return max(1, budget.recent_429s)

    def _build_response_error(
        self, response: requests.Response, error: requests.exceptions.HTTPError
    ) -> MempoolResponseError:
        content = self._decode_error_payload(response)
        if content:
            return MempoolResponseError(content)
        return MempoolResponseError(f"HTTP error: {response.status_code}")

    def get_price(self):
        """Returns bitcoin latest price denominated in main currencies."""
        api_url = "v1/prices"
        return self._request(api_url)

    def get_historical_price(self, currency=None, timestamp=None):
        """Returns bitcoin historical price denominated in main currencies.

        Available query parameters: currency, timestamp.
        If no parameter is provided, the full price history
        for all currencies is returned.
        """
        api_url = "v1/historical-price"

        params: dict[str, Union[str, int]] = {}
        if currency is not None:
            params["currency"] = str(currency).upper()
        if timestamp is not None:
            params["timestamp"] = int(timestamp)

        api_url = self._build_url_with_params(api_url, params)
        return self._request(api_url)

    def get_difficulty_adjustment(self):
        """Returns details about difficulty adjustment."""
        api_url = "v1/difficulty-adjustment"
        return self._request(api_url)

    def get_address(self, address):
        """Returns details about an address."""
        address = address.replace(" ", "")
        api_url = f"address/{address}"
        return self._request(api_url)

    def get_address_transactions(self, address):
        """Get transaction history for the specified address/scripthash, sorted with
        newest first."""
        address = address.replace(" ", "")
        api_url = f"address/{address}/txs"
        return self._request(api_url)

    def get_address_transactions_chain(self, address, last_seen_txid=None):
        """Get confirmed transaction history for the specified address/scripthash,
        sorted with newest first."""
        address = address.replace(" ", "")
        if last_seen_txid is None:
            api_url = f"address/{address}/txs/chain"
        else:
            api_url = f"address/{address}/txs/chain/{last_seen_txid}"
        return self._request(api_url)

    def get_address_transactions_mempool(self, address):
        """Get unconfirmed transaction history for the specified address/scripthash."""
        address = address.replace(" ", "")
        api_url = f"address/{address}/txs/mempool"
        return self._request(api_url)

    def get_address_utxo(self, address):
        """Get the list of unspent transaction outputs associated with the
        address/scripthash."""
        address = address.replace(" ", "")
        api_url = f"address/{address}/utxo"
        return self._request(api_url)

    def get_block(self, hash_value):
        """Returns details about a block."""
        hash_value = hash_value.replace(" ", "")
        api_url = f"block/{hash_value}"
        return self._request(api_url)

    def get_block_v1(self, hash_value):
        """Returns details about a block."""
        hash_value = hash_value.replace(" ", "")
        api_url = f"v1/block/{hash_value}"
        return self._request(api_url)

    def get_block_header(self, hash_value):
        """Returns the hex-encoded block header."""
        hash_value = hash_value.replace(" ", "")
        api_url = f"block/{hash_value}/header"
        return self._request(api_url)

    def get_block_height(self, height):
        """Returns the hash of the block currently at height."""
        height = int(height)
        api_url = f"block-height/{height}"
        return self._request(api_url)

    def get_block_raw(self, hash_value):
        """Returns the raw block representation in binary."""
        hash_value = hash_value.replace(" ", "")
        api_url = f"block/{hash_value}/raw"
        return self._request(api_url)

    def get_block_status(self, hash_value):
        """Returns the confirmation status of a block."""
        hash_value = hash_value.replace(" ", "")
        api_url = f"block/{hash_value}/status"
        return self._request(api_url)

    def get_block_tip_height(self):
        """Returns the height of the last block."""
        api_url = "blocks/tip/height"
        return self._request(api_url)

    def get_block_tip_hash(self):
        """Returns the hash of the last block."""
        api_url = "blocks/tip/hash"
        return self._request(api_url)

    def get_block_transaction_id(self, hash_value, index):
        """Returns the transaction at index index within the specified block."""
        hash_value = hash_value.replace(" ", "")
        index = int(index)
        api_url = f"block/{hash_value}/txid/{index}"
        return self._request(api_url)

    def get_block_transaction_ids(self, hash_value):
        """Returns a list of all txids in the block."""
        hash_value = hash_value.replace(" ", "")
        api_url = f"block/{hash_value}/txids"
        return self._request(api_url)

    def get_block_transactions(self, hash_value, start_index=None):
        """Returns a list of transactions in the block (up to 25 transactions beginning
        at start_index)."""
        hash_value = hash_value.replace(" ", "")
        if start_index is not None:
            start_index = int(start_index)
            api_url = f"block/{hash_value}/txs/{start_index}"
        else:
            api_url = f"block/{hash_value}/txs"
        return self._request(api_url)

    def get_blocks(self, start_height=None):
        """Returns the 10 newest blocks starting at the tip or at :start_height if
        specified."""
        if start_height is None:
            api_url = "blocks"
        else:
            start_height = int(start_height)
            api_url = f"blocks/{start_height}"
        return self._request(api_url)

    def get_blocks_v1(self, start_height=None):
        """Returns the 10 newest blocks starting at the tip or at :start_height if
        specified."""
        if start_height is None:
            api_url = "v1/blocks"
        else:
            start_height = int(start_height)
            api_url = f"v1/blocks/{start_height}"
        return self._request(api_url)

    def get_blocks_bulk(self, min_height, max_height=None):
        """Returns details on the range of blocks between :min_height and :max_height,
        inclusive, up to 10 blocks.

        If :max_height is not specified, it defaults to the current tip.
        """
        if max_height is None:
            min_height = int(min_height)
            api_url = f"v1/blocks-bulk/{min_height}"
        else:
            min_height = int(min_height)
            max_height = int(max_height)
            api_url = f"v1/blocks-bulk/{min_height}/{max_height}"
        return self._request(api_url)

    def get_mining_pools(self, time_period):
        """Returns a list of all known mining pools ordered by blocks found over the
        specified trailing time_period."""
        api_url = f"v1/mining/pools/{time_period}"
        return self._request(api_url)

    def get_mining_pool(self, slug):
        """Returns details about the mining pool specified by slug."""
        api_url = f"v1/mining/pool/{slug}"
        return self._request(api_url)

    def get_mining_pool_hashrates(self, time_period):
        """Returns average hashrates (and share of total hashrate) of mining pools
        active in the specified trailing time_period, in descending order of
        hashrate."""
        api_url = f"v1/mining/hashrate/pools/{time_period}"
        return self._request(api_url)

    def get_mining_pool_hashrate(self, slug):
        """Returns all known hashrate data for the mining pool specified by slug.

        Hashrate values are weekly averages.
        """
        api_url = f"v1/mining/pool/{slug}/hashrate"
        return self._request(api_url)

    def get_mining_pool_block(self, slug, block_height=None):
        """Returns past 10 blocks mined by the specified mining pool (slug) before the
        specified block_height.

        If no block_height is specified, the mining pool's 10 most
        recent blocks are returned.
        """
        if block_height is None:
            api_url = f"v1/mining/pool/{slug}/blocks"
        else:
            api_url = f"v1/mining/pool/{slug}/blocks/{block_height}"
        return self._request(api_url)

    def get_hashrate(self, time_period=None):
        """Returns network-wide hashrate and difficulty figures over the specified
        trailing :timePeriod:"""
        if time_period is None:
            api_url = "v1/mining/hashrate"
        else:
            api_url = f"v1/mining/hashrate/{time_period}"
        return self._request(api_url)

    def get_reward_stats(self, block_count):
        """Returns block reward and total transactions confirmed for the past.

        :blockCount blocks.
        """
        api_url = f"v1/mining/reward-stats/{block_count}"
        return self._request(api_url)

    def get_block_fees(self, time_period):
        """Returns average total fees for blocks over a trailing time period.

        The returned series is ordered from oldest to newest.
        Valid values include ``24h``, ``3d``, ``1w``, ``1m``, ``3m``, ``6m``,
        ``1y``, ``2y``, and ``3y``.
        """
        api_url = f"v1/mining/blocks/fees/{time_period}"
        return self._request(api_url)

    def get_block_rewards(self, time_period):
        """Returns average block rewards for blocks over a trailing time period.

        The returned series is ordered from oldest to newest.
        Valid values include ``24h``, ``3d``, ``1w``, ``1m``, ``3m``, ``6m``,
        ``1y``, ``2y``, and ``3y``.
        """
        api_url = f"v1/mining/blocks/rewards/{time_period}"
        return self._request(api_url)

    def get_block_feerates(self, time_period):
        """Returns average feerate percentiles for blocks in the specified.

        :timePeriod, ordered oldest to newest. :timePeriod can be any of
        the following: 24h, 3d, 1w, 1m, 3m, 6m, 1y, 2y, 3y.
        """
        api_url = f"v1/mining/blocks/fee-rates/{time_period}"
        return self._request(api_url)

    def get_block_sizes_and_weights(self, time_period):
        """Returns average size and weight for blocks over a trailing time period.

        The returned series is ordered from oldest to newest.
        Valid values include ``24h``, ``3d``, ``1w``, ``1m``, ``3m``, ``6m``,
        ``1y``, ``2y``, and ``3y``.
        """
        api_url = f"v1/mining/blocks/sizes-weights/{time_period}"
        return self._request(api_url)

    def get_mempool_blocks_fee(self):
        """Returns current mempool as projected blocks."""
        api_url = "v1/fees/mempool-blocks"
        return self._request(api_url)

    def get_recommended_fees(self):
        """Returns our currently suggested fees for new transactions."""
        api_url = "v1/fees/recommended"
        return self._request(api_url)

    def get_recommended_fees_precise(self):
        """Returns precise fee suggestions for new transactions."""
        api_url = "v1/fees/precise"
        return self._request(api_url)

    def get_mempool(self):
        """Returns current mempool backlog statistics."""
        api_url = "mempool"
        return self._request(api_url)

    def get_mempool_transactions_ids(self):
        """Get the full list of txids in the mempool as an array."""
        api_url = "mempool/txids"
        return self._request(api_url)

    def get_mempool_recent(self):
        """Get a list of the last 10 transactions to enter the mempool."""
        api_url = "mempool/recent"
        return self._request(api_url)

    def get_block_audit_summary(self, hash_value):
        """Returns the audit summary for the specified block."""
        hash_value = hash_value.replace(" ", "")
        api_url = f"v1/block/{hash_value}/audit-summary"
        return self._request(api_url)

    def get_children_pay_for_parents(self, txid):
        """Returns the ancestors and the best descendant fees for a transaction."""
        txid = txid.replace(" ", "")
        api_url = f"v1/cpfp/{txid}"
        return self._request(api_url)

    def get_transaction(self, txid):
        """Returns details about a transaction."""
        txid = txid.replace(" ", "")
        api_url = f"tx/{txid}"
        return self._request(api_url)

    def get_transaction_hex(self, txid):
        """Returns a transaction serialized as hex."""
        txid = txid.replace(" ", "")
        api_url = f"tx/{txid}/hex"
        return self._request(api_url)

    def get_transaction_merkleblock_proof(self, txid):
        """Returns a merkle inclusion proof for the transaction using bitcoind's
        merkleblock format."""
        txid = txid.replace(" ", "")
        api_url = f"tx/{txid}/merkleblock-proof"
        return self._request(api_url)

    def get_transaction_merkle_proof(self, txid):
        """Returns a merkle inclusion proof for the transaction using Electrum's
        blockchain.transaction.get_merkle format."""
        txid = txid.replace(" ", "")
        api_url = f"tx/{txid}/merkle-proof"
        return self._request(api_url)

    def get_transaction_outspend(self, txid, vout):
        """Returns the spending status of a transaction output."""
        txid = txid.replace(" ", "")
        vout = vout.replace(" ", "")
        api_url = f"tx/{txid}/outspend/{vout}"
        return self._request(api_url)

    def get_transaction_outspends(self, txid):
        """Returns the spending status of all transaction outputs."""
        txid = txid.replace(" ", "")
        api_url = f"tx/{txid}/outspends"
        return self._request(api_url)

    def get_transaction_raw(self, txid):
        """Returns a transaction as binary data."""
        txid = txid.replace(" ", "")
        api_url = f"tx/{txid}/raw"
        return self._request(api_url)

    def get_transaction_status(self, txid):
        """Returns the confirmation status of a transaction."""
        txid = txid.replace(" ", "")
        api_url = f"tx/{txid}/status"
        return self._request(api_url)

    def post_transaction(self, txHex):
        """Broadcast a raw transaction to the network."""
        txHex = txHex.replace(" ", "")
        api_url = "tx"
        return self._send(api_url, txHex)

    def get_network_stats(self, interval):
        """Returns network-wide stats such as total number of channels and nodes, total
        capacity, and average/median fee figures.

        Pass one of the following for interval: latest, 24h, 3d, 1w, 1m,
        3m, 6m, 1y, 2y, 3y.
        """
        api_url = f"v1/lightning/statistics/{interval}"
        return self._request(api_url)

    def get_nodes_channels(self, query):
        """Returns Lightning nodes and channels that match a full-text, case-insensitive
        search :query across node aliases, node pubkeys, channel IDs, and short channel
        IDs."""
        api_url = f"v1/lightning/search?searchText=:{query}"
        return self._request(api_url)

    def get_nodes_in_country(self, country):
        """Returns a list of Lightning nodes running on clearnet in the requested
        country, where :country is an ISO Alpha-2 country code."""
        api_url = f"v1/lightning/nodes/country/{country}"
        return self._request(api_url)

    def get_node_stat_per_country(self):
        """Returns aggregate capacity and number of clearnet nodes per country.

        Capacity figures are in satoshis.
        """
        api_url = "v1/lightning/nodes/countries"
        return self._request(api_url)

    def get_isp_nodes(self, isp):
        """Returns a list of nodes hosted by a specified isp, where isp is an ISP's
        ASN."""
        api_url = f"v1/lightning/nodes/nodes/isp/{isp}"
        return self._request(api_url)

    def get_node_stat_per_isp(self):
        """Returns aggregate capacity, number of nodes, and number of channels per ISP.

        Capacity figures are in satoshis.
        """
        api_url = "v1/lightning/nodes/isp-ranking"
        return self._request(api_url)

    def get_top_100_nodes(self):
        """Returns two lists of the top 100 nodes: one ordered by liquidity (aggregate
        channel capacity) and the other ordered by connectivity (number of open
        channels)."""
        api_url = "v1/lightning/nodes/rankings"
        return self._request(api_url)

    def get_top_100_nodes_by_liquidity(self):
        """Returns a list of the top 100 nodes by liquidity (aggregate channel
        capacity)."""
        api_url = "v1/lightning/nodes/rankings/liquidity"
        return self._request(api_url)

    def get_top_100_nodes_by_connectivity(self):
        """Returns a list of the top 100 nodes by connectivity (number of open
        channels)."""
        api_url = "v1/lightning/nodes/rankings/connectivity"
        return self._request(api_url)

    def get_top_100_oldest_nodes(self):
        """Returns a list of the top 100 oldest nodes."""
        api_url = "v1/lightning/nodes/rankings/age"
        return self._request(api_url)

    def get_node_stats(self, pubkey):
        """Returns details about a node with the given pubKey."""
        api_url = f"v1/lightning/nodes/{pubkey}"
        return self._request(api_url)

    def get_historical_node_stats(self, pubkey):
        """Returns details about a node with the given pubKey."""
        api_url = f"v1/lightning/nodes/{pubkey}/statistics"
        return self._request(api_url)

    def get_channel(self, channelid):
        """Returns info about a Lightning channel with the given :channelId."""
        api_url = f"v1/lightning/channels/{channelid}"
        return self._request(api_url)

    def get_channel_from_txid(self, txids: Union[str, list]) -> Any:
        """Returns info about Lightning channels with the given transaction IDs.

        Args:
            txids: Transaction ID string (comma-separated) or list of transaction IDs

        Returns:
            Information about the channels
        """
        base_url = "v1/lightning/channels/txids"

        # Convert txids to a list if it's a string
        if isinstance(txids, str):
            txid_list = txids.split(",")
        else:
            txid_list = txids

        # Build query parameters
        url = base_url
        connector = "?"

        for i, txid in enumerate(txid_list):
            if i == 0:
                url += f"{connector}txId[]={txid}"
                connector = "&"
            else:
                url += f"{connector}txId[]={txid}"

        return self._request(url)

    def get_channels_from_node_pubkey(self, pubkey, channel_status, index=None):
        """Returns a list of a node's channels given its :pubKey.

        Ten channels are returned at a time. Use :index for paging.
        :channelStatus can be open, active, or closed.
        """
        api_url = "v1/lightning/channels"
        params: dict = {
            "pub_key": pubkey,
            "status": channel_status,
            "index": index,
        }
        api_url = self._build_url_with_params(api_url, params)
        return self._request(api_url)

    def get_channel_geodata(self):
        """Returns a list of channels with corresponding node geodata."""
        api_url = "v1/lightning/channels-geo"
        return self._request(api_url)

    def get_channel_geodata_for_node(self, pubkey):
        """Returns a list of channels with corresponding geodata for a node with the
        given :pubKey."""
        api_url = f"v1/lightning/channels-geo/{pubkey}"
        return self._request(api_url)
