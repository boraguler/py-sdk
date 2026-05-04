"""Public Polymarket client."""

from polymarket.environments import PRODUCTION, Environment


class PublicClient:
    """Client for public Polymarket data workflows.

    Public methods should expose one cohesive read-only interface and avoid
    requiring callers to understand which underlying service provides the data.
    """

    def __init__(self, environment: Environment = PRODUCTION) -> None:
        self.environment = environment
