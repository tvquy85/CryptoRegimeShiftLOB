from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data.audit_schema import book_columns, validate_schema


CHECKSUM_PATH = "checksums.json"
REQUIRED_PUBLIC_FILES = [
    "README.md",
    "ARTIFACTS.md",
    "DATA_CARD.md",
    "REPRODUCIBILITY.md",
    "SCHEMA.md",
    "configs/repro_smoke.yaml",
    "configs/rsep_grid.yaml",
    "docs/l2_replay_spec.md",
    "docs/rsep_spec.md",
    "sample_data/l2_synthetic_sample.parquet",
    "sample_data/BOOK_BINANCE_SYNTH-USDT_JAN-2024.parquet",
    "scripts/create_synthetic_l2_sample.py",
    "scripts/run_smoke_pipeline.sh",
    "scripts/run_smoke_pipeline.ps1",
    "scripts/verify_artifacts.py",
]
PUBLIC_PAPER_ASSETS = [
    "outputs/paper_assets/table_1_dataset_stats.csv",
    "outputs/paper_assets/table_2_regime_distribution.csv",
    "outputs/paper_assets/table_3_forecasting_by_regime.csv",
    "outputs/paper_assets/table_4_forecast_to_execution.csv",
    "outputs/paper_assets/table_5_robust_policy.csv",
    "outputs/paper_assets/table_6_ablation.csv",
    "outputs/paper_assets/table_7_model_comparison.csv",
    "outputs/paper_assets/table_8_model_forecasting_execution_comparison.csv",
    "outputs/paper_assets/table_9_model_stress_comparison.csv",
    "outputs/paper_assets/table_10_model_robustness_comparison.csv",
    "outputs/paper_assets/table_11_acceptance_bar.csv",
    "outputs/paper_assets/table_12_claim_support_matrix.csv",
    "outputs/paper_assets/table_13_claim_to_evidence_map.csv",
    "outputs/paper_assets/table_14_number_consistency_check.csv",
    "outputs/paper_assets/table_15_reproducibility_checklist.csv",
    "outputs/paper_assets/table_18_default_benchmark_configuration.csv",
    "outputs/paper_assets/table_19_chronological_split_audit.csv",
    "outputs/paper_assets/table_20_rsep_term_mapping.csv",
    "outputs/paper_assets/table_21_deep_baseline_status.csv",
    "outputs/paper_assets/table_22_execution_ci_stage3.csv",
    "outputs/paper_assets/table_23_regime_taxonomy_inputs.csv",
    "outputs/paper_assets/table_24_regime_counts_by_asset_split.csv",
    "outputs/paper_assets/table_25_regime_sensitivity.csv",
    "outputs/paper_assets/table_26_cross_asset_distribution_shift.csv",
    "outputs/paper_assets/table_27_cross_asset_label_regime_calibration.csv",
    "outputs/paper_assets/table_28_reference_audit_summary.csv",
    "outputs/paper_assets/table_baseline_coverage.csv",
    "outputs/paper_assets/table_rsep_ablation_artifact_summary.csv",
    "outputs/paper_assets/fig_4_fee_stress.png",
    "outputs/paper_assets/fig_5_latency_decay.png",
    "outputs/paper_assets/fig_6_worst_regime.png",
    "outputs/paper_assets/fig_7_model_fee_stress.png",
    "outputs/paper_assets/fig_8_model_latency_stress.png",
]
SMOKE_OUTPUTS = [
    "data/interim/audit/audit_by_day_synthetic_smoke.parquet",
    "data/features/features_synthetic_smoke.parquet",
    "data/labels/labels_synthetic_smoke.parquet",
    "data/regimes/regimes_synthetic_smoke.parquet",
    "data/splits/splits_synthetic_smoke.parquet",
    "data/predictions/predictions_synthetic_smoke.parquet",
    "outputs/tables/table_forecasting_overall_stage0_synthetic_smoke_sgd_synthetic_smoke.csv",
    "outputs/tables/table_policy_tuning_stage0_synthetic_smoke.csv",
    "outputs/tables/table_stress_grid_tuned_stage0_synthetic_smoke.csv",
    "outputs/smoke/paper_assets/failure_case_studies.csv",
]
RESTRICTED_PATTERNS = [
    "data/full2024/",
    "data/eth/",
    "../data/full2024/",
    "../data/eth/",
    "data/predictions/",
    "data/backtests/",
    "outputs/checkpoints/",
    "outputs/logs/",
]
RESTRICTED_SUFFIXES = {".pt", ".ckpt", ".joblib", ".tmp"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify public reproducibility artifacts.")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--write-checksums", action="store_true")
    parser.add_argument("--require-smoke-outputs", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()

    errors: list[str] = []
    for relative in REQUIRED_PUBLIC_FILES:
        if not (root / relative).exists():
            errors.append(f"Missing required public artifact: {relative}")
    errors.extend(_validate_smoke_config(root))
    errors.extend(_validate_sample(root))

    checksum_entries = _checksum_file_list(root)
    if args.write_checksums:
        _write_checksums(root, checksum_entries)
    errors.extend(_verify_checksums(root))
    if args.require_smoke_outputs:
        errors.extend(_verify_smoke_outputs(root))
    errors.extend(_validate_checksum_scope(root))

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        raise SystemExit(1)
    print("[PASS] Reproducibility artifact pack is complete.")


def _checksum_file_list(root: Path) -> list[str]:
    candidates = [*REQUIRED_PUBLIC_FILES, *PUBLIC_PAPER_ASSETS]
    return [relative for relative in candidates if (root / relative).exists()]


def _write_checksums(root: Path, relatives: list[str]) -> None:
    payload = {
        "manifest_version": 1,
        "hash_algorithm": "sha256",
        "scope": "public reproducibility artifacts only; restricted raw data and large derived artifacts excluded",
        "files": [
            {"path": relative, "sha256": _sha256(root / relative), "bytes": (root / relative).stat().st_size}
            for relative in sorted(relatives)
        ],
    }
    (root / CHECKSUM_PATH).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _verify_checksums(root: Path) -> list[str]:
    path = root / CHECKSUM_PATH
    if not path.exists():
        return [f"Missing checksum manifest: {CHECKSUM_PATH}"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for entry in payload.get("files", []):
        relative = str(entry.get("path", "")).replace("\\", "/")
        current = root / relative
        if not current.exists():
            errors.append(f"Checksum target missing: {relative}")
            continue
        expected = str(entry.get("sha256", ""))
        actual = _sha256(current)
        if actual != expected:
            errors.append(f"Checksum mismatch for {relative}: expected {expected}, got {actual}")
    return errors


def _validate_checksum_scope(root: Path) -> list[str]:
    path = root / CHECKSUM_PATH
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for entry in payload.get("files", []):
        relative = str(entry.get("path", "")).replace("\\", "/")
        if any(relative.startswith(pattern) for pattern in RESTRICTED_PATTERNS):
            errors.append(f"Restricted path must not be checksummed for public release: {relative}")
        if Path(relative).suffix.lower() in RESTRICTED_SUFFIXES:
            errors.append(f"Restricted file type must not be checksummed for public release: {relative}")
    return errors


def _validate_smoke_config(root: Path) -> list[str]:
    path = root / "configs/repro_smoke.yaml"
    if not path.exists():
        return []
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    errors: list[str] = []
    raw_root = str(config.get("raw_data_root", "")).replace("\\", "/")
    if "full2024" in raw_root or raw_root in {"data/eth", "../data/eth"}:
        errors.append("Smoke config must not point to restricted raw data.")
    if config.get("artifact_namespace") != "synthetic_smoke":
        errors.append("Smoke config must use artifact_namespace=synthetic_smoke.")
    if config.get("symbols") != ["SYNTH-USDT"]:
        errors.append("Smoke config must use symbol SYNTH-USDT.")
    return errors


def _validate_sample(root: Path) -> list[str]:
    path = root / "sample_data/l2_synthetic_sample.parquet"
    if not path.exists():
        return []
    errors: list[str] = []
    parquet = pq.ParquetFile(path)
    columns = parquet.schema_arrow.names
    schema = validate_schema(columns, levels=20)
    if not schema["ok"]:
        errors.append(f"Synthetic L2 sample schema missing columns: {schema['missing']}")
    if parquet.metadata.num_rows < 2_000:
        errors.append("Synthetic L2 sample is too small for smoke split/horizon checks.")
    sample = pd.read_parquet(path, columns=["symbol", "exchange", "bid_0_price", "ask_0_price"])
    if set(sample["symbol"].dropna().unique()) != {"SYNTH-USDT"}:
        errors.append("Synthetic L2 sample symbol must be SYNTH-USDT.")
    if set(sample["exchange"].dropna().unique()) != {"BINANCE"}:
        errors.append("Synthetic L2 sample exchange must be BINANCE.")
    if (sample["bid_0_price"] > sample["ask_0_price"]).any():
        errors.append("Synthetic L2 sample contains crossed best books.")
    expected = set(book_columns(20))
    extra = set(columns) - expected
    if extra:
        errors.append(f"Synthetic L2 sample has unexpected raw columns: {sorted(extra)}")
    return errors


def _verify_smoke_outputs(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in SMOKE_OUTPUTS:
        path = root / relative
        if not path.exists():
            errors.append(f"Missing smoke output: {relative}")
            continue
        if path.stat().st_size <= 0:
            errors.append(f"Smoke output is empty: {relative}")
    prediction_path = root / "data/predictions/predictions_synthetic_smoke.parquet"
    if prediction_path.exists():
        required = {"split", "label", "regime", "prob_down", "prob_flat", "prob_up", "pred_label"}
        columns = set(pq.ParquetFile(prediction_path).schema_arrow.names)
        missing = sorted(required - columns)
        if missing:
            errors.append(f"Smoke predictions missing required columns: {missing}")
    return errors


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


if __name__ == "__main__":
    main()
