"""Cursor and timestamp helpers for Perps pagination."""

import base64
import binascii
import json
from datetime import datetime
from typing import Any, cast

from polymarket.errors import UserInputError

ONE_DAY_MS = 24 * 60 * 60 * 1000
NINETY_DAYS_MS = 90 * ONE_DAY_MS

_INTERVAL_MS: dict[str, int] = {
    "1s": 1000,
    "1m": 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": ONE_DAY_MS,
    "1w": 7 * ONE_DAY_MS,
}


def interval_ms(interval: str) -> int:
    return _INTERVAL_MS[interval]


def to_epoch_ms(name: str, value: datetime | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    if isinstance(value, bool) or not isinstance(value, int):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise UserInputError(f"{name} must be a datetime or epoch-ms int")
    if value < 0:
        raise UserInputError(f"{name} must be non-negative")
    return value


def encode_perps_cursor(state: dict[str, Any]) -> str:
    return base64.b64encode(json.dumps(state, separators=(",", ":")).encode("utf-8")).decode(
        "ascii"
    )


def as_json_dict(value: object) -> dict[str, Any] | None:
    """Return the value as a JSON object dict, or None when it is not one."""
    if isinstance(value, dict):
        return cast("dict[str, Any]", value)
    return None


def decode_perps_cursor(cursor: str, *, kind: str) -> dict[str, Any]:
    try:
        decoded = json.loads(base64.b64decode(cursor, validate=True))
    except (binascii.Error, ValueError, UnicodeDecodeError) as error:
        raise UserInputError("Invalid Perps pagination cursor") from error
    state = as_json_dict(decoded)
    if state is None or state.get("kind") != kind:
        raise UserInputError("Invalid Perps pagination cursor")
    return state


def parse_data_envelope(payload: object) -> tuple[list[object], bool]:
    from polymarket.errors import UnexpectedResponseError

    envelope = as_json_dict(payload)
    if envelope is None:
        raise UnexpectedResponseError("Perps list response did not match expected shape")
    data = envelope.get("data")
    more = envelope.get("more")
    if not isinstance(data, list) or not isinstance(more, bool):
        raise UnexpectedResponseError("Perps list response did not match expected shape")
    return cast("list[object]", data), more


__all__ = [
    "NINETY_DAYS_MS",
    "ONE_DAY_MS",
    "as_json_dict",
    "decode_perps_cursor",
    "encode_perps_cursor",
    "interval_ms",
    "parse_data_envelope",
    "to_epoch_ms",
]
