from datetime import UTC, datetime
from decimal import Decimal

import pytest

from polymarket.errors import UnexpectedResponseError
from polymarket.models.clob._validators import (
    _DecimalFromNumberOrString,  # pyright: ignore[reportPrivateUsage]
)
from polymarket.models.clob.rewards import (
    CurrentReward,
    EarningBreakdown,
    MarketReward,
    MarketRewardConfig,
    TotalUserEarning,
    UserEarning,
    UserRewardsConfig,
    UserRewardsEarning,
)


def test_current_reward_parses_with_all_optional_fields() -> None:
    reward = CurrentReward.parse_response(
        {
            "condition_id": "0xCONDITION",
            "rewards_max_spread": 3.0,
            "rewards_min_size": "100",
            "sponsors_count": 2,
            "sponsored_daily_rate": "50",
            "native_daily_rate": "10",
            "total_daily_rate": "60",
        }
    )
    assert reward.condition_id == "0xCONDITION"
    assert reward.rewards_max_spread == 3.0
    assert reward.rewards_min_size == Decimal("100")
    assert reward.sponsors_count == 2
    assert reward.rewards_config == ()


def test_current_reward_handles_minimal_payload() -> None:
    reward = CurrentReward.parse_response({"condition_id": "0xCONDITION"})
    assert reward.condition_id == "0xCONDITION"
    assert reward.rewards_max_spread is None
    assert reward.sponsors_count is None


def test_market_reward_config_parses_epoch_ms_dates() -> None:
    config = MarketRewardConfig.parse_response(
        {
            "asset_address": "0xUSDC",
            "start_date": 1700000000000,
            "end_date": 1800000000000,
            "rate_per_day": "100",
            "total_rewards": "10000",
        }
    )
    assert config.start_date == datetime.fromtimestamp(1700000000, tz=UTC)
    assert config.end_date == datetime.fromtimestamp(1800000000, tz=UTC)


def test_market_reward_config_allows_omitting_end_date_and_total() -> None:
    config = MarketRewardConfig.parse_response(
        {
            "asset_address": "0xUSDC",
            "start_date": 1700000000000,
            "rate_per_day": "100",
        }
    )
    assert config.end_date is None
    assert config.total_rewards is None


def test_market_reward_parses_full_payload() -> None:
    market = MarketReward.parse_response(
        {
            "condition_id": "0xCONDITION",
            "question": "Q?",
            "tokens": [{"token_id": "8501497", "outcome": "Yes", "price": "0.5"}],
        }
    )
    assert market.question == "Q?"
    assert len(market.tokens) == 1
    assert market.rewards_config == ()


def test_user_earning_parses_decimal_rate_from_number() -> None:
    earning = UserEarning.parse_response(
        {
            "asset_address": "0xUSDC",
            "asset_rate": 0.0001,
            "condition_id": "0xCONDITION",
            "date": 1700000000000,
            "earnings": "5.5",
            "maker_address": "0xMAKER",
        }
    )
    assert earning.asset_rate == Decimal("0.0001")
    assert earning.earnings == Decimal("5.5")


def test_total_user_earning_does_not_carry_condition_id() -> None:
    total = TotalUserEarning.parse_response(
        {
            "asset_address": "0xUSDC",
            "asset_rate": "0.01",
            "date": 1700000000000,
            "earnings": "1000",
            "maker_address": "0xMAKER",
        }
    )
    assert total.asset_address == "0xUSDC"
    assert not hasattr(total, "condition_id")


def test_user_rewards_config_requires_all_fields() -> None:
    with pytest.raises(UnexpectedResponseError):
        UserRewardsConfig.parse_response(
            {
                "asset_address": "0xUSDC",
                "start_date": 1700000000000,
                "rate_per_day": "100",
            }
        )


def test_earning_breakdown_parses_decimal_fields() -> None:
    e = EarningBreakdown.parse_response(
        {"asset_address": "0xUSDC", "asset_rate": "0.001", "earnings": "10"}
    )
    assert e.asset_rate == Decimal("0.001")
    assert e.earnings == Decimal("10")


def test_user_rewards_earning_aggregates_nested_structures() -> None:
    earning = UserRewardsEarning.parse_response(
        {
            "condition_id": "0xCONDITION",
            "earning_percentage": 0.5,
            "earnings": [
                {"asset_address": "0xUSDC", "asset_rate": "0.001", "earnings": "5"},
                {"asset_address": "0xUSDC", "asset_rate": "0.002", "earnings": "10"},
            ],
            "event_slug": "evt",
            "image": "img",
            "maker_address": "0xMAKER",
            "market_competitiveness": 0.75,
            "market_slug": "mkt",
            "question": "Q?",
            "rewards_config": [
                {
                    "asset_address": "0xUSDC",
                    "end_date": 1800000000000,
                    "rate_per_day": "100",
                    "start_date": 1700000000000,
                    "total_rewards": "10000",
                }
            ],
            "rewards_max_spread": 3.0,
            "rewards_min_size": "100",
            "tokens": [{"token_id": "8501497", "outcome": "Yes", "price": "0.5"}],
        }
    )
    assert len(earning.earnings) == 2
    assert len(earning.rewards_config) == 1
    assert earning.rewards_config[0].total_rewards == Decimal("10000")


def test_user_earning_rejects_out_of_range_epoch() -> None:
    with pytest.raises(UnexpectedResponseError):
        UserEarning.parse_response(
            {
                "asset_address": "0xUSDC",
                "asset_rate": "0.01",
                "condition_id": "0xCONDITION",
                "date": 10**18,
                "earnings": "1",
                "maker_address": "0xMAKER",
            }
        )


def test_decimalish_string_accepts_int() -> None:
    from pydantic import BaseModel as _Base

    class Foo(_Base):
        v: _DecimalFromNumberOrString

    assert Foo.model_validate({"v": 10}).v == Decimal("10")


def test_decimalish_string_accepts_float_via_str() -> None:
    from pydantic import BaseModel as _Base

    class Foo(_Base):
        v: _DecimalFromNumberOrString

    assert Foo.model_validate({"v": 0.1}).v == Decimal("0.1")


def test_decimalish_string_accepts_decimal_string() -> None:
    from pydantic import BaseModel as _Base

    class Foo(_Base):
        v: _DecimalFromNumberOrString

    assert Foo.model_validate({"v": "0.001"}).v == Decimal("0.001")


def test_decimalish_string_rejects_bool() -> None:
    from pydantic import BaseModel as _Base
    from pydantic import ValidationError

    class Foo(_Base):
        v: _DecimalFromNumberOrString

    with pytest.raises(ValidationError):
        Foo.model_validate({"v": True})
