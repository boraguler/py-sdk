from decimal import Decimal

import pytest

from polymarket._internal.actions.clob import build_midpoint_request, parse_midpoint
from polymarket.errors import UnexpectedResponseError, UserInputError


def test_build_midpoint_request_targets_midpoint_path_with_token_id() -> None:
    path, params = build_midpoint_request(token_id="123")

    assert path == "/midpoint"
    assert params == {"token_id": "123"}


def test_build_midpoint_request_rejects_empty_token_id() -> None:
    with pytest.raises(UserInputError, match="token_id"):
        build_midpoint_request(token_id="")


def test_parse_midpoint_returns_decimal_for_decimal_string() -> None:
    assert parse_midpoint({"mid": "0.53"}) == Decimal("0.53")


def test_parse_midpoint_handles_integer_decimal_response() -> None:
    assert parse_midpoint({"mid": "1"}) == Decimal("1")
    assert parse_midpoint({"mid": "0"}) == Decimal("0")


def test_parse_midpoint_rejects_non_dict_response() -> None:
    with pytest.raises(UnexpectedResponseError):
        parse_midpoint([])


def test_parse_midpoint_rejects_missing_mid_field() -> None:
    with pytest.raises(UnexpectedResponseError):
        parse_midpoint({})


def test_parse_midpoint_rejects_non_decimal_mid_value() -> None:
    with pytest.raises(UnexpectedResponseError):
        parse_midpoint({"mid": "not-a-decimal"})
