from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from regimes.rule_regime_labeler import apply_rule_regimes, fit_thresholds
from utils.io import write_run_metadata


REQUIRED_COLUMNS = [
    "symbol",
    "split",
    "event_time",
    "regime",
    "rel_spread",
    "total_depth_10",
    "vol_score",
    "depth_drop_top10",
    "spread_z_1m",
    "momentum_score",
    "adverse_selection_score",
    "choppiness_score",
    "depth_z_1m",
    "liquidity_drought_score",
]

REGIME_INPUT_ROWS = [
    {
        "regime": "LIQUIDITY_DROUGHT",
        "diagnostic_interpretation": "Severe liquidity deterioration and spread/depth stress.",
        "causal_inputs": "depth_drop_top10, spread_z_1m",
        "rule_summary": "depth_drop_top10 <= depth_drop_q10 AND spread_z_1m >= spread_z_q80",
        "threshold_source": "train-prefix quantiles only",
    },
    {
        "regime": "MOMENTUM_TOXIC",
        "diagnostic_interpretation": "Strong directional pressure with elevated adverse-selection risk.",
        "causal_inputs": "abs(momentum_score), adverse_selection_score",
        "rule_summary": "abs(momentum_score) >= momentum_abs_q80 AND adverse_selection_score >= adverse_q70",
        "threshold_source": "train-prefix quantiles only",
    },
    {
        "regime": "VOLATILE_ILLIQUID",
        "diagnostic_interpretation": "High volatility with unfavorable spread and weak visible depth.",
        "causal_inputs": "vol_score, rel_spread, total_depth_10",
        "rule_summary": "vol_score >= vol_q70 AND rel_spread >= spread_q70 AND total_depth_10 <= depth_q40",
        "threshold_source": "train-prefix quantiles only",
    },
    {
        "regime": "CHOPPY_MEAN_REVERTING",
        "diagnostic_interpretation": "Reversal-prone movement where short-horizon direction is fragile.",
        "causal_inputs": "choppiness_score, abs(momentum_score)",
        "rule_summary": "choppiness_score >= flip_q70 AND abs(momentum_score) <= momentum_abs_q50",
        "threshold_source": "train-prefix quantiles only",
    },
    {
        "regime": "SHOCK_RECOVERY",
        "diagnostic_interpretation": "Post-shock state with elevated movement but not the strict drought condition.",
        "causal_inputs": "vol_score, depth_drop_top10, spread_z_1m",
        "rule_summary": "vol_score >= vol_q70 AND depth_drop_top10 > depth_drop_q10 AND spread_z_1m < spread_z_q80",
        "threshold_source": "train-prefix quantiles only",
    },
    {
        "regime": "VOLATILE_LIQUID",
        "diagnostic_interpretation": "Elevated volatility with comparatively adequate depth and spread.",
        "causal_inputs": "vol_score, rel_spread, total_depth_10",
        "rule_summary": "vol_score >= vol_q70 AND rel_spread <= spread_q40 AND total_depth_10 >= depth_q60",
        "threshold_source": "train-prefix quantiles only",
    },
    {
        "regime": "CALM_ILLIQUID",
        "diagnostic_interpretation": "Low volatility with less favorable spread/depth conditions.",
        "causal_inputs": "vol_score, rel_spread, total_depth_10",
        "rule_summary": "vol_score <= vol_q40 AND rel_spread >= spread_q70 AND total_depth_10 <= depth_q40",
        "threshold_source": "train-prefix quantiles only",
    },
    {
        "regime": "CALM_LIQUID",
        "diagnostic_interpretation": "Low volatility, narrow spread, and sufficient visible depth.",
        "causal_inputs": "vol_score, rel_spread, total_depth_10",
        "rule_summary": "vol_score <= vol_q40 AND rel_spread <= spread_q40 AND total_depth_10 >= depth_q60",
        "threshold_source": "train-prefix quantiles only",
    },
    {
        "regime": "MILD_LIQUIDITY_STRESS",
        "diagnostic_interpretation": "Moderate liquidity deterioration below stricter drought priority.",
        "causal_inputs": "liquidity_score, stress_score, liquidity_drought_score",
        "rule_summary": "(liquidity_score <= liquidity_q45 OR liquidity_drought_score >= drought_q55) with bounded stress",
        "threshold_source": "train-prefix quantiles only",
    },
    {
        "regime": "BALANCED_TRANSITION",
        "diagnostic_interpretation": "Structured residual state that is not clearly calm or extreme.",
        "causal_inputs": "stress_score, directional_toxicity_score, liquidity_score",
        "rule_summary": "stress_score <= stress_q60 AND directional_toxicity_score <= toxicity_q65 AND liquidity_score >= liquidity_q30",
        "threshold_source": "train-prefix quantiles only",
    },
    {
        "regime": "UNKNOWN",
        "diagnostic_interpretation": "Ambiguous or insufficient diagnostics after all priority rules.",
        "causal_inputs": "fallback after all causal diagnostic rules",
        "rule_summary": "No priority or residual rule matched.",
        "threshold_source": "explicit fallback; not hidden or redistributed",
    },
]


