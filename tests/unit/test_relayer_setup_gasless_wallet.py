# pyright: reportPrivateUsage=false
import asyncio
import dataclasses
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from _relayer_helpers import (
    beacon_factory_rpc_handler,
    install_relayer_handler,
    install_rpc_handler,
    legacy_factory_rpc_handler,
    make_deposit_client,
    make_eoa_client,
    make_proxy_client,
    make_safe_client,
    request_json,
)

from polymarket._internal.wallet import (
    derive_beacon_deposit_wallet_address,
    derive_uups_deposit_wallet_address,
)
from polymarket.environments import PRODUCTION
from polymarket.errors import UserInputError


def test_setup_gasless_wallet_rejects_when_no_api_key() -> None:
    async def run() -> None:
        client = await make_eoa_client(with_api_key=False)
        try:
            with pytest.raises(UserInputError, match="Builder API Key or Relayer API Key"):
                await client.setup_gasless_wallet()
        finally:
            await client.close()

    asyncio.run(run())


def test_setup_gasless_wallet_returns_new_client_for_deposit_wallet() -> None:
    async def run() -> None:
        client = await make_deposit_client()
        try:
            returned = await client.setup_gasless_wallet()
            try:
                assert returned is not client
                assert returned.wallet_type == "DEPOSIT_WALLET"
                assert returned.wallet == client.wallet
                assert returned.signer == client.signer
            finally:
                await returned.close()
        finally:
            await client.close()

    asyncio.run(run())


def test_setup_gasless_wallet_returns_new_client_for_proxy() -> None:
    async def run() -> None:
        client = await make_proxy_client()
        try:
            returned = await client.setup_gasless_wallet()
            try:
                assert returned is not client
                assert returned.wallet_type == "POLY_PROXY"
                assert returned.wallet == client.wallet
            finally:
                await returned.close()
        finally:
            await client.close()

    asyncio.run(run())


def test_setup_gasless_wallet_returns_new_client_for_safe() -> None:
    async def run() -> None:
        client = await make_safe_client()
        try:
            returned = await client.setup_gasless_wallet()
            try:
                assert returned is not client
                assert returned.wallet_type == "GNOSIS_SAFE"
                assert returned.wallet == client.wallet
            finally:
                await returned.close()
        finally:
            await client.close()

    asyncio.run(run())


def test_setup_gasless_wallet_eoa_skips_deploy_when_already_deployed() -> None:
    captured: list[httpx.Request] = []

    async def run() -> tuple[str, str]:
        client = await make_eoa_client()
        eoa_address = client._ctx.signer.address
        expected_deposit = derive_uups_deposit_wallet_address(
            eoa_address, PRODUCTION.wallet_derivation
        )

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            path = urlparse(str(request.url)).path
            if path == "/deployed":
                return httpx.Response(200, json={"deployed": True}, request=request)
            return httpx.Response(404, request=request)

        install_relayer_handler(client, handler)
        install_rpc_handler(client, legacy_factory_rpc_handler())
        try:
            new_client = await client.setup_gasless_wallet()
            try:
                assert new_client is not client
                assert client.wallet_type == "EOA"
                assert new_client.wallet_type == "DEPOSIT_WALLET"
                return str(new_client.wallet), expected_deposit
            finally:
                await new_client.close()
        finally:
            await client.close()

    actual, expected = asyncio.run(run())
    assert actual == expected
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert submit_calls == []
    deployed_calls = [r for r in captured if urlparse(str(r.url)).path == "/deployed"]
    assert len(deployed_calls) == 1
    qs = parse_qs(urlparse(str(deployed_calls[0].url)).query)
    assert qs["type"] == ["WALLET"]


