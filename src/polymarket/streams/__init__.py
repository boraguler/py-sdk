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
from polymarket.streams._specs import MarketSpec, Subscription

StreamEvent = MarketEvent

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
    "StreamEvent",
    "Subscription",
    "SubscriptionHandle",
]
