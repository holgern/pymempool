import json
import unittest

from pymempool.block_parser import BlockParser


class TestBlockParser(unittest.TestCase):
    def setUp(self):
        self.test_json = json.dumps(
            [
                {
                    "id": (
                        "0000000000000000000384f28cb3b9cf4377a39cfd6c29ae9466951de38c0529"
                    ),
                    "height": 730000,
                    "version": 536870912,
                    "timestamp": 1648829449,
                    "tx_count": 1627,
                    "size": 1210916,
                    "weight": 3993515,
                    "merkle_root": (
                        "efa344bcd6c0607f93b709515dd6dc5496178112d680338ebea459e3de7b4fbc"
                    ),
                    "previousblockhash": (
                        "00000000000000000008b6f6fb83f8d74512ef1e0af29e642dd20daddd7d318f"
                    ),
                    "mediantime": 1648827418,
                    "nonce": 3580664066,
                    "bits": 386521239,
                    "difficulty": 28587155782195.14,
                }
            ]
        )
        self.parser = BlockParser(self.test_json)

    def test_initialization(self):
        # Test initialization with JSON string
        parser1 = BlockParser(self.test_json)
        self.assertEqual(len(parser1), 1)

        # Test initialization with parsed list
        parsed_data = json.loads(self.test_json)
        parser2 = BlockParser(parsed_data)
        self.assertEqual(len(parser2), 1)

        # Test initialization with invalid input
        with self.assertRaises(ValueError):
            BlockParser(123)

    def test_parse_block(self):
        block = self.parser[0]

        # Test basic block properties
        self.assertEqual(block["height"], 730000)
        self.assertEqual(
            block["id"],
            "0000000000000000000384f28cb3b9cf4377a39cfd6c29ae9466951de38c0529",
        )
        self.assertEqual(block["tx_count"], 1627)

        # Test calculated properties
        self.assertAlmostEqual(block["size_mb"], 1.21, places=2)
        self.assertAlmostEqual(block["weight_mwu"], 3.99, places=2)
        self.assertAlmostEqual(block["vsize"], 998378.75, places=2)

        # Test formatted date - note that this may vary by timezone
        self.assertTrue(block["formatted_date"].startswith("2022-04-01"))

    def test_len_and_getitem(self):
        self.assertEqual(len(self.parser), 1)
        self.assertIsInstance(self.parser[0], dict)

    def test_formatted_lines(self):
        lines = self.parser.formatted_lines(0)
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], "Block #730000")
        self.assertTrue(lines[2].startswith("2022-04-01"))
        self.assertEqual(lines[3], "1627 transactions")

    def test_all_formatted_lines(self):
        all_lines = self.parser.all_formatted_lines()
        self.assertEqual(len(all_lines), 1)
        self.assertEqual(len(all_lines[0]), 7)


if __name__ == "__main__":
    unittest.main()