SENSITIVITY_SETTINGS = {
    "baseline": {"low": 0.40, "mid": 0.50, "high": 0.70, "very_high": 0.80, "very_low": 0.10},
    "strict_extremes": {"low": 0.45, "mid": 0.50, "high": 0.75, "very_high": 0.85, "very_low": 0.05},
    "relaxed_extremes": {"low": 0.35, "mid": 0.50, "high": 0.65, "very_high": 0.75, "very_low": 0.15},
}


def validate_required_columns(path: Path, columns: list[str] = REQUIRED_COLUMNS) -> None:
    schema = pl.scan_parquet(str(path)).collect_schema()
    missing = [column for column in columns if column not in schema.names()]
    if missing:
        raise ValueError(f"{path} missing required regime audit columns: {missing}")


def regime_counts_by_split(path: Path, symbol: str) -> pd.DataFrame:
    validate_required_columns(path)
    frame = (
        pl.scan_parquet(str(path))
        .select(["symbol", "split", "regime"])
        .group_by(["symbol", "split", "regime"])
        .agg(pl.len().alias("n_rows"))
        .sort(["symbol", "split", "regime"])
        .collect(engine="streaming")
        .to_pandas()
    )
    frame["symbol"] = symbol
    frame["split_total_rows"] = frame.groupby(["symbol", "split"], dropna=False)["n_rows"].transform("sum")
    frame["share_within_split"] = frame["n_rows"] / frame["split_total_rows"].clip(lower=1)
    return frame


def regime_audit_summary(path: Path, symbol: str, threshold_path: Path) -> pd.DataFrame:
    validate_required_columns(path)
    lazy = (
        pl.scan_parquet(str(path))
        .select(["event_time", "regime"])
        .with_columns(
            [
                pl.col("event_time").dt.strftime("%Y-%m-%d").alias("date"),
                (pl.col("regime") == "UNKNOWN").cast(pl.Float64).alias("is_unknown"),
            ]
        )
    )
    overall = lazy.select(
        [
            pl.len().alias("n_rows"),
            pl.col("is_unknown").sum().alias("unknown_rows"),
            pl.col("is_unknown").mean().alias("unknown_share"),
        ]
    ).collect(engine="streaming").to_dicts()[0]
    daily = (
        lazy.group_by("date")
        .agg(pl.col("is_unknown").mean().alias("unknown_share"))
        .collect(engine="streaming")
        .to_pandas()
    )
    with threshold_path.open("r", encoding="utf-8") as handle:
        thresholds = json.load(handle)
    return pd.DataFrame(
        [
            {
                "symbol": symbol,
                "n_rows": int(overall["n_rows"]),
                "unknown_rows": int(overall["unknown_rows"]),
                "unknown_share": float(overall["unknown_share"]),
                "daily_unknown_p90": float(daily["unknown_share"].quantile(0.90)) if not daily.empty else 0.0,
                "n_days": int(len(daily)),
                "threshold_count": int(len(thresholds)),
                "threshold_source": "first_60pct_chronological_train_prefix",
                "threshold_artifact": str(threshold_path),
                "status": "PASS" if float(overall["unknown_share"]) < 0.15 else "REVIEW",
                "notes": "Regimes are diagnostic labels; UNKNOWN is retained and reported.",
            }
        ]
    )


def deterministic_sample(path: Path, max_rows: int, seed: int) -> pd.DataFrame:
    validate_required_columns(path)
    lazy = pl.scan_parquet(str(path)).select(REQUIRED_COLUMNS)
    total = lazy.select(pl.len().alias("n")).collect(engine="streaming").item()
    fraction = min(1.0, float(max_rows) / max(float(total), 1.0))
    if fraction >= 1.0:
        return lazy.collect(engine="streaming").to_pandas()
    return lazy.with_row_index("__row_index").filter((pl.col("__row_index").hash(seed=seed) / (2**64 - 1)) <= fraction).drop("__row_index").limit(max_rows).collect(engine="streaming").to_pandas()


