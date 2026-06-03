from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import polars as pl
import pyarrow.parquet as pq


REGIMES = [
    "CALM_LIQUID",
    "CALM_ILLIQUID",
    "VOLATILE_LIQUID",
    "VOLATILE_ILLIQUID",
    "MOMENTUM_TOXIC",
    "CHOPPY_MEAN_REVERTING",
    "LIQUIDITY_DROUGHT",
    "SHOCK_RECOVERY",
    "BALANCED_TRANSITION",
    "MILD_LIQUIDITY_STRESS",
    "UNKNOWN",
]


def fit_thresholds(frame: pd.DataFrame, train_fraction: float, quantiles: dict[str, float]) -> dict[str, float]:
    cutoff = max(1, int(len(frame) * train_fraction))
    train = add_taxonomy_scores(frame.iloc[:cutoff].copy())
    thresholds = {
        "vol_q40": float(train["vol_score"].quantile(quantiles["low"])),
        "vol_q70": float(train["vol_score"].quantile(quantiles["high"])),
        "spread_q40": float(train["rel_spread"].quantile(quantiles["low"])),
        "spread_q70": float(train["rel_spread"].quantile(quantiles["high"])),
        "depth_q40": float(train["total_depth_10"].quantile(quantiles["low"])),
        "depth_q60": float(train["total_depth_10"].quantile(0.6)),
        "depth_drop_q10": float(train["depth_drop_top10"].quantile(quantiles["very_low"])),
        "spread_z_q80": float(train["spread_z_1m"].quantile(quantiles["very_high"])),
        "momentum_abs_q80": float(train["momentum_score"].abs().quantile(quantiles["very_high"])),
        "adverse_q70": float(train["adverse_selection_score"].quantile(quantiles["high"])),
        "flip_q70": float(train["choppiness_score"].quantile(quantiles["high"])),
        "momentum_abs_q50": float(train["momentum_score"].abs().quantile(quantiles["mid"])),
    }
    thresholds.update(
        {
            "stress_q35": float(train["stress_score"].quantile(0.35)),
            "stress_q60": float(train["stress_score"].quantile(0.60)),
            "stress_q80": float(train["stress_score"].quantile(0.80)),
            "liquidity_q30": float(train["liquidity_score"].quantile(0.30)),
            "liquidity_q45": float(train["liquidity_score"].quantile(0.45)),
            "liquidity_q70": float(train["liquidity_score"].quantile(0.70)),
            "toxicity_q45": float(train["directional_toxicity_score"].quantile(0.45)),
            "toxicity_q65": float(train["directional_toxicity_score"].quantile(0.65)),
            "choppy_q60": float(train["choppiness_score"].quantile(0.60)),
            "drought_q55": float(train["liquidity_drought_score"].quantile(0.55)),
            "drought_q70": float(train["liquidity_drought_score"].quantile(0.70)),
        }
    )
    return thresholds


def fit_thresholds_from_parquet(path: Path, train_fraction: float, quantiles: dict[str, float]) -> dict[str, float]:
    total_rows = int(pq.ParquetFile(path).metadata.num_rows)
    cutoff = max(1, int(total_rows * train_fraction))
    depth_z = pl.col("depth_z_1m").fill_nan(0.0).fill_null(0.0)
    spread_z = pl.col("spread_z_1m").fill_nan(0.0).fill_null(0.0)
    momentum_abs = pl.col("momentum_score").abs()
    directional_toxicity = momentum_abs.fill_nan(0.0).fill_null(0.0) + pl.col("adverse_selection_score").fill_nan(0.0).fill_null(0.0)
    lazy = (
        pl.scan_parquet(str(path))
        .with_row_index("__row_index")
        .filter(pl.col("__row_index") < cutoff)
        .with_columns(
            [
                (depth_z - spread_z).alias("liquidity_score"),
                (pl.col("vol_score").fill_nan(0.0).fill_null(0.0) + spread_z - depth_z).alias("stress_score"),
                directional_toxicity.alias("directional_toxicity_score"),
            ]
        )
    )
    expressions = [
        _linear_quantile("vol_score", quantiles["low"], "vol_q40"),
        _linear_quantile("vol_score", quantiles["high"], "vol_q70"),
        _linear_quantile("rel_spread", quantiles["low"], "spread_q40"),
        _linear_quantile("rel_spread", quantiles["high"], "spread_q70"),
        _linear_quantile("total_depth_10", quantiles["low"], "depth_q40"),
        _linear_quantile("total_depth_10", 0.6, "depth_q60"),
        _linear_quantile("depth_drop_top10", quantiles["very_low"], "depth_drop_q10"),
        _linear_quantile("spread_z_1m", quantiles["very_high"], "spread_z_q80"),
        momentum_abs.quantile(quantiles["very_high"], interpolation="linear").alias("momentum_abs_q80"),
        _linear_quantile("adverse_selection_score", quantiles["high"], "adverse_q70"),
        _linear_quantile("choppiness_score", quantiles["high"], "flip_q70"),
        momentum_abs.quantile(quantiles["mid"], interpolation="linear").alias("momentum_abs_q50"),
        _linear_quantile("stress_score", 0.35, "stress_q35"),
        _linear_quantile("stress_score", 0.60, "stress_q60"),
        _linear_quantile("stress_score", 0.80, "stress_q80"),
        _linear_quantile("liquidity_score", 0.30, "liquidity_q30"),
        _linear_quantile("liquidity_score", 0.45, "liquidity_q45"),
        _linear_quantile("liquidity_score", 0.70, "liquidity_q70"),
        _linear_quantile("directional_toxicity_score", 0.45, "toxicity_q45"),
        _linear_quantile("directional_toxicity_score", 0.65, "toxicity_q65"),
        _linear_quantile("choppiness_score", 0.60, "choppy_q60"),
        _linear_quantile("liquidity_drought_score", 0.55, "drought_q55"),
        _linear_quantile("liquidity_drought_score", 0.70, "drought_q70"),
    ]
    row = lazy.select(expressions).collect(engine="streaming").to_dicts()[0]
    return {key: float(value) for key, value in row.items()}


