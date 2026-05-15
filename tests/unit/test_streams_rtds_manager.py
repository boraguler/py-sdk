import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest
from websockets.asyncio.server import ServerConnection, serve

from polymarket._internal.streams.rtds.manager import RtdsStreamManager
from polymarket.models.rtds_events import (
    CryptoPricesBinanceEvent,
    EquityPricesUpdateEvent,
)
from polymarket.streams._specs import CryptoPricesSpec, EquityPricesSpec

Handler = Callable[[ServerConnection], Awaitable[None]]


@asynccontextmanager
async def ws_server(handler: Handler) -> AsyncGenerator[str, None]:
    server = await serve(handler, host="127.0.0.1", port=0)
    try:
        port = next(iter(server.sockets)).getsockname()[1]
        yield f"ws://127.0.0.1:{port}"
    finally:
        server.close()
        await server.wait_closed()


def _crypto_frame(symbol: str = "btcusdt", wire_topic: str = "crypto_prices") -> dict[str, Any]:
    return {
        "topic": wire_topic,
        "type": "update",
        "timestamp": "1710000000000",
        "payload": {"symbol": symbol, "timestamp": 1710000000000, "value": "1.0"},
    }


def test_initial_subscribe_frame_sent_on_connect() -> None:
    received: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection) -> None:
        async for raw in ws:
            if raw == "PING":
                continue
            received.append(json.loads(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(CryptoPricesSpec(topic="prices.crypto.binance"))
                await asyncio.sleep(0.1)
                await handle.close()
            finally:
                await mgr.close()

    asyncio.run(run())
    assert received[0] == {
        "action": "subscribe",
        "subscriptions": [{"topic": "crypto_prices", "type": "update"}],
    }


def test_incremental_subscribe_for_new_topic_type() -> None:
    received: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection) -> None:
        async for raw in ws:
            if raw == "PING":
                continue
            received.append(json.loads(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                h1 = await mgr.subscribe(CryptoPricesSpec(topic="prices.crypto.binance"))
                h2 = await mgr.subscribe(CryptoPricesSpec(topic="prices.crypto.chainlink"))
                await asyncio.sleep(0.1)
                await h1.close()
                await h2.close()
            finally:
                await mgr.close()

    asyncio.run(run())
    assert received[0]["subscriptions"] == [{"topic": "crypto_prices", "type": "update"}]
    assert received[1] == {
        "action": "subscribe",
        "subscriptions": [{"topic": "crypto_prices_chainlink", "type": "update"}],
    }


def test_overlapping_specs_dedup_one_subscribe_frame() -> None:
    received: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection) -> None:
        async for raw in ws:
            if raw == "PING":
                continue
            received.append(json.loads(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                h1 = await mgr.subscribe(
                    CryptoPricesSpec(topic="prices.crypto.binance", symbols=["btcusdt"])
                )
                h2 = await mgr.subscribe(
                    CryptoPricesSpec(topic="prices.crypto.binance", symbols=["ethusdt"])
                )
                await asyncio.sleep(0.1)
                await h1.close()
                await h2.close()
            finally:
                await mgr.close()

    asyncio.run(run())
    subscribes = [f for f in received if f["action"] == "subscribe"]
    assert len(subscribes) == 1


def test_unsubscribe_only_after_last_user_drops_a_topic_type() -> None:
    received: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection) -> None:
        async for raw in ws:
            if raw == "PING":
                continue
            received.append(json.loads(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                h1 = await mgr.subscribe(
                    CryptoPricesSpec(topic="prices.crypto.binance", symbols=["btcusdt"])
                )
                h2 = await mgr.subscribe(
                    CryptoPricesSpec(topic="prices.crypto.binance", symbols=["ethusdt"])
                )
                await asyncio.sleep(0.05)
                await h1.close()
                await asyncio.sleep(0.05)
                unsubscribes_so_far = [f for f in received if f["action"] == "unsubscribe"]
                assert unsubscribes_so_far == []
                await h2.close()
                await asyncio.sleep(0.05)
            finally:
                await mgr.close()

    asyncio.run(run())


def test_event_topic_remapped_from_wire_to_api() -> None:
    async def handler(ws: ServerConnection) -> None:
        await ws.recv()  # initial subscribe
        await ws.send(json.dumps(_crypto_frame("btcusdt")))
        async for _ in ws:
            pass

    async def run() -> str:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(CryptoPricesSpec(topic="prices.crypto.binance"))
                event = await asyncio.wait_for(handle.__aiter__().__anext__(), timeout=2.0)
                assert isinstance(event, CryptoPricesBinanceEvent)
                topic = event.topic
                await handle.close()
                return topic
            finally:
                await mgr.close()

    assert asyncio.run(run()) == "prices.crypto.binance"


def test_crypto_symbol_filter_applies_client_side() -> None:
    async def handler(ws: ServerConnection) -> None:
        await ws.recv()  # initial subscribe
        for _ in range(20):
            await ws.send(json.dumps(_crypto_frame("ethusdt")))
            await ws.send(json.dumps(_crypto_frame("btcusdt")))
            await asyncio.sleep(0.02)

    async def run() -> str:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(
                    CryptoPricesSpec(topic="prices.crypto.binance", symbols=["btcusdt"])
                )
                event = await asyncio.wait_for(handle.__aiter__().__anext__(), timeout=2.0)
                assert isinstance(event, CryptoPricesBinanceEvent)
                symbol = event.payload.symbol
                await handle.close()
                return symbol
            finally:
                await mgr.close()

    assert asyncio.run(run()) == "btcusdt"


def test_equity_type_filter_applies_client_side() -> None:
    async def handler(ws: ServerConnection) -> None:
        await ws.recv()
        for _ in range(20):
            await ws.send(
                json.dumps(
                    {
                        "topic": "equity_prices",
                        "type": "subscribe",
                        "timestamp": "1710000000000",
                        "payload": {"symbol": "AAPL", "data": []},
                    }
                )
            )
            await ws.send(
                json.dumps(
                    {
                        "topic": "equity_prices",
                        "type": "update",
                        "timestamp": "1710000000000",
                        "payload": {"symbol": "AAPL", "value": "1", "timestamp": 1710000000000},
                    }
                )
            )
            await asyncio.sleep(0.02)

    async def run() -> str:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(EquityPricesSpec(symbol="AAPL", types=["update"]))
                event = await asyncio.wait_for(handle.__aiter__().__anext__(), timeout=2.0)
                assert isinstance(event, EquityPricesUpdateEvent)
                event_type = event.type
                await handle.close()
                return event_type
            finally:
                await mgr.close()

    assert asyncio.run(run()) == "update"


def test_malformed_event_dropped_and_counter_increments() -> None:
    async def handler(ws: ServerConnection) -> None:
        await ws.recv()
        await ws.send(json.dumps({"topic": "bogus", "type": "x"}))
        await ws.send(json.dumps(_crypto_frame("btcusdt")))
        async for _ in ws:
            pass

    async def run() -> tuple[str, int]:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(CryptoPricesSpec(topic="prices.crypto.binance"))
                event = await asyncio.wait_for(handle.__aiter__().__anext__(), timeout=2.0)
                assert isinstance(event, CryptoPricesBinanceEvent)
                symbol = event.payload.symbol
                await asyncio.sleep(0.05)
                dropped = mgr.dropped_events
                await handle.close()
                return symbol, dropped
            finally:
                await mgr.close()

    symbol, dropped = asyncio.run(run())
    assert symbol == "btcusdt"
    assert dropped == 1


def test_reconnect_resends_full_state() -> None:
    received_per_connection: list[list[dict[str, Any]]] = []
    connect_count = 0

    async def handler(ws: ServerConnection) -> None:
        nonlocal connect_count
        connect_count += 1
        frames: list[dict[str, Any]] = []
        received_per_connection.append(frames)
        if connect_count == 1:
            raw = await ws.recv()
            if isinstance(raw, str) and raw != "PING":
                frames.append(json.loads(raw))
            await ws.close()
            return
        async for raw in ws:
            if raw == "PING":
                continue
            frames.append(json.loads(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(CryptoPricesSpec(topic="prices.crypto.binance"))
                await asyncio.sleep(1.5)
                await handle.close()
            finally:
                await mgr.close()

    asyncio.run(run())
    assert connect_count >= 2
    assert received_per_connection[0][0]["subscriptions"] == [
        {"topic": "crypto_prices", "type": "update"}
    ]
    assert received_per_connection[1][0]["subscriptions"] == [
        {"topic": "crypto_prices", "type": "update"}
    ]


def test_last_handle_close_drops_socket() -> None:
    async def handler(ws: ServerConnection) -> None:
        async for _ in ws:
            pass

    async def run() -> bool:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(CryptoPricesSpec(topic="prices.crypto.binance"))
                await asyncio.sleep(0.05)
                await handle.close()
                await asyncio.sleep(0.1)
                return mgr.is_open
            finally:
                await mgr.close()

    assert asyncio.run(run()) is False


def test_subscribe_after_close_raises() -> None:
    async def run() -> None:
        mgr = RtdsStreamManager(url="ws://127.0.0.1:1")
        await mgr.close()
        with pytest.raises(RuntimeError, match="closed"):
            await mgr.subscribe(CryptoPricesSpec(topic="prices.crypto.binance"))

    asyncio.run(run())
