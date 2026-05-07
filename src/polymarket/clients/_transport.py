from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

from polymarket.errors import (
    RateLimitError,
    RequestRejectedError,
    TransportError,
    UnexpectedResponseError,
)

QueryParamValue = str | int | float | bool


_DEFAULT_LIMITS = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20,
    keepalive_expiry=30,
)
_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=2.0)


@dataclass(frozen=True, slots=True, kw_only=True)
class TransportOptions:
    limits: httpx.Limits = field(default_factory=lambda: _DEFAULT_LIMITS)
    timeout: httpx.Timeout = field(default_factory=lambda: _DEFAULT_TIMEOUT)
    http2: bool = True
    event_hooks: Mapping[str, list[Any]] | None = None


class SyncTransport:
    def __init__(
        self,
        *,
        base_url: str,
        options: TransportOptions | None = None,
        logger: logging.Logger | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        opts = options or TransportOptions()
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=base_url,
            timeout=opts.timeout,
            limits=opts.limits,
            http2=opts.http2,
            event_hooks=dict(opts.event_hooks) if opts.event_hooks else None,
        )
        self._logger = logger

    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, QueryParamValue | None] | None = None,
    ) -> Any:
        response = self._request("GET", path, params=params)
        return _read_json(response)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, QueryParamValue | None] | None = None,
    ) -> httpx.Response:
        started = time.perf_counter()
        try:
            response = self._client.request(method, path, params=_clean_params(params))
        except httpx.HTTPError as error:
            self._log_failure(method, path, error, started)
            raise TransportError(str(error) or "Request failed") from error

        self._log_response(method, path, response, started)
        _raise_for_response_status(response)
        return response

    def _log_response(
        self,
        method: str,
        path: str,
        response: httpx.Response,
        started: float,
    ) -> None:
        if self._logger is None or not self._logger.isEnabledFor(logging.DEBUG):
            return
        self._logger.debug(
            "polymarket http %s %s -> %d in %.1fms",
            method,
            path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )

    def _log_failure(
        self,
        method: str,
        path: str,
        error: Exception,
        started: float,
    ) -> None:
        if self._logger is None:
            return
        self._logger.warning(
            "polymarket http %s %s failed in %.1fms: %s",
            method,
            path,
            (time.perf_counter() - started) * 1000,
            error,
        )


class AsyncTransport:
    def __init__(
        self,
        *,
        base_url: str,
        options: TransportOptions | None = None,
        logger: logging.Logger | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        opts = options or TransportOptions()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            timeout=opts.timeout,
            limits=opts.limits,
            http2=opts.http2,
            event_hooks=dict(opts.event_hooks) if opts.event_hooks else None,
        )
        self._logger = logger

    async def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, QueryParamValue | None] | None = None,
    ) -> Any:
        response = await self._request("GET", path, params=params)
        return _read_json(response)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, QueryParamValue | None] | None = None,
    ) -> httpx.Response:
        started = time.perf_counter()
        try:
            response = await self._client.request(method, path, params=_clean_params(params))
        except httpx.HTTPError as error:
            self._log_failure(method, path, error, started)
            raise TransportError(str(error) or "Request failed") from error

        self._log_response(method, path, response, started)
        _raise_for_response_status(response)
        return response

    def _log_response(
        self,
        method: str,
        path: str,
        response: httpx.Response,
        started: float,
    ) -> None:
        if self._logger is None or not self._logger.isEnabledFor(logging.DEBUG):
            return
        self._logger.debug(
            "polymarket http %s %s -> %d in %.1fms",
            method,
            path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )

    def _log_failure(
        self,
        method: str,
        path: str,
        error: Exception,
        started: float,
    ) -> None:
        if self._logger is None:
            return
        self._logger.warning(
            "polymarket http %s %s failed in %.1fms: %s",
            method,
            path,
            (time.perf_counter() - started) * 1000,
            error,
        )


def _raise_for_response_status(response: httpx.Response) -> None:
    if response.is_success:
        return

    if response.status_code == 429:
        raise RateLimitError(f"Request to {response.url} was rate limited")

    raise RequestRejectedError(
        _extract_response_error_message(response),
        status=response.status_code,
    )


def _clean_params(
    params: Mapping[str, QueryParamValue | None] | None,
) -> dict[str, QueryParamValue] | None:
    if params is None:
        return None

    return {key: value for key, value in params.items() if value is not None}


def _read_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as error:
        raise UnexpectedResponseError(f"Received non-JSON response from {response.url}") from error


def _extract_response_error_message(response: httpx.Response) -> str:
    content_type = response.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            error = response.json().get("error")
        except (AttributeError, ValueError):
            error = None
        if error:
            return str(error)

    if "text/plain" in content_type:
        text = response.text.strip()
        if text:
            return text

    server = response.headers.get("server", "").lower()
    if "cloudflare" in server:
        return (
            f"Request to {response.url} was blocked by Cloudflare "
            f"with status {response.status_code}"
        )

    if "text/html" in content_type or "application/xhtml+xml" in content_type:
        return (
            f"Request to {response.url} failed with status {response.status_code} "
            "and an unexpected HTML response body"
        )

    return (
        f"Request to {response.url} failed with status {response.status_code} "
        "and unreadable response body"
    )
