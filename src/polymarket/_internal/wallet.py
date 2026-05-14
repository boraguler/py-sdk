from __future__ import annotations

from typing import Literal, TypeAlias

from eth_abi.abi import encode as abi_encode
from eth_abi.packed import encode_packed
from eth_utils.address import to_checksum_address
from eth_utils.crypto import keccak

from polymarket.environments import WalletDerivation
from polymarket.errors import UserInputError

WalletType: TypeAlias = Literal["EOA", "POLY_PROXY", "GNOSIS_SAFE", "DEPOSIT_WALLET"]

_SIGNATURE_TYPE_BY_WALLET: dict[WalletType, int] = {
    "EOA": 0,
    "POLY_PROXY": 1,
    "GNOSIS_SAFE": 2,
    "DEPOSIT_WALLET": 3,
}

_PROXY_BYTECODE_TEMPLATE = (
    "3d3d606380380380913d393d73"
    "{factory}"
    "5af4602a57600080fd5b602d8060366000396000f3363d3d373d3d3d363d73"
    "{impl}"
    "5af43d82803e903d91602b57fd5bf352e831dd"
    "0000000000000000000000000000000000000000000000000000000000000020"
    "0000000000000000000000000000000000000000000000000000000000000000"
)

_ERC1967_CONST1 = bytes.fromhex("cc3735a920a3ca505d382bbc545af43d6000803e6038573d6000fd5b3d6000f3")
_ERC1967_CONST2 = bytes.fromhex("5155f3363d3d373d3d363d7f360894a13ba1a3210667c828492db98dca3e2076")
_ERC1967_PREFIX_BASE = 0x61003D3D8160233D3973


def signature_type_for(wallet_type: WalletType) -> int:
    return _SIGNATURE_TYPE_BY_WALLET[wallet_type]


def derive_proxy_wallet_address(signer: str, config: WalletDerivation) -> str:
    bytecode = bytes.fromhex(
        _PROXY_BYTECODE_TEMPLATE.format(
            factory=_strip_0x(config.proxy_factory).lower(),
            impl=_strip_0x(config.proxy_implementation).lower(),
        )
    )
    bytecode_hash = keccak(bytecode)
    salt = keccak(encode_packed(["address"], [signer]))
    return _create2(config.proxy_factory, salt, bytecode_hash)


def derive_safe_wallet_address(signer: str, config: WalletDerivation) -> str:
    bytecode_hash = bytes.fromhex(_strip_0x(config.safe_init_code_hash))
    salt = keccak(abi_encode(["address"], [signer]))
    return _create2(config.safe_factory, salt, bytecode_hash)


def derive_deposit_wallet_address(signer: str, config: WalletDerivation) -> str:
    signer_bytes = bytes.fromhex(_strip_0x(signer))
    wallet_id = signer_bytes.rjust(32, b"\x00")
    args = abi_encode(["address", "bytes32"], [config.deposit_wallet_factory, wallet_id])
    bytecode_hash = _deposit_init_code_hash(config.deposit_wallet_implementation, args)
    salt = keccak(args)
    return _create2(config.deposit_wallet_factory, salt, bytecode_hash)


def classify_wallet_type(*, signer: str, wallet: str, config: WalletDerivation) -> WalletType:
    try:
        signer_checksum = to_checksum_address(signer)
    except ValueError as error:
        raise UserInputError(f"Invalid signer address: {error}") from error
    try:
        wallet_checksum = to_checksum_address(wallet)
    except ValueError as error:
        raise UserInputError(f"Invalid wallet address: {error}") from error

    if wallet_checksum == signer_checksum:
        return "EOA"
    if wallet_checksum == derive_deposit_wallet_address(signer_checksum, config):
        return "DEPOSIT_WALLET"
    if wallet_checksum == derive_proxy_wallet_address(signer_checksum, config):
        return "POLY_PROXY"
    if wallet_checksum == derive_safe_wallet_address(signer_checksum, config):
        return "GNOSIS_SAFE"

    raise UserInputError(
        f"Wallet {wallet_checksum} does not match the signer {signer_checksum} "
        "or any supported deterministic wallet address."
    )


def _create2(factory: str, salt: bytes, bytecode_hash: bytes) -> str:
    factory_bytes = bytes.fromhex(_strip_0x(factory))
    raw = b"\xff" + factory_bytes + salt + bytecode_hash
    return to_checksum_address("0x" + keccak(raw)[12:].hex())


def _deposit_init_code_hash(implementation: str, args: bytes) -> bytes:
    args_byte_length = len(args)
    prefix = _ERC1967_PREFIX_BASE + (args_byte_length << 56)
    prefix_bytes = prefix.to_bytes(10, "big")
    impl_bytes = bytes.fromhex(_strip_0x(implementation))
    bytecode = (
        prefix_bytes + impl_bytes + bytes.fromhex("6009") + _ERC1967_CONST2 + _ERC1967_CONST1 + args
    )
    return keccak(bytecode)


def _strip_0x(value: str) -> str:
    return value[2:] if value.startswith(("0x", "0X")) else value


__all__ = [
    "WalletType",
    "classify_wallet_type",
    "derive_deposit_wallet_address",
    "derive_proxy_wallet_address",
    "derive_safe_wallet_address",
    "signature_type_for",
]
