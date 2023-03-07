import unittest

from pymempool import MempoolAPI


class TestGeneral(unittest.TestCase):
    def test_difficulty(self):
        api = MempoolAPI()
        ret = api.get_difficulty_adjustment()
        self.assertTrue(len(ret) > 0)
