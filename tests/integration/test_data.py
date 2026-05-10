import asyncio
from decimal import Decimal

import pytest

from polymarket import (
    AsyncPublicClient,
    BuilderVolumeEntry,
    LiveVolume,
    MetaHolder,
    OpenInterest,
    PortfolioValue,
    PublicClient,
    TradedMarketCount,
)

EVENT_ID = "902661"

WALLET = "0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b"


def _condition_ids_for_event() -> list[str]:
    with PublicClient() as client:
        event = client.get_event(id=EVENT_ID)
    return [m.condition_id for m in event.markets if m.condition_id is not None]


@pytest.mark.integration
def test_get_event_live_volumes_returns_volume() -> None:
    with PublicClient() as client:
        volumes = client.get_event_live_volumes(id=EVENT_ID)

    assert volumes
    assert all(isinstance(v, LiveVolume) for v in volumes)
    assert volumes[0].total is not None
    assert isinstance(volumes[0].total, Decimal)
    assert volumes[0].markets is not None


@pytest.mark.integration
def test_get_open_interests_with_market_filter() -> None:
    condition_ids = _condition_ids_for_event()
    if not condition_ids:
        pytest.skip("event has no condition IDs to query")

    with PublicClient() as client:
        interests = client.get_open_interests(market=condition_ids)

    assert interests
    assert all(isinstance(oi, OpenInterest) for oi in interests)
    assert all(oi.market in condition_ids for oi in interests if oi.market is not None)
    assert all(isinstance(oi.value, Decimal) for oi in interests if oi.value is not None)


@pytest.mark.integration
def test_get_open_interests_without_filter() -> None:
    with PublicClient() as client:
        interests = client.get_open_interests()

    assert all(isinstance(oi, OpenInterest) for oi in interests)


@pytest.mark.integration
def test_get_market_holders_returns_holders() -> None:
    condition_ids = _condition_ids_for_event()
    if not condition_ids:
        pytest.skip("event has no condition IDs to query")

    with PublicClient() as client:
        holders = client.get_market_holders(market=condition_ids[:1], limit=5)

    assert holders
    assert all(isinstance(meta, MetaHolder) for meta in holders)
    assert holders[0].token is not None
    assert holders[0].holders is not None


@pytest.mark.integration
def test_get_portfolio_values_returns_values() -> None:
    with PublicClient() as client:
        values = client.get_portfolio_values(user=WALLET)

    assert values
    assert all(isinstance(v, PortfolioValue) for v in values)
    assert values[0].user == WALLET
    assert values[0].value is not None
    assert isinstance(values[0].value, Decimal)


@pytest.mark.integration
def test_get_traded_market_count_returns_count() -> None:
    with PublicClient() as client:
        count = client.get_traded_market_count(user=WALLET)

    assert isinstance(count, TradedMarketCount)
    assert count.user == WALLET
    assert count.traded is not None
    assert count.traded >= 0


@pytest.mark.integration
def test_get_builder_volumes_returns_entries() -> None:
    with PublicClient() as client:
        volumes = client.get_builder_volumes(time_period="DAY")

    assert volumes
    assert all(isinstance(entry, BuilderVolumeEntry) for entry in volumes)
    assert any(entry.builder is not None for entry in volumes)
    assert any(entry.bucket_at is not None for entry in volumes)
    assert any(isinstance(entry.volume, Decimal) for entry in volumes if entry.volume is not None)


@pytest.mark.integration
def test_async_get_event_live_volumes_returns_volume() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            volumes = await client.get_event_live_volumes(id=EVENT_ID)
        assert volumes
        assert all(isinstance(v, LiveVolume) for v in volumes)
        assert volumes[0].total is not None

    asyncio.run(run())


@pytest.mark.integration
def test_async_get_open_interests_without_filter() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            interests = await client.get_open_interests()
        assert all(isinstance(oi, OpenInterest) for oi in interests)

    asyncio.run(run())


@pytest.mark.integration
def test_async_get_market_holders_returns_holders() -> None:
    condition_ids = _condition_ids_for_event()
    if not condition_ids:
        pytest.skip("event has no condition IDs to query")

    async def run() -> None:
        async with AsyncPublicClient() as client:
            holders = await client.get_market_holders(market=condition_ids[:1], limit=5)
        assert holders
        assert all(isinstance(meta, MetaHolder) for meta in holders)
        assert holders[0].token is not None

    asyncio.run(run())


@pytest.mark.integration
def test_async_get_portfolio_values_returns_values() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            values = await client.get_portfolio_values(user=WALLET)
        assert values
        assert all(isinstance(v, PortfolioValue) for v in values)
        assert values[0].user == WALLET

    asyncio.run(run())


@pytest.mark.integration
def test_async_get_traded_market_count_returns_count() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            count = await client.get_traded_market_count(user=WALLET)
        assert isinstance(count, TradedMarketCount)
        assert count.user == WALLET
        assert count.traded is not None and count.traded >= 0

    asyncio.run(run())


@pytest.mark.integration
def test_download_accounting_snapshot_returns_zip_archive() -> None:
    with PublicClient() as client:
        snapshot = client.download_accounting_snapshot(user=WALLET)

    assert isinstance(snapshot, bytes)
    assert len(snapshot) > 0
    assert snapshot.startswith(b"PK\x03\x04")


@pytest.mark.integration
def test_async_download_accounting_snapshot_returns_zip_archive() -> None:
    async def run() -> bytes:
        async with AsyncPublicClient() as client:
            return await client.download_accounting_snapshot(user=WALLET)

    snapshot = asyncio.run(run())
    assert isinstance(snapshot, bytes)
    assert len(snapshot) > 0
    assert snapshot.startswith(b"PK\x03\x04")


@pytest.mark.integration
def test_async_get_builder_volumes_returns_entries() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            volumes = await client.get_builder_volumes(time_period="DAY")
        assert volumes
        assert all(isinstance(entry, BuilderVolumeEntry) for entry in volumes)
        assert any(entry.builder is not None for entry in volumes)

    asyncio.run(run())
