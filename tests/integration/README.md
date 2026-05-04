# Integration Tests

Integration tests are opt-in and must be marked with `@pytest.mark.integration`.

Tests that place orders, spend funds, or mutate live state must also be marked with `@pytest.mark.metered`. They are skipped unless `POLYMARKET_RUN_METERED_TESTS=1` is set.

Local integration secrets may be placed in a root `.env` file copied from `.env.example`. The SDK does not load `.env` files at runtime; the `require_env` fixture loads the file only for integration tests that request credentials.

Use the `require_env` fixture for credentials so tests skip cleanly when secrets are unavailable:

```python
def test_authenticated_flow(require_env):
    private_key = require_env("POLYMARKET_TEST_PRIVATE_KEY")
```
