"""Asynchronous public Polymarket client."""

import httpx

from polymarket.clients._market_requests import build_market_request_url
from polymarket.environments import PRODUCTION, Environment
from polymarket.models import Market


class AsyncPublicClient:
    """Async client for public Polymarket data workflows.

    Public methods return stable, idiomatic Python SDK objects.
    """

    def __init__(self, environment: Environment = PRODUCTION) -> None:
        self.environment = environment

    async def get_market(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        url: str | None = None,
    ) -> Market:
        """Get a market."""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                build_market_request_url(self.environment, id=id, slug=slug, url=url)
            )

        response.raise_for_status()
        return Market.parse_response(response.json())
