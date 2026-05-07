from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from polymarket.models.base import BaseModel
from polymarket.models.gamma.common import parse_optional_datetime, parse_optional_decimal

BuilderVolumeTimePeriod = Literal["DAY", "WEEK", "MONTH", "ALL"]


class BuilderVolumeEntry(BaseModel):
    bucket_at: datetime | None = Field(default=None, validation_alias="dt")
    builder: str | None = None
    builder_logo: str | None = Field(default=None, validation_alias="builderLogo")
    verified: bool | None = None
    volume: Decimal | None = None
    active_users: int | None = Field(default=None, validation_alias="activeUsers")
    rank: str | None = None

    @field_validator("bucket_at", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime | None:
        return parse_optional_datetime(value)

    @field_validator("volume", mode="before")
    @classmethod
    def _parse_volume(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)


__all__ = ["BuilderVolumeEntry", "BuilderVolumeTimePeriod"]
