"""Synchronous public Polymarket client."""

from polymarket.clients._market_requests import build_market_request_url
from polymarket.clients._transport import SyncTransport
from polymarket.environments import PRODUCTION, Environment
from polymarket.models import Market


class PublicClient:
    """Client for public Polymarket data workflows.

    Public methods return stable, idiomatic Python SDK objects.
    """

    def __init__(self, environment: Environment = PRODUCTION) -> None:
        self.environment = environment
        self._transport = SyncTransport(base_url=environment.gamma_url)

    def get_market(
        self,
        *,
        id: str | None = None,
        slug: str | None = None,
        url: str | None = None,
    ) -> Market:
        """Get a market."""
        payload = self._transport.get_json(build_market_request_url(id=id, slug=slug, url=url))
        return Market.parse_response(payload)
