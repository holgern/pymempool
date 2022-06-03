# mempool.info API wrapper

Python3 wrapper around the [mempool.info](https://www.mempool.info) API (V1)

### Installation
PyPI
```bash
pip install pymempool
```
or from source
```bash
git clone https://github.com/holgern/pymempool.git
cd pymempool
python3 setup.py install
```

### Usage

```python
from pymempool import MempoolAPI
mp = MempoolAPI()
```


### API documentation
https://mempool.space/docs/api/rest

### Test

Run unit tests with:

```
# after installing pytest using pip3
pytest tests
```

## License
[MIT](https://choosealicense.com/licenses/mit/)
