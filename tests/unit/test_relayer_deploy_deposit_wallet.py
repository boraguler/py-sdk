# pyright: reportPrivateUsage=false
import asyncio
from urllib.parse import urlparse

import httpx
import pytest
from _relayer_helpers import (
    install_relayer_routes,
    make_deposit_client,
    make_proxy_client,
    request_json,
)

from polymarket.errors import UserInputError


def test_deploy_deposit_wallet_wire_payload_has_no_signature() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_deposit_client()
        install_relayer_routes(
            client,
            captured,
            {
                "/submit": {
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-dep-create",
                },
            },
        )
        try:
            handle = await client.deploy_deposit_wallet()
            assert handle.transaction_id == "tx-dep-create"
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    body = request_json(submit_calls[0])
    assert body["type"] == "WALLET-CREATE"
    assert "signature" not in body
    assert "nonce" not in body
    assert body["metadata"] == "Deploy Deposit Wallet"


def test_deploy_deposit_wallet_rejects_non_deposit_wallet() -> None:
    async def run() -> None:
        client = await make_proxy_client()
        try:
            with pytest.raises(UserInputError, match="DEPOSIT_WALLET"):
                await client.deploy_deposit_wallet()
        finally:
            await client.close()

    asyncio.run(run())
