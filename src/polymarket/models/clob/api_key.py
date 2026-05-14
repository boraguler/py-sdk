from __future__ import annotations

from pydantic import Field

from polymarket.models.base import BaseModel


class ApiKeyCreds(BaseModel):
    key: str = Field(validation_alias="apiKey")
    passphrase: str = Field(repr=False)
    secret: str = Field(repr=False)


__all__ = ["ApiKeyCreds"]
