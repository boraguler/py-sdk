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


def test_setup_trading_approvals_bundles_eleven_calls_for_deposit_wallet() -> None:
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
    assert len(inner) == 11

    erc20_sel = _selector("approve(address,uint256)")
    erc1155_sel = _selector("setApprovalForAll(address,bool)")
    # ERC20 approvals: standard_exchange, neg_risk_exchange, neg_risk_adapter,
    # collateral_adapter, neg_risk_collateral_adapter
    for index, spender in enumerate(
        [
            PRODUCTION.standard_exchange,
            PRODUCTION.neg_risk_exchange,
            PRODUCTION.neg_risk_adapter,
            PRODUCTION.collateral_adapter,
            PRODUCTION.neg_risk_collateral_adapter,
        ]
    ):
        assert inner[index]["target"].lower() == PRODUCTION.collateral_token.lower()
        assert inner[index]["data"].startswith(erc20_sel)
        assert spender[2:].lower() in inner[index]["data"].lower()
    # ERC1155 approvals: standard_exchange, neg_risk_exchange, neg_risk_adapter,
    # collateral_adapter, neg_risk_collateral_adapter, auto_redeem_operator
    for offset, operator in enumerate(
        [
            PRODUCTION.standard_exchange,
            PRODUCTION.neg_risk_exchange,
            PRODUCTION.neg_risk_adapter,
            PRODUCTION.collateral_adapter,
            PRODUCTION.neg_risk_collateral_adapter,
            PRODUCTION.auto_redeem_operator,
        ]
    ):
        index = 5 + offset
        assert inner[index]["target"].lower() == PRODUCTION.conditional_tokens.lower()
        assert inner[index]["data"].startswith(erc1155_sel)
        assert operator[2:].lower() in inner[index]["data"].lower()
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
