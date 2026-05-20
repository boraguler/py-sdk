from polymarket._internal.actions import account as _account_actions
from polymarket._internal.actions.orders.types import OrderDraft
from polymarket._internal.context import AsyncSecureClientContext, SyncSecureClientContext
from polymarket._internal.request import QueryParamValue
from polymarket._internal.wallet import WalletType, signature_type_for
from polymarket.errors import InsufficientAllowanceError
from polymarket.types import EvmAddress


def _insufficient_allowance_error(spender: EvmAddress, draft: OrderDraft, current: int) -> str:
    return (
        f"Insufficient on-chain allowance for spender {spender}: "
        f"have {current} base units, need {draft.offered_amount}. "
        "Run an ERC20/ERC1155 approval transaction and try again. "
        "Automatic approval will be available in a future SDK release."
    )


async def ensure_order_allowance(ctx: AsyncSecureClientContext, draft: OrderDraft) -> None:
    spender = draft.exchange_address
    current = await _fetch_current_allowance(ctx, draft=draft, spender=spender)
    if current >= draft.offered_amount:
        return
    raise InsufficientAllowanceError(_insufficient_allowance_error(spender, draft, current))


def ensure_order_allowance_sync(ctx: SyncSecureClientContext, draft: OrderDraft) -> None:
    spender = draft.exchange_address
    current = _fetch_current_allowance_sync(ctx, draft=draft, spender=spender)
    if current >= draft.offered_amount:
        return
    raise InsufficientAllowanceError(_insufficient_allowance_error(spender, draft, current))


async def _fetch_current_allowance(
    ctx: AsyncSecureClientContext, *, draft: OrderDraft, spender: EvmAddress
) -> int:
    path, params = _balance_allowance_request_for_draft(ctx.wallet_type, draft=draft)
    balance = _account_actions.parse_balance_allowance(
        await ctx.secure_clob.get_json(path, params=params)
    )
    return _allowance_for_spender(balance.allowances, spender)


def _fetch_current_allowance_sync(
    ctx: SyncSecureClientContext, *, draft: OrderDraft, spender: EvmAddress
) -> int:
    path, params = _balance_allowance_request_for_draft(ctx.wallet_type, draft=draft)
    balance = _account_actions.parse_balance_allowance(
        ctx.secure_clob.get_json(path, params=params)
    )
    return _allowance_for_spender(balance.allowances, spender)


def _balance_allowance_request_for_draft(
    wallet_type: WalletType, *, draft: OrderDraft
) -> tuple[str, dict[str, QueryParamValue]]:
    signature_type = signature_type_for(wallet_type)
    if draft.side == "BUY":
        return _account_actions.build_balance_allowance_request(
            asset_type="COLLATERAL", token_id=None, signature_type=signature_type
        )
    return _account_actions.build_balance_allowance_request(
        asset_type="CONDITIONAL",
        token_id=draft.token_id,
        signature_type=signature_type,
    )


def _allowance_for_spender(allowances: dict[str, int], spender: str) -> int:
    target = spender.lower()
    for key, value in allowances.items():
        if key.lower() == target:
            return value
    return 0


__all__ = ["ensure_order_allowance", "ensure_order_allowance_sync"]
