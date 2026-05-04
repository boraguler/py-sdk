# Polymarket Python SDK

Official Python SDK for Polymarket.

The SDK gives Python developers one coherent, workflow-oriented interface for building on Polymarket. It follows developer workflows instead of exposing internal service boundaries, starting with public data access and expanding toward authenticated account, trading, builder attribution, and relayer-backed workflows.

## Installation

```bash
uv add polymarket-sdk
```

or:

```bash
pip install polymarket-sdk
```

## Usage

```python
from polymarket import PublicClient

client = PublicClient()
```

## Development

Install dependencies:

```bash
make sync
```

Run checks:

```bash
make check
```

Build package artifacts:

```bash
make build
```

The `Makefile` is a thin convenience wrapper around `uv`. Running the underlying commands directly is also fine.

## Testing

Unit tests run by default:

```bash
make test
```

Run unit tests in watch mode:

```bash
make test-watch
```

This runs the tests once immediately, then reruns them when Python files change.

Integration tests are opt-in:

```bash
make test-integration
```

Integration tests must not place orders, spend funds, or require credentials unless explicitly marked and documented.
