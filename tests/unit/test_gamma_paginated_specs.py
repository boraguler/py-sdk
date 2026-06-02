import pytest

from polymarket._internal.actions import gamma as gamma_actions
from polymarket._internal.request import (
    KeysetPaginatedSpec,
    OffsetPaginatedSpec,
    PageBasedSpec,
)
from polymarket.errors import UserInputError


def test_list_events_spec_default_has_no_params() -> None:
    spec = gamma_actions.list_events_spec()

    assert isinstance(spec, KeysetPaginatedSpec)
    assert spec.service == "gamma"
    assert spec.path == "/events/keyset"
    assert spec.base_params is None


def test_list_events_spec_collects_filter_params() -> None:
    spec = gamma_actions.list_events_spec(
        closed=False, exclude_tag_ids=[1, 2], ids=[10], tag_match="any"
    )

    assert spec.base_params == {
        "closed": False,
        "exclude_tag_id": (1, 2),
        "id": (10,),
        "tag_match": "any",
    }


def test_list_events_spec_rejects_invalid_recurrence() -> None:
    with pytest.raises(UserInputError, match="recurrence must be one of"):
        gamma_actions.list_events_spec(recurrence="yearly")  # type: ignore[arg-type]


def test_list_events_spec_rejects_invalid_tag_match() -> None:
    with pytest.raises(UserInputError, match="tag_match must be one of"):
        gamma_actions.list_events_spec(tag_match="some")  # type: ignore[arg-type]


def test_list_events_spec_omits_empty_sequences() -> None:
    spec = gamma_actions.list_events_spec(ids=[])

    assert spec.base_params is None


def test_list_markets_spec_default_has_no_params() -> None:
    spec = gamma_actions.list_markets_spec()

    assert isinstance(spec, KeysetPaginatedSpec)
    assert spec.service == "gamma"
    assert spec.path == "/markets/keyset"
    assert spec.base_params is None


def test_list_markets_spec_collects_array_params() -> None:
    spec = gamma_actions.list_markets_spec(
        clob_token_ids=["A", "B"], market_maker_addresses=["0xMM"], ids=[1, 2]
    )

    assert spec.base_params == {
        "clob_token_ids": ("A", "B"),
        "market_maker_address": ("0xMM",),
        "id": (1, 2),
    }


def test_list_series_spec_default_has_no_params() -> None:
    spec = gamma_actions.list_series_spec()

    assert isinstance(spec, OffsetPaginatedSpec)
    assert spec.service == "gamma"
    assert spec.path == "/series"
    assert spec.base_params is None


def test_list_series_spec_collects_filter_params() -> None:
    spec = gamma_actions.list_series_spec(closed=False, exclude_events=True, slug=["nba"])

    assert spec.base_params == {"closed": False, "exclude_events": True, "slug": ("nba",)}


def test_list_series_spec_rejects_invalid_recurrence() -> None:
    with pytest.raises(UserInputError, match="recurrence must be one of"):
        gamma_actions.list_series_spec(recurrence="yearly")  # type: ignore[arg-type]


def test_list_tags_spec_default_has_no_params() -> None:
    spec = gamma_actions.list_tags_spec()

    assert isinstance(spec, OffsetPaginatedSpec)
    assert spec.path == "/tags"
    assert spec.base_params is None


def test_list_tags_spec_with_options() -> None:
    spec = gamma_actions.list_tags_spec(include_template=True, locale="en")

    assert spec.base_params == {"include_template": True, "locale": "en"}


def test_list_teams_spec_default_has_no_params() -> None:
    spec = gamma_actions.list_teams_spec()

    assert isinstance(spec, OffsetPaginatedSpec)
    assert spec.path == "/teams"
    assert spec.base_params is None


def test_list_teams_spec_maps_provider_ids_to_singular() -> None:
    spec = gamma_actions.list_teams_spec(league=["NBA"], provider_ids=[7, 8])

    assert spec.base_params == {"league": ("NBA",), "provider_id": (7, 8)}


def test_list_comments_spec_requires_parent_entity_id() -> None:
    with pytest.raises(UserInputError, match="parent_entity_id is required"):
        gamma_actions.list_comments_spec(parent_entity_id="", parent_entity_type="Event")


def test_list_comments_spec_rejects_invalid_entity_type() -> None:
    with pytest.raises(UserInputError, match="parent_entity_type must be one of"):
        gamma_actions.list_comments_spec(
            parent_entity_id="123",
            parent_entity_type="Other",  # type: ignore[arg-type]
        )


