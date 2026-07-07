"""Perps account pagination behavior against a mocked transport."""

import asyncio
import base64
import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from polymarket._internal.actions.perps import account as perps_account
from polymarket.clients._transport import AsyncTransport
from polymarket.errors import UserInputError

_BASE_URL = "https://perps.test"


def _transport(handler: Callable[[httpx.Request], httpx.Response]) -> AsyncTransport:
    return AsyncTransport(
        base_url=_BASE_URL,
        client=httpx.AsyncClient(base_url=_BASE_URL, transport=httpx.MockTransport(handler)),
    )


def _cursor(state: dict[str, Any]) -> str:
    return base64.b64encode(json.dumps(state, separators=(",", ":")).encode()).decode()


def test_descending_account_paginators_reject_malformed_cursor_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("must not fetch with a malformed cursor")

    async def run() -> None:
        transport = _transport(handler)
        try:
            fills = perps_account.list_fills(transport)
            bad_fill_cursors: list[dict[str, Any]] = [
                {"kind": "perpsFills", "start_timestamp": 0, "end_timestamp": 1},
                {
                    "kind": "perpsFills",
                    "start_timestamp": 0,
                    "end_timestamp": 1,
                    "seen_keys": [1],
                },
            ]
            for state in bad_fill_cursors:
                with pytest.raises(UserInputError, match="cursor"):
                    await fills.from_cursor(_cursor(state)).first_page()

            deposits = perps_account.list_deposits(transport)
            with pytest.raises(UserInputError, match="cursor"):
                await deposits.from_cursor(
                    _cursor(
                        {
                            "kind": "perpsDeposits",
                            "start_timestamp": 0,
                            "end_timestamp": 1,
                            "seen_keys": [],
                            "deposit_status": "bogus",
                        }
                    )
                ).first_page()
        finally:
            await transport.close()

    asyncio.run(run())


def test_ascending_account_paginators_reject_malformed_cursor_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("must not fetch with a malformed cursor")

    async def run() -> None:
        transport = _transport(handler)
        try:
            pnl = perps_account.list_pnl_history(transport, interval="1h", start=0)
            bad_pnl_cursors: list[dict[str, Any]] = [
                {"kind": "perpsPnlHistory", "interval": "1h", "start_timestamp": 0},
                {
                    "kind": "perpsPnlHistory",
                    "interval": 5,
                    "start_timestamp": 0,
                    "end_timestamp": 1,
                },
            ]
            for state in bad_pnl_cursors:
                with pytest.raises(UserInputError, match="cursor"):
                    await pnl.from_cursor(_cursor(state)).first_page()
        finally:
            await transport.close()

    asyncio.run(run())
