# pyright: reportPrivateUsage=false
from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import httpx

from polymarket import ApiKeyCreds, AsyncSecureClient, BuilderApiKey
from polymarket.clients._transport import AsyncTransport

PK_DEPLOY_WALLET = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
PK_PROXY_WALLET = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
PK_SAFE_WALLET = "0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"

FAKE_CREDS = ApiKeyCreds(key="k", passphrase="p", secret="dGVzdA==")
BUILDER_AUTH = BuilderApiKey(key="bk", secret="dGVzdA==", passphrase="bp")

TOKEN = "0xDDeeAa11220000000000000000000000000000aA"
SPENDER = "0x000000000000000000000000000000000000dEaD"


async def make_deposit_client() -> AsyncSecureClient:
    from eth_account import Account

    from polymarket._internal.wallet import derive_deposit_wallet_address
    from polymarket.environments import PRODUCTION

    signer = Account.from_key(PK_DEPLOY_WALLET)
    wallet = derive_deposit_wallet_address(signer.address, PRODUCTION.wallet_derivation)
    return await AsyncSecureClient.create(
        private_key=PK_DEPLOY_WALLET,
        wallet=wallet,
        credentials=FAKE_CREDS,
        api_key=BUILDER_AUTH,
        validate_credentials=False,
    )


async def make_proxy_client() -> AsyncSecureClient:
    from eth_account import Account

    from polymarket._internal.wallet import derive_proxy_wallet_address
    from polymarket.environments import PRODUCTION

    signer = Account.from_key(PK_PROXY_WALLET)
    wallet = derive_proxy_wallet_address(signer.address, PRODUCTION.wallet_derivation)
    return await AsyncSecureClient.create(
        private_key=PK_PROXY_WALLET,
        wallet=wallet,
        credentials=FAKE_CREDS,
        api_key=BUILDER_AUTH,
        validate_credentials=False,
    )


async def make_safe_client() -> AsyncSecureClient:
    from eth_account import Account

    from polymarket._internal.wallet import derive_safe_wallet_address
    from polymarket.environments import PRODUCTION

    signer = Account.from_key(PK_SAFE_WALLET)
    wallet = derive_safe_wallet_address(signer.address, PRODUCTION.wallet_derivation)
    return await AsyncSecureClient.create(
        private_key=PK_SAFE_WALLET,
        wallet=wallet,
        credentials=FAKE_CREDS,
        api_key=BUILDER_AUTH,
        validate_credentials=False,
    )


def install_relayer_routes(
    client: AsyncSecureClient,
    captured: list[httpx.Request],
    routes: dict[str, Any],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        path = urlparse(str(request.url)).path
        for prefix, payload in routes.items():
            if path == prefix or path.startswith(f"{prefix}/"):
                return httpx.Response(200, json=payload, request=request)
        return httpx.Response(404, json={"error": "not mocked"}, request=request)

    install_relayer_handler(client, handler)


def install_relayer_handler(
    client: AsyncSecureClient,
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    transport = AsyncTransport(
        base_url="https://relayer.test",
        client=httpx.AsyncClient(
            base_url="https://relayer.test", transport=httpx.MockTransport(handler)
        ),
        header_resolver=client._ctx.relayer._header_resolver,
    )
    client._ctx = dataclasses.replace(client._ctx, relayer=transport)


def request_json(request: httpx.Request) -> Any:
    return json.loads(request.content.decode("utf-8"))


__all__ = [
    "BUILDER_AUTH",
    "FAKE_CREDS",
    "PK_DEPLOY_WALLET",
    "PK_PROXY_WALLET",
    "PK_SAFE_WALLET",
    "SPENDER",
    "TOKEN",
    "install_relayer_handler",
    "install_relayer_routes",
    "make_deposit_client",
    "make_proxy_client",
    "make_safe_client",
    "request_json",
]
