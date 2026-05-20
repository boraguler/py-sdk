from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Mapping
from typing import assert_never

from polymarket._internal.hmac import build_hmac_signature
from polymarket.auth import ApiKey, BuilderApiKey, RelayerApiKey

RelayerHeaderResolver = Callable[[str, str, str | None], Awaitable[Mapping[str, str]]]
SyncRelayerHeaderResolver = Callable[[str, str, str | None], Mapping[str, str]]


def make_relayer_header_resolver(api_key: ApiKey) -> RelayerHeaderResolver:
    if isinstance(api_key, BuilderApiKey):
        creds = api_key

        async def builder_resolver(method: str, path: str, body: str | None) -> Mapping[str, str]:
            timestamp = int(time.time())
            signature = build_hmac_signature(
                secret=creds.secret,
                timestamp=timestamp,
                method=method,
                path=path,
                body=body,
            )
            return {
                "POLY_BUILDER_API_KEY": creds.key,
                "POLY_BUILDER_PASSPHRASE": creds.passphrase,
                "POLY_BUILDER_SIGNATURE": signature,
                "POLY_BUILDER_TIMESTAMP": str(timestamp),
            }

        return builder_resolver

    if isinstance(api_key, RelayerApiKey):  # pyright: ignore[reportUnnecessaryIsInstance]
        headers: Mapping[str, str] = {
            "RELAYER_API_KEY": api_key.key,
            "RELAYER_API_KEY_ADDRESS": str(api_key.address),
        }

        async def relayer_resolver(method: str, path: str, body: str | None) -> Mapping[str, str]:
            return headers

        return relayer_resolver

    assert_never(api_key)


def make_relayer_header_resolver_sync(api_key: ApiKey) -> SyncRelayerHeaderResolver:
    if isinstance(api_key, BuilderApiKey):
        creds = api_key

        def builder_resolver(method: str, path: str, body: str | None) -> Mapping[str, str]:
            timestamp = int(time.time())
            signature = build_hmac_signature(
                secret=creds.secret,
                timestamp=timestamp,
                method=method,
                path=path,
                body=body,
            )
            return {
                "POLY_BUILDER_API_KEY": creds.key,
                "POLY_BUILDER_PASSPHRASE": creds.passphrase,
                "POLY_BUILDER_SIGNATURE": signature,
                "POLY_BUILDER_TIMESTAMP": str(timestamp),
            }

        return builder_resolver

    if isinstance(api_key, RelayerApiKey):  # pyright: ignore[reportUnnecessaryIsInstance]
        headers: Mapping[str, str] = {
            "RELAYER_API_KEY": api_key.key,
            "RELAYER_API_KEY_ADDRESS": str(api_key.address),
        }

        def relayer_resolver(method: str, path: str, body: str | None) -> Mapping[str, str]:
            return headers

        return relayer_resolver

    assert_never(api_key)


__all__ = [
    "RelayerHeaderResolver",
    "SyncRelayerHeaderResolver",
    "make_relayer_header_resolver",
    "make_relayer_header_resolver_sync",
]
