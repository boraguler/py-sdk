import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest
from websockets.asyncio.server import ServerConnection, serve

from polymarket import AsyncPublicClient
from polymarket.environments import PRODUCTION, Environment, WalletDerivation
from polymarket.errors import UserInputError
from polymarket.models.clob.market_events import MarketBookEvent
from polymarket.streams import MarketSpec

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


def _env_with_market_ws(url: str) -> Environment:
    return Environment(
        name="test",
        chain_id=PRODUCTION.chain_id,
        wallet_derivation=WalletDerivation(
            proxy_factory=PRODUCTION.wallet_derivation.proxy_factory,
            proxy_implementation=PRODUCTION.wallet_derivation.proxy_implementation,
            safe_factory=PRODUCTION.wallet_derivation.safe_factory,
            safe_init_code_hash=PRODUCTION.wallet_derivation.safe_init_code_hash,
            deposit_wallet_factory=PRODUCTION.wallet_derivation.deposit_wallet_factory,
            deposit_wallet_implementation=PRODUCTION.wallet_derivation.deposit_wallet_implementation,
        ),
        collateral_token=PRODUCTION.collateral_token,
        conditional_tokens=PRODUCTION.conditional_tokens,
        neg_risk_adapter=PRODUCTION.neg_risk_adapter,
        standard_exchange=PRODUCTION.standard_exchange,
        neg_risk_exchange=PRODUCTION.neg_risk_exchange,
        safe_multisend=PRODUCTION.safe_multisend,
        relay_hub=PRODUCTION.relay_hub,
        clob_url=PRODUCTION.clob_url,
        clob_market_ws_url=url,
        clob_user_ws_url=PRODUCTION.clob_user_ws_url,
        relayer_url=PRODUCTION.relayer_url,
        gamma_url=PRODUCTION.gamma_url,
        data_url=PRODUCTION.data_url,
        rtds_ws_url=PRODUCTION.rtds_ws_url,
        sports_ws_url=PRODUCTION.sports_ws_url,
    )


def _book_frame(asset_id: str, market: str = "m") -> dict[str, Any]:
    return {
        "event_type": "book",
        "market": market,
        "asset_id": asset_id,
        "bids": [{"price": "0.49", "size": "100"}],
        "asks": [{"price": "0.51", "size": "100"}],
    }


def test_subscribe_with_single_market_spec_returns_underlying_handle() -> None:
    received: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection) -> None:
        raw = await ws.recv()
        assert isinstance(raw, str)
        received.append(json.loads(raw))
        await ws.send(json.dumps(_book_frame("a")))
        async for _ in ws:
            pass

    async def run() -> str:
        async with ws_server(handler) as url:
            client = AsyncPublicClient(environment=_env_with_market_ws(url))
            try:
                async with await client.subscribe(MarketSpec(token_ids=["a"])) as stream:
                    event = await asyncio.wait_for(stream.__aiter__().__anext__(), timeout=2.0)
                    assert isinstance(event, MarketBookEvent)
                    return event.token_id
            finally:
                await client.close()

    token = asyncio.run(run())
    assert token == "a"
    assert received[0]["type"] == "market"
    assert received[0]["assets_ids"] == ["a"]


def test_subscribe_with_list_of_specs_returns_merged_handle() -> None:
    async def handler(ws: ServerConnection) -> None:
        await ws.recv()  # initial subscribe
        # Second spec adds another token via the same socket — incremental
        raw = await ws.recv()
        assert isinstance(raw, str)
        update = json.loads(raw)
        assert update == {
            "operation": "subscribe",
            "assets_ids": ["b"],
            "custom_feature_enabled": False,
        }
        await ws.send(json.dumps(_book_frame("a")))
        await ws.send(json.dumps(_book_frame("b")))
        async for _ in ws:
            pass

    async def run() -> set[str]:
        async with ws_server(handler) as url:
            client = AsyncPublicClient(environment=_env_with_market_ws(url))
            try:
                async with await client.subscribe(
                    [MarketSpec(token_ids=["a"]), MarketSpec(token_ids=["b"])]
                ) as stream:
                    seen: set[str] = set()
                    while len(seen) < 2:
                        event = await asyncio.wait_for(stream.__aiter__().__anext__(), timeout=2.0)
                        assert isinstance(event, MarketBookEvent)
                        seen.add(event.token_id)
                    return seen
            finally:
                await client.close()

    assert asyncio.run(run()) == {"a", "b"}


def test_subscribe_rejects_empty_sequence() -> None:
    async def run() -> None:
        client = AsyncPublicClient()
        try:
            with pytest.raises(UserInputError, match="at least one"):
                await client.subscribe([])
        finally:
            await client.close()

    asyncio.run(run())


def test_subscribe_rejects_bare_string() -> None:
    async def run() -> None:
        client = AsyncPublicClient()
        try:
            with pytest.raises(UserInputError, match="sequence of Subscriptions"):
                await client.subscribe("not-a-spec")  # pyright: ignore[reportArgumentType]
        finally:
            await client.close()

    asyncio.run(run())


def test_subscribe_rejects_unknown_spec_type() -> None:
    async def run() -> None:
        client = AsyncPublicClient()
        try:
            with pytest.raises(UserInputError, match="unsupported"):
                await client.subscribe([object()])  # pyright: ignore[reportArgumentType]
        finally:
            await client.close()

    asyncio.run(run())


