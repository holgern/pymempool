# Contributing

Contributions are welcome! Here's how you can contribute to the project:

## Setting Up the Development Environment

1. Clone the repository:

   ```bash
   git clone https://github.com/holgern/pymempool.git
   cd pymempool
   ```

2. Install the development dependencies:

   ```bash
   pip install -r requirements-test.txt
   ```

3. Install the package in development mode:

   ```bash
   pip install -e .
   ```

4. Install pre-commit hooks:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Running Tests

Run the whole test suite:

```bash
pytest
```

Run a specific test file:

```bash
pytest tests/test_this_file.py
```

Run a specific test:

```bash
pytest tests/test_this_file.py::test_this_specific_test
```

Run tests with coverage:

```bash
pytest --cov=pymempool
```

## Code Style

The project uses `ruff` for linting and formatting. Pre-commit hooks are configured to automatically check these when you commit.

You can manually run the pre-commit hooks on all files:

```bash
pre-commit run --all-files
```

Or with detailed output:

```bash
pre-commit run --show-diff-on-failure --color=always --all-files
```

## Pull Request Process

1. Create a new branch for your feature or bugfix
2. Make your changes
3. Add tests for your changes
4. Ensure all tests pass
5. Submit a pull request

Please make sure your code follows the project's coding standards and includes appropriate tests.
