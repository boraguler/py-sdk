import asyncio
import contextlib
import os
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

import pytest

from polymarket import (
    AcceptedOrder,
    ApiKeyCreds,
    AsyncSecureClient,
    OrderBook,
    Position,
)
from polymarket.errors import InsufficientLiquidityError

_MAX_SAFE_BUY_PRICE = Decimal("0.05")
_MIN_SAFE_SELL_PRICE = Decimal("0.95")
_BID_FRACTION = Decimal("0.20")
_SIZE_QUANTIZER = Decimal("0.01")


def _existing_credentials() -> ApiKeyCreds | None:
    key = os.environ.get("POLYMARKET_TEST_API_KEY")
    secret = os.environ.get("POLYMARKET_TEST_API_SECRET")
    passphrase = os.environ.get("POLYMARKET_TEST_API_PASSPHRASE")
    if key and secret and passphrase:
        return ApiKeyCreds(key=key, secret=secret, passphrase=passphrase)
    return None


@asynccontextmanager
async def _secure_client(
    require_env: Callable[[str], str],
) -> AsyncGenerator[AsyncSecureClient, None]:
    private_key = require_env("POLYMARKET_PRIVATE_KEY")
    wallet = require_env("POLYMARKET_DEPOSIT_WALLET")
    client = await AsyncSecureClient.create(
        private_key=private_key,
        wallet=wallet,
        credentials=_existing_credentials(),
    )
    try:
        yield client
    finally:
        await client.close()


def _safe_buy_price(book: OrderBook) -> Decimal:
    if book.bids:
        best_bid = book.bids[-1].price
        candidate = min(_MAX_SAFE_BUY_PRICE, best_bid * _BID_FRACTION)
    else:
        candidate = _MAX_SAFE_BUY_PRICE
    floored = max(candidate, book.tick_size)
    return floored.quantize(book.tick_size, rounding=ROUND_FLOOR)


def _safe_sell_price(book: OrderBook) -> Decimal:
    upper_bound = Decimal(1) - book.tick_size
    if book.asks:
        best_ask = book.asks[-1].price
        candidate = max(_MIN_SAFE_SELL_PRICE, best_ask * Decimal("5"))
    else:
        candidate = _MIN_SAFE_SELL_PRICE
    capped = min(candidate, upper_bound)
    return capped.quantize(book.tick_size, rounding=ROUND_CEILING)


def _size_for_min_notional(min_notional: Decimal, price: Decimal) -> Decimal:
    raw = min_notional / price
    return raw.quantize(_SIZE_QUANTIZER, rounding=ROUND_CEILING)


async def _find_owned_token(client: AsyncSecureClient) -> Position | None:
    paginator = client.list_positions(size_threshold=10.0)
    page = await paginator.first_page()
    for position in page.items:
        if position.token_id and position.size and position.size > 0:
            return position
    return None


async def _wait_for_order_visible(
    client: AsyncSecureClient,
    *,
    token_id: str,
    order_id: str,
    attempts: int = 8,
    delay_s: float = 0.25,
) -> bool:
    for _ in range(attempts):
        page = await client.list_open_orders(token_id=token_id).first_page()
        if any(order.id == order_id for order in page.items):
            return True
        await asyncio.sleep(delay_s)
    return False


async def _wait_for_open_orders_empty(
    client: AsyncSecureClient,
    *,
    attempts: int = 8,
    delay_s: float = 0.25,
) -> bool:
    for _ in range(attempts):
        page = await client.list_open_orders().first_page()
        if not page.items:
            return True
        await asyncio.sleep(delay_s)
    return False


