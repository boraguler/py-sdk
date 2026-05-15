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


def _coerce_decimalish(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, bool):
        msg = f"expected decimal-ish value, got bool {value!r}"
        raise ValueError(msg)
    if isinstance(value, Decimal | str):
        return value
    if isinstance(value, int | float):
        return str(value)
    msg = f"expected decimal-ish value, got {type(value).__name__}"
    raise ValueError(msg)


DecimalString = Annotated[Decimal, BeforeValidator(_require_decimal_string)]
DecimalishString = Annotated[Decimal, BeforeValidator(_coerce_decimalish)]


__all__ = ["DecimalString", "DecimalishString"]
