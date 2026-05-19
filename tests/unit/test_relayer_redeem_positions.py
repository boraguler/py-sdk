# pyright: reportPrivateUsage=false
import asyncio
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest
from _relayer_helpers import (
    install_relayer_routes,
    make_deposit_client,
    request_json,
)
from eth_utils.crypto import keccak

from polymarket.environments import PRODUCTION
from polymarket.errors import UserInputError
from polymarket.models.data.portfolio import Position
from polymarket.pagination import Page

_CONDITION_ID = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


class _StubPaginator:
    def __init__(self, items: tuple[Any, ...]) -> None:
        self._items = items

    async def first_page(self) -> Page[Any]:
        return Page(items=self._items, has_more=False)


def _pos(*, outcome_index: int, size: str, negative_risk: bool) -> Position:
    return Position.parse_response(
        {
            "conditionId": _CONDITION_ID,
            "outcomeIndex": outcome_index,
            "size": size,
            "negativeRisk": negative_risk,
        }
    )


def _setup_relayer(client: Any, captured: list[httpx.Request], tx_id: str) -> None:
    install_relayer_routes(
        client,
        captured,
        {
            "/v1/account/transactions/params": {
                "address": client._ctx.signer.address,
                "nonce": "0",
            },
            "/submit": {
                "state": "STATE_NEW",
                "transactionHash": None,
                "transactionID": tx_id,
            },
        },
    )


def test_redeem_positions_ctf_path_uses_conditional_tokens() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_deposit_client()
        _setup_relayer(client, captured, "tx-redeem-ctf")
        client.list_positions = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (
                _pos(outcome_index=0, size="100.0", negative_risk=False),
                _pos(outcome_index=1, size="0", negative_risk=False),
            )
        )
        try:
            await client.redeem_positions(condition_id=_CONDITION_ID)
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    body = request_json(submit_calls[0])
    inner = body["depositWalletParams"]["calls"][0]
    assert inner["target"].lower() == PRODUCTION.conditional_tokens.lower()
    ctf_selector = "0x" + keccak(b"redeemPositions(address,bytes32,bytes32,uint256[])")[:4].hex()
    assert inner["data"].startswith(ctf_selector)


def test_redeem_positions_neg_risk_path_uses_adapter_with_amounts() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_deposit_client()
        _setup_relayer(client, captured, "tx-redeem-nr")
        client.list_positions = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (
                _pos(outcome_index=0, size="111.0", negative_risk=True),
                _pos(outcome_index=1, size="0", negative_risk=True),
            )
        )
        try:
            await client.redeem_positions(condition_id=_CONDITION_ID)
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    body = request_json(submit_calls[0])
    inner = body["depositWalletParams"]["calls"][0]
    assert inner["target"].lower() == PRODUCTION.neg_risk_adapter.lower()
    nr_selector = "0x" + keccak(b"redeemPositions(bytes32,uint256[])")[:4].hex()
    assert inner["data"].startswith(nr_selector)
    yes_word_hex = inner["data"][-128:-64]
    assert int(yes_word_hex, 16) == 111_000_000


def test_redeem_positions_rejects_both_condition_id_and_market_id() -> None:
    async def run() -> None:
        client = await make_deposit_client()
        try:
            with pytest.raises(UserInputError, match="exactly one"):
                await client.redeem_positions(condition_id=_CONDITION_ID, market_id="123")
        finally:
            await client.close()

    asyncio.run(run())


def test_redeem_positions_rejects_neither_argument() -> None:
    async def run() -> None:
        client = await make_deposit_client()
        try:
            with pytest.raises(UserInputError, match="exactly one"):
                await client.redeem_positions()
        finally:
            await client.close()

    asyncio.run(run())


def test_redeem_positions_accepts_market_id() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_deposit_client()
        _setup_relayer(client, captured, "tx-redeem-mkt")
        client.list_positions = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (
                _pos(outcome_index=0, size="10.0", negative_risk=False),
                _pos(outcome_index=1, size="0", negative_risk=False),
            )
        )
        try:
            await client.redeem_positions(market_id="market-123")
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert len(submit_calls) == 1
