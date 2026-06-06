from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data.audit_schema import audit_daily, event_time, validate_schema
from data.crypto_lake_loader import discover_files, load_snapshots
from utils.artifacts import artifact_namespace, namespaced_name, stage_namespace_slug, stage_table_path
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.io import write_frame, write_json, write_run_metadata
from utils.logging import configure_logging
from utils.partitioning import partitioned_stage_enabled, stage_partitions


def main() -> None:
    parser = common_parser("Audit dữ liệu L2 snapshot Crypto Lake.")
    args = as_common_args(parser.parse_args())
    config = load_config(args.config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/audit.log"))

    files = discover_files(config, args.stage, symbol=args.symbol, start=args.start, end=args.end)
    logger.info("Phát hiện %s parquet phù hợp stage %s.", len(files), args.stage)
    partition_mode = partitioned_stage_enabled(config, args.stage, start=args.start, end=args.end)
    audit_parts = []
    schema = None
    interval_samples = []
    spread_samples = []
    n_rows_loaded = 0
    if partition_mode:
        partitions = stage_partitions(config, args.stage)
        for partition in partitions:
            raw = load_snapshots(
                config,
                args.stage,
                symbol=args.symbol,
                start=str(partition.start),
                end=str(partition.end),
                include_source_file=True,
            )
            if raw.empty:
                logger.warning("Partition %s rỗng trong audit.", partition.token)
                continue
            schema = schema or validate_schema(raw.columns, levels=int(config.get("levels", 20)))
            n_rows_loaded += int(len(raw))
            logger.info("Audit partition %s với %s snapshot.", partition.token, len(raw))
            for source_file, group in raw.groupby("source_file", dropna=False):
                file_size = float(group["source_file_size_mb"].iloc[0]) if "source_file_size_mb" in group else 0.0
                audit_parts.append(audit_daily(group.drop(columns=["source_file", "source_file_size_mb"], errors="ignore"), file_size))
            interval_sample, spread_sample = _plot_samples(raw)
            interval_samples.append(interval_sample)
            spread_samples.append(spread_sample)
    else:
        raw = load_snapshots(
            config,
            args.stage,
            symbol=args.symbol,
            start=args.start,
            end=args.end,
            include_source_file=True,
        )
        if raw.empty:
            raise RuntimeError("Không đọc được snapshot nào cho stage audit.")
        schema = validate_schema(raw.columns, levels=int(config.get("levels", 20)))
        n_rows_loaded = int(len(raw))
        for source_file, group in raw.groupby("source_file", dropna=False):
            file_size = float(group["source_file_size_mb"].iloc[0]) if "source_file_size_mb" in group else 0.0
            audit_parts.append(audit_daily(group.drop(columns=["source_file", "source_file_size_mb"], errors="ignore"), file_size))
        interval_sample, spread_sample = _plot_samples(raw)
        interval_samples.append(interval_sample)
        spread_samples.append(spread_sample)

    if schema is None:
        raise RuntimeError("Không đọc được snapshot nào cho stage audit.")
    audit = pd.concat(audit_parts, ignore_index=True) if audit_parts else pd.DataFrame()

    namespace = artifact_namespace(config)
    stage_ns = stage_namespace_slug(args.stage, namespace)
    audit_name = namespaced_name("audit_by_day", namespace, suffix=".parquet")
    schema_name = namespaced_name("schema_audit", namespace, suffix=".json")
    table_name = namespaced_name("table_data_audit", namespace, suffix=".csv")
    audit_path = resolve_path(config, f"data/interim/audit/{audit_name}")
    table_path = resolve_path(config, f"outputs/tables/{table_name}")
    stage_audit_path = resolve_path(config, f"data/interim/audit/audit_by_day_{stage_ns}.parquet")
    stage_table_out = stage_table_path(resolve_path(config, "outputs/tables"), "table_data_audit", args.stage, namespace=namespace)
    figure_dir = resolve_path(config, str(config.get("figures_output", "outputs/figures")))
    figure_dir.mkdir(parents=True, exist_ok=True)
    write_frame(audit, audit_path)
    write_frame(audit, stage_audit_path)
    audit.to_csv(table_path, index=False)
    audit.to_csv(stage_table_out, index=False)
    write_json(schema, resolve_path(config, f"data/interim/audit/{schema_name}"))

    symbol = args.symbol or str((config.get("symbols") or ["BTC-USDT"])[0])
    interval_values = pd.concat(interval_samples, ignore_index=True) if interval_samples else pd.Series(dtype="float64")
    spread_values = pd.concat(spread_samples, ignore_index=True) if spread_samples else pd.Series(dtype="float64")
    _histogram(interval_values.dropna(), figure_dir / f"snapshot_interval_distribution_{symbol}.png", "Snapshot interval (ms)")
    _histogram(spread_values.dropna(), figure_dir / f"spread_distribution_{symbol}.png", "Spread")

    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "00_audit_data.py",
        artifacts={
            "audit_by_day": audit_path,
            "audit_table": table_path,
            "stage_audit_by_day": stage_audit_path,
            "stage_audit_table": stage_table_out,
            "schema_audit": resolve_path(config, f"data/interim/audit/{schema_name}"),
        },
        extra={"n_rows_loaded": n_rows_loaded, "schema_ok": bool(schema["ok"]), "partition_mode": partition_mode},
    )
    logger.info("Audit hoàn tất với %s dòng.", n_rows_loaded)


def _histogram(values: pd.Series, path: Path, xlabel: str) -> None:
    plt.figure(figsize=(7, 4))
    clipped = values.replace([float("inf"), float("-inf")], pd.NA).dropna()
    if not clipped.empty:
        plt.hist(clipped, bins=50)
    plt.xlabel(xlabel)
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def _plot_samples(raw: pd.DataFrame, max_rows: int = 250_000) -> tuple[pd.Series, pd.Series]:
    plot_frame = raw[["origin_time", "received_time", "ask_0_price", "bid_0_price"]].copy()
    plot_frame["event_time"] = event_time(plot_frame)
    plot_frame = plot_frame.sort_values("event_time")
    interval_ms = plot_frame["event_time"].diff().dt.total_seconds().mul(1000)
    spread = plot_frame["ask_0_price"] - plot_frame["bid_0_price"]
    if len(interval_ms) > max_rows:
        interval_ms = interval_ms.sample(n=max_rows, random_state=7)
    if len(spread) > max_rows:
        spread = spread.sample(n=max_rows, random_state=7)
    return interval_ms.reset_index(drop=True), spread.reset_index(drop=True)


if __name__ == "__main__":
    main()
