from datetime import datetime

from .utils import time_until


class DifficultyAdjustment:
    def __init__(self, lastblocknum, difficulty_adjustment=None):
        self.lastblocknum = 0
        self.difficulty_adjustment = None
        self.last_retarget = 0
        self.minutes_between_blocks = 0
        self.found_blocks = 0
        self.blocks_behind = 0
        self.estimated_retarged_date = 0
        self.estimated_retarged_period = ""

        self.update_difficulty_adjustment(lastblocknum, difficulty_adjustment)

    def update_difficulty_adjustment(self, lastblocknum, difficulty_adjustment):
        self.lastblocknum = lastblocknum
        self.difficulty_adjustment = difficulty_adjustment
        self.last_retarget = (
            lastblocknum - 2016 + difficulty_adjustment["remainingBlocks"]
        )
        self.found_blocks = lastblocknum - self.last_retarget

        self.estimated_retarged_date = datetime.fromtimestamp(
            difficulty_adjustment["estimatedRetargetDate"] / 1000
        )

        self.estimated_retarged_period = time_until(self.estimated_retarged_date)
        self.blocks_behind = difficulty_adjustment["expectedBlocks"] - self.found_blocks
        self.minutes_between_blocks = difficulty_adjustment["timeAvg"] / 60000
        return True
