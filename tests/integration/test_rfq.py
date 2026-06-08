import json
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest
from websockets.asyncio.server import ServerConnection, serve

from polymarket import PRODUCTION, ApiKeyCreds, AsyncSecureClient
from polymarket.rfq import (
    RfqConfirmationRequestEvent,
    RfqExecutionStatus,
    RfqQuoteRequestEvent,
    RfqQuoteSource,
    RfqRequestedSizeUnit,
)

pytestmark = pytest.mark.anyio

RFQ_ID = "rfq-123"
QUOTE_ID = "quote-456"
TX_HASH = "0x1111111111111111111111111111111111111111111111111111111111111111"
CONDITION_ID = "0x5c19f205507ce03ff5f3be08a8090a5969ea6870cc07b902a4ca2e61dfe48fdd"
YES_POSITION_ID = "99878393523957043401217108863095556720659532630565063651671026144852955005052"
NO_POSITION_ID = "14961555500324159061633734348998856463418381831586644199915991405148322060881"

Handler = Callable[[ServerConnection], Awaitable[None]]


def _existing_credentials() -> ApiKeyCreds | None:
    key = os.environ.get("POLYMARKET_TEST_API_KEY")
    secret = os.environ.get("POLYMARKET_TEST_API_SECRET")
    passphrase = os.environ.get("POLYMARKET_TEST_API_PASSPHRASE")
    if key and secret and passphrase:
        return ApiKeyCreds(key=key, secret=secret, passphrase=passphrase)
    return None


@asynccontextmanager
async def _ws_server(handler: Handler) -> AsyncGenerator[str, None]:
    server = await serve(handler, host="127.0.0.1", port=0)
    try:
        sockets = tuple(server.sockets)
        assert sockets
        port = sockets[0].getsockname()[1]
        yield f"ws://127.0.0.1:{port}"
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.integration
async def test_rfq_session_quotes_confirms_and_receives_execution_update(
    require_env: Callable[[str], str],
) -> None:
    received: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection) -> None:
        async for raw in ws:
            assert isinstance(raw, str)
            frame = json.loads(raw)
            received.append(frame)
            if frame["type"] == "auth":
                await ws.send(json.dumps({"type": "auth", "success": True}))
                await ws.send(json.dumps(_quote_request_message()))
            elif frame["type"] == "RFQ_QUOTE":
                await ws.send(
                    json.dumps(
                        {
                            "type": "ACK_RFQ_QUOTE",
                            "rfq_id": RFQ_ID,
                            "quote_id": QUOTE_ID,
                        }
                    )
                )
                await ws.send(json.dumps(_confirmation_request_message(frame)))
            elif frame["type"] == "RFQ_CONFIRMATION_RESPONSE":
                await ws.send(
                    json.dumps(
                        {
                            "type": "ACK_RFQ_CONFIRMATION_RESPONSE",
                            "rfq_id": RFQ_ID,
                            "quote_id": QUOTE_ID,
                            "decision": frame["decision"],
                        }
                    )
                )
                await ws.send(
                    json.dumps(
                        {
                            "type": "RFQ_EXECUTION_UPDATE",
                            "rfq_id": RFQ_ID,
                            "status": "MINED",
                            "tx_hash": TX_HASH,
                        }
                    )
                )

    async with _ws_server(handler) as ws_url:
        client = await AsyncSecureClient.create(
            private_key=require_env("POLYMARKET_PRIVATE_KEY"),
            wallet=require_env("POLYMARKET_DEPOSIT_WALLET"),
            credentials=_existing_credentials(),
            environment=replace(PRODUCTION, rfq_quoter_ws_url=ws_url),
        )
        try:
            async with await client.open_rfq_session() as session:
                async for event in session:
                    if isinstance(event, RfqQuoteRequestEvent):
                        assert event.requested_size.unit is RfqRequestedSizeUnit.NOTIONAL
                        assert event.requested_size.value == Decimal("1")
                        quote = await event.quote(
                            price=Decimal("0.45"), source=RfqQuoteSource.COLLATERAL
                        )
                        assert quote.rfq_id == RFQ_ID
                        assert quote.quote_id == QUOTE_ID
                    elif isinstance(event, RfqConfirmationRequestEvent):
                        ack = await event.confirm()
                        assert ack.rfq_id == RFQ_ID
                        assert ack.quote_id == QUOTE_ID
                    else:
                        assert event.status is RfqExecutionStatus.MINED
                        assert event.tx_hash == TX_HASH
                        break
        finally:
            await client.close()

    auth = _first_frame(received, "auth")
    assert auth["auth"]["apiKey"]
    assert (
        auth["identity"]["maker_address"].lower()
        == require_env("POLYMARKET_DEPOSIT_WALLET").lower()
    )

    quote = _first_frame(received, "RFQ_QUOTE")
    assert quote["price_e6"] == "450000"
    assert quote["size_e6"] == "2222222"
    signed_order = quote["signed_order"]
    assert signed_order["tokenId"] == NO_POSITION_ID
    assert signed_order["side"] == 0
    assert signed_order["makerAmount"] == "1222223"
    assert signed_order["takerAmount"] == "2222222"
    assert signed_order["signature"].startswith("0x")

    confirmation = _first_frame(received, "RFQ_CONFIRMATION_RESPONSE")
    assert confirmation == {
        "type": "RFQ_CONFIRMATION_RESPONSE",
        "rfq_id": RFQ_ID,
        "quote_id": QUOTE_ID,
        "decision": "CONFIRM",
    }


def _quote_request_message() -> dict[str, object]:
    return {
        "type": "RFQ_REQUEST",
        "rfq_id": RFQ_ID,
        "requestor_public_id": "requestor-abc",
        "leg_position_ids": [YES_POSITION_ID, NO_POSITION_ID],
        "condition_id": CONDITION_ID,
        "yes_position_id": YES_POSITION_ID,
        "no_position_id": NO_POSITION_ID,
        "direction": "BUY",
        "side": "YES",
        "requested_size": {"unit": "notional", "value_e6": "1000000"},
        "submission_deadline": 1780805856000,
    }


def _confirmation_request_message(quote: dict[str, Any]) -> dict[str, object]:
    signed_order = quote["signed_order"]
    return {
        "type": "RFQ_CONFIRMATION_REQUEST",
        "rfq_id": RFQ_ID,
        "quote_id": QUOTE_ID,
        "signer_address": signed_order["signer"],
        "maker_address": signed_order["maker"],
        "signature_type": signed_order["signatureType"],
        "leg_position_ids": [YES_POSITION_ID, NO_POSITION_ID],
        "condition_id": CONDITION_ID,
        "yes_position_id": YES_POSITION_ID,
        "no_position_id": NO_POSITION_ID,
        "direction": "BUY",
        "side": "YES",
        "fill_size_e6": quote["size_e6"],
        "price_e6": quote["price_e6"],
        "confirm_by": 1780805866000,
    }


def _first_frame(frames: list[dict[str, Any]], frame_type: str) -> dict[str, Any]:
    for frame in frames:
        if frame.get("type") == frame_type:
            return frame
    raise AssertionError(f"No {frame_type} frame recorded")
