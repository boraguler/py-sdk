from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from eth_abi.abi import encode as abi_encode
from eth_utils.crypto import keccak
from eth_utils.hexadecimal import decode_hex

from polymarket.errors import UserInputError
from polymarket.types import EvmAddress, HexString

MAX_UINT256 = (1 << 256) - 1


def _selector(signature: str) -> bytes:
    return keccak(signature.encode("ascii"))[:4]


_ERC20_APPROVE_SELECTOR = _selector("approve(address,uint256)")
_ERC20_TRANSFER_SELECTOR = _selector("transfer(address,uint256)")
_ERC1155_SET_APPROVAL_FOR_ALL_SELECTOR = _selector("setApprovalForAll(address,bool)")
_CTF_SPLIT_POSITION_SELECTOR = _selector("splitPosition(address,bytes32,bytes32,uint256[],uint256)")
_CTF_MERGE_POSITIONS_SELECTOR = _selector(
    "mergePositions(address,bytes32,bytes32,uint256[],uint256)"
)
_CTF_REDEEM_POSITIONS_SELECTOR = _selector("redeemPositions(address,bytes32,bytes32,uint256[])")
_NEG_RISK_REDEEM_POSITIONS_SELECTOR = _selector("redeemPositions(bytes32,uint256[])")
_SAFE_MULTISEND_SELECTOR = _selector("multiSend(bytes)")
_PROXY_FACTORY_SELECTOR = _selector("proxy((uint8,address,uint256,bytes)[])")
_INNER_OPERATION_CALL = 0
_PROXY_TYPE_CODE_CALL = 1
_ZERO_BYTES32 = b"\x00" * 32
_BINARY_PARTITION = [1, 2]
_BINARY_INDEX_SETS = [1, 2]


@dataclass(frozen=True, slots=True)
class TransactionCall:
    to: EvmAddress
    data: HexString
    value: int = 0


def erc20_approval_call(
    *, token_address: EvmAddress, spender: EvmAddress, amount: int
) -> TransactionCall:
    _expect_uint256(amount, "Approval amount")
    payload = _ERC20_APPROVE_SELECTOR + abi_encode(["address", "uint256"], [str(spender), amount])
    return TransactionCall(
        to=token_address,
        data=cast(HexString, "0x" + payload.hex()),
    )


def erc20_transfer_call(
    *, token_address: EvmAddress, recipient: EvmAddress, amount: int
) -> TransactionCall:
    _expect_uint256(amount, "Transfer amount")
    payload = _ERC20_TRANSFER_SELECTOR + abi_encode(
        ["address", "uint256"], [str(recipient), amount]
    )
    return TransactionCall(
        to=token_address,
        data=cast(HexString, "0x" + payload.hex()),
    )


def erc1155_set_approval_for_all_call(
    *, token_address: EvmAddress, operator: EvmAddress, approved: bool = True
) -> TransactionCall:
    payload = _ERC1155_SET_APPROVAL_FOR_ALL_SELECTOR + abi_encode(
        ["address", "bool"], [str(operator), approved]
    )
    return TransactionCall(
        to=token_address,
        data=cast(HexString, "0x" + payload.hex()),
    )


def split_position_call(
    *,
    target: EvmAddress,
    collateral: EvmAddress,
    condition_id: str,
    amount: int,
    neg_risk: bool = False,
) -> TransactionCall:
    _expect_uint256(amount, "Split amount")
    partition: list[int] = [] if neg_risk else list(_BINARY_PARTITION)
    payload = _CTF_SPLIT_POSITION_SELECTOR + abi_encode(
        ["address", "bytes32", "bytes32", "uint256[]", "uint256"],
        [str(collateral), _ZERO_BYTES32, _condition_id_bytes(condition_id), partition, amount],
    )
    return TransactionCall(to=target, data=cast(HexString, "0x" + payload.hex()))


