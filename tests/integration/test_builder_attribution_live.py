import asyncio
import contextlib
import os
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from decimal import Decimal

import pytest

from polymarket import ApiKeyCreds, AsyncSecureClient
from polymarket.models.clob.order_response import AcceptedOrder


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
    private_key = require_env("POLYMARKET_TEST_PRIVATE_KEY")
    wallet = require_env("POLYMARKET_TEST_WALLET")
    client = await AsyncSecureClient.create(
        private_key=private_key,
        wallet=wallet,
        credentials=_existing_credentials(),
    )
    try:
        yield client
    finally:
        await client.close()


@pytest.mark.integration
@pytest.mark.metered
def test_get_builder_fee_rates_against_live_clob(
    require_env: Callable[[str], str],
) -> None:
    builder_code = require_env("POLYMARKET_BUILDER_CODE")

    async def run() -> tuple[Decimal, Decimal]:
        async with _secure_client(require_env) as client:
            rates = await client.get_builder_fee_rates(builder_code)
            return rates.maker, rates.taker

    maker, taker = asyncio.run(run())
    assert maker >= Decimal(0)
    assert taker >= Decimal(0)
    assert maker < Decimal(1)
    assert taker < Decimal(1)


@pytest.mark.integration
@pytest.mark.metered
def test_place_limit_order_with_builder_code_round_trips(
    require_env: Callable[[str], str],
    active_clob_token: str,
) -> None:
    builder_code = require_env("POLYMARKET_BUILDER_CODE")

    async def run() -> None:
        async with _secure_client(require_env) as client:
            book = await client.get_order_book(token_id=active_clob_token)
            assert book.asks, "active token must have at least one resting ask"

            best_ask = book.asks[-1].price
            tick = book.tick_size or Decimal("0.01")
            price = (best_ask - tick * Decimal(5)).quantize(tick)
            if price <= tick:
                price = tick
            size = (book.min_order_size or Decimal(5)) / price
            size = size.quantize(Decimal("1"))

            placed_id: str | None = None
            try:
                placed = await client.place_limit_order(
                    token_id=active_clob_token,
                    price=price,
                    size=size,
                    side="BUY",
                    builder_code=builder_code,
                )
                assert isinstance(placed, AcceptedOrder)
                placed_id = placed.order_id
            finally:
                if placed_id is not None:
                    with contextlib.suppress(Exception):
                        await client.cancel_order(order_id=placed_id)

    asyncio.run(run())
