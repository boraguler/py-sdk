from __future__ import annotations

import asyncio
import time
from typing import assert_never

from polymarket._internal.actions.relayer.calls import (
    TransactionCall,
    encode_proxy_call,
    encode_safe_multisend_call,
)
from polymarket._internal.actions.relayer.nonce import (
    fetch_execute_params,
    fetch_relay_payload,
)
from polymarket._internal.actions.relayer.signing.deposit_wallet import (
    sign_deposit_wallet_batch,
)
from polymarket._internal.actions.relayer.signing.proxy import (
    build_proxy_transaction_hash,
    sign_proxy_message,
)
from polymarket._internal.actions.relayer.signing.safe import sign_safe_transaction
from polymarket._internal.actions.relayer.submit import (
    GASLESS_SUBMIT_RETRY_ATTEMPTS,
    is_retryable_submit_error,
    submit_gasless,
)
from polymarket._internal.context import AsyncSecureClientContext
from polymarket.errors import UserInputError
from polymarket.models.clob.relayer import (
    RelayerExecuteResponse,
    RelayerTransactionType,
)
from polymarket.transactions import GaslessTransactionHandle
from polymarket.types import EvmAddress, HexString

_DEPOSIT_WALLET_DEADLINE_S = 600
_ZERO_ADDRESS: EvmAddress = EvmAddress("0x0000000000000000000000000000000000000000")
_PROXY_RELAYER_FEE = "0"
_PROXY_GAS_PRICE = "0"
_PROXY_DEFAULT_GAS_LIMIT = "1500000"
_SAFE_OPERATION_CALL = 0
_SAFE_OPERATION_DELEGATECALL = 1
_METADATA_MAX_LENGTH = 500


async def prepare_gasless_transaction(
    ctx: AsyncSecureClientContext,
    *,
    calls: list[TransactionCall],
    metadata: str = "",
) -> GaslessTransactionHandle:
    if ctx.api_key is None:
        raise UserInputError(
            "Gasless transactions require a Builder API Key or Relayer API Key. "
            "Pass api_key= when constructing the client."
        )
    if ctx.wallet_type == "EOA":
        raise UserInputError(
            "EOA wallets do not use the relayer in this SDK version. "
            "Direct EOA broadcasting is planned but not yet supported."
        )
    if not calls:
        raise UserInputError("prepare_gasless_transaction requires at least one call")
    if len(metadata) > _METADATA_MAX_LENGTH:
        raise UserInputError(f"metadata must be at most {_METADATA_MAX_LENGTH} characters")

    env = ctx.environment
    retry_delay_s = env.relayer_poll_frequency_ms / 1000
    last_error: BaseException | None = None
    for attempt in range(GASLESS_SUBMIT_RETRY_ATTEMPTS + 1):
        try:
            response = await _submit_for_wallet_type(ctx, calls=calls, metadata=metadata)
            return GaslessTransactionHandle(
                transaction_id=response.transaction_id,
                transaction_hash=response.transaction_hash,
                _relayer=ctx.relayer,
                _max_polls=env.relayer_max_polls,
                _poll_delay_s=env.relayer_poll_frequency_ms / 1000,
            )
        except Exception as error:
            last_error = error
            if attempt == GASLESS_SUBMIT_RETRY_ATTEMPTS or not is_retryable_submit_error(error):
                raise
            await asyncio.sleep(retry_delay_s)
    assert last_error is not None
    raise last_error


async def _submit_for_wallet_type(
    ctx: AsyncSecureClientContext,
    *,
    calls: list[TransactionCall],
    metadata: str,
) -> RelayerExecuteResponse:
    wallet_type = ctx.wallet_type
    if wallet_type == "DEPOSIT_WALLET":
        return await _submit_deposit_wallet(ctx, calls=calls, metadata=metadata)
    if wallet_type == "POLY_PROXY":
        return await _submit_proxy(ctx, calls=calls, metadata=metadata)
    if wallet_type == "GNOSIS_SAFE":
        return await _submit_safe(ctx, calls=calls, metadata=metadata)
    if wallet_type == "EOA":
        raise UserInputError("EOA wallets are not supported by the relayer in this SDK version")
    assert_never(wallet_type)


async def _submit_deposit_wallet(
    ctx: AsyncSecureClientContext,
    *,
    calls: list[TransactionCall],
    metadata: str,
) -> RelayerExecuteResponse:
    params = await fetch_execute_params(
        ctx.relayer, address=ctx.signer.address, type=RelayerTransactionType.WALLET
    )
    deadline = str(int(time.time()) + _DEPOSIT_WALLET_DEADLINE_S)
    signature = sign_deposit_wallet_batch(
        ctx.signer,
        wallet=ctx.wallet,
        calls=calls,
        nonce=params.nonce,
        deadline=deadline,
        chain_id=ctx.environment.chain_id,
    )
    payload = {
        "type": RelayerTransactionType.WALLET.value,
        "from": ctx.signer.address,
        "to": ctx.environment.wallet_derivation.deposit_wallet_factory,
        "nonce": params.nonce,
        "signature": signature,
        "metadata": metadata,
        "depositWalletParams": {
            "depositWallet": str(ctx.wallet),
            "deadline": deadline,
            "calls": [{"target": str(c.to), "value": str(c.value), "data": c.data} for c in calls],
        },
    }
    return await submit_gasless(ctx.relayer, payload=payload)


