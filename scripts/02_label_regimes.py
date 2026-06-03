from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import polars as pl
import pandas as pd

from regimes.cluster_regime_labeler import residual_cluster_alignment
from regimes.regime_diagnostics import (
    save_partitioned_regime_tables,
    save_regime_calendar,
    save_regime_tables,
    save_residual_projection,
    save_stage2_stability_figures,
    save_transition_map,
)
from regimes.rule_regime_labeler import (
    apply_rule_regimes,
    fit_thresholds,
    fit_thresholds_from_parquet,
    save_thresholds,
)
from utils.artifacts import artifact_namespace, namespaced_dir, namespaced_name
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.io import merge_parquet_parts, read_frame, write_frame, write_run_metadata
from utils.logging import configure_logging
from utils.partitioning import partitioned_stage_enabled, stage_partitions


def main() -> None:
    parser = common_parser("Gán regime rule-based và sinh diagnostics.")
    args = as_common_args(parser.parse_args())
    config = load_config(args.config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/regimes.log"))
    label_path = resolve_path(config, str(config["labels_output"]))
    regime_path = resolve_path(config, str(config["regime_output"]))
    thresholds_path = resolve_path(config, str(config["thresholds_output"]))
    namespace = artifact_namespace(config)
    partition_mode = partitioned_stage_enabled(config, args.stage, start=args.start, end=args.end)
    if partition_mode:
        thresholds = fit_thresholds_from_parquet(
            label_path,
            train_fraction=float(config.get("train_fraction_for_thresholds", 0.6)),
            quantiles=config.get("quantiles", {}),
        )
        save_thresholds(thresholds, thresholds_path)
        part_root = namespaced_dir(resolve_path(config, "data/interim/regime_parts"), namespace)
        part_root.mkdir(parents=True, exist_ok=True)
        regime_part_paths = []
        label_part_root = namespaced_dir(resolve_path(config, "data/interim/feature_parts"), namespace)
        for partition in stage_partitions(config, args.stage):
            label_part_path = label_part_root / f"labels_{args.stage}_{partition.token.lower()}.parquet"
            if not label_part_path.exists():
                logger.warning("Thiếu label part %s, bỏ qua.", label_part_path.name)
                continue
            labels = read_frame(label_part_path)
            regimes = apply_rule_regimes(labels, thresholds)
            part_path = part_root / f"regimes_{args.stage}_{partition.token.lower()}.parquet"
            write_frame(regimes, part_path)
            regime_part_paths.append(part_path)
            logger.info("Gán regime partition %s xong: %s dòng.", partition.token, len(regimes))
        if not regime_part_paths:
            raise RuntimeError("Không có regime part nào được sinh.")
        merge_parquet_parts(regime_part_paths, regime_path)
        table_paths = save_partitioned_regime_tables(regime_path, resolve_path(config, "outputs/tables"), stage=args.stage, namespace=namespace)
        stability_figures = save_stage2_stability_figures(
            resolve_path(config, "outputs/tables"),
            resolve_path(config, "outputs/figures"),
            stage=args.stage,
            namespace=namespace,
        )
        residual_sample = _residual_sample_from_parquet(
            regime_path,
            [
                "liquidity_score",
                "stress_score",
                "directional_toxicity_score",
                "choppiness_score",
                "liquidity_drought_score",
            ],
            sample_size=int(config.get("hybrid_taxonomy", {}).get("diagnostic_sample_size", 200000)),
        )
        regime_counts = pd.read_csv(table_paths["stage_share"]).set_index("regime")["n_rows"].to_dict()
        extra_artifacts = {
            **{f"regime_part_{idx:02d}": path for idx, path in enumerate(regime_part_paths, start=1)},
            **stability_figures,
        }
    else:
        labels = read_frame(label_path)
        thresholds = fit_thresholds(
            labels,
            train_fraction=float(config.get("train_fraction_for_thresholds", 0.6)),
            quantiles=config.get("quantiles", {}),
        )
        regimes = apply_rule_regimes(labels, thresholds)
        write_frame(regimes, regime_path)
        save_thresholds(thresholds, thresholds_path)
        table_paths = save_regime_tables(regimes, resolve_path(config, "outputs/tables"), namespace=namespace, stage=args.stage)
        symbol = args.symbol or str(regimes["symbol"].dropna().iloc[0])
        figure_path = save_regime_calendar(regimes, resolve_path(config, "outputs/figures"), symbol)
        transition_map = save_transition_map(regimes, resolve_path(config, "outputs/figures"))
        residual_sample = regimes
        regime_counts = regimes["regime"].value_counts().to_dict()
        extra_artifacts = {"calendar": figure_path, "transition_map": transition_map}
    cluster_columns = [
        "liquidity_score",
        "stress_score",
        "directional_toxicity_score",
        "choppiness_score",
        "liquidity_drought_score",
    ]
    hybrid_cfg = config.get("hybrid_taxonomy", {})
    alignment, projection = residual_cluster_alignment(
        residual_sample,
        [column for column in cluster_columns if column in residual_sample.columns],
        sample_size=int(hybrid_cfg.get("diagnostic_sample_size", 200000)),
        random_state=int(hybrid_cfg.get("random_seed", 7)),
    )
    alignment_path = resolve_path(config, f"outputs/tables/{namespaced_name('table_residual_cluster_alignment', namespace, suffix='.csv')}")
    projection_path = resolve_path(config, f"data/reports/{namespaced_name('residual_cluster_projection', namespace, suffix='.parquet')}")
    write_frame(alignment, alignment_path.with_suffix(".parquet"))
    alignment.to_csv(alignment_path, index=False)
    write_frame(projection, projection_path)
    projection_figure = save_residual_projection(projection, resolve_path(config, "outputs/figures"))
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "02_label_regimes.py",
        artifacts={
            "regimes": regime_path,
            "thresholds": thresholds_path,
            "cluster_alignment": alignment_path,
            "cluster_projection_data": projection_path,
            "cluster_projection_figure": projection_figure,
            **extra_artifacts,
            **table_paths,
        },
        extra={"regime_counts": regime_counts, "partition_mode": partition_mode},
    )
    logger.info("Đã gán regime xong cho stage %s.", args.stage)


def _residual_sample_from_parquet(path: Path, columns: list[str], sample_size: int) -> pd.DataFrame:
    selected = ["regime", *columns]
    return (
        pl.scan_parquet(str(path))
        .filter(pl.col("regime").is_in(["BALANCED_TRANSITION", "MILD_LIQUIDITY_STRESS", "UNKNOWN"]))
        .select(selected)
        .head(sample_size)
        .collect(engine="streaming")
        .to_pandas()
    )


if __name__ == "__main__":
    main()
