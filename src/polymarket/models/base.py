"""Base model configuration for SDK objects."""

from typing import Self

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, ValidationError

from polymarket.errors import UnexpectedResponseError


class BaseModel(PydanticBaseModel):
    """Base model for immutable SDK objects."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        populate_by_name=True,
    )

    @classmethod
    def parse_response(cls, data: object) -> Self:
        """Parse response data into this SDK object."""
        try:
            return cls.model_validate(data)
        except ValidationError as error:
            raise UnexpectedResponseError(
                f"{cls.__name__} response did not match expected shape"
            ) from error


__all__ = ["BaseModel"]
