"""Asynchronous secure Polymarket client."""

from types import TracebackType
from typing import Self, cast

from eth_account import Account
from eth_account.signers.local import LocalAccount

from polymarket.clients._transport import AsyncTransport
from polymarket.environments import PRODUCTION, Environment
from polymarket.errors import UserInputError


class AsyncSecureClient:
    """Async client for authenticated Polymarket workflows."""

    def __init__(self, *, private_key: str, environment: Environment = PRODUCTION) -> None:
        if not private_key:
            raise UserInputError("private_key is required")

        self.environment = environment
        self._signer = cast(LocalAccount, Account.from_key(private_key))
        self._gamma = AsyncTransport(base_url=environment.gamma_url)

    @classmethod
    async def create(cls, *, private_key: str, environment: Environment = PRODUCTION) -> Self:
        """Create an authenticated secure client from a private key."""
        client = cls(private_key=private_key, environment=environment)
        return await client._login()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying network transport."""
        await self._gamma.close()

    async def _login(self) -> Self:
        return self
