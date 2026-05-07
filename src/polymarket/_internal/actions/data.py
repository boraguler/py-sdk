from collections.abc import Sequence
from typing import get_args

from polymarket._internal.data_params import build_data_params
from polymarket._internal.request import RequestSpec
from polymarket.errors import UserInputError
from polymarket.models.data import (
    BuilderVolumeEntry,
    BuilderVolumeTimePeriod,
    LiveVolume,
    MetaHolder,
    OpenInterest,
    PortfolioValue,
    TradedMarketCount,
)

_BUILDER_VOLUME_TIME_PERIODS: tuple[str, ...] = get_args(BuilderVolumeTimePeriod)


def get_event_live_volumes_spec(*, id: str) -> RequestSpec[tuple[LiveVolume, ...]]:
    if not id:
        raise UserInputError("id is required.")
    return RequestSpec(
        service="data",
        method="GET",
        path="/live-volume",
        params={"id": id},
        parse=LiveVolume.parse_response_list,
    )


def get_open_interests_spec(
    *, market: Sequence[str] | None = None
) -> RequestSpec[tuple[OpenInterest, ...]]:
    return RequestSpec(
        service="data",
        method="GET",
        path="/oi",
        params=build_data_params({"market": market}),
        parse=OpenInterest.parse_response_list,
    )


def get_market_holders_spec(
    *,
    market: Sequence[str],
    limit: int | None = None,
    min_balance: int | None = None,
) -> RequestSpec[tuple[MetaHolder, ...]]:
    if not list(market):
        raise UserInputError("market must be a non-empty sequence of condition IDs.")
    if limit is not None and limit < 1:
        raise UserInputError("limit must be a positive integer.")
    if min_balance is not None and min_balance < 0:
        raise UserInputError("min_balance must be non-negative.")
    return RequestSpec(
        service="data",
        method="GET",
        path="/holders",
        params=build_data_params({"market": market, "limit": limit, "minBalance": min_balance}),
        parse=MetaHolder.parse_response_list,
    )


def get_portfolio_values_spec(
    *,
    user: str,
    market: Sequence[str] | None = None,
) -> RequestSpec[tuple[PortfolioValue, ...]]:
    if not user:
        raise UserInputError("user is required.")
    return RequestSpec(
        service="data",
        method="GET",
        path="/value",
        params=build_data_params({"user": user, "market": market}),
        parse=PortfolioValue.parse_response_list,
    )


def get_traded_market_count_spec(*, user: str) -> RequestSpec[TradedMarketCount]:
    if not user:
        raise UserInputError("user is required.")
    return RequestSpec(
        service="data",
        method="GET",
        path="/traded",
        params={"user": user},
        parse=TradedMarketCount.parse_response,
    )


def get_builder_volumes_spec(
    *, time_period: BuilderVolumeTimePeriod | None = None
) -> RequestSpec[tuple[BuilderVolumeEntry, ...]]:
    if time_period is not None and time_period not in _BUILDER_VOLUME_TIME_PERIODS:
        raise UserInputError(
            f"time_period must be one of {_BUILDER_VOLUME_TIME_PERIODS}, got {time_period!r}."
        )
    return RequestSpec(
        service="data",
        method="GET",
        path="/v1/builders/volume",
        params=build_data_params({"timePeriod": time_period}),
        parse=BuilderVolumeEntry.parse_response_list,
    )


__all__ = [
    "get_builder_volumes_spec",
    "get_event_live_volumes_spec",
    "get_market_holders_spec",
    "get_open_interests_spec",
    "get_portfolio_values_spec",
    "get_traded_market_count_spec",
]
