"""Asynchronous public Polymarket client."""

from urllib.parse import quote

import httpx

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
            response = await client.get(
                f"{self.environment.gamma_url}/markets/{quote(market_id, safe='')}"
            )

        response.raise_for_status()
        return Market.parse_response(response.json())