def test_invalid_spec_construction_raises_before_any_socket_opens() -> None:
    accepts = 0

    async def handler(ws: ServerConnection) -> None:
        nonlocal accepts
        accepts += 1
        async for _ in ws:
            pass

    async def run() -> tuple[int, bool]:
        async with ws_server(handler) as url:
            client = AsyncPublicClient(environment=_env_with_market_ws(url))
            try:
                # Invalid spec construction itself raises — no subscribe call needed.
                with pytest.raises(UserInputError, match="non-empty"):
                    MarketSpec(token_ids=[])
                await asyncio.sleep(0.05)
                return accepts, client._streams_router is None  # pyright: ignore[reportPrivateUsage]
            finally:
                await client.close()

    count, router_lazy = asyncio.run(run())
    assert count == 0
    assert router_lazy is True


def test_failed_mid_subscribe_rolls_back_prior_handles() -> None:
    """If subscribe() raises partway through the spec list, prior handles
    must be closed so the socket doesn't leak."""

    async def handler(ws: ServerConnection) -> None:
        async for _ in ws:
            pass

    async def run() -> bool:
        async with ws_server(handler) as url:
            client = AsyncPublicClient(environment=_env_with_market_ws(url))
            try:
                # First spec is valid; we use a mock manager-level failure on the
                # second by passing too-many subscribes against a manager that
                # we then close out-of-band. Simpler approach: validate that the
                # router invokes our rollback path when manager.subscribe raises.
                router = client._get_streams_router()  # pyright: ignore[reportPrivateUsage]
                manager = router._get_market_manager()  # pyright: ignore[reportPrivateUsage]
                # Open one successful sub, then close the manager to force the
                # second subscribe to raise.
                spec1 = MarketSpec(token_ids=["a"])
                spec2 = MarketSpec(token_ids=["b"])

                original_subscribe = manager.subscribe
                call_count = 0

                async def failing_subscribe(**kwargs: Any) -> Any:
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return await original_subscribe(**kwargs)
                    raise RuntimeError("simulated mid-subscribe failure")

                manager.subscribe = failing_subscribe  # type: ignore[method-assign]
                with pytest.raises(RuntimeError, match="simulated"):
                    await client.subscribe([spec1, spec2])
                # After rollback, registry should be empty and socket dropped.
                await asyncio.sleep(0.1)
                return not manager.is_open
            finally:
                await client.close()

    assert asyncio.run(run()) is True


def test_merged_handle_preserves_first_child_error() -> None:
    """If a child handle ends with an error, the merged handle must re-raise
    it at end-of-stream rather than silently producing StopAsyncIteration."""
    from polymarket._internal.streams.handle import AsyncSubscriptionHandle
    from polymarket._internal.streams.merged_handle import MergedSubscriptionHandle

    async def run() -> None:
        good: AsyncSubscriptionHandle[int] = AsyncSubscriptionHandle(queue_size=4)
        bad: AsyncSubscriptionHandle[int] = AsyncSubscriptionHandle(queue_size=4)
        good._push(1)  # pyright: ignore[reportPrivateUsage]
        good._end()  # pyright: ignore[reportPrivateUsage]
        bad._end(RuntimeError("child boom"))  # pyright: ignore[reportPrivateUsage]
        merged: MergedSubscriptionHandle[int] = MergedSubscriptionHandle([good, bad])
        first = await merged.__aiter__().__anext__()
        assert first == 1
        with pytest.raises(RuntimeError, match="child boom"):
            await merged.__aiter__().__anext__()
        await merged.close()

    asyncio.run(run())


def test_merged_handle_uses_bounded_queue_with_drop_oldest() -> None:
    """Slow consumer of a merged handle must not unboundedly grow memory."""
    from polymarket._internal.streams.handle import AsyncSubscriptionHandle
    from polymarket._internal.streams.merged_handle import MergedSubscriptionHandle

    async def run() -> int:
        child: AsyncSubscriptionHandle[int] = AsyncSubscriptionHandle(queue_size=8)
        merged: MergedSubscriptionHandle[int] = MergedSubscriptionHandle([child], queue_size=4)
        # Push more events than fit into the merged queue.
        for i in range(20):
            child._push(i)  # pyright: ignore[reportPrivateUsage]
        child._end()  # pyright: ignore[reportPrivateUsage]
        # Drain.
        collected: list[int] = []
        async for event in merged:
            collected.append(event)
        # Some events were dropped — the merged queue is bounded.
        assert len(collected) < 20
        return merged.dropped

    dropped = asyncio.run(run())
    assert dropped > 0


def test_close_cascades_to_streams() -> None:
    async def handler(ws: ServerConnection) -> None:
        async for _ in ws:
            pass

    async def run() -> bool:
        async with ws_server(handler) as url:
            client = AsyncPublicClient(environment=_env_with_market_ws(url))
            handle = await client.subscribe(MarketSpec(token_ids=["a"]))
            await asyncio.sleep(0.05)
            await client.close()
            # Iterating after client close should yield the end sentinel.
            with pytest.raises(StopAsyncIteration):
                await handle.__aiter__().__anext__()
            return True

    assert asyncio.run(run()) is True
