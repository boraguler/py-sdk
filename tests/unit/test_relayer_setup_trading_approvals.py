# pyright: reportPrivateUsage=false
import asyncio
from urllib.parse import urlparse

import httpx
from _relayer_helpers import (
    install_relayer_routes,
    make_deposit_client,
    make_safe_client,
    request_json,
)
from eth_utils.crypto import keccak

from polymarket.environments import PRODUCTION


def _selector(sig: str) -> str:
    return "0x" + keccak(sig.encode("ascii"))[:4].hex()


def test_setup_trading_approvals_bundles_seven_calls_for_deposit_wallet() -> None:
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
                    "transactionID": "tx-setup",
                },
            },
        )
        try:
            await client.setup_trading_approvals()
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert len(submit_calls) == 1
    body = request_json(submit_calls[0])
    assert body["type"] == "WALLET"
    inner = body["depositWalletParams"]["calls"]
    assert len(inner) == 7

    erc20_sel = _selector("approve(address,uint256)")
    erc1155_sel = _selector("setApprovalForAll(address,bool)")
    assert inner[0]["target"].lower() == PRODUCTION.collateral_token.lower()
    assert inner[0]["data"].startswith(erc20_sel)
    assert inner[1]["target"].lower() == PRODUCTION.collateral_token.lower()
    assert inner[1]["data"].startswith(erc20_sel)
    assert inner[2]["target"].lower() == PRODUCTION.collateral_token.lower()
    assert inner[2]["data"].startswith(erc20_sel)
    assert inner[3]["target"].lower() == PRODUCTION.conditional_tokens.lower()
    assert inner[3]["data"].startswith(erc1155_sel)
    assert inner[6]["target"].lower() == PRODUCTION.conditional_tokens.lower()
    assert inner[6]["data"].startswith(erc1155_sel)
    assert PRODUCTION.auto_redeem_operator[2:].lower() in inner[6]["data"].lower()
    assert body["metadata"] == "Trading setup approvals"


def test_setup_trading_approvals_uses_safe_multisend_for_safe() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_safe_client()
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
                    "transactionID": "tx-setup-safe",
                },
            },
        )
        try:
            await client.setup_trading_approvals()
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    body = request_json(submit_calls[0])
    assert body["type"] == "SAFE"
    assert body["to"].lower() == PRODUCTION.safe_multisend.lower()
    assert body["signatureParams"]["operation"] == "1"
    assert body["data"].startswith("0x8d80ff0a")
