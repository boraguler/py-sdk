# pyright: reportPrivateUsage=false
import asyncio
import dataclasses
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from _relayer_helpers import (
    install_relayer_handler,
    make_deposit_client,
    make_eoa_client,
    make_proxy_client,
    make_safe_client,
    request_json,
)

from polymarket._internal.wallet import derive_deposit_wallet_address
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


def test_setup_gasless_wallet_returns_self_for_deposit_wallet() -> None:
    async def run() -> None:
        client = await make_deposit_client()
        try:
            returned = await client.setup_gasless_wallet()
            assert returned is client
        finally:
            await client.close()

    asyncio.run(run())


def test_setup_gasless_wallet_returns_self_for_proxy() -> None:
    async def run() -> None:
        client = await make_proxy_client()
        try:
            returned = await client.setup_gasless_wallet()
            assert returned is client
        finally:
            await client.close()

    asyncio.run(run())


def test_setup_gasless_wallet_returns_self_for_safe() -> None:
    async def run() -> None:
        client = await make_safe_client()
        try:
            returned = await client.setup_gasless_wallet()
            assert returned is client
        finally:
            await client.close()

    asyncio.run(run())


def test_setup_gasless_wallet_eoa_skips_deploy_when_already_deployed() -> None:
    captured: list[httpx.Request] = []

    async def run() -> tuple[str, str]:
        client = await make_eoa_client()
        eoa_address = client._ctx.signer.address
        expected_deposit = derive_deposit_wallet_address(eoa_address, PRODUCTION.wallet_derivation)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            path = urlparse(str(request.url)).path
            if path == "/deployed":
                return httpx.Response(200, json={"deployed": True}, request=request)
            return httpx.Response(404, request=request)

        install_relayer_handler(client, handler)
        try:
            new_client = await client.setup_gasless_wallet()
            assert new_client is client
            assert new_client.wallet_type == "DEPOSIT_WALLET"
            return str(new_client.wallet), expected_deposit
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
        client._ctx = dataclasses.replace(
            client._ctx,
            environment=dataclasses.replace(client._ctx.environment, relayer_poll_frequency_ms=1),
        )
        try:
            new_client = await client.setup_gasless_wallet()
            assert new_client.wallet_type == "DEPOSIT_WALLET"
            return str(new_client.wallet)
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


def test_setup_gasless_wallet_does_not_share_transports_across_closes() -> None:
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
        async with client:
            returned = await client.setup_gasless_wallet()
            assert returned is client
            assert returned.wallet_type == "DEPOSIT_WALLET"
            return str(returned.wallet)

    asyncio.run(run())
