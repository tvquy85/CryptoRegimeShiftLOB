from __future__ import annotations

import importlib.util
from pathlib import Path

import pyarrow.parquet as pq
import yaml

from data.audit_schema import validate_schema


ROOT = Path(__file__).resolve().parents[1]


def _load_verify_module():
    path = ROOT / "scripts" / "verify_artifacts.py"
    spec = importlib.util.spec_from_file_location("verify_artifacts", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_synthetic_sample_matches_l2_schema() -> None:
    path = ROOT / "sample_data" / "l2_synthetic_sample.parquet"
    parquet = pq.ParquetFile(path)
    schema = validate_schema(parquet.schema_arrow.names, levels=20)
    assert schema["ok"], schema
    assert parquet.metadata.num_rows >= 2_000


def test_smoke_config_uses_public_synthetic_data_only() -> None:
    config = yaml.safe_load((ROOT / "configs" / "repro_smoke.yaml").read_text(encoding="utf-8"))
    assert config["raw_data_root"] == "sample_data"
    assert config["symbols"] == ["SYNTH-USDT"]
    assert config["artifact_namespace"] == "synthetic_smoke"
    assert "full2024" not in str(config["raw_data_root"])
    assert "eth" not in str(config["raw_data_root"]).lower()


def test_verify_artifacts_detects_checksum_mismatch(tmp_path: Path) -> None:
    verify = _load_verify_module()
    (tmp_path / "file.txt").write_text("current\n", encoding="utf-8")
    (tmp_path / "checksums.json").write_text(
        '{"files": [{"path": "file.txt", "sha256": "bad"}]}',
        encoding="utf-8",
    )
    errors = verify._verify_checksums(tmp_path)
    assert any("Checksum mismatch" in error for error in errors)


def test_verify_artifacts_rejects_restricted_checksum_paths(tmp_path: Path) -> None:
    verify = _load_verify_module()
    (tmp_path / "checksums.json").write_text(
        '{"files": [{"path": "data/full2024/BOOK_BINANCE_BTC-USDT_JAN-2024.parquet", "sha256": "x"}]}',
        encoding="utf-8",
    )
    errors = verify._validate_checksum_scope(tmp_path)
    assert any("Restricted path" in error for error in errors)


def test_smoke_script_calls_full_reproducibility_chain() -> None:
    script = (ROOT / "scripts" / "run_smoke_pipeline.sh").read_text(encoding="utf-8")
    for command in [
        "00_audit_data.py",
        "01_build_features.py",
        "02_label_regimes.py",
        "03_make_splits.py",
        "04_train_forecasters.py",
        "05_backtest_forecasts.py",
        "06_run_rsep.py",
        "09_tune_execution_policies.py",
        "07_run_stress_grid.py",
        "08_generate_report_pack.py",
        "verify_artifacts.py --require-smoke-outputs",
    ]:
        assert command in script


def test_powershell_smoke_script_matches_required_chain() -> None:
    script = (ROOT / "scripts" / "run_smoke_pipeline.ps1").read_text(encoding="utf-8")
    for command in [
        "00_audit_data.py",
        "01_build_features.py",
        "02_label_regimes.py",
        "03_make_splits.py",
        "04_train_forecasters.py",
        "05_backtest_forecasts.py",
        "06_run_rsep.py",
        "09_tune_execution_policies.py",
        "07_run_stress_grid.py",
        "08_generate_report_pack.py",
        "verify_artifacts.py --require-smoke-outputs",
    ]:
        assert command in script
