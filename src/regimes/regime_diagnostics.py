from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl

from utils.artifacts import is_stage2, namespaced_name, stage_namespace_slug, stage_slug, stage_table_path


def save_regime_tables(frame: pd.DataFrame, tables_dir: Path, *, namespace: str | None = None, stage: str | None = None) -> dict[str, Path]:
    tables_dir.mkdir(parents=True, exist_ok=True)
    current = frame.copy()
    current["month"] = pd.to_datetime(current["event_time"], utc=True).dt.tz_convert(None).dt.to_period("M").astype(str)
    counts = current.groupby(["symbol", "month", "regime"], dropna=False, observed=False).size().reset_index(name="n_rows")
    medians = current.groupby("regime", dropna=False)[
        ["rel_spread", "total_depth_10", "vol_score", "liquidity_drought_score", "adverse_selection_score"]
    ].median().reset_index()
    counts_path = tables_dir / namespaced_name("table_regime_counts_by_symbol_month", namespace, suffix=".csv")
    medians_path = tables_dir / namespaced_name("table_regime_feature_medians", namespace, suffix=".csv")
    counts.to_csv(counts_path, index=False)
    medians.to_csv(medians_path, index=False)
    refined_share_path = save_regime_share(frame, tables_dir / namespaced_name("table_regime_share_refined", namespace, suffix=".csv"))
    unknown_daily_path = save_unknown_daily_share(frame, tables_dir / namespaced_name("table_unknown_daily_share_refined", namespace, suffix=".csv"))
    run_length_path = save_regime_run_lengths(frame, tables_dir / namespaced_name("table_regime_run_lengths_refined", namespace, suffix=".csv"))
    refined_medians_path = save_refined_feature_medians(frame, tables_dir / namespaced_name("table_regime_feature_medians_refined", namespace, suffix=".csv"))
    if stage:
        save_regime_share(frame, stage_table_path(tables_dir, "table_regime_share", stage, namespace=namespace))
        save_unknown_daily_share(frame, stage_table_path(tables_dir, "table_unknown_daily_share", stage, namespace=namespace))
    return {
        "counts": counts_path,
        "medians": medians_path,
        "refined_share": refined_share_path,
        "unknown_daily": unknown_daily_path,
        "run_lengths": run_length_path,
        "refined_medians": refined_medians_path,
    }


def save_partitioned_regime_tables(regime_path: Path, tables_dir: Path, *, stage: str | None = None, namespace: str | None = None) -> dict[str, Path]:
    tables_dir.mkdir(parents=True, exist_ok=True)
    lazy = (
        pl.scan_parquet(str(regime_path))
        .with_columns(
            [
                pl.col("event_time").dt.strftime("%Y-%m").alias("month"),
                pl.col("event_time").dt.strftime("%Y-%m-%d").alias("date"),
                (pl.col("regime") == "UNKNOWN").cast(pl.Float64).alias("is_unknown"),
            ]
        )
    )
    counts = (
        lazy.group_by(["symbol", "month", "regime"])
        .agg(pl.len().alias("n_rows"))
        .sort(["symbol", "month", "regime"])
        .collect(engine="streaming")
        .to_pandas()
    )
    medians = _collect_feature_medians(
        lazy,
        ["rel_spread", "total_depth_10", "vol_score", "liquidity_drought_score", "adverse_selection_score"],
    )
    share = (
        lazy.group_by("regime")
        .agg(pl.len().alias("n_rows"))
        .sort("n_rows", descending=True)
        .collect(engine="streaming")
        .to_pandas()
    )
    share["share"] = share["n_rows"] / max(float(share["n_rows"].sum()), 1.0)
    unknown_daily = (
        lazy.group_by("date")
        .agg(pl.col("is_unknown").mean().alias("unknown_share"))
        .sort("date")
        .collect(engine="streaming")
        .to_pandas()
    )
    unknown_monthly = (
        lazy.group_by("month")
        .agg(pl.col("is_unknown").mean().alias("unknown_share"))
        .sort("month")
        .collect(engine="streaming")
        .to_pandas()
    )
    refined_medians = _collect_feature_medians(
        lazy,
        [
            "rel_spread",
            "total_depth_10",
            "vol_score",
            "liquidity_drought_score",
            "adverse_selection_score",
            "liquidity_score",
            "stress_score",
            "directional_toxicity_score",
        ],
    )
    run_lengths = _run_length_summary(regime_path)

    paths = {
        "counts": tables_dir / namespaced_name("table_regime_counts_by_symbol_month", namespace, suffix=".csv"),
        "medians": tables_dir / namespaced_name("table_regime_feature_medians", namespace, suffix=".csv"),
        "refined_share": tables_dir / namespaced_name("table_regime_share_refined", namespace, suffix=".csv"),
        "unknown_daily": tables_dir / namespaced_name("table_unknown_daily_share_refined", namespace, suffix=".csv"),
        "run_lengths": tables_dir / namespaced_name("table_regime_run_lengths_refined", namespace, suffix=".csv"),
        "refined_medians": tables_dir / namespaced_name("table_regime_feature_medians_refined", namespace, suffix=".csv"),
        "stage_share": stage_table_path(tables_dir, "table_regime_share", stage, namespace=namespace),
        "stage_unknown_monthly": stage_table_path(tables_dir, "table_unknown_monthly_share", stage, namespace=namespace),
        "stage_unknown_daily": stage_table_path(tables_dir, "table_unknown_daily_share", stage, namespace=namespace),
        "stage_feature_medians": stage_table_path(tables_dir, "table_regime_feature_medians", stage, namespace=namespace),
    }
    counts.to_csv(paths["counts"], index=False)
    medians.to_csv(paths["medians"], index=False)
    share.to_csv(paths["refined_share"], index=False)
    share.to_csv(paths["stage_share"], index=False)
    unknown_daily.to_csv(paths["unknown_daily"], index=False)
    unknown_daily.to_csv(paths["stage_unknown_daily"], index=False)
    unknown_monthly.to_csv(paths["stage_unknown_monthly"], index=False)
    run_lengths.to_csv(paths["run_lengths"], index=False)
    refined_medians.to_csv(paths["refined_medians"], index=False)
    refined_medians.to_csv(paths["stage_feature_medians"], index=False)
    if is_stage2(stage):
        paths["stage2_share"] = tables_dir / "table_regime_share_stage2.csv"
        paths["stage2_unknown_monthly"] = tables_dir / "table_unknown_monthly_share_stage2.csv"
        paths["stage2_feature_medians"] = tables_dir / "table_regime_feature_medians_stage2.csv"
        share.to_csv(paths["stage2_share"], index=False)
        unknown_monthly.to_csv(paths["stage2_unknown_monthly"], index=False)
        refined_medians.to_csv(paths["stage2_feature_medians"], index=False)
    return paths


