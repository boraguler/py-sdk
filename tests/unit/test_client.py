from polymarket import AsyncPublicClient, PublicClient


def test_client_uses_production_by_default() -> None:
    client = PublicClient()

    assert client.environment.name == "production"


def test_async_client_uses_production_by_default() -> None:
    client = AsyncPublicClient()

    assert client.environment.name == "production"
