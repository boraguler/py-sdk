from typing import Annotated, Any, Literal, cast

from pydantic import AliasChoices, BeforeValidator, Field, TypeAdapter, ValidationError

from polymarket.models.base import BaseModel
from polymarket.models.clob._validators import (
    DecimalishString,
    EpochSecondsOrMsTimestamp,
    EpochSecondsTimestamp,
    ExpirationTimestamp,
)
from polymarket.models.types import TokenId


def _uppercase_string(value: object) -> object:
    return value.upper() if isinstance(value, str) else value


_OrderSide = Annotated[Literal["BUY", "SELL"], BeforeValidator(_uppercase_string)]


_OrderEventType = Literal["PLACEMENT", "UPDATE", "CANCELLATION"]


_OrderStatus = Literal["LIVE", "MATCHED", "DELAYED", "UNMATCHED", "CANCELED"]


_OrderType = Literal["GTC", "FOK", "IOC", "GTD", "FAK"]


_TraderSide = Annotated[Literal["TAKER", "MAKER"], BeforeValidator(_uppercase_string)]


_TradeStatus = Literal[
    "MATCHED",
    "MATCHED_NOT_BROADCASTED",
    "MINED",
    "CONFIRMED",
    "RETRYING",
    "FAILED",
]


def _normalize_trade_status(value: object) -> object:
    if isinstance(value, str) and value.startswith("TRADE_STATUS_"):
        return value[len("TRADE_STATUS_") :]
    return value


_TradeStatusValidator = Annotated[_TradeStatus, BeforeValidator(_normalize_trade_status)]


class UserOrderPayload(BaseModel):
    id: str
    owner: str
    market: str
    token_id: TokenId = Field(validation_alias="asset_id")
    side: _OrderSide
    original_size: DecimalishString
    size_matched: DecimalishString
    price: DecimalishString
    order_event_type: _OrderEventType = Field(validation_alias="type")
    timestamp: EpochSecondsOrMsTimestamp = None
    created_at: EpochSecondsTimestamp = None
    expiration: ExpirationTimestamp = None
    order_type: _OrderType | None = None
    status: _OrderStatus | None = None
    maker_address: str | None = None
    order_owner: str | None = None
    associate_trades: tuple[str, ...] | None = None
    outcome: str | None = None


class UserTradeMakerOrder(BaseModel):
    order_id: str
    owner: str
    maker_address: str | None = None
    matched_amount: DecimalishString
    price: DecimalishString
    fee_rate_bps: DecimalishString | None = None
    token_id: TokenId = Field(validation_alias="asset_id")
    side: _OrderSide
    outcome: str | None = None
    outcome_index: int | None = None


class UserTradePayload(BaseModel):
    id: str
    taker_order_id: str
    market: str
    token_id: TokenId = Field(validation_alias="asset_id")
    side: _OrderSide
    size: DecimalishString
    price: DecimalishString
    status: _TradeStatusValidator
    owner: str
    timestamp: EpochSecondsOrMsTimestamp = None
    fee_rate_bps: DecimalishString | None = None
    match_time: EpochSecondsTimestamp = Field(
        default=None, validation_alias=AliasChoices("match_time", "matchtime")
    )
    last_update: EpochSecondsTimestamp = None
    trade_owner: str | None = None
    maker_address: str | None = None
    transaction_hash: str | None = None
    bucket_index: int | None = None
    maker_orders: tuple[UserTradeMakerOrder, ...] | None = None
    trader_side: _TraderSide | None = None
    outcome: str | None = None


class UserOrderEvent(BaseModel):
    topic: Literal["user"] = "user"
    type: Literal["order"]
    payload: UserOrderPayload


class UserTradeEvent(BaseModel):
    topic: Literal["user"] = "user"
    type: Literal["trade"]
    payload: UserTradePayload


UserEvent = Annotated[UserOrderEvent | UserTradeEvent, Field(discriminator="type")]


_USER_EVENT_ADAPTER: TypeAdapter[UserEvent] = TypeAdapter(UserEvent)


def _normalize_to_envelope(raw: object) -> Any:
    if not isinstance(raw, dict):
        return raw
    wire = cast(dict[str, Any], raw)
    if "type" in wire and "payload" in wire and "topic" in wire:
        return wire
    event_type = wire.get("event_type")
    if event_type is None:
        raise ValueError("user event missing event_type")
    return {
        "topic": "user",
        "type": event_type,
        "payload": {k: v for k, v in wire.items() if k not in ("event_type", "topic")},
    }


def parse_user_event(raw: object) -> UserEvent:
    return _USER_EVENT_ADAPTER.validate_python(_normalize_to_envelope(raw))


def parse_user_events(raw: object) -> tuple[list[UserEvent], int]:
    items: list[object] = list(cast(list[object], raw)) if isinstance(raw, list) else [raw]
    parsed: list[UserEvent] = []
    dropped = 0
    for item in items:
        try:
            parsed.append(parse_user_event(item))
        except (ValueError, ValidationError):
            dropped += 1
    return parsed, dropped


__all__ = [
    "UserEvent",
    "UserOrderEvent",
    "UserOrderPayload",
    "UserTradeEvent",
    "UserTradeMakerOrder",
    "UserTradePayload",
    "parse_user_event",
    "parse_user_events",
]
