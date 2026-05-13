# pyright: reportPrivateUsage=false
import asyncio
import dataclasses
from decimal import Decimal
from typing import cast
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from polymarket import AsyncPublicClient, AsyncSecureClient
from polymarket._internal.context import AsyncSecureClientContext
from polymarket.clients._transport import AsyncTransport
from polymarket.errors import UnexpectedResponseError

PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def _clob_handler(captured: list[httpx.Request], payload: object) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=payload, request=request)

    return httpx.MockTransport(handler)


def _install_async_clob(
    client: AsyncPublicClient | AsyncSecureClient, handler: httpx.MockTransport
) -> None:
    transport = AsyncTransport(
        base_url="https://clob.test",
        client=httpx.AsyncClient(base_url="https://clob.test", transport=handler),
    )
    client._ctx = cast(AsyncSecureClientContext, dataclasses.replace(client._ctx, clob=transport))


def test_async_public_get_midpoint_hits_clob_midpoint_with_token_id() -> None:
    captured: list[httpx.Request] = []

    async def run() -> Decimal:
        async with AsyncPublicClient() as client:
            _install_async_clob(client, _clob_handler(captured, {"mid": "0.5125"}))
            return await client.get_midpoint(token_id="8501497")

    result = asyncio.run(run())

    assert result == Decimal("0.5125")
    assert len(captured) == 1
    parsed = urlparse(str(captured[0].url))
    assert parsed.path == "/midpoint"
    assert parse_qs(parsed.query) == {"token_id": ["8501497"]}


def test_async_secure_get_midpoint_uses_same_clob_endpoint() -> None:
    captured: list[httpx.Request] = []

    async def run() -> Decimal:
        client = await AsyncSecureClient.create(private_key=PRIVATE_KEY)
        try:
            _install_async_clob(client, _clob_handler(captured, {"mid": "0.42"}))
            return await client.get_midpoint(token_id="99")
        finally:
            await client.close()

    assert asyncio.run(run()) == Decimal("0.42")
    parsed = urlparse(str(captured[0].url))
    assert parsed.path == "/midpoint"
    assert parse_qs(parsed.query) == {"token_id": ["99"]}


def test_async_get_midpoint_propagates_malformed_response_error() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            _install_async_clob(client, _clob_handler([], {"unexpected": "shape"}))
            await client.get_midpoint(token_id="1")

    with pytest.raises(UnexpectedResponseError):
        asyncio.run(run())
