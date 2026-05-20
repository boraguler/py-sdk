from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from polymarket._internal.actions.orders.types import BYTES32_ZERO
from polymarket._internal.context import AsyncClientContext, SyncClientContext
from polymarket._internal.validation import require_nonempty, validate_builder_code
from polymarket.errors import UnexpectedResponseError, UserInputError
from polymarket.models.clob.builder import BuilderFeeRates
from polymarket.models.types import ConditionId, TokenId

_ALLOWED_TICK_SIZES: frozenset[Decimal] = frozenset(
    {Decimal("0.1"), Decimal("0.01"), Decimal("0.001"), Decimal("0.0001")}
)


@dataclass(frozen=True, slots=True)
class PlatformFeeInfo:
    rate: Decimal
    exponent: Decimal


async def fetch_tick_size(ctx: AsyncClientContext, *, token_id: str) -> Decimal:
    validated = require_nonempty("token_id", token_id)
    data = await ctx.clob.get_json("/tick-size", params={"token_id": validated})
    return _parse_tick_size(data)


def fetch_tick_size_sync(ctx: SyncClientContext, *, token_id: str) -> Decimal:
    validated = require_nonempty("token_id", token_id)
    data = ctx.clob.get_json("/tick-size", params={"token_id": validated})
    return _parse_tick_size(data)


async def fetch_neg_risk(ctx: AsyncClientContext, *, token_id: str) -> bool:
    validated = require_nonempty("token_id", token_id)
    data = await ctx.clob.get_json("/neg-risk", params={"token_id": validated})
    return _parse_neg_risk(data)


async def resolve_condition_by_token(ctx: AsyncClientContext, *, token_id: TokenId) -> ConditionId:
    validated = require_nonempty("token_id", token_id)
    data = await ctx.clob.get_json(f"/markets-by-token/{validated}")
    return _parse_condition_by_token(data)


async def fetch_platform_fee_info(
    ctx: AsyncClientContext, *, condition_id: ConditionId
) -> PlatformFeeInfo:
    validated = require_nonempty("condition_id", condition_id)
    data = await ctx.clob.get_json(f"/clob-markets/{validated}")
    return _parse_platform_fee_info(data)


async def fetch_builder_fee_rates(ctx: AsyncClientContext, *, builder_code: str) -> BuilderFeeRates:
    validated = validate_builder_code(builder_code)
    if validated == BYTES32_ZERO:
        raise UserInputError(
            "builder_code must be a real builder; zero (0x000…000) represents no attribution."
        )
    data = await ctx.clob.get_json(f"/fees/builder-fees/{validated}")
    return BuilderFeeRates.parse_response(data)


def _parse_tick_size(data: object) -> Decimal:
    if not isinstance(data, dict):
        raise UnexpectedResponseError("tick-size response did not match expected shape")
    raw = cast(dict[str, object], data).get("minimum_tick_size")
    if isinstance(raw, bool):
        raise UnexpectedResponseError(
            f"tick-size 'minimum_tick_size' must be numeric, got bool {raw!r}"
        )
    if isinstance(raw, int | float):
        value = Decimal(str(raw))
    elif isinstance(raw, str):
        try:
            value = Decimal(raw)
        except (ValueError, ArithmeticError) as error:
            raise UnexpectedResponseError(
                f"tick-size 'minimum_tick_size' is not a valid number: {raw!r}"
            ) from error
    else:
        raise UnexpectedResponseError(
            f"tick-size 'minimum_tick_size' must be numeric, got {type(raw).__name__}"
        )
    if value not in _ALLOWED_TICK_SIZES:
        raise UnexpectedResponseError(f"Unsupported tick size received: {value}")
    return value


def _parse_neg_risk(data: object) -> bool:
    if not isinstance(data, dict):
        raise UnexpectedResponseError("neg-risk response did not match expected shape")
    raw = cast(dict[str, object], data).get("neg_risk")
    if not isinstance(raw, bool):
        raise UnexpectedResponseError(
            f"neg-risk 'neg_risk' must be a bool, got {type(raw).__name__}"
        )
    return raw


def _parse_condition_by_token(data: object) -> ConditionId:
    if not isinstance(data, dict):
        raise UnexpectedResponseError("markets-by-token response did not match expected shape")
    raw = cast(dict[str, object], data).get("condition_id")
    if not isinstance(raw, str) or not raw:
        raise UnexpectedResponseError("markets-by-token response missing or invalid 'condition_id'")
    return ConditionId(raw)


def _parse_platform_fee_info(data: object) -> PlatformFeeInfo:
    if not isinstance(data, dict):
        raise UnexpectedResponseError("clob-markets response did not match expected shape")
    payload = cast(dict[str, object], data)
    raw_fee = payload.get("fd")
    if raw_fee is None:
        return PlatformFeeInfo(rate=Decimal(0), exponent=Decimal(0))
    if not isinstance(raw_fee, dict):
        raise UnexpectedResponseError(
            f"clob-markets 'fd' must be an object, got {type(raw_fee).__name__}"
        )
    fee = cast(dict[str, object], raw_fee)
    return PlatformFeeInfo(
        rate=_coerce_decimal(fee.get("r"), "fd.r"),
        exponent=_coerce_decimal(fee.get("e"), "fd.e"),
    )


def _coerce_decimal(value: object, field: str) -> Decimal:
    if value is None:
        return Decimal(0)
    if isinstance(value, bool):
        raise UnexpectedResponseError(f"{field} must be numeric, got bool")
    if isinstance(value, int | float):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except (ValueError, ArithmeticError) as error:
            raise UnexpectedResponseError(f"{field} is not a valid number: {value!r}") from error
    raise UnexpectedResponseError(f"{field} must be numeric, got {type(value).__name__}")


__all__ = [
    "PlatformFeeInfo",
    "fetch_builder_fee_rates",
    "fetch_neg_risk",
    "fetch_platform_fee_info",
    "fetch_tick_size",
    "fetch_tick_size_sync",
    "resolve_condition_by_token",
]
