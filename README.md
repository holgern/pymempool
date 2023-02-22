# mempool.space API wrapper

Python3 wrapper around the [mempool.space](https://www.mempool.space) API (V1)

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


## Pre-commit-config

### Installation

```
$ pip install pre-commit
```

### Using homebrew:
```
$ brew install pre-commit
```

```
$ pre-commit --version
pre-commit 2.10.0
```

### Install the git hook scripts

```
$ pre-commit install
```

### Run against all the files
```
pre-commit run --all-files
pre-commit run --show-diff-on-failure --color=always --all-files
```

### Update package rev in pre-commit yaml
```bash
pre-commit autoupdate
pre-commit run --show-diff-on-failure --color=always --all-files
```
