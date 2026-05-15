# pyright: reportUnnecessaryIsInstance=false
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from polymarket.errors import UserInputError


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketSpec:
    """Subscription for the CLOB market stream."""

    token_ids: Sequence[str]
    custom_feature_enabled: bool = False
    topic: Literal["market"] = field(default="market", init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.custom_feature_enabled, bool):
            raise UserInputError("custom_feature_enabled must be a bool")
        if isinstance(self.token_ids, str | bytes):
            raise UserInputError("token_ids must be a sequence of token ids, not a single string")
        normalized: list[str] = []
        for tid in self.token_ids:
            if not isinstance(tid, str):
                raise UserInputError(f"token_id must be a string, got {type(tid).__name__}")
            if not tid:
                raise UserInputError("token_id must be non-empty")
            normalized.append(tid)
        if not normalized:
            raise UserInputError("token_ids must be a non-empty sequence")
        object.__setattr__(self, "token_ids", tuple(normalized))


@dataclass(frozen=True, slots=True, kw_only=True)
class SportsSpec:
    """Subscription for the Sports stream.

    Sports has no per-subscription filtering — every subscriber receives
    every event the server broadcasts.
    """

    topic: Literal["sports"] = field(default="sports", init=False)


Subscription = MarketSpec | SportsSpec


def _normalize_specs(
    specs: Subscription | Sequence[Subscription],
) -> list[Subscription]:
    if isinstance(specs, MarketSpec | SportsSpec):
        return [specs]
    if not isinstance(specs, Sequence) or isinstance(specs, str | bytes):
        raise UserInputError("subscribe() expects a Subscription or a sequence of Subscriptions")
    items = list(specs)
    if not items:
        raise UserInputError("subscribe() requires at least one subscription")
    for spec in items:
        if not isinstance(spec, MarketSpec | SportsSpec):
            raise UserInputError(f"unsupported subscription type: {type(spec).__name__}")
    return items


__all__ = ["MarketSpec", "SportsSpec", "Subscription", "_normalize_specs"]
