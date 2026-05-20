# pyright: reportPrivateUsage=false
import dataclasses
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from _relayer_helpers import (
    SPENDER,
    TOKEN,
    beacon_factory_rpc_handler,
    install_sync_relayer_handler,
    install_sync_rpc_handler,
    legacy_factory_rpc_handler,
    make_sync_deposit_client,
    make_sync_eoa_client,
    make_sync_proxy_client,
    make_sync_safe_client,
    request_json,
)

from polymarket._internal.wallet import (
    derive_beacon_deposit_wallet_address,
    derive_uups_deposit_wallet_address,
)
from polymarket.environments import PRODUCTION
from polymarket.errors import (
    TimeoutError as PolyTimeoutError,
)
from polymarket.errors import (
    TransactionFailedError,
    UnexpectedResponseError,
    UserInputError,
)
from polymarket.transactions import SyncEoaTransactionHandle, SyncGaslessTransactionHandle


def _deposit_relayer_handler(captured: list[httpx.Request]):  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        path = urlparse(str(request.url)).path
        if path == "/v1/account/transactions/params":
            return httpx.Response(200, json={"address": "0xRELAY", "nonce": "0"}, request=request)
        if path == "/submit":
            return httpx.Response(
                200,
                json={
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-sync",
                },
                request=request,
            )
        return httpx.Response(404, json={"error": "not mocked"}, request=request)

    return handler


def test_approve_erc20_gasless_returns_sync_handle() -> None:
    captured: list[httpx.Request] = []

    with make_sync_deposit_client() as client:
        install_sync_relayer_handler(client, _deposit_relayer_handler(captured))
        handle = client.approve_erc20(token_address=TOKEN, spender_address=SPENDER, amount=1)

    assert isinstance(handle, SyncGaslessTransactionHandle)
    assert handle.transaction_id == "tx-sync"
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert len(submit_calls) == 1
    body = request_json(submit_calls[0])
    assert body["type"] == "WALLET"


def test_approve_erc20_eoa_uses_direct_broadcast() -> None:
    rpc_calls: list[dict[str, object]] = []

    def rpc_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        rpc_calls.append(body)
        method = body["method"]
        if method == "eth_chainId":
            result: object = hex(137)
        elif method == "eth_getTransactionCount":
            result = hex(7)
        elif method == "eth_gasPrice":
            result = hex(30_000_000_000)
        elif method == "eth_estimateGas":
            result = hex(100_000)
        elif method == "eth_sendRawTransaction":
            result = "0x" + "aa" * 32
        else:
            return httpx.Response(
                404, json={"jsonrpc": "2.0", "id": body["id"], "error": "?"}, request=request
            )
        return httpx.Response(
            200, json={"jsonrpc": "2.0", "id": body["id"], "result": result}, request=request
        )

    with make_sync_eoa_client() as client:
        install_sync_rpc_handler(client, rpc_handler)
        handle = client.approve_erc20(token_address=TOKEN, spender_address=SPENDER, amount=1)

    assert isinstance(handle, SyncEoaTransactionHandle)
    assert handle.transaction_hash == "0x" + "aa" * 32
    methods = [c["method"] for c in rpc_calls]
    assert "eth_sendRawTransaction" in methods


def test_is_gasless_ready_deposit_wallet_returns_true() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"deployed": True}, request=request)

    with make_sync_deposit_client() as client:
        install_sync_relayer_handler(client, handler)
        result = client.is_gasless_ready()

    assert result is True
    qs = parse_qs(urlparse(str(captured[0].url)).query)
    assert qs["type"] == ["WALLET"]


