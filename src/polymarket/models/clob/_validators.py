from datetime import UTC, datetime
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


def _parse_epoch_ms_timestamp(value: object) -> object:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        msg = f"expected epoch-ms timestamp string, got {type(value).__name__}"
        raise ValueError(msg)
    # Unsigned digits only; int() alone would accept "-1", "+1", " 1 ", etc.
    if not value.isdecimal():
        msg = f"invalid epoch-ms timestamp: {value!r}"
        raise ValueError(msg)
    ms = int(value)
    try:
        return datetime.fromtimestamp(ms / 1000, tz=UTC)
    except (OverflowError, OSError, ValueError) as error:
        msg = f"invalid epoch-ms timestamp: {value!r}"
        raise ValueError(msg) from error


def _parse_epoch_ms_or_iso_timestamp(value: object) -> object:
    """Permissive timestamp parser.

    Accepts ``int`` (epoch ms), digit-string (epoch ms), and ISO-8601 strings.
    Returns ``datetime`` (UTC-aware for epoch inputs; the string's own tz for
    ISO inputs). Empty string / None / boolean / unknown shapes all surface
    via ``ValueError``.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, bool):
        msg = f"expected timestamp, got bool {value!r}"
        raise ValueError(msg)
    if isinstance(value, int):
        try:
            return datetime.fromtimestamp(value / 1000, tz=UTC)
        except (OverflowError, OSError, ValueError) as error:
            msg = f"invalid epoch-ms timestamp: {value!r}"
            raise ValueError(msg) from error
    if isinstance(value, str):
        if value.isdecimal():
            ms = int(value)
            try:
                return datetime.fromtimestamp(ms / 1000, tz=UTC)
            except (OverflowError, OSError, ValueError) as error:
                msg = f"invalid epoch-ms timestamp: {value!r}"
                raise ValueError(msg) from error
        try:
            return datetime.fromisoformat(value)
        except ValueError as error:
            msg = f"invalid timestamp: {value!r}"
            raise ValueError(msg) from error
    msg = f"expected epoch-ms or ISO timestamp, got {type(value).__name__}"
    raise ValueError(msg)


DecimalString = Annotated[Decimal, BeforeValidator(_require_decimal_string)]
DecimalishString = Annotated[Decimal, BeforeValidator(_coerce_decimalish)]
EpochMsTimestamp = Annotated[datetime | None, BeforeValidator(_parse_epoch_ms_timestamp)]
EpochMsOrIsoTimestamp = Annotated[
    datetime | None, BeforeValidator(_parse_epoch_ms_or_iso_timestamp)
]


__all__ = [
    "DecimalString",
    "DecimalishString",
    "EpochMsOrIsoTimestamp",
    "EpochMsTimestamp",
]
