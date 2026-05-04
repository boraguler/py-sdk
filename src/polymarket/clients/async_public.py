"""Asynchronous public Polymarket client."""

import httpx

from polymarket.clients._markets import market_url, parse_market
from polymarket.environments import PRODUCTION, Environment
from polymarket.models import Market


class AsyncPublicClient:
    """Async client for public Polymarket data workflows.

    Public methods return stable, idiomatic Python SDK objects.
    """

    def __init__(self, environment: Environment = PRODUCTION) -> None:
        self.environment = environment

    async def get_market(self, market_id: str) -> Market:
        """Get a market by ID."""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(market_url(self.environment, market_id))

        response.raise_for_status()
        return parse_market(response.json())