def test_is_gasless_ready_eoa_legacy_factory_queries_uups_address() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"deployed": True}, request=request)

    with make_sync_eoa_client() as client:
        signer_address = client._ctx.signer.address
        install_sync_relayer_handler(client, handler)
        install_sync_rpc_handler(client, legacy_factory_rpc_handler())
        assert client.is_gasless_ready() is True

    expected = derive_uups_deposit_wallet_address(signer_address, PRODUCTION.wallet_derivation)
    qs = parse_qs(urlparse(str(captured[0].url)).query)
    assert qs["address"] == [expected]
    assert qs["type"] == ["WALLET"]


def test_is_gasless_ready_eoa_beacon_factory_queries_beacon_address() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"deployed": False}, request=request)

    with make_sync_eoa_client() as client:
        signer_address = client._ctx.signer.address
        install_sync_relayer_handler(client, handler)
        install_sync_rpc_handler(
            client,
            beacon_factory_rpc_handler(PRODUCTION.wallet_derivation.deposit_wallet_beacon),
        )
        assert client.is_gasless_ready() is False

    expected = derive_beacon_deposit_wallet_address(signer_address, PRODUCTION.wallet_derivation)
    qs = parse_qs(urlparse(str(captured[0].url)).query)
    assert qs["address"] == [expected]
    assert qs["type"] == ["WALLET"]


def test_setup_gasless_wallet_rejects_without_api_key() -> None:
    with (
        pytest.raises(UserInputError, match="Builder API Key or Relayer API Key"),
        make_sync_eoa_client(with_api_key=False) as client,
    ):
        client.setup_gasless_wallet()


def test_setup_gasless_wallet_eoa_skips_deploy_when_already_deployed() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        path = urlparse(str(request.url)).path
        if path == "/deployed":
            return httpx.Response(200, json={"deployed": True}, request=request)
        return httpx.Response(404, request=request)

    with make_sync_eoa_client() as client:
        signer_address = client._ctx.signer.address
        install_sync_relayer_handler(client, handler)
        install_sync_rpc_handler(client, legacy_factory_rpc_handler())
        gasless = client.setup_gasless_wallet()
        try:
            assert gasless.wallet_type == "DEPOSIT_WALLET"
            expected = derive_uups_deposit_wallet_address(
                signer_address, PRODUCTION.wallet_derivation
            )
            assert str(gasless.wallet) == expected
        finally:
            gasless.close()

    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert submit_calls == []


def test_setup_gasless_wallet_eoa_deploys_when_not_deployed_and_returns_fresh_client() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        path = urlparse(str(request.url)).path
        if path == "/deployed":
            return httpx.Response(200, json={"deployed": False}, request=request)
        if path == "/submit":
            return httpx.Response(
                200,
                json={
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-deploy",
                },
                request=request,
            )
        if path.startswith("/v1/account/transactions/"):
            return httpx.Response(
                200,
                json={
                    "state": "STATE_MINED",
                    "transaction_hash": "0x" + "ab" * 32,
                    "transaction_id": "tx-deploy",
                },
                request=request,
            )
        return httpx.Response(404, request=request)

    with make_sync_eoa_client() as client:
        install_sync_relayer_handler(client, handler)
        install_sync_rpc_handler(client, legacy_factory_rpc_handler())
        client._ctx = dataclasses.replace(
            client._ctx,
            environment=dataclasses.replace(client._ctx.environment, relayer_poll_frequency_ms=1),
        )
        gasless = client.setup_gasless_wallet()
        try:
            assert gasless is not client
            assert gasless.wallet_type == "DEPOSIT_WALLET"
        finally:
            gasless.close()

    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert len(submit_calls) == 1
    body = request_json(submit_calls[0])
    assert body["type"] == "WALLET-CREATE"


