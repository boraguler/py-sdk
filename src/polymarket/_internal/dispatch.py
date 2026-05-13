from __future__ import annotations

from typing import TypeVar, assert_never

from polymarket._internal.context import AsyncClientContext, SyncClientContext
from polymarket._internal.pagination import compute_offset_page, decode_offset_cursor
from polymarket._internal.request import OffsetPaginatedSpec, RequestSpec, Service
from polymarket.clients._transport import AsyncTransport, SyncTransport
from polymarket.errors import UserInputError
from polymarket.pagination import AsyncPaginator, Page, Paginator

T = TypeVar("T")


def _sync_transport_for(ctx: SyncClientContext, service: Service) -> SyncTransport:
    match service:
        case "gamma":
            return ctx.gamma
        case "data":
            return ctx.data
        case _ as unreachable:
            assert_never(unreachable)


def _async_transport_for(ctx: AsyncClientContext, service: Service) -> AsyncTransport:
    match service:
        case "gamma":
            return ctx.gamma
        case "data":
            return ctx.data
        case _ as unreachable:
            assert_never(unreachable)


def sync_dispatch(ctx: SyncClientContext, spec: RequestSpec[T]) -> T:
    transport = _sync_transport_for(ctx, spec.service)
    match spec.method:
        case "GET":
            payload = transport.get_json(spec.path, params=spec.params)
        case _ as unreachable:
            assert_never(unreachable)
    return spec.parse(payload)


async def async_dispatch(ctx: AsyncClientContext, spec: RequestSpec[T]) -> T:
    transport = _async_transport_for(ctx, spec.service)
    match spec.method:
        case "GET":
            payload = await transport.get_json(spec.path, params=spec.params)
        case _ as unreachable:
            assert_never(unreachable)
    return spec.parse(payload)


def sync_paginate_offset(
    ctx: SyncClientContext,
    spec: OffsetPaginatedSpec[T],
    *,
    page_size: int,
    initial_cursor: str | None = None,
) -> Paginator[T]:
    if page_size < 1:
        raise UserInputError("page_size must be a positive integer.")
    transport = _sync_transport_for(ctx, spec.service)

    def fetch(cursor: str | None) -> Page[T]:
        offset, effective_size = (
            decode_offset_cursor(
                cursor,
                expected_service=spec.service,
                expected_path=spec.path,
                expected_base_params=spec.base_params,
            )
            if cursor is not None
            else (0, page_size)
        )
        params: dict[str, str | int | float | bool] = {
            **(spec.base_params or {}),
            "limit": effective_size + 1,
            "offset": offset,
        }
        payload = transport.get_json(spec.path, params=params)
        items = spec.parse_items(payload)
        return compute_offset_page(
            service=spec.service,
            path=spec.path,
            base_params=spec.base_params,
            offset=offset,
            page_size=effective_size,
            items=items,
        )

    return Paginator(fetch=fetch, initial_cursor=initial_cursor)


def async_paginate_offset(
    ctx: AsyncClientContext,
    spec: OffsetPaginatedSpec[T],
    *,
    page_size: int,
    initial_cursor: str | None = None,
) -> AsyncPaginator[T]:
    if page_size < 1:
        raise UserInputError("page_size must be a positive integer.")
    transport = _async_transport_for(ctx, spec.service)

    async def fetch(cursor: str | None) -> Page[T]:
        offset, effective_size = (
            decode_offset_cursor(
                cursor,
                expected_service=spec.service,
                expected_path=spec.path,
                expected_base_params=spec.base_params,
            )
            if cursor is not None
            else (0, page_size)
        )
        params: dict[str, str | int | float | bool] = {
            **(spec.base_params or {}),
            "limit": effective_size + 1,
            "offset": offset,
        }
        payload = await transport.get_json(spec.path, params=params)
        items = spec.parse_items(payload)
        return compute_offset_page(
            service=spec.service,
            path=spec.path,
            base_params=spec.base_params,
            offset=offset,
            page_size=effective_size,
            items=items,
        )

    return AsyncPaginator(fetch=fetch, initial_cursor=initial_cursor)


__all__ = [
    "async_dispatch",
    "async_paginate_offset",
    "sync_dispatch",
    "sync_paginate_offset",
]
