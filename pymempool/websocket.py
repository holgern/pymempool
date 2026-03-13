import asyncio
import json
import logging
import random
from typing import Any, Callable, Optional

import websockets


class MempoolWebSocketClient:
    def __init__(
        self,
        uri="wss://mempool.space/api/v1/ws",
        max_retries=5,
        max_backoff=60,
        want_data=None,
        track_address=None,
        track_addresses=None,
        track_mempool=False,
        track_mempool_txids=False,
        track_mempool_block_index=None,
        track_rbf=None,
        enable_logging=True,
    ):
        self.uri = uri
        self.connection: Optional[Any] = None
        self.max_retries = max_retries
        self.max_backoff = max_backoff
        self.enable_logging = enable_logging

        self.want_data = want_data or ["mempool-blocks", "stats"]
        self.track_address = track_address
        self.track_addresses = track_addresses or []
        self.track_mempool = track_mempool
        self.track_mempool_txids = track_mempool_txids
        self.track_mempool_block_index = track_mempool_block_index
        self.track_rbf = track_rbf

        if self.enable_logging:
            logging.basicConfig(level=logging.INFO)

        self.message_handler: Callable = self.default_handler
        self.queue: Optional[asyncio.Queue] = None

    def build_subscription_payloads(self) -> list[dict[str, Any]]:
        """Build websocket subscription payloads from the configured options."""

        payloads: list[dict[str, Any]] = []

        if self.want_data:
            payloads.append({"action": "want", "data": self.want_data})
        if self.track_address:
            payloads.append({"track-address": self.track_address})
        if self.track_addresses:
            payloads.append({"track-addresses": self.track_addresses})
        if self.track_mempool:
            payloads.append({"track-mempool": True})
        if self.track_mempool_txids:
            payloads.append({"track-mempool-txids": True})
        if self.track_mempool_block_index is not None:
            payloads.append({"track-mempool-block": self.track_mempool_block_index})
        if self.track_rbf in ["all", "fullRbf"]:
            payloads.append({"track-rbf": self.track_rbf})

        return payloads

    async def connect(self, use_queue=False, consumer=None):
        retry_count = 0
        self.queue = asyncio.Queue() if use_queue else None
        if use_queue and consumer:
            asyncio.create_task(consumer(self.queue))
        while True:
            try:
                async with websockets.connect(self.uri) as websocket:
                    self.connection = websocket
                    retry_count = 0
                    if self.enable_logging:
                        logging.info("Connected to WebSocket.")
                    await self.subscribe_all()
                    await self.receive_data()
            except (
                websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.InvalidStatus,
                websockets.exceptions.WebSocketException,
                asyncio.TimeoutError,
                OSError,
            ) as e:
                retry_count += 1
                backoff = min(self.max_backoff, 2**retry_count + random.uniform(0, 1))
                if self.enable_logging:
                    logging.warning(
                        f"WebSocket error: {e}. Retrying in {backoff:.2f} seconds..."
                    )

                if retry_count > self.max_retries:
                    if self.enable_logging:
                        logging.error("Max retries exceeded. Stopping.")
                    break

                await asyncio.sleep(backoff)
            except Exception as e:
                if self.enable_logging:
                    logging.error(f"Unexpected error: {e}", exc_info=True)
                break

    async def subscribe_all(self):
        for payload in self.build_subscription_payloads():
            await self._send(payload)
            if self.enable_logging:
                logging.info("Sent subscription payload: %s", payload)

    async def _send(self, payload):
        if self.connection is not None:
            await self.connection.send(json.dumps(payload))

    async def receive_data(self):
        if self.connection is not None:
            async for message in self.connection:
                try:
                    data = json.loads(message)
                    if self.queue:
                        await self.queue.put(data)
                    else:
                        await self.message_handler(data)
                except json.JSONDecodeError:
                    if self.enable_logging:
                        logging.warning(f"Non-JSON message received: {message}")

    async def default_handler(self, data):
        if self.enable_logging:
            logging.info("Received message:\n%s", json.dumps(data, indent=2))

    def run(self, handler=None, stream_to_queue=False, queue_consumer=None):
        if handler:
            self.message_handler = handler
        asyncio.run(self.connect(use_queue=stream_to_queue, consumer=queue_consumer))
