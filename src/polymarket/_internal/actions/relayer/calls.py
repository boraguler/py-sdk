from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from eth_abi.abi import encode as abi_encode
from eth_utils.crypto import keccak

from polymarket.errors import UserInputError
from polymarket.types import EvmAddress, HexString

MAX_UINT256 = (1 << 256) - 1


def _selector(signature: str) -> bytes:
    return keccak(signature.encode("ascii"))[:4]


_ERC20_APPROVE_SELECTOR = _selector("approve(address,uint256)")
_SAFE_MULTISEND_SELECTOR = _selector("multiSend(bytes)")
_PROXY_FACTORY_SELECTOR = _selector("proxy((uint8,address,uint256,bytes)[])")
_INNER_OPERATION_CALL = 0
_PROXY_TYPE_CODE_CALL = 1


@dataclass(frozen=True, slots=True)
class TransactionCall:
    to: EvmAddress
    data: HexString
    value: int = 0


def erc20_approval_call(
    *, token_address: EvmAddress, spender: EvmAddress, amount: int
) -> TransactionCall:
    if not isinstance(amount, int) or isinstance(amount, bool):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise UserInputError("Approval amount must be an int")
    if amount < 0:
        raise UserInputError("Approval amount must be non-negative")
    if amount > MAX_UINT256:
        raise UserInputError("Approval amount exceeds uint256 range")
    payload = _ERC20_APPROVE_SELECTOR + abi_encode(["address", "uint256"], [str(spender), amount])
    return TransactionCall(
        to=token_address,
        data=cast(HexString, "0x" + payload.hex()),
    )


def encode_proxy_call(calls: list[TransactionCall]) -> HexString:
    if not calls:
        raise UserInputError("encode_proxy_call requires at least one call")
    tuples = [
        (_PROXY_TYPE_CODE_CALL, str(call.to), call.value, _to_bytes(call.data)) for call in calls
    ]
    encoded_args = abi_encode(
        ["(uint8,address,uint256,bytes)[]"],
        [tuples],
    )
    return cast(HexString, "0x" + (_PROXY_FACTORY_SELECTOR + encoded_args).hex())


def encode_safe_multisend_call(calls: list[TransactionCall]) -> HexString:
    if not calls:
        raise UserInputError("encode_safe_multisend_call requires at least one call")
    inner = b""
    for call in calls:
        to_bytes = _strip_0x_to_bytes(str(call.to))
        if len(to_bytes) != 20:
            raise UserInputError(f"Expected 20-byte address, got {len(to_bytes)} bytes")
        data_bytes = _to_bytes(call.data)
        inner += bytes([_INNER_OPERATION_CALL])
        inner += to_bytes
        inner += call.value.to_bytes(32, "big")
        inner += len(data_bytes).to_bytes(32, "big")
        inner += data_bytes
    payload = _SAFE_MULTISEND_SELECTOR + abi_encode(["bytes"], [inner])
    return cast(HexString, "0x" + payload.hex())


def _to_bytes(value: str) -> bytes:
    s = value[2:] if value.startswith(("0x", "0X")) else value
    return bytes.fromhex(s) if s else b""


def _strip_0x_to_bytes(value: str) -> bytes:
    s = value[2:] if value.startswith(("0x", "0X")) else value
    return bytes.fromhex(s)


__all__ = [
    "MAX_UINT256",
    "TransactionCall",
    "encode_proxy_call",
    "encode_safe_multisend_call",
    "erc20_approval_call",
]