@pytest.mark.integration
@pytest.mark.metered
def test_estimate_market_price_for_buy_returns_decimal_in_unit_range(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    async def run() -> Decimal:
        async with _secure_client(require_env) as client:
            return await client.estimate_market_price(
                token_id=active_clob_token, side="BUY", amount=Decimal("5")
            )

    price = asyncio.run(run())
    assert isinstance(price, Decimal)
    assert Decimal(0) < price < Decimal(1)


@pytest.mark.integration
@pytest.mark.metered
def test_estimate_market_price_fok_raises_on_insufficient_liquidity(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    async def run() -> Decimal:
        async with _secure_client(require_env) as client:
            return await client.estimate_market_price(
                token_id=active_clob_token,
                side="BUY",
                amount=Decimal("1000000000"),
                order_type="FOK",
            )

    with pytest.raises(InsufficientLiquidityError):
        asyncio.run(run())


@pytest.mark.integration
@pytest.mark.metered
def test_place_limit_order_buy_creates_visible_open_order_and_cancels_cleanly(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    async def run() -> None:
        async with _secure_client(require_env) as client:
            book = await client.get_order_book(token_id=active_clob_token)
            assert book.asks, "active token must have at least one resting ask"
            price = _safe_buy_price(book)
            size = _size_for_min_notional(book.min_order_size, price)
            best_ask_price = book.asks[-1].price
            assert price < best_ask_price, (
                f"computed safe price {price} not below best ask {best_ask_price}"
            )

            placed_id: str | None = None
            try:
                placed = await client.place_limit_order(
                    token_id=active_clob_token,
                    price=price,
                    size=size,
                    side="BUY",
                )
                assert isinstance(placed, AcceptedOrder)
                placed_id = placed.order_id

                assert await _wait_for_order_visible(
                    client, token_id=active_clob_token, order_id=placed_id
                ), f"order {placed_id} never appeared in list_open_orders"

                canceled_id = placed_id
                response = await client.cancel_order(order_id=placed_id)
                assert placed_id in response.canceled
                placed_id = None

                for _ in range(8):
                    after = await client.list_open_orders(token_id=active_clob_token).first_page()
                    if all(order.id != canceled_id for order in after.items):
                        break
                    await asyncio.sleep(0.25)
                else:
                    raise AssertionError(f"cancel_order did not clear {canceled_id}")
            finally:
                if placed_id is not None:
                    with contextlib.suppress(Exception):
                        await client.cancel_order(order_id=placed_id)

    asyncio.run(run())


@pytest.mark.integration
@pytest.mark.metered
def test_place_limit_order_sell_round_trips_after_acquiring_inventory(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    async def run() -> None:
        async with _secure_client(require_env) as client:
            position = await _find_owned_token(client)
            if position is not None and position.token_id and position.size:
                token_id = position.token_id
                acquired_shares: Decimal = position.size
            else:
                token_id = active_clob_token
                book = await client.get_order_book(token_id=token_id)
                buy_response = await client.place_market_order(
                    token_id=token_id,
                    side="BUY",
                    amount=book.min_order_size,
                    order_type="FAK",
                )
                assert isinstance(buy_response, AcceptedOrder), (
                    f"market BUY did not accept: {buy_response}"
                )
                acquired_shares = buy_response.taking_amount
                if acquired_shares <= 0:
                    pytest.skip("market BUY filled zero shares; cannot proceed")

            book = await client.get_order_book(token_id=token_id)
            price = _safe_sell_price(book)
            sell_size = acquired_shares.quantize(_SIZE_QUANTIZER, rounding=ROUND_FLOOR)
            if sell_size * price < book.min_order_size:
                pytest.skip(
                    f"acquired {acquired_shares} shares at sell price {price} "
                    f"falls below min_order_size {book.min_order_size}"
                )

            placed_id: str | None = None
            try:
                placed = await client.place_limit_order(
                    token_id=token_id, price=price, size=sell_size, side="SELL"
                )
                assert isinstance(placed, AcceptedOrder)
                placed_id = placed.order_id

                assert await _wait_for_order_visible(client, token_id=token_id, order_id=placed_id)

                response = await client.cancel_order(order_id=placed_id)
                assert placed_id in response.canceled
                placed_id = None
            finally:
                if placed_id is not None:
                    with contextlib.suppress(Exception):
                        await client.cancel_order(order_id=placed_id)

    asyncio.run(run())


@pytest.mark.integration
@pytest.mark.metered
def test_place_limit_order_post_only_lands_on_book(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    async def run() -> None:
        async with _secure_client(require_env) as client:
            book = await client.get_order_book(token_id=active_clob_token)
            price = _safe_buy_price(book)
            size = _size_for_min_notional(book.min_order_size, price)

            placed_id: str | None = None
            try:
                placed = await client.place_limit_order(
                    token_id=active_clob_token,
                    price=price,
                    size=size,
                    side="BUY",
                    post_only=True,
                )
                assert isinstance(placed, AcceptedOrder)
                placed_id = placed.order_id

                assert await _wait_for_order_visible(
                    client, token_id=active_clob_token, order_id=placed_id
                )
            finally:
                if placed_id is not None:
                    with contextlib.suppress(Exception):
                        await client.cancel_order(order_id=placed_id)

    asyncio.run(run())


@pytest.mark.integration
@pytest.mark.metered
def test_create_then_post_split_workflow_matches_place_helper(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    async def run() -> None:
        async with _secure_client(require_env) as client:
            book = await client.get_order_book(token_id=active_clob_token)
            price = _safe_buy_price(book)
            size = _size_for_min_notional(book.min_order_size, price)

            placed_id: str | None = None
            try:
                signed = await client.create_limit_order(
                    token_id=active_clob_token, price=price, size=size, side="BUY"
                )
                assert signed.signature.startswith("0x")
                response = await client.post_order(signed)
                assert isinstance(response, AcceptedOrder)
                placed_id = response.order_id

                assert await _wait_for_order_visible(
                    client, token_id=active_clob_token, order_id=placed_id
                )
            finally:
                if placed_id is not None:
                    with contextlib.suppress(Exception):
                        await client.cancel_order(order_id=placed_id)

    asyncio.run(run())


@pytest.mark.integration
@pytest.mark.metered
def test_place_market_order_buy_executes_against_book(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    async def run() -> None:
        async with _secure_client(require_env) as client:
            book = await client.get_order_book(token_id=active_clob_token)
            amount = book.min_order_size
            response = await client.place_market_order(
                token_id=active_clob_token,
                side="BUY",
                amount=amount,
                order_type="FAK",
            )
            assert isinstance(response, AcceptedOrder)
            assert response.status in ("live", "matched", "delayed")

    asyncio.run(run())


@pytest.mark.integration
@pytest.mark.metered
def test_post_orders_batch_places_multiple_resting_orders(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    async def run() -> None:
        async with _secure_client(require_env) as client:
            book = await client.get_order_book(token_id=active_clob_token)
            price = _safe_buy_price(book)
            size = _size_for_min_notional(book.min_order_size, price)

            signed_orders = [
                await client.create_limit_order(
                    token_id=active_clob_token, price=price, size=size, side="BUY"
                )
                for _ in range(2)
            ]
            placed_ids: list[str] = []
            try:
                responses = await client.post_orders(signed_orders)
                assert len(responses) == 2
                for r in responses:
                    assert isinstance(r, AcceptedOrder)
                    placed_ids.append(r.order_id)
                assert len(set(placed_ids)) == 2, "batch posts produced duplicate order IDs"
            finally:
                for order_id in placed_ids:
                    with contextlib.suppress(Exception):
                        await client.cancel_order(order_id=order_id)

    asyncio.run(run())


@pytest.mark.integration
@pytest.mark.metered
def test_cancel_orders_batch_removes_multiple_open_orders(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    async def run() -> None:
        async with _secure_client(require_env) as client:
            book = await client.get_order_book(token_id=active_clob_token)
            price = _safe_buy_price(book)
            size = _size_for_min_notional(book.min_order_size, price)

            placed_ids: list[str] = []
            try:
                for _ in range(2):
                    placed = await client.place_limit_order(
                        token_id=active_clob_token, price=price, size=size, side="BUY"
                    )
                    assert isinstance(placed, AcceptedOrder)
                    placed_ids.append(placed.order_id)

                response = await client.cancel_orders(order_ids=placed_ids)
                for order_id in placed_ids:
                    assert order_id in response.canceled
                placed_ids = []
            finally:
                for order_id in placed_ids:
                    with contextlib.suppress(Exception):
                        await client.cancel_order(order_id=order_id)

    asyncio.run(run())


@pytest.mark.integration
@pytest.mark.metered
def test_cancel_market_orders_filters_by_token_id(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    async def run() -> None:
        async with _secure_client(require_env) as client:
            book = await client.get_order_book(token_id=active_clob_token)
            price = _safe_buy_price(book)
            size = _size_for_min_notional(book.min_order_size, price)

            placed_id: str | None = None
            try:
                placed = await client.place_limit_order(
                    token_id=active_clob_token, price=price, size=size, side="BUY"
                )
                assert isinstance(placed, AcceptedOrder)
                placed_id = placed.order_id

                response = await client.cancel_market_orders(token_id=active_clob_token)
                assert placed_id in response.canceled
                placed_id = None
            finally:
                if placed_id is not None:
                    with contextlib.suppress(Exception):
                        await client.cancel_order(order_id=placed_id)

    asyncio.run(run())


@pytest.mark.integration
@pytest.mark.metered
def test_cancel_all_removes_all_open_orders(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    async def run() -> None:
        async with _secure_client(require_env) as client:
            existing = await client.list_open_orders().first_page()
            if existing.items:
                pytest.skip(
                    "wallet has open orders not placed by this test; "
                    "skipping cancel_all to avoid destructive cleanup of unrelated state"
                )

            book = await client.get_order_book(token_id=active_clob_token)
            price = _safe_buy_price(book)
            size = _size_for_min_notional(book.min_order_size, price)

            placed_id: str | None = None
            try:
                placed = await client.place_limit_order(
                    token_id=active_clob_token, price=price, size=size, side="BUY"
                )
                assert isinstance(placed, AcceptedOrder)
                placed_id = placed.order_id

                response = await client.cancel_all()
                assert placed_id in response.canceled
                placed_id = None

                assert await _wait_for_open_orders_empty(client), (
                    "cancel_all did not clear open orders within the polling window"
                )
            finally:
                if placed_id is not None:
                    with contextlib.suppress(Exception):
                        await client.cancel_order(order_id=placed_id)

    asyncio.run(run())
