# pyright: reportPrivateUsage=false
import asyncio
import dataclasses
from urllib.parse import urlparse

import httpx
from _relayer_helpers import install_relayer_handler, make_deposit_client

from polymarket.models.clob.relayer import RelayerTransactionState, TransactionOutcome


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


def test_attach_gasless_handle_resumes_wait_until_mined() -> None:
    poll_count = 0

    async def run() -> TransactionOutcome:
        nonlocal poll_count
        client = await make_deposit_client()

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal poll_count
            path = urlparse(str(request.url)).path
            if path.startswith("/v1/account/transactions/"):
                poll_count += 1
                if poll_count < 2:
                    return httpx.Response(
                        200,
                        json={
                            "state": "STATE_NEW",
                            "transaction_hash": "",
                            "transaction_id": "tx-resume",
                        },
                        request=request,
                    )
                return httpx.Response(
                    200,
                    json={
                        "state": "STATE_MINED",
                        "transaction_hash": "0x" + "cd" * 32,
                        "transaction_id": "tx-resume",
                    },
                    request=request,
                )
            return httpx.Response(404, request=request)

        install_relayer_handler(client, handler)
        client._ctx = dataclasses.replace(
            client._ctx,
            environment=dataclasses.replace(client._ctx.environment, relayer_poll_frequency_ms=1),
        )
        try:
            handle = client.attach_gasless_handle(transaction_id="tx-resume")
            return await handle.wait()
        finally:
            await client.close()

    outcome = asyncio.run(run())
    assert outcome.transaction_id == "tx-resume"
    assert outcome.transaction_hash == "0x" + "cd" * 32
    assert poll_count >= 2


def test_attach_gasless_handle_preserves_fallback_hash() -> None:
    async def run() -> TransactionOutcome:
        client = await make_deposit_client()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "state": "STATE_CONFIRMED",
                    "transaction_hash": "",
                    "transaction_id": "tx-fb",
                },
                request=request,
            )

        install_relayer_handler(client, handler)
        try:
            handle = client.attach_gasless_handle(
                transaction_id="tx-fb",
                transaction_hash="0x" + "ee" * 32,
            )
            return await handle.wait()
        finally:
            await client.close()

    outcome = asyncio.run(run())
    assert outcome.transaction_hash == "0x" + "ee" * 32
