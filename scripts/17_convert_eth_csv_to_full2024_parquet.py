from __future__ import annotations

import argparse
import csv as py_csv
import json
import os
import platform
import re
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as arrow_csv
import pyarrow.parquet as pq

try:
    import polars as pl
except ImportError:  # pragma: no cover - Polars is optional fallback.
    pl = None


MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MONTH_RE = re.compile(r"^BOOK_(?P<exchange>[A-Z0-9]+)_(?P<symbol>[A-Z0-9\-]+)_(?P<month>[A-Z]{3})-2024\.csv$")


@dataclass(frozen=True)
class ConversionTask:
    month: str
    input_path: Path
    output_path: Path


def expected_columns(levels: int = 20) -> list[str]:
    columns = ["origin_time", "received_time", "sequence_number"]
    for side in ("bid", "ask"):
        for level in range(levels):
            columns.extend([f"{side}_{level}_price", f"{side}_{level}_size"])
    columns.extend(["symbol", "exchange"])
    return columns


def source_column_types(levels: int = 20) -> dict[str, pa.DataType]:
    types: dict[str, pa.DataType] = {
        "origin_time": pa.timestamp("ns"),
        "received_time": pa.timestamp("ns"),
        "sequence_number": pa.int64(),
        "symbol": pa.dictionary(pa.int32(), pa.string()),
        "exchange": pa.dictionary(pa.int32(), pa.string()),
    }
    for side in ("bid", "ask"):
        for level in range(levels):
            types[f"{side}_{level}_price"] = pa.float32()
            types[f"{side}_{level}_size"] = pa.float32()
    return types


def target_schema(levels: int = 20) -> pa.Schema:
    fields = [
        pa.field("origin_time", pa.timestamp("ns", tz="UTC")),
        pa.field("received_time", pa.timestamp("ns", tz="UTC")),
        pa.field("sequence_number", pa.int64()),
    ]
    for side in ("bid", "ask"):
        for level in range(levels):
            fields.append(pa.field(f"{side}_{level}_price", pa.float32()))
            fields.append(pa.field(f"{side}_{level}_size", pa.float32()))
    fields.extend(
        [
            pa.field("symbol", pa.dictionary(pa.int32(), pa.string())),
            pa.field("exchange", pa.dictionary(pa.int32(), pa.string())),
        ]
    )
    return pa.schema(fields)


def discover_input_files(input_root: Path, symbol: str, exchange: str, months: Iterable[str] | None = None) -> list[ConversionTask]:
    requested = list(months or MONTHS)
    invalid = sorted(set(requested) - set(MONTHS))
    if invalid:
        raise ValueError(f"Month token không hợp lệ: {invalid}. Chỉ nhận {MONTHS}.")

    tasks_by_month: dict[str, ConversionTask] = {}
    for path in sorted(input_root.glob("*.csv")):
        match = MONTH_RE.match(path.name)
        if not match:
            continue
        if match.group("symbol") != symbol or match.group("exchange") != exchange:
            continue
        month = match.group("month")
        tasks_by_month[month] = ConversionTask(month=month, input_path=path, output_path=Path())

    missing = [month for month in requested if month not in tasks_by_month]
    if missing:
        raise FileNotFoundError(f"Thiếu CSV ETH 2024 cho tháng: {missing}")
    return [tasks_by_month[month] for month in requested]


def attach_output_paths(tasks: list[ConversionTask], output_root: Path, symbol: str, exchange: str) -> list[ConversionTask]:
    return [
        ConversionTask(
            month=task.month,
            input_path=task.input_path,
            output_path=output_root / f"BOOK_{exchange}_{symbol}_{task.month}-2024.parquet",
        )
        for task in tasks
    ]


def read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = py_csv.reader(handle)
        return next(reader)


def validate_headers(tasks: list[ConversionTask], levels: int) -> None:
    expected = expected_columns(levels)
    failures = []
    for task in tasks:
        header = read_header(task.input_path)
        if header != expected:
            missing = sorted(set(expected) - set(header))
            extra = sorted(set(header) - set(expected))
            failures.append({"file": str(task.input_path), "missing": missing, "extra": extra})
    if failures:
        raise ValueError(f"Header CSV không khớp schema full2024: {failures}")


def check_disk_space(output_root: Path, min_free_gb: float) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    free_gb = shutil.disk_usage(output_root).free / (1024**3)
    if free_gb < min_free_gb:
        raise RuntimeError(f"Free disk chỉ còn {free_gb:.2f} GB, thấp hơn gate {min_free_gb:.2f} GB.")


