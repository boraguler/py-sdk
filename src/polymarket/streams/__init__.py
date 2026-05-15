"""Public types for Polymarket realtime stream consumers."""

from polymarket._internal.streams.handle import SubscriptionHandle
from polymarket.models.clob.market_events import (
    MarketBestBidAskEvent,
    MarketBestBidAskPayload,
    MarketBookEvent,
    MarketBookPayload,
    MarketEvent,
    MarketEventMessage,
    MarketLastTradePriceEvent,
    MarketLastTradePricePayload,
    MarketPriceChangeEvent,
    MarketPriceChangePayload,
    MarketResolvedEvent,
    MarketResolvedPayload,
    MarketTickSizeChangeEvent,
    MarketTickSizeChangePayload,
    NewMarketEvent,
    NewMarketPayload,
    PriceChange,
)
from polymarket.models.sports_events import (
    SportsEvent,
    SportsGameResult,
    SportsResultEvent,
)
from polymarket.streams._specs import MarketSpec, SportsSpec, Subscription

StreamEvent = MarketEvent | SportsEvent

__all__ = [
    "MarketBestBidAskEvent",
    "MarketBestBidAskPayload",
    "MarketBookEvent",
    "MarketBookPayload",
    "MarketEvent",
    "MarketEventMessage",
    "MarketLastTradePriceEvent",
    "MarketLastTradePricePayload",
    "MarketPriceChangeEvent",
    "MarketPriceChangePayload",
    "MarketResolvedEvent",
    "MarketResolvedPayload",
    "MarketSpec",
    "MarketTickSizeChangeEvent",
    "MarketTickSizeChangePayload",
    "NewMarketEvent",
    "NewMarketPayload",
    "PriceChange",
    "SportsEvent",
    "SportsGameResult",
    "SportsResultEvent",
    "SportsSpec",
    "StreamEvent",
    "Subscription",
    "SubscriptionHandle",
]
