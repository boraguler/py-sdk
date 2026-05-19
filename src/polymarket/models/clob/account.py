from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, TypeAlias, cast

from pydantic import Field, field_validator

from polymarket.models.base import BaseModel
from polymarket.models.clob._validators import (
    _DecimalFromString,  # pyright: ignore[reportPrivateUsage]
)
from polymarket.models.types import OrderSide, TokenId

AssetType: TypeAlias = Literal["COLLATERAL", "CONDITIONAL"]


_EPOCH_MS_THRESHOLD = 100_000_000_000


def _parse_epoch(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, bool):
        msg = f"expected an epoch timestamp, got bool {value!r}"
        raise ValueError(msg)
    if isinstance(value, str):
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            value = int(value)
        else:
            try:
                normalized = value.replace("Z", "+00:00")
                parsed = datetime.fromisoformat(normalized)
            except ValueError as error:
                msg = f"invalid epoch or ISO timestamp: {value!r}"
                raise ValueError(msg) from error
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    if isinstance(value, int):
        seconds = value / 1000 if abs(value) >= _EPOCH_MS_THRESHOLD else value
        try:
            return datetime.fromtimestamp(seconds, tz=UTC)
        except (OverflowError, OSError, ValueError) as error:
            msg = f"epoch timestamp out of range: {value!r}"
            raise ValueError(msg) from error
    msg = f"expected an epoch timestamp, got {type(value).__name__}"
    raise ValueError(msg)


def _parse_optional_epoch(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    return _parse_epoch(value)


class OpenOrder(BaseModel):
    id: str
    market: str
    token_id: TokenId = Field(validation_alias="asset_id")
    owner: str
    maker_address: str = Field(validation_alias="maker_address")
    side: OrderSide
    price: _DecimalFromString
    original_size: _DecimalFromString = Field(validation_alias="original_size")
    size_matched: _DecimalFromString = Field(validation_alias="size_matched")
    outcome: str
    order_type: str = Field(validation_alias="order_type")
    status: str
    associate_trades: tuple[str, ...] = Field(default=(), validation_alias="associate_trades")
    created_at: datetime = Field(validation_alias="created_at")
    expires_at: datetime | None = Field(default=None, validation_alias="expiration")

    @field_validator("created_at", mode="before")
    @classmethod
    def _parse_created_at(cls, value: object) -> datetime:
        return _parse_epoch(value)

    @field_validator("expires_at", mode="before")
    @classmethod
    def _parse_expires_at(cls, value: object) -> datetime | None:
        return _parse_optional_epoch(value)


class MakerOrder(BaseModel):
    order_id: str = Field(validation_alias="order_id")
    token_id: TokenId = Field(validation_alias="asset_id")
    maker_address: str = Field(validation_alias="maker_address")
    owner: str
    side: OrderSide
    price: _DecimalFromString
    matched_amount: _DecimalFromString = Field(validation_alias="matched_amount")
    outcome: str
    fee_rate_bps: _DecimalFromString | None = Field(default=None, validation_alias="fee_rate_bps")

    @field_validator("fee_rate_bps", mode="before")
    @classmethod
    def _empty_to_none(cls, value: object) -> object:
        return None if value == "" else value


class ClobTrade(BaseModel):
    id: str
    market: str
    token_id: TokenId = Field(validation_alias="asset_id")
    owner: str
    maker_address: str = Field(validation_alias="maker_address")
    taker_order_id: str = Field(validation_alias="taker_order_id")
    side: OrderSide
    trader_side: Literal["TAKER", "MAKER"] = Field(validation_alias="trader_side")
    price: _DecimalFromString
    size: _DecimalFromString
    outcome: str
    status: str
    fee_rate_bps: _DecimalFromString = Field(validation_alias="fee_rate_bps")
    bucket_index: int = Field(validation_alias="bucket_index")
    transaction_hash: str = Field(validation_alias="transaction_hash")
    maker_orders: tuple[MakerOrder, ...] = Field(validation_alias="maker_orders")
    matched_at: datetime = Field(validation_alias="match_time")
    updated_at: datetime = Field(validation_alias="last_update")

    @field_validator("matched_at", "updated_at", mode="before")
    @classmethod
    def _parse_epoch_field(cls, value: object) -> datetime:
        return _parse_epoch(value)


class Notification(BaseModel):
    id: int
    owner: str
    type: int
    payload: Any = None
    timestamp: datetime

    @field_validator("id", mode="before")
    @classmethod
    def _parse_id(cls, value: object) -> int:
        if isinstance(value, bool):
            msg = f"notification id must be an integer, got bool {value!r}"
            raise ValueError(msg)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and (
            value.isdigit() or (value.startswith("-") and value[1:].isdigit())
        ):
            return int(value)
        msg = f"notification id must be an integer or numeric string, got {type(value).__name__}"
        raise ValueError(msg)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, value: object) -> datetime:
        return _parse_epoch(value)


class BalanceAllowance(BaseModel):
    balance: int
    allowances: dict[str, int]

    @field_validator("balance", mode="before")
    @classmethod
    def _parse_balance(cls, value: object) -> int:
        return _parse_base_units(value, "balance")

    @field_validator("allowances", mode="before")
    @classmethod
    def _parse_allowances(cls, value: object) -> object:
        if not isinstance(value, dict):
            msg = f"allowances must be a mapping, got {type(value).__name__}"
            raise ValueError(msg)
        items = cast(dict[object, object], value).items()
        result: dict[str, int] = {}
        for key, raw in items:
            if not isinstance(key, str):
                msg = f"allowances key must be a string, got {type(key).__name__}"
                raise ValueError(msg)
            result[key] = _parse_base_units(raw, f"allowances[{key}]")
        return result


def _parse_base_units(value: object, name: str) -> int:
    if isinstance(value, bool):
        msg = f"{name} must be an integer, got bool"
        raise ValueError(msg)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as error:
            msg = f"{name} must be a base-units integer, got {value!r}"
            raise ValueError(msg) from error
    msg = f"{name} must be an integer or numeric string, got {type(value).__name__}"
    raise ValueError(msg)


__all__ = [
    "AssetType",
    "BalanceAllowance",
    "ClobTrade",
    "MakerOrder",
    "Notification",
    "OpenOrder",
]
