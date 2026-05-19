from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from polymarket.models.clob.relayer import TransactionOutcome

if TYPE_CHECKING:
    from polymarket.clients._transport import AsyncTransport


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


__all__ = ["GaslessTransactionHandle"]
