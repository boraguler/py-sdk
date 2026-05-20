"""Synchronous secure Polymarket client."""

import logging
import time
from collections.abc import Mapping, Sequence
from decimal import Decimal
from types import TracebackType
from typing import TYPE_CHECKING, Self, cast

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils.address import to_checksum_address

from polymarket._internal.actions import account as _account_actions
from polymarket._internal.actions import auth as _auth_actions
from polymarket._internal.actions import clob as _clob_actions
from polymarket._internal.actions import data as _data_actions
from polymarket._internal.actions import gamma as _gamma_actions
from polymarket._internal.actions import rewards as _rewards_actions
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
from polymarket._internal.actions.orders import cancel as _cancel_actions
from polymarket._internal.actions.orders import post as _post_actions
from polymarket._internal.actions.orders.allowance import ensure_order_allowance_sync
from polymarket._internal.actions.orders.estimate import (
    estimate_market_price_sync as _estimate_market_price_sync,
)
from polymarket._internal.actions.orders.limit import (
    prepare_limit_order_draft_sync,
    validate_limit_order_params,
)
from polymarket._internal.actions.orders.market import (
    prepare_market_order_draft_sync,
    validate_market_order_params,
)
from polymarket._internal.actions.orders.orders import (
    create_signed_order,
    create_unsigned_order,
)
from polymarket._internal.actions.orders.typed_data import (
    build_order_signature,
    build_order_typed_data,
)
from polymarket._internal.actions.orders.types import OrderDraft
from polymarket._internal.context import SyncSecureClientContext
from polymarket._internal.dispatch import (
    sync_dispatch,
    sync_paginate_keyset,
    sync_paginate_offset,
    sync_paginate_page_based,
)
from polymarket._internal.hmac import build_hmac_signature
from polymarket._internal.l1_auth import sign_api_key_auth
from polymarket._internal.wallet import WalletType, classify_wallet_type, signature_type_for
from polymarket.clients._transport import SyncHeaderResolver, SyncTransport
from polymarket.environments import PRODUCTION, Environment
from polymarket.errors import RequestRejectedError, SigningError, UserInputError
from polymarket.models import (
    ApiKeyCreds,
    AssetType,
    BalanceAllowance,
    BuilderFeeRates,
    ClobTrade,
    Comment,
    Event,
    LastTradePrice,
    LastTradePriceForToken,
    Market,
    Notification,
    OpenOrder,
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
from polymarket.models.clob.cancel import CancelOrdersResponse
from polymarket.models.clob.order_response import OrderResponse
from polymarket.models.clob.orders import MarketOrderType, SignedOrder
from polymarket.models.clob.rewards import (
    CurrentReward,
    MarketReward,
    RewardsPercentages,
    TotalUserEarning,
    UserEarning,
    UserRewardsEarning,
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
from polymarket.models.types import ConditionId
from polymarket.pagination import Page, Paginator
from polymarket.types import EvmAddress, HexString

if TYPE_CHECKING:
    from polymarket.clients.public import PublicClient

_CREATE_TOKEN = object()


def _validate_nonce(nonce: object) -> None:
    if isinstance(nonce, bool) or not isinstance(nonce, int):
        raise UserInputError("nonce must be a non-negative integer.")
    if nonce < 0:
        raise UserInputError("nonce must be a non-negative integer.")


class SecureClient:
    def __init__(
        self,
        *,
        ctx: SyncSecureClientContext,
        _create_token: object | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        if _create_token is not _CREATE_TOKEN:
            raise RuntimeError("Use SecureClient.create(...) to create a secure client")
        self._ended = False
        self._ctx_inner = ctx
        self._logger = logger

    @property
    def _ctx(self) -> SyncSecureClientContext:
        if self._ended:
            raise RuntimeError(
                "SecureClient has ended authentication; use the returned PublicClient "
                "or create a new SecureClient."
            )
        return self._ctx_inner

    @_ctx.setter
    def _ctx(self, value: SyncSecureClientContext) -> None:
        self._ctx_inner = value

    @classmethod
    def create(
        cls,
        *,
        private_key: str,
        wallet: str,
        environment: Environment = PRODUCTION,
        credentials: ApiKeyCreds | None = None,
        nonce: int = 0,
        validate_credentials: bool = True,
        logger: logging.Logger | None = None,
    ) -> Self:
        if not private_key:
            raise UserInputError("private_key is required")
        if not wallet:
            raise UserInputError(
                "wallet is required. Pass the signer address itself to authenticate as an EOA."
            )
        _validate_nonce(nonce)
        if credentials is not None and nonce != 0:
            raise UserInputError("nonce cannot be combined with credentials.")
        try:
            signer = cast(LocalAccount, Account.from_key(private_key))
        except (ValueError, TypeError) as error:
            raise UserInputError(f"Invalid private_key: {error}") from error

        try:
            wallet_checksum = to_checksum_address(wallet)
        except ValueError as error:
            raise UserInputError(f"Invalid wallet address: {error}") from error
        wallet_type = classify_wallet_type(
            signer=signer.address,
            wallet=wallet_checksum,
            config=environment.wallet_derivation,
        )
        branded_wallet = cast(EvmAddress, wallet_checksum)

        gamma = SyncTransport(base_url=environment.gamma_url, logger=logger)
        data = SyncTransport(base_url=environment.data_url, logger=logger)
        clob = SyncTransport(base_url=environment.clob_url, logger=logger)

        try:
            resolved_credentials = _bootstrap_credentials_sync(
                environment=environment,
                signer=signer,
                clob=clob,
                provided=credentials,
                nonce=nonce,
                validate=validate_credentials,
                logger=logger,
            )
            secure_clob = SyncTransport(
                base_url=environment.clob_url,
                logger=logger,
                header_resolver=_make_l2_header_resolver_sync(signer, resolved_credentials),
            )
        except BaseException:
            gamma.close()
            data.close()
            clob.close()
            raise

        ctx = SyncSecureClientContext(
            environment=environment,
            gamma=gamma,
            data=data,
            clob=clob,
            signer=signer,
            credentials=resolved_credentials,
            secure_clob=secure_clob,
            wallet=branded_wallet,
            wallet_type=wallet_type,
        )
        return cls(ctx=ctx, _create_token=_CREATE_TOKEN, logger=logger)

    @property
    def environment(self) -> Environment:
        return self._ctx.environment

    @property
    def wallet(self) -> EvmAddress:
        return self._ctx.wallet

    @property
    def signer(self) -> EvmAddress:
        return cast(EvmAddress, self._ctx.signer.address)

    @property
    def wallet_type(self) -> WalletType:
        return self._ctx.wallet_type

    @property
    def credentials(self) -> ApiKeyCreds:
        return self._ctx.credentials

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
        ctx = self._ctx_inner
        try:
            ctx.gamma.close()
        finally:
            try:
                ctx.data.close()
            finally:
                try:
                    ctx.clob.close()
                finally:
                    ctx.secure_clob.close()

    def _user_or_wallet(self, user: str | None) -> str:
        return self._ctx.wallet if user is None else user

    def get_market(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        url: str | None = None,
        include_tag: bool | None = None,
        locale: str | None = None,
    ) -> Market:
        return sync_dispatch(
            self._ctx,
            _gamma_actions.get_market_spec(
                id=id, slug=slug, url=url, include_tag=include_tag, locale=locale
            ),
        )

    def get_market_tags(self, id: str) -> tuple[TagReference, ...]:
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
        return sync_dispatch(self._ctx, _gamma_actions.get_event_tags_spec(id))

    def get_series(
        self,
        id: str,
        *,
        include_chat: bool | None = None,
        locale: str | None = None,
    ) -> Series:
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
        return sync_dispatch(
            self._ctx,
            _gamma_actions.get_related_tag_resources_spec(
                id=id, slug=slug, locale=locale, omit_empty=omit_empty, status=status
            ),
        )

    def get_sports(self) -> tuple[SportsMetadata, ...]:
        return sync_dispatch(self._ctx, _gamma_actions.get_sports_spec())

    def get_sports_market_types(self) -> SportsMarketTypes:
        return sync_dispatch(self._ctx, _gamma_actions.get_sports_market_types_spec())

    def get_public_profile(self, address: str) -> PublicProfile | None:
        try:
            return sync_dispatch(self._ctx, _gamma_actions.get_public_profile_spec(address))
        except RequestRejectedError as error:
            if error.status == 404:
                return None
            raise

    def get_comment_thread(
        self, id: str, *, get_positions: bool | None = None
    ) -> tuple[Comment, ...]:
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
        self,
        *,
        user: str | None = None,
        market: Sequence[str] | None = None,
    ) -> tuple[PortfolioValue, ...]:
        return sync_dispatch(
            self._ctx,
            _data_actions.get_portfolio_values_spec(user=self._user_or_wallet(user), market=market),
        )

    def get_traded_market_count(self, *, user: str | None = None) -> TradedMarketCount:
        return sync_dispatch(
            self._ctx,
            _data_actions.get_traded_market_count_spec(user=self._user_or_wallet(user)),
        )

    def get_builder_volumes(
        self, *, time_period: BuilderVolumeTimePeriod | None = None
    ) -> tuple[BuilderVolumeEntry, ...]:
        return sync_dispatch(
            self._ctx, _data_actions.get_builder_volumes_spec(time_period=time_period)
        )

    def list_positions(
        self,
        *,
        user: str | None = None,
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
            user=self._user_or_wallet(user),
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
        user: str | None = None,
        market: Sequence[str] | None = None,
        event_id: Sequence[int] | None = None,
        title: str | None = None,
        sort_by: ClosedPositionSortBy | None = None,
        sort_direction: SortDirection | None = None,
        page_size: int = 20,
    ) -> Paginator[ClosedPosition]:
        spec = _data_actions.list_closed_positions_spec(
            user=self._user_or_wallet(user),
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
            user=self._user_or_wallet(user),
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
        user: str | None = None,
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
            user=self._user_or_wallet(user),
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

    def download_accounting_snapshot(self, *, user: str | None = None) -> bytes:
        path, params = _data_actions.build_accounting_snapshot_request(
            user=self._user_or_wallet(user)
        )
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
    ) -> Paginator[Event]:
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
        return sync_paginate_keyset(self._ctx, spec, page_size=page_size)

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
    ) -> Paginator[Market]:
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
        return sync_paginate_keyset(self._ctx, spec, page_size=page_size)

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
    ) -> Paginator[Series]:
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
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)

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
    ) -> Paginator[Tag]:
        spec = _gamma_actions.list_tags_spec(
            ascending=ascending,
            include_chat=include_chat,
            include_template=include_template,
            is_carousel=is_carousel,
            locale=locale,
            order=order,
        )
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)

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
    ) -> Paginator[Team]:
        spec = _gamma_actions.list_teams_spec(
            abbreviation=abbreviation,
            ascending=ascending,
            league=league,
            name=name,
            order=order,
            provider_ids=provider_ids,
        )
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)

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
    ) -> Paginator[Comment]:
        spec = _gamma_actions.list_comments_spec(
            parent_entity_id=parent_entity_id,
            parent_entity_type=parent_entity_type,
            ascending=ascending,
            get_positions=get_positions,
            holders_only=holders_only,
            order=order,
        )
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)

    def list_comments_by_user_address(
        self,
        *,
        address: str,
        ascending: bool | None = None,
        order: str | None = None,
        page_size: int = 20,
    ) -> Paginator[Comment]:
        spec = _gamma_actions.list_comments_by_user_address_spec(
            address=address,
            ascending=ascending,
            order=order,
        )
        return sync_paginate_offset(self._ctx, spec, page_size=page_size)

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
    ) -> Paginator[SearchResults]:
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
        return sync_paginate_page_based(self._ctx, spec, page_size=page_size)

    def get_midpoint(self, *, token_id: str) -> Decimal:
        path, params = _clob_actions.build_midpoint_request(token_id=token_id)
        return _clob_actions.parse_midpoint(self._ctx.clob.get_json(path, params=params))

    def get_midpoints(self, *, token_ids: Sequence[str]) -> dict[str, Decimal]:
        path, body = _clob_actions.build_midpoints_request(token_ids=token_ids)
        return _clob_actions.parse_midpoints(self._ctx.clob.post_json(path, json=body))

    def get_price(self, *, token_id: str, side: OrderSide) -> Decimal:
        path, params = _clob_actions.build_price_request(token_id=token_id, side=side)
        return _clob_actions.parse_price(self._ctx.clob.get_json(path, params=params))

    def get_prices(
        self, *, requests: Sequence[PriceRequest]
    ) -> dict[str, dict[OrderSide, Decimal]]:
        path, body = _clob_actions.build_prices_request(requests=requests)
        return _clob_actions.parse_prices(self._ctx.clob.post_json(path, json=body))

    def get_order_book(self, *, token_id: str) -> OrderBook:
        path, params = _clob_actions.build_order_book_request(token_id=token_id)
        return _clob_actions.parse_order_book(self._ctx.clob.get_json(path, params=params))

    def get_order_books(self, *, token_ids: Sequence[str]) -> tuple[OrderBook, ...]:
        path, body = _clob_actions.build_order_books_request(token_ids=token_ids)
        return _clob_actions.parse_order_books(self._ctx.clob.post_json(path, json=body))

    def get_spread(self, *, token_id: str) -> Decimal:
        path, params = _clob_actions.build_spread_request(token_id=token_id)
        return _clob_actions.parse_spread(self._ctx.clob.get_json(path, params=params))

    def get_spreads(self, *, token_ids: Sequence[str]) -> dict[str, Decimal]:
        path, body = _clob_actions.build_spreads_request(token_ids=token_ids)
        return _clob_actions.parse_spreads(self._ctx.clob.post_json(path, json=body))

    def get_last_trade_price(self, *, token_id: str) -> LastTradePrice:
        path, params = _clob_actions.build_last_trade_price_request(token_id=token_id)
        return _clob_actions.parse_last_trade_price(self._ctx.clob.get_json(path, params=params))

    def get_last_trade_prices(
        self, *, token_ids: Sequence[str]
    ) -> tuple[LastTradePriceForToken, ...]:
        path, body = _clob_actions.build_last_trade_prices_request(token_ids=token_ids)
        return _clob_actions.parse_last_trade_prices(self._ctx.clob.post_json(path, json=body))

    def get_price_history(
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
        return _clob_actions.parse_price_history(self._ctx.clob.get_json(path, params=params))

    def estimate_market_price(
        self,
        *,
        token_id: str,
        side: OrderSide,
        amount: Decimal | int | float | str | None = None,
        shares: Decimal | int | float | str | None = None,
        order_type: MarketOrderType = "FOK",
    ) -> Decimal:
        return _estimate_market_price_sync(
            self._ctx,
            token_id=token_id,
            side=side,
            amount=amount,
            shares=shares,
            order_type=order_type,
        )

    def list_current_rewards(self, *, sponsored: bool | None = None) -> Paginator[CurrentReward]:
        def fetch(cursor: str | None) -> Page[CurrentReward]:
            path, params = _rewards_actions.build_list_current_rewards_request(
                sponsored=sponsored, cursor=cursor
            )
            return _rewards_actions.parse_current_rewards_page(
                self._ctx.clob.get_json(path, params=params)
            )

        return Paginator(fetch=fetch)

    def list_market_rewards(
        self, *, condition_id: str, sponsored: bool | None = None
    ) -> Paginator[MarketReward]:
        def fetch(cursor: str | None) -> Page[MarketReward]:
            path, params = _rewards_actions.build_list_market_rewards_request(
                condition_id=ConditionId(condition_id), sponsored=sponsored, cursor=cursor
            )
            return _rewards_actions.parse_market_rewards_page(
                self._ctx.clob.get_json(path, params=params)
            )

        return Paginator(fetch=fetch)

    def fetch_api_keys(self) -> tuple[str, ...]:
        return _auth_actions.fetch_api_keys_sync(self._ctx.secure_clob)

    def delete_api_key(self) -> None:
        _auth_actions.delete_api_key_sync(self._ctx.secure_clob)

    def end_authentication(self) -> "PublicClient":
        from polymarket.clients.public import PublicClient

        environment = self._ctx.environment
        try:
            self.delete_api_key()
        except RequestRejectedError as error:
            if error.status not in (401, 404):
                raise
        finally:
            self.close()
            self._ended = True
        return PublicClient(environment=environment)

    def get_closed_only_mode(self) -> bool:
        path, params = _account_actions.build_closed_only_mode_request()
        return _account_actions.parse_closed_only_mode(
            self._ctx.secure_clob.get_json(path, params=params)
        )

    def list_open_orders(
        self,
        *,
        token_id: str | None = None,
        id: str | None = None,
        market: str | None = None,
    ) -> Paginator[OpenOrder]:
        def fetch(cursor: str | None) -> Page[OpenOrder]:
            path, params = _account_actions.build_list_open_orders_request(
                token_id=token_id, id=id, market=market, cursor=cursor
            )
            payload = self._ctx.secure_clob.get_json(path, params=params)
            return _account_actions.parse_open_orders_page(payload)

        return Paginator(fetch=fetch)

    def get_order(self, *, order_id: str) -> OpenOrder:
        path, params = _account_actions.build_get_order_request(order_id=order_id)
        return _account_actions.parse_open_order(
            self._ctx.secure_clob.get_json(path, params=params)
        )

    def list_account_trades(
        self,
        *,
        token_id: str | None = None,
        id: str | None = None,
        market: str | None = None,
        maker_address: str | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> Paginator[ClobTrade]:
        def fetch(cursor: str | None) -> Page[ClobTrade]:
            path, params = _account_actions.build_list_account_trades_request(
                token_id=token_id,
                id=id,
                market=market,
                maker_address=maker_address,
                after=after,
                before=before,
                cursor=cursor,
            )
            payload = self._ctx.secure_clob.get_json(path, params=params)
            return _account_actions.parse_account_trades_page(payload)

        return Paginator(fetch=fetch)

    def get_notifications(self) -> tuple[Notification, ...]:
        path, params = _account_actions.build_notifications_request(
            signature_type=signature_type_for(self._ctx.wallet_type)
        )
        return _account_actions.parse_notifications(
            self._ctx.secure_clob.get_json(path, params=params)
        )

    def drop_notifications(self, *, ids: Sequence[int | str]) -> None:
        path, params = _account_actions.build_drop_notifications_request(
            ids=ids, signature_type=signature_type_for(self._ctx.wallet_type)
        )
        self._ctx.secure_clob.delete(path, params=params)

    def get_balance_allowance(
        self, *, asset_type: AssetType, token_id: str | None = None
    ) -> BalanceAllowance:
        path, params = _account_actions.build_balance_allowance_request(
            asset_type=asset_type,
            token_id=token_id,
            signature_type=signature_type_for(self._ctx.wallet_type),
        )
        return _account_actions.parse_balance_allowance(
            self._ctx.secure_clob.get_json(path, params=params)
        )

    def create_limit_order(
        self,
        *,
        token_id: str,
        price: Decimal | int | float | str,
        size: Decimal | int | float | str,
        side: OrderSide,
        post_only: bool = False,
        expiration: int | None = None,
        builder_code: str | None = None,
    ) -> SignedOrder:
        return self._prepare_and_sign_limit_order(
            token_id=token_id,
            price=price,
            size=size,
            side=side,
            post_only=post_only,
            expiration=expiration,
            builder_code=builder_code,
        )

    def create_market_order(
        self,
        *,
        token_id: str,
        side: OrderSide,
        amount: Decimal | int | float | str | None = None,
        shares: Decimal | int | float | str | None = None,
        max_spend: Decimal | int | float | str | None = None,
        order_type: MarketOrderType = "FAK",
        builder_code: str | None = None,
    ) -> SignedOrder:
        return self._prepare_and_sign_market_order(
            token_id=token_id,
            side=side,
            amount=amount,
            shares=shares,
            max_spend=max_spend,
            order_type=order_type,
            builder_code=builder_code,
        )

    def place_limit_order(
        self,
        *,
        token_id: str,
        price: Decimal | int | float | str,
        size: Decimal | int | float | str,
        side: OrderSide,
        post_only: bool = False,
        expiration: int | None = None,
        builder_code: str | None = None,
    ) -> OrderResponse:
        signed = self._prepare_and_sign_limit_order(
            token_id=token_id,
            price=price,
            size=size,
            side=side,
            post_only=post_only,
            expiration=expiration,
            builder_code=builder_code,
        )
        return self.post_order(signed)

    def place_market_order(
        self,
        *,
        token_id: str,
        side: OrderSide,
        amount: Decimal | int | float | str | None = None,
        shares: Decimal | int | float | str | None = None,
        max_spend: Decimal | int | float | str | None = None,
        order_type: MarketOrderType = "FAK",
        builder_code: str | None = None,
    ) -> OrderResponse:
        signed = self._prepare_and_sign_market_order(
            token_id=token_id,
            side=side,
            amount=amount,
            shares=shares,
            max_spend=max_spend,
            order_type=order_type,
            builder_code=builder_code,
        )
        return self.post_order(signed)

    def get_builder_fee_rates(self, builder_code: str) -> BuilderFeeRates:
        from polymarket._internal.actions.orders.market_data import fetch_builder_fee_rates_sync

        return fetch_builder_fee_rates_sync(self._ctx, builder_code=builder_code)

    def post_order(self, signed_order: SignedOrder) -> OrderResponse:
        path, payload = _post_actions.build_post_order_request(
            signed_order, owner_api_key=self._ctx.credentials.key
        )
        return _post_actions.parse_order_response(
            self._ctx.secure_clob.post_json(path, json=payload)
        )

    def post_orders(self, signed_orders: Sequence[SignedOrder]) -> tuple[OrderResponse, ...]:
        path, payload = _post_actions.build_post_orders_request(
            signed_orders, owner_api_key=self._ctx.credentials.key
        )
        return _post_actions.parse_order_responses(
            self._ctx.secure_clob.post_json(path, json=payload)
        )

    def cancel_order(self, *, order_id: str) -> CancelOrdersResponse:
        path, body = _cancel_actions.build_cancel_order_request(order_id=order_id)
        return _cancel_actions.parse_cancel_orders_response(
            self._ctx.secure_clob.delete_json(path, json=body)
        )

    def cancel_orders(self, *, order_ids: Sequence[str]) -> CancelOrdersResponse:
        path, body = _cancel_actions.build_cancel_orders_request(order_ids=order_ids)
        return _cancel_actions.parse_cancel_orders_response(
            self._ctx.secure_clob.delete_json(path, json=body)
        )

    def cancel_all(self) -> CancelOrdersResponse:
        path, body = _cancel_actions.build_cancel_all_request()
        return _cancel_actions.parse_cancel_orders_response(
            self._ctx.secure_clob.delete_json(path, json=body)
        )

    def cancel_market_orders(
        self, *, market: str | None = None, token_id: str | None = None
    ) -> CancelOrdersResponse:
        path, body = _cancel_actions.build_cancel_market_orders_request(
            market=market, token_id=token_id
        )
        return _cancel_actions.parse_cancel_orders_response(
            self._ctx.secure_clob.delete_json(path, json=body)
        )

    def _prepare_and_sign_limit_order(
        self,
        *,
        token_id: str,
        price: Decimal | int | float | str,
        size: Decimal | int | float | str,
        side: OrderSide,
        post_only: bool,
        expiration: int | None,
        builder_code: str | None,
    ) -> SignedOrder:
        params = validate_limit_order_params(
            token_id=token_id,
            price=price,
            size=size,
            side=side,
            post_only=post_only,
            expiration=expiration,
            builder_code=builder_code,
        )
        draft = prepare_limit_order_draft_sync(self._ctx, params)
        return self._sign_order(draft, post_only=params.post_only)

    def _prepare_and_sign_market_order(
        self,
        *,
        token_id: str,
        side: OrderSide,
        amount: Decimal | int | float | str | None,
        shares: Decimal | int | float | str | None,
        max_spend: Decimal | int | float | str | None,
        order_type: MarketOrderType,
        builder_code: str | None,
    ) -> SignedOrder:
        params = validate_market_order_params(
            token_id=token_id,
            side=side,
            amount=amount,
            shares=shares,
            max_spend=max_spend,
            order_type=order_type,
            builder_code=builder_code,
        )
        draft = prepare_market_order_draft_sync(self._ctx, params)
        return self._sign_order(draft, post_only=False)

    def _sign_order(self, draft: OrderDraft, *, post_only: bool) -> SignedOrder:
        ensure_order_allowance_sync(self._ctx, draft)
        unsigned = create_unsigned_order(
            draft, wallet=self._ctx.wallet, wallet_type=self._ctx.wallet_type
        )
        typed_data = build_order_typed_data(unsigned)
        try:
            signed_message = self._ctx.signer.sign_typed_data(full_message=typed_data)
        except Exception as error:
            raise SigningError(f"Failed to sign order: {error}") from error
        raw_hex = signed_message.signature.hex()
        signature_hex = HexString(raw_hex if raw_hex.startswith("0x") else "0x" + raw_hex)
        final_signature = build_order_signature(unsigned, signature_hex)
        return create_signed_order(unsigned, final_signature, post_only=post_only)

    def get_order_scoring(self, *, order_id: str) -> bool:
        path, params = _rewards_actions.build_get_order_scoring_request(order_id=order_id)
        return _rewards_actions.parse_order_scoring(
            self._ctx.secure_clob.get_json(path, params=params)
        )

    def get_orders_scoring(self, *, order_ids: Sequence[str]) -> dict[str, bool]:
        path, body = _rewards_actions.build_get_orders_scoring_request(order_ids=order_ids)
        return _rewards_actions.parse_orders_scoring(
            self._ctx.secure_clob.post_json(path, json=body)
        )

    def list_user_earnings_for_day(self, *, date: str) -> Paginator[UserEarning]:
        def fetch(cursor: str | None) -> Page[UserEarning]:
            path, params = _rewards_actions.build_list_user_earnings_for_day_request(
                date=date,
                signature_type=signature_type_for(self._ctx.wallet_type),
                cursor=cursor,
            )
            return _rewards_actions.parse_user_earnings_page(
                self._ctx.secure_clob.get_json(path, params=params)
            )

        return Paginator(fetch=fetch)

    def get_total_earnings_for_user_for_day(self, *, date: str) -> tuple[TotalUserEarning, ...]:
        path, params = _rewards_actions.build_total_user_earnings_for_day_request(
            date=date, signature_type=signature_type_for(self._ctx.wallet_type)
        )
        return _rewards_actions.parse_total_user_earnings(
            self._ctx.secure_clob.get_json(path, params=params)
        )

    def list_user_earnings_and_markets_config(
        self,
        *,
        date: str,
        no_competition: bool | None = None,
        order_by: str | None = None,
        position: str | None = None,
        page_size: int | None = None,
    ) -> Paginator[UserRewardsEarning]:
        def fetch(cursor: str | None) -> Page[UserRewardsEarning]:
            path, params = _rewards_actions.build_list_user_earnings_and_markets_config_request(
                date=date,
                signature_type=signature_type_for(self._ctx.wallet_type),
                no_competition=no_competition,
                order_by=order_by,
                position=position,
                page_size=page_size,
                cursor=cursor,
            )
            return _rewards_actions.parse_user_rewards_earnings_page(
                self._ctx.secure_clob.get_json(path, params=params)
            )

        return Paginator(fetch=fetch)

    def get_reward_percentages(self) -> RewardsPercentages:
        path, params = _rewards_actions.build_get_reward_percentages_request(
            signature_type=signature_type_for(self._ctx.wallet_type)
        )
        return _rewards_actions.parse_reward_percentages(
            self._ctx.secure_clob.get_json(path, params=params)
        )


def _bootstrap_credentials_sync(
    *,
    environment: Environment,
    signer: LocalAccount,
    clob: SyncTransport,
    provided: ApiKeyCreds | None,
    nonce: int,
    validate: bool,
    logger: logging.Logger | None,
) -> ApiKeyCreds:
    if provided is not None and (
        not validate
        or _credentials_are_active_sync(
            environment=environment,
            signer=signer,
            credentials=provided,
            logger=logger,
        )
    ):
        return provided

    signature = sign_api_key_auth(
        signer, chain_id=environment.chain_id, timestamp=int(time.time()), nonce=nonce
    )
    return _auth_actions.create_or_derive_api_key_sync(clob, signature)


def _credentials_are_active_sync(
    *,
    environment: Environment,
    signer: LocalAccount,
    credentials: ApiKeyCreds,
    logger: logging.Logger | None,
) -> bool:
    probe = SyncTransport(
        base_url=environment.clob_url,
        logger=logger,
        header_resolver=_make_l2_header_resolver_sync(signer, credentials),
    )
    try:
        keys = _auth_actions.fetch_api_keys_sync(probe)
    except RequestRejectedError as error:
        if error.status == 401:
            return False
        raise
    finally:
        probe.close()
    return credentials.key in keys


def _make_l2_header_resolver_sync(
    signer: LocalAccount, credentials: ApiKeyCreds
) -> SyncHeaderResolver:
    def resolver(method: str, path: str, body: str | None) -> Mapping[str, str]:
        timestamp = int(time.time())
        signature = build_hmac_signature(
            secret=credentials.secret,
            timestamp=timestamp,
            method=method,
            path=path,
            body=body,
        )
        return {
            "POLY_ADDRESS": signer.address,
            "POLY_API_KEY": credentials.key,
            "POLY_PASSPHRASE": credentials.passphrase,
            "POLY_SIGNATURE": signature,
            "POLY_TIMESTAMP": str(timestamp),
        }

    return resolver
