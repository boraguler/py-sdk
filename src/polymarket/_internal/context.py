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


@dataclass(frozen=True, slots=True)
class SyncSecureClientContext(SyncClientContext):
    signer: LocalAccount


@dataclass(frozen=True, slots=True)
class AsyncClientContext:
    environment: Environment
    gamma: AsyncTransport
    data: AsyncTransport


@dataclass(frozen=True, slots=True)
class AsyncSecureClientContext(AsyncClientContext):
    signer: LocalAccount


__all__ = [
    "AsyncClientContext",
    "AsyncSecureClientContext",
    "SyncClientContext",
    "SyncSecureClientContext",
]