async def _submit_proxy(
    ctx: AsyncSecureClientContext,
    *,
    calls: list[TransactionCall],
    metadata: str,
) -> RelayerExecuteResponse:
    params = await fetch_relay_payload(
        ctx.relayer, address=ctx.signer.address, type=RelayerTransactionType.PROXY
    )
    to = ctx.environment.wallet_derivation.proxy_factory
    data = encode_proxy_call(calls)
    relay = EvmAddress(params.address)
    gas_limit = await _estimate_proxy_gas_limit(
        ctx, from_address=ctx.signer.address, to=to, data=data
    )
    hash_ = build_proxy_transaction_hash(
        from_address=EvmAddress(ctx.signer.address),
        to=EvmAddress(to),
        data=data,
        relayer_fee=_PROXY_RELAYER_FEE,
        gas_price=_PROXY_GAS_PRICE,
        gas_limit=gas_limit,
        nonce=params.nonce,
        relay_hub=EvmAddress(ctx.environment.relay_hub),
        relay=relay,
    )
    signature = sign_proxy_message(ctx.signer, hash_)
    payload = {
        "type": RelayerTransactionType.PROXY.value,
        "from": ctx.signer.address,
        "to": to,
        "proxyWallet": str(ctx.wallet),
        "data": data,
        "nonce": params.nonce,
        "signature": signature,
        "metadata": metadata,
        "signatureParams": {
            "gasLimit": gas_limit,
            "gasPrice": _PROXY_GAS_PRICE,
            "relay": str(relay),
            "relayHub": ctx.environment.relay_hub,
            "relayerFee": _PROXY_RELAYER_FEE,
        },
    }
    return await submit_gasless(ctx.relayer, payload=payload)


async def _estimate_proxy_gas_limit(
    ctx: AsyncSecureClientContext,
    *,
    from_address: str,
    to: str,
    data: str,
) -> str:
    if ctx.rpc is None:
        return _PROXY_DEFAULT_GAS_LIMIT
    try:
        estimated = await ctx.rpc.eth_estimate_gas(
            {"from": from_address, "to": to, "data": data}
        )
    except Exception:
        return _PROXY_DEFAULT_GAS_LIMIT
    return str(estimated)


async def _submit_safe(
    ctx: AsyncSecureClientContext,
    *,
    calls: list[TransactionCall],
    metadata: str,
) -> RelayerExecuteResponse:
    params = await fetch_execute_params(
        ctx.relayer, address=ctx.signer.address, type=RelayerTransactionType.SAFE
    )

    if len(calls) == 1:
        target = calls[0].to
        data: HexString = calls[0].data
        value = calls[0].value
        operation = _SAFE_OPERATION_CALL
    else:
        target = EvmAddress(ctx.environment.safe_multisend)
        data = encode_safe_multisend_call(calls)
        value = 0
        operation = _SAFE_OPERATION_DELEGATECALL

    signature = sign_safe_transaction(
        ctx.signer,
        safe_address=ctx.wallet,
        to=target,
        data=data,
        value=value,
        operation=operation,
        nonce=params.nonce,
        chain_id=ctx.environment.chain_id,
    )
    payload: dict[str, object] = {
        "type": RelayerTransactionType.SAFE.value,
        "from": ctx.signer.address,
        "to": str(target),
        "proxyWallet": str(ctx.wallet),
        "data": data,
        "nonce": params.nonce,
        "signature": signature,
        "metadata": metadata,
        "signatureParams": {
            "baseGas": "0",
            "gasPrice": "0",
            "gasToken": str(_ZERO_ADDRESS),
            "operation": str(operation),
            "refundReceiver": str(_ZERO_ADDRESS),
            "safeTxnGas": "0",
        },
    }
    if value > 0:
        payload["value"] = str(value)
    return await submit_gasless(ctx.relayer, payload=payload)


async def submit_deposit_wallet_create(
    ctx: AsyncSecureClientContext,
    *,
    metadata: str = "",
) -> GaslessTransactionHandle:
    if ctx.api_key is None:
        raise UserInputError(
            "Gasless transactions require a Builder API Key or Relayer API Key. "
            "Pass api_key= when constructing the client."
        )
    if len(metadata) > _METADATA_MAX_LENGTH:
        raise UserInputError(f"metadata must be at most {_METADATA_MAX_LENGTH} characters")
    payload = {
        "type": RelayerTransactionType.WALLET_CREATE.value,
        "from": ctx.signer.address,
        "to": ctx.environment.wallet_derivation.deposit_wallet_factory,
        "metadata": metadata,
    }
    response = await submit_gasless(ctx.relayer, payload=payload)
    env = ctx.environment
    return GaslessTransactionHandle(
        transaction_id=response.transaction_id,
        transaction_hash=response.transaction_hash,
        _relayer=ctx.relayer,
        _max_polls=env.relayer_max_polls,
        _poll_delay_s=env.relayer_poll_frequency_ms / 1000,
    )


__all__ = ["prepare_gasless_transaction", "submit_deposit_wallet_create"]
