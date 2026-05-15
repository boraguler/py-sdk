from polymarket._internal.actions import account as _account_actions
from polymarket._internal.actions.orders.types import OrderDraft
from polymarket._internal.context import AsyncSecureClientContext
from polymarket._internal.wallet import signature_type_for
from polymarket.errors import InsufficientAllowanceError
from polymarket.types import EvmAddress


async def ensure_order_allowance(ctx: AsyncSecureClientContext, draft: OrderDraft) -> None:
    spender = draft.exchange_address
    current = await _fetch_current_allowance(ctx, draft=draft, spender=spender)
    if current >= draft.offered_amount:
        return
    raise InsufficientAllowanceError(
        f"Insufficient on-chain allowance for spender {spender}: "
        f"have {current} base units, need {draft.offered_amount}. "
        "Run an ERC20/ERC1155 approval transaction and try again. "
        "Automatic approval will be available in a future SDK release."
    )


async def _fetch_current_allowance(
    ctx: AsyncSecureClientContext, *, draft: OrderDraft, spender: EvmAddress
) -> int:
    signature_type = signature_type_for(ctx.wallet_type)
    if draft.side == "BUY":
        path, params = _account_actions.build_balance_allowance_request(
            asset_type="COLLATERAL", token_id=None, signature_type=signature_type
        )
    else:
        path, params = _account_actions.build_balance_allowance_request(
            asset_type="CONDITIONAL",
            token_id=draft.token_id,
            signature_type=signature_type,
        )
    balance = _account_actions.parse_balance_allowance(
        await ctx.secure_clob.get_json(path, params=params)
    )
    return _allowance_for_spender(balance.allowances, spender)


def _allowance_for_spender(allowances: dict[str, int], spender: str) -> int:
    target = spender.lower()
    for key, value in allowances.items():
        if key.lower() == target:
            return value
    return 0


__all__ = ["ensure_order_allowance"]
