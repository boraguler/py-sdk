from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, DecimalException
from typing import Any, cast

from pydantic import Field, field_validator, model_validator

from polymarket.models.base import BaseModel
from polymarket.models.clob._validators import (
    _DecimalFromString,  # pyright: ignore[reportPrivateUsage]
)
from polymarket.models.types import OrderSide, TokenId

_BUILDER_FEES_BPS = Decimal(10_000)
_EPOCH_MS_THRESHOLD = 100_000_000_000


class BuilderFeeRates(BaseModel):
    maker: Decimal = Field(validation_alias="builder_maker_fee_rate_bps")
    taker: Decimal = Field(validation_alias="builder_taker_fee_rate_bps")

    @model_validator(mode="before")
    @classmethod
    def _scale_bps(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(cast(dict[str, Any], value))
        for key in ("builder_maker_fee_rate_bps", "builder_taker_fee_rate_bps"):
            raw = data.get(key)
            if raw is None or isinstance(raw, bool):
                continue
            if not isinstance(raw, int | float | str):
                continue
            try:
                data[key] = Decimal(str(raw)) / _BUILDER_FEES_BPS
            except DecimalException as error:
                raise ValueError(f"{key} is not a valid number: {raw!r}") from error
        return data


def _parse_epoch_ms_required(value: object) -> datetime:
    parsed = _parse_epoch_ms_optional(value)
    if parsed is None:
        msg = f"expected epoch-ms timestamp, got {value!r}"
        raise ValueError(msg)
    return parsed


def _parse_epoch_ms_optional(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, bool):
        msg = f"expected epoch-ms timestamp, got bool {value!r}"
        raise ValueError(msg)
    if isinstance(value, str):
        if not (value.isdigit() or (value.startswith("-") and value[1:].isdigit())):
            msg = f"invalid epoch-ms timestamp: {value!r}"
            raise ValueError(msg)
        value = int(value)
    if not isinstance(value, int):
        msg = f"expected epoch-ms timestamp, got {type(value).__name__}"
        raise ValueError(msg)
    seconds = value / 1000 if abs(value) >= _EPOCH_MS_THRESHOLD else value
    try:
        return datetime.fromtimestamp(seconds, tz=UTC)
    except (OverflowError, OSError, ValueError) as error:
        msg = f"epoch-ms timestamp out of range: {value!r}"
        raise ValueError(msg) from error


class BuilderTrade(BaseModel):
    id: str
    trade_type: str = Field(validation_alias="tradeType")
    taker_order_hash: str = Field(validation_alias="takerOrderHash")
    builder: str
    market: str
    token_id: TokenId = Field(validation_alias="assetId")
    side: OrderSide
    size: _DecimalFromString
    size_usdc: _DecimalFromString = Field(validation_alias="sizeUsdc")
    price: _DecimalFromString
    status: str
    outcome: str
    outcome_index: int = Field(validation_alias="outcomeIndex")
    owner: str
    maker: str
    transaction_hash: str = Field(validation_alias="transactionHash")
    matched_at: datetime = Field(validation_alias="matchTime")
    bucket_index: int = Field(validation_alias="bucketIndex")
    fee: _DecimalFromString
    fee_usdc: _DecimalFromString = Field(validation_alias="feeUsdc")
    error_msg: str | None = Field(default=None, validation_alias="err_msg")
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")
    updated_at: datetime | None = Field(default=None, validation_alias="updatedAt")

    @field_validator("matched_at", mode="before")
    @classmethod
    def _parse_matched_at(cls, value: object) -> datetime:
        return _parse_epoch_ms_required(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _parse_optional_epoch_ms(cls, value: object) -> datetime | None:
        return _parse_epoch_ms_optional(value)


__all__ = ["BuilderFeeRates", "BuilderTrade"]
