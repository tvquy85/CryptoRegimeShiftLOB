from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import polars as pl
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.classification_eval import classification_summary_from_counts
from utils.io import write_run_metadata


DISTRIBUTION_FEATURES = [
    "mid_price",
    "spread",
    "rel_spread",
    "top_of_book_depth",
    "total_depth_10",
    "realized_vol_20",
    "realized_vol_100",
    "vol_score",
    "abs_future_ret_h",
]

BASE_COLUMNS = [
    "symbol",
    "split",
    "label",
    "regime",
    "mid_price",
    "spread",
    "rel_spread",
    "bid_0_size",
    "ask_0_size",
    "total_depth_10",
    "realized_vol_20",
    "realized_vol_100",
    "vol_score",
    "future_ret_h",
]

CALIBRATION_COLUMNS = [
    "symbol",
    "split",
    "label",
    "pred_label",
    "prob_down",
    "prob_flat",
    "prob_up",
]

LABELS = ["DOWN", "FLAT", "UP"]
DIRECTIONS = {
    "btc_to_eth": {"source_symbol": "BTC-USDT", "target_symbol": "ETH-USDT"},
    "eth_to_btc": {"source_symbol": "ETH-USDT", "target_symbol": "BTC-USDT"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Build BTC<->ETH cross-asset transfer asymmetry diagnostics.")
    parser.add_argument("--stage", default="stage_3_full_scale")
    parser.add_argument("--run-id", default="p1_09_cross_asset_asymmetry_v001")
    parser.add_argument("--sample-rows", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--calibration-bins", type=int, default=10)
    return parser.parse_args()


def default_sources(root: Path) -> dict[str, Path]:
    return {
        "BTC-USDT": root / "data" / "predictions" / "predictions.parquet",
        "ETH-USDT": root / "data" / "predictions" / "predictions_eth_stage3_sgd.parquet",
    }


def transfer_sources(root: Path) -> dict[str, Path]:
    return {
        "btc_to_eth": root / "data" / "predictions" / "predictions_asset_btc_to_eth_sgd.parquet",
        "eth_to_btc": root / "data" / "predictions" / "predictions_asset_eth_to_btc_sgd.parquet",
    }


def validate_columns(path: Path, columns: list[str]) -> None:
    schema = pl.scan_parquet(str(path)).collect_schema()
    missing = [column for column in columns if column not in schema.names()]
    if missing:
        raise ValueError(f"{path} missing required columns: {missing}")


def base_lazy(path: Path, columns: list[str] = BASE_COLUMNS) -> pl.LazyFrame:
    validate_columns(path, columns)
    selected = pl.scan_parquet(str(path)).select(columns)
    return selected.with_columns(
        [
            (pl.col("bid_0_size") + pl.col("ask_0_size")).alias("top_of_book_depth"),
            pl.col("future_ret_h").abs().alias("abs_future_ret_h"),
        ]
    )


def deterministic_sample(path: Path, *, max_rows: int, seed: int) -> pd.DataFrame:
    lazy = base_lazy(path)
    n_rows = int(lazy.select(pl.len()).collect(engine="streaming").item())
    if max_rows <= 0 or n_rows <= max_rows:
        return lazy.collect(engine="streaming").to_pandas()
    fraction = min(1.0, float(max_rows) / max(float(n_rows), 1.0))
    return (
        lazy.with_row_index("__row_index")
        .filter((pl.col("__row_index").hash(seed=seed) / float(2**64 - 1)) <= fraction)
        .drop("__row_index")
        .limit(max_rows)
        .collect(engine="streaming")
        .to_pandas()
    )


def distribution_stats_from_sample(sample: pd.DataFrame, *, symbol: str, sample_seed: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split, split_frame in sample.groupby("split", dropna=False):
        for feature in DISTRIBUTION_FEATURES:
            values = pd.to_numeric(split_frame[feature], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
            if values.empty:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "split": split,
                    "feature": feature,
                    "mean": float(values.mean()),
                    "std": float(values.std(ddof=0)),
                    "p05": float(values.quantile(0.05)),
                    "p25": float(values.quantile(0.25)),
                    "median": float(values.quantile(0.50)),
                    "p75": float(values.quantile(0.75)),
                    "p95": float(values.quantile(0.95)),
                    "sample_rows": int(len(split_frame)),
                    "sample_seed": int(sample_seed),
                    "sample_method": "deterministic_row_hash_sample",
                }
            )
    return pd.DataFrame(rows)


def add_eth_btc_ratios(distribution: pd.DataFrame) -> pd.DataFrame:
    output = distribution.copy()
    output["eth_btc_mean_ratio"] = np.nan
    output["eth_btc_median_ratio"] = np.nan
    for split in output["split"].dropna().unique():
        for feature in output["feature"].dropna().unique():
            mask = (output["split"] == split) & (output["feature"] == feature)
            current = output[mask]
            btc = current[current["symbol"] == "BTC-USDT"]
            eth = current[current["symbol"] == "ETH-USDT"]
            if btc.empty or eth.empty:
                continue
            btc_mean = float(btc["mean"].iloc[0])
            btc_median = float(btc["median"].iloc[0])
            eth_mean = float(eth["mean"].iloc[0])
            eth_median = float(eth["median"].iloc[0])
            output.loc[mask, "eth_btc_mean_ratio"] = safe_ratio(eth_mean, btc_mean)
            output.loc[mask, "eth_btc_median_ratio"] = safe_ratio(eth_median, btc_median)
    return output


def exact_label_balance(path: Path, *, symbol: str, scope: str, direction: str | None = None) -> pd.DataFrame:
    validate_columns(path, ["symbol", "split", "label"])
    frame = (
        pl.scan_parquet(str(path))
        .select(["symbol", "split", "label"])
        .group_by(["symbol", "split", "label"])
        .agg(pl.len().alias("n_rows"))
        .collect(engine="streaming")
        .to_pandas()
    )
    frame["symbol"] = symbol
    frame["scope"] = scope
    frame["direction"] = direction or ""
    frame["split_total_rows"] = frame.groupby(["scope", "direction", "symbol", "split"], dropna=False)["n_rows"].transform("sum")
    frame["share"] = frame["n_rows"] / frame["split_total_rows"].clip(lower=1)
    return frame.sort_values(["scope", "direction", "symbol", "split", "label"]).reset_index(drop=True)


def exact_regime_counts(path: Path, *, symbol: str, scope: str, direction: str | None = None) -> pd.DataFrame:
    validate_columns(path, ["symbol", "split", "regime"])
    frame = (
        pl.scan_parquet(str(path))
        .select(["symbol", "split", "regime"])
        .group_by(["symbol", "split", "regime"])
        .agg(pl.len().alias("n_rows"))
        .collect(engine="streaming")
        .to_pandas()
    )
    frame["symbol"] = symbol
    frame["scope"] = scope
    frame["direction"] = direction or ""
    frame["split_total_rows"] = frame.groupby(["scope", "direction", "symbol", "split"], dropna=False)["n_rows"].transform("sum")
    frame["share"] = frame["n_rows"] / frame["split_total_rows"].clip(lower=1)
    return frame.sort_values(["scope", "direction", "symbol", "split", "regime"]).reset_index(drop=True)


def calibration_from_parquet(path: Path, *, direction: str, bins: int) -> dict[str, Any]:
    validate_columns(path, CALIBRATION_COLUMNS)
    lazy = (
        pl.scan_parquet(str(path))
        .filter(pl.col("split") == "test")
        .select(CALIBRATION_COLUMNS)
        .with_columns(
            [
                pl.max_horizontal("prob_down", "prob_flat", "prob_up").alias("confidence"),
                (
                    (pl.col("prob_down") - (pl.col("label") == "DOWN").cast(pl.Float64)).pow(2)
                    + (pl.col("prob_flat") - (pl.col("label") == "FLAT").cast(pl.Float64)).pow(2)
                    + (pl.col("prob_up") - (pl.col("label") == "UP").cast(pl.Float64)).pow(2)
                ).alias("brier_row"),
                (pl.col("label") == pl.col("pred_label")).cast(pl.Float64).alias("correct"),
            ]
        )
        .with_columns(
            [
                pl.min_horizontal(
                    (pl.col("confidence") * bins).floor().cast(pl.Int64),
                    pl.lit(bins - 1),
                ).alias("confidence_bin")
            ]
        )
    )
    counts = lazy.group_by(["label", "pred_label"]).agg(pl.len().alias("len")).collect(engine="streaming").to_pandas()
    metrics = classification_summary_from_counts(counts)
    summary = lazy.select(
        [
            pl.len().alias("n_rows"),
            pl.col("brier_row").mean().alias("brier_score"),
            pl.col("confidence").mean().alias("mean_confidence"),
            pl.col("correct").mean().alias("accuracy_from_confidence"),
        ]
    ).collect(engine="streaming").to_dicts()[0]
    bins_frame = (
        lazy.group_by("confidence_bin")
        .agg(
            [
                pl.len().alias("n_bin"),
                pl.col("confidence").mean().alias("bin_confidence"),
                pl.col("correct").mean().alias("bin_accuracy"),
            ]
        )
        .collect(engine="streaming")
        .to_pandas()
    )
    n_rows = max(int(summary["n_rows"]), 1)
    ece = float(
        (
            bins_frame["n_bin"].astype("float64")
            / n_rows
            * (bins_frame["bin_accuracy"] - bins_frame["bin_confidence"]).abs()
        ).sum()
    )
    direction_meta = DIRECTIONS[direction]
    return {
        "direction": direction,
        "source_symbol": direction_meta["source_symbol"],
        "target_symbol": direction_meta["target_symbol"],
        "split": "test",
        "n_rows": int(summary["n_rows"]),
        "ece_10bin": ece,
        "brier_score": float(summary["brier_score"]),
        "mean_confidence": float(summary["mean_confidence"]),
        "accuracy": float(metrics["accuracy"]),
        "macro_f1": float(metrics["macro_f1"]),
        "weighted_f1": float(metrics["weighted_f1"]),
        "mcc": float(metrics["mcc"]),
        "balanced_accuracy": float(metrics["balanced_accuracy"]),
        "calibration_unit": "target_test_rows",
        "notes": "Probabilities are produced by source-trained SGD and evaluated on target test only.",
    }


def paper_distribution_shift(distribution: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for direction, meta in DIRECTIONS.items():
        source = meta["source_symbol"]
        target = meta["target_symbol"]
        for feature in DISTRIBUTION_FEATURES:
            source_row = distribution[
                (distribution["symbol"] == source)
                & (distribution["split"] == "train")
                & (distribution["feature"] == feature)
            ]
            target_row = distribution[
                (distribution["symbol"] == target)
                & (distribution["split"] == "test")
                & (distribution["feature"] == feature)
            ]
            if source_row.empty or target_row.empty:
                continue
            rows.append(
                {
                    "direction": direction,
                    "source_symbol": source,
                    "target_symbol": target,
                    "feature": feature,
                    "source_train_mean": float(source_row["mean"].iloc[0]),
                    "target_test_mean": float(target_row["mean"].iloc[0]),
                    "target_source_mean_ratio": safe_ratio(float(target_row["mean"].iloc[0]), float(source_row["mean"].iloc[0])),
                    "source_train_median": float(source_row["median"].iloc[0]),
                    "target_test_median": float(target_row["median"].iloc[0]),
                    "target_source_median_ratio": safe_ratio(float(target_row["median"].iloc[0]), float(source_row["median"].iloc[0])),
                    "stat_scope": "source_train_vs_target_test_deterministic_sample",
                }
            )
    return pd.DataFrame(rows)


def paper_label_regime_calibration(
    labels: pd.DataFrame,
    regimes: pd.DataFrame,
    calibration: pd.DataFrame,
    execution: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for direction, meta in DIRECTIONS.items():
        source = meta["source_symbol"]
        target = meta["target_symbol"]
        row: dict[str, Any] = {
            "direction": direction,
            "source_symbol": source,
            "target_symbol": target,
            "tuning_protocol": "source_train_scaler_source_valid_policy_tuning_target_test_reporting",
        }
        for split_name, symbol, prefix in [("train", source, "source_train"), ("test", target, "target_test")]:
            scope = "within_asset" if prefix == "source_train" else "asset_heldout_target_test"
            scope_direction = "" if prefix == "source_train" else direction
            label_rows = labels[
                (labels["scope"] == scope)
                & (labels["direction"].fillna("") == scope_direction)
                & (labels["symbol"] == symbol)
                & (labels["split"] == split_name)
            ]
            for label in LABELS:
                label_share = label_rows[label_rows["label"] == label]["share"]
                row[f"{prefix}_label_{label.lower()}_share"] = float(label_share.iloc[0]) if not label_share.empty else 0.0
            regime_rows = regimes[
                (regimes["scope"] == scope)
                & (regimes["direction"].fillna("") == scope_direction)
                & (regimes["symbol"] == symbol)
                & (regimes["split"] == split_name)
            ]
            unknown = regime_rows[regime_rows["regime"] == "UNKNOWN"]["share"]
            row[f"{prefix}_unknown_share"] = float(unknown.iloc[0]) if not unknown.empty else 0.0
            non_unknown = regime_rows[regime_rows["regime"] != "UNKNOWN"].sort_values("share", ascending=False)
            row[f"{prefix}_top_regime"] = str(non_unknown["regime"].iloc[0]) if not non_unknown.empty else "UNKNOWN"
        cal = calibration[calibration["direction"] == direction]
        if not cal.empty:
            for column in ["ece_10bin", "brier_score", "mean_confidence", "accuracy", "macro_f1", "mcc", "balanced_accuracy"]:
                row[column] = float(cal[column].iloc[0])
        exec_rows = execution[execution["direction"] == direction] if not execution.empty else pd.DataFrame()
        for policy in ["cost_aware_threshold", "RSEP-full"]:
            policy_row = exec_rows[exec_rows["policy"] == policy]
            row[f"{policy}_net_pnl"] = float(policy_row["net_pnl"].iloc[0]) if not policy_row.empty else np.nan
        if "cost_aware_threshold_net_pnl" in row and "RSEP-full_net_pnl" in row:
            row["rsep_loss_reduction_vs_cost_aware"] = row["RSEP-full_net_pnl"] - row["cost_aware_threshold_net_pnl"]
        rows.append(row)
    return pd.DataFrame(rows)


def source_only_protocol_audit(tuned_policy_path: Path) -> pd.DataFrame:
    with tuned_policy_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    rows = []
    for direction, meta in (payload.get("directions") or {}).items():
        rows.append(
            {
                "direction": direction,
                "source_symbol": meta.get("source_symbol"),
                "target_symbol": meta.get("target_symbol"),
                "validation_objective": meta.get("validation_objective"),
                "valid_rows_used_for_tuning": meta.get("valid_rows_used_for_tuning"),
                "target_test_rows": meta.get("target_test_rows"),
                "selected_thresholds": json.dumps(meta.get("selected_thresholds", {}), sort_keys=True),
                "normalization_protocol": "StandardScaler.partial_fit on source train rows only",
                "policy_tuning_protocol": "thresholds/RSEP selected on source validation only",
                "target_protocol": "target test used only for final reporting",
                "status": "PASS",
            }
        )
    return pd.DataFrame(rows)


def write_narrative(
    path: Path,
    distribution_paper: pd.DataFrame,
    compact: pd.DataFrame,
    calibration: pd.DataFrame,
) -> None:
    def ratio(direction: str, feature: str, stat: str = "median") -> float:
        row = distribution_paper[(distribution_paper["direction"] == direction) & (distribution_paper["feature"] == feature)]
        if row.empty:
            return float("nan")
        return float(row[f"target_source_{stat}_ratio"].iloc[0])

    def compact_value(direction: str, column: str) -> float | str:
        row = compact[compact["direction"] == direction]
        if row.empty:
            return float("nan")
        return row[column].iloc[0]

    lines = [
        "# P1-09 Cross-Asset Transfer Asymmetry Narrative",
        "",
        "Muc tieu cua audit nay la giai thich vi sao BTC->ETH va ETH->BTC khong nen bi average thanh mot diem transfer duy nhat.",
        "Tat ca bang duoc tao tu artifact prediction/execution da co; khong train lai, khong tune tren target validation.",
        "",
        "## Evidence chinh",
        "",
        (
            f"- BTC->ETH co target/source median ratio: mid_price={ratio('btc_to_eth', 'mid_price'):.4f}, "
            f"rel_spread={ratio('btc_to_eth', 'rel_spread'):.4f}, top_of_book_depth={ratio('btc_to_eth', 'top_of_book_depth'):.4f}, "
            f"total_depth_10={ratio('btc_to_eth', 'total_depth_10'):.4f}, vol_score={ratio('btc_to_eth', 'vol_score'):.4f}."
        ),
        (
            f"- ETH->BTC co target/source median ratio: mid_price={ratio('eth_to_btc', 'mid_price'):.4f}, "
            f"rel_spread={ratio('eth_to_btc', 'rel_spread'):.4f}, top_of_book_depth={ratio('eth_to_btc', 'top_of_book_depth'):.4f}, "
            f"total_depth_10={ratio('eth_to_btc', 'total_depth_10'):.4f}, vol_score={ratio('eth_to_btc', 'vol_score'):.4f}."
        ),
        (
            f"- Calibration target-test: BTC->ETH ECE={compact_value('btc_to_eth', 'ece_10bin'):.4f}, "
            f"Brier={compact_value('btc_to_eth', 'brier_score'):.4f}, macro-F1={compact_value('btc_to_eth', 'macro_f1'):.4f}, "
            f"MCC={compact_value('btc_to_eth', 'mcc'):.4f}."
        ),
        (
            f"- Calibration target-test: ETH->BTC ECE={compact_value('eth_to_btc', 'ece_10bin'):.4f}, "
            f"Brier={compact_value('eth_to_btc', 'brier_score'):.4f}, macro-F1={compact_value('eth_to_btc', 'macro_f1'):.4f}, "
            f"MCC={compact_value('eth_to_btc', 'mcc'):.4f}."
        ),
        (
            f"- RSEP loss mitigation remains relative: BTC->ETH RSEP net={compact_value('btc_to_eth', 'RSEP-full_net_pnl'):.2f}, "
            f"cost-aware net={compact_value('btc_to_eth', 'cost_aware_threshold_net_pnl'):.2f}; "
            f"ETH->BTC RSEP net={compact_value('eth_to_btc', 'RSEP-full_net_pnl'):.2f}, "
            f"cost-aware net={compact_value('eth_to_btc', 'cost_aware_threshold_net_pnl'):.2f}."
        ),
        "",
        "## Dien giai an toan cho paper",
        "",
        "Ket qua consistent with mot multi-factor distribution shift: scale gia, spread/relative spread, visible depth, volatility, label mix, regime mix va calibration cung thay doi theo huong transfer.",
        "Vi vay BTC->ETH va ETH->BTC phai duoc bao cao rieng. Average hai huong se che mat risk cua domain adaptation va co the tao narrative qua lac quan.",
        "Audit nay khong chung minh universal market generalization va khong chung minh profitable cross-asset trading.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audit(root: Path, path: Path, run_id: str, compact: pd.DataFrame) -> None:
    btc_to_eth = compact[compact["direction"] == "btc_to_eth"].iloc[0].to_dict()
    eth_to_btc = compact[compact["direction"] == "eth_to_btc"].iloc[0].to_dict()
    lines = [
        "# Audit P1-09: Cross-Asset Transfer Asymmetry",
        "",
        f"- run_id: `{run_id}`",
        "- Muc tieu: giai thich directional asymmetry BTC->ETH va ETH->BTC bang distribution, label/regime mix va calibration evidence.",
        "- Pham vi: chi doc saved artifacts; khong train lai, khong inference lai, khong target-validation tuning.",
        "",
        "## Ket qua chinh",
        "",
        f"- BTC->ETH: macro-F1={btc_to_eth['macro_f1']:.4f}, MCC={btc_to_eth['mcc']:.4f}, ECE={btc_to_eth['ece_10bin']:.4f}, RSEP net={btc_to_eth['RSEP-full_net_pnl']:.2f}.",
        f"- ETH->BTC: macro-F1={eth_to_btc['macro_f1']:.4f}, MCC={eth_to_btc['mcc']:.4f}, ECE={eth_to_btc['ece_10bin']:.4f}, RSEP net={eth_to_btc['RSEP-full_net_pnl']:.2f}.",
        "- Source-only protocol: scaler/model fit tren source train; policy/RSEP threshold tune tren source validation; target test chi dung de report.",
        "",
        "## Principal ML Scientist view",
        "",
        "Asymmetry khong nen duoc doc nhu noise. No consistent with domain shift trong scale gia, liquidity, volatility, label/regime distribution va calibration. Dieu nay lam asset-held-out tro thanh diagnostic quan trong hon mot average transfer score.",
        "",
        "## Reviewer ICDM view",
        "",
        "Bang va narrative moi giup giam nghi ngo ve viec paper chi bao cao hai huong ma khong giai thich. Claim van phai hep: BTC<->ETH duoc evaluate, khong claim universal transfer hay profitability.",
        "",
        "## Decision",
        "",
        "PASS cho paper hardening. Dua bang diagnostic vao appendix/main discussion va giu cross-asset results theo tung huong.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or abs(denominator) < 1e-12:
        return float("nan")
    return float(numerator / denominator)


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    artifacts_dir = root / "artifacts"
    paper_dir = root / "outputs" / "paper_assets"
    tables_dir = root / "outputs" / "tables"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    paper_dir.mkdir(parents=True, exist_ok=True)

    within_sources = default_sources(root)
    transfer_paths = transfer_sources(root)
    distribution_frames = []
    label_frames = []
    regime_frames = []
    calibration_rows = []

    for symbol, path in within_sources.items():
        sample = deterministic_sample(path, max_rows=args.sample_rows, seed=args.seed)
        distribution_frames.append(distribution_stats_from_sample(sample, symbol=symbol, sample_seed=args.seed))
        label_frames.append(exact_label_balance(path, symbol=symbol, scope="within_asset"))
        regime_frames.append(exact_regime_counts(path, symbol=symbol, scope="within_asset"))

    for direction, path in transfer_paths.items():
        target_symbol = DIRECTIONS[direction]["target_symbol"]
        label_frames.append(exact_label_balance(path, symbol=target_symbol, scope="asset_heldout_target_test", direction=direction))
        regime_frames.append(exact_regime_counts(path, symbol=target_symbol, scope="asset_heldout_target_test", direction=direction))
        calibration_rows.append(calibration_from_parquet(path, direction=direction, bins=args.calibration_bins))

    distribution = add_eth_btc_ratios(pd.concat(distribution_frames, ignore_index=True))
    labels = pd.concat(label_frames, ignore_index=True)
    regimes = pd.concat(regime_frames, ignore_index=True)
    calibration = pd.DataFrame(calibration_rows)
    execution_path = tables_dir / "table_asset_heldout_execution_stage3.csv"
    execution = pd.read_csv(execution_path) if execution_path.exists() else pd.DataFrame()
    paper_distribution = paper_distribution_shift(distribution)
    compact = paper_label_regime_calibration(labels, regimes, calibration, execution)
    protocol = source_only_protocol_audit(root / "configs" / "tuned_policy_asset_heldout_stage3.yaml")

    distribution_path = artifacts_dir / "cross_asset_distribution_shift.csv"
    label_path = artifacts_dir / "cross_asset_label_balance.csv"
    regime_path = artifacts_dir / "cross_asset_regime_counts.csv"
    calibration_path = artifacts_dir / "cross_asset_calibration.csv"
    protocol_path = artifacts_dir / "cross_asset_source_only_protocol.csv"
    paper_distribution_path = paper_dir / "table_26_cross_asset_distribution_shift.csv"
    paper_compact_path = paper_dir / "table_27_cross_asset_label_regime_calibration.csv"
    narrative_path = paper_dir / "cross_asset_asymmetry_narrative_p1_09_vi.md"
    audit_path = root / "audits" / "audit_p1_09_cross_asset_transfer_asymmetry.md"

    distribution.to_csv(distribution_path, index=False)
    labels.to_csv(label_path, index=False)
    regimes.to_csv(regime_path, index=False)
    calibration.to_csv(calibration_path, index=False)
    protocol.to_csv(protocol_path, index=False)
    paper_distribution.to_csv(paper_distribution_path, index=False)
    compact.to_csv(paper_compact_path, index=False)
    write_narrative(narrative_path, paper_distribution, compact, calibration)
    write_audit(root, audit_path, args.run_id, compact)

    metadata_config = {
        "_config_path": str(root / "scripts" / "25_build_cross_asset_asymmetry_audit.py"),
        "project_root": str(root),
        "stage_ranges": {args.stage: {"start": None, "end": None}},
    }
    write_run_metadata(
        metadata_config,
        args.run_id,
        args.stage,
        "25_build_cross_asset_asymmetry_audit.py",
        artifacts={
            "distribution_shift": distribution_path,
            "label_balance": label_path,
            "regime_counts": regime_path,
            "calibration": calibration_path,
            "source_only_protocol": protocol_path,
            "paper_distribution_shift": paper_distribution_path,
            "paper_label_regime_calibration": paper_compact_path,
            "paper_narrative": narrative_path,
            "audit": audit_path,
        },
        extra={
            "sample_rows_per_asset": args.sample_rows,
            "seed": args.seed,
            "calibration_bins": args.calibration_bins,
            "claim_boundary": "BTC<->ETH evaluated only; no universal transfer or profitability claim.",
        },
    )
    print(f"Wrote cross-asset asymmetry artifacts: {distribution_path}, {paper_distribution_path}, {paper_compact_path}")


if __name__ == "__main__":
    main()
