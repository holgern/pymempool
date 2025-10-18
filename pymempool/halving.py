import datetime
from typing import Any, Optional, Union

from .difficulty_adjustment import DifficultyAdjustment
from .utils import time_until


class Halving:
    """Bitcoin halving calculation and information."""

    INITIAL_REWARD = 50.0
    HALVING_INTERVAL = 210000

    def __init__(
        self,
        current_height: int,
        difficulty_adjustment: Optional[dict[Any, Any]] = None,
    ):
        """Initialize the Halving calculator.

        Args:
            current_height: Current blockchain height
            difficulty_adjustment: Difficulty adjustment data from mempool API
        """
        self.current_height = current_height
        self.difficulty_adjustment = difficulty_adjustment

        self.current_halving = self.current_height // self.HALVING_INTERVAL
        self.next_halving_height = (self.current_halving + 1) * self.HALVING_INTERVAL
        self.blocks_remaining = self.next_halving_height - self.current_height
        self.current_reward = self.INITIAL_REWARD / (2**self.current_halving)
        self.next_reward = self.current_reward / 2

        self.estimated_date: Union[datetime.datetime, str] = "Unknown"
        self.estimated_days: Union[float, str] = "Unknown"
        self.estimated_time_until: str = "Unknown"

        if difficulty_adjustment is not None:
            self._calculate_time_estimates()

    def _calculate_time_estimates(self) -> None:
        """Calculate time-related estimates for the next halving."""
        da = DifficultyAdjustment(self.current_height, self.difficulty_adjustment or {})

        # Use the average block time to estimate halving date
        avg_block_time_mins = da.minutes_between_blocks
        if avg_block_time_mins > 0:
            mins_remaining = self.blocks_remaining * avg_block_time_mins
            self.estimated_days = mins_remaining / (60 * 24)

            self.estimated_date = datetime.datetime.now() + datetime.timedelta(
                minutes=mins_remaining
            )

            self.estimated_time_until = time_until(self.estimated_date)

    def update(
        self,
        current_height: int,
        difficulty_adjustment: Optional[dict[Any, Any]] = None,
    ) -> None:
        """Update halving calculations with new data.

        Args:
            current_height: Current blockchain height
            difficulty_adjustment: Difficulty adjustment data from mempool API
        """
        self.current_height = current_height
        self.difficulty_adjustment = difficulty_adjustment

        self.current_halving = self.current_height // self.HALVING_INTERVAL
        self.next_halving_height = (self.current_halving + 1) * self.HALVING_INTERVAL
        self.blocks_remaining = self.next_halving_height - self.current_height
        self.current_reward = self.INITIAL_REWARD / (2**self.current_halving)
        self.next_reward = self.current_reward / 2

        self.estimated_date = "Unknown"
        self.estimated_days = "Unknown"
        self.estimated_time_until = "Unknown"

        if difficulty_adjustment is not None:
            self._calculate_time_estimates()
