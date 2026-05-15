from __future__ import annotations

from decimal import Decimal, DecimalException
from typing import Any, cast

from pydantic import Field, model_validator

from polymarket.models.base import BaseModel

_BUILDER_FEES_BPS = Decimal(10_000)


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


__all__ = ["BuilderFeeRates"]
