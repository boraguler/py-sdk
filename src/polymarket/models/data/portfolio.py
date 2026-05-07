from __future__ import annotations

from decimal import Decimal

from pydantic import field_validator

from polymarket.models.base import BaseModel
from polymarket.models.gamma.common import parse_optional_decimal
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


__all__ = ["PortfolioValue", "TradedMarketCount"]
