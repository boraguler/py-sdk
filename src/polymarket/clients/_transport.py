"""Internal HTTP transport helpers."""

from __future__ import annotations

from typing import Any

import httpx

from polymarket.errors import (
    RateLimitError,
    RequestRejectedError,
    TransportError,
    UnexpectedResponseError,
)


class SyncTransport:
    """Synchronous HTTP transport with SDK error mapping."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 10,
        client: httpx.Client | None = None,
    ) -> None:
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def get_json(self, path: str) -> Any:
        """GET a JSON response body."""
        response = self._request("GET", path)
        return _read_json(response)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def _request(self, method: str, path: str) -> httpx.Response:
        try:
            response = self._client.request(method, path)
        except httpx.HTTPError as error:
            raise TransportError(str(error) or "Request failed") from error

        _raise_for_response_status(response)
        return response


class AsyncTransport:
    """Asynchronous HTTP transport with SDK error mapping."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 10,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def get_json(self, path: str) -> Any:
        """GET a JSON response body."""
        response = await self._request("GET", path)
        return _read_json(response)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def _request(self, method: str, path: str) -> httpx.Response:
        try:
            response = await self._client.request(method, path)
        except httpx.HTTPError as error:
            raise TransportError(str(error) or "Request failed") from error

        _raise_for_response_status(response)
        return response


def _raise_for_response_status(response: httpx.Response) -> None:
    if response.is_success:
        return

    if response.status_code == 429:
        raise RateLimitError(f"Request to {response.url} was rate limited")

    raise RequestRejectedError(
        _extract_response_error_message(response),
        status=response.status_code,
    )


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
