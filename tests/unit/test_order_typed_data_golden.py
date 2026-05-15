from eth_account import Account
from eth_account.messages import encode_typed_data

from polymarket._internal.actions.orders.typed_data import (
    build_order_signature,
    build_order_typed_data,
)
from polymarket._internal.actions.orders.types import BYTES32_ZERO, UnsignedOrder
from polymarket.models.types import TokenId
from polymarket.types import EvmAddress, HexString

EXCHANGE = EvmAddress("0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e")
DEPOSIT_WALLET = EvmAddress("0x57ffbc34de23124faeb8387fcd689d314e57accd")
EVM_SIGNATURE = HexString(
    "0x111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111b"
)

ANVIL_KEY_0 = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
ANVIL_ADDR_0 = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


def _fixture(signature_type: int) -> UnsignedOrder:
    return UnsignedOrder(
        builder=BYTES32_ZERO,
        chain_id=137,
        exchange_address=EXCHANGE,
        expiration=0,
        maker=DEPOSIT_WALLET,
        maker_amount=1_000_000,
        metadata=BYTES32_ZERO,
        order_type="GTC",
        salt=1,
        side="BUY",
        signature_type=signature_type,
        signer=DEPOSIT_WALLET,
        taker_amount=500_000,
        timestamp=0,
        token_id=TokenId("1"),
    )


def _digest(typed_data: dict[str, object]) -> str:
    from eth_utils.crypto import keccak

    signable = encode_typed_data(full_message=typed_data)
    return "0x" + keccak(b"\x19\x01" + signable.header + signable.body).hex()


def test_eip712_hash_matches_ts_for_eoa_fixture() -> None:
    typed_data = build_order_typed_data(_fixture(signature_type=0))
    assert _digest(typed_data) == (
        "0xa511aa6ff25ecfc36227717b080802396f686a8cf012fe38b4c30153b91be7a5"
    )


def test_eip712_hash_matches_ts_for_poly_proxy_fixture() -> None:
    typed_data = build_order_typed_data(_fixture(signature_type=1))
    assert _digest(typed_data) == (
        "0x6c1e2461f1aceb08efa25fbd99c6087f86ee7e67dab570dc7a0aad194bd9c653"
    )


def test_eip712_hash_matches_ts_for_poly_1271_envelope() -> None:
    typed_data = build_order_typed_data(_fixture(signature_type=3))
    assert _digest(typed_data) == (
        "0x1b9566eedd9589a73275df23a3a9d9e2e9897e76d31cd46d436f1b824d161b33"
    )


def test_sign_typed_data_recovers_to_signer_for_eoa() -> None:
    account = Account.from_key(ANVIL_KEY_0)
    typed_data = build_order_typed_data(_fixture(signature_type=0))
    signed = account.sign_typed_data(full_message=typed_data)
    recovered = Account.recover_message(
        encode_typed_data(full_message=typed_data), signature=signed.signature
    )
    assert recovered == ANVIL_ADDR_0


def test_sign_typed_data_recovers_to_signer_for_poly_1271_envelope() -> None:
    account = Account.from_key(ANVIL_KEY_0)
    typed_data = build_order_typed_data(_fixture(signature_type=3))
    signed = account.sign_typed_data(full_message=typed_data)
    recovered = Account.recover_message(
        encode_typed_data(full_message=typed_data), signature=signed.signature
    )
    assert recovered == ANVIL_ADDR_0


def test_eip712_hashes_remain_stable_across_invocations() -> None:
    typed_data = build_order_typed_data(_fixture(signature_type=0))
    hashes = {_digest(typed_data) for _ in range(5)}
    assert len(hashes) == 1


def test_build_order_signature_appends_exact_erc7739_trailer_bytes() -> None:
    order = _fixture(signature_type=3)
    wrapped = build_order_signature(order, EVM_SIGNATURE)

    # 0x prefix + 65-byte signature + 32-byte app domain separator
    #                                + 32-byte contents hash
    #                                + ORDER_TYPE_STRING bytes
    #                                + 2-byte uint16 length suffix
    body = wrapped[2:]
    sig_part = body[: 65 * 2]
    domain_sep = body[65 * 2 : 65 * 2 + 32 * 2]
    contents_hash = body[65 * 2 + 32 * 2 : 65 * 2 + 64 * 2]
    trailer = body[65 * 2 + 64 * 2 :]

    assert sig_part == EVM_SIGNATURE[2:]
    assert len(domain_sep) == 64
    assert len(contents_hash) == 64
    assert trailer.endswith("00ba")
    assert int(trailer[-4:], 16) == 186  # ORDER_TYPE_STRING length

    type_string = (
        "Order(uint256 salt,address maker,address signer,uint256 tokenId,"
        "uint256 makerAmount,uint256 takerAmount,uint8 side,uint8 signatureType,"
        "uint256 timestamp,bytes32 metadata,bytes32 builder)"
    )
    expected_type_hex = type_string.encode("utf-8").hex()
    assert trailer[:-4] == expected_type_hex
