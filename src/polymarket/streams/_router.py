# pyright: reportUnnecessaryIsInstance=false
from __future__ import annotations

import contextlib
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from polymarket._internal.streams.handle import AsyncSubscriptionHandle, SubscriptionHandle
from polymarket.environments import Environment
from polymarket.errors import UserInputError
from polymarket.streams._specs import MarketSpec, Subscription

if TYPE_CHECKING:
    from polymarket._internal.streams.clob.market import ClobMarketStreamManager
    from polymarket.models.clob.market_events import MarketEvent


_WEBSOCKET_EXTRA_HINT = (
    "Polymarket streams require the optional websocket dependency. "
    'Install with: pip install "polymarket-sdk[websocket]"'
)


class _StreamsRouter:
    """Routes ``Subscription`` specs to the right internal manager.

    Owns one lazy manager instance per channel; the ``websockets`` extra is
    imported on first use only.
    """

    def __init__(self, *, environment: Environment, logger: logging.Logger | None = None) -> None:
        self._environment = environment
        self._logger = logger
        self._market: ClobMarketStreamManager | None = None

    async def subscribe(
        self, specs: Subscription | Sequence[Subscription]
    ) -> SubscriptionHandle[MarketEvent]:
        normalized = _normalize_specs(specs)
        market_specs = [s for s in normalized if isinstance(s, MarketSpec)]
        if len(market_specs) != len(normalized):
            unknown = next(s for s in normalized if not isinstance(s, MarketSpec))
            raise UserInputError(f"unsupported subscription topic: {unknown.topic!r}")

        manager = self._get_market_manager()
        handles: list[AsyncSubscriptionHandle[MarketEvent]] = []
        try:
            for spec in market_specs:
                handles.append(
                    await manager.subscribe(
                        token_ids=spec.token_ids,
                        custom_feature_enabled=spec.custom_feature_enabled,
                    )
                )
        except BaseException:
            for handle in handles:
                with contextlib.suppress(Exception):
                    await handle.close()
            raise

        if len(handles) == 1:
            return handles[0]
        from polymarket._internal.streams.merged_handle import MergedSubscriptionHandle

        return MergedSubscriptionHandle(handles)

    def _get_market_manager(self) -> ClobMarketStreamManager:
        if self._market is None:
            try:
                from polymarket._internal.streams.clob.market import (
                    ClobMarketStreamManager as _Manager,
                )
            except ImportError as exc:
                raise ImportError(_WEBSOCKET_EXTRA_HINT) from exc
            self._market = _Manager(
                url=self._environment.clob_market_ws_url,
                logger=self._logger,
            )
        return self._market

    async def close(self) -> None:
        if self._market is not None:
            await self._market.close()


def _normalize_specs(
    specs: Subscription | Sequence[Subscription],
) -> list[Subscription]:
    if isinstance(specs, MarketSpec):
        return [specs]
    if not isinstance(specs, Sequence) or isinstance(specs, str | bytes):
        raise UserInputError("subscribe() expects a Subscription or a sequence of Subscriptions")
    items = list(specs)
    if not items:
        raise UserInputError("subscribe() requires at least one subscription")
    for spec in items:
        if not isinstance(spec, MarketSpec):
            raise UserInputError(f"unsupported subscription type: {type(spec).__name__}")
    return items


__all__ = ["_StreamsRouter"]
