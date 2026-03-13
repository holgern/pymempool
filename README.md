# pymempool

[![codecov](https://codecov.io/gh/holgern/pymempool/graph/badge.svg?token=VyIU0ZxwpD)](https://codecov.io/gh/holgern/pymempool)
[![PyPi Version](https://img.shields.io/pypi/v/pymempool.svg)](https://pypi.python.org/pypi/pymempool/)

Python wrapper and terminal dashboard for the [mempool.space](https://mempool.space) API.

## Installation

PyPI:

```bash
pip install pymempool
```

From source:

```bash
git clone https://github.com/holgern/pymempool.git
cd pymempool
python -m pip install -e .
```

## Quick Start

```python
from pymempool import MempoolAPI, RecommendedFees

mp = MempoolAPI()

fees = RecommendedFees(mp.get_recommended_fees_precise())
print(fees.as_dict())

mempool = mp.get_mempool()
print(mempool["count"], mempool["vsize"])

projected_blocks = mp.get_mempool_blocks_fee()
print(projected_blocks[0]["medianFee"])
```

## Best First Commands

```bash
pymempool overview
pymempool pressure
pymempool ladder
pymempool watch
```

## CLI Commands

```bash
# One-screen mempool dashboard
pymempool overview --precise-fees --blocks 6

# Fee pressure across human-readable bands
pymempool pressure

# Decision-first projected block ladder
pymempool ladder --limit 8

# Legacy ASCII mempool blocks view
pymempool mempool-blocks --limit 4

# Live mempool dashboard
pymempool watch --rbf fullRbf

# Stream raw websocket events
pymempool stream --want stats --want mempool-blocks
```

For command details:

```bash
pymempool --help
pymempool overview --help
```

## API Highlights

```python
from pymempool import MempoolAPI, MempoolWebSocketClient

mp = MempoolAPI()

rounded = mp.get_recommended_fees()
precise = mp.get_recommended_fees_precise()
recent = mp.get_mempool_recent()
audit = mp.get_block_audit_summary("<block_hash>")

client = MempoolWebSocketClient(want_data=["stats", "mempool-blocks"])
print(client.build_subscription_payloads())
```

## Rate Limiting

`pymempool` now treats HTTP `429 Too Many Requests` as back-pressure instead of a
generic fast retry. The client:

- rate-limits itself before sending REST requests with conservative per-host defaults
- honors integer `Retry-After` headers when present
- applies exponential backoff with jitter when `Retry-After` is absent
- keeps cooldown state per host so failover stays resilient without turning into rate-limit evasion
- reuses short-lived cached snapshots for hot endpoints like fees, mempool summary, and projected blocks
- prefers WebSocket flows for live dashboards so `watch` and `stream` do not depend on tight REST polling

You can tune the policy via `MempoolAPI(...)`:

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

## Development

Install dev and test dependencies:

```bash
uv pip install -r requirements.txt -r requirements-test.txt
```

Common checks:

```bash
pytest
pre-commit run --show-diff-on-failure --color=always --all-files
mypy pymempool
python docs/make.py
```

## Documentation

- REST API reference: https://mempool.space/docs/api/rest
- Project docs: `docs/`

## License

[MIT](https://choosealicense.com/licenses/mit/)
