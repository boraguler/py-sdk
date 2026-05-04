import asyncio

import pytest

from polymarket import AsyncPublicClient, Market, PublicClient


@pytest.mark.integration
def test_get_market_returns_canonical_market() -> None:
    client = PublicClient()

    market = client.get_market(id="540816")

    assert isinstance(market, Market)
    assert market.id == "540816"
    assert market.outcomes.yes.label
    assert market.outcomes.no.label


@pytest.mark.integration
def test_get_market_by_slug_returns_canonical_market() -> None:
    client = PublicClient()

    market = client.get_market(slug="russia-ukraine-ceasefire-before-gta-vi-554")

    assert isinstance(market, Market)
    assert market.id == "540816"
    assert market.outcomes.yes.label
    assert market.outcomes.no.label


@pytest.mark.integration
def test_get_market_by_url_returns_canonical_market() -> None:
    client = PublicClient()

    market = client.get_market(
        url="https://polymarket.com/market/russia-ukraine-ceasefire-before-gta-vi-554"
    )

    assert isinstance(market, Market)
    assert market.id == "540816"
    assert market.outcomes.yes.label
    assert market.outcomes.no.label


@pytest.mark.integration
def test_async_get_market_returns_canonical_market() -> None:
    client = AsyncPublicClient()

    market = asyncio.run(client.get_market(id="540816"))

    assert isinstance(market, Market)
    assert market.id == "540816"
    assert market.outcomes.yes.label
    assert market.outcomes.no.label
