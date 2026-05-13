# pyright: reportPrivateUsage=false
import asyncio
import dataclasses
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from polymarket import AsyncPublicClient, AsyncSecureClient, PublicClient, SecureClient
from polymarket.clients._transport import AsyncTransport, SyncTransport

PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
SIGNER_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


def _capture(captured: list[httpx.Request], payload: Any = ()) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=payload, request=request)

    return httpx.MockTransport(handler)


def _install_sync(client: PublicClient | SecureClient, handler: httpx.MockTransport) -> None:
    transport = SyncTransport(
        base_url="https://example.test",
        client=httpx.Client(base_url="https://example.test", transport=handler),
    )
    client._ctx = dataclasses.replace(client._ctx, data=transport)


def _install_async(
    client: AsyncPublicClient | AsyncSecureClient, handler: httpx.MockTransport
) -> None:
    transport = AsyncTransport(
        base_url="https://example.test",
        client=httpx.AsyncClient(base_url="https://example.test", transport=handler),
    )
    client._ctx = dataclasses.replace(client._ctx, data=transport)


def _qs(request: httpx.Request) -> dict[str, list[str]]:
    return parse_qs(urlparse(str(request.url)).query)


# ---- list_trades: user is optional on Public ----


def test_public_list_trades_user_is_optional() -> None:
    captured: list[httpx.Request] = []
    with PublicClient() as client:
        _install_sync(client, _capture(captured))
        client.list_trades(market=["0xMARKET"]).first_page()

    qs = _qs(captured[0])
    assert qs.get("market") == ["0xMARKET"]
    assert "user" not in qs


def test_async_public_list_trades_user_is_optional() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        async with AsyncPublicClient() as client:
            _install_async(client, _capture(captured))
            await client.list_trades(market=["0xMARKET"]).first_page()

    asyncio.run(run())
    qs = _qs(captured[0])
    assert qs.get("market") == ["0xMARKET"]
    assert "user" not in qs


# ---- list_trades: event_id passthrough ----


def test_public_list_trades_passes_event_id() -> None:
    captured: list[httpx.Request] = []
    with PublicClient() as client:
        _install_sync(client, _capture(captured))
        client.list_trades(event_id=[42, 43]).first_page()

    assert _qs(captured[0]).get("eventId") == ["42,43"]


def test_async_public_list_trades_passes_event_id() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        async with AsyncPublicClient() as client:
            _install_async(client, _capture(captured))
            await client.list_trades(event_id=[42]).first_page()

    asyncio.run(run())
    assert _qs(captured[0]).get("eventId") == ["42"]


def test_secure_list_trades_passes_event_id() -> None:
    captured: list[httpx.Request] = []
    with SecureClient.create(private_key=PRIVATE_KEY) as client:
        _install_sync(client, _capture(captured))
        client.list_trades(event_id=[7]).first_page()

    qs = _qs(captured[0])
    assert qs.get("eventId") == ["7"]
    assert qs.get("user") == [SIGNER_ADDRESS]


def test_async_secure_list_trades_passes_event_id() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await AsyncSecureClient.create(private_key=PRIVATE_KEY)
        try:
            _install_async(client, _capture(captured))
            await client.list_trades(event_id=[7]).first_page()
        finally:
            await client.close()

    asyncio.run(run())
    qs = _qs(captured[0])
    assert qs.get("eventId") == ["7"]
    assert qs.get("user") == [SIGNER_ADDRESS]


# ---- list_activity: event_id passthrough ----


def test_public_list_activity_passes_event_id() -> None:
    captured: list[httpx.Request] = []
    with PublicClient() as client:
        _install_sync(client, _capture(captured))
        client.list_activity(user="0xUSER", event_id=[99]).first_page()

    assert _qs(captured[0]).get("eventId") == ["99"]


def test_async_public_list_activity_passes_event_id() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        async with AsyncPublicClient() as client:
            _install_async(client, _capture(captured))
            await client.list_activity(user="0xUSER", event_id=[99]).first_page()

    asyncio.run(run())
    assert _qs(captured[0]).get("eventId") == ["99"]


def test_secure_list_activity_passes_event_id() -> None:
    captured: list[httpx.Request] = []
    with SecureClient.create(private_key=PRIVATE_KEY) as client:
        _install_sync(client, _capture(captured))
        client.list_activity(event_id=[12, 13]).first_page()

    qs = _qs(captured[0])
    assert qs.get("eventId") == ["12,13"]
    assert qs.get("user") == [SIGNER_ADDRESS]


def test_async_secure_list_activity_passes_event_id() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await AsyncSecureClient.create(private_key=PRIVATE_KEY)
        try:
            _install_async(client, _capture(captured))
            await client.list_activity(event_id=[12]).first_page()
        finally:
            await client.close()

    asyncio.run(run())
    qs = _qs(captured[0])
    assert qs.get("eventId") == ["12"]
    assert qs.get("user") == [SIGNER_ADDRESS]


# ---- list_positions: event_id passthrough (existed on Public; verify Secure) ----


def test_public_list_positions_passes_event_id() -> None:
    captured: list[httpx.Request] = []
    with PublicClient() as client:
        _install_sync(client, _capture(captured))
        client.list_positions(user="0xUSER", event_id=[5]).first_page()

    assert _qs(captured[0]).get("eventId") == ["5"]


def test_secure_list_positions_passes_event_id() -> None:
    captured: list[httpx.Request] = []
    with SecureClient.create(private_key=PRIVATE_KEY) as client:
        _install_sync(client, _capture(captured))
        client.list_positions(event_id=[5]).first_page()

    qs = _qs(captured[0])
    assert qs.get("eventId") == ["5"]
    assert qs.get("user") == [SIGNER_ADDRESS]


# ---- mutual exclusivity check still surfaces ----


def test_public_list_trades_rejects_market_and_event_id_together() -> None:
    from polymarket.errors import UserInputError

    with (
        PublicClient() as client,
        pytest.raises(UserInputError, match="Provide market or event_id"),
    ):
        client.list_trades(market=["0xM"], event_id=[1])


def test_secure_list_trades_rejects_market_and_event_id_together() -> None:
    from polymarket.errors import UserInputError

    with (
        SecureClient.create(private_key=PRIVATE_KEY) as client,
        pytest.raises(UserInputError, match="Provide market or event_id"),
    ):
        client.list_trades(market=["0xM"], event_id=[1])
