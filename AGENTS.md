# AGENTS.md

## Build, Lint, and Test

- **Install dependencies:** `uv pip install -r requirements.txt -r requirements-test.txt`
- **Run all tests:** `pytest`
- **Run a single test:** `pytest tests/test_api.py::TestClass::test_method`
- **Test coverage:** `pytest --cov=pymempool`
- **Lint and format:** `pre-commit run --show-diff-on-failure --color=always --all-files` or `ruff check --fix --exit-non-zero-on-fix --config=.ruff.toml`
- doc is created by `python docs/make.py`
- mypy check: `mypy pymempool`

## Code Style Guidelines

- **Imports:** Use isort order: future, stdlib, third-party, first-party, local. Group and sort imports.
- **Formatting:** Use `ruff format` (PEP8, 88-char lines, trailing whitespace removed).
- **Types:** Use type hints for all public functions and methods.
- **Naming:** Use snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants.
- **Error Handling:** Use explicit exception types; avoid bare `except:`. Prefer custom errors for API boundaries.

## Pre-commit & Ruff Rules

- **Pre-commit hooks:** ruff, ruff-format, check-toml/yaml, end-of-file-fixer, trailing-whitespace, debug-statements, check-docstring-first.
- **Ruff lint:** Enforces B, C90, E501, I (isort), UP (pyupgrade). Max complexity: 16.
- **Per-file ignores:** `__init__.py` ignores unused/unsorted imports.

## Misc

- **Python version:** 3.9+
- **Entry point:** `pymempool.cli:app` (typer CLI)
- **Docs:** Keep docstrings first in modules/classes/functions.
