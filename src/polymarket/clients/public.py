"""Synchronous public Polymarket client."""

import httpx

from polymarket.clients._markets import market_url, parse_market
from polymarket.environments import PRODUCTION, Environment
from polymarket.models import Market


class PublicClient:
    """Client for public Polymarket data workflows.

    Public methods return stable, idiomatic Python SDK objects.
    """

    def __init__(self, environment: Environment = PRODUCTION) -> None:
        self.environment = environment

    def get_market(self, market_id: str) -> Market:
        """Get a market by ID."""
        response = httpx.get(market_url(self.environment, market_id), timeout=10)
        response.raise_for_status()
        return parse_market(response.json())
