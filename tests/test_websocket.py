import asyncio
import unittest

from pymempool.websocket import MempoolWebSocketClient


class TestMempoolWebSocketClient(unittest.TestCase):
    def test_build_subscription_payloads(self):
        client = MempoolWebSocketClient(
            want_data=["stats", "mempool-blocks"],
            track_address="bc1test",
            track_addresses=["bc1a", "bc1b"],
            track_mempool=True,
            track_mempool_txids=True,
            track_mempool_block_index=2,
            track_rbf="all",
            enable_logging=False,
        )

        self.assertEqual(
            client.build_subscription_payloads(),
            [
                {"action": "want", "data": ["stats", "mempool-blocks"]},
                {"track-address": "bc1test"},
                {"track-addresses": ["bc1a", "bc1b"]},
                {"track-mempool": True},
                {"track-mempool-txids": True},
                {"track-mempool-block": 2},
                {"track-rbf": "all"},
            ],
        )

    def test_subscribe_all_sends_expected_payloads(self):
        sent_payloads = []
        client = MempoolWebSocketClient(
            want_data=["stats"],
            track_rbf="fullRbf",
            enable_logging=False,
        )

        async def fake_send(payload):
            sent_payloads.append(payload)

        client._send = fake_send  # type: ignore[method-assign]
        asyncio.run(client.subscribe_all())

        self.assertEqual(
            sent_payloads,
            [
                {"action": "want", "data": ["stats"]},
                {"track-rbf": "fullRbf"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
