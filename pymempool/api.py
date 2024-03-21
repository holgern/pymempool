import json
import logging
import warnings

import requests
from requests.adapters import HTTPAdapter
from requests.packages import urllib3

logger = logging.getLogger(__name__)


class MempoolAPI:
    __API_URL_BASE = [
        "https://mempool.space/api/",
        "https://mempool.emzy.de/api/",
        "https://mempool.bitcoin-21.org/api/",
    ]

    def __init__(
        self, api_base_url=__API_URL_BASE, retries=3, request_verify=True, proxies=None
    ):
        self.set_api_base_url(api_base_url)
        self.proxies = proxies
        self.connect_timeout = 1
        self.reading_timeout = 120
        self.sending_timeout = 120
        self.request_verify = request_verify
        if not request_verify:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        self.session = requests.Session()
        retries = urllib3.util.retry.Retry(
            total=retries, backoff_factor=0.1, status_forcelist=[502, 503, 504, 429]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def set_api_base_url(self, api_base_url):
        if isinstance(api_base_url, list):
            self.api_base_url = api_base_url
        else:
            self.api_base_url = api_base_url.split(",")

    def get_api_base_url(self, index=0):
        if len(self.api_base_url) > index:
            return self.api_base_url[index]
        else:
            return self.api_base_url[0]

    def _request(self, url):
        index = 0
        while True:
            complete_url = f"{self.get_api_base_url(index)}{url}"
            try:
                return self.__request(complete_url)
            except Exception as e:
                logger.info(f"Timeout on {complete_url} - {e}")
                index += 1
                if index >= len(self.api_base_url):
                    raise

    def __request(self, url):
        logger.info(url)
        try:
            response = self.session.get(
                url,
                timeout=(self.connect_timeout, self.reading_timeout),
                verify=self.request_verify,
                proxies=self.proxies,
            )
        except requests.exceptions.RequestException:
            raise
        try:
            response.raise_for_status()

        except Exception:
            # check if json (with error message) is returned
            try:
                content = json.loads(response.content.decode('utf-8'))
                raise ValueError(content)
            # if no json
            except json.decoder.JSONDecodeError:
                pass
            raise
        try:
            decoded_content = response.content.decode('utf-8')
            content = json.loads(decoded_content)
            return content
        except UnicodeDecodeError:
            return response.content
        except json.decoder.JSONDecodeError:
            return response.content.decode('utf-8')
        raise

    def _send(self, url, data):
        index = 0
        while True:
            complete_url = f"{self.get_api_base_url(index)}{url}"
            try:
                return self.__send(complete_url, data)
            except Exception as e:
                logger.info(f"Timeout on {complete_url} - {e}")
                index += 1
                if index >= len(self.api_base_url):
                    raise

    def __send(self, url, data):
        logger.info(url)
        try:
            req = requests.Request('POST', url, data=data)
            prepped = req.prepare()
            response = self.session.send(
                prepped,
                timeout=(self.connect_timeout, self.sending_timeout),
                verify=self.request_verify,
            )
        except requests.exceptions.RequestException:
            raise

        try:
            response.raise_for_status()
            content = response.content.decode('utf-8')
            return content
        except Exception:
            # check if json (with error message) is returned
            try:
                content = response.content.decode('utf-8')
                raise ValueError(content)
            # if no json
            except json.decoder.JSONDecodeError:
                pass

            raise

    def get_price(self):
        """Returns bitcoin latest price denominated in main currencies."""
        api_url = 'v1/prices'
        return self._request(api_url)

    def get_historical_price(self, currency=None, timestamp=None):
        """Returns bitcoin historical price denominated in main currencies.

        Available query parameters: currency, timestamp.
        If no parameter is provided, the full price history
        for all currencies is returned.
        """
        api_url = 'v1/historical-price'
        connector = "?"
        if currency is not None:
            currency = str(currency).upper()
            api_url += f'{connector}currency={currency}'
            connector = "&"
        if timestamp is not None:
            timestamp = int(timestamp)
            api_url += f'{connector}timestamp={timestamp}'
        return self._request(api_url)

    def get_difficulty_adjustment(self):
        """Returns details about difficulty adjustment."""
        api_url = 'v1/difficulty-adjustment'
        return self._request(api_url)

    def get_address(self, address):
        """Returns details about an address."""
        address = address.replace(' ', '')
        api_url = f'address/{address}'
        return self._request(api_url)

    def get_address_transactions(self, address):
        """Get transaction history for the specified address/scripthash, sorted with
        newest first."""
        address = address.replace(' ', '')
        api_url = f'address/{address}/txs'
        return self._request(api_url)

    def get_address_transactions_chain(self, address, last_seen_txid=None):
        """Get confirmed transaction history for the specified address/scripthash,
        sorted with newest first."""
        address = address.replace(' ', '')
        if last_seen_txid is None:
            api_url = f'address/{address}/txs/chain'
        else:
            api_url = f'address/{address}/txs/chain/{last_seen_txid}'
        return self._request(api_url)

    def get_address_transactions_mempool(self, address):
        """Get unconfirmed transaction history for the specified address/scripthash."""
        address = address.replace(' ', '')
        api_url = f'address/{address}/txs/mempool'
        return self._request(api_url)

    def get_address_utxo(self, address):
        """Get the list of unspent transaction outputs associated with the
        address/scripthash."""
        address = address.replace(' ', '')
        api_url = f'address/{address}/utxo'
        return self._request(api_url)

    def get_block(self, hash_value):
        """Returns details about a block."""
        hash_value = hash_value.replace(' ', '')
        api_url = f'block/{hash_value}'
        return self._request(api_url)

    def get_block_header(self, hash_value):
        """Returns the hex-encoded block header."""
        hash_value = hash_value.replace(' ', '')
        api_url = f'block/{hash_value}/header'
        return self._request(api_url)

    def get_block_height(self, height):
        """Returns the hash of the block currently at height."""
        height = int(height)
        api_url = f'block-height/{height}'
        return self._request(api_url)

    def get_block_raw(self, hash_value):
        """Returns the raw block representation in binary."""
        hash_value = hash_value.replace(' ', '')
        api_url = f'block/{hash_value}/raw'
        return self._request(api_url)

    def get_block_status(self, hash_value):
        """Returns the confirmation status of a block."""
        hash_value = hash_value.replace(' ', '')
        api_url = f'block/{hash_value}/status'
        return self._request(api_url)

    def get_block_tip_height(self):
        """Returns the height of the last block."""
        api_url = 'blocks/tip/height'
        return self._request(api_url)

    def get_block_tip_hash(self):
        """Returns the hash of the last block."""
        api_url = 'blocks/tip/hash'
        return self._request(api_url)

    def get_block_transaction_id(self, hash_value, index):
        """Returns the transaction at index index within the specified block."""
        hash_value = hash_value.replace(' ', '')
        index = int(index)
        api_url = f'block/{hash_value}/txid/{index}'
        return self._request(api_url)

    def get_block_transaction_ids(self, hash_value):
        """Returns a list of all txids in the block."""
        hash_value = hash_value.replace(' ', '')
        api_url = f'block/{hash_value}/txids'
        return self._request(api_url)

    def get_block_transactions(self, hash_value, start_index=None):
        """Returns a list of transactions in the block (up to 25 transactions beginning
        at start_index)."""
        hash_value = hash_value.replace(' ', '')
        if start_index is not None:
            start_index = int(start_index)
            api_url = f'block/{hash_value}/txs/{start_index}'
        else:
            api_url = f'block/{hash_value}/txs'
        return self._request(api_url)

    def get_blocks(self, start_height=None):
        """Returns the 10 newest blocks starting at the tip or at :start_height if
        specified."""
        if start_height is None:
            api_url = 'v1/blocks'
        else:
            start_height = int(start_height)
            api_url = f'v1/blocks/{start_height}'
        return self._request(api_url)

    def get_blocks_bulk(self, min_height, max_height=None):
        """Returns details on the range of blocks between :min_height and :max_height,
        inclusive, up to 10 blocks.

        If :max_height is not specified, it defaults to the current tip.
        """
        if max_height is None:
            min_height = int(min_height)
            api_url = f'v1/blocks-bulk/{min_height}'
        else:
            min_height = int(min_height)
            max_height = int(max_height)
            api_url = f'v1/blocks-bulk/{min_height}/{max_height}'
        return self._request(api_url)

    def get_mining_pools(self, time_period):
        """Returns a list of all known mining pools ordered by blocks found over the
        specified trailing time_period."""
        api_url = f'v1/mining/pools/{time_period}'
        return self._request(api_url)

    def get_mining_pool(self, slug):
        """Returns details about the mining pool specified by slug."""
        api_url = f'v1/mining/pool/{slug}'
        return self._request(api_url)

    def get_mining_pool_hashrates(self, time_period):
        """Returns average hashrates (and share of total hashrate) of mining pools
        active in the specified trailing time_period, in descending order of
        hashrate."""
        api_url = f'v1/mining/hashrate/pools/{time_period}'
        return self._request(api_url)

    def get_mining_pool_hashrate(self, slug):
        """Returns all known hashrate data for the mining pool specified by slug.

        Hashrate values are weekly averages.
        """
        api_url = f'v1/mining/pool/{slug}/hashrate'
        return self._request(api_url)

    def get_mining_pool_block(self, slug, block_height=None):
        """Returns past 10 blocks mined by the specified mining pool (slug) before the
        specified block_height.

        If no block_height is specified, the mining pool's 10 most
        recent blocks are returned.
        """
        if block_height is None:
            api_url = f'v1/mining/pool/{slug}/blocks'
        else:
            api_url = f'v1/mining/pool/{slug}/blocks/{block_height}'
        return self._request(api_url)

    def get_hashrate(self, time_period=None):
        """Returns network-wide hashrate and difficulty figures over the specified
        trailing :timePeriod:"""
        if time_period is None:
            api_url = 'v1/mining/hashrate'
        else:
            api_url = f'v1/mining/hashrate/{time_period}'
        return self._request(api_url)

    def get_reward_stats(self, block_count):
        """Returns block reward and total transactions confirmed for the past.

        :blockCount blocks.
        """
        api_url = f'v1/mining/reward-stats/{block_count}'
        return self._request(api_url)

    def get_block_fees(self, time_period):
        """Returns average total fees for blocks in the specified :timePeriod, ordered
        oldest to newest.

        :timePeriod can be any of the following: 24h, 3d, 1w, 1m, 3m,
        6m, 1y, 2y, 3y.
        """
        api_url = f'v1/mining/blocks/fees/{time_period}'
        return self._request(api_url)

    def get_block_rewards(self, time_period):
        """Returns average block rewards for blocks in the specified :timePeriod,
        ordered oldest to newest.

        :timePeriod can be any of the following: 24h, 3d, 1w, 1m, 3m,
        6m, 1y, 2y, 3y.
        """
        api_url = f'v1/mining/blocks/rewards/{time_period}'
        return self._request(api_url)

    def get_block_feerates(self, time_period):
        """Returns average feerate percentiles for blocks in the specified.

        :timePeriod, ordered oldest to newest. :timePeriod can be any of
        the following: 24h, 3d, 1w, 1m, 3m, 6m, 1y, 2y, 3y.
        """
        api_url = f'v1/mining/blocks/fee-rates/{time_period}'
        return self._request(api_url)

    def get_block_sizes_and_weights(self, time_period):
        """Returns average size (bytes) and average weight (weight units) for blocks in
        the specified :timePeriod, ordered oldest to newest.

        :timePeriod can be any of the following: 24h, 3d, 1w, 1m, 3m,
        6m, 1y, 2y, 3y.
        """
        api_url = f'v1/mining/blocks/sizes-weights/{time_period}'
        return self._request(api_url)

    def get_mempool_blocks_fee(self):
        """Returns current mempool as projected blocks."""
        api_url = 'v1/fees/mempool-blocks'
        return self._request(api_url)

    def get_recommended_fees(self):
        """Returns our currently suggested fees for new transactions."""
        api_url = 'v1/fees/recommended'
        return self._request(api_url)

    def get_mempool(self):
        """Returns current mempool backlog statistics."""
        api_url = 'mempool'
        return self._request(api_url)

    def get_mempool_transactions_ids(self):
        """Get the full list of txids in the mempool as an array."""
        api_url = 'mempool/txids'
        return self._request(api_url)

    def get_mempool_recent(self):
        """Get a list of the last 10 transactions to enter the mempool."""
        api_url = 'mempool/recent'
        return self._request(api_url)

    def get_children_pay_for_parents(self, txid):
        """Returns the ancestors and the best descendant fees for a transaction."""
        txid = txid.replace(' ', '')
        api_url = f'v1/cpfp/{txid}'
        return self._request(api_url)

    def get_transaction(self, txid):
        """Returns details about a transaction."""
        txid = txid.replace(' ', '')
        api_url = f'tx/{txid}'
        return self._request(api_url)

    def get_transaction_hex(self, txid):
        """Returns a transaction serialized as hex."""
        txid = txid.replace(' ', '')
        api_url = f'tx/{txid}/hex'
        return self._request(api_url)

    def get_transaction_merkleblock_proof(self, txid):
        """Returns a merkle inclusion proof for the transaction using bitcoind's
        merkleblock format."""
        txid = txid.replace(' ', '')
        api_url = f'tx/{txid}/merkleblock-proof'
        return self._request(api_url)

    def get_transaction_merkle_proof(self, txid):
        """Returns a merkle inclusion proof for the transaction using Electrum's
        blockchain.transaction.get_merkle format."""
        txid = txid.replace(' ', '')
        api_url = f'tx/{txid}/merkle-proof'
        return self._request(api_url)

    def get_transaction_outspend(self, txid, vout):
        """Returns the spending status of a transaction output."""
        txid = txid.replace(' ', '')
        vout = vout.replace(' ', '')
        api_url = f'tx/{txid}/outspend/{vout}'
        return self._request(api_url)

    def get_transaction_outspends(self, txid):
        """Returns the spending status of all transaction outputs."""
        txid = txid.replace(' ', '')
        api_url = f'tx/{txid}/outspends'
        return self._request(api_url)

    def get_transaction_raw(self, txid):
        """Returns a transaction as binary data."""
        txid = txid.replace(' ', '')
        api_url = f'tx/{txid}/raw'
        return self._request(api_url)

    def get_transaction_status(self, txid):
        """Returns the confirmation status of a transaction."""
        txid = txid.replace(' ', '')
        api_url = f'tx/{txid}/status'
        return self._request(api_url)

    def post_transaction(self, txHex):
        """Broadcast a raw transaction to the network."""
        txHex = txHex.replace(' ', '')
        api_url = 'tx'
        return self._send(api_url, txHex)

    def get_network_stats(self, interval):
        """Returns network-wide stats such as total number of channels and nodes, total
        capacity, and average/median fee figures.

        Pass one of the following for interval: latest, 24h, 3d, 1w, 1m,
        3m, 6m, 1y, 2y, 3y.
        """
        api_url = f'v1/lightning/statistics/{interval}'
        return self._request(api_url)

    def get_nodes_channels(self, query):
        """Returns Lightning nodes and channels that match a full-text, case-insensitive
        search :query across node aliases, node pubkeys, channel IDs, and short channel
        IDs."""
        api_url = f'v1/lightning/search?searchText=:{query}'
        return self._request(api_url)

    def get_nodes_in_country(self, country):
        """Returns a list of Lightning nodes running on clearnet in the requested
        country, where :country is an ISO Alpha-2 country code."""
        api_url = f'v1/lightning/nodes/country/{country}'
        return self._request(api_url)

    def get_node_stat_per_country(self):
        """Returns aggregate capacity and number of clearnet nodes per country.

        Capacity figures are in satoshis.
        """
        api_url = 'v1/lightning/nodes/countries'
        return self._request(api_url)

    def get_isp_nodes(self, isp):
        """Returns a list of nodes hosted by a specified isp, where isp is an ISP's
        ASN."""
        api_url = f'v1/lightning/nodes/nodes/isp/{isp}'
        return self._request(api_url)

    def get_node_stat_per_isp(self):
        """Returns aggregate capacity, number of nodes, and number of channels per ISP.

        Capacity figures are in satoshis.
        """
        api_url = 'v1/lightning/nodes/isp-ranking'
        return self._request(api_url)

    def get_top_100_nodes(self):
        """Returns two lists of the top 100 nodes: one ordered by liquidity (aggregate
        channel capacity) and the other ordered by connectivity (number of open
        channels)."""
        api_url = 'v1/lightning/nodes/rankings'
        return self._request(api_url)

    def get_top_100_nodes_by_liquidity(self):
        """Returns a list of the top 100 nodes by liquidity (aggregate channel
        capacity)."""
        api_url = 'v1/lightning/nodes/rankings/liquidity'
        return self._request(api_url)

    def get_top_100_nodes_by_connectivity(self):
        """Returns a list of the top 100 nodes by connectivity (number of open
        channels)."""
        api_url = 'v1/lightning/nodes/rankings/connectivity'
        return self._request(api_url)

    def get_top_100_oldest_nodes(self):
        """Returns a list of the top 100 oldest nodes."""
        api_url = 'v1/lightning/nodes/rankings/age'
        return self._request(api_url)

    def get_node_stats(self, pubkey):
        """Returns details about a node with the given pubKey."""
        api_url = f'v1/lightning/nodes/{pubkey}'
        return self._request(api_url)

    def get_historical_node_stats(self, pubkey):
        """Returns details about a node with the given pubKey."""
        api_url = f'v1/lightning/nodes/{pubkey}/statistics'
        return self._request(api_url)

    def get_channel(self, channelid):
        """Returns info about a Lightning channel with the given :channelId."""
        api_url = f'v1/lightning/channels/{channelid}'
        return self._request(api_url)

    def get_channel_from_txid(self, txids):
        """Returns info about a Lightning channel with the given :channelId."""
        api_url = 'v1/lightning/channels/txids'
        if isinstance(txids, "str"):
            first = True
            for txid in txids.split(","):
                if first:
                    api_url += f'?txId[]={txid}'
                    first = False
                else:
                    api_url += f'&txId[]={txid}'
        elif isinstance(txids, list):
            first = True
            for txid in txids:
                if first:
                    api_url += f'?txId[]={txid}'
                    first = True
                else:
                    api_url += f'&txId[]={txid}'
        return self._request(api_url)

    def get_channels_from_node_pubkey(self, pubkey, channel_status, index=None):
        """Returns a list of a node's channels given its :pubKey.

        Ten channels are returned at a time. Use :index for paging.
        :channelStatus can be open, active, or closed.
        """
        api_url = 'v1/lightning/channels'
        api_url += f'?pub_key={pubkey}&status={channel_status}'
        if index is not None:
            api_url += f'&index={index}'
        return self._request(api_url)

    def get_channel_geodata(self):
        """Returns a list of channels with corresponding node geodata."""
        api_url = 'v1/lightning/channels-geo'
        return self._request(api_url)

    def get_channel_geodata_for_node(self, pubkey):
        """Returns a list of channels with corresponding geodata for a node with the
        given :pubKey."""
        api_url = f'v1/lightning/channels-geo/{pubkey}'
        return self._request(api_url)
