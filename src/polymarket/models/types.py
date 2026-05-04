"""Model-specific Polymarket domain types."""

from typing import NewType

ConditionId = NewType("ConditionId", str)
ClobRewardId = NewType("ClobRewardId", str)
EventId = NewType("EventId", str)
MarketId = NewType("MarketId", str)
OrderId = NewType("OrderId", str)
QuestionId = NewType("QuestionId", str)
ResolutionRequestId = NewType("ResolutionRequestId", str)
TagId = NewType("TagId", str)
TokenId = NewType("TokenId", str)

__all__ = [
    "ClobRewardId",
    "ConditionId",
    "EventId",
    "MarketId",
    "OrderId",
    "QuestionId",
    "ResolutionRequestId",
    "TagId",
    "TokenId",
]
