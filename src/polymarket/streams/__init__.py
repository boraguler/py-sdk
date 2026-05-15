"""Public types for Polymarket realtime stream consumers."""

from polymarket._internal.streams.handle import SubscriptionHandle
from polymarket.models.clob.market_events import (
    MarketBestBidAskEvent,
    MarketBookEvent,
    MarketEvent,
    MarketEventMessage,
    MarketLastTradePriceEvent,
    MarketPriceChangeEvent,
    MarketResolvedEvent,
    MarketTickSizeChangeEvent,
    NewMarketEvent,
    PriceChange,
)
from polymarket.streams._specs import MarketSpec, Subscription

StreamEvent = MarketEvent

__all__ = [
    "MarketBestBidAskEvent",
    "MarketBookEvent",
    "MarketEvent",
    "MarketEventMessage",
    "MarketLastTradePriceEvent",
    "MarketPriceChangeEvent",
    "MarketResolvedEvent",
    "MarketSpec",
    "MarketTickSizeChangeEvent",
    "NewMarketEvent",
    "PriceChange",
    "StreamEvent",
    "Subscription",
    "SubscriptionHandle",
]
