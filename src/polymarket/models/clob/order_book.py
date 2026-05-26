from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field, field_validator

from polymarket.models.base import BaseModel
from polymarket.models.clob._validators import (
    _DecimalFromString,  # pyright: ignore[reportPrivateUsage]
)
from polymarket.models.types import TokenId


class OrderBookLevel(BaseModel):
    price: _DecimalFromString
    size: _DecimalFromString


class OrderBook(BaseModel):
    market: str
    token_id: TokenId = Field(validation_alias="asset_id")
    timestamp: datetime | None = None
    bids: tuple[OrderBookLevel, ...]
    """Bid levels in ascending price order, lowest bid first."""
    asks: tuple[OrderBookLevel, ...]
    """Ask levels in descending price order, highest ask first."""
    min_order_size: _DecimalFromString
    tick_size: _DecimalFromString
    neg_risk: bool
    last_trade_price: _DecimalFromString | None = None
    hash: str

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, value: object) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                ms = int(value)
            except ValueError as error:
                msg = f"invalid epoch-ms timestamp: {value!r}"
                raise ValueError(msg) from error
            try:
                return datetime.fromtimestamp(ms / 1000, tz=UTC)
            except (OverflowError, OSError, ValueError) as error:
                msg = f"invalid epoch-ms timestamp: {value!r}"
                raise ValueError(msg) from error
        msg = f"expected a string epoch-ms timestamp, got {type(value).__name__}"
        raise ValueError(msg)

    @field_validator("last_trade_price", mode="before")
    @classmethod
    def _parse_last_trade_price(cls, value: object) -> object:
        return None if value in (None, "") else value


__all__ = ["OrderBook", "OrderBookLevel"]
