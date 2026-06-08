from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from pydantic import Field, field_validator

from polymarket._frames_bridge import frames_func as _frames_func
from polymarket.models.base import BaseModel
from polymarket.models.clob._validators import (
    EpochMsTimestamp,
    _DecimalFromString,  # pyright: ignore[reportPrivateUsage]
)
from polymarket.models.types import TokenId

_DecimalMode = Literal["decimal", "float"]


class OrderBookLevel(BaseModel):
    price: _DecimalFromString
    size: _DecimalFromString


class OrderBook(BaseModel):
    market: str
    token_id: TokenId = Field(validation_alias="asset_id")
    timestamp: EpochMsTimestamp = None
    bids: tuple[OrderBookLevel, ...]
    """Ascending price order, lowest bid first."""
    asks: tuple[OrderBookLevel, ...]
    """Descending price order, highest ask first."""
    min_order_size: _DecimalFromString
    tick_size: _DecimalFromString
    neg_risk: bool
    last_trade_price: _DecimalFromString | None = None
    hash: str

    @field_validator("last_trade_price", mode="before")
    @classmethod
    def _parse_last_trade_price(cls, value: object) -> object:
        return None if value in (None, "") else value

    def to_arrow(self) -> Any:
        """Flatten this book into ``[side, level, price, size]`` rows."""
        return _frames_func("to_arrow")(self)

    def to_pandas(
        self,
        *,
        decimal: _DecimalMode = "decimal",
        explode: Sequence[str] | None = None,
    ) -> Any:
        return _frames_func("to_pandas")(self, decimal=decimal, explode=explode)

    def to_polars(
        self,
        *,
        explode: Sequence[str] | None = None,
    ) -> Any:
        return _frames_func("to_polars")(self, explode=explode)


__all__ = ["OrderBook", "OrderBookLevel"]
