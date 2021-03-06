import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import warnings


class MempoolAPI():
    __API_URL_BASE = "https://mempool.space/api/"
    def __init__(self, api_base_url=__API_URL_BASE, retries=5, request_verify=True, proxies=None):
        self.api_base_url = api_base_url
        self.proxies = proxies
        self.request_timeout = 120
        self.request_verify = request_verify
        if not request_verify:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        self.session = requests.Session()
        retries = Retry(total=retries, backoff_factor=0.5, status_forcelist=[502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def __request(self, url):
        # print(url)
        try:
            response = self.session.get(url, timeout=self.request_timeout, verify=self.request_verify, proxies=self.proxies)
        except requests.exceptions.RequestException:
            raise

        try:
            response.raise_for_status()
            content = json.loads(response.content.decode('utf-8'))
            return content
        except Exception as e:
            # check if json (with error message) is returned
            try:
                content = json.loads(response.content.decode('utf-8'))
                raise ValueError(content)
            # if no json
            except json.decoder.JSONDecodeError:
                pass
            raise

    def __send(self, url, data):
        # print(url)
        try:
            req = requests.Request('POST',  url, data=data)
            prepped = req.prepare()
            response = self.session.send(prepped, timeout=self.request_timeout, verify=self.request_verify)
        except requests.exceptions.RequestException:
            raise

        try:
            response.raise_for_status()
            content = response.content.decode('utf-8')
            return content
        except Exception as e:
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
        api_url = '{0}v1/difficulty-adjustment'.format(self.api_base_url)
        return self.__request(api_url)

    def get_address(self, address):
        """Returns details about an address."""
        address = address.replace(' ', '')
        api_url = '{0}address/{1}'.format(self.api_base_url, address)
        return self.__request(api_url)

    def get_address_transactions(self, address):
        """Get transaction history for the specified address/scripthash, sorted with newest first."""
        address = address.replace(' ', '')
        api_url = '{0}address/{1}/txs'.format(self.api_base_url, address)
        return self.__request(api_url)

    def get_address_transactions_chain(self, address, last_seen_txid=None):
        """Get confirmed transaction history for the specified address/scripthash, sorted with newest first. """
        address = address.replace(' ', '')
        if last_seen_txid is None:
            api_url = '{0}address/{1}/txs/chain'.format(self.api_base_url, address)
        else:
            api_url = '{0}address/{1}/txs/chain/{2}'.format(self.api_base_url, address, last_seen_txid)
        return self.__request(api_url)

    def get_address_transactions_mempool(self, address):
        """Get unconfirmed transaction history for the specified address/scripthash."""
        address = address.replace(' ', '')
        api_url = '{0}address/{1}/txs/mempool'.format(self.api_base_url, address)
        return self.__request(api_url)

    def get_address_utxo(self, address):
        """Get the list of unspent transaction outputs associated with the address/scripthash."""
        address = address.replace(' ', '')
        api_url = '{0}address/{1}/utxo'.format(self.api_base_url, address)
        return self.__request(api_url)

    def get_block(self, hash_value):
        """Returns details about a block."""
        hash_value = hash_value.replace(' ','')
        api_url = '{0}block/{1}'.format(self.api_base_url, hash_value)
        return self.__request(api_url)

    def get_block_header(self, hash_value):
        """Returns the hex-encoded block header."""
        hash_value = hash_value.replace(' ','')
        api_url = '{0}block/{1}/header'.format(self.api_base_url, hash_value)
        return self.__request(api_url)

    def get_block_height(self, height):
        """Returns the hash of the block currently at height."""
        height = int(height)
        api_url = '{0}block-height/{1}'.format(self.api_base_url, height)
        return self.__request(api_url)

    def get_block_raw(self, hash_value):
        """Returns the raw block representation in binary."""
        hash_value = hash_value.replace(' ','')
        api_url = '{0}block/{1}/raw'.format(self.api_base_url, hash_value)
        return self.__request(api_url)

    def get_block_status(self, hash_value):
        """Returns the confirmation status of a block."""
        hash_value = hash_value.replace(' ','')
        api_url = '{0}block/{1}/status'.format(self.api_base_url, hash_value)
        return self.__request(api_url)

    def get_block_tip_height(self):
        """Returns the height of the last block."""
        api_url = '{0}blocks/tip/height'.format(self.api_base_url)
        return self.__request(api_url)

    def get_block_tip_hash(self):
        """Returns the hash of the last block."""
        api_url = '{0}blocks/tip/hash'.format(self.api_base_url)
        return self.__request(api_url)

    def get_block_transaction_id(self, hash_value, index):
        """Returns the transaction at index index within the specified block."""
        hash_value = hash_value.replace(' ','')
        index = int(index)
        api_url = '{0}block/{1}/txid/{2}'.format(self.api_base_url, hash_value, index)
        return self.__request(api_url)

    def get_block_transaction_ids(self, hash_value):
        """Returns a list of all txids in the block."""
        hash_value = hash_value.replace(' ','')
        api_url = '{0}block/{1}/txids'.format(self.api_base_url, hash_value)
        return self.__request(api_url)

    def get_block_transactions(self, hash_value, start_index=None):
        """Returns a list of transactions in the block (up to 25 transactions beginning at start_index). """
        hash_value = hash_value.replace(' ','')
        if start_index is not None:
            start_index = int(start_index)
            api_url = '{0}block/{1}/txs/{2}'.format(self.api_base_url, hash_value, start_index)
        else:
            api_url = '{0}block/{1}/txs'.format(self.api_base_url, hash_value)
        return self.__request(api_url)

    def get_blocks(self, start_height=None):
        """Returns the 10 newest blocks starting at the tip or at :start_height if specified."""
        if start_height is None:
            api_url = '{0}blocks'.format(self.api_base_url)
        else:
            start_height = int(start_height)
            api_url = '{0}blocks/{1}'.format(self.api_base_url, start_height)
        return self.__request(api_url)

    def get_mempool_blocks_fee(self):
        """Returns current mempool as projected blocks."""
        api_url = '{0}v1/fees/mempool-blocks'.format(self.api_base_url)
        return self.__request(api_url)

    def get_recommended_fees(self):
        """Returns our currently suggested fees for new transactions."""
        api_url = '{0}v1/fees/recommended'.format(self.api_base_url)
        return self.__request(api_url)

    def get_mempool(self):
        """Returns current mempool backlog statistics."""
        api_url = '{0}mempool'.format(self.api_base_url)
        return self.__request(api_url)

    def get_mempool_transactions_ids(self):
        """Get the full list of txids in the mempool as an array."""
        api_url = '{0}mempool/txids'.format(self.api_base_url)
        return self.__request(api_url)

    def get_mempool_recent(self):
        """Get a list of the last 10 transactions to enter the mempool."""
        api_url = '{0}mempool/recent'.format(self.api_base_url)
        return self.__request(api_url)

    def get_children_pay_for_parents(self, txid):
        """Returns the ancestors and the best descendant fees for a transaction."""
        txid = txid.replace(' ','')
        api_url = '{0}v1/cpfp/{1}'.format(self.api_base_url, txid)
        return self.__request(api_url)
    
    def get_transaction(self, txid):
        """Returns details about a transaction."""
        txid = txid.replace(' ','')
        api_url = '{0}tx/{1}'.format(self.api_base_url, txid)
        return self.__request(api_url)
    
    def get_transaction_hex(self, txid):
        """Returns a transaction serialized as hex."""
        txid = txid.replace(' ','')
        api_url = '{0}tx/{1}/hex'.format(self.api_base_url, txid)
        return self.__request(api_url)
    
    def get_transaction_merkleblock_proof(self, txid):
        """Returns a merkle inclusion proof for the transaction using bitcoind's merkleblock format."""
        txid = txid.replace(' ','')
        api_url = '{0}tx/{1}/merkleblock-proof'.format(self.api_base_url, txid)
        return self.__request(api_url)
    
    def get_transaction_merkle_proof(self, txid):
        """Returns a merkle inclusion proof for the transaction using Electrum's blockchain.transaction.get_merkle format."""
        txid = txid.replace(' ','')
        api_url = '{0}tx/{1}/merkle-proof'.format(self.api_base_url, txid)
        return self.__request(api_url)
    
    def get_transaction_outspend(self, txid, vout):
        """Returns the spending status of a transaction output."""
        txid = txid.replace(' ','')
        vout = vout.replace(' ','')
        api_url = '{0}tx/{1}/outspend/{2}'.format(self.api_base_url, txid, vout)
        return self.__request(api_url)
    
    def get_transaction_outspends(self, txid):
        """Returns the spending status of all transaction outputs."""
        txid = txid.replace(' ','')
        api_url = '{0}tx/{1}/outspends'.format(self.api_base_url, txid)
        return self.__request(api_url)

    def get_transaction_raw(self, txid):
        """Returns a transaction as binary data."""
        txid = txid.replace(' ','')
        api_url = '{0}tx/{1}/raw'.format(self.api_base_url, txid)
        return self.__request(api_url)

    def get_transaction_status(self, txid):
        """Returns the confirmation status of a transaction."""
        txid = txid.replace(' ','')
        api_url = '{0}tx/{1}/status'.format(self.api_base_url, txid)
        return self.__request(api_url)

    def post_transaction(self, txHex):
        """Broadcast a raw transaction to the network."""
        txHex = txHex.replace(' ','')
        api_url = '{0}tx'.format(self.api_base_url)
        return self.__send(api_url, txHex)
