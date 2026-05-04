import asyncio

from polymarket import AsyncPublicClient, AsyncSecureClient, PublicClient, SecureClient

PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


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


def test_secure_client_factory_uses_production_by_default() -> None:
    client = SecureClient.create(private_key=PRIVATE_KEY)
    try:
        assert client.environment.name == "production"
    finally:
        client.close()


def test_secure_client_supports_context_manager() -> None:
    with SecureClient.create(private_key=PRIVATE_KEY) as client:
        assert client.environment.name == "production"


def test_async_secure_client_factory_uses_production_by_default() -> None:
    async def run() -> None:
        client = await AsyncSecureClient.create(private_key=PRIVATE_KEY)
        try:
            assert client.environment.name == "production"
        finally:
            await client.close()

    asyncio.run(run())


def test_async_secure_client_supports_context_manager() -> None:
    async def run() -> None:
        client = await AsyncSecureClient.create(private_key=PRIVATE_KEY)
        async with client:
            assert client.environment.name == "production"

    asyncio.run(run())
