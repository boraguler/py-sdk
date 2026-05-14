from __future__ import annotations

from polymarket.models.base import BaseModel
from polymarket.models.clob._validators import DecimalString
from polymarket.models.types import OrderSide, TokenId


class LastTradePrice(BaseModel):
    price: DecimalString
    side: OrderSide


class LastTradePriceForToken(BaseModel):
    token_id: TokenId
    price: DecimalString
    side: OrderSide


__all__ = ["LastTradePrice", "LastTradePriceForToken"]
