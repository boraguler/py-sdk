"""Synchronous public Polymarket client."""

import logging
from collections.abc import Sequence
from types import TracebackType
from typing import Self, TypeVar, assert_never

from polymarket._internal.actions import data as _data_actions
from polymarket._internal.actions import gamma as _gamma_actions
from polymarket._internal.request import RequestSpec, Service
from polymarket.clients._transport import SyncTransport, TransportOptions
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
    BuilderVolumeEntry,
    BuilderVolumeTimePeriod,
    LiveVolume,
    MetaHolder,
    OpenInterest,
    PortfolioValue,
    TradedMarketCount,
)

T = TypeVar("T")


class PublicClient:
    """Client for public Polymarket data workflows.

    Public methods return stable, idiomatic Python SDK objects.
    """

    def __init__(
        self,
        environment: Environment = PRODUCTION,
        *,
        transport_options: TransportOptions | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._environment = environment
        self._gamma = SyncTransport(
            base_url=environment.gamma_url,
            options=transport_options,
            logger=logger,
        )
        self._data = SyncTransport(
            base_url=environment.data_url,
            options=transport_options,
            logger=logger,
        )

    @property
    def environment(self) -> Environment:
        return self._environment

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
        self._gamma.close()
        self._data.close()

    def _dispatch(self, spec: RequestSpec[T]) -> T:
        transport = self._transport_for(spec.service)
        match spec.method:
            case "GET":
                payload = transport.get_json(spec.path, params=spec.params)
            case _ as unreachable:
                assert_never(unreachable)
        return spec.parse(payload)

    def _transport_for(self, service: Service) -> SyncTransport:
        match service:
            case "gamma":
                return self._gamma
            case "data":
                return self._data
            case _ as unreachable:
                assert_never(unreachable)

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
        return self._dispatch(
            _gamma_actions.get_market_spec(
                id=id, slug=slug, url=url, include_tag=include_tag, locale=locale
            )
        )

    def get_market_tags(self, id: str) -> tuple[TagReference, ...]:
        """Get a market's tags."""
        return self._dispatch(_gamma_actions.get_market_tags_spec(id))

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
        return self._dispatch(
            _gamma_actions.get_event_spec(
                id=id,
                slug=slug,
                url=url,
                include_best_lines=include_best_lines,
                include_chat=include_chat,
                include_template=include_template,
                locale=locale,
            )
        )

    def get_event_tags(self, id: str) -> tuple[TagReference, ...]:
        """Get an event's tags."""
        return self._dispatch(_gamma_actions.get_event_tags_spec(id))

    def get_series(
        self,
        id: str,
        *,
        include_chat: bool | None = None,
        locale: str | None = None,
    ) -> Series:
        """Get a series."""
        return self._dispatch(
            _gamma_actions.get_series_spec(id, include_chat=include_chat, locale=locale)
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
        return self._dispatch(
            _gamma_actions.get_tag_spec(
                id=id,
                slug=slug,
                include_chat=include_chat,
                include_template=include_template,
                locale=locale,
            )
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
        return self._dispatch(
            _gamma_actions.get_related_tags_spec(
                id=id, slug=slug, omit_empty=omit_empty, status=status
            )
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
        return self._dispatch(
            _gamma_actions.get_related_tag_resources_spec(
                id=id, slug=slug, locale=locale, omit_empty=omit_empty, status=status
            )
        )

    def get_sports(self) -> tuple[SportsMetadata, ...]:
        """Get available sports metadata."""
        return self._dispatch(_gamma_actions.get_sports_spec())

    def get_sports_market_types(self) -> SportsMarketTypes:
        """Get available sports market types."""
        return self._dispatch(_gamma_actions.get_sports_market_types_spec())

    def get_public_profile(self, address: str) -> PublicProfile | None:
        """Get a public profile by wallet address. Returns None if no profile exists."""
        try:
            return self._dispatch(_gamma_actions.get_public_profile_spec(address))
        except RequestRejectedError as error:
            if error.status == 404:
                return None
            raise

    def get_comment_thread(
        self, id: str, *, get_positions: bool | None = None
    ) -> tuple[Comment, ...]:
        """Get a comment thread by comment ID."""
        return self._dispatch(
            _gamma_actions.get_comment_thread_spec(id, get_positions=get_positions)
        )

    def get_event_live_volumes(self, *, id: str) -> tuple[LiveVolume, ...]:
        return self._dispatch(_data_actions.get_event_live_volumes_spec(id=id))

    def get_open_interests(
        self, *, market: Sequence[str] | None = None
    ) -> tuple[OpenInterest, ...]:
        return self._dispatch(_data_actions.get_open_interests_spec(market=market))

    def get_market_holders(
        self,
        *,
        market: Sequence[str],
        limit: int | None = None,
        min_balance: int | None = None,
    ) -> tuple[MetaHolder, ...]:
        return self._dispatch(
            _data_actions.get_market_holders_spec(
                market=market, limit=limit, min_balance=min_balance
            )
        )

    def get_portfolio_values(
        self, *, user: str, market: Sequence[str] | None = None
    ) -> tuple[PortfolioValue, ...]:
        return self._dispatch(_data_actions.get_portfolio_values_spec(user=user, market=market))

    def get_traded_market_count(self, *, user: str) -> TradedMarketCount:
        return self._dispatch(_data_actions.get_traded_market_count_spec(user=user))

    def get_builder_volumes(
        self, *, time_period: BuilderVolumeTimePeriod | None = None
    ) -> tuple[BuilderVolumeEntry, ...]:
        return self._dispatch(_data_actions.get_builder_volumes_spec(time_period=time_period))
