from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import Field

from polymarket.models.base import BaseModel

PriceHistoryInterval: TypeAlias = Literal["max", "1w", "1d", "6h", "1h"]


class PriceHistoryPoint(BaseModel):
    t: int = Field(strict=True)
    p: float = Field(strict=True)


__all__ = ["PriceHistoryInterval", "PriceHistoryPoint"]
