"""Synchronous public Polymarket client."""

import logging
from collections.abc import Sequence
from types import TracebackType
from typing import Self

from polymarket._internal.actions import data as _data_actions
from polymarket._internal.actions import gamma as _gamma_actions
from polymarket._internal.actions.data import (
    ActivitySortBy,
    ActivityTypeFilter,
    ClosedPositionSortBy,
    MarketPositionSortBy,
    MarketPositionStatus,
    PositionSortBy,
    SortDirection,
    TradeFilterType,
    TradeSide,
)
from polymarket._internal.context import SyncClientContext
from polymarket._internal.dispatch import sync_dispatch, sync_paginate_offset
from polymarket.clients._transport import SyncTransport
from polymarket.environments import PRODUCTION, Environment
from polymarket.errors import RequestRejectedError
from polymarket.models import (
    Comment,
    Event,
    Market,
    PublicProfile,
    RelatedTag,
    Series,
    SportsMarketTypes,
    SportsMetadata,
    Tag,
    TagReference,
)
from polymarket.models.data import (
    Activity,
    BuilderVolumeEntry,
    BuilderVolumeTimePeriod,
    ClosedPosition,
    LeaderboardCategory,
    LeaderboardEntry,
    LeaderboardOrderBy,
    LeaderboardTimePeriod,
    LiveVolume,
    MetaHolder,
    MetaMarketPosition,
    OpenInterest,
    PortfolioValue,
    Position,
    Trade,
    TradedMarketCount,
    TraderLeaderboardEntry,
)
from polymarket.pagination import Paginator