def read_csv_table_pyarrow(task: ConversionTask, levels: int, max_rows: int | None, block_size_mb: int) -> pa.Table:
    read_options = arrow_csv.ReadOptions(use_threads=True, block_size=block_size_mb * 1024 * 1024)
    convert_options = arrow_csv.ConvertOptions(column_types=source_column_types(levels))

    if max_rows is None:
        table = arrow_csv.read_csv(task.input_path, read_options=read_options, convert_options=convert_options)
        return prepare_table(table, levels)

    reader = arrow_csv.open_csv(task.input_path, read_options=read_options, convert_options=convert_options)
    batches = []
    rows_remaining = max_rows
    while rows_remaining > 0:
        try:
            batch = reader.read_next_batch()
        except StopIteration:
            break
        if batch.num_rows > rows_remaining:
            batch = batch.slice(0, rows_remaining)
        batches.append(batch)
        rows_remaining -= batch.num_rows
    if not batches:
        return pa.Table.from_arrays([pa.array([], type=field.type) for field in target_schema(levels)], schema=target_schema(levels))
    table = pa.Table.from_batches(batches)
    return prepare_table(table, levels)


def prepare_table(table: pa.Table, levels: int) -> pa.Table:
    expected = expected_columns(levels)
    missing = sorted(set(expected) - set(table.column_names))
    if missing:
        raise ValueError(f"CSV thiếu cột bắt buộc: {missing}")
    selected = table.select(expected)
    # CSV timestamps are timezone-naive strings. Casting annotates them as UTC
    # without needing a local tzdata database, matching BTC full2024 parquet.
    return selected.cast(target_schema(levels))


def is_monotonic_table(table: pa.Table) -> bool:
    if table.num_rows <= 1:
        return True
    keys = table.select(["origin_time", "received_time", "sequence_number"]).to_pandas()
    origin = keys["origin_time"]
    received = keys["received_time"]
    sequence = keys["sequence_number"]
    prev_origin = origin.shift(1)
    prev_received = received.shift(1)
    prev_sequence = sequence.shift(1)
    ordered = (
        origin.gt(prev_origin)
        | (origin.eq(prev_origin) & received.gt(prev_received))
        | (origin.eq(prev_origin) & received.eq(prev_received) & sequence.ge(prev_sequence))
    )
    return bool(ordered.iloc[1:].all())


def sort_table(table: pa.Table) -> pa.Table:
    indices = pc.sort_indices(
        table,
        sort_keys=[
            ("origin_time", "ascending"),
            ("received_time", "ascending"),
            ("sequence_number", "ascending"),
        ],
    )
    return pc.take(table, indices)


def write_pyarrow_table(table: pa.Table, temp_path: Path, row_group_size: int) -> None:
    pq.write_table(
        table,
        temp_path,
        row_group_size=row_group_size,
        compression="snappy",
        use_dictionary=["symbol", "exchange"],
        write_statistics=True,
    )


def convert_polars_streaming(task: ConversionTask, temp_path: Path, levels: int, max_rows: int | None, row_group_size: int) -> int:
    if pl is None:
        raise RuntimeError("Polars chưa được cài, không thể dùng fallback streaming.")
    schema_overrides: dict[str, object] = {
        "origin_time": pl.Datetime("ns"),
        "received_time": pl.Datetime("ns"),
        "sequence_number": pl.Int64,
        "symbol": pl.Categorical,
        "exchange": pl.Categorical,
    }
    for side in ("bid", "ask"):
        for level in range(levels):
            schema_overrides[f"{side}_{level}_price"] = pl.Float32
            schema_overrides[f"{side}_{level}_size"] = pl.Float32

    lazy = pl.scan_csv(str(task.input_path), schema_overrides=schema_overrides, try_parse_dates=True).select(
        expected_columns(levels)
    )
    if max_rows is not None:
        lazy = lazy.head(max_rows)
    lazy = lazy.with_columns(
        [
            pl.col("origin_time").dt.replace_time_zone("UTC"),
            pl.col("received_time").dt.replace_time_zone("UTC"),
        ]
    )
    lazy.sink_parquet(str(temp_path), compression="snappy", row_group_size=row_group_size)
    return int(pq.ParquetFile(temp_path).metadata.num_rows)


def table_sample(table: pa.Table, sample_rows: int) -> pd.DataFrame:
    if table.num_rows <= sample_rows * 2:
        return table.to_pandas()
    head = table.slice(0, sample_rows)
    tail = table.slice(table.num_rows - sample_rows, sample_rows)
    return pa.concat_tables([head, tail]).to_pandas()


