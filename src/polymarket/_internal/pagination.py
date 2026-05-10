from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from polymarket._internal.request import QueryParamValue
from polymarket.errors import UnexpectedResponseError, UserInputError

T = TypeVar("T")

_CURSOR_VERSION = 1
_FINGERPRINT_LEN = 12


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: tuple[T, ...]
    has_more: bool
    next_cursor: str | None = None
    total_count: int | None = None


class Paginator(Generic[T]):
    def __init__(
        self,
        fetch: Callable[[str | None], Page[T]],
        initial_cursor: str | None = None,
    ) -> None:
        self._fetch = fetch
        self._initial_cursor = initial_cursor

    def first_page(self) -> Page[T]:
        return self._fetch(self._initial_cursor)

    def from_cursor(self, cursor: str | None) -> Paginator[T]:
        if cursor is None:
            return cast(Paginator[T], _EmptyPaginator())
        return Paginator(self._fetch, initial_cursor=cursor)

    def __iter__(self) -> Iterator[Page[T]]:
        return self._iter_pages()

    def items(self) -> Iterator[T]:
        for page in self._iter_pages():
            yield from page.items

    def _iter_pages(self) -> Iterator[Page[T]]:
        cursor = self._initial_cursor
        while True:
            page = self._fetch(cursor)
            yield page
            if not page.has_more:
                return
            if page.next_cursor is None:
                raise UnexpectedResponseError(
                    "Paginated response set has_more=True without a next cursor."
                )
            cursor = page.next_cursor


class AsyncPaginator(Generic[T]):
    def __init__(
        self,
        fetch: Callable[[str | None], Awaitable[Page[T]]],
        initial_cursor: str | None = None,
    ) -> None:
        self._fetch = fetch
        self._initial_cursor = initial_cursor

    async def first_page(self) -> Page[T]:
        return await self._fetch(self._initial_cursor)

    def from_cursor(self, cursor: str | None) -> AsyncPaginator[T]:
        if cursor is None:
            return cast(AsyncPaginator[T], _EmptyAsyncPaginator())
        return AsyncPaginator(self._fetch, initial_cursor=cursor)

    def __aiter__(self) -> AsyncIterator[Page[T]]:
        return self._iter_pages()

    def items(self) -> AsyncIterator[T]:
        return self._iter_items()

    async def _iter_pages(self) -> AsyncIterator[Page[T]]:
        cursor = self._initial_cursor
        while True:
            page = await self._fetch(cursor)
            yield page
            if not page.has_more:
                return
            if page.next_cursor is None:
                raise UnexpectedResponseError(
                    "Paginated response set has_more=True without a next cursor."
                )
            cursor = page.next_cursor

    async def _iter_items(self) -> AsyncIterator[T]:
        async for page in self._iter_pages():
            for item in page.items:
                yield item


class _EmptyPaginator(Paginator[object]):
    def __init__(self) -> None:
        super().__init__(fetch=_empty_sync_fetch, initial_cursor=None)

    def first_page(self) -> Page[object]:
        return Page(items=(), has_more=False)

    def from_cursor(self, cursor: str | None) -> Paginator[object]:
        if cursor is None:
            return self
        return Paginator(self._fetch, initial_cursor=cursor)

    def _iter_pages(self) -> Iterator[Page[object]]:
        return iter(())


class _EmptyAsyncPaginator(AsyncPaginator[object]):
    def __init__(self) -> None:
        super().__init__(fetch=_empty_async_fetch, initial_cursor=None)

    async def first_page(self) -> Page[object]:
        return Page(items=(), has_more=False)

    def from_cursor(self, cursor: str | None) -> AsyncPaginator[object]:
        if cursor is None:
            return self
        return AsyncPaginator(self._fetch, initial_cursor=cursor)

    async def _iter_pages(self) -> AsyncIterator[Page[object]]:
        return
        yield  # pragma: no cover - keeps the method an async generator


def _empty_sync_fetch(_cursor: str | None) -> Page[object]:
    return Page(items=(), has_more=False)


async def _empty_async_fetch(_cursor: str | None) -> Page[object]:
    return Page(items=(), has_more=False)


def fingerprint_query(base_params: Mapping[str, QueryParamValue] | None) -> str:
    canonical = json.dumps(
        dict(base_params or {}),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:_FINGERPRINT_LEN]


def encode_offset_cursor(
    *,
    path: str,
    base_params: Mapping[str, QueryParamValue] | None,
    offset: int,
    page_size: int,
) -> str:
    if not path:
        raise UserInputError("path must be a non-empty string.")
    if offset < 0:
        raise UserInputError("offset must be non-negative.")
    if page_size < 1:
        raise UserInputError("page_size must be a positive integer.")
    payload = json.dumps(
        {
            "v": _CURSOR_VERSION,
            "p": path,
            "f": fingerprint_query(base_params),
            "o": offset,
            "s": page_size,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return base64.b64encode(payload.encode("utf-8")).decode("ascii")


def decode_offset_cursor(
    cursor: str,
    *,
    expected_path: str,
    expected_base_params: Mapping[str, QueryParamValue] | None,
) -> tuple[int, int]:
    try:
        decoded = base64.b64decode(cursor, validate=True).decode("utf-8")
        parsed = json.loads(decoded)
    except (binascii.Error, ValueError, UnicodeDecodeError) as error:
        raise UserInputError("Invalid pagination cursor.") from error

    if not isinstance(parsed, dict):
        raise UserInputError("Invalid pagination cursor.")
    payload = cast(dict[str, object], parsed)

    version = payload.get("v")
    if version != _CURSOR_VERSION:
        raise UserInputError(
            f"Unsupported pagination cursor version: {version!r}. Expected {_CURSOR_VERSION}."
        )

    raw_path = payload.get("p")
    if not isinstance(raw_path, str) or raw_path != expected_path:
        raise UserInputError("Pagination cursor does not belong to this endpoint.")

    expected_fingerprint = fingerprint_query(expected_base_params)
    raw_fingerprint = payload.get("f")
    if not isinstance(raw_fingerprint, str) or raw_fingerprint != expected_fingerprint:
        raise UserInputError("Pagination cursor was created with different query parameters.")

    raw_offset = payload.get("o")
    raw_page_size = payload.get("s")
    if not isinstance(raw_offset, int) or isinstance(raw_offset, bool) or raw_offset < 0:
        raise UserInputError("Invalid pagination cursor.")
    if not isinstance(raw_page_size, int) or isinstance(raw_page_size, bool) or raw_page_size < 1:
        raise UserInputError("Invalid pagination cursor.")
    return raw_offset, raw_page_size


def compute_offset_page(
    *,
    path: str,
    base_params: Mapping[str, QueryParamValue] | None,
    offset: int,
    page_size: int,
    items: tuple[T, ...],
) -> Page[T]:
    has_more = len(items) > page_size
    trimmed = items[:page_size]
    next_cursor = (
        encode_offset_cursor(
            path=path,
            base_params=base_params,
            offset=offset + page_size,
            page_size=page_size,
        )
        if has_more
        else None
    )
    return Page(items=trimmed, has_more=has_more, next_cursor=next_cursor)


__all__ = [
    "AsyncPaginator",
    "Page",
    "Paginator",
    "compute_offset_page",
    "decode_offset_cursor",
    "encode_offset_cursor",
    "fingerprint_query",
]
