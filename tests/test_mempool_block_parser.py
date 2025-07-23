import json
import unittest

from pymempool.mempool_block_parser import MempoolBlockParser


class TestMempoolBlockParser(unittest.TestCase):
    def setUp(self):
        self.test_json = json.dumps(
            [
                {
                    "blockSize": 1000000,
                    "blockVSize": 998000,
                    "nTx": 2500,
                    "totalFees": 12500000,  # 0.125 BTC in sats
                    "medianFee": 8.5,
                    "feeRange": [1.0, 3.5, 5.0, 7.8, 8.5, 10.2, 15.0, 25.0],
                },
                {
                    "blockSize": 800000,
                    "blockVSize": 795000,
                    "nTx": 1800,
                    "totalFees": 9000000,  # 0.09 BTC in sats
                    "medianFee": 6.5,
                    "feeRange": [1.2, 2.5, 4.0, 6.0, 6.5, 8.2, 12.0, 20.0],
                },
            ]
        )
        self.parser = MempoolBlockParser(self.test_json)

    def test_initialization(self):
        # Test initialization with JSON string
        parser1 = MempoolBlockParser(self.test_json)
        self.assertEqual(len(parser1), 2)

        # Test initialization with parsed list
        parsed_data = json.loads(self.test_json)
        parser2 = MempoolBlockParser(parsed_data)
        self.assertEqual(len(parser2), 2)

        # Test initialization with invalid input
        with self.assertRaises(ValueError):
            MempoolBlockParser(123)

    def test_parse_block(self):
        block = self.parser[0]

        # Test basic block properties
        self.assertEqual(block["nTx"], 2500)
        self.assertEqual(block["min_fee"], 1.0)
        self.assertEqual(block["max_fee"], 25.0)
        self.assertEqual(block["median_fee"], 8.5)

        # Test calculated properties
        self.assertEqual(block["total_btc"], 0.125)
        self.assertEqual(block["block_size_mb"], 1.0)

        # Test fee range
        self.assertEqual(len(block["fee_range"]), 8)
        self.assertEqual(
            block["fee_range"], [1.0, 3.5, 5.0, 7.8, 8.5, 10.2, 15.0, 25.0]
        )

    def test_len_and_getitem(self):
        self.assertEqual(len(self.parser), 2)
        self.assertIsInstance(self.parser[0], dict)
        self.assertIsInstance(self.parser[1], dict)

    def test_formatted_lines(self):
        lines = self.parser.formatted_lines(0)
        self.assertEqual(len(lines), 6)
        self.assertEqual(lines[0], "25.00-1.00 sat/vB")
        self.assertEqual(lines[2], "Median: 8.50")
        self.assertEqual(lines[3], "2500 TX")
        self.assertEqual(lines[4], "0.125 BTC")
        self.assertEqual(lines[5], "1.0 MB")

    def test_all_formatted_lines(self):
        all_lines = self.parser.all_formatted_lines()
        self.assertEqual(len(all_lines), 2)
        self.assertEqual(len(all_lines[0]), 6)
        self.assertEqual(len(all_lines[1]), 6)

        # Test second block's formatted lines
        second_block_lines = all_lines[1]
        self.assertEqual(second_block_lines[0], "20.00-1.20 sat/vB")
        self.assertEqual(second_block_lines[2], "Median: 6.50")
        self.assertEqual(second_block_lines[3], "1800 TX")
        self.assertEqual(second_block_lines[4], "0.09 BTC")
        self.assertEqual(second_block_lines[5], "0.8 MB")


if __name__ == "__main__":
    unittest.main()
