"""Public types for Polymarket realtime stream consumers."""

from polymarket._internal.streams.handle import AsyncSubscriptionHandle
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

MarketSubscriptionHandle = AsyncSubscriptionHandle[MarketEvent]

__all__ = [
    "AsyncSubscriptionHandle",
    "MarketBestBidAskEvent",
    "MarketBookEvent",
    "MarketEvent",
    "MarketEventMessage",
    "MarketLastTradePriceEvent",
    "MarketPriceChangeEvent",
    "MarketResolvedEvent",
    "MarketSubscriptionHandle",
    "MarketTickSizeChangeEvent",
    "NewMarketEvent",
    "PriceChange",
]
