from typing import Any

import pytest

from polymarket.models.rtds_events import (
    CommentCreatedEvent,
    CryptoPricesBinanceEvent,
    CryptoPricesChainlinkEvent,
    EquityPricesSubscribeEvent,
    EquityPricesUpdateEvent,
    ReactionCreatedEvent,
    api_topic_to_wire,
    parse_rtds_event,
    wire_topic_to_api,
)

_COMMENT_CREATED: dict[str, Any] = {
    "topic": "comments",
    "type": "comment_created",
    "timestamp": "1710000000000",
    "payload": {
        "id": "42",
        "body": "hi",
        "parentEntityType": "Event",
        "parentEntityID": 123,
        "userAddress": "0xabc",
        "createdAt": "2024-03-09T00:00:00Z",
    },
}

_REACTION_CREATED: dict[str, Any] = {
    "topic": "comments",
    "type": "reaction_created",
    "timestamp": "1710000000000",
    "payload": {
        "id": "7",
        "commentID": 42,
        "reactionType": "like",
        "userAddress": "0xdef",
    },
}

_CRYPTO_BINANCE: dict[str, Any] = {
    "topic": "crypto_prices",
    "type": "update",
    "timestamp": "1710000000000",
    "payload": {"symbol": "btcusdt", "timestamp": 1710000000000, "value": "65000.5"},
}

_CRYPTO_CHAINLINK: dict[str, Any] = {
    "topic": "crypto_prices_chainlink",
    "type": "update",
    "timestamp": "1710000000000",
    "payload": {"symbol": "ETH/USD", "timestamp": 1710000000000, "value": "3500.25"},
}

_EQUITY_UPDATE: dict[str, Any] = {
    "topic": "equity_prices",
    "type": "update",
    "timestamp": "1710000000000",
    "payload": {
        "symbol": "AAPL",
        "value": "180.42",
        "timestamp": 1710000000000,
        "received_at": 1710000000050,
        "is_carried_forward": False,
    },
}

_EQUITY_SUBSCRIBE: dict[str, Any] = {
    "topic": "equity_prices",
    "type": "subscribe",
    "timestamp": "1710000000000",
    "payload": {
        "symbol": "AAPL",
        "data": [
            {"timestamp": 1710000000000, "value": "180.00"},
            {"timestamp": 1710000060000, "value": "180.42"},
        ],
    },
}


def test_wire_to_api_topic_mapping() -> None:
    assert wire_topic_to_api("comments") == "comments"
    assert wire_topic_to_api("crypto_prices") == "prices.crypto.binance"
    assert wire_topic_to_api("crypto_prices_chainlink") == "prices.crypto.chainlink"
    assert wire_topic_to_api("equity_prices") == "prices.equity.pyth"
    assert wire_topic_to_api("unknown") is None


def test_api_to_wire_topic_mapping() -> None:
    assert api_topic_to_wire("comments") == "comments"
    assert api_topic_to_wire("prices.crypto.binance") == "crypto_prices"
    assert api_topic_to_wire("prices.crypto.chainlink") == "crypto_prices_chainlink"
    assert api_topic_to_wire("prices.equity.pyth") == "equity_prices"


def test_comment_created_parses_with_camelcase_aliases() -> None:
    event = parse_rtds_event(_COMMENT_CREATED)
    assert isinstance(event, CommentCreatedEvent)
    assert event.topic == "comments"
    assert event.type == "comment_created"
    assert event.payload.id == "42"
    assert event.payload.parent_entity_type == "Event"
    assert event.payload.parent_entity_id == "123"
    assert event.payload.user_address == "0xabc"


def test_reaction_created_parses() -> None:
    event = parse_rtds_event(_REACTION_CREATED)
    assert isinstance(event, ReactionCreatedEvent)
    assert event.payload.comment_id == 42
    assert event.payload.reaction_type == "like"


def test_crypto_binance_wire_topic_remapped_to_api_topic() -> None:
    event = parse_rtds_event(_CRYPTO_BINANCE)
    assert isinstance(event, CryptoPricesBinanceEvent)
    assert event.topic == "prices.crypto.binance"
    assert event.payload.symbol == "btcusdt"


def test_crypto_chainlink_wire_topic_remapped_to_api_topic() -> None:
    event = parse_rtds_event(_CRYPTO_CHAINLINK)
    assert isinstance(event, CryptoPricesChainlinkEvent)
    assert event.topic == "prices.crypto.chainlink"
    assert event.payload.symbol == "ETH/USD"


def test_equity_update_parses_with_aliases() -> None:
    event = parse_rtds_event(_EQUITY_UPDATE)
    assert isinstance(event, EquityPricesUpdateEvent)
    assert event.topic == "prices.equity.pyth"
    assert event.payload.symbol == "AAPL"
    assert event.payload.received_at == 1710000000050
    assert event.payload.is_carried_forward is False


def test_equity_update_prefers_full_accuracy_value_when_present() -> None:
    from decimal import Decimal

    event = parse_rtds_event(
        {
            "topic": "equity_prices",
            "type": "update",
            "timestamp": "1710000000000",
            "payload": {
                "symbol": "AAPL",
                "value": 180.42,
                "full_accuracy_value": "180.42178100000",
                "timestamp": 1710000000000,
            },
        }
    )
    assert isinstance(event, EquityPricesUpdateEvent)
    assert event.payload.value == Decimal("180.42178100000")


def test_equity_update_falls_back_to_value_when_full_accuracy_missing() -> None:
    from decimal import Decimal

    event = parse_rtds_event(_EQUITY_UPDATE)
    assert isinstance(event, EquityPricesUpdateEvent)
    assert event.payload.value == Decimal("180.42")


def test_equity_subscribe_parses_snapshot_data() -> None:
    event = parse_rtds_event(_EQUITY_SUBSCRIBE)
    assert isinstance(event, EquityPricesSubscribeEvent)
    assert event.topic == "prices.equity.pyth"
    assert event.payload.symbol == "AAPL"
    assert len(event.payload.data) == 2
    assert event.payload.data[0].timestamp == 1710000000000


def test_unknown_wire_topic_raises() -> None:
    with pytest.raises(ValueError, match="unknown RTDS wire topic"):
        parse_rtds_event({"topic": "made_up", "type": "update", "timestamp": "1", "payload": {}})


def test_unknown_event_type_raises() -> None:
    with pytest.raises(ValueError, match="unknown RTDS event"):
        parse_rtds_event({"topic": "comments", "type": "made_up", "timestamp": "1", "payload": {}})


def test_missing_topic_raises() -> None:
    with pytest.raises(ValueError, match="missing topic"):
        parse_rtds_event({"type": "update", "payload": {}})


def test_non_dict_raises() -> None:
    with pytest.raises(ValueError, match="expected dict"):
        parse_rtds_event("not a dict")
