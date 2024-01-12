import math

from .utils import median


class RecommendedFees:
    def __init__(self, recommended_fees=None, mempool_blocks_fee=None):
        self.mempool_blocks_fee = None
        self.hour_fee = None
        self.half_hour_fee = None
        self.fastest_fee = None
        self.economy_fee = None
        self.minimum_fee = 1.0
        self.default_fee = 1.0
        self.n_fee_blocks = 5
        self.mempool_vsize = 0
        self.mempool_size_mb = 0
        self.mempool_tx_count = 0
        self.mempool_blocks = 0
        self.max_mempool_mb = 300
        self.update_recommended_fees(recommended_fees)
        self.update_mempool_blocks(mempool_blocks_fee)

    def update_recommended_fees(self, recommended_fees):
        if not recommended_fees:
            return
        if "hourFee" in recommended_fees:
            self.hour_fee = recommended_fees["hourFee"]
        if "halfHourFee" in recommended_fees:
            self.half_hour_fee = recommended_fees["halfHourFee"]
        if "fastestFee" in recommended_fees:
            self.fastest_fee = recommended_fees["fastestFee"]
        if "economy_fee" in recommended_fees:
            self.economy_fee = recommended_fees["economy_fee"]
        if "minimumFee" in recommended_fees:
            self.minimum_fee = recommended_fees["minimumFee"]

    def optimize_median_fee(self, p_block, next_block=None, previous_fee=None):
        if previous_fee is not None:
            use_fee = (p_block["medianFee"] + previous_fee) / 2
        else:
            use_fee = p_block["medianFee"]
        if p_block["blockVSize"] <= 500000:
            return self.default_fee
        elif p_block["blockVSize"] <= 950000 and next_block is None:
            multiplier = (p_block["blockVSize"] - 500000) / 500000
            return max(use_fee * multiplier, self.default_fee)
        return use_fee

    def update_mempool_blocks(self, mempool_blocks_fee):
        if not mempool_blocks_fee or len(mempool_blocks_fee) < 1:
            return False
        self.mempool_blocks_fee = mempool_blocks_fee

        vsize = 0
        count = 0
        for block in self.mempool_blocks_fee:
            vsize += block["blockVSize"]
            count += block["nTx"]
            if vsize / 1024 / 1024 * 3.99 < self.max_mempool_mb:
                minimum_fee = block["feeRange"][0]
        if minimum_fee < self.default_fee:
            minimum_fee = self.default_fee
        self.minimum_fee = minimum_fee
        self.mempool_vsize = vsize
        self.mempool_size_mb = vsize / 1024 / 1024 * 3.99
        self.mempool_size_gb = vsize / 1024 / 1024 / 1024 * 3.99
        self.mempool_tx_count = count
        self.mempool_blocks = math.ceil(vsize / 1e6)

        if len(mempool_blocks_fee) == 1:
            first_median_fee = self.optimize_median_fee(mempool_blocks_fee[0])
        else:
            first_median_fee = self.optimize_median_fee(
                mempool_blocks_fee[0], mempool_blocks_fee[1]
            )
        if len(mempool_blocks_fee) >= 2:
            second_median_fee = self.optimize_median_fee(
                mempool_blocks_fee[1],
                mempool_blocks_fee[2],
                previous_fee=first_median_fee,
            )
        elif len(mempool_blocks_fee) >= 1:
            second_median_fee = self.optimize_median_fee(
                mempool_blocks_fee[1], previous_fee=first_median_fee
            )
        else:
            second_median_fee = self.default_fee
        if len(mempool_blocks_fee) >= 3:
            third_median_fee = self.optimize_median_fee(
                mempool_blocks_fee[2],
                mempool_blocks_fee[3],
                previous_fee=second_median_fee,
            )
        elif len(mempool_blocks_fee) >= 1:
            third_median_fee = self.optimize_median_fee(
                mempool_blocks_fee[2], previous_fee=second_median_fee
            )
        else:
            third_median_fee = self.default_fee

        fastest_fee = max(self.minimum_fee, first_median_fee)
        half_hour_fee = max(self.minimum_fee, second_median_fee)
        hour_fee = max(self.minimum_fee, third_median_fee)
        self.economy_fee = max(
            self.minimum_fee, min(2 * self.minimum_fee, third_median_fee)
        )

        self.fastest_fee = max(fastest_fee, half_hour_fee, hour_fee, self.economy_fee)
        self.half_hour_fee = max(half_hour_fee, hour_fee, self.economy_fee)
        self.hour_fee = max(hour_fee, self.economy_fee)
        return True

    def build_fee_array(self):
        minFee = []
        maxFee = []
        medianFee = []
        for n in range(self.n_fee_blocks):
            if len(self.mempool_blocks_fee) > n:
                minFee.append(self.mempool_blocks_fee[n]["feeRange"][0])
                maxFee.append(self.mempool_blocks_fee[n]["feeRange"][-1])
                medianFee.append(median(self.mempool_blocks_fee[n]["feeRange"]))
            else:
                minFee.append(
                    self.mempool_blocks_fee[len(self.mempool_blocks_fee) - 1][
                        "feeRange"
                    ][0]
                )
                maxFee.append(
                    self.mempool_blocks_fee[len(self.mempool_blocks_fee) - 1][
                        "feeRange"
                    ][-1]
                )
                medianFee.append(
                    median(
                        self.mempool_blocks_fee[len(self.mempool_blocks_fee) - 1][
                            "feeRange"
                        ]
                    )
                )
        return minFee, medianFee, maxFee
