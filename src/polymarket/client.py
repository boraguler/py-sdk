"""Public Polymarket client."""

from dataclasses import dataclass

from polymarket.environments import PRODUCTION, Environment


@dataclass(frozen=True, slots=True)
class PublicClient:
    """Client for public Polymarket data workflows.

    Public methods should expose one cohesive read-only interface and avoid
    requiring callers to understand which underlying service provides the data.
    """

    environment: Environment = PRODUCTION
