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

## Rate-Limit Behavior

`pymempool` treats HTTP `429` as back-pressure. Instead of hammering the same host,
the client slows itself down, honors integer `Retry-After` headers when present,
applies capped exponential backoff with jitter otherwise, and keeps cooldown state
per host so configured mirrors remain a resilience feature rather than rate-limit
evasion.

Short-lived caching is enabled by default for hot endpoints such as recommended fees,
the mempool summary, and projected mempool blocks. This reduces repeated polling
from CLI dashboards while still keeping snapshots fresh.

```python
from pymempool import MempoolAPI

mp = MempoolAPI(
    rate_limit_per_sec=1.0,
    rate_limit_burst=5,
    respect_retry_after=True,
    enable_response_cache=True,
    cache_ttl_seconds=3.0,
)
```

For live terminal views, prefer the WebSocket-backed `pymempool watch` and
`pymempool stream` commands over building tight REST polling loops.
