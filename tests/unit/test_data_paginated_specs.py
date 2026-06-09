import pytest

from polymarket._internal.actions import data as data_actions
from polymarket.errors import UserInputError


def test_list_positions_spec_builds_request() -> None:
    spec = data_actions.list_positions_spec(user="0xWALLET", market=["0xabc", "0xdef"])
    assert spec.service == "data"
    assert spec.path == "/positions"
    assert spec.base_params == {"user": "0xWALLET", "market": "0xabc,0xdef"}


def test_list_positions_spec_rejects_empty_user() -> None:
    with pytest.raises(UserInputError, match="user is required"):
        data_actions.list_positions_spec(user="")


def test_list_positions_spec_rejects_market_and_event_id() -> None:
    with pytest.raises(UserInputError, match="not both"):
        data_actions.list_positions_spec(user="0xWALLET", market=["0xabc"], event_id=[1])


def test_list_positions_spec_rejects_long_title() -> None:
    with pytest.raises(UserInputError, match="100 characters"):
        data_actions.list_positions_spec(user="0xWALLET", title="x" * 101)


def test_list_positions_spec_validates_sort_by() -> None:
    with pytest.raises(UserInputError, match="sort_by"):
        data_actions.list_positions_spec(user="0xWALLET", sort_by="BOGUS")  # type: ignore[arg-type]


def test_list_closed_positions_spec_builds_request() -> None:
    spec = data_actions.list_closed_positions_spec(
        user="0xWALLET", sort_by="REALIZEDPNL", sort_direction="DESC"
    )
    assert spec.path == "/closed-positions"
    assert spec.base_params == {
        "user": "0xWALLET",
        "sortBy": "REALIZEDPNL",
        "sortDirection": "DESC",
    }


def test_list_combo_positions_spec_builds_request() -> None:
    spec = data_actions.list_combo_positions_spec(
        user="0xWALLET",
        status="OPEN",
        condition_id="0x03abc",
        position_id="123",
    )
    assert spec.path == "/v1/positions/combos"
    assert spec.base_params == {
        "user": "0xWALLET",
        "status": "OPEN",
        "combo_condition_id": "0x03abc",
        "combo_position_id": "123",
    }


def test_list_combo_positions_spec_validates_status() -> None:
    with pytest.raises(UserInputError, match="status"):
        data_actions.list_combo_positions_spec(user="0xWALLET", status="CLOSED")  # type: ignore[arg-type]


def test_list_market_positions_spec_requires_market() -> None:
    with pytest.raises(UserInputError, match="market is required"):
        data_actions.list_market_positions_spec(market="")


def test_list_market_positions_spec_validates_status() -> None:
    with pytest.raises(UserInputError, match="status"):
        data_actions.list_market_positions_spec(market="0xabc", status="ACTIVE")  # type: ignore[arg-type]


def test_list_trades_spec_rejects_market_and_event_id() -> None:
    with pytest.raises(UserInputError, match="not both"):
        data_actions.list_trades_spec(market=["0xabc"], event_id=[1])


def test_list_trades_spec_requires_filter_pair() -> None:
    with pytest.raises(UserInputError, match="filter_type and filter_amount"):
        data_actions.list_trades_spec(filter_type="CASH")
    with pytest.raises(UserInputError, match="filter_type and filter_amount"):
        data_actions.list_trades_spec(filter_amount=10.0)


def test_list_trades_spec_accepts_paired_filter() -> None:
    spec = data_actions.list_trades_spec(filter_type="CASH", filter_amount=10.0)
    assert spec.base_params == {"filterType": "CASH", "filterAmount": 10.0}


def test_list_activity_spec_validates_type_entries() -> None:
    with pytest.raises(UserInputError, match="activity_types entries"):
        data_actions.list_activity_spec(user="0xWALLET", activity_types=["BOGUS"])  # type: ignore[list-item]


def test_list_activity_spec_serializes_filters() -> None:
    spec = data_actions.list_activity_spec(
        user="0xWALLET",
        activity_types=["TRADE", "REWARD"],
        sort_by="TIMESTAMP",
        sort_direction="DESC",
    )
    assert spec.path == "/activity"
    assert spec.base_params == {
        "user": "0xWALLET",
        "type": "TRADE,REWARD",
        "sortBy": "TIMESTAMP",
        "sortDirection": "DESC",
    }


def test_list_builder_leaderboard_spec() -> None:
    spec = data_actions.list_builder_leaderboard_spec(time_period="WEEK")
    assert spec.path == "/v1/builders/leaderboard"
    assert spec.base_params == {"timePeriod": "WEEK"}


def test_list_builder_leaderboard_spec_rejects_unknown_time_period() -> None:
    with pytest.raises(UserInputError, match="time_period"):
        data_actions.list_builder_leaderboard_spec(time_period="YEAR")  # type: ignore[arg-type]


def test_list_trader_leaderboard_spec_serializes_all_filters() -> None:
    spec = data_actions.list_trader_leaderboard_spec(
        category="POLITICS",
        time_period="MONTH",
        order_by="PNL",
        user="0xWALLET",
        user_name="alice",
    )
    assert spec.path == "/v1/leaderboard"
    assert spec.base_params == {
        "category": "POLITICS",
        "timePeriod": "MONTH",
        "orderBy": "PNL",
        "user": "0xWALLET",
        "userName": "alice",
    }


def test_list_trader_leaderboard_spec_validates_category() -> None:
    with pytest.raises(UserInputError, match="category"):
        data_actions.list_trader_leaderboard_spec(category="OTHER")  # type: ignore[arg-type]
