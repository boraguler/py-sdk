from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

from polymarket.models.clob.relayer import TransactionOutcome

if TYPE_CHECKING:
    from polymarket._internal.eoa.rpc import JsonRpcClient, SyncJsonRpcClient
    from polymarket.clients._transport import AsyncTransport, SyncTransport


@dataclass(frozen=True, slots=True)
class GaslessTransactionHandle:
    transaction_id: str
    transaction_hash: str | None
    _relayer: AsyncTransport = field(repr=False)
    _max_polls: int
    _poll_delay_s: float

    async def wait(self) -> TransactionOutcome:
        from polymarket._internal.actions.relayer.poll import poll_until_terminal

        return await poll_until_terminal(
            self._relayer,
            transaction_id=self.transaction_id,
            fallback_hash=self.transaction_hash,
            max_polls=self._max_polls,
            poll_delay_s=self._poll_delay_s,
        )


@dataclass(frozen=True, slots=True)
class EoaTransactionHandle:
    transaction_hash: str
    _rpc: JsonRpcClient = field(repr=False)
    _max_polls: int
    _poll_delay_s: float

    @property
    def transaction_id(self) -> None:
        return None

    async def wait(self) -> TransactionOutcome:
        from polymarket._internal.eoa.broadcast import wait_for_receipt

        return await wait_for_receipt(
            self._rpc,
            transaction_hash=self.transaction_hash,
            max_polls=self._max_polls,
            poll_delay_s=self._poll_delay_s,
        )


@dataclass(frozen=True, slots=True)
class SyncGaslessTransactionHandle:
    transaction_id: str
    transaction_hash: str | None
    _relayer: SyncTransport = field(repr=False)
    _max_polls: int
    _poll_delay_s: float

    def wait(self) -> TransactionOutcome:
        from polymarket._internal.actions.relayer.poll import poll_until_terminal_sync

        return poll_until_terminal_sync(
            self._relayer,
            transaction_id=self.transaction_id,
            fallback_hash=self.transaction_hash,
            max_polls=self._max_polls,
            poll_delay_s=self._poll_delay_s,
        )


@dataclass(frozen=True, slots=True)
class SyncEoaTransactionHandle:
    transaction_hash: str
    _rpc: SyncJsonRpcClient = field(repr=False)
    _max_polls: int
    _poll_delay_s: float

    @property
    def transaction_id(self) -> None:
        return None

    def wait(self) -> TransactionOutcome:
        from polymarket._internal.eoa.broadcast import wait_for_receipt_sync

        return wait_for_receipt_sync(
            self._rpc,
            transaction_hash=self.transaction_hash,
            max_polls=self._max_polls,
            poll_delay_s=self._poll_delay_s,
        )


TransactionHandle: TypeAlias = GaslessTransactionHandle | EoaTransactionHandle
SyncTransactionHandle: TypeAlias = SyncGaslessTransactionHandle | SyncEoaTransactionHandle


__all__ = [
    "EoaTransactionHandle",
    "GaslessTransactionHandle",
    "SyncEoaTransactionHandle",
    "SyncGaslessTransactionHandle",
    "SyncTransactionHandle",
    "TransactionHandle",
]
