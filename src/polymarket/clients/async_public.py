"""Asynchronous public Polymarket client."""

import logging
from collections.abc import Sequence
from decimal import Decimal
from types import TracebackType
from typing import Self

from polymarket._internal.actions import clob as _clob_actions
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
from polymarket._internal.actions.gamma import (
    CommentParentEntityType,
    Recurrence,
    TagMatch,
)
from polymarket._internal.actions.orders.estimate import (
    estimate_market_price as _estimate_market_price,
)
from polymarket._internal.actions.orders.types import MarketOrderType
from polymarket._internal.context import AsyncClientContext
from polymarket._internal.dispatch import (
    async_dispatch,
    async_paginate_keyset,
    async_paginate_offset,
    async_paginate_page_based,
)
from polymarket.clients._transport import AsyncTransport
from polymarket.environments import PRODUCTION, Environment
from polymarket.errors import RequestRejectedError
from polymarket.models import (
    Comment,
    Event,
    LastTradePrice,
    LastTradePriceForToken,
    Market,
    OrderBook,
    OrderSide,
    PriceHistoryInterval,
    PriceHistoryPoint,
    PriceRequest,
    PublicProfile,
    RelatedTag,
    SearchResults,
    Series,
    SportsMarketTypes,
    SportsMetadata,
    Tag,
    TagReference,
    Team,
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
from polymarket.pagination import AsyncPaginator


class AsyncPublicClient:
    """Async client for public Polymarket data workflows.

    Public methods return stable, idiomatic Python SDK objects.
    """

    def __init__(
        self,
        environment: Environment = PRODUCTION,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._ctx = AsyncClientContext(
            environment=environment,
            gamma=AsyncTransport(base_url=environment.gamma_url, logger=logger),
            data=AsyncTransport(base_url=environment.data_url, logger=logger),
            clob=AsyncTransport(base_url=environment.clob_url, logger=logger),
        )

    @property
    def environment(self) -> Environment:
        return self._ctx.environment

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying network transports."""
        try:
            await self._ctx.gamma.close()
        finally:
            try:
                await self._ctx.data.close()
            finally:
                await self._ctx.clob.close()

    async def get_market(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        url: str | None = None,
        include_tag: bool | None = None,
        locale: str | None = None,
    ) -> Market:
        return await async_dispatch(
            self._ctx,
            _gamma_actions.get_market_spec(
                id=id, slug=slug, url=url, include_tag=include_tag, locale=locale
            ),
        )

    async def get_market_tags(self, id: str) -> tuple[TagReference, ...]:
        return await async_dispatch(self._ctx, _gamma_actions.get_market_tags_spec(id))

    async def get_event(
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
        return await async_dispatch(
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

    async def get_event_tags(self, id: str) -> tuple[TagReference, ...]:
        return await async_dispatch(self._ctx, _gamma_actions.get_event_tags_spec(id))

    async def get_series(
        self,
        id: str,
        *,
        include_chat: bool | None = None,
        locale: str | None = None,
    ) -> Series:
        return await async_dispatch(
            self._ctx,
            _gamma_actions.get_series_spec(id, include_chat=include_chat, locale=locale),
        )

    async def get_tag(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        include_chat: bool | None = None,
        include_template: bool | None = None,
        locale: str | None = None,
    ) -> Tag:
        return await async_dispatch(
            self._ctx,
            _gamma_actions.get_tag_spec(
                id=id,
                slug=slug,
                include_chat=include_chat,
                include_template=include_template,
                locale=locale,
            ),
        )

    async def get_related_tags(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        omit_empty: bool | None = None,
        status: str | None = None,
    ) -> tuple[RelatedTag, ...]:
        return await async_dispatch(
            self._ctx,
            _gamma_actions.get_related_tags_spec(
                id=id, slug=slug, omit_empty=omit_empty, status=status
            ),
        )

    async def get_related_tag_resources(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        locale: str | None = None,
        omit_empty: bool | None = None,
        status: str | None = None,
    ) -> tuple[Tag, ...]:
        return await async_dispatch(
            self._ctx,
            _gamma_actions.get_related_tag_resources_spec(
                id=id, slug=slug, locale=locale, omit_empty=omit_empty, status=status
            ),
        )

    async def get_sports(self) -> tuple[SportsMetadata, ...]:
        return await async_dispatch(self._ctx, _gamma_actions.get_sports_spec())

    async def get_sports_market_types(self) -> SportsMarketTypes:
        return await async_dispatch(self._ctx, _gamma_actions.get_sports_market_types_spec())

    async def get_public_profile(self, address: str) -> PublicProfile | None:
        try:
            return await async_dispatch(self._ctx, _gamma_actions.get_public_profile_spec(address))
        except RequestRejectedError as error:
            if error.status == 404:
                return None
            raise

    async def get_comment_thread(
        self, id: str, *, get_positions: bool | None = None
    ) -> tuple[Comment, ...]:
        return await async_dispatch(
            self._ctx,
            _gamma_actions.get_comment_thread_spec(id, get_positions=get_positions),
        )

    async def get_event_live_volumes(self, *, id: str) -> tuple[LiveVolume, ...]:
        return await async_dispatch(self._ctx, _data_actions.get_event_live_volumes_spec(id=id))

    async def get_open_interests(
        self, *, market: Sequence[str] | None = None
    ) -> tuple[OpenInterest, ...]:
        return await async_dispatch(self._ctx, _data_actions.get_open_interests_spec(market=market))

    async def get_market_holders(
        self,
        *,
        market: Sequence[str],
        limit: int | None = None,
        min_balance: int | None = None,
    ) -> tuple[MetaHolder, ...]:
        return await async_dispatch(
            self._ctx,
            _data_actions.get_market_holders_spec(
                market=market, limit=limit, min_balance=min_balance
            ),
        )

    async def get_portfolio_values(
        self, *, user: str, market: Sequence[str] | None = None
    ) -> tuple[PortfolioValue, ...]:
        return await async_dispatch(
            self._ctx, _data_actions.get_portfolio_values_spec(user=user, market=market)
        )

    async def get_traded_market_count(self, *, user: str) -> TradedMarketCount:
        return await async_dispatch(
            self._ctx, _data_actions.get_traded_market_count_spec(user=user)
        )

    async def get_builder_volumes(
        self, *, time_period: BuilderVolumeTimePeriod | None = None
    ) -> tuple[BuilderVolumeEntry, ...]:
        return await async_dispatch(
            self._ctx, _data_actions.get_builder_volumes_spec(time_period=time_period)
        )

    def list_positions(
        self,
        *,
        user: str,
        market: str | Sequence[str] | None = None,
        event_id: int | Sequence[int] | None = None,
        size_threshold: float | None = None,
        redeemable: bool | None = None,
        mergeable: bool | None = None,
        sort_by: PositionSortBy | None = None,
        sort_direction: SortDirection | None = None,
        title: str | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[Position]:
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
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_closed_positions(
        self,
        *,
        user: str,
        market: str | Sequence[str] | None = None,
        event_id: int | Sequence[int] | None = None,
        title: str | None = None,
        sort_by: ClosedPositionSortBy | None = None,
        sort_direction: SortDirection | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[ClosedPosition]:
        spec = _data_actions.list_closed_positions_spec(
            user=user,
            market=market,
            event_id=event_id,
            title=title,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_market_positions(
        self,
        *,
        market: str,
        user: str | None = None,
        status: MarketPositionStatus | None = None,
        sort_by: MarketPositionSortBy | None = None,
        sort_direction: SortDirection | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[MetaMarketPosition]:
        spec = _data_actions.list_market_positions_spec(
            market=market,
            user=user,
            status=status,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

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
    ) -> AsyncPaginator[Trade]:
        spec = _data_actions.list_trades_spec(
            user=user,
            market=market,
            event_id=event_id,
            side=side,
            taker_only=taker_only,
            filter_type=filter_type,
            filter_amount=filter_amount,
        )
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_activity(
        self,
        *,
        user: str,
        market: str | Sequence[str] | None = None,
        event_id: int | Sequence[int] | None = None,
        activity_types: Sequence[ActivityTypeFilter] | None = None,
        side: TradeSide | None = None,
        sort_by: ActivitySortBy | None = None,
        sort_direction: SortDirection | None = None,
        start: int | None = None,
        end: int | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[Activity]:
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
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_builder_leaderboard(
        self,
        *,
        time_period: LeaderboardTimePeriod | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[LeaderboardEntry]:
        spec = _data_actions.list_builder_leaderboard_spec(time_period=time_period)
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

    async def download_accounting_snapshot(self, *, user: str) -> bytes:
        path, params = _data_actions.build_accounting_snapshot_request(user=user)
        return await self._ctx.data.get_bytes(path, params=params)

    def list_trader_leaderboard(
        self,
        *,
        category: LeaderboardCategory | None = None,
        time_period: LeaderboardTimePeriod | None = None,
        order_by: LeaderboardOrderBy | None = None,
        user: str | None = None,
        user_name: str | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[TraderLeaderboardEntry]:
        spec = _data_actions.list_trader_leaderboard_spec(
            category=category,
            time_period=time_period,
            order_by=order_by,
            user=user,
            user_name=user_name,
        )
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_events(
        self,
        *,
        ascending: bool | None = None,
        closed: bool | None = None,
        cyom: bool | None = None,
        end_date_max: str | None = None,
        end_date_min: str | None = None,
        ended: bool | None = None,
        event_date: str | None = None,
        event_week: int | None = None,
        exclude_tag_ids: int | Sequence[int] | None = None,
        featured: bool | None = None,
        featured_order: bool | None = None,
        game_ids: int | Sequence[int] | None = None,
        ids: int | Sequence[int] | None = None,
        include_best_lines: bool | None = None,
        include_chat: bool | None = None,
        include_children: bool | None = None,
        include_template: bool | None = None,
        liquidity_max: float | None = None,
        liquidity_min: float | None = None,
        live: bool | None = None,
        locale: str | None = None,
        order: str | None = None,
        parent_event_id: int | None = None,
        partner_slug: str | None = None,
        recurrence: Recurrence | None = None,
        related_tags: bool | None = None,
        series_ids: int | Sequence[int] | None = None,
        slug: str | Sequence[str] | None = None,
        start_date_max: str | None = None,
        start_date_min: str | None = None,
        start_time_max: str | None = None,
        start_time_min: str | None = None,
        tag_ids: int | Sequence[int] | None = None,
        tag_match: TagMatch | None = None,
        tag_slug: str | None = None,
        title_search: str | None = None,
        volume_max: float | None = None,
        volume_min: float | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[Event]:
        spec = _gamma_actions.list_events_spec(
            ascending=ascending,
            closed=closed,
            cyom=cyom,
            end_date_max=end_date_max,
            end_date_min=end_date_min,
            ended=ended,
            event_date=event_date,
            event_week=event_week,
            exclude_tag_ids=exclude_tag_ids,
            featured=featured,
            featured_order=featured_order,
            game_ids=game_ids,
            ids=ids,
            include_best_lines=include_best_lines,
            include_chat=include_chat,
            include_children=include_children,
            include_template=include_template,
            liquidity_max=liquidity_max,
            liquidity_min=liquidity_min,
            live=live,
            locale=locale,
            order=order,
            parent_event_id=parent_event_id,
            partner_slug=partner_slug,
            recurrence=recurrence,
            related_tags=related_tags,
            series_ids=series_ids,
            slug=slug,
            start_date_max=start_date_max,
            start_date_min=start_date_min,
            start_time_max=start_time_max,
            start_time_min=start_time_min,
            tag_ids=tag_ids,
            tag_match=tag_match,
            tag_slug=tag_slug,
            title_search=title_search,
            volume_max=volume_max,
            volume_min=volume_min,
        )
        return async_paginate_keyset(self._ctx, spec, page_size=page_size)

    def list_markets(
        self,
        *,
        ascending: bool | None = None,
        closed: bool | None = None,
        clob_token_ids: str | Sequence[str] | None = None,
        condition_ids: str | Sequence[str] | None = None,
        cyom: bool | None = None,
        decimalized: bool | None = None,
        end_date_max: str | None = None,
        end_date_min: str | None = None,
        game_id: str | None = None,
        ids: int | Sequence[int] | None = None,
        include_tag: bool | None = None,
        liquidity_num_max: float | None = None,
        liquidity_num_min: float | None = None,
        locale: str | None = None,
        market_maker_addresses: str | Sequence[str] | None = None,
        order: str | None = None,
        question_ids: str | Sequence[str] | None = None,
        related_tags: bool | None = None,
        rfq_enabled: bool | None = None,
        rewards_min_size: float | None = None,
        slug: str | Sequence[str] | None = None,
        sports_market_types: str | Sequence[str] | None = None,
        start_date_max: str | None = None,
        start_date_min: str | None = None,
        tag_id: int | None = None,
        tag_match: TagMatch | None = None,
        uma_resolution_status: str | None = None,
        volume_num_max: float | None = None,
        volume_num_min: float | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[Market]:
        spec = _gamma_actions.list_markets_spec(
            ascending=ascending,
            closed=closed,
            clob_token_ids=clob_token_ids,
            condition_ids=condition_ids,
            cyom=cyom,
            decimalized=decimalized,
            end_date_max=end_date_max,
            end_date_min=end_date_min,
            game_id=game_id,
            ids=ids,
            include_tag=include_tag,
            liquidity_num_max=liquidity_num_max,
            liquidity_num_min=liquidity_num_min,
            locale=locale,
            market_maker_addresses=market_maker_addresses,
            order=order,
            question_ids=question_ids,
            related_tags=related_tags,
            rfq_enabled=rfq_enabled,
            rewards_min_size=rewards_min_size,
            slug=slug,
            sports_market_types=sports_market_types,
            start_date_max=start_date_max,
            start_date_min=start_date_min,
            tag_id=tag_id,
            tag_match=tag_match,
            uma_resolution_status=uma_resolution_status,
            volume_num_max=volume_num_max,
            volume_num_min=volume_num_min,
        )
        return async_paginate_keyset(self._ctx, spec, page_size=page_size)

    def list_series(
        self,
        *,
        ascending: bool | None = None,
        categories_ids: int | Sequence[int] | None = None,
        categories_labels: str | Sequence[str] | None = None,
        closed: bool | None = None,
        exclude_events: bool | None = None,
        include_chat: bool | None = None,
        locale: str | None = None,
        order: str | None = None,
        recurrence: Recurrence | None = None,
        slug: str | Sequence[str] | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[Series]:
        spec = _gamma_actions.list_series_spec(
            ascending=ascending,
            categories_ids=categories_ids,
            categories_labels=categories_labels,
            closed=closed,
            exclude_events=exclude_events,
            include_chat=include_chat,
            locale=locale,
            order=order,
            recurrence=recurrence,
            slug=slug,
        )
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_tags(
        self,
        *,
        ascending: bool | None = None,
        include_chat: bool | None = None,
        include_template: bool | None = None,
        is_carousel: bool | None = None,
        locale: str | None = None,
        order: str | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[Tag]:
        spec = _gamma_actions.list_tags_spec(
            ascending=ascending,
            include_chat=include_chat,
            include_template=include_template,
            is_carousel=is_carousel,
            locale=locale,
            order=order,
        )
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_teams(
        self,
        *,
        abbreviation: str | Sequence[str] | None = None,
        ascending: bool | None = None,
        league: str | Sequence[str] | None = None,
        name: str | Sequence[str] | None = None,
        order: str | None = None,
        provider_ids: int | Sequence[int] | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[Team]:
        spec = _gamma_actions.list_teams_spec(
            abbreviation=abbreviation,
            ascending=ascending,
            league=league,
            name=name,
            order=order,
            provider_ids=provider_ids,
        )
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_comments(
        self,
        *,
        parent_entity_id: str,
        parent_entity_type: CommentParentEntityType,
        ascending: bool | None = None,
        get_positions: bool | None = None,
        holders_only: bool | None = None,
        order: str | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[Comment]:
        spec = _gamma_actions.list_comments_spec(
            parent_entity_id=parent_entity_id,
            parent_entity_type=parent_entity_type,
            ascending=ascending,
            get_positions=get_positions,
            holders_only=holders_only,
            order=order,
        )
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_comments_by_user_address(
        self,
        *,
        address: str,
        ascending: bool | None = None,
        order: str | None = None,
        page_size: int = 20,
    ) -> AsyncPaginator[Comment]:
        spec = _gamma_actions.list_comments_by_user_address_spec(
            address=address,
            ascending=ascending,
            order=order,
        )
        return async_paginate_offset(self._ctx, spec, page_size=page_size)

    def search(
        self,
        *,
        q: str,
        ascending: bool | None = None,
        cache: bool | None = None,
        events_status: str | None = None,
        events_tag: str | Sequence[str] | None = None,
        exclude_tag_ids: int | Sequence[int] | None = None,
        keep_closed_markets: int | None = None,
        optimized: bool | None = None,
        presets: str | Sequence[str] | None = None,
        recurrence: Recurrence | None = None,
        search_profiles: bool | None = None,
        search_tags: bool | None = None,
        sort: str | None = None,
        page_size: int = 10,
    ) -> AsyncPaginator[SearchResults]:
        spec = _gamma_actions.search_spec(
            q=q,
            ascending=ascending,
            cache=cache,
            events_status=events_status,
            events_tag=events_tag,
            exclude_tag_ids=exclude_tag_ids,
            keep_closed_markets=keep_closed_markets,
            optimized=optimized,
            presets=presets,
            recurrence=recurrence,
            search_profiles=search_profiles,
            search_tags=search_tags,
            sort=sort,
        )
        return async_paginate_page_based(self._ctx, spec, page_size=page_size)

    async def get_midpoint(self, *, token_id: str) -> Decimal:
        path, params = _clob_actions.build_midpoint_request(token_id=token_id)
        return _clob_actions.parse_midpoint(await self._ctx.clob.get_json(path, params=params))

    async def get_midpoints(self, *, token_ids: Sequence[str]) -> dict[str, Decimal]:
        path, body = _clob_actions.build_midpoints_request(token_ids=token_ids)
        return _clob_actions.parse_midpoints(await self._ctx.clob.post_json(path, json=body))

    async def get_price(self, *, token_id: str, side: OrderSide) -> Decimal:
        path, params = _clob_actions.build_price_request(token_id=token_id, side=side)
        return _clob_actions.parse_price(await self._ctx.clob.get_json(path, params=params))

    async def get_prices(
        self, *, requests: Sequence[PriceRequest]
    ) -> dict[str, dict[OrderSide, Decimal]]:
        path, body = _clob_actions.build_prices_request(requests=requests)
        return _clob_actions.parse_prices(await self._ctx.clob.post_json(path, json=body))

    async def get_order_book(self, *, token_id: str) -> OrderBook:
        path, params = _clob_actions.build_order_book_request(token_id=token_id)
        return _clob_actions.parse_order_book(await self._ctx.clob.get_json(path, params=params))

    async def get_order_books(self, *, token_ids: Sequence[str]) -> tuple[OrderBook, ...]:
        path, body = _clob_actions.build_order_books_request(token_ids=token_ids)
        return _clob_actions.parse_order_books(await self._ctx.clob.post_json(path, json=body))

    async def get_spread(self, *, token_id: str) -> Decimal:
        path, params = _clob_actions.build_spread_request(token_id=token_id)
        return _clob_actions.parse_spread(await self._ctx.clob.get_json(path, params=params))

    async def get_spreads(self, *, token_ids: Sequence[str]) -> dict[str, Decimal]:
        path, body = _clob_actions.build_spreads_request(token_ids=token_ids)
        return _clob_actions.parse_spreads(await self._ctx.clob.post_json(path, json=body))

    async def get_last_trade_price(self, *, token_id: str) -> LastTradePrice:
        path, params = _clob_actions.build_last_trade_price_request(token_id=token_id)
        return _clob_actions.parse_last_trade_price(
            await self._ctx.clob.get_json(path, params=params)
        )

    async def get_last_trade_prices(
        self, *, token_ids: Sequence[str]
    ) -> tuple[LastTradePriceForToken, ...]:
        path, body = _clob_actions.build_last_trade_prices_request(token_ids=token_ids)
        return _clob_actions.parse_last_trade_prices(
            await self._ctx.clob.post_json(path, json=body)
        )

    async def get_price_history(
        self,
        *,
        token_id: str,
        start_ts: int | None = None,
        end_ts: int | None = None,
        fidelity: int | None = None,
        interval: PriceHistoryInterval | None = None,
    ) -> tuple[PriceHistoryPoint, ...]:
        path, params = _clob_actions.build_price_history_request(
            token_id=token_id,
            start_ts=start_ts,
            end_ts=end_ts,
            fidelity=fidelity,
            interval=interval,
        )
        return _clob_actions.parse_price_history(await self._ctx.clob.get_json(path, params=params))

    async def estimate_market_price(
        self,
        *,
        token_id: str,
        side: OrderSide,
        amount: Decimal | int | float | str | None = None,
        shares: Decimal | int | float | str | None = None,
        order_type: MarketOrderType = "FOK",
    ) -> Decimal:
        return await _estimate_market_price(
            self._ctx,
            token_id=token_id,
            side=side,
            amount=amount,
            shares=shares,
            order_type=order_type,
        )
