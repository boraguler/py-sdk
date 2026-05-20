from __future__ import annotations

from dataclasses import dataclass

from eth_account.signers.local import LocalAccount

from polymarket._internal.eoa.rpc import JsonRpcClient
from polymarket._internal.wallet import WalletType
from polymarket.auth import ApiKey
from polymarket.clients._transport import AsyncTransport, SyncTransport
from polymarket.environments import Environment
from polymarket.models.clob import ApiKeyCreds
from polymarket.types import EvmAddress


@dataclass(frozen=True, slots=True)
class SyncClientContext:
    environment: Environment
    gamma: SyncTransport
    data: SyncTransport
    clob: SyncTransport


@dataclass(frozen=True, slots=True)
class SyncSecureClientContext(SyncClientContext):
    signer: LocalAccount


@dataclass(frozen=True, slots=True)
class AsyncClientContext:
    environment: Environment
    gamma: AsyncTransport
    data: AsyncTransport
    clob: AsyncTransport


@dataclass(frozen=True, slots=True)
class AsyncSecureClientContext(AsyncClientContext):
    signer: LocalAccount
    credentials: ApiKeyCreds
    secure_clob: AsyncTransport
    wallet: EvmAddress
    wallet_type: WalletType
    relayer: AsyncTransport
    api_key: ApiKey | None
    rpc: JsonRpcClient | None


__all__ = [
    "AsyncClientContext",
    "AsyncSecureClientContext",
    "SyncClientContext",
    "SyncSecureClientContext",
]
