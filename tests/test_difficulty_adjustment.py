import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from pymempool.difficulty_adjustment import DifficultyAdjustment

time_until_patch_value = "5 days 0 hours 0 minutes"


def fake_time_until(dt, short=False):
    return time_until_patch_value


def make_sample_data(now=None):
    if now is None:
        now = datetime.now()
    return {
        "remainingBlocks": 100,
        "estimatedRetargetDate": int((now + timedelta(days=5)).timestamp() * 1000),
        "expectedBlocks": 1916,
        "timeAvg": 600000,  # 10 minutes in ms
    }


class TestDifficultyAdjustment(unittest.TestCase):
    def test_initialization_typical(self):
        lastblocknum = 300000
        data = make_sample_data()
        with patch("pymempool.difficulty_adjustment.time_until", fake_time_until):
            adj = DifficultyAdjustment(lastblocknum, data)
            self.assertEqual(adj.lastblocknum, lastblocknum)
            self.assertEqual(adj.difficulty_adjustment, data)
            self.assertEqual(
                adj.last_retarget, lastblocknum - 2016 + data["remainingBlocks"]
            )
            self.assertEqual(adj.found_blocks, lastblocknum - adj.last_retarget)
            self.assertEqual(
                adj.blocks_behind, data["expectedBlocks"] - adj.found_blocks
            )
            self.assertEqual(adj.minutes_between_blocks, data["timeAvg"] / 60000)
            self.assertEqual(adj.estimated_retarget_period, time_until_patch_value)
            self.assertIsInstance(adj.estimated_retarget_date, datetime)

    def test_update_with_missing_keys(self):
        lastblocknum = 300000
        data = {}  # All keys missing
        with patch("pymempool.difficulty_adjustment.time_until", fake_time_until):
            adj = DifficultyAdjustment(lastblocknum, data)
            self.assertEqual(adj.lastblocknum, lastblocknum)
            self.assertEqual(adj.difficulty_adjustment, data)
            self.assertEqual(adj.last_retarget, lastblocknum - 2016)
            self.assertEqual(adj.found_blocks, lastblocknum - adj.last_retarget)
            self.assertEqual(adj.blocks_behind, 0 - adj.found_blocks)
            self.assertEqual(adj.minutes_between_blocks, 600000 / 60000)
            self.assertIsNone(adj.estimated_retarget_date)
            self.assertEqual(adj.estimated_retarget_period, "Unknown")

    def test_update_with_none_estimatedRetargetDate(self):
        lastblocknum = 300000
        data = make_sample_data()
        data["estimatedRetargetDate"] = None  # type: ignore
        with patch("pymempool.difficulty_adjustment.time_until", fake_time_until):
            adj = DifficultyAdjustment(lastblocknum, data)
            self.assertIsNone(adj.estimated_retarget_date)
            self.assertEqual(adj.estimated_retarget_period, "Unknown")

    def test_update_method(self):
        lastblocknum = 300000
        data1 = make_sample_data()
        data2 = make_sample_data(now=datetime.now() + timedelta(days=1))
        with patch("pymempool.difficulty_adjustment.time_until", fake_time_until):
            adj = DifficultyAdjustment(lastblocknum, data1)
            # Update with new data
            adj.update_difficulty_adjustment(lastblocknum + 10, data2)
            self.assertEqual(adj.lastblocknum, lastblocknum + 10)
            self.assertEqual(adj.difficulty_adjustment, data2)
            self.assertEqual(adj.estimated_retarget_period, time_until_patch_value)

    def test_negative_remaining_blocks(self):
        lastblocknum = 300000
        for remainingBlocks in [-10, 0, 100]:
            with self.subTest(remainingBlocks=remainingBlocks):
                data = make_sample_data()
                data["remainingBlocks"] = remainingBlocks
                with patch(
                    "pymempool.difficulty_adjustment.time_until", fake_time_until
                ):
                    adj = DifficultyAdjustment(lastblocknum, data)
                    self.assertEqual(
                        adj.last_retarget, lastblocknum - 2016 + remainingBlocks
                    )
                    self.assertEqual(adj.found_blocks, lastblocknum - adj.last_retarget)


if __name__ == "__main__":
    unittest.main()