def merge_positions_call(
    *,
    target: EvmAddress,
    collateral: EvmAddress,
    condition_id: str,
    amount: int,
    neg_risk: bool = False,
) -> TransactionCall:
    _expect_uint256(amount, "Merge amount")
    partition: list[int] = [] if neg_risk else list(_BINARY_PARTITION)
    payload = _CTF_MERGE_POSITIONS_SELECTOR + abi_encode(
        ["address", "bytes32", "bytes32", "uint256[]", "uint256"],
        [str(collateral), _ZERO_BYTES32, _condition_id_bytes(condition_id), partition, amount],
    )
    return TransactionCall(to=target, data=cast(HexString, "0x" + payload.hex()))


def ctf_redeem_positions_call(
    *,
    ctf: EvmAddress,
    collateral: EvmAddress,
    condition_id: str,
) -> TransactionCall:
    payload = _CTF_REDEEM_POSITIONS_SELECTOR + abi_encode(
        ["address", "bytes32", "bytes32", "uint256[]"],
        [
            str(collateral),
            _ZERO_BYTES32,
            _condition_id_bytes(condition_id),
            list(_BINARY_INDEX_SETS),
        ],
    )
    return TransactionCall(to=ctf, data=cast(HexString, "0x" + payload.hex()))


def neg_risk_redeem_positions_call(
    *,
    neg_risk_adapter: EvmAddress,
    condition_id: str,
    amounts: tuple[int, int],
) -> TransactionCall:
    for amount in amounts:
        _expect_uint256(amount, "Redeem amount")
    payload = _NEG_RISK_REDEEM_POSITIONS_SELECTOR + abi_encode(
        ["bytes32", "uint256[]"],
        [_condition_id_bytes(condition_id), list(amounts)],
    )
    return TransactionCall(to=neg_risk_adapter, data=cast(HexString, "0x" + payload.hex()))


def _expect_uint256(amount: int, label: str) -> None:
    if not isinstance(amount, int) or isinstance(amount, bool):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise UserInputError(f"{label} must be an int")
    if amount < 0:
        raise UserInputError(f"{label} must be non-negative")
    if amount > MAX_UINT256:
        raise UserInputError(f"{label} exceeds uint256 range")


def _condition_id_bytes(condition_id: str) -> bytes:
    s = condition_id[2:] if condition_id.startswith(("0x", "0X")) else condition_id
    try:
        raw = bytes.fromhex(s)
    except ValueError as error:
        raise UserInputError(f"condition_id is not valid hex: {error}") from error
    if len(raw) != 32:
        raise UserInputError(f"condition_id must be a 32-byte hex string, got {len(raw)} bytes")
    return raw


def encode_proxy_call(calls: list[TransactionCall]) -> HexString:
    if not calls:
        raise UserInputError("encode_proxy_call requires at least one call")
    tuples = [
        (_PROXY_TYPE_CODE_CALL, str(call.to), call.value, decode_hex(call.data)) for call in calls
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
        to_bytes = decode_hex(str(call.to))
        if len(to_bytes) != 20:
            raise UserInputError(f"Expected 20-byte address, got {len(to_bytes)} bytes")
        data_bytes = decode_hex(call.data)
        inner += bytes([_INNER_OPERATION_CALL])
        inner += to_bytes
        inner += call.value.to_bytes(32, "big")
        inner += len(data_bytes).to_bytes(32, "big")
        inner += data_bytes
    payload = _SAFE_MULTISEND_SELECTOR + abi_encode(["bytes"], [inner])
    return cast(HexString, "0x" + payload.hex())


__all__ = [
    "MAX_UINT256",
    "TransactionCall",
    "ctf_redeem_positions_call",
    "encode_proxy_call",
    "encode_safe_multisend_call",
    "erc1155_set_approval_for_all_call",
    "erc20_approval_call",
    "erc20_transfer_call",
    "merge_positions_call",
    "neg_risk_redeem_positions_call",
    "split_position_call",
]
