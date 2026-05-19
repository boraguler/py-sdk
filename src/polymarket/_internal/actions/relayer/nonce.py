from __future__ import annotations

from polymarket.clients._transport import AsyncTransport
from polymarket.models.clob.relayer import RelayerExecuteParams, RelayerTransactionType


async def fetch_execute_params(
    relayer: AsyncTransport,
    *,
    address: str,
    type: RelayerTransactionType,
) -> RelayerExecuteParams:
    data = await relayer.get_json(
        "/v1/account/transactions/params",
        params={"address": address, "type": type.value},
    )
    return RelayerExecuteParams.parse_response(data)


__all__ = ["fetch_execute_params"]
