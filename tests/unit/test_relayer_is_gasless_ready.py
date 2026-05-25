# pyright: reportPrivateUsage=false
import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
from _relayer_helpers import (
    FAKE_CREDS,
    PK_DEPLOY_WALLET,
    beacon_factory_rpc_handler,
    install_relayer_handler,
    install_rpc_handler,
    legacy_factory_rpc_handler,
    make_deposit_client,
    make_proxy_client,
    make_safe_client,
)

from polymarket import AsyncSecureClient
from polymarket._internal.wallet import (
    derive_beacon_deposit_wallet_address,
    derive_uups_deposit_wallet_address,
)
from polymarket.environments import PRODUCTION


async def _make_eoa_secure_client() -> AsyncSecureClient:
    from eth_account import Account

    signer = Account.from_key(PK_DEPLOY_WALLET)
    return await AsyncSecureClient._create_for_testing(
        private_key=PK_DEPLOY_WALLET,
        wallet=signer.address,
        credentials=FAKE_CREDS,
        validate_credentials=False,
    )


def test_is_gasless_ready_eoa_legacy_factory_queries_uups_deposit_wallet() -> None:
    captured: list[httpx.Request] = []

    async def run() -> tuple[bool, str]:
        client = await _make_eoa_secure_client()
        signer_address = client._ctx.signer.address

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"deployed": True}, request=request)

        install_relayer_handler(client, handler)
        install_rpc_handler(client, legacy_factory_rpc_handler())
        try:
            result = await client.is_gasless_ready()
            return result, signer_address
        finally:
            await client.close()

    result, signer_address = asyncio.run(run())
    expected = derive_uups_deposit_wallet_address(signer_address, PRODUCTION.wallet_derivation)
    assert result is True
    assert len(captured) == 1
    parsed = urlparse(str(captured[0].url))
    assert parsed.path == "/deployed"
    qs = parse_qs(parsed.query)
    assert qs["type"] == ["WALLET"]
    assert qs["address"] == [expected]


def test_is_gasless_ready_eoa_beacon_factory_queries_beacon_deposit_wallet() -> None:
    captured: list[httpx.Request] = []

    async def run() -> tuple[bool, str]:
        client = await _make_eoa_secure_client()
        signer_address = client._ctx.signer.address

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"deployed": False}, request=request)

        install_relayer_handler(client, handler)
        install_rpc_handler(
            client, beacon_factory_rpc_handler(PRODUCTION.wallet_derivation.deposit_wallet_beacon)
        )
        try:
            result = await client.is_gasless_ready()
            return result, signer_address
        finally:
            await client.close()

    result, signer_address = asyncio.run(run())
    expected = derive_beacon_deposit_wallet_address(signer_address, PRODUCTION.wallet_derivation)
    assert result is False
    assert len(captured) == 1
    parsed = urlparse(str(captured[0].url))
    qs = parse_qs(parsed.query)
    assert qs["type"] == ["WALLET"]
    assert qs["address"] == [expected]


def test_is_gasless_ready_eoa_propagates_generic_rpc_failure() -> None:
    import pytest

    from polymarket._internal.eoa.rpc import JsonRpcCallError

    async def run() -> bool:
        client = await _make_eoa_secure_client()

        def rpc_handler(request: httpx.Request) -> httpx.Response:
            import json

            body = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "error": {"code": -32_603, "message": "upstream unavailable"},
                },
                request=request,
            )

        install_relayer_handler(
            client, lambda r: httpx.Response(500, json={"error": "unused"}, request=r)
        )
        install_rpc_handler(client, rpc_handler)
        try:
            return await client.is_gasless_ready()
        finally:
            await client.close()

    with pytest.raises(JsonRpcCallError, match="upstream unavailable"):
        asyncio.run(run())


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
