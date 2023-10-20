import unittest

from pymempool import MempoolAPI


class TestMining(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.time_period = "1w"
        cls.slug = "antpool"

    def test_mining_pools(self):
        api = MempoolAPI()

        ret = api.get_mining_pools(self.time_period)
        self.assertIsInstance(ret, dict)

    def test_mining_pool(self):
        api = MempoolAPI()

        ret = api.get_mining_pool(self.slug)
        self.assertIsInstance(ret, dict)

    def test_mining_pool_hashrates(self):
        api = MempoolAPI()
        ret = api.get_mining_pool_hashrates(self.time_period)
        self.assertIsInstance(ret, list)

    def test_mining_pool_hashrate(self):
        api = MempoolAPI()
        ret = api.get_mining_pool_hashrate(self.slug)
        self.assertIsInstance(ret, list)

    def test_mining_pool_block(self):
        api = MempoolAPI()
        ret = api.get_mining_pool_block(self.slug)
        self.assertIsInstance(ret, list)

    def test_hashrate(self):
        api = MempoolAPI()
        ret = api.get_hashrate(self.time_period)
        self.assertIsInstance(ret, dict)
