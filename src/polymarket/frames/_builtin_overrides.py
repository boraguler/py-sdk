"""Built-in Arrow overrides registered on ``polymarket.frames`` import."""

from __future__ import annotations

from typing import TYPE_CHECKING

from polymarket.frames._overrides import register_override
from polymarket.models import OrderBook

if TYPE_CHECKING:
    import pyarrow as pa


@register_override(OrderBook)
def _orderbook_to_arrow(value: object) -> pa.Table:  # pyright: ignore[reportUnusedFunction]
    from polymarket.frames._arrow import _build_table_from_rows

    assert isinstance(value, OrderBook)
    rows: list[dict[str, object]] = []
    for level_idx, lvl in enumerate(value.bids):
        rows.append({"side": "bid", "level": level_idx, "price": lvl.price, "size": lvl.size})
    for level_idx, lvl in enumerate(value.asks):
        rows.append({"side": "ask", "level": level_idx, "price": lvl.price, "size": lvl.size})
    return _build_table_from_rows(rows)
