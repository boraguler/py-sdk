from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator

from polymarket.models.base import BaseModel
from polymarket.models.gamma.common import parse_epoch_seconds_optional, parse_optional_decimal
from polymarket.models.types import ConditionId, TokenId
from polymarket.types import EvmAddress


class PortfolioValue(BaseModel):
    user: EvmAddress | None = None
    value: Decimal | None = None

    @field_validator("value", mode="before")
    @classmethod
    def _parse_value(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)


class TradedMarketCount(BaseModel):
    user: EvmAddress | None = None
    traded: int | None = None


class Position(BaseModel):
    condition_id: ConditionId = Field(validation_alias="conditionId")
    wallet: EvmAddress | None = Field(default=None, validation_alias="proxyWallet")
    token_id: TokenId | None = Field(default=None, validation_alias="asset")
    size: Decimal | None = None
    avg_price: Decimal | None = Field(default=None, validation_alias="avgPrice")
    initial_value: Decimal | None = Field(default=None, validation_alias="initialValue")
    current_value: Decimal | None = Field(default=None, validation_alias="currentValue")
    cash_pnl: Decimal | None = Field(default=None, validation_alias="cashPnl")
    percent_pnl: float | None = Field(default=None, validation_alias="percentPnl")
    total_bought: Decimal | None = Field(default=None, validation_alias="totalBought")
    realized_pnl: Decimal | None = Field(default=None, validation_alias="realizedPnl")
    percent_realized_pnl: float | None = Field(default=None, validation_alias="percentRealizedPnl")
    cur_price: Decimal | None = Field(default=None, validation_alias="curPrice")
    redeemable: bool | None = None
    mergeable: bool | None = None
    title: str | None = None
    slug: str | None = None
    icon: str | None = None
    event_id: str | None = Field(default=None, validation_alias="eventId")
    event_slug: str | None = Field(default=None, validation_alias="eventSlug")
    outcome: str | None = None
    outcome_index: int | None = Field(default=None, validation_alias="outcomeIndex")
    opposite_outcome: str | None = Field(default=None, validation_alias="oppositeOutcome")
    opposite_token_id: TokenId | None = Field(default=None, validation_alias="oppositeAsset")
    end_date: str | None = Field(default=None, validation_alias="endDate")
    negative_risk: bool | None = Field(default=None, validation_alias="negativeRisk")

    @field_validator(
        "size",
        "avg_price",
        "initial_value",
        "current_value",
        "cash_pnl",
        "total_bought",
        "realized_pnl",
        "cur_price",
        mode="before",
    )
    @classmethod
    def _parse_decimal(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)


class ClosedPosition(BaseModel):
    wallet: EvmAddress | None = Field(default=None, validation_alias="proxyWallet")
    token_id: TokenId | None = Field(default=None, validation_alias="asset")
    condition_id: ConditionId | None = Field(default=None, validation_alias="conditionId")
    avg_price: Decimal | None = Field(default=None, validation_alias="avgPrice")
    total_bought: Decimal | None = Field(default=None, validation_alias="totalBought")
    realized_pnl: Decimal | None = Field(default=None, validation_alias="realizedPnl")
    cur_price: Decimal | None = Field(default=None, validation_alias="curPrice")
    timestamp: datetime | None = None
    title: str | None = None
    slug: str | None = None
    icon: str | None = None
    event_slug: str | None = Field(default=None, validation_alias="eventSlug")
    outcome: str | None = None
    outcome_index: int | None = Field(default=None, validation_alias="outcomeIndex")
    opposite_outcome: str | None = Field(default=None, validation_alias="oppositeOutcome")
    opposite_token_id: TokenId | None = Field(default=None, validation_alias="oppositeAsset")
    end_date: str | None = Field(default=None, validation_alias="endDate")

    @field_validator(
        "avg_price",
        "total_bought",
        "realized_pnl",
        "cur_price",
        mode="before",
    )
    @classmethod
    def _parse_decimal(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, value: object) -> datetime | None:
        return parse_epoch_seconds_optional(value)


__all__ = ["ClosedPosition", "PortfolioValue", "Position", "TradedMarketCount"]
