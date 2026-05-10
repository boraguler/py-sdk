# pyright: reportPrivateUsage=false
import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from polymarket._internal.pagination import decode_offset_cursor
from polymarket._internal.request import OffsetPaginatedSpec
from polymarket.clients._transport import AsyncTransport, SyncTransport
from polymarket.clients.async_public import AsyncPublicClient
from polymarket.clients.public import PublicClient
from polymarket.errors import UserInputError


def _items_handler(captured: list[httpx.Request], rows: list[list[int]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        offset = int(parse_qs(urlparse(str(request.url)).query)["offset"][0])
        empty: list[int] = []
        page = next((row for row in rows if row and row[0] == offset), empty)
        return httpx.Response(200, json=page, request=request)

    return httpx.MockTransport(handler)


def _spec(path: str = "/positions", base_params: dict[str, str] | None = None):
    return OffsetPaginatedSpec[int](
        service="data",
        path=path,
        parse_items=lambda payload: tuple(payload),  # type: ignore[arg-type]
        base_params=base_params,
    )


def _install_sync_data_transport(client: PublicClient, handler: httpx.MockTransport) -> None:
    client._data = SyncTransport(
        base_url="https://example.test",
        client=httpx.Client(base_url="https://example.test", transport=handler),
    )


def _install_async_data_transport(client: AsyncPublicClient, handler: httpx.MockTransport) -> None:
    client._data = AsyncTransport(
        base_url="https://example.test",
        client=httpx.AsyncClient(base_url="https://example.test", transport=handler),
    )


def test_sync_paginate_offset_sends_limit_and_offset() -> None:
    captured: list[httpx.Request] = []
    handler = _items_handler(captured, [list(range(0, 11))])
    with PublicClient() as client:
        _install_sync_data_transport(client, handler)
        page = client._paginate_offset(
            _spec(base_params={"user": "0xA"}), page_size=10
        ).first_page()

    assert len(captured) == 1
    qs = parse_qs(urlparse(str(captured[0].url)).query)
    assert qs["limit"] == ["11"]
    assert qs["offset"] == ["0"]
    assert qs["user"] == ["0xA"]
    assert page.items == tuple(range(10))
    assert page.has_more is True
    assert page.next_cursor is not None


def test_sync_paginate_offset_trims_to_page_size() -> None:
    captured: list[httpx.Request] = []
    handler = _items_handler(captured, [list(range(15))])
    with PublicClient() as client:
        _install_sync_data_transport(client, handler)
        page = client._paginate_offset(_spec(), page_size=10).first_page()

    assert page.items == tuple(range(10))
    assert page.has_more is True


def test_sync_paginate_offset_no_more_when_partial() -> None:
    captured: list[httpx.Request] = []
    handler = _items_handler(captured, [list(range(3))])
    with PublicClient() as client:
        _install_sync_data_transport(client, handler)
        page = client._paginate_offset(_spec(), page_size=10).first_page()

    assert page.items == (0, 1, 2)
    assert page.has_more is False
    assert page.next_cursor is None


def test_sync_paginate_offset_round_trip_next_cursor() -> None:
    captured: list[httpx.Request] = []
    handler = _items_handler(
        captured,
        [list(range(0, 11)), list(range(10, 13))],
    )
    with PublicClient() as client:
        _install_sync_data_transport(client, handler)
        spec = _spec(base_params={"user": "0xA"})
        paginator = client._paginate_offset(spec, page_size=10)
        all_items = list(paginator.items())

    assert all_items == list(range(13))
    assert len(captured) == 2
    qs1 = parse_qs(urlparse(str(captured[1].url)).query)
    assert qs1["offset"] == ["10"]
    assert qs1["limit"] == ["11"]


def test_sync_paginate_offset_cursor_rejects_different_endpoint() -> None:
    captured: list[httpx.Request] = []
    handler = _items_handler(captured, [list(range(11))])
    with PublicClient() as client:
        _install_sync_data_transport(client, handler)
        paginator = client._paginate_offset(_spec(path="/positions"), page_size=10)
        first = paginator.first_page()
        assert first.next_cursor is not None
        other_spec_paginator = client._paginate_offset(_spec(path="/trades"), page_size=10)
        with pytest.raises(UserInputError, match="does not belong"):
            other_spec_paginator.from_cursor(first.next_cursor).first_page()


def test_sync_paginate_offset_cursor_rejects_different_query() -> None:
    captured: list[httpx.Request] = []
    handler = _items_handler(captured, [list(range(11))])
    with PublicClient() as client:
        _install_sync_data_transport(client, handler)
        a_paginator = client._paginate_offset(_spec(base_params={"user": "0xA"}), page_size=10)
        first = a_paginator.first_page()
        assert first.next_cursor is not None
        b_paginator = client._paginate_offset(_spec(base_params={"user": "0xB"}), page_size=10)
        with pytest.raises(UserInputError, match="different query parameters"):
            b_paginator.from_cursor(first.next_cursor).first_page()


def test_sync_paginate_offset_next_cursor_decodes_to_expected_offset() -> None:
    captured: list[httpx.Request] = []
    handler = _items_handler(captured, [list(range(11))])
    with PublicClient() as client:
        _install_sync_data_transport(client, handler)
        spec = _spec(base_params={"user": "0xA"})
        page = client._paginate_offset(spec, page_size=10).first_page()

    assert page.next_cursor is not None
    assert decode_offset_cursor(
        page.next_cursor,
        expected_path="/positions",
        expected_base_params={"user": "0xA"},
    ) == (10, 10)


def test_async_paginate_offset_sends_limit_and_offset() -> None:
    async def run() -> None:
        captured: list[httpx.Request] = []
        handler = _items_handler(captured, [list(range(0, 11))])
        async with AsyncPublicClient() as client:
            _install_async_data_transport(client, handler)
            page = await client._paginate_offset(
                _spec(base_params={"user": "0xA"}), page_size=10
            ).first_page()

        assert len(captured) == 1
        qs = parse_qs(urlparse(str(captured[0].url)).query)
        assert qs["limit"] == ["11"]
        assert qs["offset"] == ["0"]
        assert qs["user"] == ["0xA"]
        assert page.items == tuple(range(10))
        assert page.has_more is True

    asyncio.run(run())


def test_async_paginate_offset_round_trip_next_cursor() -> None:
    async def run() -> None:
        captured: list[httpx.Request] = []
        handler = _items_handler(
            captured,
            [list(range(0, 11)), list(range(10, 13))],
        )
        async with AsyncPublicClient() as client:
            _install_async_data_transport(client, handler)
            paginator = client._paginate_offset(_spec(), page_size=10)
            collected: list[int] = []
            async for page in paginator:
                collected.extend(page.items)

        assert collected == list(range(13))
        assert len(captured) == 2
        qs1 = parse_qs(urlparse(str(captured[1].url)).query)
        assert qs1["offset"] == ["10"]
        assert qs1["limit"] == ["11"]

    asyncio.run(run())


def test_async_paginate_offset_cursor_rejects_different_endpoint() -> None:
    async def run() -> None:
        captured: list[httpx.Request] = []
        handler = _items_handler(captured, [list(range(11))])
        async with AsyncPublicClient() as client:
            _install_async_data_transport(client, handler)
            paginator = client._paginate_offset(_spec(path="/positions"), page_size=10)
            first = await paginator.first_page()
            assert first.next_cursor is not None
            other = client._paginate_offset(_spec(path="/trades"), page_size=10)
            with pytest.raises(UserInputError, match="does not belong"):
                await other.from_cursor(first.next_cursor).first_page()

    asyncio.run(run())


def test_async_paginate_offset_cursor_rejects_different_query() -> None:
    async def run() -> None:
        captured: list[httpx.Request] = []
        handler = _items_handler(captured, [list(range(11))])
        async with AsyncPublicClient() as client:
            _install_async_data_transport(client, handler)
            a_paginator = client._paginate_offset(_spec(base_params={"user": "0xA"}), page_size=10)
            first = await a_paginator.first_page()
            assert first.next_cursor is not None
            b_paginator = client._paginate_offset(_spec(base_params={"user": "0xB"}), page_size=10)
            with pytest.raises(UserInputError, match="different query parameters"):
                await b_paginator.from_cursor(first.next_cursor).first_page()

    asyncio.run(run())
