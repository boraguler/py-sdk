# Contributing

## Development Setup

```bash
make sync
```

## Checks

```bash
make check
```

## Dependency Policy

Runtime dependencies should use conservative ranges in `pyproject.toml`.

Development and CI dependencies are locked in `uv.lock`.

Do not pin transitive dependencies in published package metadata unless there is a known incompatibility.

## Tests

Unit tests should be deterministic and avoid live network calls.

Integration tests must be marked with `@pytest.mark.integration` and must be safe to skip in default CI.

Integration tests that need credentials should read them through the `require_env` fixture instead of calling `os.environ` directly at import time. Missing credentials should skip the test, not fail collection.

```python
import pytest


@pytest.mark.integration
def test_authenticated_flow(require_env):
    private_key = require_env("POLYMARKET_TEST_PRIVATE_KEY")
```

For local runs, copy `.env.example` to `.env` and fill only the values needed by the tests you are running:

```bash
cp .env.example .env
make test-integration
```

Use disposable test credentials only. Never commit `.env` files or real secrets. In GitHub Actions, define the names from `.env.example` as repository or environment secrets instead of generating `.env` files.

Tests that place orders, spend funds, or mutate live state must also use `@pytest.mark.metered`. Metered tests are skipped unless `POLYMARKET_RUN_METERED_TESTS=1` is set.

```python
import pytest


@pytest.mark.integration
@pytest.mark.metered
def test_order_lifecycle(require_env):
    private_key = require_env("POLYMARKET_TEST_PRIVATE_KEY")
```

```bash
POLYMARKET_RUN_METERED_TESTS=1 make test-integration
```

## Releases

Use Conventional Commits. Release PRs and changelog updates are managed by release-please.