def test_split_position_routes_through_collateral_adapter() -> None:
    captured: list[httpx.Request] = []
    _CONDITION_ID = "0x" + "11" * 32

    class _StubPaginator:
        def __init__(self, items: tuple[object, ...]) -> None:
            self._items = items

        def first_page(self):  # type: ignore[no-untyped-def]
            from polymarket.pagination import Page

            return Page(items=self._items, has_more=False, next_cursor=None, total_count=1)

    def _market_stub(neg_risk: bool):  # type: ignore[no-untyped-def]
        class _MarketState:
            def __init__(self) -> None:
                self.neg_risk = neg_risk

        class _Market:
            def __init__(self) -> None:
                self.state = _MarketState()

        return _Market()

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        path = urlparse(str(request.url)).path
        if path == "/v1/account/transactions/params":
            return httpx.Response(200, json={"address": "0xRELAY", "nonce": "0"}, request=request)
        if path == "/submit":
            return httpx.Response(
                200,
                json={
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-split",
                },
                request=request,
            )
        return httpx.Response(404, request=request)

    with make_sync_deposit_client() as client:
        client.list_markets = lambda **_: _StubPaginator((_market_stub(neg_risk=False),))  # type: ignore[method-assign]
        install_sync_relayer_handler(client, handler)
        client.split_position(condition_id=_CONDITION_ID, amount=1_000_000)

    submit = [r for r in captured if urlparse(str(r.url)).path == "/submit"][0]
    body = request_json(submit)
    inner = body["depositWalletParams"]["calls"][0]
    assert inner["target"].lower() == PRODUCTION.collateral_adapter.lower()


def test_setup_trading_approvals_bundles_eleven_calls_for_deposit_wallet() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        path = urlparse(str(request.url)).path
        if path == "/v1/account/transactions/params":
            return httpx.Response(200, json={"address": "0xRELAY", "nonce": "0"}, request=request)
        if path == "/submit":
            return httpx.Response(
                200,
                json={
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-setup",
                },
                request=request,
            )
        return httpx.Response(404, request=request)

    with make_sync_deposit_client() as client:
        install_sync_relayer_handler(client, handler)
        client.setup_trading_approvals()

    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    body = request_json(submit_calls[0])
    inner_calls = body["depositWalletParams"]["calls"]
    assert len(inner_calls) == 11


def test_close_closes_relayer_and_rpc_transports() -> None:
    client = make_sync_proxy_client()
    client.close()


def _proxy_relayer_handler(captured: list[httpx.Request]):  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        path = urlparse(str(request.url)).path
        if path == "/relay-payload":
            return httpx.Response(
                200,
                json={"address": "0xe679d14b2fe0bdee4a54f25bcec2978e372de566", "nonce": "0"},
                request=request,
            )
        if path == "/submit":
            return httpx.Response(
                200,
                json={
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-proxy",
                },
                request=request,
            )
        return httpx.Response(404, request=request)

    return handler


def _safe_relayer_handler(captured: list[httpx.Request]):  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        path = urlparse(str(request.url)).path
        if path == "/v1/account/transactions/params":
            return httpx.Response(200, json={"address": "0xRELAY", "nonce": "0"}, request=request)
        if path == "/submit":
            return httpx.Response(
                200,
                json={
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-safe",
                },
                request=request,
            )
        return httpx.Response(404, request=request)

    return handler


def test_approve_erc20_proxy_uses_default_gas_limit_when_rpc_estimate_fails() -> None:
    captured: list[httpx.Request] = []

    def rpc_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "error": {"code": -32_603, "message": "upstream unavailable"},
            },
            request=request,
        )

    with make_sync_proxy_client() as client:
        install_sync_relayer_handler(client, _proxy_relayer_handler(captured))
        install_sync_rpc_handler(client, rpc_handler)
        client.approve_erc20(token_address=TOKEN, spender_address=SPENDER, amount=1)

    submit = [r for r in captured if urlparse(str(r.url)).path == "/submit"][0]
    body = request_json(submit)
    assert body["type"] == "PROXY"
    assert body["signatureParams"]["gasLimit"] == "200000"
    assert body["signatureParams"]["relay"].lower() == "0xe679d14b2fe0bdee4a54f25bcec2978e372de566"


