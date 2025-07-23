import datetime
import unittest
from unittest.mock import patch

from pymempool.halving import Halving


class TestHalving(unittest.TestCase):
    def test_initialization_without_difficulty(self):
        """Test initialization without difficulty adjustment data."""
        # Test with current height at beginning of a halving period
        current_height = 840000  # 4th halving just occurred
        halving_info = Halving(current_height)

        # Check basic calculations
        self.assertEqual(halving_info.current_halving, 4)
        self.assertEqual(halving_info.next_halving_height, 1050000)
        self.assertEqual(halving_info.blocks_remaining, 210000)
        self.assertEqual(halving_info.current_reward, 3.125)
        self.assertEqual(halving_info.next_reward, 1.5625)

        # Time estimates should be "Unknown" without difficulty data
        self.assertEqual(halving_info.estimated_date, "Unknown")
        self.assertEqual(halving_info.estimated_days, "Unknown")
        self.assertEqual(halving_info.estimated_time_until, "Unknown")

        # Test with height in middle of a halving period
        current_height = 735000  # In the middle of 3rd halving period
        halving_info = Halving(current_height)

        self.assertEqual(halving_info.current_halving, 3)
        self.assertEqual(halving_info.next_halving_height, 840000)
        self.assertEqual(halving_info.blocks_remaining, 105000)
        self.assertEqual(halving_info.current_reward, 6.25)
        self.assertEqual(halving_info.next_reward, 3.125)

    def test_initialization_with_difficulty(self):
        """Test initialization with difficulty adjustment data."""
        current_height = 735000

        # Mock difficulty adjustment data
        difficulty_adjustment = {
            "progressPercent": 75.6,
            "difficultyChange": 1.5,
            "estimatedRetargetDate": 1625097600000,  # Example timestamp
            "remainingBlocks": 256,
            "remainingTime": 152755,
            "previousRetarget": 1.2,
            "nextRetargetHeight": 736512,
            "timeAvg": 600000,  # 10 minutes in milliseconds (Bitcoin target)
            "timeOffset": 0.1,
            "expectedBlocks": 1050,
        }

        # We need to patch both datetime.datetime.now and the time_until function
        # since mocking datetime has complications with tzinfo
        with (
            patch("pymempool.halving.datetime") as mock_datetime,
            patch("pymempool.halving.time_until") as mock_time_until,
        ):
            # Set up the datetime mock
            mock_now = datetime.datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.datetime.now.return_value = mock_now

            # Set up a future date that would be calculated
            future_date = datetime.datetime(2025, 1, 1, 12, 0, 0)
            mock_datetime.datetime.now.return_value = mock_now
            mock_datetime.timedelta.return_value = datetime.timedelta(days=730)
            mock_datetime.datetime.__add__.return_value = future_date

            # Mock the time_until function to return a predictable string
            mock_time_until.return_value = "730 days 0 hours 0 minutes"

            halving_info = Halving(current_height, difficulty_adjustment)

            # Basic calculations should still work
            self.assertEqual(halving_info.current_halving, 3)
            self.assertEqual(halving_info.next_halving_height, 840000)
            self.assertEqual(halving_info.blocks_remaining, 105000)
            self.assertEqual(halving_info.current_reward, 6.25)
            self.assertEqual(halving_info.next_reward, 3.125)

            # With 10-minute blocks and 105000 blocks remaining
            # Expected days = 105000 * 10 / (60 * 24) = 729.17 days
            # Test should be close to this value (allowing for small rounding diffs)
            self.assertAlmostEqual(halving_info.estimated_days, 729.17, delta=1)

            # Check that the time_until function was called
            mock_time_until.assert_called_once()

    def test_update_method(self):
        """Test the update method refreshes calculations."""
        initial_height = 735000
        halving_info = Halving(initial_height)

        # Initial values
        self.assertEqual(halving_info.current_halving, 3)
        self.assertEqual(halving_info.next_halving_height, 840000)
        self.assertEqual(halving_info.blocks_remaining, 105000)

        # Update with new height
        new_height = 739000
        halving_info.update(new_height)

        # Check updated values
        self.assertEqual(halving_info.current_halving, 3)
        self.assertEqual(halving_info.next_halving_height, 840000)
        self.assertEqual(halving_info.blocks_remaining, 101000)

    def test_constants(self):
        """Test that Bitcoin constants are correctly defined."""
        halving_info = Halving(0)
        self.assertEqual(halving_info.INITIAL_REWARD, 50.0)
        self.assertEqual(halving_info.HALVING_INTERVAL, 210000)
