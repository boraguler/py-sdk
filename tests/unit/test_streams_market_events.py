from typing import Any

import pytest
from pydantic import ValidationError

from polymarket.models.clob.market_events import (
    MarketBestBidAskEvent,
    MarketBookEvent,
    MarketLastTradePriceEvent,
    MarketPriceChangeEvent,
    MarketResolvedEvent,
    MarketTickSizeChangeEvent,
    NewMarketEvent,
    market_event_adapter,
)

_ADAPTER = market_event_adapter()

_BOOK: dict[str, Any] = {
    "event_type": "book",
    "market": "0xmarket",
    "asset_id": "token-a",
    "bids": [{"price": "0.49", "size": "100"}],
    "asks": [{"price": "0.51", "size": "100"}],
    "hash": None,
    "timestamp": "1710000000000",
}

_PRICE_CHANGE: dict[str, Any] = {
    "event_type": "price_change",
    "market": "0xmarket",
    "price_changes": [
        {
            "asset_id": "token-a",
            "price": "0.50",
            "size": "10",
            "side": "BUY",
            "best_bid": "0.49",
            "best_ask": "0.51",
        }
    ],
    "timestamp": "1710000000000",
}

_LAST_TRADE: dict[str, Any] = {
    "event_type": "last_trade_price",
    "market": "0xmarket",
    "asset_id": "token-a",
    "price": "0.50",
    "size": "5",
    "side": "SELL",
    "fee_rate_bps": "0.05",
    "timestamp": "1710000000000",
    "transaction_hash": "0xhash",
}

_TICK: dict[str, Any] = {
    "event_type": "tick_size_change",
    "market": "0xmarket",
    "asset_id": "token-a",
    "old_tick_size": "0.01",
    "new_tick_size": "0.001",
    "timestamp": "1710000000000",
}

_BBA: dict[str, Any] = {
    "event_type": "best_bid_ask",
    "market": "0xmarket",
    "asset_id": "token-a",
    "best_bid": "0.49",
    "best_ask": "0.51",
    "spread": "0.02",
    "timestamp": "1710000000000",
}

_NEW_MARKET: dict[str, Any] = {
    "event_type": "new_market",
    "id": "evt-1",
    "market": "0xmarket",
    "question": "Will X happen?",
    "assets_ids": ["token-a", "token-b"],
    "active": True,
    "timestamp": "1710000000000",
}

_RESOLVED: dict[str, Any] = {
    "event_type": "market_resolved",
    "id": "evt-1",
    "market": "0xmarket",
    "assets_ids": ["token-a", "token-b"],
    "winning_asset_id": "token-a",
    "winning_outcome": "Yes",
    "timestamp": "1710000000000",
}


def test_book_event_parses_with_asset_id_aliased_to_token_id() -> None:
    event = _ADAPTER.validate_python(_BOOK)
    assert isinstance(event, MarketBookEvent)
    assert event.token_id == "token-a"
    assert event.market == "0xmarket"
    assert len(event.bids) == 1
    assert event.bids[0].price == event.bids[0].price  # smoke


def test_price_change_event_parses_nested_changes() -> None:
    event = _ADAPTER.validate_python(_PRICE_CHANGE)
    assert isinstance(event, MarketPriceChangeEvent)
    assert len(event.price_changes) == 1
    assert event.price_changes[0].token_id == "token-a"
    assert event.price_changes[0].side == "BUY"


def test_last_trade_price_event_parses() -> None:
    event = _ADAPTER.validate_python(_LAST_TRADE)
    assert isinstance(event, MarketLastTradePriceEvent)
    assert event.token_id == "token-a"
    assert event.transaction_hash == "0xhash"


def test_tick_size_change_event_parses() -> None:
    event = _ADAPTER.validate_python(_TICK)
    assert isinstance(event, MarketTickSizeChangeEvent)
    assert event.token_id == "token-a"


def test_best_bid_ask_event_parses() -> None:
    event = _ADAPTER.validate_python(_BBA)
    assert isinstance(event, MarketBestBidAskEvent)
    assert event.token_id == "token-a"
    assert event.spread is not None


def test_new_market_event_parses_with_assets_ids_aliased() -> None:
    event = _ADAPTER.validate_python(_NEW_MARKET)
    assert isinstance(event, NewMarketEvent)
    assert event.token_ids == ("token-a", "token-b")
    assert event.active is True


def test_market_resolved_event_parses_winning_asset_id_alias() -> None:
    event = _ADAPTER.validate_python(_RESOLVED)
    assert isinstance(event, MarketResolvedEvent)
    assert event.winning_token_id == "token-a"
    assert event.token_ids == ("token-a", "token-b")


def test_discriminator_rejects_unknown_event_type() -> None:
    with pytest.raises(ValidationError):
        _ADAPTER.validate_python({"event_type": "unknown_event", "market": "x"})


def test_missing_required_field_raises() -> None:
    payload = dict(_BOOK)
    del payload["asset_id"]
    with pytest.raises(ValidationError):
        _ADAPTER.validate_python(payload)


def test_order_side_normalized_to_uppercase() -> None:
    payload = dict(_LAST_TRADE) | {"side": "sell"}
    event = _ADAPTER.validate_python(payload)
    assert isinstance(event, MarketLastTradePriceEvent)
    assert event.side == "SELL"


def test_order_side_normalized_in_nested_price_change() -> None:
    payload: dict[str, Any] = {
        **_PRICE_CHANGE,
        "price_changes": [
            {
                "asset_id": "token-a",
                "price": "0.5",
                "size": "10",
                "side": "buy",
            }
        ],
    }
    event = _ADAPTER.validate_python(payload)
    assert isinstance(event, MarketPriceChangeEvent)
    assert event.price_changes[0].side == "BUY"


def test_timestamp_parsed_to_utc_datetime() -> None:
    from datetime import UTC, datetime

    event = _ADAPTER.validate_python(_BOOK)
    assert isinstance(event, MarketBookEvent)
    assert event.timestamp == datetime.fromtimestamp(1710000000, tz=UTC)
    assert event.timestamp is not None
    assert event.timestamp.tzinfo is UTC


def test_empty_string_timestamp_normalized_to_none() -> None:
    payload = dict(_BOOK) | {"timestamp": ""}
    event = _ADAPTER.validate_python(payload)
    assert isinstance(event, MarketBookEvent)
    assert event.timestamp is None


def test_invalid_timestamp_raises_validation_error() -> None:
    payload = dict(_BOOK) | {"timestamp": "not-a-number"}
    with pytest.raises(ValidationError):
        _ADAPTER.validate_python(payload)


@pytest.mark.parametrize(
    "bad_value",
    [
        "-1710000000000",  # negative
        "+1710000000000",  # signed
        " 1710000000000",  # leading whitespace
        "1710000000000 ",  # trailing whitespace
        "1.7e12",  # scientific
        "1710000000000.0",  # decimal
        "0x123",  # hex
    ],
)
def test_loose_numeric_strings_rejected_as_epoch_ms(bad_value: str) -> None:
    payload = dict(_BOOK) | {"timestamp": bad_value}
    with pytest.raises(ValidationError):
        _ADAPTER.validate_python(payload)


def test_new_market_game_start_time_parsed_to_datetime() -> None:
    from datetime import UTC, datetime

    payload = dict(_NEW_MARKET) | {"game_start_time": "1710000000000"}
    event = _ADAPTER.validate_python(payload)
    assert isinstance(event, NewMarketEvent)
    assert event.game_start_time == datetime.fromtimestamp(1710000000, tz=UTC)
