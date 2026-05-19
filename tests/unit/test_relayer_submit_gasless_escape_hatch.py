# pyright: reportPrivateUsage=false
import asyncio
from urllib.parse import urlparse

import httpx
from _relayer_helpers import install_relayer_routes, make_deposit_client, request_json

from polymarket.calls import (
    MAX_UINT256,
    erc20_approval_call,
    erc20_transfer_call,
)
from polymarket.types import EvmAddress

_TOKEN = EvmAddress("0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB")
_SPENDER = EvmAddress("0xE111180000d2663C0091e4f400237545B87B996B")
_RECIPIENT = EvmAddress("0x000000000000000000000000000000000000dEaD")


def test_submit_gasless_bundles_arbitrary_calls() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_deposit_client()
        install_relayer_routes(
            client,
            captured,
            {
                "/v1/account/transactions/params": {
                    "address": client._ctx.signer.address,
                    "nonce": "0",
                },
                "/submit": {
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-escape",
                },
            },
        )
        try:
            calls = [
                erc20_approval_call(token_address=_TOKEN, spender=_SPENDER, amount=MAX_UINT256),
                erc20_transfer_call(token_address=_TOKEN, recipient=_RECIPIENT, amount=1),
            ]
            handle = await client.submit_gasless(calls=calls, metadata="custom batch")
            assert handle.transaction_id == "tx-escape"
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert len(submit_calls) == 1
    body = request_json(submit_calls[0])
    inner = body["depositWalletParams"]["calls"]
    assert len(inner) == 2
    assert body["metadata"] == "custom batch"


def test_submit_gasless_default_metadata_is_empty() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_deposit_client()
        install_relayer_routes(
            client,
            captured,
            {
                "/v1/account/transactions/params": {
                    "address": client._ctx.signer.address,
                    "nonce": "0",
                },
                "/submit": {
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-emptymeta",
                },
            },
        )
        try:
            call = erc20_approval_call(token_address=_TOKEN, spender=_SPENDER, amount=1)
            await client.submit_gasless(calls=[call])
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    body = request_json(submit_calls[0])
    assert body["metadata"] == ""