def test_list_comments_spec_builds_base_params() -> None:
    spec = gamma_actions.list_comments_spec(
        parent_entity_id="123",
        parent_entity_type="Event",
        get_positions=True,
        holders_only=False,
    )

    assert isinstance(spec, OffsetPaginatedSpec)
    assert spec.path == "/comments"
    assert spec.base_params == {
        "parent_entity_id": "123",
        "parent_entity_type": "Event",
        "get_positions": True,
        "holders_only": False,
    }


def test_list_comments_by_user_address_spec_builds_path_from_address() -> None:
    spec = gamma_actions.list_comments_by_user_address_spec(address="0xUSER", order="DESC")

    assert isinstance(spec, OffsetPaginatedSpec)
    assert spec.path == "/comments/user_address/0xUSER"
    assert spec.base_params == {"order": "DESC"}


def test_list_comments_by_user_address_spec_rejects_empty_address() -> None:
    with pytest.raises(UserInputError, match="address is required"):
        gamma_actions.list_comments_by_user_address_spec(address="")


def test_search_spec_requires_q() -> None:
    with pytest.raises(UserInputError, match="q is required"):
        gamma_actions.search_spec(q="")


def test_search_spec_builds_request_with_filters() -> None:
    spec = gamma_actions.search_spec(
        q="trump",
        ascending=True,
        events_tag=["politics"],
        exclude_tag_ids=[5, 6],
        sort="recent",
    )

    assert isinstance(spec, PageBasedSpec)
    assert spec.service == "gamma"
    assert spec.path == "/public-search"
    assert spec.base_params == {
        "q": "trump",
        "ascending": True,
        "events_tag": ("politics",),
        "exclude_tag_id": (5, 6),
        "sort": "recent",
    }


def test_search_spec_rejects_invalid_recurrence() -> None:
    with pytest.raises(UserInputError, match="recurrence must be one of"):
        gamma_actions.search_spec(q="x", recurrence="yearly")  # type: ignore[arg-type]


def test_list_markets_spec_treats_bare_slug_string_as_single_item() -> None:
    spec = gamma_actions.list_markets_spec(slug="foo")

    assert spec.base_params == {"slug": ("foo",)}


def test_list_markets_spec_accepts_list_of_slugs() -> None:
    spec = gamma_actions.list_markets_spec(slug=["foo", "bar"])

    assert spec.base_params == {"slug": ("foo", "bar")}


def test_list_events_spec_treats_bare_int_id_as_single_item() -> None:
    spec = gamma_actions.list_events_spec(ids=10)

    assert spec.base_params == {"id": (10,)}


def test_list_events_spec_rejects_bytes_param() -> None:
    with pytest.raises(UserInputError, match="does not accept bytes"):
        gamma_actions.list_events_spec(slug=b"foo")  # type: ignore[arg-type]


def test_list_events_spec_rejects_bool_in_int_seq() -> None:
    with pytest.raises(UserInputError, match="got bool"):
        gamma_actions.list_events_spec(ids=True)  # type: ignore[arg-type]


def test_keyset_parser_rejects_missing_items_key() -> None:
    spec = gamma_actions.list_events_spec()
    with pytest.raises(__import__("polymarket").errors.UnexpectedResponseError):
        spec.parse_page({})


def test_keyset_parser_rejects_non_list_items() -> None:
    spec = gamma_actions.list_events_spec()
    with pytest.raises(__import__("polymarket").errors.UnexpectedResponseError):
        spec.parse_page({"events": "not-a-list"})


def test_keyset_parser_rejects_empty_next_cursor() -> None:
    spec = gamma_actions.list_events_spec()
    with pytest.raises(__import__("polymarket").errors.UnexpectedResponseError, match="non-empty"):
        spec.parse_page({"events": [], "next_cursor": ""})


def test_keyset_parser_rejects_non_string_next_cursor() -> None:
    spec = gamma_actions.list_events_spec()
    with pytest.raises(
        __import__("polymarket").errors.UnexpectedResponseError, match="must be a string"
    ):
        spec.parse_page({"events": [], "next_cursor": 123})


def test_keyset_parser_accepts_absent_next_cursor_as_terminal() -> None:
    spec = gamma_actions.list_events_spec()
    payload = spec.parse_page({"events": []})

    assert payload.items == ()
    assert payload.server_next_cursor is None


def test_keyset_parser_accepts_null_next_cursor_as_terminal() -> None:
    spec = gamma_actions.list_events_spec()
    payload = spec.parse_page({"events": [], "next_cursor": None})

    assert payload.server_next_cursor is None


def test_keyset_parser_accepts_valid_next_cursor() -> None:
    spec = gamma_actions.list_events_spec()
    payload = spec.parse_page({"events": [], "next_cursor": "opaque"})

    assert payload.server_next_cursor == "opaque"
