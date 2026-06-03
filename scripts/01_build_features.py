from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data.crypto_lake_loader import load_snapshots
from features.feature_store import build_feature_and_label_frames
from utils.artifacts import artifact_namespace, namespaced_dir
from utils.cli import as_common_args, common_parser
from utils.config import load_config, resolve_path
from utils.io import merge_parquet_parts, write_frame, write_run_metadata
from utils.logging import configure_logging
from utils.partitioning import partitioned_stage_enabled, stage_partitions


def main() -> None:
    parser = common_parser("Tạo feature store causal và label cost-aware.")
    args = as_common_args(parser.parse_args())
    config = load_config(args.config)
    logger = configure_logging(resolve_path(config, f"outputs/logs/{args.run_id}/features.log"))
    feature_path = resolve_path(config, str(config["feature_output"]))
    label_path = resolve_path(config, str(config["labels_output"]))
    partition_mode = partitioned_stage_enabled(config, args.stage, start=args.start, end=args.end)
    if partition_mode:
        n_features, n_labels, part_artifacts = _build_partitioned_features(
            config,
            args,
            logger,
            feature_path=feature_path,
            label_path=label_path,
        )
    else:
        raw = load_snapshots(config, args.stage, symbol=args.symbol, start=args.start, end=args.end)
        if raw.empty:
            raise RuntimeError("Không có dữ liệu snapshot cho feature pipeline.")
        features, labels = build_feature_and_label_frames(raw, config)
        write_frame(features, feature_path)
        write_frame(labels, label_path)
        n_features = int(len(features))
        n_labels = int(len(labels))
        part_artifacts = {}
    write_run_metadata(
        config,
        args.run_id,
        args.stage,
        "01_build_features.py",
        artifacts={"features": feature_path, "labels": label_path, **part_artifacts},
        extra={"n_features": n_features, "n_labels": n_labels, "partition_mode": partition_mode},
    )
    logger.info("Đã ghi %s feature rows và %s label rows.", n_features, n_labels)


def _build_partitioned_features(
    config: dict[str, object],
    args,
    logger,
    *,
    feature_path: Path,
    label_path: Path,
) -> tuple[int, int, dict[str, Path]]:
    partitions = stage_partitions(config, args.stage)
    if not partitions:
        raise RuntimeError("Thiếu stage partition hợp lệ cho partitioned feature build.")
    namespace = artifact_namespace(config)
    part_root = namespaced_dir(resolve_path(config, "data/interim/feature_parts"), namespace)
    part_root.mkdir(parents=True, exist_ok=True)
    feature_part_paths: list[Path] = []
    label_part_paths: list[Path] = []

    for partition in partitions:
        feature_part_path = part_root / f"features_{args.stage}_{partition.token.lower()}.parquet"
        label_part_path = part_root / f"labels_{args.stage}_{partition.token.lower()}.parquet"
        if bool(config.get("reuse_partitioned_feature_parts", True)) and feature_part_path.exists() and label_part_path.exists():
            feature_part_paths.append(feature_part_path)
            label_part_paths.append(label_part_path)
            logger.info("Tái sử dụng feature/label partition %s đã có.", partition.token)
            continue
        logger.info("Đang build feature partition %s: %s -> %s.", partition.token, partition.start, partition.end)
        raw = load_snapshots(
            config,
            args.stage,
            symbol=args.symbol,
            start=str(partition.start),
            end=str(partition.end),
        )
        if raw.empty:
            logger.warning("Partition %s rỗng, bỏ qua.", partition.token)
            continue
        features, labels = build_feature_and_label_frames(raw, config)
        write_frame(features, feature_part_path)
        write_frame(labels, label_part_path)
        feature_part_paths.append(feature_part_path)
        label_part_paths.append(label_part_path)
        logger.info("Partition %s xong: %s feature rows, %s label rows.", partition.token, len(features), len(labels))

    if not feature_part_paths or not label_part_paths:
        raise RuntimeError("Không build được partition feature/label nào.")
    _, n_features = merge_parquet_parts(feature_part_paths, feature_path)
    _, n_labels = merge_parquet_parts(label_part_paths, label_path)
    artifacts = {
        **{f"feature_part_{idx:02d}": path for idx, path in enumerate(feature_part_paths, start=1)},
        **{f"label_part_{idx:02d}": path for idx, path in enumerate(label_part_paths, start=1)},
    }
    return n_features, n_labels, artifacts


if __name__ == "__main__":
    main()
