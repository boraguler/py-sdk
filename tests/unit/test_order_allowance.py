# pyright: reportPrivateUsage=false
import asyncio
import dataclasses
from typing import Any

import httpx
import pytest

from polymarket import ApiKeyCreds, AsyncSecureClient
from polymarket._internal.actions.orders.allowance import ensure_order_allowance
from polymarket._internal.actions.orders.types import OrderDraft
from polymarket.clients._transport import AsyncTransport
from polymarket.errors import InsufficientAllowanceError
from polymarket.models.types import TokenId
from polymarket.types import EvmAddress

PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
SIGNER_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
FAKE_CREDS = ApiKeyCreds(key="test-key", passphrase="test-passphrase", secret="dGVzdA==")
EXCHANGE = EvmAddress("0xE111180000d2663C0091e4f400237545B87B996B")


def _draft(*, side: str, offered: int) -> OrderDraft:
    return OrderDraft(
        chain_id=137,
        exchange_address=EXCHANGE,
        expiration=0,
        funder_address=EvmAddress(SIGNER_ADDRESS),
        offered_amount=offered,
        order_type="GTC",
        side=side,  # type: ignore[arg-type]
        signer=EvmAddress(SIGNER_ADDRESS),
        requested_amount=1_000_000,
        token_id=TokenId("8501497"),
    )


def _install_secure_clob(client: AsyncSecureClient, payload: dict[str, Any]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload, request=request)

    transport = AsyncTransport(
        base_url="https://clob.test",
        client=httpx.AsyncClient(
            base_url="https://clob.test", transport=httpx.MockTransport(handler)
        ),
        header_resolver=client._ctx.secure_clob._header_resolver,
    )
    client._ctx = dataclasses.replace(client._ctx, secure_clob=transport)


async def _make_client() -> AsyncSecureClient:
    return await AsyncSecureClient.create(
        private_key=PRIVATE_KEY,
        wallet=SIGNER_ADDRESS,
        credentials=FAKE_CREDS,
        validate_credentials=False,
    )


def test_ensure_order_allowance_passes_when_collateral_sufficient_for_buy() -> None:
    async def run() -> None:
        client = await _make_client()
        try:
            _install_secure_clob(
                client,
                {"balance": "100000000", "allowances": {EXCHANGE: "100000000"}},
            )
            await ensure_order_allowance(client._ctx, _draft(side="BUY", offered=1_000_000))
        finally:
            await client.close()

    asyncio.run(run())


def test_ensure_order_allowance_raises_when_collateral_short_for_buy() -> None:
    async def run() -> None:
        client = await _make_client()
        try:
            _install_secure_clob(
                client,
                {"balance": "100", "allowances": {EXCHANGE: "100"}},
            )
            await ensure_order_allowance(client._ctx, _draft(side="BUY", offered=1_000_000))
        finally:
            await client.close()

    with pytest.raises(InsufficientAllowanceError, match="Insufficient"):
        asyncio.run(run())


def test_ensure_order_allowance_passes_when_conditional_sufficient_for_sell() -> None:
    async def run() -> None:
        client = await _make_client()
        try:
            _install_secure_clob(
                client,
                {"balance": "100000000", "allowances": {EXCHANGE: "100000000"}},
            )
            await ensure_order_allowance(client._ctx, _draft(side="SELL", offered=1_000_000))
        finally:
            await client.close()

    asyncio.run(run())


def test_ensure_order_allowance_spender_lookup_is_case_insensitive() -> None:
    async def run() -> None:
        client = await _make_client()
        try:
            _install_secure_clob(
                client,
                {
                    "balance": "100000000",
                    "allowances": {EXCHANGE.lower(): "100000000"},
                },
            )
            await ensure_order_allowance(client._ctx, _draft(side="BUY", offered=1_000_000))
        finally:
            await client.close()

    asyncio.run(run())
