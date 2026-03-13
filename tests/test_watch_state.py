import unittest

from pymempool.watch_state import build_watch_state, reduce_watch_message


class TestWatchState(unittest.TestCase):
    def test_reduce_stats_message(self):
        state = build_watch_state(
            height=900000,
            mempool_info={"count": 10, "vsize": 1000},
            fees={"fastestFee": 3, "minimumFee": 1},
            projected_blocks=[],
        )

        reduce_watch_message(
            state,
            {
                "stats": {
                    "mempoolInfo": {"count": 20, "vsize": 5000},
                    "fees": {
                        "fastestFee": 5.5,
                        "halfHourFee": 4.0,
                        "hourFee": 3.0,
                        "economyFee": 2.0,
                        "minimumFee": 1.0,
                    },
                    "da": {"currentBlockHeight": 900001},
                }
            },
        )

        self.assertEqual(state["stats"]["mempoolInfo"]["count"], 20)
        self.assertEqual(state["stats"]["fees"]["fastest_fee"], 5.5)
        self.assertEqual(state["height"], 900001)

    def test_reduce_mempool_blocks_message(self):
        state = build_watch_state(
            height=900000,
            mempool_info={"count": 10, "vsize": 1000},
            fees={"fastestFee": 3, "minimumFee": 1},
            projected_blocks=[],
        )

        reduce_watch_message(
            state,
            {
                "mempool-blocks": [
                    {
                        "blockSize": 1000000,
                        "blockVSize": 1000000,
                        "nTx": 1000,
                        "totalFees": 10000,
                        "medianFee": 5,
                        "feeRange": [1, 5, 10],
                    }
                ]
            },
        )

        self.assertEqual(len(state["mempool_blocks"]), 1)
        self.assertEqual(state["mempool_blocks"][0]["median_fee"], 5.0)

    def test_reduce_rbf_message(self):
        state = build_watch_state(
            height=900000,
            mempool_info={"count": 10, "vsize": 1000},
            fees={"fastestFee": 3, "minimumFee": 1},
            projected_blocks=[],
        )

        reduce_watch_message(state, {"rbfLatest": [{"fullRbf": True}]})

        self.assertEqual(state["rbf_count"], 1)
        self.assertEqual(state["last_rbf_type"], "fullRbf")


if __name__ == "__main__":
    unittest.main()
