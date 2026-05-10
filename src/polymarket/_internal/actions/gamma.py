from polymarket._internal.gamma_paths import (
    build_comment_thread_path,
    build_event_path,
    build_event_tags_path,
    build_market_path,
    build_market_tags_path,
    build_related_tag_resources_path,
    build_related_tags_path,
    build_series_path,
    build_tag_path,
)
from polymarket._internal.request import RequestSpec
from polymarket._internal.validation import require_nonempty
from polymarket.errors import UserInputError
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


def get_market_spec(
    *,
    id: str | None,
    slug: str | None,
    url: str | None,
    include_tag: bool | None,
    locale: str | None,
) -> RequestSpec[Market]:
    return RequestSpec(
        service="gamma",
        method="GET",
        path=build_market_path(id=id, slug=slug, url=url),
        params={"include_tag": include_tag, "locale": locale},
        parse=Market.parse_response,
    )


def get_market_tags_spec(id: str) -> RequestSpec[tuple[TagReference, ...]]:
    return RequestSpec(
        service="gamma",
        method="GET",
        path=build_market_tags_path(id),
        parse=TagReference.parse_response_list,
    )


def get_event_spec(
    *,
    id: str | None,
    slug: str | None,
    url: str | None,
    include_best_lines: bool | None,
    include_chat: bool | None,
    include_template: bool | None,
    locale: str | None,
) -> RequestSpec[Event]:
    return RequestSpec(
        service="gamma",
        method="GET",
        path=build_event_path(id=id, slug=slug, url=url),
        params={
            "include_best_lines": include_best_lines,
            "include_chat": include_chat,
            "include_template": include_template,
            "locale": locale,
        },
        parse=Event.parse_response,
    )


def get_event_tags_spec(id: str) -> RequestSpec[tuple[TagReference, ...]]:
    return RequestSpec(
        service="gamma",
        method="GET",
        path=build_event_tags_path(id),
        parse=TagReference.parse_response_list,
    )


def get_series_spec(
    id: str,
    *,
    include_chat: bool | None,
    locale: str | None,
) -> RequestSpec[Series]:
    return RequestSpec(
        service="gamma",
        method="GET",
        path=build_series_path(id),
        params={"include_chat": include_chat, "locale": locale},
        parse=Series.parse_response,
    )


def get_tag_spec(
    *,
    id: str | None,
    slug: str | None,
    include_chat: bool | None,
    include_template: bool | None,
    locale: str | None,
) -> RequestSpec[Tag]:
    if slug is not None and (include_chat is not None or include_template is not None):
        raise UserInputError(
            "include_chat and include_template are only supported for tag id lookup."
        )
    return RequestSpec(
        service="gamma",
        method="GET",
        path=build_tag_path(id=id, slug=slug),
        params={
            "include_chat": include_chat,
            "include_template": include_template,
            "locale": locale,
        },
        parse=Tag.parse_response,
    )


def get_related_tags_spec(
    *,
    id: str | None,
    slug: str | None,
    omit_empty: bool | None,
    status: str | None,
) -> RequestSpec[tuple[RelatedTag, ...]]:
    if slug is not None and (omit_empty is not None or status is not None):
        raise UserInputError("omit_empty and status are only supported for related tag id lookup.")
    return RequestSpec(
        service="gamma",
        method="GET",
        path=build_related_tags_path(id=id, slug=slug),
        params={"omit_empty": omit_empty, "status": status},
        parse=RelatedTag.parse_response_list,
    )


def get_related_tag_resources_spec(
    *,
    id: str | None,
    slug: str | None,
    locale: str | None,
    omit_empty: bool | None,
    status: str | None,
) -> RequestSpec[tuple[Tag, ...]]:
    return RequestSpec(
        service="gamma",
        method="GET",
        path=build_related_tag_resources_path(id=id, slug=slug),
        params={"locale": locale, "omit_empty": omit_empty, "status": status},
        parse=Tag.parse_response_list,
    )


def get_sports_spec() -> RequestSpec[tuple[SportsMetadata, ...]]:
    return RequestSpec(
        service="gamma",
        method="GET",
        path="/sports",
        parse=SportsMetadata.parse_response_list,
    )


def get_sports_market_types_spec() -> RequestSpec[SportsMarketTypes]:
    return RequestSpec(
        service="gamma",
        method="GET",
        path="/sports/market-types",
        parse=SportsMarketTypes.parse_response,
    )


def get_public_profile_spec(address: str) -> RequestSpec[PublicProfile]:
    return RequestSpec(
        service="gamma",
        method="GET",
        path="/public-profile",
        params={"address": require_nonempty("address", address)},
        parse=PublicProfile.parse_response,
    )


def get_comment_thread_spec(
    id: str, *, get_positions: bool | None
) -> RequestSpec[tuple[Comment, ...]]:
    return RequestSpec(
        service="gamma",
        method="GET",
        path=build_comment_thread_path(id),
        params={"get_positions": get_positions},
        parse=Comment.parse_response_list,
    )


__all__ = [
    "get_comment_thread_spec",
    "get_event_spec",
    "get_event_tags_spec",
    "get_market_spec",
    "get_market_tags_spec",
    "get_public_profile_spec",
    "get_related_tag_resources_spec",
    "get_related_tags_spec",
    "get_series_spec",
    "get_sports_market_types_spec",
    "get_sports_spec",
    "get_tag_spec",
]
