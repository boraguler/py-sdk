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


def test_merge_positions_resolves_max_to_min_of_yes_no() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_deposit_client()
        _setup_relayer(client, captured, "tx-merge-max")
        client.list_positions = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (
                _pos(outcome_index=0, size="100.0", negative_risk=False),
                _pos(outcome_index=1, size="60.0", negative_risk=False),
            )
        )
        try:
            await client.merge_positions(condition_id=_CONDITION_ID, amount="max")
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    body = request_json(submit_calls[0])
    inner = body["depositWalletParams"]["calls"][0]
    assert inner["target"].lower() == PRODUCTION.conditional_tokens.lower()
    assert "Merge 60000000 positions" in body["metadata"]


def test_merge_positions_rejects_amount_above_max() -> None:
    async def run() -> None:
        client = await make_deposit_client()
        client.list_positions = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (
                _pos(outcome_index=0, size="100.0", negative_risk=False),
                _pos(outcome_index=1, size="60.0", negative_risk=False),
            )
        )
        try:
            with pytest.raises(UserInputError, match="exceeds the maximum"):
                await client.merge_positions(condition_id=_CONDITION_ID, amount=70_000_000)
        finally:
            await client.close()

    asyncio.run(run())


def test_merge_positions_neg_risk_uses_adapter_target() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_deposit_client()
        _setup_relayer(client, captured, "tx-merge-nr")
        client.list_positions = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (
                _pos(outcome_index=0, size="50.0", negative_risk=True),
                _pos(outcome_index=1, size="50.0", negative_risk=True),
            )
        )
        try:
            await client.merge_positions(condition_id=_CONDITION_ID, amount="max")
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    body = request_json(submit_calls[0])
    inner = body["depositWalletParams"]["calls"][0]
    assert inner["target"].lower() == PRODUCTION.neg_risk_adapter.lower()


def test_merge_positions_rejects_when_no_positions() -> None:
    async def run() -> None:
        client = await make_deposit_client()
        client.list_positions = lambda **_: _StubPaginator(())  # type: ignore[method-assign]
        try:
            with pytest.raises(UserInputError, match="no positions"):
                await client.merge_positions(condition_id=_CONDITION_ID, amount="max")
        finally:
            await client.close()

    asyncio.run(run())


def test_merge_positions_rejects_single_side_only() -> None:
    async def run() -> None:
        client = await make_deposit_client()
        client.list_positions = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (_pos(outcome_index=0, size="100.0", negative_risk=False),)
        )
        try:
            with pytest.raises(UserInputError, match="no complementary"):
                await client.merge_positions(condition_id=_CONDITION_ID, amount="max")
        finally:
            await client.close()

    asyncio.run(run())
