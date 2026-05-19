from __future__ import annotations

from typing import cast

from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount
from eth_utils.crypto import keccak

from polymarket.errors import SigningError
from polymarket.types import EvmAddress, HexString

_PROXY_PREFIX = b"rlx:"


def build_proxy_transaction_hash(
    *,
    from_address: EvmAddress,
    to: EvmAddress,
    data: HexString,
    relayer_fee: str,
    gas_price: str,
    gas_limit: str,
    nonce: str,
    relay_hub: EvmAddress,
    relay: EvmAddress,
) -> HexString:
    payload = (
        _PROXY_PREFIX
        + _addr_bytes(from_address)
        + _addr_bytes(to)
        + _hex_bytes(data)
        + int(relayer_fee).to_bytes(32, "big")
        + int(gas_price).to_bytes(32, "big")
        + int(gas_limit).to_bytes(32, "big")
        + int(nonce).to_bytes(32, "big")
        + _addr_bytes(relay_hub)
        + _addr_bytes(relay)
    )
    return cast(HexString, "0x" + keccak(payload).hex())


def sign_proxy_message(signer: LocalAccount, message_hash: HexString) -> HexString:
    try:
        signable = encode_defunct(hexstr=message_hash)
        signed = signer.sign_message(signable)
    except Exception as error:
        raise SigningError(f"Failed to sign proxy transaction: {error}") from error
    return cast(HexString, "0x" + signed.signature.hex())


def _addr_bytes(value: str) -> bytes:
    s = value[2:] if value.startswith(("0x", "0X")) else value
    out = bytes.fromhex(s)
    if len(out) != 20:
        raise ValueError(f"Expected 20-byte address, got {len(out)} bytes")
    return out


def _hex_bytes(value: str) -> bytes:
    s = value[2:] if value.startswith(("0x", "0X")) else value
    return bytes.fromhex(s) if s else b""


__all__ = ["build_proxy_transaction_hash", "sign_proxy_message"]