def test_setup_gasless_wallet_eoa_deploys_when_not_deployed() -> None:
    captured: list[httpx.Request] = []
    deployed_calls_seen = 0

    async def run() -> str:
        nonlocal deployed_calls_seen
        client = await make_eoa_client()

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal deployed_calls_seen
            captured.append(request)
            path = urlparse(str(request.url)).path
            if path == "/deployed":
                deployed_calls_seen += 1
                return httpx.Response(200, json={"deployed": False}, request=request)
            if path == "/submit":
                return httpx.Response(
                    200,
                    json={
                        "state": "STATE_NEW",
                        "transactionHash": None,
                        "transactionID": "tx-deploy",
                    },
                    request=request,
                )
            if path.startswith("/v1/account/transactions/"):
                return httpx.Response(
                    200,
                    json={
                        "state": "STATE_MINED",
                        "transaction_hash": "0x" + "ab" * 32,
                        "transaction_id": "tx-deploy",
                    },
                    request=request,
                )
            return httpx.Response(404, request=request)

        install_relayer_handler(client, handler)
        install_rpc_handler(client, legacy_factory_rpc_handler())
        client._ctx = dataclasses.replace(
            client._ctx,
            environment=dataclasses.replace(client._ctx.environment, relayer_poll_frequency_ms=1),
        )
        try:
            new_client = await client.setup_gasless_wallet()
            try:
                assert new_client is not client
                assert client.wallet_type == "EOA"
                assert new_client.wallet_type == "DEPOSIT_WALLET"
                return str(new_client.wallet)
            finally:
                await new_client.close()
        finally:
            await client.close()

    asyncio.run(run())
    assert deployed_calls_seen == 1
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert len(submit_calls) == 1
    body = request_json(submit_calls[0])
    assert body["type"] == "WALLET-CREATE"
    assert "signature" not in body
    assert body["metadata"] == "Deploy Deposit Wallet"


def test_setup_gasless_wallet_eoa_uses_beacon_factory_when_available() -> None:
    captured: list[httpx.Request] = []

    async def run() -> tuple[str, str]:
        client = await make_eoa_client()
        eoa_address = client._ctx.signer.address
        expected = derive_beacon_deposit_wallet_address(eoa_address, PRODUCTION.wallet_derivation)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            path = urlparse(str(request.url)).path
            if path == "/deployed":
                return httpx.Response(200, json={"deployed": True}, request=request)
            return httpx.Response(404, request=request)

        install_relayer_handler(client, handler)
        install_rpc_handler(
            client,
            beacon_factory_rpc_handler(PRODUCTION.wallet_derivation.deposit_wallet_beacon),
        )
        try:
            new_client = await client.setup_gasless_wallet()
            try:
                return str(new_client.wallet), expected
            finally:
                await new_client.close()
        finally:
            await client.close()

    actual, expected = asyncio.run(run())
    assert actual == expected
    deployed_calls = [r for r in captured if urlparse(str(r.url)).path == "/deployed"]
    assert len(deployed_calls) == 1
    qs = parse_qs(urlparse(str(deployed_calls[0].url)).query)
    assert qs["address"] == [expected]


def test_setup_gasless_wallet_eoa_propagates_generic_rpc_failure() -> None:
    import pytest

    from polymarket._internal.eoa.rpc import JsonRpcCallError

    async def run() -> None:
        client = await make_eoa_client()

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

        install_rpc_handler(client, rpc_handler)
        install_relayer_handler(
            client,
            lambda r: httpx.Response(500, json={"error": "unused"}, request=r),
        )
        try:
            await client.setup_gasless_wallet()
        finally:
            await client.close()

    with pytest.raises(JsonRpcCallError, match="upstream unavailable"):
        asyncio.run(run())


def test_setup_gasless_wallet_returns_independent_client_with_fresh_transports() -> None:
    captured: list[httpx.Request] = []

    async def run() -> str:
        client = await make_eoa_client()

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            path = urlparse(str(request.url)).path
            if path == "/deployed":
                return httpx.Response(200, json={"deployed": True}, request=request)
            return httpx.Response(404, request=request)

        install_relayer_handler(client, handler)
        install_rpc_handler(client, legacy_factory_rpc_handler())
        async with client:
            returned = await client.setup_gasless_wallet()
            async with returned:
                assert returned is not client
                assert returned.wallet_type == "DEPOSIT_WALLET"
                assert client.wallet_type == "EOA"
                return str(returned.wallet)

    asyncio.run(run())
