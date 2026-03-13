import unittest

from pymempool.metrics import (
    bucket_fee_histogram,
    classify_queue_shape,
    estimate_backlog_blocks,
    interpret_mempool_condition,
    summarize_projected_blocks,
)


def make_projected_block(block_vsize, median_fee, minimum_fee, maximum_fee, ntx=1000):
    return {
        "blockSize": block_vsize,
        "blockVSize": block_vsize,
        "nTx": ntx,
        "totalFees": 123456,
        "medianFee": median_fee,
        "feeRange": [minimum_fee, median_fee, maximum_fee],
    }


class TestMetrics(unittest.TestCase):
    def test_estimate_backlog_blocks(self):
        self.assertEqual(estimate_backlog_blocks(0), 0.0)
        self.assertEqual(estimate_backlog_blocks(2_500_000), 2.5)

    def test_summarize_projected_blocks(self):
        blocks = [
            make_projected_block(1_000_000, 12.0, 8.0, 20.0),
            make_projected_block(750_000, 6.0, 3.0, 9.0),
        ]

        summary = summarize_projected_blocks(blocks, limit=2)

        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0]["index"], 1)
        self.assertEqual(summary[0]["min_fee"], 8.0)
        self.assertEqual(summary[0]["max_fee"], 20.0)
        self.assertEqual(summary[0]["median_fee"], 12.0)
        self.assertEqual(summary[1]["cumulative_depth"], 1.75)

    def test_classify_queue_shape_front_loaded(self):
        blocks = [
            make_projected_block(1_000_000, 18.0, 10.0, 30.0),
            make_projected_block(1_000_000, 9.0, 5.0, 15.0),
            make_projected_block(1_000_000, 4.0, 2.0, 8.0),
            make_projected_block(1_000_000, 2.0, 1.0, 4.0),
        ]

        self.assertEqual(
            classify_queue_shape(blocks, {"minimum_fee": 1.0}), "front-loaded"
        )

    def test_interpret_mempool_condition_low_fee_tail(self):
        blocks = [
            make_projected_block(1_000_000, 8.0, 5.0, 12.0),
            make_projected_block(1_000_000, 4.0, 2.0, 6.0),
            make_projected_block(1_000_000, 1.5, 1.0, 2.0),
            make_projected_block(1_000_000, 1.2, 1.0, 1.4),
        ]

        interpretation = interpret_mempool_condition(
            {"vsize": 4_000_000}, blocks, {"minimum_fee": 1.0}
        )

        self.assertIn("low-fee", interpretation)

    def test_bucket_fee_histogram(self):
        histogram = [[25.0, 400_000], [7.0, 600_000], [1.5, 500_000], [0.8, 250_000]]

        buckets = bucket_fee_histogram(histogram)
        by_label = {bucket["label"]: bucket for bucket in buckets}

        self.assertEqual(by_label[">= 20 sat/vB"]["vsize"], 400_000)
        self.assertEqual(by_label["5-10 sat/vB"]["vsize"], 600_000)
        self.assertEqual(by_label["1-2 sat/vB"]["vsize"], 500_000)
        self.assertEqual(by_label["< 1 sat/vB"]["vsize"], 250_000)
        self.assertAlmostEqual(sum(bucket["percent"] for bucket in buckets), 100.0)


if __name__ == "__main__":
    unittest.main()
