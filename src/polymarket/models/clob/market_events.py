from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, TypeAdapter

from polymarket.models.base import BaseModel
from polymarket.models.clob._validators import DecimalishString, EpochMsTimestamp
from polymarket.models.clob.order_book import OrderBookLevel
from polymarket.models.types import ConditionId, TokenId


def _uppercase_order_side(value: object) -> object:
    return value.upper() if isinstance(value, str) else value


_OrderSide = Annotated[Literal["BUY", "SELL"], BeforeValidator(_uppercase_order_side)]


class MarketEventMessage(BaseModel):
    id: str
    ticker: str | None = None
    slug: str | None = None
    title: str | None = None
    description: str | None = None


class PriceChange(BaseModel):
    token_id: TokenId = Field(validation_alias="asset_id")
    price: DecimalishString
    size: DecimalishString
    side: _OrderSide
    hash: str | None = None
    best_bid: DecimalishString | None = None
    best_ask: DecimalishString | None = None


class MarketBookEvent(BaseModel):
    event_type: Literal["book"]
    market: str
    token_id: TokenId = Field(validation_alias="asset_id")
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    hash: str | None = None
    timestamp: EpochMsTimestamp = None
    min_order_size: DecimalishString | None = None
    tick_size: DecimalishString | None = None
    neg_risk: bool | None = None
    last_trade_price: DecimalishString | None = None


class MarketPriceChangeEvent(BaseModel):
    event_type: Literal["price_change"]
    market: str
    price_changes: tuple[PriceChange, ...]
    timestamp: EpochMsTimestamp = None


class MarketLastTradePriceEvent(BaseModel):
    event_type: Literal["last_trade_price"]
    market: str
    token_id: TokenId = Field(validation_alias="asset_id")
    price: DecimalishString
    size: DecimalishString | None = None
    side: _OrderSide
    fee_rate_bps: DecimalishString | None = None
    transaction_hash: str | None = None
    timestamp: EpochMsTimestamp = None


class MarketTickSizeChangeEvent(BaseModel):
    event_type: Literal["tick_size_change"]
    market: str
    token_id: TokenId = Field(validation_alias="asset_id")
    old_tick_size: DecimalishString | None = None
    new_tick_size: DecimalishString
    timestamp: EpochMsTimestamp = None


class MarketBestBidAskEvent(BaseModel):
    event_type: Literal["best_bid_ask"]
    market: str
    token_id: TokenId = Field(validation_alias="asset_id")
    best_bid: DecimalishString | None = None
    best_ask: DecimalishString | None = None
    spread: DecimalishString | None = None
    timestamp: EpochMsTimestamp = None


class NewMarketEvent(BaseModel):
    event_type: Literal["new_market"]
    id: str
    market: str
    question: str | None = None
    slug: str | None = None
    description: str | None = None
    token_ids: tuple[TokenId, ...] | None = Field(default=None, validation_alias="assets_ids")
    outcomes: tuple[str, ...] | None = None
    event_message: MarketEventMessage | None = None
    timestamp: EpochMsTimestamp = None
    tags: tuple[str, ...] | None = None
    condition_id: ConditionId | None = None
    active: bool | None = None
    clob_token_ids: tuple[str, ...] | None = None
    sports_market_type: str | None = None
    line: DecimalishString | None = None
    game_start_time: EpochMsTimestamp = None
    order_price_min_tick_size: DecimalishString | None = None
    group_item_title: str | None = None
    taker_base_fee: DecimalishString | None = None
    fees_enabled: bool | None = None
    fee_schedule: object | None = None


class MarketResolvedEvent(BaseModel):
    event_type: Literal["market_resolved"]
    id: str
    market: str
    token_ids: tuple[TokenId, ...] | None = Field(default=None, validation_alias="assets_ids")
    winning_token_id: TokenId | None = Field(default=None, validation_alias="winning_asset_id")
    winning_outcome: str | None = None
    event_message: MarketEventMessage | None = None
    timestamp: EpochMsTimestamp = None
    tags: tuple[str, ...] | None = None


MarketEvent = Annotated[
    MarketBookEvent
    | MarketPriceChangeEvent
    | MarketLastTradePriceEvent
    | MarketTickSizeChangeEvent
    | MarketBestBidAskEvent
    | NewMarketEvent
    | MarketResolvedEvent,
    Field(discriminator="event_type"),
]

_MARKET_EVENT_ADAPTER: TypeAdapter[MarketEvent] = TypeAdapter(MarketEvent)


def market_event_adapter() -> TypeAdapter[MarketEvent]:
    return _MARKET_EVENT_ADAPTER


__all__ = [
    "MarketBestBidAskEvent",
    "MarketBookEvent",
    "MarketEvent",
    "MarketEventMessage",
    "MarketLastTradePriceEvent",
    "MarketPriceChangeEvent",
    "MarketResolvedEvent",
    "MarketTickSizeChangeEvent",
    "NewMarketEvent",
    "PriceChange",
    "market_event_adapter",
]
