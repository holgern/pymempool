# mempool.space API wrapper

[![codecov](https://codecov.io/gh/holgern/pymempool/graph/badge.svg?token=VyIU0ZxwpD)](https://codecov.io/gh/holgern/pymempool)
[![PyPi Version](https://img.shields.io/pypi/v/pymempool.svg)](https://pypi.python.org/pypi/pymempool/)

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

### CLI Commands

The package provides a command-line interface with various commands to interact with the mempool.space API.

```bash
# Display recent Bitcoin blocks as ASCII art with statistics
pymempool blocks --limit 5

# Display mempool blocks as ASCII art with statistics
pymempool mempool-blocks

# Get information about the next Bitcoin halving
pymempool halving

# Get current mempool information
pymempool mempool

# Get current fee recommendations
pymempool fees

# Get details about a specific Bitcoin address
pymempool address <address>

# Get details about a specific block
pymempool block <block_hash>

# Stream live Bitcoin data from the WebSocket API
pymempool stream
```

For more details on any command, use the `--help` option:

```bash
pymempool blocks --help
```

### API Documentation

https://mempool.space/docs/api/rest

## Test Suite

### Set up the test environment

Install the test-runner dependencies:

```
pip3 install -r requirements-test.txt
```

Then make the `pymempool` python module visible/importable to the tests by installing the local dev dir as an editable module:

```
# from the repo root
pip3 install -e .
```

### Running the test suite

Run the whole test suite:

```
# from the repo root
pytest
```

Run a specific test file:

```
pytest test/test_this_file.py
```

Run a specific test:

```
pytest test/test_this_file.py::test_this_specific_test
```

### Running tests with tox

Install tox

```
pip install tox
```

Run tests

```
tox
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