def parquet_sample(path: Path, sample_rows: int) -> pd.DataFrame:
    parquet = pq.ParquetFile(path)
    if parquet.metadata.num_rows <= sample_rows * 2:
        return parquet.read().to_pandas()
    head = parquet.read_row_group(0).slice(0, sample_rows)
    tail_group = parquet.read_row_group(parquet.num_row_groups - 1)
    tail = tail_group.slice(max(0, tail_group.num_rows - sample_rows), sample_rows)
    return pa.concat_tables([head, tail]).to_pandas()


def compare_samples(expected: pd.DataFrame, actual: pd.DataFrame, levels: int) -> str:
    if len(expected) != len(actual):
        return f"FAIL:length {len(expected)} != {len(actual)}"
    for column in expected_columns(levels):
        left = expected[column]
        right = actual[column]
        if column.endswith("_price") or column.endswith("_size"):
            if not np.allclose(left.to_numpy(dtype="float64"), right.to_numpy(dtype="float64"), rtol=1e-5, atol=1e-6):
                return f"FAIL:float mismatch {column}"
        else:
            if not left.astype(str).reset_index(drop=True).equals(right.astype(str).reset_index(drop=True)):
                return f"FAIL:value mismatch {column}"
    return "PASS"


def validate_parquet(
    path: Path,
    *,
    expected_rows: int | None,
    expected_sample: pd.DataFrame | None,
    levels: int,
    symbol: str,
    exchange: str,
    sample_rows: int,
) -> dict[str, object]:
    parquet = pq.ParquetFile(path)
    schema_status = "PASS" if parquet.schema_arrow.equals(target_schema(levels), check_metadata=False) else "FAIL"
    row_count = int(parquet.metadata.num_rows)
    row_count_status = "PASS" if expected_rows is None or row_count == expected_rows else "FAIL"
    actual_sample = parquet_sample(path, sample_rows)
    symbol_status = "PASS" if set(actual_sample["symbol"].astype(str).unique()) == {symbol} else "FAIL"
    exchange_status = "PASS" if set(actual_sample["exchange"].astype(str).unique()) == {exchange} else "FAIL"
    sample_status = compare_samples(expected_sample, actual_sample, levels) if expected_sample is not None else "SKIP"
    return {
        "schema_status": schema_status,
        "row_count_status": row_count_status,
        "symbol_status": symbol_status,
        "exchange_status": exchange_status,
        "sample_status": sample_status,
        "n_rows": row_count,
    }


