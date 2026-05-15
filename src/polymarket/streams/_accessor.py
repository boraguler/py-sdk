from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from polymarket.environments import Environment

if TYPE_CHECKING:
    from polymarket._internal.streams.clob.market import ClobMarketStreamManager


_WEBSOCKET_EXTRA_HINT = (
    "Polymarket streams require the optional websocket dependency. "
    'Install with: pip install "polymarket-sdk[websocket]"'
)


class StreamsAccessor:
    """Lazy entry point for realtime stream managers."""

    def __init__(self, *, environment: Environment, logger: logging.Logger | None = None) -> None:
        self._environment = environment
        self._logger = logger
        self._market: ClobMarketStreamManager | None = None

    @property
    def market(self) -> ClobMarketStreamManager:
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


__all__ = ["StreamsAccessor"]
