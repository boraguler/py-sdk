from decimal import Decimal
from typing import Annotated

from pydantic import BeforeValidator


def _require_decimal_string(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if not isinstance(value, str):
        msg = f"expected decimal string, got {type(value).__name__}"
        raise ValueError(msg)
    return value


DecimalString = Annotated[Decimal, BeforeValidator(_require_decimal_string)]


__all__ = ["DecimalString"]