def convert_month(
    task: ConversionTask,
    *,
    engine: str,
    overwrite: bool,
    levels: int,
    max_rows: int | None,
    row_group_size: int,
    block_size_mb: int,
    sample_rows: int,
    symbol: str,
    exchange: str,
) -> dict[str, object]:
    started = time.perf_counter()
    input_size_mb = task.input_path.stat().st_size / (1024 * 1024)
    record: dict[str, object] = {
        "month": task.month,
        "input_path": str(task.input_path),
        "output_path": str(task.output_path),
        "engine_requested": engine,
        "engine_used": None,
        "status": None,
        "n_rows": 0,
        "input_size_mb": round(input_size_mb, 4),
        "output_size_mb": 0.0,
        "duration_sec": 0.0,
        "throughput_input_mb_sec": 0.0,
        "worker_thread": threading.get_ident(),
        "monotonic_before_write": None,
        "sorted_applied": False,
        "schema_status": None,
        "row_count_status": None,
        "symbol_status": None,
        "exchange_status": None,
        "sample_status": None,
        "error": "",
    }

    if task.output_path.exists() and not overwrite:
        record["status"] = "skipped_existing"
        record["n_rows"] = int(pq.ParquetFile(task.output_path).metadata.num_rows)
        record["output_size_mb"] = round(task.output_path.stat().st_size / (1024 * 1024), 4)
        record["duration_sec"] = round(time.perf_counter() - started, 4)
        return record

    task.output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = task.output_path.with_suffix(task.output_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()

    expected_sample: pd.DataFrame | None = None
    expected_rows: int | None = None
    engine_used = engine
    try:
        if engine not in {"pyarrow", "polars"}:
            raise ValueError("--engine chỉ nhận pyarrow hoặc polars.")
        if engine == "pyarrow":
            table = read_csv_table_pyarrow(task, levels, max_rows, block_size_mb)
            expected_rows = int(table.num_rows)
            monotonic = is_monotonic_table(table)
            record["monotonic_before_write"] = monotonic
            if not monotonic:
                table = sort_table(table)
                record["sorted_applied"] = True
            expected_sample = table_sample(table, sample_rows)
            write_pyarrow_table(table, temp_path, row_group_size)
            del table
        else:
            expected_rows = convert_polars_streaming(task, temp_path, levels, max_rows, row_group_size)
            engine_used = "polars"

        validation = validate_parquet(
            temp_path,
            expected_rows=expected_rows,
            expected_sample=expected_sample,
            levels=levels,
            symbol=symbol,
            exchange=exchange,
            sample_rows=sample_rows,
        )
        record.update(validation)
        failed_checks = [
            key
            for key in ("schema_status", "row_count_status", "symbol_status", "exchange_status", "sample_status")
            if str(record.get(key)).startswith("FAIL")
        ]
        if failed_checks:
            raise RuntimeError(f"Validation fail: {failed_checks}")
        if task.output_path.exists():
            task.output_path.unlink()
        temp_path.replace(task.output_path)
        record["status"] = "converted"
        record["engine_used"] = engine_used
        record["output_size_mb"] = round(task.output_path.stat().st_size / (1024 * 1024), 4)
    except MemoryError as exc:
        if engine == "pyarrow":
            temp_path.unlink(missing_ok=True)
            record["engine_requested"] = engine
            try:
                expected_rows = convert_polars_streaming(task, temp_path, levels, max_rows, row_group_size)
                validation = validate_parquet(
                    temp_path,
                    expected_rows=expected_rows,
                    expected_sample=None,
                    levels=levels,
                    symbol=symbol,
                    exchange=exchange,
                    sample_rows=sample_rows,
                )
                record.update(validation)
                if any(str(record.get(key)).startswith("FAIL") for key in ("schema_status", "row_count_status", "symbol_status", "exchange_status")):
                    raise RuntimeError("Validation fail trong Polars fallback.")
                if task.output_path.exists():
                    task.output_path.unlink()
                temp_path.replace(task.output_path)
                record["status"] = "converted"
                record["engine_used"] = "polars_fallback"
                record["output_size_mb"] = round(task.output_path.stat().st_size / (1024 * 1024), 4)
            except Exception as fallback_exc:  # noqa: BLE001
                temp_path.unlink(missing_ok=True)
                record["status"] = "failed"
                record["error"] = f"PyArrow MemoryError: {exc}; Polars fallback error: {fallback_exc}"
        else:
            temp_path.unlink(missing_ok=True)
            record["status"] = "failed"
            record["error"] = str(exc)
    except Exception as exc:  # noqa: BLE001
        temp_path.unlink(missing_ok=True)
        record["status"] = "failed"
        record["engine_used"] = engine_used
        record["error"] = str(exc)
    finally:
        duration = time.perf_counter() - started
        record["duration_sec"] = round(duration, 4)
        record["throughput_input_mb_sec"] = round(input_size_mb / duration, 4) if duration > 0 else 0.0
    return record


def write_outputs(records: list[dict[str, object]], args: argparse.Namespace) -> None:
    table_path = Path(args.table_output)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame.from_records(records).to_csv(table_path, index=False)

    metadata_path = Path("CryptoRegimeShift") / "outputs" / "logs" / args.run_id / "metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": args.run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_name": "17_convert_eth_csv_to_full2024_parquet.py",
        "args": vars(args),
        "platform": platform.platform(),
        "python": sys.version,
        "pyarrow": pa.__version__,
        "polars": getattr(pl, "__version__", None) if pl is not None else None,
        "cpu_count": os.cpu_count(),
        "summary": summarize(records),
        "artifacts": {
            "conversion_table": str(table_path),
            "audit": str(args.audit_output),
        },
    }
    metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    audit_path = Path(args.audit_output)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(render_audit(records, args), encoding="utf-8")


def summarize(records: list[dict[str, object]]) -> dict[str, object]:
    converted = [row for row in records if row.get("status") == "converted"]
    failed = [row for row in records if row.get("status") == "failed"]
    skipped = [row for row in records if row.get("status") == "skipped_existing"]
    return {
        "n_records": len(records),
        "n_converted": len(converted),
        "n_failed": len(failed),
        "n_skipped_existing": len(skipped),
        "total_rows_converted": int(sum(int(row.get("n_rows") or 0) for row in converted)),
        "total_output_size_mb": round(sum(float(row.get("output_size_mb") or 0.0) for row in records), 4),
        "decision": "PASS" if not failed else "FAIL",
    }


