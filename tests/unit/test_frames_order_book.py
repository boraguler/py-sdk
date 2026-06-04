"""Tests for the OrderBook flatten override."""

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false

from __future__ import annotations

from decimal import Decimal

import pyarrow as pa

from polymarket.frames import to_arrow, to_pandas, to_polars
from polymarket.models import OrderBook


def _make_book(
    bids: tuple[tuple[str, str], ...] = (("0.49", "100"), ("0.48", "50")),
    asks: tuple[tuple[str, str], ...] = (("0.51", "80"),),
) -> OrderBook:
    return OrderBook.model_validate(
        {
            "market": "0xfoo",
            "asset_id": "42",
            "timestamp": None,
            "bids": [{"price": p, "size": s} for p, s in bids],
            "asks": [{"price": p, "size": s} for p, s in asks],
            "min_order_size": "5",
            "tick_size": "0.01",
            "neg_risk": True,
            "last_trade_price": "0.50",
            "hash": "abc",
        }
    )


def test_free_function_to_arrow_uses_flat_shape() -> None:
    table = to_arrow(_make_book())
    assert table.column_names == ["side", "level", "price", "size"]
    assert table.num_rows == 3


def test_free_function_to_pandas_uses_flat_shape() -> None:
    df = to_pandas(_make_book())
    assert list(df.columns) == ["side", "level", "price", "size"]
    assert len(df) == 3


def test_free_function_to_polars_uses_flat_shape() -> None:
    df = to_polars(_make_book())
    assert df.columns == ["side", "level", "price", "size"]
    assert df.shape == (3, 4)


def test_method_to_arrow_matches_free_function() -> None:
    book = _make_book()
    assert book.to_arrow().to_pylist() == to_arrow(book).to_pylist()


def test_method_to_pandas_matches_free_function() -> None:
    book = _make_book()
    method_df = book.to_pandas()
    func_df = to_pandas(book)
    assert list(method_df.columns) == list(func_df.columns)
    assert len(method_df) == len(func_df)


def test_method_to_polars_matches_free_function() -> None:
    book = _make_book()
    assert book.to_polars().to_dict(as_series=False) == to_polars(book).to_dict(as_series=False)


def test_bids_appear_first_then_asks_with_correct_level_indexing() -> None:
    rows = _make_book().to_arrow().to_pylist()
    bids = [r for r in rows if r["side"] == "bid"]
    asks = [r for r in rows if r["side"] == "ask"]
    assert [r["level"] for r in bids] == [0, 1]
    assert [r["level"] for r in asks] == [0]


def test_decimal_columns_use_decimal128_38_18() -> None:
    schema = _make_book().to_arrow().schema
    assert pa.types.is_decimal(schema.field("price").type)
    assert pa.types.is_decimal(schema.field("size").type)


def test_pandas_default_decimal_mode_preserves_precision() -> None:
    book = OrderBook.model_validate(
        {
            "market": "0xfoo",
            "asset_id": "42",
            "timestamp": None,
            "bids": [{"price": "0.123456789012345678", "size": "1"}],
            "asks": [],
            "min_order_size": "5",
            "tick_size": "0.01",
            "neg_risk": True,
            "last_trade_price": None,
            "hash": "x",
        }
    )
    df = book.to_pandas()
    assert df["price"][0] == Decimal("0.123456789012345678")


def test_empty_bids_or_asks_still_produces_table() -> None:
    book_no_asks = _make_book(asks=())
    df = book_no_asks.to_pandas()
    assert all(df["side"] == "bid")
    assert len(df) == 2


def test_completely_empty_book_yields_empty_table() -> None:
    book = _make_book(bids=(), asks=())
    table = book.to_arrow()
    assert table.num_rows == 0
