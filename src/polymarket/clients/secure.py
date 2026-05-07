"""Synchronous secure Polymarket client."""

import logging
from typing import Self, cast

from eth_account import Account
from eth_account.signers.local import LocalAccount

from polymarket.clients._transport import TransportOptions
from polymarket.clients.public import PublicClient
from polymarket.environments import PRODUCTION, Environment
from polymarket.errors import UserInputError

_CREATE_TOKEN = object()


class SecureClient(PublicClient):
    def __init__(
        self,
        *,
        private_key: str,
        environment: Environment = PRODUCTION,
        transport_options: TransportOptions | None = None,
        logger: logging.Logger | None = None,
        _create_token: object | None = None,
    ) -> None:
        if _create_token is not _CREATE_TOKEN:
            raise RuntimeError("Use SecureClient.create(...) to create a secure client")
        if not private_key:
            raise UserInputError("private_key is required")

        try:
            signer = cast(LocalAccount, Account.from_key(private_key))
        except (ValueError, TypeError) as error:
            raise UserInputError(f"Invalid private_key: {error}") from error

        super().__init__(
            environment=environment,
            transport_options=transport_options,
            logger=logger,
        )
        self._signer = signer

    @classmethod
    def create(
        cls,
        *,
        private_key: str,
        environment: Environment = PRODUCTION,
        transport_options: TransportOptions | None = None,
        logger: logging.Logger | None = None,
    ) -> Self:
        client = cls(
            private_key=private_key,
            environment=environment,
            transport_options=transport_options,
            logger=logger,
            _create_token=_CREATE_TOKEN,
        )
        try:
            return client._login()
        except BaseException:
            client.close()
            raise

    def _login(self) -> Self:
        return self