def save_stage2_stability_figures(tables_dir: Path, figures_dir: Path, *, stage: str | None = None, namespace: str | None = None) -> dict[str, Path]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    counts_path = tables_dir / namespaced_name("table_regime_counts_by_symbol_month", namespace, suffix=".csv")
    unknown_daily_path = tables_dir / namespaced_name("table_unknown_daily_share_refined", namespace, suffix=".csv")
    counts = pd.read_csv(counts_path) if counts_path.exists() else pd.DataFrame()
    unknown_daily = pd.read_csv(unknown_daily_path) if unknown_daily_path.exists() else pd.DataFrame()

    slug = stage_namespace_slug(stage, namespace)
    regime_share_path = figures_dir / f"regime_share_by_month_{slug}.png"
    plt.figure(figsize=(10, 5))
    if not counts.empty:
        month_totals = counts.groupby("month", dropna=False)["n_rows"].transform("sum")
        current = counts.assign(month_share=counts["n_rows"] / month_totals)
        pivot = current.pivot_table(index="month", columns="regime", values="month_share", fill_value=0.0)
        for regime in pivot.columns:
            plt.plot(pivot.index.astype(str), pivot[regime], marker="o", linewidth=1.5, label=str(regime))
        plt.legend(loc="best", fontsize=7, ncol=2)
    plt.xlabel("Month")
    plt.ylabel("Share")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(regime_share_path)
    plt.close()

    unknown_share_path = figures_dir / f"unknown_share_by_day_{slug}.png"
    plt.figure(figsize=(11, 4))
    if not unknown_daily.empty:
        plt.plot(unknown_daily["date"].astype(str), unknown_daily["unknown_share"], linewidth=1.0)
        step = max(1, len(unknown_daily) // 12)
        plt.xticks(range(0, len(unknown_daily), step), unknown_daily["date"].iloc[::step], rotation=45, ha="right")
    plt.xlabel("Day")
    plt.ylabel("UNKNOWN share")
    plt.tight_layout()
    plt.savefig(unknown_share_path)
    plt.close()
    return {f"{slug}_regime_share_figure": regime_share_path, f"{slug}_unknown_daily_figure": unknown_share_path}


def save_regime_calendar(frame: pd.DataFrame, figures_dir: Path, symbol: str) -> Path:
    figures_dir.mkdir(parents=True, exist_ok=True)
    current = frame.copy()
    current["date"] = pd.to_datetime(current["event_time"], utc=True).dt.date.astype(str)
    counts = current.groupby(["date", "regime"]).size().unstack(fill_value=0)
    dominance = counts.idxmax(axis=1)
    regime_codes = {regime: idx for idx, regime in enumerate(sorted(dominance.unique()))}
    encoded = dominance.map(regime_codes).to_numpy().reshape(1, -1)
    plt.figure(figsize=(max(8, len(encoded[0]) / 8), 2.5))
    plt.imshow(encoded, aspect="auto")
    plt.yticks([])
    plt.xticks(range(len(dominance)), dominance.index, rotation=90, fontsize=6)
    plt.title(f"Regime calendar {symbol}")
    plt.tight_layout()
    path = figures_dir / f"regime_calendar_{symbol}.png"
    plt.savefig(path)
    plt.close()
    return path


def save_regime_share(frame: pd.DataFrame, path: Path) -> Path:
    share = frame["regime"].value_counts(dropna=False).rename_axis("regime").reset_index(name="n_rows")
    share["share"] = share["n_rows"] / max(len(frame), 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    share.to_csv(path, index=False)
    return path


def save_unknown_daily_share(frame: pd.DataFrame, path: Path) -> Path:
    current = frame[["event_time", "regime"]].copy()
    current["date"] = pd.to_datetime(current["event_time"], utc=True).dt.date.astype(str)
    current["is_unknown"] = current["regime"].eq("UNKNOWN")
    daily = current.groupby("date", dropna=False)["is_unknown"].mean().reset_index(name="unknown_share")
    path.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(path, index=False)
    return path


def save_regime_run_lengths(frame: pd.DataFrame, path: Path) -> Path:
    regimes = frame["regime"].astype(str).reset_index(drop=True)
    run_id = regimes.ne(regimes.shift()).cumsum()
    runs = pd.DataFrame({"regime": regimes, "run_id": run_id}).groupby(["run_id", "regime"], dropna=False).size().reset_index(name="run_length")
    summary = runs.groupby("regime", dropna=False)["run_length"].agg(
        n_runs="count",
        mean_run_length="mean",
        p50_run_length=lambda values: float(np.quantile(values, 0.50)),
        p90_run_length=lambda values: float(np.quantile(values, 0.90)),
        p99_run_length=lambda values: float(np.quantile(values, 0.99)),
        max_run_length="max",
    ).reset_index()
    path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(path, index=False)
    return path


def save_refined_feature_medians(frame: pd.DataFrame, path: Path) -> Path:
    columns = [
        "rel_spread",
        "total_depth_10",
        "vol_score",
        "liquidity_drought_score",
        "adverse_selection_score",
        "liquidity_score",
        "stress_score",
        "directional_toxicity_score",
    ]
    available = [column for column in columns if column in frame.columns]
    medians = frame.groupby("regime", dropna=False)[available].median().reset_index()
    path.parent.mkdir(parents=True, exist_ok=True)
    medians.to_csv(path, index=False)
    return path


def save_transition_map(frame: pd.DataFrame, figures_dir: Path) -> Path:
    figures_dir.mkdir(parents=True, exist_ok=True)
    sample = frame.sample(n=min(100000, len(frame)), random_state=7)
    plt.figure(figsize=(7, 5))
    regimes = sorted(sample["regime"].astype(str).unique())
    for regime in regimes:
        current = sample[sample["regime"].astype(str).eq(regime)]
        plt.scatter(current["liquidity_score"], current["stress_score"], s=2, alpha=0.2, label=regime)
    plt.xlabel("liquidity_score")
    plt.ylabel("stress_score")
    plt.legend(loc="best", fontsize=6, ncol=2)
    plt.tight_layout()
    path = figures_dir / "regime_transition_map_refined.png"
    plt.savefig(path)
    plt.close()
    return path


def save_residual_projection(projection: pd.DataFrame, figures_dir: Path) -> Path:
    figures_dir.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 5))
    if not projection.empty:
        for regime in sorted(projection["regime"].astype(str).unique()):
            current = projection[projection["regime"].astype(str).eq(regime)]
            plt.scatter(current["pca_x"], current["pca_y"], s=3, alpha=0.25, label=regime)
        plt.legend(loc="best", fontsize=7)
    plt.xlabel("PCA-1")
    plt.ylabel("PCA-2")
    plt.tight_layout()
    path = figures_dir / "residual_cluster_projection.png"
    plt.savefig(path)
    plt.close()
    return path


