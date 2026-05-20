from __future__ import annotations

from typing import Any, cast

from polymarket.clients._transport import AsyncTransport
from polymarket.errors import UnexpectedResponseError, UserInputError


class JsonRpcClient:
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport
        self._id = 0
        self._verified_chain_id: int | None = None

    async def close(self) -> None:
        await self._transport.close()

    async def verify_chain_id(self, expected: int) -> None:
        if self._verified_chain_id is not None:
            if self._verified_chain_id != expected:
                raise UserInputError(
                    f"RPC chain id {self._verified_chain_id} does not match "
                    f"environment.chain_id {expected}. Configure rpc_url for the correct chain."
                )
            return
        actual = await self.eth_chain_id()
        if actual != expected:
            raise UserInputError(
                f"RPC chain id {actual} does not match environment.chain_id {expected}. "
                "Configure rpc_url for the correct chain."
            )
        self._verified_chain_id = actual

    async def _call(self, method: str, params: list[Any]) -> Any:
        self._id += 1
        envelope = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": method,
            "params": params,
        }
        raw = await self._transport.post_json("", json=envelope)
        if not isinstance(raw, dict):
            raise UnexpectedResponseError(f"JSON-RPC {method} returned a non-object response")
        response = cast(dict[str, Any], raw)
        if "error" in response:
            err: Any = response["error"]
            message = _extract_error_message(err)
            raise UnexpectedResponseError(f"JSON-RPC {method} failed: {message}")
        return response.get("result")

    async def eth_chain_id(self) -> int:
        result = await self._call("eth_chainId", [])
        return _hex_to_int(result, "eth_chainId")

    async def eth_get_transaction_count(self, address: str, block: str = "pending") -> int:
        result = await self._call("eth_getTransactionCount", [address, block])
        return _hex_to_int(result, "eth_getTransactionCount")

    async def eth_gas_price(self) -> int:
        result = await self._call("eth_gasPrice", [])
        return _hex_to_int(result, "eth_gasPrice")

    async def eth_estimate_gas(self, tx: dict[str, Any]) -> int:
        result = await self._call("eth_estimateGas", [tx])
        return _hex_to_int(result, "eth_estimateGas")

    async def eth_send_raw_transaction(self, signed_hex: str) -> str:
        result = await self._call("eth_sendRawTransaction", [signed_hex])
        if not isinstance(result, str):
            raise UnexpectedResponseError("eth_sendRawTransaction did not return a hex string")
        return result

    async def eth_get_transaction_receipt(self, tx_hash: str) -> dict[str, Any] | None:
        result = await self._call("eth_getTransactionReceipt", [tx_hash])
        if result is None:
            return None
        if not isinstance(result, dict):
            raise UnexpectedResponseError("eth_getTransactionReceipt did not return an object")
        return cast(dict[str, Any], result)


def _extract_error_message(err: object) -> str:
    if isinstance(err, dict):
        err_dict = cast(dict[str, object], err)
        msg = err_dict.get("message")
        if isinstance(msg, str):
            return msg
        return repr(err_dict)
    return str(err)


def _hex_to_int(value: Any, method: str) -> int:
    if not isinstance(value, str):
        raise UnexpectedResponseError(f"{method} did not return a hex string")
    try:
        return int(value, 16)
    except ValueError as error:
        raise UnexpectedResponseError(f"{method} returned malformed hex: {error}") from error


__all__ = ["JsonRpcClient"]
