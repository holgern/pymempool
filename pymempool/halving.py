import datetime

from .difficulty_adjustment import DifficultyAdjustment
from .utils import time_until


class Halving:
    """Bitcoin halving calculation and information."""

    # Bitcoin constants
    INITIAL_REWARD = 50.0  # Initial day 1 BTC block reward
    HALVING_INTERVAL = 210000  # Block intervals in which BTC halves

    def __init__(
        self, current_height: int, difficulty_adjustment: dict | None = None
    ):
        """Initialize the Halving calculator.

        Args:
            current_height: Current blockchain height
            difficulty_adjustment: Difficulty adjustment data from mempool API
        """
        self.current_height = current_height
        self.difficulty_adjustment = difficulty_adjustment

        # Calculate halving data
        self.current_halving = self.current_height // self.HALVING_INTERVAL
        self.next_halving_height = (self.current_halving + 1) * self.HALVING_INTERVAL
        self.blocks_remaining = self.next_halving_height - self.current_height
        self.current_reward = self.INITIAL_REWARD / (2**self.current_halving)
        self.next_reward = self.current_reward / 2

        # Initialize estimated halving time variables
        self.estimated_date: datetime.datetime | str = "Unknown"
        self.estimated_days: float | str = "Unknown"
        self.estimated_time_until: str = "Unknown"

        # Calculate time estimates if difficulty data is available
        if difficulty_adjustment is not None:
            self._calculate_time_estimates()

    def _calculate_time_estimates(self) -> None:
        """Calculate time-related estimates for the next halving."""
        da = DifficultyAdjustment(self.current_height, self.difficulty_adjustment)

        # Use the average block time to estimate halving date
        avg_block_time_mins = da.minutes_between_blocks
        if avg_block_time_mins > 0:
            mins_remaining = self.blocks_remaining * avg_block_time_mins
            self.estimated_days = mins_remaining / (60 * 24)

            # Calculate estimated date
            self.estimated_date = datetime.datetime.now() + datetime.timedelta(
                minutes=mins_remaining
            )

            # Format time until halving
            self.estimated_time_until = time_until(self.estimated_date)

    def update(
        self, current_height: int, difficulty_adjustment: dict | None = None
    ) -> None:
        """Update halving calculations with new data.

        Args:
            current_height: Current blockchain height
            difficulty_adjustment: Difficulty adjustment data from mempool API
        """
        self.__init__(current_height, difficulty_adjustment)
