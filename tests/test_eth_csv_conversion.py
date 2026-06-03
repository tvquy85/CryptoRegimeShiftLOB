from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


def _load_converter():
    script = Path(__file__).resolve().parents[1] / "scripts" / "17_convert_eth_csv_to_full2024_parquet.py"
    spec = importlib.util.spec_from_file_location("eth_csv_converter", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rows(symbol: str = "ETH-USDT") -> list[dict[str, object]]:
    rows = []
    for i in range(3):
        row: dict[str, object] = {
            "origin_time": f"2024-01-01 00:00:0{i}.000000000",
            "received_time": f"2024-01-01 00:00:0{i}.100000000",
            "sequence_number": 100 + i,
        }
        for side, base in [("bid", 100.0), ("ask", 100.2)]:
            for level in range(20):
                price = base - level * 0.01 if side == "bid" else base + level * 0.01
                row[f"{side}_{level}_price"] = price + i * 0.001
                row[f"{side}_{level}_size"] = 1.0 + level + i
        row["symbol"] = symbol
        row["exchange"] = "BINANCE"
        rows.append(row)
    return rows


def _write_csv(path: Path, symbol: str = "ETH-USDT") -> None:
    converter = _load_converter()
    frame = pd.DataFrame(_rows(symbol=symbol), columns=converter.expected_columns())
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def test_convert_synthetic_csv_to_full2024_schema(tmp_path: Path) -> None:
    converter = _load_converter()
    csv_path = tmp_path / "BOOK_BINANCE_ETH-USDT_JAN-2024.csv"
    output_path = tmp_path / "out" / "BOOK_BINANCE_ETH-USDT_JAN-2024.parquet"
    _write_csv(csv_path)

    record = converter.convert_month(
        converter.ConversionTask("JAN", csv_path, output_path),
        engine="pyarrow",
        overwrite=False,
        levels=20,
        max_rows=None,
        row_group_size=2,
        block_size_mb=1,
        sample_rows=1,
        symbol="ETH-USDT",
        exchange="BINANCE",
    )

    assert record["status"] == "converted"
    assert record["schema_status"] == "PASS"
    assert record["row_count_status"] == "PASS"
    assert record["symbol_status"] == "PASS"
    assert record["exchange_status"] == "PASS"
    assert record["sample_status"] == "PASS"
    assert pq.ParquetFile(output_path).schema_arrow.equals(converter.target_schema(), check_metadata=False)
    dtypes = pd.read_parquet(output_path).dtypes
    assert str(dtypes["origin_time"]) == "datetime64[ns, UTC]"
    assert str(dtypes["bid_0_price"]) == "float32"


def test_discover_ignores_out_of_year_file_and_rejects_bad_month(tmp_path: Path) -> None:
    converter = _load_converter()
    _write_csv(tmp_path / "BOOK_BINANCE_ETH-USDT_JAN-2024.csv")
    _write_csv(tmp_path / "ETH-USDT-BOOK-2023-12-31.csv")

    tasks = converter.discover_input_files(tmp_path, "ETH-USDT", "BINANCE", months=["JAN"])
    assert [task.month for task in tasks] == ["JAN"]

    try:
        converter.discover_input_files(tmp_path, "ETH-USDT", "BINANCE", months=["BAD"])
    except ValueError as exc:
        assert "Month token" in str(exc)
    else:
        raise AssertionError("Bad month token phải bị từ chối.")


def test_no_overwrite_skips_existing_output(tmp_path: Path) -> None:
    converter = _load_converter()
    csv_path = tmp_path / "BOOK_BINANCE_ETH-USDT_JAN-2024.csv"
    output_path = tmp_path / "BOOK_BINANCE_ETH-USDT_JAN-2024.parquet"
    _write_csv(csv_path)
    frame = pd.DataFrame(_rows(), columns=converter.expected_columns())
    frame["origin_time"] = pd.to_datetime(frame["origin_time"], utc=True)
    frame["received_time"] = pd.to_datetime(frame["received_time"], utc=True)
    frame.to_parquet(output_path, index=False)
    before_mtime = output_path.stat().st_mtime_ns

    record = converter.convert_month(
        converter.ConversionTask("JAN", csv_path, output_path),
        engine="pyarrow",
        overwrite=False,
        levels=20,
        max_rows=None,
        row_group_size=2,
        block_size_mb=1,
        sample_rows=1,
        symbol="ETH-USDT",
        exchange="BINANCE",
    )

    assert record["status"] == "skipped_existing"
    assert output_path.stat().st_mtime_ns == before_mtime


def test_failed_validation_does_not_publish_parquet(tmp_path: Path) -> None:
    converter = _load_converter()
    csv_path = tmp_path / "BOOK_BINANCE_ETH-USDT_JAN-2024.csv"
    output_path = tmp_path / "BOOK_BINANCE_ETH-USDT_JAN-2024.parquet"
    _write_csv(csv_path, symbol="BTC-USDT")

    record = converter.convert_month(
        converter.ConversionTask("JAN", csv_path, output_path),
        engine="pyarrow",
        overwrite=False,
        levels=20,
        max_rows=None,
        row_group_size=2,
        block_size_mb=1,
        sample_rows=1,
        symbol="ETH-USDT",
        exchange="BINANCE",
    )

    assert record["status"] == "failed"
    assert not output_path.exists()
    assert not output_path.with_suffix(output_path.suffix + ".tmp").exists()