def sensitivity_table(sample: pd.DataFrame, symbol: str, train_fraction: float = 0.6) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    baseline_labels: pd.Series | None = None
    for setting, quantiles in SENSITIVITY_SETTINGS.items():
        thresholds = fit_thresholds(sample, train_fraction=train_fraction, quantiles=quantiles)
        labeled = apply_rule_regimes(sample, thresholds)
        if setting == "baseline":
            baseline_labels = labeled["regime"].astype(str).reset_index(drop=True)
        current_labels = labeled["regime"].astype(str).reset_index(drop=True)
        agreement = float(current_labels.eq(baseline_labels).mean()) if baseline_labels is not None else 1.0
        counts = current_labels.value_counts(dropna=False)
        total = max(int(len(current_labels)), 1)
        for regime, n_rows in counts.items():
            rows.append(
                {
                    "symbol": symbol,
                    "setting": setting,
                    "regime": regime,
                    "n_rows": int(n_rows),
                    "share": float(n_rows) / total,
                    "unknown_share": float(current_labels.eq("UNKNOWN").mean()),
                    "agreement_with_baseline": agreement,
                    "sample_rows": total,
                    "train_fraction_for_thresholds": float(train_fraction),
                }
            )
    return pd.DataFrame(rows)


def taxonomy_input_table() -> pd.DataFrame:
    return pd.DataFrame(REGIME_INPUT_ROWS)


def _default_sources(root: Path) -> list[dict[str, Path | str]]:
    return [
        {
            "symbol": "BTC-USDT",
            "prediction": root / "data" / "predictions" / "predictions.parquet",
            "thresholds": root / "data" / "regimes" / "regime_thresholds.json",
        },
        {
            "symbol": "ETH-USDT",
            "prediction": root / "data" / "predictions" / "predictions_eth_stage3_sgd.parquet",
            "thresholds": root / "data" / "regimes" / "regime_thresholds_eth_stage3.json",
        },
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Build reviewer-facing regime taxonomy audit artifacts.")
    parser.add_argument("--stage", default="stage_3_full_scale")
    parser.add_argument("--run-id", default="p1_08_regime_taxonomy_audit_v001")
    parser.add_argument("--sample-rows", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    artifacts_dir = root / "artifacts"
    paper_dir = root / "outputs" / "paper_assets"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    paper_dir.mkdir(parents=True, exist_ok=True)

    audit_frames = []
    count_frames = []
    sensitivity_frames = []
    for source in _default_sources(root):
        symbol = str(source["symbol"])
        prediction = Path(source["prediction"])
        thresholds = Path(source["thresholds"])
        audit_frames.append(regime_audit_summary(prediction, symbol, thresholds))
        count_frames.append(regime_counts_by_split(prediction, symbol))
        sample = deterministic_sample(prediction, max_rows=args.sample_rows, seed=args.seed)
        sensitivity_frames.append(sensitivity_table(sample, symbol))

    audit = pd.concat(audit_frames, ignore_index=True)
    counts = pd.concat(count_frames, ignore_index=True)
    sensitivity = pd.concat(sensitivity_frames, ignore_index=True)
    taxonomy = taxonomy_input_table()

    audit_path = artifacts_dir / "regime_audit.csv"
    counts_path = artifacts_dir / "regime_counts_by_split.csv"
    taxonomy_path = paper_dir / "table_23_regime_taxonomy_inputs.csv"
    counts_paper_path = paper_dir / "table_24_regime_counts_by_asset_split.csv"
    sensitivity_path = paper_dir / "table_25_regime_sensitivity.csv"
    audit.to_csv(audit_path, index=False)
    counts.to_csv(counts_path, index=False)
    taxonomy.to_csv(taxonomy_path, index=False)
    counts.to_csv(counts_paper_path, index=False)
    sensitivity.to_csv(sensitivity_path, index=False)

    metadata_config = {
        "_config_path": str(root / "scripts" / "24_build_regime_audit.py"),
        "project_root": str(root),
        "stage_ranges": {args.stage: {"start": None, "end": None}},
    }
    write_run_metadata(
        metadata_config,
        args.run_id,
        args.stage,
        "24_build_regime_audit.py",
        artifacts={
            "regime_audit": audit_path,
            "regime_counts_by_split": counts_path,
            "taxonomy_input_table": taxonomy_path,
            "paper_counts_by_split": counts_paper_path,
            "sensitivity": sensitivity_path,
        },
        extra={
            "sample_rows_per_asset": args.sample_rows,
            "seed": args.seed,
            "sensitivity_settings": SENSITIVITY_SETTINGS,
            "threshold_source": "first 60pct chronological train prefix",
        },
    )
    print(f"Wrote regime audit artifacts: {audit_path}, {counts_path}, {sensitivity_path}")


if __name__ == "__main__":
    main()