def apply_rule_regimes(frame: pd.DataFrame, thresholds: dict[str, float]) -> pd.DataFrame:
    labeled = add_taxonomy_scores(frame.copy())
    labeled["regime"] = "UNKNOWN"

    calm_liquid = (
        (labeled["vol_score"] <= thresholds["vol_q40"])
        & (labeled["rel_spread"] <= thresholds["spread_q40"])
        & (labeled["total_depth_10"] >= thresholds["depth_q60"])
    )
    calm_illiquid = (
        (labeled["vol_score"] <= thresholds["vol_q40"])
        & (labeled["rel_spread"] >= thresholds["spread_q70"])
        & (labeled["total_depth_10"] <= thresholds["depth_q40"])
    )
    volatile_liquid = (
        (labeled["vol_score"] >= thresholds["vol_q70"])
        & (labeled["rel_spread"] <= thresholds["spread_q40"])
        & (labeled["total_depth_10"] >= thresholds["depth_q60"])
    )
    volatile_illiquid = (
        (labeled["vol_score"] >= thresholds["vol_q70"])
        & (labeled["rel_spread"] >= thresholds["spread_q70"])
        & (labeled["total_depth_10"] <= thresholds["depth_q40"])
    )
    liquidity_drought = (
        (labeled["depth_drop_top10"] <= thresholds["depth_drop_q10"])
        & (labeled["spread_z_1m"] >= thresholds["spread_z_q80"])
    )
    momentum_toxic = (
        (labeled["momentum_score"].abs() >= thresholds["momentum_abs_q80"])
        & (labeled["adverse_selection_score"] >= thresholds["adverse_q70"])
    )
    choppy = (
        (labeled["choppiness_score"] >= thresholds["flip_q70"])
        & (labeled["momentum_score"].abs() <= thresholds["momentum_abs_q50"])
    )
    shock_recovery = (
        (labeled["vol_score"] >= thresholds["vol_q70"])
        & (labeled["depth_drop_top10"] > thresholds["depth_drop_q10"])
        & (labeled["spread_z_1m"] < thresholds["spread_z_q80"])
    )
    mild_liquidity_stress = (
        (
            (labeled["liquidity_score"] <= thresholds["liquidity_q45"])
            & (labeled["stress_score"] >= thresholds["stress_q35"])
        )
        | (
            (labeled["liquidity_drought_score"] >= thresholds["drought_q55"])
            & (labeled["stress_score"] >= thresholds["stress_q35"])
        )
    ) & (labeled["stress_score"] <= thresholds["stress_q80"])
    balanced_transition = (
        (labeled["stress_score"] <= thresholds["stress_q60"])
        & (labeled["directional_toxicity_score"] <= thresholds["toxicity_q65"])
        & (labeled["liquidity_score"] >= thresholds["liquidity_q30"])
    )

    ordered_rules = [
        ("LIQUIDITY_DROUGHT", liquidity_drought),
        ("MOMENTUM_TOXIC", momentum_toxic),
        ("VOLATILE_ILLIQUID", volatile_illiquid),
        ("CHOPPY_MEAN_REVERTING", choppy),
        ("SHOCK_RECOVERY", shock_recovery),
        ("VOLATILE_LIQUID", volatile_liquid),
        ("CALM_ILLIQUID", calm_illiquid),
        ("CALM_LIQUID", calm_liquid),
        ("MILD_LIQUIDITY_STRESS", mild_liquidity_stress),
        ("BALANCED_TRANSITION", balanced_transition),
    ]
    for regime, mask in ordered_rules:
        labeled.loc[mask & labeled["regime"].eq("UNKNOWN"), "regime"] = regime
    return labeled


def add_taxonomy_scores(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["liquidity_score"] = (
        enriched["depth_z_1m"].fillna(0.0) - enriched["spread_z_1m"].fillna(0.0)
    ).astype("float32")
    enriched["stress_score"] = (
        enriched["vol_score"].fillna(0.0)
        + enriched["spread_z_1m"].fillna(0.0)
        - enriched["depth_z_1m"].fillna(0.0)
    ).astype("float32")
    enriched["directional_toxicity_score"] = (
        enriched["momentum_score"].abs().fillna(0.0) + enriched["adverse_selection_score"].fillna(0.0)
    ).astype("float32")
    return enriched


def save_thresholds(thresholds: dict[str, float], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(thresholds, handle, ensure_ascii=False, indent=2)


def _linear_quantile(column: str, quantile: float, alias: str) -> pl.Expr:
    return pl.col(column).quantile(float(quantile), interpolation="linear").alias(alias)
