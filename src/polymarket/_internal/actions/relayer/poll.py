from __future__ import annotations

import asyncio
from typing import cast

from polymarket.clients._transport import AsyncTransport
from polymarket.errors import TimeoutError, TransactionFailedError, UnexpectedResponseError
from polymarket.models.clob.relayer import (
    GaslessTransaction,
    RelayerTransactionState,
    TransactionOutcome,
)
from polymarket.types import TransactionHash

_TERMINAL_SUCCESS = (RelayerTransactionState.MINED, RelayerTransactionState.CONFIRMED)
_TERMINAL_FAILURE = (RelayerTransactionState.FAILED, RelayerTransactionState.INVALID)


async def fetch_gasless_transaction(
    relayer: AsyncTransport, *, transaction_id: str
) -> GaslessTransaction:
    data = await relayer.get_json(f"/v1/account/transactions/{transaction_id}")
    return GaslessTransaction.parse_response(data)


async def poll_until_terminal(
    relayer: AsyncTransport,
    *,
    transaction_id: str,
    fallback_hash: str | None,
    max_polls: int,
    poll_delay_s: float,
) -> TransactionOutcome:
    for _ in range(max_polls):
        tx = await fetch_gasless_transaction(relayer, transaction_id=transaction_id)
        if tx.state in _TERMINAL_SUCCESS:
            tx_hash = tx.transaction_hash or fallback_hash
            if tx_hash is None:
                raise UnexpectedResponseError(
                    f"Transaction {transaction_id} settled without a transaction hash"
                )
            return TransactionOutcome(
                transaction_hash=cast(TransactionHash, tx_hash),
                transaction_id=tx.transaction_id,
            )
        if tx.state in _TERMINAL_FAILURE:
            raise TransactionFailedError(
                tx.error_msg or f"Transaction {transaction_id} reached terminal state {tx.state}"
            )
        await asyncio.sleep(poll_delay_s)
    raise TimeoutError(
        f"Timed out waiting for transaction {transaction_id} after "
        f"{max_polls} polls ({max_polls * poll_delay_s:.0f}s)"
    )


__all__ = ["fetch_gasless_transaction", "poll_until_terminal"]
