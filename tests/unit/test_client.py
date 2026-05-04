import asyncio

from polymarket import AsyncPublicClient, PublicClient


def test_client_uses_production_by_default() -> None:
    client = PublicClient()

    assert client.environment.name == "production"


def test_async_client_uses_production_by_default() -> None:
    client = AsyncPublicClient()

    assert client.environment.name == "production"


def test_public_client_supports_context_manager() -> None:
    with PublicClient() as client:
        assert client.environment.name == "production"


def test_async_public_client_supports_context_manager() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            assert client.environment.name == "production"

    asyncio.run(run())
