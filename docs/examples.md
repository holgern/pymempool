# Examples

## Getting Block Information

```python
from pymempool import MempoolAPI

# Initialize the API
mp = MempoolAPI()

# Get the latest block
latest_block = mp.get_blocks(limit=1)[0]
print(f"Latest block height: {latest_block['height']}")
print(f"Latest block hash: {latest_block['id']}")

# Get detailed information about the block
block_details = mp.get_block(latest_block['id'])
print(f"Block size: {block_details['size']} bytes")
print(f"Transaction count: {block_details['tx_count']}")
```

## Working with Fees

```python
from pymempool import MempoolAPI

# Initialize the API
mp = MempoolAPI()

# Get current fee recommendations
fees = mp.get_recommended_fees()
print(f"Fast transaction fee (next block): {fees['fastestFee']} sat/vB")
print(f"Half hour fee: {fees['halfHourFee']} sat/vB")
print(f"Hour fee: {fees['hourFee']} sat/vB")
print(f"Economy fee: {fees['economyFee']} sat/vB")
print(f"Minimum fee: {fees['minimumFee']} sat/vB")
```

## Monitoring the Mempool

```python
from pymempool import MempoolAPI

# Initialize the API
mp = MempoolAPI()

# Get current mempool information
mempool_info = mp.get_mempool()
print(f"Total transactions in mempool: {mempool_info['count']}")
print(f"Total mempool size: {mempool_info['vsize']} vBytes")
print(f"Total fees: {mempool_info['total_fee']} BTC")

# Get mempool transactions by fee rate
mempool_blocks = mp.get_mempool_blocks()
for i, block in enumerate(mempool_blocks):
    print(f"Potential block {i+1}: {len(block['feeRange'])} fee levels, {block['blockVSize']} vBytes")
```

## Using the WebSocket API

```python
import asyncio
from pymempool.websocket import MempoolWebsocket

async def main():
    # Initialize the WebSocket client
    client = MempoolWebsocket()

    # Define a callback function to handle new blocks
    async def on_block(block):
        print(f"New block received: {block['height']} - {block['id']}")

    # Subscribe to new blocks
    await client.connect()
    await client.subscribe("blocks", on_block)

    # Keep the connection alive for 10 minutes
    await asyncio.sleep(600)
    await client.disconnect()

# Run the async function
asyncio.run(main())
```
