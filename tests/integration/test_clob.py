import asyncio
from decimal import Decimal

import pytest

from polymarket import AsyncPublicClient, AsyncSecureClient

PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

_PAGES_TO_SCAN = 5


async def _find_active_clob_token() -> str:
    async with AsyncPublicClient() as client:
        paginator = client.list_markets(closed=False, page_size=20)
        pages_seen = 0
        async for page in paginator:
            pages_seen += 1
            for market in page.items:
                if not market.state.enable_order_book:
                    continue
                if not market.state.accepting_orders:
                    continue
                token_id = market.outcomes.yes.token_id
                if token_id is None:
                    continue
                return token_id
            if pages_seen >= _PAGES_TO_SCAN:
                break

    pytest.skip("no CLOB-active market with a Yes-outcome token id found")


@pytest.mark.integration
def test_async_public_get_midpoint_returns_decimal_in_unit_range() -> None:
    async def run() -> Decimal:
        token_id = await _find_active_clob_token()
        async with AsyncPublicClient() as client:
            return await client.get_midpoint(token_id=token_id)

    midpoint = asyncio.run(run())

    assert isinstance(midpoint, Decimal)
    assert Decimal("0") <= midpoint <= Decimal("1")


@pytest.mark.integration
def test_async_secure_get_midpoint_returns_decimal_in_unit_range() -> None:
    async def run() -> Decimal:
        token_id = await _find_active_clob_token()
        client = await AsyncSecureClient.create(private_key=PRIVATE_KEY)
        try:
            return await client.get_midpoint(token_id=token_id)
        finally:
            await client.close()

    midpoint = asyncio.run(run())

    assert isinstance(midpoint, Decimal)
    assert Decimal("0") <= midpoint <= Decimal("1")
