import unittest

from pymempool import MempoolAPI


class TestBlocks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hash = "000000000000000015dc777b3ff2611091336355d3f0ee9766a2cf3be8e4b1ce"
        cls.index = "216"
        cls.height = "363366"

    def test_block(self):
        api = MempoolAPI()

        ret = api.get_block(self.hash)
        self.assertIsInstance(ret, dict)
        self.assertEqual(ret["height"], int(self.height))

    def test_block_header(self):
        api = MempoolAPI()

        ret = api.get_block_header(self.hash)
        self.assertIsInstance(ret, str)

    def test_block_height(self):
        api = MempoolAPI()

        ret = api.get_block_height(self.height)
        self.assertIsInstance(ret, str)
        self.assertEqual(ret, self.hash)

    def test_block_raw(self):
        api = MempoolAPI()

        ret = api.get_block_raw(self.hash)
        self.assertIsInstance(ret, bytes)

    def test_block_status(self):
        api = MempoolAPI()

        ret = api.get_block_status(self.hash)
        self.assertIsInstance(ret, dict)
        self.assertEqual(ret["height"], int(self.height))

    def test_block_tip_height(self):
        api = MempoolAPI()

        ret = api.get_block_tip_height()
        self.assertIsInstance(ret, int)

    def test_block_tip_hash(self):
        api = MempoolAPI()

        ret = api.get_block_tip_hash()
        self.assertIsInstance(ret, str)

    def test_block_transaction_id(self):
        api = MempoolAPI()

        ret = api.get_block_transaction_id(self.hash, self.index)
        self.assertIsInstance(ret, str)

    def test_block_transaction_ids(self):
        api = MempoolAPI()

        ret = api.get_block_transaction_ids(self.hash)
        self.assertIsInstance(ret, list)

    def test_block_transactions(self):
        api = MempoolAPI()

        ret = api.get_block_transactions(self.hash)
        self.assertIsInstance(ret, list)

    def test_blocks(self):
        api = MempoolAPI()

        ret = api.get_blocks(self.height)
        self.assertIsInstance(ret, list)

    # def test_blocks_bulk(self):
    #    api = MempoolAPI()
    #
    #    ret = api.get_blocks_bulk(self.height, self.height)
    #    self.assertIsInstance(ret, list)
