from dataclasses import dataclass
from decimal import Decimal

from polymarket.environments import Environment
from polymarket.errors import UnexpectedResponseError
from polymarket.types import EvmAddress


@dataclass(frozen=True, slots=True)
class RoundingConfig:
    amount: int
    price: int
    size: int


_ROUNDING_BY_TICK: dict[Decimal, RoundingConfig] = {
    Decimal("0.1"): RoundingConfig(amount=3, price=1, size=2),
    Decimal("0.01"): RoundingConfig(amount=4, price=2, size=2),
    Decimal("0.005"): RoundingConfig(amount=5, price=3, size=2),
    Decimal("0.0025"): RoundingConfig(amount=6, price=4, size=2),
    Decimal("0.001"): RoundingConfig(amount=5, price=3, size=2),
    Decimal("0.0001"): RoundingConfig(amount=6, price=4, size=2),
}


def resolve_rounding_config(tick_size: Decimal) -> RoundingConfig:
    config = _ROUNDING_BY_TICK.get(tick_size)
    if config is None:
        raise UnexpectedResponseError(f"Unsupported tick size: {tick_size}")
    return config


def resolve_exchange_address(environment: Environment, neg_risk: bool) -> EvmAddress:
    return EvmAddress(environment.neg_risk_exchange if neg_risk else environment.standard_exchange)


__all__ = ["RoundingConfig", "resolve_exchange_address", "resolve_rounding_config"]
