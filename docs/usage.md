# Usage

## Basic Python Usage

```python
from pymempool import MempoolAPI, RecommendedFees

mp = MempoolAPI()

fees = RecommendedFees(mp.get_recommended_fees())
print(fees.fastest_fee, fees.minimum_fee)

precise_fees = RecommendedFees(mp.get_recommended_fees_precise())
print(precise_fees.as_dict())

mempool_info = mp.get_mempool()
print(mempool_info["count"], mempool_info["vsize"])

blocks = mp.get_blocks()
print(blocks[0]["height"])
```

## Useful High-Value Endpoints

```python
from pymempool import MempoolAPI

mp = MempoolAPI()

recent_entries = mp.get_mempool_recent()
projected_blocks = mp.get_mempool_blocks_fee()
audit = mp.get_block_audit_summary(mp.get_blocks()[0]["id"])

print(len(recent_entries), len(projected_blocks), audit["id"])
```

## Custom API Endpoints

You can specify a custom mempool.space API instance or a comma-separated failover list:

```python
from pymempool import MempoolAPI

mp = MempoolAPI(api_base_url="https://mempool.space/api/")
fallback = MempoolAPI(
    api_base_url="https://mempool.space/api/,https://mempool.emzy.de/api/"
)
```
