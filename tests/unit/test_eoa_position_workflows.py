# pyright: reportPrivateUsage=false
import asyncio
from typing import Any

from _relayer_helpers import make_eoa_client_with_rpc, make_rpc_handler

from polymarket.models.data.portfolio import Position
from polymarket.pagination import Page
from polymarket.transactions import EoaTransactionHandle

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


def _make_market_stub(neg_risk: bool):
    class _MarketState:
        def __init__(self) -> None:
            self.neg_risk = neg_risk

    class _Market:
        def __init__(self) -> None:
            self.state = _MarketState()

    return _Market()


def test_eoa_split_position_signs_and_broadcasts() -> None:
    handler = make_rpc_handler(send_response="0x" + "a1" * 32)

    async def run() -> object:
        client = await make_eoa_client_with_rpc(rpc_handler=handler)
        client.list_markets = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (_make_market_stub(neg_risk=False),)
        )
        try:
            return await client.split_position(condition_id=_CONDITION_ID, amount=1_000_000)
        finally:
            await client.close()

    handle = asyncio.run(run())
    assert isinstance(handle, EoaTransactionHandle)
    assert handle.transaction_hash == "0x" + "a1" * 32
    methods = [c["method"] for c in handler.captured]  # pyright: ignore[reportFunctionMemberAccess]
    assert "eth_sendRawTransaction" in methods


def test_eoa_merge_positions_signs_and_broadcasts() -> None:
    handler = make_rpc_handler(send_response="0x" + "b2" * 32)

    async def run() -> object:
        client = await make_eoa_client_with_rpc(rpc_handler=handler)
        client.list_positions = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (
                _pos(outcome_index=0, size="50.0", negative_risk=False),
                _pos(outcome_index=1, size="30.0", negative_risk=False),
            )
        )
        try:
            return await client.merge_positions(condition_id=_CONDITION_ID, amount="max")
        finally:
            await client.close()

    handle = asyncio.run(run())
    assert isinstance(handle, EoaTransactionHandle)
    assert handle.transaction_hash == "0x" + "b2" * 32


def test_eoa_redeem_positions_ctf_signs_and_broadcasts() -> None:
    handler = make_rpc_handler(send_response="0x" + "c3" * 32)

    async def run() -> object:
        client = await make_eoa_client_with_rpc(rpc_handler=handler)
        client.list_positions = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (
                _pos(outcome_index=0, size="10.0", negative_risk=False),
                _pos(outcome_index=1, size="0", negative_risk=False),
            )
        )
        try:
            return await client.redeem_positions(condition_id=_CONDITION_ID)
        finally:
            await client.close()

    handle = asyncio.run(run())
    assert isinstance(handle, EoaTransactionHandle)
    assert handle.transaction_hash == "0x" + "c3" * 32


def test_eoa_redeem_positions_neg_risk_signs_and_broadcasts() -> None:
    handler = make_rpc_handler(send_response="0x" + "d4" * 32)

    async def run() -> object:
        client = await make_eoa_client_with_rpc(rpc_handler=handler)
        client.list_positions = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (
                _pos(outcome_index=0, size="111.0", negative_risk=True),
                _pos(outcome_index=1, size="0", negative_risk=True),
            )
        )
        try:
            return await client.redeem_positions(condition_id=_CONDITION_ID)
        finally:
            await client.close()

    handle = asyncio.run(run())
    assert isinstance(handle, EoaTransactionHandle)
    assert handle.transaction_hash == "0x" + "d4" * 32


def test_eoa_split_position_invalid_amount_propagates() -> None:
    handler = make_rpc_handler()

    async def run() -> None:
        client = await make_eoa_client_with_rpc(rpc_handler=handler)
        client.list_markets = lambda **_: _StubPaginator(  # type: ignore[method-assign]
            (_make_market_stub(neg_risk=False),)
        )
        try:
            import pytest as _pytest

            from polymarket.errors import UserInputError

            with _pytest.raises(UserInputError, match="non-negative"):
                await client.split_position(condition_id=_CONDITION_ID, amount=-1)
        finally:
            await client.close()

    asyncio.run(run())
