import unittest

import pytest
import responses

from pymempool import MempoolAPI
from pymempool.api import (
    MempoolNetworkError,
    MempoolRateLimitError,
    MempoolResponseError,
)


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.current = start
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.current += seconds


class TestWrapper(unittest.TestCase):
    @responses.activate
    def test_connection_error(self):
        with pytest.raises(MempoolNetworkError):
            MempoolAPI(api_base_url="https://mempool.space/api/").get_block_tip_height()

    @responses.activate
    def test_failed_height(self):
        # Arrange
        responses.add(
            responses.GET,
            "https://mempool.space/api/blocks/tip/height",
            status=404,
            body="Not Found",
        )

        # Act Assert
        with pytest.raises(MempoolResponseError):
            MempoolAPI(api_base_url="https://mempool.space/api/").get_block_tip_height()

    @responses.activate
    def test_get_adress(self):
        # Arrange
        ping_json = {}
        responses.add(
            responses.GET,
            "https://mempool.space/api/address/1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv",
            json=ping_json,
            status=200,
        )

        # Act
        response = MempoolAPI(api_base_url="https://mempool.space/api/").get_address(
            "1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv"
        )

        self.assertEqual(response, ping_json)

    @responses.activate
    def test_post(self):
        responses.add(
            responses.POST,
            "https://mempool.space/api/tx",
            status=400,
            body='{"code":-25,"message":"bad-txns-inputs-missingorspent"}',
        )

        with pytest.raises(MempoolResponseError):
            MempoolAPI(api_base_url="https://mempool.space/api/").post_transaction(
                "0200000001fd5b5fcd1cb066c27cfc9fda5428b9be850b81ac440ea51f1ddba2f9871"
                "89ac1010000008a4730440220686a40e9d2dbffeab4ca1ff66341d06a17806767f12a"
                "1fc4f55740a7af24c6b5022049dd3c9a85ac6c51fecd5f4baff7782a518781bbdd944"
                "53c8383755e24ba755c01410436d554adf4a3eb03a317c77aa4020a7bba62999df63"
                "bba0ea8f83f48b9e01b0861d3b3c796840f982ee6b14c3c4b7ad04fcfcc3774f81bf"
                "f9aaf52a15751fedfdffffff02416c00000000000017a914bc791b2afdfe1e1b5650"
                "864a9297b20d74c61f4787d71d0000000000001976a9140a59837ccd4df25adc31cd"
                "ad39be6a8d97557ed688ac00000000"
            )

    @responses.activate
    def test_difficulty_adjustment(self):
        base_api_url = "https://mempool.space/api/"
        # Arrange
        res_json = {}
        responses.add(
            responses.GET,
            f"{base_api_url}v1/difficulty-adjustment",
            json=res_json,
            status=200,
        )

        # Act
        response = MempoolAPI(api_base_url=base_api_url).get_difficulty_adjustment()
        self.assertEqual(response, res_json)

    @responses.activate
    def test_address_transactions(self):
        base_api_url = "https://mempool.space/api/"
        address = "1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv"
        # Arrange
        res_json = {}
        responses.add(
            responses.GET,
            f"{base_api_url}address/{address}/txs",
            json=res_json,
            status=200,
        )

        # Act
        response = MempoolAPI(api_base_url=base_api_url).get_address_transactions(
            address
        )
        self.assertEqual(response, res_json)

    @responses.activate
    def test_address_transactions_chain(self):
        base_api_url = "https://mempool.space/api/"
        address = "1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv"
        # Arrange
        res_json = {}
        responses.add(
            responses.GET,
            f"{base_api_url}address/{address}/txs/chain",
            json=res_json,
            status=200,
        )

        # Act
        response = MempoolAPI(api_base_url=base_api_url).get_address_transactions_chain(
            address
        )
        self.assertEqual(response, res_json)

        last_seen_txid = (
            "4654a83d953c68ba2c50473a80921bb4e1f01d428b18c65ff0128920865cc314"
        )
        res_json2 = {}
        responses.add(
            responses.GET,
            f"{base_api_url}address/{address}/txs/chain/{last_seen_txid}",
            json=res_json2,
            status=200,
        )

        # Act
        response = MempoolAPI(api_base_url=base_api_url).get_address_transactions_chain(
            address, last_seen_txid
        )
        self.assertEqual(response, res_json2)

    @responses.activate
    def test_address_transactions_mempool(self):
        base_api_url = "https://mempool.space/api/"
        address = "1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv"
        # Arrange
        res_json = {}
        responses.add(
            responses.GET,
            f"{base_api_url}address/{address}/txs/mempool",
            json=res_json,
            status=200,
        )

        # Act
        response = MempoolAPI(
            api_base_url=base_api_url
        ).get_address_transactions_mempool(address)
        self.assertEqual(response, res_json)

    @responses.activate
    def test_address_utxo(self):
        base_api_url = "https://mempool.space/api/"
        address = "1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv"
        # Arrange
        res_json = {}
        responses.add(
            responses.GET,
            f"{base_api_url}address/{address}/utxo",
            json=res_json,
            status=200,
        )

        # Act
        response = MempoolAPI(api_base_url=base_api_url).get_address_utxo(address)
        self.assertEqual(response, res_json)

    @responses.activate
    def test_get_recommended_fees_precise(self):
        base_api_url = "https://mempool.space/api/"
        res_json = {
            "fastestFee": 12.345,
            "halfHourFee": 8.75,
            "hourFee": 5.5,
            "economyFee": 2.25,
            "minimumFee": 1.001,
        }
        responses.add(
            responses.GET,
            f"{base_api_url}v1/fees/precise",
            json=res_json,
            status=200,
        )

        response = MempoolAPI(api_base_url=base_api_url).get_recommended_fees_precise()
        self.assertEqual(response, res_json)

    @responses.activate
    def test_get_mempool_recent(self):
        base_api_url = "https://mempool.space/api/"
        res_json = [{"txid": "abc", "fee": 250, "vsize": 140, "value": 1000}]
        responses.add(
            responses.GET,
            f"{base_api_url}mempool/recent",
            json=res_json,
            status=200,
        )

        response = MempoolAPI(api_base_url=base_api_url).get_mempool_recent()
        self.assertEqual(response, res_json)

    @responses.activate
    def test_get_block_audit_summary(self):
        base_api_url = "https://mempool.space/api/"
        block_hash = "00" * 32
        res_json = {"id": block_hash, "matchRate": 99.8}
        responses.add(
            responses.GET,
            f"{base_api_url}v1/block/{block_hash}/audit-summary",
            json=res_json,
            status=200,
        )

        response = MempoolAPI(api_base_url=base_api_url).get_block_audit_summary(
            block_hash
        )
        self.assertEqual(response, res_json)

    @responses.activate
    def test_429_with_retry_after_raises_rate_limit_error_and_sets_cooldown(self):
        base_api_url = "https://mempool.space/api/"
        clock = FakeClock()
        responses.add(
            responses.GET,
            f"{base_api_url}mempool",
            status=429,
            headers={"Retry-After": "8"},
            body='{"error":"slow down"}',
        )

        api = MempoolAPI(api_base_url=base_api_url)
        api.rate_limiter._time_func = clock.time
        api.rate_limiter._sleep_func = clock.sleep
        api.response_cache._time_func = clock.time

        with pytest.raises(MempoolRateLimitError) as exc:
            api.get_mempool()

        assert exc.value.retry_after_seconds == 8.0
        assert exc.value.cooldown_seconds == 8.0
        assert exc.value.host == "mempool.space"

    @responses.activate
    def test_429_without_retry_after_uses_backoff_jitter(self):
        base_api_url = "https://mempool.space/api/"
        clock = FakeClock()
        responses.add(
            responses.GET,
            f"{base_api_url}mempool",
            status=429,
            body='{"error":"slow down"}',
        )

        api = MempoolAPI(api_base_url=base_api_url)
        api.rate_limiter._time_func = clock.time
        api.rate_limiter._sleep_func = clock.sleep
        api.rate_limiter._random_func = lambda _a, _b: 0.5
        api.response_cache._time_func = clock.time

        with pytest.raises(MempoolRateLimitError) as exc:
            api.get_mempool()

        assert exc.value.retry_after_seconds is None
        assert exc.value.cooldown_seconds == 1.0

    @responses.activate
    def test_repeated_429s_increase_cooldown(self):
        base_api_url = "https://mempool.space/api/"
        clock = FakeClock()
        responses.add(
            responses.GET,
            f"{base_api_url}address/test",
            status=429,
            body='{"error":"slow down"}',
        )
        responses.add(
            responses.GET,
            f"{base_api_url}address/test",
            status=429,
            body='{"error":"slow down again"}',
        )

        api = MempoolAPI(api_base_url=base_api_url, enable_response_cache=False)
        api.rate_limiter._time_func = clock.time
        api.rate_limiter._sleep_func = clock.sleep
        api.rate_limiter._random_func = lambda _a, _b: 0.0

        with pytest.raises(MempoolRateLimitError) as first:
            api.get_address("test")
        with pytest.raises(MempoolRateLimitError) as second:
            api.get_address("test")

        assert first.value.cooldown_seconds == 0.5
        assert second.value.cooldown_seconds == 1.0

    @responses.activate
    def test_rate_limited_host_fails_over_once_to_next_host(self):
        primary = "https://mempool.space/api/"
        fallback = "https://mempool.emzy.de/api/"
        responses.add(
            responses.GET,
            f"{primary}address/test",
            status=429,
            body='{"error":"slow down"}',
        )
        responses.add(
            responses.GET,
            f"{fallback}address/test",
            json={"ok": True},
            status=200,
        )

        api = MempoolAPI(
            api_base_url=f"{primary},{fallback}", enable_response_cache=False
        )
        result = api.get_address("test")

        assert result == {"ok": True}
        assert len(responses.calls) == 2

    @responses.activate
    def test_all_hosts_cooling_down_waits_for_earliest_host(self):
        primary = "https://mempool.space/api/"
        fallback = "https://mempool.emzy.de/api/"
        clock = FakeClock()
        api = MempoolAPI(
            api_base_url=f"{primary},{fallback}", enable_response_cache=False
        )
        api.rate_limiter._time_func = clock.time
        api.rate_limiter._sleep_func = clock.sleep
        api.rate_limiter.punish_429("mempool.space", retry_after=5.0, attempt=1)
        api.rate_limiter.punish_429("mempool.emzy.de", retry_after=2.0, attempt=1)

        responses.add(
            responses.GET,
            f"{fallback}address/test",
            json={"ok": True},
            status=200,
        )

        result = api.get_address("test")

        assert result == {"ok": True}
        assert clock.sleeps == [2.0]

    @responses.activate
    def test_cache_reuses_hot_endpoint_within_ttl(self):
        base_api_url = "https://mempool.space/api/"
        clock = FakeClock()
        responses.add(
            responses.GET,
            f"{base_api_url}mempool",
            json={"count": 1, "vsize": 2},
            status=200,
        )

        api = MempoolAPI(api_base_url=base_api_url, cache_ttl_seconds=3.0)
        api.rate_limiter._time_func = clock.time
        api.rate_limiter._sleep_func = clock.sleep
        api.response_cache._time_func = clock.time

        first = api.get_mempool()
        second = api.get_mempool()

        assert first == second == {"count": 1, "vsize": 2}
        assert len(responses.calls) == 1

    @responses.activate
    def test_rate_limited_hot_endpoint_returns_stale_cache(self):
        base_api_url = "https://mempool.space/api/"
        clock = FakeClock()
        responses.add(
            responses.GET,
            f"{base_api_url}mempool",
            json={"count": 1, "vsize": 2},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{base_api_url}mempool",
            status=429,
            body='{"error":"slow down"}',
        )

        notices: list[str] = []
        api = MempoolAPI(
            api_base_url=base_api_url,
            cache_ttl_seconds=1.0,
            rate_limit_notifier=notices.append,
        )
        api.rate_limiter._time_func = clock.time
        api.rate_limiter._sleep_func = clock.sleep
        api.response_cache._time_func = clock.time

        first = api.get_mempool()
        clock.current = 2.0
        second = api.get_mempool()

        assert first == second == {"count": 1, "vsize": 2}
        assert "Using cached snapshot while upstream rate limit clears." in notices

    @responses.activate
    def test_non_429_response_errors_still_raise_response_error(self):
        base_api_url = "https://mempool.space/api/"
        responses.add(
            responses.GET,
            f"{base_api_url}address/test",
            status=404,
            json={"error": "not found"},
        )

        with pytest.raises(MempoolResponseError):
            MempoolAPI(
                api_base_url=base_api_url, enable_response_cache=False
            ).get_address("test")
