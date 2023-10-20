import json
import warnings

import requests
from requests.adapters import HTTPAdapter
from requests.packages import urllib3


class MempoolAPI:
    __API_URL_BASE = "https://mempool.space/api/"

    def __init__(
        self, api_base_url=__API_URL_BASE, retries=5, request_verify=True, proxies=None
    ):
        self.api_base_url = api_base_url
        self.proxies = proxies
        self.request_timeout = 120
        self.request_verify = request_verify
        if not request_verify:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        self.session = requests.Session()
        retries = urllib3.util.retry.Retry(
            total=retries, backoff_factor=0.5, status_forcelist=[502, 503, 504]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def __request(self, url):
        # print(url)
        try:
            response = self.session.get(
                url,
                timeout=self.request_timeout,
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

    def __send(self, url, data):
        # print(url)
        try:
            req = requests.Request('POST', url, data=data)
            prepped = req.prepare()
            response = self.session.send(
                prepped, timeout=self.request_timeout, verify=self.request_verify
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

    def get_difficulty_adjustment(self):
        """Returns details about difficulty adjustment."""
        api_url = f'{self.api_base_url}v1/difficulty-adjustment'
        return self.__request(api_url)

    def get_address(self, address):
        """Returns details about an address."""
        address = address.replace(' ', '')
        api_url = f'{self.api_base_url}address/{address}'
        return self.__request(api_url)

    def get_address_transactions(self, address):
        """Get transaction history for the specified address/scripthash, sorted with
        newest first."""
        address = address.replace(' ', '')
        api_url = f'{self.api_base_url}address/{address}/txs'
        return self.__request(api_url)

    def get_address_transactions_chain(self, address, last_seen_txid=None):
        """Get confirmed transaction history for the specified address/scripthash,
        sorted with newest first."""
        address = address.replace(' ', '')
        if last_seen_txid is None:
            api_url = f'{self.api_base_url}address/{address}/txs/chain'
        else:
            api_url = '{}address/{}/txs/chain/{}'.format(
                self.api_base_url, address, last_seen_txid
            )
        return self.__request(api_url)

    def get_address_transactions_mempool(self, address):
        """Get unconfirmed transaction history for the specified address/scripthash."""
        address = address.replace(' ', '')
        api_url = f'{self.api_base_url}address/{address}/txs/mempool'
        return self.__request(api_url)

    def get_address_utxo(self, address):
        """Get the list of unspent transaction outputs associated with the
        address/scripthash."""
        address = address.replace(' ', '')
        api_url = f'{self.api_base_url}address/{address}/utxo'
        return self.__request(api_url)

    def get_block(self, hash_value):
        """Returns details about a block."""
        hash_value = hash_value.replace(' ', '')
        api_url = f'{self.api_base_url}block/{hash_value}'
        return self.__request(api_url)

    def get_block_header(self, hash_value):
        """Returns the hex-encoded block header."""
        hash_value = hash_value.replace(' ', '')
        api_url = f'{self.api_base_url}block/{hash_value}/header'
        return self.__request(api_url)

    def get_block_height(self, height):
        """Returns the hash of the block currently at height."""
        height = int(height)
        api_url = f'{self.api_base_url}block-height/{height}'
        return self.__request(api_url)

    def get_block_raw(self, hash_value):
        """Returns the raw block representation in binary."""
        hash_value = hash_value.replace(' ', '')
        api_url = f'{self.api_base_url}block/{hash_value}/raw'
        return self.__request(api_url)

    def get_block_status(self, hash_value):
        """Returns the confirmation status of a block."""
        hash_value = hash_value.replace(' ', '')
        api_url = f'{self.api_base_url}block/{hash_value}/status'
        return self.__request(api_url)

    def get_block_tip_height(self):
        """Returns the height of the last block."""
        api_url = f'{self.api_base_url}blocks/tip/height'
        return self.__request(api_url)

    def get_block_tip_hash(self):
        """Returns the hash of the last block."""
        api_url = f'{self.api_base_url}blocks/tip/hash'
        return self.__request(api_url)

    def get_block_transaction_id(self, hash_value, index):
        """Returns the transaction at index index within the specified block."""
        hash_value = hash_value.replace(' ', '')
        index = int(index)
        api_url = f'{self.api_base_url}block/{hash_value}/txid/{index}'
        return self.__request(api_url)

    def get_block_transaction_ids(self, hash_value):
        """Returns a list of all txids in the block."""
        hash_value = hash_value.replace(' ', '')
        api_url = f'{self.api_base_url}block/{hash_value}/txids'
        return self.__request(api_url)

    def get_block_transactions(self, hash_value, start_index=None):
        """Returns a list of transactions in the block (up to 25 transactions beginning
        at start_index)."""
        hash_value = hash_value.replace(' ', '')
        if start_index is not None:
            start_index = int(start_index)
            api_url = '{}block/{}/txs/{}'.format(
                self.api_base_url, hash_value, start_index
            )
        else:
            api_url = f'{self.api_base_url}block/{hash_value}/txs'
        return self.__request(api_url)

    def get_blocks(self, start_height=None):
        """Returns the 10 newest blocks starting at the tip or at :start_height if
        specified."""
        if start_height is None:
            api_url = f'{self.api_base_url}v1/blocks'
        else:
            start_height = int(start_height)
            api_url = f'{self.api_base_url}v1/blocks/{start_height}'
        return self.__request(api_url)

    def get_blocks_bulk(self, min_height, max_height=None):
        """Returns details on the range of blocks between :min_height and :max_height,
        inclusive, up to 10 blocks.

        If :max_height is not specified, it defaults to the current tip.
        """
        if max_height is None:
            min_height = int(min_height)
            api_url = f'{self.api_base_url}v1/blocks-bulk/{min_height}'
        else:
            min_height = int(min_height)
            max_height = int(max_height)
            api_url = f'{self.api_base_url}v1/blocks-bulk/{min_height}/{max_height}'
        return self.__request(api_url)

    def get_mining_pools(self, time_period):
        """Returns a list of all known mining pools ordered by blocks found over the
        specified trailing time_period."""
        api_url = f'{self.api_base_url}v1/mining/pools/{time_period}'
        return self.__request(api_url)

    def get_mining_pool(self, slug):
        """Returns details about the mining pool specified by slug."""
        api_url = f'{self.api_base_url}v1/mining/pool/{slug}'
        return self.__request(api_url)

    def get_mining_pool_hashrates(self, time_period):
        """Returns average hashrates (and share of total hashrate) of mining pools
        active in the specified trailing time_period, in descending order of
        hashrate."""
        api_url = f'{self.api_base_url}v1/mining/hashrate/pools/{time_period}'
        return self.__request(api_url)

    def get_mining_pool_hashrate(self, slug):
        """Returns all known hashrate data for the mining pool specified by slug.

        Hashrate values are weekly averages.
        """
        api_url = f'{self.api_base_url}v1/mining/pool/{slug}/hashrate'
        return self.__request(api_url)

    def get_mining_pool_block(self, slug, block_height=None):
        """Returns past 10 blocks mined by the specified mining pool (slug) before the
        specified block_height.

        If no block_height is specified, the mining pool's 10 most
        recent blocks are returned.
        """
        if block_height is None:
            api_url = f'{self.api_base_url}v1/mining/pool/{slug}/blocks'
        else:
            api_url = f'{self.api_base_url}v1/mining/pool/{slug}/blocks/{block_height}'
        return self.__request(api_url)

    def get_hashrate(self, time_period=None):
        """Returns network-wide hashrate and difficulty figures over the specified
        trailing :timePeriod:"""
        if time_period is None:
            api_url = f'{self.api_base_url}v1/mining/hashrate'
        else:
            api_url = f'{self.api_base_url}v1/mining/hashrate/{time_period}'
        return self.__request(api_url)

    def get_reward_stats(self, block_count):
        """Returns block reward and total transactions confirmed for the past.

        :blockCount blocks.
        """
        api_url = f'{self.api_base_url}v1/mining/reward-stats/{block_count}'
        return self.__request(api_url)

    def get_block_fees(self, time_period):
        """Returns average total fees for blocks in the specified :timePeriod, ordered
        oldest to newest.

        :timePeriod can be any of the following:
        24h, 3d, 1w, 1m, 3m, 6m, 1y, 2y, 3y.
        """
        api_url = f'{self.api_base_url}v1/mining/blocks/fees/{time_period}'
        return self.__request(api_url)

    def get_block_rewards(self, time_period):
        """Returns average block rewards for blocks in the specified :timePeriod,
        ordered oldest to newest.

        :timePeriod can be any of the following:
        24h, 3d, 1w, 1m, 3m, 6m, 1y, 2y, 3y.
        """
        api_url = f'{self.api_base_url}v1/mining/blocks/rewards/{time_period}'
        return self.__request(api_url)

    def get_block_feerates(self, time_period):
        """Returns average feerate percentiles for blocks in the specified.

        :timePeriod, ordered oldest to newest. :timePeriod can be any of
        the following: 24h, 3d, 1w, 1m, 3m, 6m, 1y, 2y, 3y.
        """
        api_url = f'{self.api_base_url}v1/mining/blocks/fee-rates/{time_period}'
        return self.__request(api_url)

    def get_block_sizes_and_weights(self, time_period):
        """Returns average size (bytes) and average weight (weight units) for blocks in
        the specified :timePeriod, ordered oldest to newest.

        :timePeriod can be any of the following:
        24h, 3d, 1w, 1m, 3m, 6m, 1y, 2y, 3y.
        """
        api_url = f'{self.api_base_url}v1/mining/blocks/sizes-weights/{time_period}'
        return self.__request(api_url)

    def get_mempool_blocks_fee(self):
        """Returns current mempool as projected blocks."""
        api_url = f'{self.api_base_url}v1/fees/mempool-blocks'
        return self.__request(api_url)

    def get_recommended_fees(self):
        """Returns our currently suggested fees for new transactions."""
        api_url = f'{self.api_base_url}v1/fees/recommended'
        return self.__request(api_url)

    def get_mempool(self):
        """Returns current mempool backlog statistics."""
        api_url = f'{self.api_base_url}mempool'
        return self.__request(api_url)

    def get_mempool_transactions_ids(self):
        """Get the full list of txids in the mempool as an array."""
        api_url = f'{self.api_base_url}mempool/txids'
        return self.__request(api_url)

    def get_mempool_recent(self):
        """Get a list of the last 10 transactions to enter the mempool."""
        api_url = f'{self.api_base_url}mempool/recent'
        return self.__request(api_url)

    def get_children_pay_for_parents(self, txid):
        """Returns the ancestors and the best descendant fees for a transaction."""
        txid = txid.replace(' ', '')
        api_url = f'{self.api_base_url}v1/cpfp/{txid}'
        return self.__request(api_url)

    def get_transaction(self, txid):
        """Returns details about a transaction."""
        txid = txid.replace(' ', '')
        api_url = f'{self.api_base_url}tx/{txid}'
        return self.__request(api_url)

    def get_transaction_hex(self, txid):
        """Returns a transaction serialized as hex."""
        txid = txid.replace(' ', '')
        api_url = f'{self.api_base_url}tx/{txid}/hex'
        return self.__request(api_url)

    def get_transaction_merkleblock_proof(self, txid):
        """Returns a merkle inclusion proof for the transaction using bitcoind's
        merkleblock format."""
        txid = txid.replace(' ', '')
        api_url = f'{self.api_base_url}tx/{txid}/merkleblock-proof'
        return self.__request(api_url)

    def get_transaction_merkle_proof(self, txid):
        """Returns a merkle inclusion proof for the transaction using Electrum's
        blockchain.transaction.get_merkle format."""
        txid = txid.replace(' ', '')
        api_url = f'{self.api_base_url}tx/{txid}/merkle-proof'
        return self.__request(api_url)

    def get_transaction_outspend(self, txid, vout):
        """Returns the spending status of a transaction output."""
        txid = txid.replace(' ', '')
        vout = vout.replace(' ', '')
        api_url = f'{self.api_base_url}tx/{txid}/outspend/{vout}'
        return self.__request(api_url)

    def get_transaction_outspends(self, txid):
        """Returns the spending status of all transaction outputs."""
        txid = txid.replace(' ', '')
        api_url = f'{self.api_base_url}tx/{txid}/outspends'
        return self.__request(api_url)

    def get_transaction_raw(self, txid):
        """Returns a transaction as binary data."""
        txid = txid.replace(' ', '')
        api_url = f'{self.api_base_url}tx/{txid}/raw'
        return self.__request(api_url)

    def get_transaction_status(self, txid):
        """Returns the confirmation status of a transaction."""
        txid = txid.replace(' ', '')
        api_url = f'{self.api_base_url}tx/{txid}/status'
        return self.__request(api_url)

    def post_transaction(self, txHex):
        """Broadcast a raw transaction to the network."""
        txHex = txHex.replace(' ', '')
        api_url = f'{self.api_base_url}tx'
        return self.__send(api_url, txHex)
