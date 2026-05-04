"""Model-specific Polymarket domain types."""

from typing import NewType

ConditionId = NewType("ConditionId", str)
EventId = NewType("EventId", str)
MarketId = NewType("MarketId", str)
OrderId = NewType("OrderId", str)
TokenId = NewType("TokenId", str)

__all__ = ["ConditionId", "EventId", "MarketId", "OrderId", "TokenId"]
