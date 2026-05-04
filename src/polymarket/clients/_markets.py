"""Shared market client helpers."""

from urllib.parse import quote

from polymarket.environments import Environment
from polymarket.models import Market


def market_url(environment: Environment, market_id: str) -> str:
    return f"{environment.gamma_url}/markets/{quote(market_id, safe='')}"


def parse_market(data: object) -> Market:
    return Market.model_validate(data)