def test_approve_erc20_safe_single_call_uses_call_operation() -> None:
    captured: list[httpx.Request] = []

    with make_sync_safe_client() as client:
        install_sync_relayer_handler(client, _safe_relayer_handler(captured))
        client.approve_erc20(token_address=TOKEN, spender_address=SPENDER, amount=1)

    submit = [r for r in captured if urlparse(str(r.url)).path == "/submit"][0]
    body = request_json(submit)
    assert body["type"] == "SAFE"
    assert body["signatureParams"]["operation"] == "0"
    assert body["to"].lower() == TOKEN.lower()


def test_setup_trading_approvals_safe_uses_multisend_delegatecall() -> None:
    captured: list[httpx.Request] = []

    with make_sync_safe_client() as client:
        install_sync_relayer_handler(client, _safe_relayer_handler(captured))
        client.setup_trading_approvals()

    submit = [r for r in captured if urlparse(str(r.url)).path == "/submit"][0]
    body = request_json(submit)
    assert body["type"] == "SAFE"
    assert body["signatureParams"]["operation"] == "1"
    assert body["to"].lower() == PRODUCTION.safe_multisend.lower()


def _stub_binary_positions(client, *, neg_risk: bool, yes_size: str, no_size: str):  # type: ignore[no-untyped-def]
    from polymarket.models.data.portfolio import Position
    from polymarket.pagination import Page

    yes = Position.parse_response(
        {
            "conditionId": "0x" + "11" * 32,
            "outcomeIndex": 0,
            "size": yes_size,
            "negativeRisk": neg_risk,
        }
    )
    no = Position.parse_response(
        {
            "conditionId": "0x" + "11" * 32,
            "outcomeIndex": 1,
            "size": no_size,
            "negativeRisk": neg_risk,
        }
    )

    class _StubPaginator:
        def first_page(self):  # type: ignore[no-untyped-def]
            return Page(items=(yes, no), has_more=False, next_cursor=None, total_count=2)

    client.list_positions = lambda **_: _StubPaginator()  # type: ignore[method-assign]


def test_merge_positions_routes_through_collateral_adapter() -> None:
    captured: list[httpx.Request] = []

    with make_sync_deposit_client() as client:
        _stub_binary_positions(client, neg_risk=False, yes_size="100.0", no_size="60.0")
        install_sync_relayer_handler(client, _deposit_relayer_handler(captured))
        client.merge_positions(condition_id="0x" + "11" * 32, amount="max")

    submit = [r for r in captured if urlparse(str(r.url)).path == "/submit"][0]
    body = request_json(submit)
    inner = body["depositWalletParams"]["calls"][0]
    assert inner["target"].lower() == PRODUCTION.collateral_adapter.lower()


def test_redeem_positions_routes_through_neg_risk_collateral_adapter() -> None:
    captured: list[httpx.Request] = []

    with make_sync_deposit_client() as client:
        _stub_binary_positions(client, neg_risk=True, yes_size="111.0", no_size="0")
        install_sync_relayer_handler(client, _deposit_relayer_handler(captured))
        client.redeem_positions(condition_id="0x" + "11" * 32)

    submit = [r for r in captured if urlparse(str(r.url)).path == "/submit"][0]
    body = request_json(submit)
    inner = body["depositWalletParams"]["calls"][0]
    assert inner["target"].lower() == PRODUCTION.neg_risk_collateral_adapter.lower()


def test_split_position_raises_unexpected_response_when_neg_risk_flag_missing() -> None:
    class _StubMarket:
        class _State:
            neg_risk: bool | None = None

        state = _State()

    class _StubPaginator:
        def first_page(self):  # type: ignore[no-untyped-def]
            from polymarket.pagination import Page

            return Page(items=(_StubMarket(),), has_more=False, next_cursor=None, total_count=1)

    with (
        pytest.raises(UnexpectedResponseError, match="Missing negRisk"),
        make_sync_deposit_client() as client,
    ):
        client.list_markets = lambda **_: _StubPaginator()  # type: ignore[method-assign]
        client.split_position(condition_id="0x" + "11" * 32, amount=1)


