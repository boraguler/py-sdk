from __future__ import annotations

from pydantic import Field

from polymarket.models.base import BaseModel


class CancelOrdersResponse(BaseModel):
    canceled: tuple[str, ...]
    not_canceled: dict[str, str] = Field(default_factory=dict, validation_alias="not_canceled")


__all__ = ["CancelOrdersResponse"]
