"""Public Polymarket client."""

from urllib.parse import quote

import httpx

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
        response = httpx.get(
            f"{self.environment.gamma_url}/markets/{quote(market_id, safe='')}",
            timeout=10,
        )
        response.raise_for_status()
        return Market.model_validate(response.json())
