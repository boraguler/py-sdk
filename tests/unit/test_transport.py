import asyncio

import httpx
import pytest

from polymarket.clients._transport import AsyncTransport, SyncTransport
from polymarket.errors import (
    RateLimitError,
    RequestRejectedError,
    TransportError,
    UnexpectedResponseError,
)


def test_sync_transport_returns_json_payload() -> None:
    transport = SyncTransport(
        base_url="https://example.test",
        client=httpx.Client(
            base_url="https://example.test",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"ok": True}, request=request)
            ),
        ),
    )

    assert transport.get_json("/markets/1") == {"ok": True}


def test_sync_transport_maps_rate_limit_response() -> None:
    transport = SyncTransport(
        base_url="https://example.test",
        client=httpx.Client(
            base_url="https://example.test",
            transport=httpx.MockTransport(lambda request: httpx.Response(429, request=request)),
        ),
    )

    with pytest.raises(RateLimitError, match="was rate limited"):
        transport.get_json("/markets/1")


def test_sync_transport_maps_rejected_json_error_response() -> None:
    transport = SyncTransport(
        base_url="https://example.test",
        client=httpx.Client(
            base_url="https://example.test",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    400,
                    json={"error": "bad market"},
                    request=request,
                )
            ),
        ),
    )

    with pytest.raises(RequestRejectedError, match="bad market") as exc_info:
        transport.get_json("/markets/1")

    assert exc_info.value.status == 400


def test_sync_transport_maps_non_json_success_response() -> None:
    transport = SyncTransport(
        base_url="https://example.test",
        client=httpx.Client(
            base_url="https://example.test",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    text="not json",
                    request=request,
                    headers={"content-type": "text/plain"},
                )
            ),
        ),
    )

    with pytest.raises(UnexpectedResponseError, match="Received non-JSON response"):
        transport.get_json("/markets/1")


def test_sync_transport_maps_transport_failure() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    transport = SyncTransport(
        base_url="https://example.test",
        client=httpx.Client(
            base_url="https://example.test",
            transport=httpx.MockTransport(fail),
        ),
    )

    with pytest.raises(TransportError, match="connection failed") as exc_info:
        transport.get_json("/markets/1")

    assert isinstance(exc_info.value.__cause__, httpx.ConnectError)


def test_async_transport_returns_json_payload() -> None:
    async def run() -> None:
        transport = AsyncTransport(
            base_url="https://example.test",
            client=httpx.AsyncClient(
                base_url="https://example.test",
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(200, json={"ok": True}, request=request)
                ),
            ),
        )

        assert await transport.get_json("/markets/1") == {"ok": True}

    asyncio.run(run())
