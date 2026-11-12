# List available recipes
default:
    @just --list

# Install dependencies from uv.lock
install:
    uv sync

# Run a calendar sync
sync:
    uv run python -m src.main

# Authenticate with Google and save token.pickle (needs a browser)
auth:
    uv run python -m src.auth_google

# Run the test suite; extra arguments go to pytest
test *args:
    uv run pytest {{args}}

# Run the tests with a coverage report
coverage:
    uv run pytest --cov=src --cov-report=term-missing tests/

# Check linting and formatting, as CI does
lint:
    uv run ruff check
    uv run ruff format --check

# Fix lint issues and format the code
fmt:
    uv run ruff check --fix
    uv run ruff format

# Run all pre-commit hooks on every file
pre-commit:
    uv run pre-commit run --all-files

# Run lint and tests, as CI does
check: lint test
