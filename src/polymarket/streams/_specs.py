from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from polymarket.errors import UserInputError


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketSpec:
    """Subscription for the CLOB market stream."""

    token_ids: Sequence[str]
    custom_feature_enabled: bool = False
    topic: Literal["market"] = "market"

    def __post_init__(self) -> None:
        if not isinstance(self.custom_feature_enabled, bool):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise UserInputError("custom_feature_enabled must be a bool")
        if isinstance(self.token_ids, str | bytes):
            raise UserInputError("token_ids must be a sequence of token ids, not a single string")
        normalized: list[str] = []
        for tid in self.token_ids:
            if not isinstance(tid, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise UserInputError(f"token_id must be a string, got {type(tid).__name__}")
            if not tid:
                raise UserInputError("token_id must be non-empty")
            normalized.append(tid)
        if not normalized:
            raise UserInputError("token_ids must be a non-empty sequence")
        object.__setattr__(self, "token_ids", tuple(normalized))


Subscription = MarketSpec


__all__ = ["MarketSpec", "Subscription"]