def _collect_feature_medians(lazy: pl.LazyFrame, columns: list[str]) -> pd.DataFrame:
    available = [column for column in columns if column in lazy.collect_schema().names()]
    return (
        lazy.group_by("regime")
        .agg([pl.col(column).median().alias(column) for column in available])
        .sort("regime")
        .collect(engine="streaming")
        .to_pandas()
    )


def _run_length_summary(regime_path: Path) -> pd.DataFrame:
    runs = (
        pl.scan_parquet(str(regime_path))
        .select(["regime"])
        .with_columns((pl.col("regime") != pl.col("regime").shift(1)).fill_null(True).cum_sum().alias("run_id"))
        .group_by(["run_id", "regime"])
        .agg(pl.len().alias("run_length"))
        .group_by("regime")
        .agg(
            [
                pl.len().alias("n_runs"),
                pl.col("run_length").mean().alias("mean_run_length"),
                pl.col("run_length").quantile(0.50, interpolation="linear").alias("p50_run_length"),
                pl.col("run_length").quantile(0.90, interpolation="linear").alias("p90_run_length"),
                pl.col("run_length").quantile(0.99, interpolation="linear").alias("p99_run_length"),
                pl.col("run_length").max().alias("max_run_length"),
            ]
        )
        .sort("regime")
        .collect(engine="streaming")
        .to_pandas()
    )
    return runs
