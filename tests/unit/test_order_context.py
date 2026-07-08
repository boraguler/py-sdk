from decimal import Decimal

import pytest

from polymarket._internal.actions.orders.context import (
    resolve_exchange_address,
    resolve_rounding_config,
)
from polymarket.environments import PRODUCTION
from polymarket.errors import UnexpectedResponseError


def test_resolve_rounding_config_supports_known_tick_sizes() -> None:
    assert resolve_rounding_config(Decimal("0.1")).price == 1
    assert resolve_rounding_config(Decimal("0.01")).price == 2
    assert resolve_rounding_config(Decimal("0.005")).price == 3
    assert resolve_rounding_config(Decimal("0.0025")).price == 4
    assert resolve_rounding_config(Decimal("0.001")).price == 3
    assert resolve_rounding_config(Decimal("0.0001")).price == 4


def test_resolve_rounding_config_amount_and_size_follow_table() -> None:
    config = resolve_rounding_config(Decimal("0.001"))
    assert config.amount == 5
    assert config.size == 2


def test_resolve_rounding_config_rejects_unsupported_tick_size() -> None:
    with pytest.raises(UnexpectedResponseError, match="Unsupported tick size"):
        resolve_rounding_config(Decimal("0.0005"))


def test_resolve_exchange_address_selects_neg_risk_when_true() -> None:
    assert resolve_exchange_address(PRODUCTION, neg_risk=True) == PRODUCTION.neg_risk_exchange


def test_resolve_exchange_address_selects_standard_when_false() -> None:
    assert resolve_exchange_address(PRODUCTION, neg_risk=False) == PRODUCTION.standard_exchange
