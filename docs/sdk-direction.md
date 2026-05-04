# SDK Direction

This document records developer-experience decisions that shape the public Polymarket Python SDK API.

## API Principles

- Present one cohesive consumer interface instead of exposing current service boundaries directly.
- Design public APIs around developer workflows.
- Keep the default experience simple for scripts, notebooks, CLIs, tests, and bots.
- Preserve feature parity direction with other Polymarket SDKs while adapting API shape to Python ecosystem norms.

## Sync and Async Clients

The default clients are synchronous:

```python
from polymarket import PublicClient

client = PublicClient()
market = client.get_market("540816")
```

When async support is added, it should use explicit async client classes while retaining the same mental model:

```python
from polymarket import AsyncPublicClient

client = AsyncPublicClient()
market = await client.get_market("540816")
```

We evaluated common Python SDKs in trading, exchange, and Web3 ecosystems. The most Pythonic convention is to keep unprefixed clients synchronous and expose async variants with an `Async` prefix, rather than using mode flags or adding separate `_async` methods to every sync client.

The sync and async clients should share request builders, models, auth/signing, serialization, validation, response parsing, and namespace structure. Their implementations should differ at the transport boundary: sync clients use sync transports, async clients use async transports.
