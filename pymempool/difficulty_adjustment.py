class DifficultyAdjustment:
    def __init__(self, lastblocknum, difficulty_adjustment=None):
        self.lastblocknum = 0
        self.difficulty_adjustment = None
        self.last_retarget = 0
        self.minutes_between_blocks = 0
        self.update_difficulty_adjustment(lastblocknum, difficulty_adjustment)

    def update_difficulty_adjustment(self, lastblocknum, difficulty_adjustment):
        self.lastblocknum = lastblocknum
        self.difficulty_adjustment = difficulty_adjustment
        self.last_retarget = (
            lastblocknum - 2016 + difficulty_adjustment["remainingBlocks"]
        )
        self.minutes_between_blocks = difficulty_adjustment["timeAvg"] / 60000
        return True
