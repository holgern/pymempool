# Examples

## Fetching Recent Blocks

```python
from pymempool import MempoolAPI

mp = MempoolAPI()

latest_block = mp.get_blocks()[0]
print(f"Latest block height: {latest_block['height']}")
print(f"Latest block hash: {latest_block['id']}")

block_details = mp.get_block(latest_block["id"])
print(f"Block size: {block_details['size']} bytes")
print(f"Transaction count: {block_details['tx_count']}")
```

## Working With Fees

```python
from pymempool import MempoolAPI, RecommendedFees

mp = MempoolAPI()

rounded = RecommendedFees(mp.get_recommended_fees())
precise = RecommendedFees(mp.get_recommended_fees_precise())

print(f"Rounded fastest fee: {rounded.fastest_fee} sat/vB")
print(f"Precise hour fee: {precise.hour_fee} sat/vB")
print(precise.as_dict())
```

## Monitoring The Mempool

```python
from pymempool import MempoolAPI

mp = MempoolAPI()

mempool_info = mp.get_mempool()
print(f"Total transactions in mempool: {mempool_info['count']}")
print(f"Total mempool size: {mempool_info['vsize']} vBytes")
print(f"Total fees: {mempool_info['total_fee']} sats")

projected_blocks = mp.get_mempool_blocks_fee()
for index, block in enumerate(projected_blocks[:3], start=1):
    print(
        f"Projected block {index}: min={block['feeRange'][0]} median={block['medianFee']} "
        f"max={block['feeRange'][-1]} sat/vB"
    )

recent_entries = mp.get_mempool_recent()
for tx in recent_entries[:3]:
    print(tx["txid"], tx.get("fee"), tx.get("vsize"))
```

## Inspecting A Block Audit Summary

```python
from pymempool import MempoolAPI

mp = MempoolAPI()
block_hash = mp.get_blocks()[0]["id"]
audit = mp.get_block_audit_summary(block_hash)

print(audit["id"], audit["matchRate"])
```

## Preparing WebSocket Subscriptions

```python
from pymempool import MempoolWebSocketClient

client = MempoolWebSocketClient(
    want_data=["stats", "mempool-blocks"],
    track_rbf="fullRbf",
    enable_logging=False,
)

print(client.build_subscription_payloads())
```
