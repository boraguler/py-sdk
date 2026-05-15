from dataclasses import dataclass
from decimal import Decimal

from polymarket._internal.actions.orders._numeric import coerce_positive_decimal
from polymarket._internal.actions.orders.context import (
    resolve_exchange_address,
    resolve_rounding_config,
)
from polymarket._internal.actions.orders.estimate import resolve_estimated_market_price
from polymarket._internal.actions.orders.market_data import (
    PlatformFeeInfo,
    fetch_neg_risk,
    fetch_platform_fee_info,
    fetch_tick_size,
    resolve_condition_by_token,
)
from polymarket._internal.actions.orders.math import (
    decimal_places,
    parse_amount,
    round_down,
    round_up,
)
from polymarket._internal.actions.orders.types import MarketOrderType, OrderDraft
from polymarket._internal.context import AsyncSecureClientContext
from polymarket._internal.validation import require_nonempty
from polymarket.errors import UserInputError
from polymarket.models.types import OrderSide, TokenId
from polymarket.types import EvmAddress


@dataclass(frozen=True, slots=True, kw_only=True)
class PrepareMarketOrderParams:
    token_id: TokenId
    side: OrderSide
    order_type: MarketOrderType
    amount: Decimal | None = None
    shares: Decimal | None = None
    max_spend: Decimal | None = None


def validate_market_order_params(
    *,
    token_id: str,
    side: OrderSide,
    amount: Decimal | int | float | str | None = None,
    shares: Decimal | int | float | str | None = None,
    max_spend: Decimal | int | float | str | None = None,
    order_type: MarketOrderType = "FAK",
) -> PrepareMarketOrderParams:
    validated_token = TokenId(require_nonempty("token_id", token_id))
    if side not in ("BUY", "SELL"):
        raise UserInputError(f"side must be 'BUY' or 'SELL', got {side!r}.")
    if order_type not in ("FAK", "FOK"):
        raise UserInputError(f"order_type must be 'FAK' or 'FOK', got {order_type!r}.")
    if side == "BUY":
        if amount is None:
            raise UserInputError("amount is required for BUY market orders.")
        if shares is not None:
            raise UserInputError("shares must not be set for BUY market orders.")
        validated_amount = coerce_positive_decimal("amount", amount)
        validated_max_spend = (
            coerce_positive_decimal("max_spend", max_spend) if max_spend is not None else None
        )
        return PrepareMarketOrderParams(
            token_id=validated_token,
            side=side,
            order_type=order_type,
            amount=validated_amount,
            max_spend=validated_max_spend,
        )
    if shares is None:
        raise UserInputError("shares is required for SELL market orders.")
    if amount is not None:
        raise UserInputError("amount must not be set for SELL market orders.")
    if max_spend is not None:
        raise UserInputError("max_spend is only valid for BUY market orders.")
    return PrepareMarketOrderParams(
        token_id=validated_token,
        side=side,
        order_type=order_type,
        shares=coerce_positive_decimal("shares", shares),
    )


async def prepare_market_order_draft(
    ctx: AsyncSecureClientContext, params: PrepareMarketOrderParams
) -> OrderDraft:
    tick_size = await fetch_tick_size(ctx, token_id=params.token_id)
    notional = params.amount if params.side == "BUY" else params.shares
    assert notional is not None
    price = await resolve_estimated_market_price(
        ctx,
        token_id=params.token_id,
        side=params.side,
        notional=notional,
        order_type=params.order_type,
        tick_size=tick_size,
    )
    neg_risk = await fetch_neg_risk(ctx, token_id=params.token_id)
    resolved_amount = await _resolve_buy_amount_for_fees(ctx, params, price=price)
    offered, requested = _compute_market_order_amounts(
        amount=resolved_amount, price=price, side=params.side, tick_size=tick_size
    )
    return OrderDraft(
        chain_id=ctx.environment.chain_id,
        exchange_address=resolve_exchange_address(ctx.environment, neg_risk),
        expiration=0,
        funder_address=ctx.wallet,
        offered_amount=offered,
        order_type=params.order_type,
        side=params.side,
        signer=EvmAddress(ctx.signer.address),
        requested_amount=requested,
        token_id=params.token_id,
    )


def _compute_market_order_amounts(
    *, amount: Decimal, price: Decimal, side: OrderSide, tick_size: Decimal
) -> tuple[int, int]:
    config = resolve_rounding_config(tick_size)
    raw_price = round_down(price, config.price)
    raw_maker = round_down(amount, config.size)
    raw_taker = raw_maker / raw_price if side == "BUY" else raw_maker * raw_price
    if decimal_places(raw_taker) > config.amount:
        raw_taker = round_up(raw_taker, config.amount + 4)
        if decimal_places(raw_taker) > config.amount:
            raw_taker = round_down(raw_taker, config.amount)
    return parse_amount(raw_maker), parse_amount(raw_taker)


async def _resolve_buy_amount_for_fees(
    ctx: AsyncSecureClientContext, params: PrepareMarketOrderParams, *, price: Decimal
) -> Decimal:
    if params.side != "BUY" or params.max_spend is None or params.amount is None:
        return params.amount if params.amount is not None else params.shares  # type: ignore[return-value]
    condition_id = await resolve_condition_by_token(ctx, token_id=params.token_id)
    fee_info = await fetch_platform_fee_info(ctx, condition_id=condition_id)
    return adjust_buy_amount_for_fees(
        amount=params.amount, price=price, max_spend=params.max_spend, fee=fee_info
    )


def adjust_buy_amount_for_fees(
    *, amount: Decimal, price: Decimal, max_spend: Decimal, fee: PlatformFeeInfo
) -> Decimal:
    effective_rate = fee.rate * ((price * (Decimal(1) - price)) ** fee.exponent)
    platform_fee = (amount / price) * effective_rate
    total_cost = amount + platform_fee
    if max_spend <= total_cost:
        return max_spend / (Decimal(1) + effective_rate / price)
    return amount


__all__ = [
    "PrepareMarketOrderParams",
    "adjust_buy_amount_for_fees",
    "prepare_market_order_draft",
    "validate_market_order_params",
]
