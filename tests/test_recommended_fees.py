import unittest

from pymempool.recommended_fees import RecommendedFees


def make_recommended_fees_sample():
    """Create sample recommended fees data for testing."""
    return {
        "fastestFee": 10.0,
        "halfHourFee": 5.0,
        "hourFee": 3.0,
        "economy_fee": 2.0,
        "minimumFee": 1.0,
    }


def make_block_fee_data(block_vsize=1000000, median_fee=5.0, n_tx=100):
    """Create sample block fee data for testing."""
    return {
        "blockVSize": block_vsize,
        "medianFee": median_fee,
        "nTx": n_tx,
        "feeRange": [1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0],
    }


def make_mempool_blocks_fee_sample(num_blocks=5):
    """Create sample mempool blocks fee data for testing."""
    blocks = []
    for i in range(num_blocks):
        # Decreasing fees and sizes for subsequent blocks
        block = make_block_fee_data(
            block_vsize=1000000 - i * 100000,
            median_fee=10.0 - i,
            n_tx=100 - i * 10,
        )
        blocks.append(block)
    return blocks


class TestRecommendedFees(unittest.TestCase):
    def setUp(self):
        """Set up for each test."""
        # Default instance without data
        self.fees = RecommendedFees()

    def test_initialization_default(self):
        """Test initialization with default values."""
        # Assert default initialization
        self.assertIsNone(self.fees.mempool_blocks_fee)
        self.assertIsNone(self.fees.hour_fee)
        self.assertIsNone(self.fees.half_hour_fee)
        self.assertIsNone(self.fees.fastest_fee)
        self.assertIsNone(self.fees.economy_fee)
        self.assertEqual(self.fees.minimum_fee, 1.0)
        self.assertEqual(self.fees.default_fee, 1.0)
        self.assertEqual(self.fees.n_fee_blocks, 5)
        self.assertEqual(self.fees.mempool_vsize, 0)
        self.assertEqual(self.fees.mempool_size_mb, 0)
        self.assertEqual(self.fees.mempool_size_gb, 0)
        self.assertEqual(self.fees.mempool_tx_count, 0)
        self.assertEqual(self.fees.mempool_blocks, 0)
        self.assertEqual(self.fees.max_mempool_mb, 300)

    def test_initialization_with_recommended_fees(self):
        """Test initialization with recommended fees data."""
        # Arrange
        recommended_fees = make_recommended_fees_sample()

        # Act
        fees = RecommendedFees(recommended_fees=recommended_fees)

        # Assert
        self.assertEqual(fees.fastest_fee, recommended_fees["fastestFee"])
        self.assertEqual(fees.half_hour_fee, recommended_fees["halfHourFee"])
        self.assertEqual(fees.hour_fee, recommended_fees["hourFee"])
        self.assertEqual(fees.economy_fee, recommended_fees["economy_fee"])
        self.assertEqual(fees.minimum_fee, recommended_fees["minimumFee"])

    def test_initialization_with_mempool_blocks(self):
        """Test initialization with mempool blocks fee data."""
        # Arrange
        mempool_blocks_fee = make_mempool_blocks_fee_sample(3)

        # Act
        fees = RecommendedFees(mempool_blocks_fee=mempool_blocks_fee)

        # Assert
        self.assertEqual(fees.mempool_blocks_fee, mempool_blocks_fee)
        self.assertIsNotNone(fees.fastest_fee)
        self.assertIsNotNone(fees.half_hour_fee)
        self.assertIsNotNone(fees.hour_fee)
        self.assertIsNotNone(fees.economy_fee)
        self.assertGreater(fees.mempool_vsize, 0)
        self.assertGreater(fees.mempool_size_mb, 0)
        self.assertGreater(fees.mempool_tx_count, 0)
        self.assertGreater(fees.mempool_blocks, 0)

    def test_update_recommended_fees_with_none(self):
        """Test updating recommended fees with None."""
        # Act
        self.fees.update_recommended_fees(None)

        # Assert - nothing should change
        self.assertIsNone(self.fees.hour_fee)
        self.assertIsNone(self.fees.half_hour_fee)
        self.assertIsNone(self.fees.fastest_fee)
        self.assertIsNone(self.fees.economy_fee)
        self.assertEqual(self.fees.minimum_fee, 1.0)  # Default value

    def test_update_recommended_fees_with_data(self):
        """Test updating recommended fees with valid data."""
        # Arrange
        recommended_fees = make_recommended_fees_sample()

        # Act
        self.fees.update_recommended_fees(recommended_fees)

        # Assert
        self.assertEqual(self.fees.fastest_fee, recommended_fees["fastestFee"])
        self.assertEqual(self.fees.half_hour_fee, recommended_fees["halfHourFee"])
        self.assertEqual(self.fees.hour_fee, recommended_fees["hourFee"])
        self.assertEqual(self.fees.economy_fee, recommended_fees["economy_fee"])
        self.assertEqual(self.fees.minimum_fee, recommended_fees["minimumFee"])

    def test_update_recommended_fees_partial_data(self):
        """Test updating recommended fees with partial data."""
        # Arrange
        initial_fees = make_recommended_fees_sample()
        self.fees.update_recommended_fees(initial_fees)

        # Only update some fields
        partial_update = {
            "fastestFee": 20.0,
            "minimumFee": 2.0,
        }

        # Act
        self.fees.update_recommended_fees(partial_update)

        # Assert - only specified fields should change
        self.assertEqual(self.fees.fastest_fee, 20.0)
        self.assertEqual(self.fees.half_hour_fee, initial_fees["halfHourFee"])
        self.assertEqual(self.fees.hour_fee, initial_fees["hourFee"])
        self.assertEqual(self.fees.economy_fee, initial_fees["economy_fee"])
        self.assertEqual(self.fees.minimum_fee, 2.0)

    def test_optimize_median_fee_small_block(self):
        """Test optimize_median_fee with a small block."""
        # Arrange
        block = make_block_fee_data(block_vsize=400000, median_fee=8.0)

        # Act
        result = self.fees.optimize_median_fee(block)

        # Assert - for small blocks, return default fee
        self.assertEqual(result, self.fees.default_fee)

    def test_optimize_median_fee_medium_block_no_next(self):
        """Test optimize_median_fee with a medium block and no next block."""
        # Arrange
        block = make_block_fee_data(block_vsize=800000, median_fee=8.0)

        # Act
        result = self.fees.optimize_median_fee(block)

        # Assert - for medium blocks with no next block, use proportional fee
        # Formula: max(use_fee * multiplier, default_fee)
        # multiplier = (blockVSize - 500000) / 500000 = (800000 - 500000) / 500000 = 0.6
        # use_fee = 8.0
        # result = max(8.0 * 0.6, 1.0) = max(4.8, 1.0) = 4.8
        self.assertEqual(result, 4.8)

    def test_optimize_median_fee_medium_block_with_next(self):
        """Test optimize_median_fee with a medium block and next block."""
        # Arrange
        block = make_block_fee_data(block_vsize=800000, median_fee=8.0)
        next_block = make_block_fee_data(block_vsize=700000, median_fee=7.0)

        # Act
        result = self.fees.optimize_median_fee(block, next_block)

        # Assert - with next block, return original median fee
        self.assertEqual(result, 8.0)

    def test_optimize_median_fee_large_block(self):
        """Test optimize_median_fee with a large block."""
        # Arrange
        block = make_block_fee_data(block_vsize=1200000, median_fee=10.0)

        # Act
        result = self.fees.optimize_median_fee(block)

        # Assert - for large blocks, return original median fee
        self.assertEqual(result, 10.0)

    def test_optimize_median_fee_with_previous_fee(self):
        """Test optimize_median_fee with a previous fee."""
        # Arrange
        block = make_block_fee_data(block_vsize=1000000, median_fee=8.0)
        previous_fee = 4.0

        # Act
        result = self.fees.optimize_median_fee(block, previous_fee=previous_fee)

        # Assert - average current with previous
        # (8.0 + 4.0) / 2 = 6.0
        self.assertEqual(result, 6.0)

    def test_update_mempool_blocks_empty(self):
        """Test update_mempool_blocks with empty data."""
        # Act with None
        result_none = self.fees.update_mempool_blocks(None)
        # Act with empty list
        result_empty = self.fees.update_mempool_blocks([])

        # Assert
        self.assertFalse(result_none)
        self.assertFalse(result_empty)
        self.assertIsNone(self.fees.mempool_blocks_fee)
        self.assertEqual(self.fees.mempool_vsize, 0)
        self.assertEqual(self.fees.mempool_tx_count, 0)

    def test_update_mempool_blocks_single_block(self):
        """Test update_mempool_blocks with a single block."""
        # Arrange
        blocks = [make_block_fee_data(block_vsize=800000, median_fee=5.0, n_tx=100)]

        # Act
        result = self.fees.update_mempool_blocks(blocks)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.fees.mempool_blocks_fee, blocks)
        self.assertEqual(self.fees.mempool_vsize, 800000)
        self.assertEqual(self.fees.mempool_tx_count, 100)
        self.assertEqual(self.fees.mempool_blocks, 1)
        # Verify fee calculations based on the single block
        self.assertIsNotNone(self.fees.fastest_fee)
        self.assertIsNotNone(self.fees.half_hour_fee)
        self.assertIsNotNone(self.fees.hour_fee)

    def test_update_mempool_blocks_multiple_blocks(self):
        """Test update_mempool_blocks with multiple blocks."""
        # Arrange
        blocks = make_mempool_blocks_fee_sample(3)

        # Act
        result = self.fees.update_mempool_blocks(blocks)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.fees.mempool_blocks_fee, blocks)
        # Verify fee calculations with multiple blocks
        # Fastest fee should be max of first block median fee and minimum fee
        # Half hour fee should be derived from second block
        # Hour fee should be derived from third block
        self.assertIsNotNone(self.fees.fastest_fee)
        self.assertIsNotNone(self.fees.half_hour_fee)
        self.assertIsNotNone(self.fees.hour_fee)

        # Total vsize, tx count, and blocks should be calculated from all blocks
        expected_vsize = sum(block["blockVSize"] for block in blocks)
        expected_tx_count = sum(block["nTx"] for block in blocks)
        self.assertEqual(self.fees.mempool_vsize, expected_vsize)
        self.assertEqual(self.fees.mempool_tx_count, expected_tx_count)
        self.assertEqual(self.fees.mempool_blocks, expected_vsize // 1000000 + 1)

    def test_fee_calculations_from_update(self):
        """Test that fees are calculated correctly after update."""
        # Arrange - create blocks where we know the expected output
        blocks = [
            # First block: Small block size = default fee
            make_block_fee_data(block_vsize=400000, median_fee=10.0, n_tx=100),
            # Second block: Median fee = 8.0
            make_block_fee_data(block_vsize=1000000, median_fee=8.0, n_tx=100),
            # Third block: Median fee = 6.0
            make_block_fee_data(block_vsize=1000000, median_fee=6.0, n_tx=100),
        ]

        # Act
        self.fees.update_mempool_blocks(blocks)

        # Assert - verify that each fee is set correctly
        # Minimum fee should be minimum of first block fee range
        self.assertEqual(self.fees.minimum_fee, 1.0)

        # Fees should follow the principle of monotonically decreasing
        # with confirmation time
        self.assertGreaterEqual(self.fees.fastest_fee, self.fees.half_hour_fee)
        self.assertGreaterEqual(self.fees.half_hour_fee, self.fees.hour_fee)
        self.assertGreaterEqual(self.fees.hour_fee, self.fees.economy_fee)

        # Economy fee should be at most twice the minimum fee,
        # but at least the minimum fee
        self.assertGreaterEqual(self.fees.economy_fee, self.fees.minimum_fee)
        self.assertLessEqual(self.fees.economy_fee, 2 * self.fees.minimum_fee)

    def test_build_fee_array_no_data(self):
        """Test build_fee_array with no mempool data."""
        # Act
        min_fees, median_fees, max_fees = self.fees.build_fee_array()

        # Assert
        # Should return arrays of default fees for each block
        self.assertEqual(len(min_fees), self.fees.n_fee_blocks)
        self.assertEqual(len(median_fees), self.fees.n_fee_blocks)
        self.assertEqual(len(max_fees), self.fees.n_fee_blocks)

        # All fees should be the default fee
        for fee in min_fees + median_fees + max_fees:
            self.assertEqual(fee, self.fees.default_fee)

    def test_build_fee_array_with_data(self):
        """Test build_fee_array with mempool data."""
        # Arrange
        blocks = make_mempool_blocks_fee_sample(3)
        self.fees.update_mempool_blocks(blocks)

        # Act
        min_fees, median_fees, max_fees = self.fees.build_fee_array()

        # Assert
        # Should return arrays with fee data for each block
        self.assertEqual(len(min_fees), self.fees.n_fee_blocks)
        self.assertEqual(len(median_fees), self.fees.n_fee_blocks)
        self.assertEqual(len(max_fees), self.fees.n_fee_blocks)

        # First 3 elements should match the block data
        for i in range(3):
            self.assertEqual(min_fees[i], blocks[i]["feeRange"][0])
            self.assertEqual(max_fees[i], blocks[i]["feeRange"][-1])
            # Median calculated via utility function
            from pymempool.utils import median

            self.assertEqual(median_fees[i], median(blocks[i]["feeRange"]))

        # Last 2 elements should use data from the last block
        for i in range(3, self.fees.n_fee_blocks):
            self.assertEqual(min_fees[i], blocks[-1]["feeRange"][0])
            self.assertEqual(max_fees[i], blocks[-1]["feeRange"][-1])
            from pymempool.utils import median

            self.assertEqual(median_fees[i], median(blocks[-1]["feeRange"]))

    def test_fee_array_reflects_updated_data(self):
        """Test that build_fee_array reflects newly updated data."""
        # Arrange
        initial_blocks = make_mempool_blocks_fee_sample(2)
        self.fees.update_mempool_blocks(initial_blocks)

        # Get initial fee arrays
        initial_min, initial_median, initial_max = self.fees.build_fee_array()

        # Update with new data
        new_blocks = [
            make_block_fee_data(block_vsize=1000000, median_fee=20.0, n_tx=200),
            make_block_fee_data(block_vsize=900000, median_fee=15.0, n_tx=150),
        ]
        new_blocks[0]["feeRange"] = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
        new_blocks[1]["feeRange"] = [2.0, 5.0, 10.0, 15.0, 20.0, 25.0]

        self.fees.update_mempool_blocks(new_blocks)

        # Act
        new_min, new_median, new_max = self.fees.build_fee_array()

        # Assert
        # Arrays should be different after update
        self.assertNotEqual(initial_min, new_min)
        self.assertNotEqual(initial_median, new_median)
        self.assertNotEqual(initial_max, new_max)

        # Values should match the new blocks
        self.assertEqual(new_min[0], 5.0)
        self.assertEqual(new_min[1], 2.0)
        self.assertEqual(new_max[0], 30.0)
        self.assertEqual(new_max[1], 25.0)


if __name__ == "__main__":
    unittest.main()
