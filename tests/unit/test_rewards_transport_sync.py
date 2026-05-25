# pyright: reportPrivateUsage=false
import dataclasses
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

import httpx

from polymarket import (
    ApiKeyCreds,
    PublicClient,
    SecureClient,
)
from polymarket._internal.context import SyncSecureClientContext
from polymarket.clients._transport import SyncTransport
from polymarket.models.clob.rewards import (
    CurrentReward,
    MarketReward,
)

PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
SIGNER_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
FAKE_CREDS = ApiKeyCreds(key="test-key", passphrase="test-passphrase", secret="dGVzdA==")


def _routed_handler(
    captured: list[httpx.Request],
    routes: dict[tuple[str, str], Any],
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        path = urlparse(str(request.url)).path
        key = (request.method, path)
        if key in routes:
            return httpx.Response(200, json=routes[key], request=request)
        return httpx.Response(404, json={"error": "not mocked"}, request=request)

    return httpx.MockTransport(handler)


def _install_sync_clob(client: PublicClient | SecureClient, handler: httpx.MockTransport) -> None:
    transport = SyncTransport(
        base_url="https://clob.test",
        client=httpx.Client(base_url="https://clob.test", transport=handler),
    )
    client._ctx = cast(SyncSecureClientContext, dataclasses.replace(client._ctx, clob=transport))


_CURRENT_REWARDS_PAGE: dict[str, Any] = {
    "limit": 100,
    "count": 1,
    "next_cursor": "LTE=",
    "data": [
        {
            "condition_id": "0xCONDITION",
            "rewards_max_spread": 3.0,
            "tokens": [],
        }
    ],
}

_MARKET_REWARDS_PAGE: dict[str, Any] = {
    "limit": 100,
    "count": 1,
    "next_cursor": "LTE=",
    "data": [
        {
            "condition_id": "0xCONDITION",
            "question": "Q?",
            "tokens": [{"token_id": "8501497", "outcome": "Yes", "price": "0.5"}],
        }
    ],
}


class TestListCurrentRewards:
    def test_public_routes_to_clob(self) -> None:
        captured: list[httpx.Request] = []
        with PublicClient() as client:
            _install_sync_clob(
                client,
                _routed_handler(
                    captured, {("GET", "/rewards/markets/current"): _CURRENT_REWARDS_PAGE}
                ),
            )
            page = client.list_current_rewards().first_page()

        assert len(page.items) == 1
        assert isinstance(page.items[0], CurrentReward)
        assert captured[0].method == "GET"
        assert urlparse(str(captured[0].url)).path == "/rewards/markets/current"
        assert captured[0].headers.get("POLY_SIGNATURE") is None

    def test_public_passes_sponsored_filter(self) -> None:
        captured: list[httpx.Request] = []
        with PublicClient() as client:
            _install_sync_clob(
                client,
                _routed_handler(
                    captured, {("GET", "/rewards/markets/current"): _CURRENT_REWARDS_PAGE}
                ),
            )
            client.list_current_rewards(sponsored=True).first_page()

        qs = parse_qs(urlparse(str(captured[0].url)).query)
        assert qs.get("sponsored") == ["true"]

    def test_secure_uses_unsigned_clob_not_secure_clob(self) -> None:
        captured: list[httpx.Request] = []
        with SecureClient._create(
            private_key=PRIVATE_KEY,
            wallet=SIGNER_ADDRESS,
            credentials=FAKE_CREDS,
            validate_credentials=False,
        ) as client:
            _install_sync_clob(
                client,
                _routed_handler(
                    captured, {("GET", "/rewards/markets/current"): _CURRENT_REWARDS_PAGE}
                ),
            )
            page = client.list_current_rewards().first_page()

        assert len(page.items) == 1
        assert captured[0].headers.get("POLY_SIGNATURE") is None


class TestListMarketRewards:
    def test_public_routes_with_condition_id_in_path(self) -> None:
        captured: list[httpx.Request] = []
        with PublicClient() as client:
            _install_sync_clob(
                client,
                _routed_handler(
                    captured,
                    {("GET", "/rewards/markets/0xCONDITION"): _MARKET_REWARDS_PAGE},
                ),
            )
            page = client.list_market_rewards(condition_id="0xCONDITION").first_page()

        assert len(page.items) == 1
        assert isinstance(page.items[0], MarketReward)
        assert urlparse(str(captured[0].url)).path == "/rewards/markets/0xCONDITION"

    def test_secure_uses_unsigned_clob_not_secure_clob(self) -> None:
        captured: list[httpx.Request] = []
        with SecureClient._create(
            private_key=PRIVATE_KEY,
            wallet=SIGNER_ADDRESS,
            credentials=FAKE_CREDS,
            validate_credentials=False,
        ) as client:
            _install_sync_clob(
                client,
                _routed_handler(
                    captured,
                    {("GET", "/rewards/markets/0xCONDITION"): _MARKET_REWARDS_PAGE},
                ),
            )
            page = client.list_market_rewards(condition_id="0xCONDITION").first_page()

        assert len(page.items) == 1
        assert captured[0].headers.get("POLY_SIGNATURE") is None
