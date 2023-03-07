import unittest

from pymempool import MempoolAPI


class TestAddresses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.address = "1wiz18xYmhRX6xStj2b9t1rwWX4GKUgpv"

    def test_address(self):
        api = MempoolAPI()

        ret = api.get_address(self.address)
        self.assertIsInstance(ret, dict)

    def test_address_transactions(self):
        api = MempoolAPI()

        ret = api.get_address_transactions(self.address)
        self.assertIsInstance(ret, list)

    def test_address_transactions_chain(self):
        api = MempoolAPI()

        ret = api.get_address_transactions_chain(self.address)
        self.assertIsInstance(ret, list)

    def test_address_transactions_mempool(self):
        api = MempoolAPI()

        ret = api.get_address_transactions_mempool(self.address)
        self.assertIsInstance(ret, list)

    def test_address_transactions_utxo(self):
        api = MempoolAPI()

        ret = api.get_address_utxo(self.address)
        self.assertIsInstance(ret, list)
