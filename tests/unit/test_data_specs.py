import pytest

from polymarket._internal.actions import data as data_actions
from polymarket.errors import UserInputError


def test_get_event_live_volumes_spec_builds_request() -> None:
    spec = data_actions.get_event_live_volumes_spec(id="123")

    assert spec.service == "data"
    assert spec.method == "GET"
    assert spec.path == "/live-volume"
    assert spec.params == {"id": "123"}


def test_get_event_live_volumes_spec_rejects_empty_id() -> None:
    with pytest.raises(UserInputError, match="id is required"):
        data_actions.get_event_live_volumes_spec(id="")


def test_get_open_interests_spec_omits_market_when_absent() -> None:
    spec = data_actions.get_open_interests_spec()

    assert spec.path == "/oi"
    assert spec.params == {}


def test_get_open_interests_spec_joins_market_with_commas() -> None:
    spec = data_actions.get_open_interests_spec(market=["0xabc", "0xdef"])

    assert spec.params == {"market": "0xabc,0xdef"}


def test_get_open_interests_spec_drops_empty_market_sequence() -> None:
    spec = data_actions.get_open_interests_spec(market=[])

    assert spec.params == {}


def test_get_market_holders_spec_builds_request_with_filters() -> None:
    spec = data_actions.get_market_holders_spec(market=["0xabc", "0xdef"], limit=5, min_balance=100)

    assert spec.path == "/holders"
    assert spec.params == {
        "market": "0xabc,0xdef",
        "limit": 5,
        "minBalance": 100,
    }


def test_get_market_holders_spec_rejects_empty_market() -> None:
    with pytest.raises(UserInputError, match="non-empty"):
        data_actions.get_market_holders_spec(market=[])


def test_get_market_holders_spec_omits_optional_filters() -> None:
    spec = data_actions.get_market_holders_spec(market=["0xabc"])

    assert spec.params == {"market": "0xabc"}


def test_get_portfolio_values_spec_builds_request() -> None:
    spec = data_actions.get_portfolio_values_spec(user="0xWALLET", market=["0xabc", "0xdef"])

    assert spec.path == "/value"
    assert spec.params == {"user": "0xWALLET", "market": "0xabc,0xdef"}


def test_get_portfolio_values_spec_rejects_empty_user() -> None:
    with pytest.raises(UserInputError, match="user is required"):
        data_actions.get_portfolio_values_spec(user="")


def test_get_portfolio_values_spec_omits_market_when_absent() -> None:
    spec = data_actions.get_portfolio_values_spec(user="0xWALLET")

    assert spec.params == {"user": "0xWALLET"}


def test_get_traded_market_count_spec_builds_request() -> None:
    spec = data_actions.get_traded_market_count_spec(user="0xWALLET")

    assert spec.path == "/traded"
    assert spec.params == {"user": "0xWALLET"}


def test_get_traded_market_count_spec_rejects_empty_user() -> None:
    with pytest.raises(UserInputError, match="user is required"):
        data_actions.get_traded_market_count_spec(user="")


def test_get_builder_volumes_spec_omits_time_period_when_absent() -> None:
    spec = data_actions.get_builder_volumes_spec()

    assert spec.path == "/v1/builders/volume"
    assert spec.params == {}


def test_get_builder_volumes_spec_includes_time_period() -> None:
    spec = data_actions.get_builder_volumes_spec(time_period="WEEK")

    assert spec.params == {"timePeriod": "WEEK"}


def test_build_accounting_snapshot_request_builds_path_and_params() -> None:
    path, params = data_actions.build_accounting_snapshot_request(user="0xWALLET")
    assert path == "/v1/accounting/snapshot"
    assert params == {"user": "0xWALLET"}


def test_build_accounting_snapshot_request_rejects_empty_user() -> None:
    with pytest.raises(UserInputError, match="user is required"):
        data_actions.build_accounting_snapshot_request(user="")


def test_get_builder_volumes_spec_rejects_unknown_time_period() -> None:
    with pytest.raises(UserInputError, match="time_period must be one of"):
        data_actions.get_builder_volumes_spec(time_period="YEAR")  # type: ignore[arg-type]


def test_get_market_holders_spec_rejects_zero_limit() -> None:
    with pytest.raises(UserInputError, match="limit must be a positive integer"):
        data_actions.get_market_holders_spec(market=["0xabc"], limit=0)


def test_get_market_holders_spec_rejects_negative_min_balance() -> None:
    with pytest.raises(UserInputError, match="min_balance must be non-negative"):
        data_actions.get_market_holders_spec(market=["0xabc"], min_balance=-1)


def test_get_market_holders_spec_accepts_zero_min_balance() -> None:
    spec = data_actions.get_market_holders_spec(market=["0xabc"], min_balance=0)

    assert spec.params == {"market": "0xabc", "minBalance": 0}