def render_audit(records: list[dict[str, object]], args: argparse.Namespace) -> str:
    summary = summarize(records)
    lines = [
        "# Audit convert ETH CSV sang parquet full2024",
        "",
        f"- `run_id`: `{args.run_id}`",
        "- Mục tiêu: chuyển CSV ETH-USDT 2024 sang raw parquet tương thích `data/full2024` để mở khóa asset-held-out.",
        f"- Engine yêu cầu: `{args.engine}`",
        f"- Workers: `{args.workers}`",
        f"- Max rows: `{args.max_rows}`",
        f"- Quyết định: `{summary['decision']}`",
        "",
        "## Tóm tắt",
        "",
        f"- Số tháng xử lý: `{summary['n_records']}`",
        f"- Converted: `{summary['n_converted']}`",
        f"- Skipped existing: `{summary['n_skipped_existing']}`",
        f"- Failed: `{summary['n_failed']}`",
        f"- Tổng rows converted: `{summary['total_rows_converted']}`",
        f"- Tổng output size MB: `{summary['total_output_size_mb']}`",
        "",
        "## Kết quả theo tháng",
        "",
        "| Month | Status | Rows | Engine | Duration sec | MB/s | Checks | Error |",
        "|---|---:|---:|---|---:|---:|---|---|",
    ]
    for row in records:
        checks = ",".join(
            str(row.get(key))
            for key in ("schema_status", "row_count_status", "symbol_status", "exchange_status", "sample_status")
            if row.get(key)
        )
        lines.append(
            f"| `{row.get('month')}` | `{row.get('status')}` | `{row.get('n_rows')}` | `{row.get('engine_used')}` | "
            f"`{row.get('duration_sec')}` | `{row.get('throughput_input_mb_sec')}` | `{checks}` | `{row.get('error') or ''}` |"
        )
    lines.extend(
        [
            "",
            "## Đánh giá ICDM/reproducibility",
            "",
            "- Converter không thay đổi BTC parquet hiện có.",
            "- Output giữ schema raw snapshot-level L2, chưa build feature/label/regime ETH trong bước này.",
            "- GPU không dùng ở bước này vì conversion CSV -> Parquet là CPU/disk-bound trên Windows; RTX 3090 dành cho model training/inference sau khi ETH parquet sẵn sàng.",
            "",
            "## Bước tiếp theo",
            "",
            "- Nếu `PASS`: chạy audit dữ liệu ETH ở stage nhỏ trước khi mở feature/label/regime full-year.",
            "- Nếu `FAIL`: sửa lỗi schema/data theo tháng thất bại, không mở asset-held-out cho tới khi đủ 12 parquet hợp lệ.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert ETH CSV full-year 2024 sang parquet tương thích data/full2024.")
    parser.add_argument("--input-root", default="data/eth")
    parser.add_argument("--output-root", default="data/full2024")
    parser.add_argument("--symbol", default="ETH-USDT")
    parser.add_argument("--exchange", default="BINANCE")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--engine", choices=["pyarrow", "polars"], default="pyarrow")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--months", nargs="*", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--levels", type=int, default=20)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--row-group-size", type=int, default=1_000_000)
    parser.add_argument("--block-size-mb", type=int, default=16)
    parser.add_argument("--sample-rows", type=int, default=1000)
    parser.add_argument("--min-free-gb", type=float, default=60.0)
    parser.add_argument("--arrow-threads", type=int, default=0)
    parser.add_argument("--table-output", default="CryptoRegimeShift/outputs/tables/table_eth_csv_to_parquet_conversion.csv")
    parser.add_argument("--audit-output", default="CryptoRegimeShift/audits/audit_stage_eth_full2024_conversion_v001.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers phải >= 1.")
    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    check_disk_space(output_root, args.min_free_gb)
    tasks = discover_input_files(input_root, args.symbol, args.exchange, args.months)
    tasks = attach_output_paths(tasks, output_root, args.symbol, args.exchange)
    validate_headers(tasks, args.levels)

    arrow_threads = args.arrow_threads or max(1, (os.cpu_count() or 1) // max(args.workers, 1))
    pa.set_cpu_count(arrow_threads)
    pa.set_io_thread_count(arrow_threads)

    records: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                convert_month,
                task,
                engine=args.engine,
                overwrite=args.overwrite,
                levels=args.levels,
                max_rows=args.max_rows,
                row_group_size=args.row_group_size,
                block_size_mb=args.block_size_mb,
                sample_rows=args.sample_rows,
                symbol=args.symbol,
                exchange=args.exchange,
            ): task
            for task in tasks
        }
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            print(
                f"[{record['month']}] status={record['status']} rows={record['n_rows']} "
                f"engine={record['engine_used']} duration={record['duration_sec']}s"
            )
    records.sort(key=lambda row: MONTHS.index(str(row["month"])))
    write_outputs(records, args)
    if summarize(records)["decision"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
