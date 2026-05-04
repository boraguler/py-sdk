import asyncio

import pytest

from polymarket import AsyncPublicClient, Market, PublicClient


@pytest.mark.integration
def test_get_market_returns_canonical_market() -> None:
    client = PublicClient()

    market = client.get_market("540816")

    assert isinstance(market, Market)
    assert market.id == "540816"
    assert market.condition_id.startswith("0x")
    assert market.question
    assert market.outcomes
    assert market.outcome_prices


@pytest.mark.integration
def test_async_get_market_returns_canonical_market() -> None:
    client = AsyncPublicClient()

    market = asyncio.run(client.get_market("540816"))

    assert isinstance(market, Market)
    assert market.id == "540816"
    assert market.condition_id.startswith("0x")
    assert market.question
    assert market.outcomes
    assert market.outcome_prices
