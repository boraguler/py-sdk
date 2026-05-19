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


async def make_eoa_client(*, with_api_key: bool = True) -> AsyncSecureClient:
    from eth_account import Account

    signer = Account.from_key(PK_DEPLOY_WALLET)
    return await AsyncSecureClient.create(
        private_key=PK_DEPLOY_WALLET,
        wallet=signer.address,
        credentials=FAKE_CREDS,
        api_key=BUILDER_AUTH if with_api_key else None,
        validate_credentials=False,
    )


async def make_eoa_client_with_rpc(
    *, rpc_handler: Callable[[httpx.Request], httpx.Response]
) -> AsyncSecureClient:
    from eth_account import Account

    from polymarket._internal.eoa.rpc import JsonRpcClient
    from polymarket.environments import PRODUCTION

    env = dataclasses.replace(PRODUCTION, rpc_url="https://rpc.test")
    signer = Account.from_key(PK_DEPLOY_WALLET)
    client = await AsyncSecureClient.create(
        private_key=PK_DEPLOY_WALLET,
        wallet=signer.address,
        credentials=FAKE_CREDS,
        api_key=BUILDER_AUTH,
        environment=env,
        validate_credentials=False,
    )
    rpc_transport = AsyncTransport(
        base_url="https://rpc.test",
        client=httpx.AsyncClient(
            base_url="https://rpc.test", transport=httpx.MockTransport(rpc_handler)
        ),
    )
    client._ctx = dataclasses.replace(client._ctx, rpc=JsonRpcClient(rpc_transport))
    return client


def make_rpc_handler(
    *,
    nonce: int = 7,
    gas_price: int = 30_000_000_000,
    gas_estimate: int = 100_000,
    send_response: str | None = None,
    receipt_responses: list[dict[str, object] | None] | None = None,
    chain_id: int = 137,
) -> Callable[[httpx.Request], httpx.Response]:
    captured: list[dict[str, object]] = []
    receipt_iter = iter(receipt_responses or [])

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        captured.append(body)
        method = body["method"]
        if method == "eth_chainId":
            result: object = hex(chain_id)
        elif method == "eth_getTransactionCount":
            result = hex(nonce)
        elif method == "eth_gasPrice":
            result = hex(gas_price)
        elif method == "eth_estimateGas":
            result = hex(gas_estimate)
        elif method == "eth_sendRawTransaction":
            result = send_response or ("0x" + "ab" * 32)
        elif method == "eth_getTransactionReceipt":
            try:
                result = next(receipt_iter)
            except StopIteration:
                result = None
        else:
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": body["id"], "error": {"message": "unmocked"}},
                request=request,
            )
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": body["id"], "result": result},
            request=request,
        )

    handler.captured = captured  # type: ignore[attr-defined]
    return handler


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


RELAY_PAYLOAD_DEFAULT_ADDRESS = "0xe679d14b2fe0bdee4a54f25bcec2978e372de566"


def install_relayer_routes(
    client: AsyncSecureClient,
    captured: list[httpx.Request],
    routes: dict[str, Any],
) -> None:
    if "/relay-payload" not in routes and "/v1/account/transactions/params" in routes:
        legacy = routes["/v1/account/transactions/params"]
        nonce = legacy.get("nonce") if isinstance(legacy, dict) else None
        routes = {
            **routes,
            "/relay-payload": {
                "address": RELAY_PAYLOAD_DEFAULT_ADDRESS,
                "nonce": nonce if nonce is not None else "0",
            },
        }

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
    "RELAY_PAYLOAD_DEFAULT_ADDRESS",
    "SPENDER",
    "TOKEN",
    "install_relayer_handler",
    "install_relayer_routes",
    "make_deposit_client",
    "make_eoa_client",
    "make_eoa_client_with_rpc",
    "make_proxy_client",
    "make_rpc_handler",
    "make_safe_client",
    "request_json",
]
