# Usage

## Basic Usage

```python
from pymempool import MempoolAPI
mp = MempoolAPI()

# Get current recommended fees
fees = mp.get_recommended_fees()
print(fees)

# Get mempool information
mempool_info = mp.get_mempool()
print(mempool_info)

# Get recent blocks
blocks = mp.get_blocks()
print(blocks)
```

## Custom API Endpoint

You can specify a custom mempool.space API endpoint:

```python
from pymempool import MempoolAPI
# Use a specific instance of mempool.space
mp = MempoolAPI(api_base_url="https://mempool.space/api/")
```
