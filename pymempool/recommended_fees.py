"""
This module provides the RecommendedFees class for calculating and updating
Bitcoin transaction fee recommendations based on mempool and block data.
"""

import math
from typing import Optional

from .utils import median

# Constants for fee calculations
DEFAULT_FEE = 1.0
MAX_MEMPOOL_MB = 300
SMALL_BLOCK_SIZE = 500000
MEDIUM_BLOCK_SIZE = 950000
MEMPOOL_SIZE_MULTIPLIER = 3.99
BLOCK_SIZE_DIVISOR = 1e6
KB_TO_MB = 1024 * 1024
KB_TO_GB = 1024 * 1024 * 1024
DEFAULT_FEE_BLOCKS = 5


class RecommendedFees:
    """
    Handles recommended Bitcoin transaction fees based on mempool and block data.

    This class provides methods to update and calculate recommended fees for different
    confirmation times (fastest, half-hour, hour, economy) using mempool statistics
    and block fee data.
    """

    def __init__(
        self,
        recommended_fees: Optional[dict] = None,
        mempool_blocks_fee: Optional[list] = None,
    ):
        """
        Initialize RecommendedFees with optional recommended fee and mempool block data.

        Args:
            recommended_fees (dict, optional): Dictionary with recommended fee values.
            mempool_blocks_fee (list, optional): List of mempool block fee data dicts.
        """
        self.mempool_blocks_fee: Optional[list] = None
        self.hour_fee: Optional[float] = None
        self.half_hour_fee: Optional[float] = None
        self.fastest_fee: Optional[float] = None
        self.economy_fee: Optional[float] = None
        self.minimum_fee: float = DEFAULT_FEE
        self.default_fee: float = DEFAULT_FEE
        self.n_fee_blocks: int = DEFAULT_FEE_BLOCKS
        self.mempool_vsize: int = 0
        self.mempool_size_mb: float = 0
        self.mempool_size_gb: float = 0
        self.mempool_tx_count: int = 0
        self.mempool_blocks: int = 0
        self.max_mempool_mb: int = MAX_MEMPOOL_MB
        self.update_recommended_fees(recommended_fees)
        self.update_mempool_blocks(mempool_blocks_fee)

    def update_recommended_fees(self, recommended_fees: Optional[dict]) -> None:
        """
        Update the recommended fee values from a provided dictionary.

        Args:
            recommended_fees (dict): Dictionary containing fee recommendations.
                Keys may include 'hourFee', 'halfHourFee', 'fastestFee',
                'economy_fee', and 'minimumFee'.
        """
        if not recommended_fees:
            return

        self.hour_fee = recommended_fees.get("hourFee", self.hour_fee)
        self.half_hour_fee = recommended_fees.get("halfHourFee", self.half_hour_fee)
        self.fastest_fee = recommended_fees.get("fastestFee", self.fastest_fee)
        self.economy_fee = recommended_fees.get("economy_fee", self.economy_fee)
        self.minimum_fee = recommended_fees.get("minimumFee", self.minimum_fee)

    def optimize_median_fee(
        self,
        p_block: dict,
        next_block: Optional[dict] = None,
        previous_fee: Optional[float] = None,
    ) -> float:
        """
        Calculate an optimized median fee for a mempool block.

        Args:
            p_block (dict): Block data containing 'medianFee' and 'blockVSize'.
            next_block (dict, optional): Next block's data for context (default: None).
            previous_fee (float, optional): Previous block's optimized fee
                (default: None).

        Returns:
            float: Optimized median fee for the block.
        """
        # Calculate base fee using previous fee if available
        use_fee = (
            (p_block["medianFee"] + previous_fee) / 2
            if previous_fee is not None
            else p_block["medianFee"]
        )

        # For small blocks, return default fee
        block_vsize = p_block["blockVSize"]
        if block_vsize <= SMALL_BLOCK_SIZE:
            return self.default_fee

        # For medium blocks with no next block, use proportional multiplier
        elif block_vsize <= MEDIUM_BLOCK_SIZE and next_block is None:
            multiplier = (block_vsize - SMALL_BLOCK_SIZE) / SMALL_BLOCK_SIZE
            return max(use_fee * multiplier, self.default_fee)

        # Otherwise use the calculated fee
        return use_fee

    def _calculate_mempool_stats(
        self, mempool_blocks_fee: list
    ) -> tuple[int, int, float]:
        """
        Calculate mempool statistics from block data.

        Args:
            mempool_blocks_fee: List of mempool block fee data

        Returns:
            Tuple of (total_vsize, transaction_count, minimum_fee)
        """
        vsize = 0
        count = 0
        minimum_fee = 0.0

        for block in mempool_blocks_fee:
            vsize += block["blockVSize"]
            count += block["nTx"]
            if vsize / KB_TO_MB * MEMPOOL_SIZE_MULTIPLIER < self.max_mempool_mb:
                minimum_fee = block["feeRange"][0]

        # Ensure minimum fee is at least the default fee
        minimum_fee = float(max(minimum_fee, self.default_fee))

        return vsize, count, minimum_fee

    def _calculate_median_fees(
        self, mempool_blocks_fee: list
    ) -> tuple[float, float, float]:
        """
        Calculate optimized median fees for different confirmation targets.

        Args:
            mempool_blocks_fee: List of mempool block fee data

        Returns:
            Tuple of (first_median_fee, second_median_fee, third_median_fee)
        """
        # Calculate first median fee (fastest, next block)
        if len(mempool_blocks_fee) == 1:
            first_median_fee = self.optimize_median_fee(mempool_blocks_fee[0])
        elif len(mempool_blocks_fee) > 1:
            first_median_fee = self.optimize_median_fee(
                mempool_blocks_fee[0], mempool_blocks_fee[1]
            )
        else:
            first_median_fee = self.default_fee

        # Calculate second median fee (half hour, ~3 blocks)
        if len(mempool_blocks_fee) > 2:
            second_median_fee = self.optimize_median_fee(
                mempool_blocks_fee[1],
                mempool_blocks_fee[2],
                previous_fee=first_median_fee,
            )
        elif len(mempool_blocks_fee) > 1:
            second_median_fee = self.optimize_median_fee(
                mempool_blocks_fee[1], previous_fee=first_median_fee
            )
        else:
            second_median_fee = self.default_fee

        # Calculate third median fee (hour, ~6 blocks)
        if len(mempool_blocks_fee) > 3:
            third_median_fee = self.optimize_median_fee(
                mempool_blocks_fee[2],
                mempool_blocks_fee[3],
                previous_fee=second_median_fee,
            )
        elif len(mempool_blocks_fee) > 2:
            third_median_fee = self.optimize_median_fee(
                mempool_blocks_fee[2], previous_fee=second_median_fee
            )
        else:
            third_median_fee = self.default_fee

        return first_median_fee, second_median_fee, third_median_fee

    def _set_recommended_fees(
        self,
        minimum_fee: float,
        first_median_fee: float,
        second_median_fee: float,
        third_median_fee: float,
    ) -> None:
        """
        Set the recommended fee values based on calculated median fees.

        Args:
            minimum_fee: The minimum fee rate
            first_median_fee: Fee for fastest confirmation
            second_median_fee: Fee for half-hour confirmation
            third_median_fee: Fee for hour confirmation
        """
        # Calculate base fees
        fastest_fee = max(minimum_fee, first_median_fee)
        half_hour_fee = max(minimum_fee, second_median_fee)
        hour_fee = max(minimum_fee, third_median_fee)

        # Economy fee is at most twice the minimum fee, but at least the minimum fee
        economy_fee_calc = max(minimum_fee, min(2 * minimum_fee, third_median_fee))
        self.economy_fee = economy_fee_calc

        # Ensure fees are monotonically decreasing with confirmation time
        self.fastest_fee = max(fastest_fee, half_hour_fee, hour_fee, economy_fee_calc)
        self.half_hour_fee = max(half_hour_fee, hour_fee, economy_fee_calc)
        self.hour_fee = max(hour_fee, economy_fee_calc)

    def update_mempool_blocks(self, mempool_blocks_fee: Optional[list]) -> bool:
        """
        Update mempool block statistics and recalculate recommended fees.

        Args:
            mempool_blocks_fee (list): List of mempool block fee data dicts.

        Returns:
            bool: True if update was successful, False otherwise.
        """
        if not mempool_blocks_fee or len(mempool_blocks_fee) < 1:
            return False

        self.mempool_blocks_fee = mempool_blocks_fee

        # Calculate basic mempool statistics
        vsize, count, minimum_fee = self._calculate_mempool_stats(mempool_blocks_fee)
        self.minimum_fee = minimum_fee
        self.mempool_vsize = vsize
        self.mempool_size_mb = float(vsize / KB_TO_MB * MEMPOOL_SIZE_MULTIPLIER)
        self.mempool_size_gb = float(vsize / KB_TO_GB * MEMPOOL_SIZE_MULTIPLIER)
        self.mempool_tx_count = count
        self.mempool_blocks = math.ceil(vsize / BLOCK_SIZE_DIVISOR)

        # Calculate fees for different confirmation targets
        first_median_fee, second_median_fee, third_median_fee = (
            self._calculate_median_fees(mempool_blocks_fee)
        )

        # Set the recommended fees
        self._set_recommended_fees(
            minimum_fee, first_median_fee, second_median_fee, third_median_fee
        )

        return True

    def _get_fee_data_for_block(self, block_index: int) -> tuple[float, float, float]:
        """
        Get fee data (min, median, max) for a specific block index.

        Args:
            block_index: Index of the block in the mempool_blocks_fee list

        Returns:
            Tuple of (min_fee, median_fee, max_fee) for the block
        """
        # If we have data for this specific block, use it
        if self.mempool_blocks_fee and len(self.mempool_blocks_fee) > block_index:
            block = self.mempool_blocks_fee[block_index]
        # Otherwise use the last available block
        elif self.mempool_blocks_fee:
            block = self.mempool_blocks_fee[-1]
        else:
            # No data available
            return self.default_fee, self.default_fee, self.default_fee

        min_fee = block["feeRange"][0]
        max_fee = block["feeRange"][-1]
        med_fee = median(block["feeRange"])

        return min_fee, med_fee, max_fee

    def build_fee_array(self) -> tuple[list[float], list[float], list[float]]:
        """
        Build arrays of minimum, median, and maximum fees for the next n blocks.

        Returns:
            tuple: (minFee, medianFee, maxFee) lists for the next n fee blocks.
        """
        min_fees = []
        median_fees = []
        max_fees = []

        for n in range(self.n_fee_blocks):
            min_fee, med_fee, max_fee = self._get_fee_data_for_block(n)
            min_fees.append(min_fee)
            median_fees.append(med_fee)
            max_fees.append(max_fee)

        return min_fees, median_fees, max_fees
