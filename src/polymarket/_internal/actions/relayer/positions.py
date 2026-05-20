from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Literal

from polymarket.errors import UnexpectedResponseError, UserInputError
from polymarket.models.data.portfolio import Position

_TOKEN_DECIMALS = 1_000_000

BinaryPositions = tuple[Position | None, Position | None]


def expect_binary_positions(positions: Sequence[Position]) -> BinaryPositions:
    if not positions:
        raise UserInputError("You have no positions")
    if len(positions) > 2:
        raise UnexpectedResponseError(f"Expected at most two positions, got {len(positions)}")

    yes_position: Position | None = None
    no_position: Position | None = None
    for position in positions:
        if position.outcome_index not in (0, 1):
            raise UnexpectedResponseError(
                f"Unexpected outcomeIndex {position.outcome_index} for condition "
                f"{position.condition_id}"
            )
        if position.outcome_index == 0:
            if yes_position is not None:
                raise UnexpectedResponseError(
                    f"Duplicate YES position for condition {position.condition_id}"
                )
            yes_position = position
        else:
            if no_position is not None:
                raise UnexpectedResponseError(
                    f"Duplicate NO position for condition {position.condition_id}"
                )
            no_position = position

    return yes_position, no_position


def expect_negative_risk_flag(positions: BinaryPositions) -> bool:
    yes_position, no_position = positions
    first = yes_position if yes_position is not None else no_position
    assert first is not None
    condition_id = first.condition_id
    if first.negative_risk is None:
        raise UnexpectedResponseError(f"Missing negativeRisk flag for condition {condition_id}")
    if yes_position is not None and no_position is not None:
        if yes_position.negative_risk is None or no_position.negative_risk is None:
            raise UnexpectedResponseError(f"Missing negativeRisk flag for condition {condition_id}")
        if yes_position.negative_risk != no_position.negative_risk:
            raise UnexpectedResponseError(f"Mixed negativeRisk flags for condition {condition_id}")
    return first.negative_risk


def resolve_binary_positions_condition_id(positions: BinaryPositions) -> str:
    yes_position, no_position = positions
    first = yes_position if yes_position is not None else no_position
    assert first is not None
    return first.condition_id


def _derive_binary_position_amounts(positions: BinaryPositions) -> tuple[int, int]:
    yes_position, no_position = positions
    return (
        _to_position_amount(yes_position, expected_outcome_index=0),
        _to_position_amount(no_position, expected_outcome_index=1),
    )


def calculate_max_merge_amount(positions: BinaryPositions) -> int:
    yes_amount, no_amount = _derive_binary_position_amounts(positions)
    return min(yes_amount, no_amount)


def resolve_merge_amount(
    positions: BinaryPositions,
    requested: int | Literal["max"],
) -> int:
    max_amount = calculate_max_merge_amount(positions)
    condition_id = resolve_binary_positions_condition_id(positions)
    if max_amount == 0:
        raise UserInputError(
            f"You have no complementary positions to merge for condition {condition_id}"
        )
    if requested == "max":
        return max_amount
    if requested <= 0:
        raise UserInputError("Merge amount must be positive")
    if requested > max_amount:
        raise UserInputError(
            f"Requested merge amount {requested} exceeds the maximum mergeable "
            f"amount {max_amount} for condition {condition_id}"
        )
    return requested


def _to_position_amount(position: Position | None, *, expected_outcome_index: Literal[0, 1]) -> int:
    if position is None:
        return 0
    if position.outcome_index != expected_outcome_index:
        raise UnexpectedResponseError(
            f"Expected outcomeIndex {expected_outcome_index}, got {position.outcome_index}"
        )
    if position.size is None:
        return 0
    if not position.size.is_finite():
        raise UnexpectedResponseError(f"Position size must be a finite number, got {position.size}")
    if position.size < 0:
        raise UnexpectedResponseError("Position size must be non-negative")
    return int(position.size * Decimal(_TOKEN_DECIMALS))


__all__ = [
    "BinaryPositions",
    "calculate_max_merge_amount",
    "expect_binary_positions",
    "expect_negative_risk_flag",
    "resolve_binary_positions_condition_id",
    "resolve_merge_amount",
]
