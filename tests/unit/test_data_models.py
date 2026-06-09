from datetime import UTC, datetime
from decimal import Decimal

from polymarket.models.data import (
    BuilderVolumeEntry,
    ComboPosition,
    Holder,
    LiveVolume,
    MetaHolder,
    OpenInterest,
    PortfolioValue,
    TradedMarketCount,
)


def test_live_volume_parses_total_and_markets() -> None:
    payload = {
        "total": "12345.67",
        "markets": [
            {"market": "0xabc", "value": "100.5"},
            {"market": "0xdef", "value": 200},
        ],
    }

    volume = LiveVolume.parse_response(payload)

    assert volume.total == Decimal("12345.67")
    assert volume.markets is not None
    assert len(volume.markets) == 2
    assert volume.markets[0].market == "0xabc"
    assert volume.markets[0].value == Decimal("100.5")
    assert volume.markets[1].value == Decimal("200")


def test_live_volume_handles_missing_fields() -> None:
    volume = LiveVolume.parse_response({})

    assert volume.total is None
    assert volume.markets is None


def test_open_interest_parses_payload() -> None:
    interest = OpenInterest.parse_response({"market": "0xabc", "value": "1500"})

    assert interest.market == "0xabc"
    assert interest.value == Decimal("1500")


def test_holder_renames_proxy_wallet_and_asset() -> None:
    holder = Holder.parse_response(
        {
            "proxyWallet": "0xWALLET",
            "asset": "TOKEN_123",
            "amount": "42.5",
            "outcomeIndex": 1,
            "name": "Alice",
            "displayUsernamePublic": True,
        }
    )

    assert holder.wallet == "0xWALLET"
    assert holder.token_id == "TOKEN_123"
    assert holder.amount == Decimal("42.5")
    assert holder.outcome_index == 1
    assert holder.name == "Alice"
    assert holder.display_username_public is True


def test_meta_holder_nests_holders() -> None:
    payload = {
        "token": "TOKEN_123",
        "holders": [
            {"proxyWallet": "0xA", "asset": "TOKEN_123", "amount": "1"},
            {"proxyWallet": "0xB", "asset": "TOKEN_123", "amount": "2"},
        ],
    }

    meta = MetaHolder.parse_response(payload)

    assert meta.token == "TOKEN_123"
    assert meta.holders is not None
    assert len(meta.holders) == 2
    assert meta.holders[0].wallet == "0xA"


def test_portfolio_value_parses_user_and_value() -> None:
    value = PortfolioValue.parse_response({"user": "0xWALLET", "value": "9876.54"})

    assert value.user == "0xWALLET"
    assert value.value == Decimal("9876.54")


def test_traded_market_count_parses_payload() -> None:
    count = TradedMarketCount.parse_response({"user": "0xWALLET", "traded": 42})

    assert count.user == "0xWALLET"
    assert count.traded == 42


def test_builder_volume_entry_renames_dt_to_bucket_at() -> None:
    entry = BuilderVolumeEntry.parse_response(
        {
            "dt": "2026-05-08T00:00:00Z",
            "builder": "polymarket",
            "builderLogo": "https://example.test/logo.png",
            "verified": True,
            "volume": "1000.5",
            "activeUsers": 25,
            "rank": "1",
        }
    )

    assert entry.bucket_at == datetime(2026, 5, 8, tzinfo=UTC)
    assert entry.builder == "polymarket"
    assert entry.builder_logo == "https://example.test/logo.png"
    assert entry.verified is True
    assert entry.volume == Decimal("1000.5")
    assert entry.active_users == 25
    assert entry.rank == "1"


def test_builder_volume_entry_handles_missing_fields() -> None:
    entry = BuilderVolumeEntry.parse_response({})

    assert entry.bucket_at is None
    assert entry.builder is None
    assert entry.volume is None


def test_combo_position_parses_payload() -> None:
    payload = {
        "combo_condition_id": "0x032def24bfb0c5c57fb236fac08b94236a0000000000000000000000000000",
        "combo_position_id": "123",
        "module_id": 3,
        "user_address": "0x0000000000000000000000000000000000000001",
        "shares_balance": "42.5",
        "entry_avg_price_usdc": "0.12",
        "entry_cost_usdc": "5.1",
        "status": "OPEN",
        "first_entry_at": "2026-06-01T12:00:00Z",
        "resolved_at": None,
        "legs_total": 2,
        "legs_resolved": 1,
        "legs_pending": 1,
        "legs": [
            {
                "leg_index": 0,
                "leg_position_id": "456",
                "leg_condition_id": (
                    "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
                ),
                "leg_outcome_index": 1,
                "leg_outcome_label": "Yes",
                "leg_status": "PARTIAL",
                "leg_resolved_at": None,
                "leg_current_price": "0.77",
                "market": {
                    "market_id": "789",
                    "slug": "market-slug",
                    "title": "Market title",
                    "outcome": "Yes",
                    "image_url": "https://example.test/image.png",
                    "icon_url": "https://example.test/icon.png",
                    "category": "Politics",
                    "subcategory": None,
                    "tags": ["a", "b"],
                    "end_date": "2026-07-01T00:00:00Z",
                    "event": {
                        "event_id": "event-1",
                        "event_slug": "event-slug",
                        "event_title": "Event title",
                        "event_image": "https://example.test/event.png",
                    },
                },
            }
        ],
    }

    combo = ComboPosition.parse_response(payload)

    assert combo.condition_id == payload["combo_condition_id"]
    assert combo.position_id == "123"
    assert combo.shares == Decimal("42.5")
    assert combo.status == "OPEN"
    assert combo.legs[0].leg_position_id == "456"
    assert combo.legs[0].leg_current_price == Decimal("0.77")
    assert combo.legs[0].market is not None
    assert combo.legs[0].market.market_id == "789"
    assert combo.legs[0].market.event is not None
    assert combo.legs[0].market.event.event_slug == "event-slug"
