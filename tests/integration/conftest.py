import os
from collections.abc import Callable
from pathlib import Path

import pytest
from dotenv import load_dotenv

_DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"
_METERED_ENV_VAR = "POLYMARKET_RUN_METERED_TESTS"
_METERED_SKIP_REASON = f"set {_METERED_ENV_VAR}=1 to run metered integration tests"


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
