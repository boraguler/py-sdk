# pyright: reportPrivateUsage=false
import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
from _relayer_helpers import (
    FAKE_CREDS,
    PK_DEPLOY_WALLET,
    install_relayer_handler,
    make_deposit_client,
    make_proxy_client,
    make_safe_client,
)

from polymarket import AsyncSecureClient


def test_is_gasless_ready_eoa_returns_false_without_network_call() -> None:
    captured: list[httpx.Request] = []

    async def run() -> bool:
        from eth_account import Account

        signer = Account.from_key(PK_DEPLOY_WALLET)
        client = await AsyncSecureClient.create(
            private_key=PK_DEPLOY_WALLET,
            wallet=signer.address,
            credentials=FAKE_CREDS,
            validate_credentials=False,
        )

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(500, json={"error": "should not be called"}, request=request)

        install_relayer_handler(client, handler)
        try:
            return await client.is_gasless_ready()
        finally:
            await client.close()

    result = asyncio.run(run())
    assert result is False
    assert captured == []


def test_is_gasless_ready_deposit_wallet_sends_type_wallet() -> None:
    captured: list[httpx.Request] = []

    async def run() -> bool:
        client = await make_deposit_client()

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"deployed": True}, request=request)

        install_relayer_handler(client, handler)
        try:
            return await client.is_gasless_ready()
        finally:
            await client.close()

    result = asyncio.run(run())
    assert result is True
    assert len(captured) == 1
    parsed = urlparse(str(captured[0].url))
    assert parsed.path == "/deployed"
    qs = parse_qs(parsed.query)
    assert qs["type"] == ["WALLET"]


def test_is_gasless_ready_proxy_omits_type() -> None:
    captured: list[httpx.Request] = []

    async def run() -> bool:
        client = await make_proxy_client()

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"deployed": False}, request=request)

        install_relayer_handler(client, handler)
        try:
            return await client.is_gasless_ready()
        finally:
            await client.close()

    result = asyncio.run(run())
    assert result is False
    parsed = urlparse(str(captured[0].url))
    assert parsed.path == "/deployed"
    qs = parse_qs(parsed.query)
    assert "type" not in qs


def test_is_gasless_ready_safe_omits_type() -> None:
    captured: list[httpx.Request] = []

    async def run() -> bool:
        client = await make_safe_client()

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"deployed": True}, request=request)

        install_relayer_handler(client, handler)
        try:
            return await client.is_gasless_ready()
        finally:
            await client.close()

    result = asyncio.run(run())
    assert result is True
    parsed = urlparse(str(captured[0].url))
    qs = parse_qs(parsed.query)
    assert "type" not in qs
