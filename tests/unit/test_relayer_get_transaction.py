# pyright: reportPrivateUsage=false
import asyncio
from urllib.parse import urlparse

import httpx
from _relayer_helpers import install_relayer_handler, make_deposit_client

from polymarket.models.clob.relayer import RelayerTransactionState


def test_get_transaction_returns_parsed_model() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_deposit_client()

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={
                    "state": "STATE_MINED",
                    "transaction_hash": "0x" + "ab" * 32,
                    "transaction_id": "tx-fetch",
                },
                request=request,
            )

        install_relayer_handler(client, handler)
        try:
            tx = await client.get_transaction(transaction_id="tx-fetch")
            assert tx.state == RelayerTransactionState.MINED
            assert tx.transaction_hash == "0x" + "ab" * 32
            assert tx.transaction_id == "tx-fetch"
        finally:
            await client.close()

    asyncio.run(run())
    assert len(captured) == 1
    path = urlparse(str(captured[0].url)).path
    assert path == "/v1/account/transactions/tx-fetch"
