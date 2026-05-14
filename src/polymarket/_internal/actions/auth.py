from typing import cast

from pydantic import TypeAdapter, ValidationError

from polymarket._internal.l1_auth import ApiKeyAuthSignature
from polymarket.clients._transport import AsyncTransport
from polymarket.errors import RequestRejectedError, UnexpectedResponseError
from polymarket.models.clob import ApiKeyCreds

_ApiKeysListAdapter = TypeAdapter(tuple[str, ...])


def build_l1_auth_headers(signature: ApiKeyAuthSignature) -> dict[str, str]:
    return {
        "POLY_ADDRESS": signature.address,
        "POLY_NONCE": str(signature.nonce),
        "POLY_SIGNATURE": signature.signature,
        "POLY_TIMESTAMP": str(signature.timestamp),
    }


def parse_api_key_creds(data: object) -> ApiKeyCreds:
    return ApiKeyCreds.parse_response(data)


def parse_api_keys_response(data: object) -> tuple[str, ...]:
    if not isinstance(data, dict):
        raise UnexpectedResponseError("api keys response did not match expected shape")
    api_keys = cast(dict[str, object], data).get("apiKeys")
    try:
        return _ApiKeysListAdapter.validate_python(api_keys)
    except ValidationError as error:
        raise UnexpectedResponseError("api keys response did not match expected shape") from error


async def create_api_key(clob: AsyncTransport, signature: ApiKeyAuthSignature) -> ApiKeyCreds:
    payload = await clob.post_json("/auth/api-key", headers=build_l1_auth_headers(signature))
    return parse_api_key_creds(payload)


async def derive_api_key(clob: AsyncTransport, signature: ApiKeyAuthSignature) -> ApiKeyCreds:
    payload = await clob.get_json("/auth/derive-api-key", headers=build_l1_auth_headers(signature))
    return parse_api_key_creds(payload)


async def create_or_derive_api_key(
    clob: AsyncTransport, signature: ApiKeyAuthSignature
) -> ApiKeyCreds:
    try:
        return await create_api_key(clob, signature)
    except RequestRejectedError as error:
        if error.status != 400:
            raise
    return await derive_api_key(clob, signature)


async def fetch_api_keys(secure_clob: AsyncTransport) -> tuple[str, ...]:
    payload = await secure_clob.get_json("/auth/api-keys")
    return parse_api_keys_response(payload)


async def delete_api_key(secure_clob: AsyncTransport) -> None:
    payload = await secure_clob.delete_json("/auth/api-key")
    if payload != "OK":
        raise UnexpectedResponseError(
            f"delete api key response did not match expected shape: {payload!r}"
        )


__all__ = [
    "build_l1_auth_headers",
    "create_api_key",
    "create_or_derive_api_key",
    "delete_api_key",
    "derive_api_key",
    "fetch_api_keys",
    "parse_api_key_creds",
    "parse_api_keys_response",
]
