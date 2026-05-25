from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from polymarket.errors import UnexpectedResponseError

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    """One page of paginated SDK results."""

    items: tuple[T, ...]
    """Items returned on this page."""
    has_more: bool
    """Whether another page is available."""
    next_cursor: str | None = None
    """Cursor to pass to ``from_cursor()`` for the next page, when available."""
    total_count: int | None = None
    """Total matching item count when the API provides it."""


class Paginator(Generic[T]):
    """Synchronous paginator returned by list-style client methods.

    Iterate over the paginator to fetch pages lazily, or call ``items()`` to
    iterate over individual items across pages.
    """

    def __init__(
        self,
        fetch: Callable[[str | None], Page[T]],
        initial_cursor: str | None = None,
    ) -> None:
        self._fetch = fetch
        self._initial_cursor = initial_cursor

    def first_page(self) -> Page[T]:
        """Fetch the first page for this paginator."""
        return self._fetch(self._initial_cursor)

    def from_cursor(self, cursor: str | None) -> Paginator[T]:
        """Create a paginator that starts from ``cursor``.

        Passing ``None`` returns an empty paginator because no next page exists.
        """
        if cursor is None:
            return cast(Paginator[T], _EmptyPaginator())
        return Paginator(self._fetch, initial_cursor=cursor)

    def __iter__(self) -> Iterator[Page[T]]:
        return self._iter_pages()

    def items(self) -> Iterator[T]:
        """Iterate over individual items across all fetched pages."""
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
    """Async paginator returned by async list-style client methods.

    Use ``async for`` over the paginator to fetch pages lazily, or call
    ``items()`` to iterate over individual items across pages.
    """

    def __init__(
        self,
        fetch: Callable[[str | None], Awaitable[Page[T]]],
        initial_cursor: str | None = None,
    ) -> None:
        self._fetch = fetch
        self._initial_cursor = initial_cursor

    async def first_page(self) -> Page[T]:
        """Fetch the first page for this paginator."""
        return await self._fetch(self._initial_cursor)

    def from_cursor(self, cursor: str | None) -> AsyncPaginator[T]:
        """Create an async paginator that starts from ``cursor``.

        Passing ``None`` returns an empty paginator because no next page exists.
        """
        if cursor is None:
            return cast(AsyncPaginator[T], _EmptyAsyncPaginator())
        return AsyncPaginator(self._fetch, initial_cursor=cursor)

    def __aiter__(self) -> AsyncIterator[Page[T]]:
        return self._iter_pages()

    def items(self) -> AsyncIterator[T]:
        """Iterate over individual items across all fetched pages."""
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


__all__ = ["AsyncPaginator", "Page", "Paginator"]
