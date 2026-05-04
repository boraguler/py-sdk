"""Asynchronous public Polymarket client."""

from types import TracebackType
from typing import Self

from polymarket.clients._gamma_requests import (
    build_event_path,
    build_market_path,
    build_related_tag_resources_path,
    build_related_tags_path,
    build_tag_path,
)
from polymarket.clients._transport import AsyncTransport
from polymarket.environments import PRODUCTION, Environment
from polymarket.errors import RequestRejectedError, UserInputError
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


class AsyncPublicClient:
    """Async client for public Polymarket data workflows.

    Public methods return stable, idiomatic Python SDK objects.
    """

    def __init__(self, environment: Environment = PRODUCTION) -> None:
        self.environment = environment
        self._gamma = AsyncTransport(base_url=environment.gamma_url)

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
        """Close the underlying network transport."""
        await self._gamma.close()

    async def get_market(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        url: str | None = None,
        include_tag: bool | None = None,
        locale: str | None = None,
    ) -> Market:
        """Get a market."""
        payload = await self._gamma.get_json(
            build_market_path(id=id, slug=slug, url=url),
            params={"include_tag": include_tag, "locale": locale},
        )
        return Market.parse_response(payload)

    async def get_market_tags(self, id: str) -> tuple[TagReference, ...]:
        """Get a market's tags."""
        payload = await self._gamma.get_json(f"/markets/{id}/tags")
        return TagReference.parse_response_list(payload)

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
        """Get an event."""
        payload = await self._gamma.get_json(
            build_event_path(id=id, slug=slug, url=url),
            params={
                "include_best_lines": include_best_lines,
                "include_chat": include_chat,
                "include_template": include_template,
                "locale": locale,
            },
        )
        return Event.parse_response(payload)

    async def get_event_tags(self, id: str) -> tuple[TagReference, ...]:
        """Get an event's tags."""
        payload = await self._gamma.get_json(f"/events/{id}/tags")
        return TagReference.parse_response_list(payload)

    async def get_series(
        self,
        id: str,
        *,
        include_chat: bool | None = None,
        locale: str | None = None,
    ) -> Series:
        """Get a series."""
        payload = await self._gamma.get_json(
            f"/series/{id}",
            params={"include_chat": include_chat, "locale": locale},
        )
        return Series.parse_response(payload)

    async def get_tag(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        include_chat: bool | None = None,
        include_template: bool | None = None,
        locale: str | None = None,
    ) -> Tag:
        """Get a tag."""
        if slug is not None and (include_chat is not None or include_template is not None):
            raise UserInputError(
                "include_chat and include_template are only supported for tag id lookup."
            )

        payload = await self._gamma.get_json(
            build_tag_path(id=id, slug=slug),
            params={
                "include_chat": include_chat,
                "include_template": include_template,
                "locale": locale,
            },
        )
        return Tag.parse_response(payload)

    async def get_related_tags(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        omit_empty: bool | None = None,
        status: str | None = None,
    ) -> tuple[RelatedTag, ...]:
        """Get related tag relationships."""
        if slug is not None and (omit_empty is not None or status is not None):
            raise UserInputError(
                "omit_empty and status are only supported for related tag id lookup."
            )

        payload = await self._gamma.get_json(
            build_related_tags_path(id=id, slug=slug),
            params={"omit_empty": omit_empty, "status": status},
        )
        return RelatedTag.parse_response_list(payload)

    async def get_related_tag_resources(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        locale: str | None = None,
        omit_empty: bool | None = None,
        status: str | None = None,
    ) -> tuple[Tag, ...]:
        """Get tag resources linked from related tag relationships."""
        payload = await self._gamma.get_json(
            build_related_tag_resources_path(id=id, slug=slug),
            params={"locale": locale, "omit_empty": omit_empty, "status": status},
        )
        return Tag.parse_response_list(payload)

    async def get_sports(self) -> tuple[SportsMetadata, ...]:
        """Get available sports metadata."""
        payload = await self._gamma.get_json("/sports")
        return SportsMetadata.parse_response_list(payload)

    async def get_sports_market_types(self) -> SportsMarketTypes:
        """Get available sports market types."""
        payload = await self._gamma.get_json("/sports/market-types")
        return SportsMarketTypes.parse_response(payload)

    async def get_public_profile(self, address: str) -> PublicProfile | None:
        """Get a public profile by wallet address."""
        try:
            payload = await self._gamma.get_json("/public-profile", params={"address": address})
        except RequestRejectedError as error:
            if error.status == 404:
                return None
            raise

        return PublicProfile.parse_response(payload)

    async def get_comment_thread(
        self, id: str, *, get_positions: bool | None = None
    ) -> tuple[Comment, ...]:
        """Get a comment thread by comment ID."""
        payload = await self._gamma.get_json(
            f"/comments/{id}",
            params={"get_positions": get_positions},
        )
        return Comment.parse_response_list(payload)
