import asyncio
from typing import cast

import pytest

from polymarket import (
    ApiKeyCreds,
    AsyncPublicClient,
    AsyncSecureClient,
    PublicClient,
    SecureClient,
)
from polymarket._internal.context import AsyncSecureClientContext
from polymarket.errors import UserInputError

PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
PRIVATE_KEY_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
FAKE_CREDS = ApiKeyCreds(key="test-key", passphrase="test-passphrase", secret="dGVzdA==")


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


def test_secure_client_requires_factory() -> None:
    with pytest.raises(RuntimeError, match="SecureClient.create"):
        SecureClient(private_key=PRIVATE_KEY)


def test_secure_client_supports_context_manager() -> None:
    with SecureClient.create(private_key=PRIVATE_KEY) as client:
        assert client.environment.name == "production"


def test_async_secure_client_factory_uses_production_by_default() -> None:
    async def run() -> None:
        client = await AsyncSecureClient.create(
            private_key=PRIVATE_KEY, credentials=FAKE_CREDS, validate_credentials=False
        )
        try:
            assert client.environment.name == "production"
        finally:
            await client.close()

    asyncio.run(run())


def test_async_secure_client_requires_factory() -> None:
    with pytest.raises(RuntimeError, match="AsyncSecureClient.create"):
        AsyncSecureClient(ctx=cast(AsyncSecureClientContext, object()))


def test_async_secure_client_supports_context_manager() -> None:
    async def run() -> None:
        client = await AsyncSecureClient.create(
            private_key=PRIVATE_KEY, credentials=FAKE_CREDS, validate_credentials=False
        )
        async with client:
            assert client.environment.name == "production"

    asyncio.run(run())


def test_secure_client_exposes_signer_wallet() -> None:
    with SecureClient.create(private_key=PRIVATE_KEY) as client:
        assert client.wallet == PRIVATE_KEY_ADDRESS


def test_async_secure_client_exposes_signer_wallet() -> None:
    async def run() -> None:
        client = await AsyncSecureClient.create(
            private_key=PRIVATE_KEY, credentials=FAKE_CREDS, validate_credentials=False
        )
        try:
            assert client.wallet == PRIVATE_KEY_ADDRESS
        finally:
            await client.close()

    asyncio.run(run())


def test_secure_client_invalid_key_raises_user_input_error() -> None:
    with pytest.raises(UserInputError, match="Invalid private_key"):
        SecureClient.create(private_key="not-a-valid-key")


def test_async_secure_client_invalid_key_raises_user_input_error() -> None:
    async def run() -> None:
        with pytest.raises(UserInputError, match="Invalid private_key"):
            await AsyncSecureClient.create(private_key="not-a-valid-key")

    asyncio.run(run())
