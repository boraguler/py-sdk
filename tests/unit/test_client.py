from polymarket import PublicClient


def test_client_uses_production_by_default() -> None:
    client = PublicClient()

    assert client.environment.name == "production"
