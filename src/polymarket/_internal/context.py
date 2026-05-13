from __future__ import annotations

from dataclasses import dataclass

from eth_account.signers.local import LocalAccount

from polymarket.clients._transport import AsyncTransport, SyncTransport
from polymarket.environments import Environment


@dataclass(frozen=True, slots=True)
class SyncClientContext:
    environment: Environment
    gamma: SyncTransport
    data: SyncTransport
    signer: LocalAccount | None = None


@dataclass(frozen=True, slots=True)
class AsyncClientContext:
    environment: Environment
    gamma: AsyncTransport
    data: AsyncTransport
    signer: LocalAccount | None = None


__all__ = ["AsyncClientContext", "SyncClientContext"]
