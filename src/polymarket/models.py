"""Canonical SDK models.

These models define the public objects returned by the SDK.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class SDKModel(BaseModel):
    """Base model for immutable SDK objects."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        populate_by_name=True,
    )


class Market(SDKModel):
    """A Polymarket market."""

    id: str = Field(validation_alias=AliasChoices("id", "market_id", "marketId"))
    condition_id: str = Field(
        validation_alias=AliasChoices("condition_id", "conditionId", "condition")
    )
    question: str
    slug: str | None = None
    active: bool | None = None
    closed: bool | None = None
    archived: bool | None = None
    accepting_orders: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("accepting_orders", "acceptingOrders"),
    )
    outcomes: tuple[str, ...] = ()
    outcome_prices: tuple[Decimal, ...] = Field(
        default=(),
        validation_alias=AliasChoices("outcome_prices", "outcomePrices"),
    )
    volume: Decimal | None = None
    liquidity: Decimal | None = None
    created_at: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("created_at", "createdAt"),
    )
    end_at: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("end_at", "endDate", "endDateIso"),
    )

    @field_validator("outcomes", mode="before")
    @classmethod
    def _parse_outcomes(cls, value: object) -> tuple[str, ...]:
        if value is None:
            return ()

        return tuple(str(item) for item in _parse_sequence(value))

    @field_validator("outcome_prices", mode="before")
    @classmethod
    def _parse_outcome_prices(cls, value: object) -> tuple[Decimal, ...]:
        if value is None:
            return ()

        return tuple(_parse_decimal(item) for item in _parse_sequence(value))

    @field_validator("volume", "liquidity", mode="before")
    @classmethod
    def _parse_optional_decimal(cls, value: object) -> Decimal | None:
        if value in (None, ""):
            return None

        return _parse_decimal(value)


def _parse_sequence(value: object) -> tuple[Any, ...]:
    if isinstance(value, str):
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            msg = "expected a JSON array"
            raise ValueError(msg)

        return tuple(cast(list[Any], parsed))

    if isinstance(value, list | tuple):
        return tuple(cast(list[Any] | tuple[Any, ...], value))

    msg = "expected a sequence"
    raise ValueError(msg)


def _parse_decimal(value: object) -> Decimal:
    return Decimal(str(value))


__all__ = ["Market", "SDKModel"]