class PublicClient:
    """Client for public Polymarket data workflows.

    Public methods return stable, idiomatic Python SDK objects.
    """

    def __init__(
        self,
        environment: Environment = PRODUCTION,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._ctx = SyncClientContext(
            environment=environment,
            gamma=SyncTransport(base_url=environment.gamma_url, logger=logger),
            data=SyncTransport(base_url=environment.data_url, logger=logger),
        )

    @property
    def environment(self) -> Environment:
        return self._ctx.environment

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying network transports."""
        try:
            self._ctx.gamma.close()
        finally:
            self._ctx.data.close()

    def get_market(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        url: str | None = None,
        include_tag: bool | None = None,
        locale: str | None = None,
    ) -> Market:
        """Get a market."""
        return sync_dispatch(
            self._ctx,
            _gamma_actions.get_market_spec(
                id=id, slug=slug, url=url, include_tag=include_tag, locale=locale
            ),
        )

    def get_market_tags(self, id: str) -> tuple[TagReference, ...]:
        """Get a market's tags."""
        return sync_dispatch(self._ctx, _gamma_actions.get_market_tags_spec(id))

    def get_event(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        url: str | None = None,
        include_best_lines: bool | None = None,
        include_chat: bool | None = None,
        include_template: bool | None = None,
        locale: str | None = None,
    ) -> Event:
        """Get an event."""
        return sync_dispatch(
            self._ctx,
            _gamma_actions.get_event_spec(
                id=id,
                slug=slug,
                url=url,
                include_best_lines=include_best_lines,
                include_chat=include_chat,
                include_template=include_template,
                locale=locale,
            ),
        )

    def get_event_tags(self, id: str) -> tuple[TagReference, ...]:
        """Get an event's tags."""
        return sync_dispatch(self._ctx, _gamma_actions.get_event_tags_spec(id))

    def get_series(
        self,
        id: str,
        *,
        include_chat: bool | None = None,
        locale: str | None = None,
    ) -> Series:
        """Get a series."""
        return sync_dispatch(
            self._ctx,
            _gamma_actions.get_series_spec(id, include_chat=include_chat, locale=locale),
        )

    def get_tag(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        include_chat: bool | None = None,
        include_template: bool | None = None,
        locale: str | None = None,
    ) -> Tag:
        """Get a tag."""
        return sync_dispatch(
            self._ctx,
            _gamma_actions.get_tag_spec(
                id=id,
                slug=slug,
                include_chat=include_chat,
                include_template=include_template,
                locale=locale,
            ),
        )

    def get_related_tags(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        omit_empty: bool | None = None,
        status: str | None = None,
    ) -> tuple[RelatedTag, ...]:
        """Get related tag relationships."""
        return sync_dispatch(
            self._ctx,
            _gamma_actions.get_related_tags_spec(
                id=id, slug=slug, omit_empty=omit_empty, status=status
            ),
        )

    def get_related_tag_resources(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        locale: str | None = None,
        omit_empty: bool | None = None,
        status: str | None = None,
    ) -> tuple[Tag, ...]:
        """Get tag resources linked from related tag relationships."""
        return sync_dispatch(
            self._ctx,
            _gamma_actions.get_related_tag_resources_spec(
                id=id, slug=slug, locale=locale, omit_empty=omit_empty, status=status
            ),
        )

    def get_sports(self) -> tuple[SportsMetadata, ...]:
        """Get available sports metadata."""
        return sync_dispatch(self._ctx, _gamma_actions.get_sports_spec())

    def get_sports_market_types(self) -> SportsMarketTypes:
        """Get available sports market types."""
        return sync_dispatch(self._ctx, _gamma_actions.get_sports_market_types_spec())

    def get_public_profile(self, address: str) -> PublicProfile | None:
        """Get a public profile by wallet address. Returns None if no profile exists."""
        try:
            return sync_dispatch(self._ctx, _gamma_actions.get_public_profile_spec(address))
        except RequestRejectedError as error:
            if error.status == 404:
                return None
            raise

    def get_comment_thread(
        self, id: str, *, get_positions: bool | None = None
    ) -> tuple[Comment, ...]:
        """Get a comment thread by comment ID."""
        return sync_dispatch(
            self._ctx,
            _gamma_actions.get_comment_thread_spec(id, get_positions=get_positions),
        )

    def get_event_live_volumes(self, *, id: str) -> tuple[LiveVolume, ...]:
        return sync_dispatch(self._ctx, _data_actions.get_event_live_volumes_spec(id=id))

    def get_open_interests(
        self, *, market: Sequence[str] | None = None
    ) -> tuple[OpenInterest, ...]:
        return sync_dispatch(self._ctx, _data_actions.get_open_interests_spec(market=market))

    def get_market_holders(
        self,
        *,
        market: Sequence[str],
        limit: int | None = None,
        min_balance: int | None = None,
    ) -> tuple[MetaHolder, ...]:
        return sync_dispatch(
            self._ctx,
            _data_actions.get_market_holders_spec(
                market=market, limit=limit, min_balance=min_balance
            ),
        )

    def get_portfolio_values(
        self, *, user: str, market: Sequence[str] | None = None
    ) -> tuple[PortfolioValue, ...]:
        return sync_dispatch(
            self._ctx, _data_actions.get_portfolio_values_spec(user=user, market=market)
        )

    def get_traded_market_count(self, *, user: str) -> TradedMarketCount:
        return sync_dispatch(self._ctx, _data_actions.get_traded_market_count_spec(user=user))

    def get_builder_volumes(
        self, *, time_period: BuilderVolumeTimePeriod | None = None
    ) -> tuple[BuilderVolumeEntry, ...]:
        return sync_dispatch(
            self._ctx, _data_actions.get_builder_volumes_spec(time_period=time_period)
        )

    def list_positions(
        self,
        *,
        user: str,
        market: Sequence[str] | None = None,
        event_id: Sequence[int] | None = None,
        size_threshold: float | None = None,
        redeemable: bool | None = None,
        mergeable: bool | None = None,
        sort_by: PositionSortBy | None = None,
        sort_direction: SortDirection | None = None,
        title: str | None = None,
        page_size: int = 20,
    ) -> Paginator[Position]:
        spec = _data_actions.list_positions_spec(
            user=user,
            market=market,
            event_id=event_id,
            size_threshold=size_threshold,
            redeemable=redeemable,
            mergeable=mergeable,
            sort_by=sort_by,
            sort_direction=sort_direction,
            title=title,
        )
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_closed_positions(
        self,
        *,
        user: str,
        market: Sequence[str] | None = None,
        event_id: Sequence[int] | None = None,
        title: str | None = None,
        sort_by: ClosedPositionSortBy | None = None,
        sort_direction: SortDirection | None = None,
        page_size: int = 20,
    ) -> Paginator[ClosedPosition]:
        spec = _data_actions.list_closed_positions_spec(
            user=user,
            market=market,
            event_id=event_id,
            title=title,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_market_positions(
        self,
        *,
        market: str,
        user: str | None = None,
        status: MarketPositionStatus | None = None,
        sort_by: MarketPositionSortBy | None = None,
        sort_direction: SortDirection | None = None,
        page_size: int = 20,
    ) -> Paginator[MetaMarketPosition]:
        spec = _data_actions.list_market_positions_spec(
            market=market,
            user=user,
            status=status,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_trades(
        self,
        *,
        user: str | None = None,
        market: Sequence[str] | None = None,
        event_id: Sequence[int] | None = None,
        side: TradeSide | None = None,
        taker_only: bool | None = None,
        filter_type: TradeFilterType | None = None,
        filter_amount: float | None = None,
        page_size: int = 20,
    ) -> Paginator[Trade]:
        spec = _data_actions.list_trades_spec(
            user=user,
            market=market,
            event_id=event_id,
            side=side,
            taker_only=taker_only,
            filter_type=filter_type,
            filter_amount=filter_amount,
        )
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_activity(
        self,
        *,
        user: str,
        market: Sequence[str] | None = None,
        event_id: Sequence[int] | None = None,
        activity_types: Sequence[ActivityTypeFilter] | None = None,
        side: TradeSide | None = None,
        sort_by: ActivitySortBy | None = None,
        sort_direction: SortDirection | None = None,
        start: int | None = None,
        end: int | None = None,
        page_size: int = 20,
    ) -> Paginator[Activity]:
        spec = _data_actions.list_activity_spec(
            user=user,
            market=market,
            event_id=event_id,
            activity_types=activity_types,
            side=side,
            sort_by=sort_by,
            sort_direction=sort_direction,
            start=start,
            end=end,
        )
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_builder_leaderboard(
        self,
        *,
        time_period: LeaderboardTimePeriod | None = None,
        page_size: int = 20,
    ) -> Paginator[LeaderboardEntry]:
        spec = _data_actions.list_builder_leaderboard_spec(time_period=time_period)
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)

    def download_accounting_snapshot(self, *, user: str) -> bytes:
        path, params = _data_actions.build_accounting_snapshot_request(user=user)
        return self._ctx.data.get_bytes(path, params=params)

    def list_trader_leaderboard(
        self,
        *,
        category: LeaderboardCategory | None = None,
        time_period: LeaderboardTimePeriod | None = None,
        order_by: LeaderboardOrderBy | None = None,
        user: str | None = None,
        user_name: str | None = None,
        page_size: int = 20,
    ) -> Paginator[TraderLeaderboardEntry]:
        spec = _data_actions.list_trader_leaderboard_spec(
            category=category,
            time_period=time_period,
            order_by=order_by,
            user=user,
            user_name=user_name,
        )
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)
