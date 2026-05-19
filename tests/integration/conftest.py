import asyncio
import os
from collections.abc import AsyncGenerator, Callable
from decimal import Decimal
from pathlib import Path

import pytest
from dotenv import load_dotenv

from polymarket import AsyncPublicClient, AsyncSecureClient, Market
from polymarket.models.types import TokenId

_DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"
_METERED_ENV_VAR = "POLYMARKET_RUN_METERED_TESTS"
_METERED_SKIP_REASON = f"set {_METERED_ENV_VAR}=1 to run metered integration tests"

_PAGES_TO_SCAN = 5
_TRADABLE_MARKET_PAGE_SIZE = 100


def _load_dotenv() -> None:
    load_dotenv(_DOTENV_PATH, override=False)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    metered_items = [item for item in items if "metered" in item.keywords]
    if not metered_items:
        return

    _load_dotenv()
    if os.environ.get(_METERED_ENV_VAR) == "1":
        return

    skip_metered = pytest.mark.skip(reason=_METERED_SKIP_REASON)
    for item in metered_items:
        item.add_marker(skip_metered)


@pytest.fixture
def require_env() -> Callable[[str], str]:
    _load_dotenv()

    def get(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            pytest.skip(f"{name} is required for this integration test")
        return value

    return get


@pytest.fixture
def builder_code(require_env: Callable[[str], str]) -> str:
    return require_env("POLYMARKET_BUILDER_CODE")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def deposit_wallet_client(
    require_env: Callable[[str], str],
) -> AsyncGenerator[AsyncSecureClient, None]:
    private_key = require_env("POLYMARKET_PRIVATE_KEY")
    wallet = require_env("POLYMARKET_DEPOSIT_WALLET")
    client = await AsyncSecureClient.create(
        private_key=private_key,
        wallet=wallet,
    )
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
async def public_client() -> AsyncGenerator[AsyncPublicClient, None]:
    async with AsyncPublicClient() as client:
        yield client


@pytest.fixture(scope="session")
def active_clob_token() -> TokenId:
    async def find() -> TokenId:
        async with AsyncPublicClient() as client:
            paginator = client.list_markets(closed=False, page_size=20)
            pages_seen = 0
            async for page in paginator:
                pages_seen += 1
                for market in page.items:
                    if not market.state.enable_order_book:
                        continue
                    if not market.state.accepting_orders:
                        continue
                    token_id = market.outcomes.yes.token_id
                    if token_id is None:
                        continue
                    return token_id
                if pages_seen >= _PAGES_TO_SCAN:
                    break
        pytest.skip("no CLOB-active market with a Yes-outcome token id found")

    return asyncio.run(find())


@pytest.fixture(scope="session")
def tradable_market() -> Market:
    async def find() -> Market:
        async with AsyncPublicClient() as client:
            paginator = client.list_markets(
                ascending=False,
                closed=False,
                liquidity_num_min=1000,
                order="liquidityNum",
                sports_market_types=("moneyline", "spreads", "totals"),
                page_size=_TRADABLE_MARKET_PAGE_SIZE,
            )
            pages_seen = 0
            async for page in paginator:
                pages_seen += 1
                for market in page.items:
                    if not _has_required_trading_fields(market):
                        continue
                    if not _has_tradable_prices(market):
                        continue
                    if not _has_clob_liquidity(market):
                        continue
                    return market
                if pages_seen >= _PAGES_TO_SCAN:
                    break
        pytest.skip("no tradable market found")

    return asyncio.run(find())


def _has_required_trading_fields(market: Market) -> bool:
    return (
        market.condition_id is not None
        and market.state.enable_order_book is True
        and market.state.accepting_orders is True
        and market.trading.minimum_order_size is not None
        and market.trading.minimum_tick_size is not None
        and market.outcomes.yes.token_id is not None
    )


def _has_tradable_prices(market: Market) -> bool:
    return (
        market.prices.best_ask is not None
        and market.prices.best_ask < Decimal(1)
        and market.trading.minimum_tick_size is not None
        and market.prices.best_ask > market.trading.minimum_tick_size
        and market.prices.best_bid is not None
        and market.prices.best_bid > Decimal(0)
    )


def _has_clob_liquidity(market: Market) -> bool:
    liquidity = market.metrics.liquidity_clob or market.metrics.liquidity_num or Decimal(0)
    return liquidity > Decimal(0)
