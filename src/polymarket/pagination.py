"""Paginators and pages returned by SDK list-style endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar, cast

from polymarket._frames_bridge import frames_func as _frames_func
from polymarket.errors import UnexpectedResponseError

T = TypeVar("T")


# Frame-method returns are typed as ``Any`` because pandas/polars/pyarrow
# stubs don't survive strict-mode pyright. Drain ``limit`` is required so
# multi-page truncation can't be silent.
LimitArg = int | None
DecimalMode = Literal["decimal", "float"]


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: tuple[T, ...]
    has_more: bool
    next_cursor: str | None = None
    total_count: int | None = None

    def to_arrow(self) -> Any:
        return _frames_func("to_arrow")(self)

    def to_pandas(
        self,
        *,
        decimal: DecimalMode = "decimal",
        explode: Sequence[str] | None = None,
    ) -> Any:
        return _frames_func("to_pandas")(self, decimal=decimal, explode=explode)

    def to_polars(
        self,
        *,
        explode: Sequence[str] | None = None,
    ) -> Any:
        return _frames_func("to_polars")(self, explode=explode)


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

    def to_arrow(self, *, limit: LimitArg) -> Any:
        items, _truncated = _drain_paginator(self, limit)
        return _frames_func("to_arrow")(tuple(items))

    def to_pandas(
        self,
        *,
        limit: LimitArg,
        decimal: DecimalMode = "decimal",
        explode: Sequence[str] | None = None,
    ) -> Any:
        items, truncated = _drain_paginator(self, limit)
        df = _frames_func("to_pandas")(tuple(items), decimal=decimal, explode=explode)
        if truncated:
            df.attrs["polymarket_truncated"] = True
        return df

    def to_polars(
        self,
        *,
        limit: LimitArg,
        explode: Sequence[str] | None = None,
    ) -> Any:
        items, _truncated = _drain_paginator(self, limit)
        return _frames_func("to_polars")(tuple(items), explode=explode)


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

    async def to_arrow(self, *, limit: LimitArg) -> Any:
        items, _truncated = await _drain_async_paginator(self, limit)
        return _frames_func("to_arrow")(tuple(items))

    async def to_pandas(
        self,
        *,
        limit: LimitArg,
        decimal: DecimalMode = "decimal",
        explode: Sequence[str] | None = None,
    ) -> Any:
        items, truncated = await _drain_async_paginator(self, limit)
        df = _frames_func("to_pandas")(tuple(items), decimal=decimal, explode=explode)
        if truncated:
            df.attrs["polymarket_truncated"] = True
        return df

    async def to_polars(
        self,
        *,
        limit: LimitArg,
        explode: Sequence[str] | None = None,
    ) -> Any:
        items, _truncated = await _drain_async_paginator(self, limit)
        return _frames_func("to_polars")(tuple(items), explode=explode)


def _drain_paginator(paginator: Paginator[T], limit: int | None) -> tuple[list[T], bool]:
    if limit is None:
        return list(paginator.items()), False
    if limit < 0:
        from polymarket.errors import UserInputError

        raise UserInputError(f"limit must be >= 0 or None; got {limit}.")
    if limit == 0:
        # Skip the fetch entirely; with no observation we can't claim truncation.
        return [], False
    out: list[T] = []
    truncated = False
    for item in paginator.items():
        if len(out) >= limit:
            truncated = True
            break
        out.append(item)
    return out, truncated


async def _drain_async_paginator(
    paginator: AsyncPaginator[T], limit: int | None
) -> tuple[list[T], bool]:
    if limit is None:
        out: list[T] = []
        async for item in paginator.items():
            out.append(item)
        return out, False
    if limit < 0:
        from polymarket.errors import UserInputError

        raise UserInputError(f"limit must be >= 0 or None; got {limit}.")
    if limit == 0:
        return [], False
    out2: list[T] = []
    truncated = False
    async for item in paginator.items():
        if len(out2) >= limit:
            truncated = True
            break
        out2.append(item)
    return out2, truncated


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
        yield  # pragma: no cover - forces this method to be an async generator


def _empty_sync_fetch(_cursor: str | None) -> Page[object]:
    return Page(items=(), has_more=False)


async def _empty_async_fetch(_cursor: str | None) -> Page[object]:
    return Page(items=(), has_more=False)


__all__ = ["AsyncPaginator", "DecimalMode", "LimitArg", "Page", "Paginator"]
