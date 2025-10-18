from datetime import datetime
from typing import Any, Optional

from .utils import time_until


class DifficultyAdjustment:
    """Bitcoin difficulty adjustment calculation and information.

    This class processes and calculates information related to Bitcoin's
    difficulty adjustment mechanism, which occurs every 2016 blocks.

    Attributes:
        lastblocknum (int): Current blockchain height
        difficulty_adjustment (Optional[Dict]): Raw difficulty adjustment data
            from mempool API
        last_retarget (int): Block height of the last difficulty adjustment
        minutes_between_blocks (float): Average time between blocks in minutes
        found_blocks (int): Number of blocks found since last retarget
        blocks_behind (int): Difference between expected and found blocks
        estimated_retarget_date (Optional[datetime]): Datetime of the next
            difficulty adjustment
        estimated_retarget_period (str): Human-readable time until next adjustment
    """

    def __init__(self, lastblocknum: int, difficulty_adjustment: dict[Any, Any]):
        """Initialize the DifficultyAdjustment calculator.

        Args:
            lastblocknum: Current blockchain height
            difficulty_adjustment: Difficulty adjustment data from mempool API
        """
        self.lastblocknum: int
        self.difficulty_adjustment: Optional[dict]
        self.last_retarget: int
        self.minutes_between_blocks: float
        self.found_blocks: int
        self.blocks_behind: int
        self.estimated_retarget_date: Optional[datetime]
        self.estimated_retarget_period: str

        self.update_difficulty_adjustment(lastblocknum, difficulty_adjustment)

    def update_difficulty_adjustment(
        self, lastblocknum: int, difficulty_adjustment: dict[Any, Any]
    ) -> bool:
        """
        Update difficulty adjustment calculations with new blockchain data.

        This method processes the difficulty adjustment data from the mempool API
        and calculates various metrics related to the difficulty adjustment.

        Args:
            lastblocknum: Current blockchain height
            difficulty_adjustment: Difficulty adjustment data from mempool API

        Returns:
            True if the update was successful

        Note:
            The difficulty_adjustment dict is expected to contain the following keys:
            - remainingBlocks: Number of blocks until next adjustment
            - estimatedRetargetDate: Timestamp of estimated next adjustment
            - expectedBlocks: Number of blocks expected to be found since last retarget
            - timeAvg: Average time between blocks in milliseconds
        """

        """Update difficulty adjustment calculations with new blockchain data.

        This method processes the difficulty adjustment data from the mempool API
        and calculates various metrics related to the difficulty adjustment.

        Args:
            lastblocknum: Current blockchain height
            difficulty_adjustment: Difficulty adjustment data from mempool API

        Returns:
            True if the update was successful

        Note:
            The difficulty_adjustment dict is expected to contain the following keys:
            - remainingBlocks: Number of blocks until next adjustment
            - estimatedRetargetDate: Timestamp of estimated next adjustment
            - expectedBlocks: Number of blocks expected to be found since last retarget
            - timeAvg: Average time between blocks in milliseconds
        """
        self.lastblocknum = lastblocknum
        self.difficulty_adjustment = difficulty_adjustment
        remaining_blocks = difficulty_adjustment.get("remainingBlocks", 0)
        estimated_retarget_ts = difficulty_adjustment.get("estimatedRetargetDate")
        expected_blocks = difficulty_adjustment.get("expectedBlocks", 0)
        time_avg = difficulty_adjustment.get("timeAvg", 600000)  # default 10 min

        self.last_retarget = lastblocknum - 2016 + remaining_blocks
        self.found_blocks = lastblocknum - self.last_retarget

        if estimated_retarget_ts is not None:
            self.estimated_retarget_date = datetime.fromtimestamp(
                estimated_retarget_ts / 1000
            )
            self.estimated_retarget_period = time_until(self.estimated_retarget_date)
        else:
            self.estimated_retarget_date = None
            self.estimated_retarget_period = "Unknown"

        self.blocks_behind = expected_blocks - self.found_blocks
        self.minutes_between_blocks = time_avg / 60000
        return True