def _wait_relayer_handler(state: str, *, error_msg: str | None = None):  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        path = urlparse(str(request.url)).path
        if path == "/v1/account/transactions/params":
            return httpx.Response(200, json={"address": "0xRELAY", "nonce": "0"}, request=request)
        if path == "/submit":
            return httpx.Response(
                200,
                json={"state": "STATE_NEW", "transactionHash": None, "transactionID": "tx-w"},
                request=request,
            )
        if path.startswith("/v1/account/transactions/"):
            body: dict[str, object] = {
                "state": state,
                "transaction_hash": "0x" + "aa" * 32,
                "transaction_id": "tx-w",
            }
            if error_msg is not None:
                body["error_msg"] = error_msg
            return httpx.Response(200, json=body, request=request)
        return httpx.Response(404, request=request)

    return handler


def test_gasless_wait_returns_outcome_on_terminal_success() -> None:
    with make_sync_deposit_client() as client:
        client._ctx = dataclasses.replace(
            client._ctx,
            environment=dataclasses.replace(client._ctx.environment, relayer_poll_frequency_ms=1),
        )
        install_sync_relayer_handler(client, _wait_relayer_handler("STATE_MINED"))
        handle = client.approve_erc20(token_address=TOKEN, spender_address=SPENDER, amount=1)
        outcome = handle.wait()

    assert outcome.transaction_id == "tx-w"
    assert outcome.transaction_hash == "0x" + "aa" * 32


def test_gasless_wait_raises_transaction_failed_on_terminal_failure() -> None:
    with make_sync_deposit_client() as client:
        client._ctx = dataclasses.replace(
            client._ctx,
            environment=dataclasses.replace(client._ctx.environment, relayer_poll_frequency_ms=1),
        )
        install_sync_relayer_handler(
            client, _wait_relayer_handler("STATE_FAILED", error_msg="reverted on chain")
        )
        handle = client.approve_erc20(token_address=TOKEN, spender_address=SPENDER, amount=1)
        with pytest.raises(TransactionFailedError, match="reverted on chain"):
            handle.wait()


def test_gasless_wait_times_out_when_terminal_state_never_reached() -> None:
    with make_sync_deposit_client() as client:
        client._ctx = dataclasses.replace(
            client._ctx,
            environment=dataclasses.replace(
                client._ctx.environment,
                relayer_poll_frequency_ms=1,
                relayer_max_polls=3,
            ),
        )
        install_sync_relayer_handler(client, _wait_relayer_handler("STATE_NEW"))
        handle = client.approve_erc20(token_address=TOKEN, spender_address=SPENDER, amount=1)
        with pytest.raises(PolyTimeoutError):
            handle.wait()


def test_gasless_submit_retries_on_retryable_400_then_succeeds() -> None:
    captured: list[httpx.Request] = []
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        path = urlparse(str(request.url)).path
        if path == "/v1/account/transactions/params":
            return httpx.Response(200, json={"address": "0xRELAY", "nonce": "0"}, request=request)
        if path == "/submit":
            attempts["n"] += 1
            if attempts["n"] == 1:
                return httpx.Response(
                    400,
                    json={"error": "wallet busy with active action"},
                    request=request,
                )
            return httpx.Response(
                200,
                json={
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-retry",
                },
                request=request,
            )
        return httpx.Response(404, request=request)

    with make_sync_deposit_client() as client:
        client._ctx = dataclasses.replace(
            client._ctx,
            environment=dataclasses.replace(client._ctx.environment, relayer_poll_frequency_ms=1),
        )
        install_sync_relayer_handler(client, handler)
        handle = client.approve_erc20(token_address=TOKEN, spender_address=SPENDER, amount=1)

    assert handle.transaction_id == "tx-retry"
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert len(submit_calls) == 2
