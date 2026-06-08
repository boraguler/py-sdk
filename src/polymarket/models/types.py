"""Model-specific Polymarket domain types."""

from typing import Literal, NewType, TypeAlias

OrderSide: TypeAlias = Literal["BUY", "SELL"]

BestLineId = NewType("BestLineId", str)
CategoryId = NewType("CategoryId", str)
ChatId = NewType("ChatId", str)
ClobRewardId = NewType("ClobRewardId", str)
CollectionId = NewType("CollectionId", str)
CommentId = NewType("CommentId", str)
ConditionId = NewType("ConditionId", str)
EventCreatorId = NewType("EventCreatorId", str)
EventExternalPartnerMappingId = NewType("EventExternalPartnerMappingId", int)
EventId = NewType("EventId", str)
ImageOptimizationId = NewType("ImageOptimizationId", str)
InternalUserId = NewType("InternalUserId", str)
MarketId = NewType("MarketId", str)
OrderId = NewType("OrderId", str)
PartnerId = NewType("PartnerId", int)
PositionId = NewType("PositionId", str)
QuestionId = NewType("QuestionId", str)
ResolutionRequestId = NewType("ResolutionRequestId", str)
SeriesId = NewType("SeriesId", str)
SportId = NewType("SportId", int)
TagId = NewType("TagId", str)
TeamId = NewType("TeamId", int)
TemplateId = NewType("TemplateId", str)
TokenId = NewType("TokenId", str)

__all__ = [
    "BestLineId",
    "CategoryId",
    "ChatId",
    "ClobRewardId",
    "CollectionId",
    "CommentId",
    "ConditionId",
    "EventCreatorId",
    "EventExternalPartnerMappingId",
    "EventId",
    "ImageOptimizationId",
    "InternalUserId",
    "MarketId",
    "OrderId",
    "OrderSide",
    "PartnerId",
    "PositionId",
    "QuestionId",
    "ResolutionRequestId",
    "SeriesId",
    "SportId",
    "TagId",
    "TeamId",
    "TemplateId",
    "TokenId",
]
