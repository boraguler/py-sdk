import pytest
from eth_abi.abi import encode as abi_encode
from eth_utils.crypto import keccak

from polymarket._internal.actions.relayer.calls import (
    MAX_UINT256,
    ctf_redeem_positions_call,
    erc20_approval_call,
    erc20_transfer_call,
    erc1155_set_approval_for_all_call,
    merge_positions_call,
    split_position_call,
)
from polymarket.errors import UserInputError
from polymarket.types import EvmAddress

_USDC = EvmAddress("0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB")
_CTF = EvmAddress("0x4D97DCd97eC945f40cF65F87097ACe5EA0476045")
_NEG_RISK_ADAPTER = EvmAddress("0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296")
_STANDARD_EXCHANGE = EvmAddress("0xE111180000d2663C0091e4f400237545B87B996B")
_RECIPIENT = EvmAddress("0x000000000000000000000000000000000000dEaD")
_CONDITION_ID = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
_ZERO_BYTES32 = b"\x00" * 32


def _sel(sig: str) -> bytes:
    return keccak(sig.encode("ascii"))[:4]


def _cond_bytes(cid: str) -> bytes:
    return bytes.fromhex(cid[2:] if cid.startswith("0x") else cid)


def test_erc20_transfer_call_golden_calldata() -> None:
    call = erc20_transfer_call(token_address=_USDC, recipient=_RECIPIENT, amount=123)
    expected = (
        "0x"
        + (
            _sel("transfer(address,uint256)")
            + abi_encode(["address", "uint256"], [str(_RECIPIENT), 123])
        ).hex()
    )
    assert call.to == _USDC
    assert call.value == 0
    assert call.data == expected


def test_erc20_transfer_call_rejects_negative_amount() -> None:
    with pytest.raises(UserInputError, match="non-negative"):
        erc20_transfer_call(token_address=_USDC, recipient=_RECIPIENT, amount=-1)


def test_erc1155_set_approval_for_all_call_golden_calldata() -> None:
    call = erc1155_set_approval_for_all_call(
        token_address=_CTF, operator=_STANDARD_EXCHANGE, approved=True
    )
    expected = (
        "0x"
        + (
            _sel("setApprovalForAll(address,bool)")
            + abi_encode(["address", "bool"], [str(_STANDARD_EXCHANGE), True])
        ).hex()
    )
    assert call.to == _CTF
    assert call.data == expected


def test_erc1155_set_approval_for_all_call_revoke() -> None:
    call = erc1155_set_approval_for_all_call(
        token_address=_CTF, operator=_STANDARD_EXCHANGE, approved=False
    )
    expected = (
        "0x"
        + (
            _sel("setApprovalForAll(address,bool)")
            + abi_encode(["address", "bool"], [str(_STANDARD_EXCHANGE), False])
        ).hex()
    )
    assert call.data == expected


def test_split_position_call_binary_partition() -> None:
    call = split_position_call(
        target=_CTF,
        collateral=_USDC,
        condition_id=_CONDITION_ID,
        amount=1_000_000,
    )
    expected = (
        "0x"
        + (
            _sel("splitPosition(address,bytes32,bytes32,uint256[],uint256)")
            + abi_encode(
                ["address", "bytes32", "bytes32", "uint256[]", "uint256"],
                [str(_USDC), _ZERO_BYTES32, _cond_bytes(_CONDITION_ID), [1, 2], 1_000_000],
            )
        ).hex()
    )
    assert call.to == _CTF
    assert call.data == expected


def test_split_position_call_rejects_negative_amount() -> None:
    with pytest.raises(UserInputError, match="non-negative"):
        split_position_call(
            target=_CTF,
            collateral=_USDC,
            condition_id=_CONDITION_ID,
            amount=-1,
        )


def test_split_position_call_rejects_above_uint256() -> None:
    with pytest.raises(UserInputError, match="uint256"):
        split_position_call(
            target=_CTF,
            collateral=_USDC,
            condition_id=_CONDITION_ID,
            amount=MAX_UINT256 + 1,
        )


def test_split_position_call_rejects_bad_condition_id() -> None:
    with pytest.raises(UserInputError, match="32-byte"):
        split_position_call(target=_CTF, collateral=_USDC, condition_id="0x1234", amount=1)


def test_split_position_call_rejects_non_hex_condition_id() -> None:
    with pytest.raises(UserInputError, match="not valid hex"):
        split_position_call(
            target=_CTF, collateral=_USDC, condition_id="0xZZZZZZZZ" + "11" * 30, amount=1
        )


def test_merge_positions_call_binary_partition() -> None:
    call = merge_positions_call(
        target=_CTF,
        collateral=_USDC,
        condition_id=_CONDITION_ID,
        amount=5,
    )
    expected = (
        "0x"
        + (
            _sel("mergePositions(address,bytes32,bytes32,uint256[],uint256)")
            + abi_encode(
                ["address", "bytes32", "bytes32", "uint256[]", "uint256"],
                [str(_USDC), _ZERO_BYTES32, _cond_bytes(_CONDITION_ID), [1, 2], 5],
            )
        ).hex()
    )
    assert call.data == expected


def test_ctf_redeem_positions_call_golden_calldata() -> None:
    call = ctf_redeem_positions_call(ctf=_CTF, collateral=_USDC, condition_id=_CONDITION_ID)
    expected = (
        "0x"
        + (
            _sel("redeemPositions(address,bytes32,bytes32,uint256[])")
            + abi_encode(
                ["address", "bytes32", "bytes32", "uint256[]"],
                [str(_USDC), _ZERO_BYTES32, _cond_bytes(_CONDITION_ID), [1, 2]],
            )
        ).hex()
    )
    assert call.to == _CTF
    assert call.data == expected


def test_erc20_approval_call_max_amount() -> None:
    call = erc20_approval_call(token_address=_USDC, spender=_STANDARD_EXCHANGE, amount=MAX_UINT256)
    assert call.data.lower().endswith("f" * 64)
