from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


def _load_script_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "12_build_model_comparative_stress_pack.py"
    spec = importlib.util.spec_from_file_location("comparative_pack_script", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_model_comparative_pack_uses_both_models_without_touching_predictions(tmp_path: Path) -> None:
    module = _load_script_module()
    root = tmp_path
    tables = root / "outputs" / "tables"
    data_predictions = root / "data" / "predictions"
    tables.mkdir(parents=True)
    data_predictions.mkdir(parents=True)
    (data_predictions / "predictions.parquet").write_bytes(b"sgd")
    (data_predictions / "predictions_stage3_xgboost_gpu.parquet").write_bytes(b"xgb")

    pd.DataFrame(
        [
            {"model": "sgd_stage3", "accuracy": 0.55, "macro_f1": 0.46, "mcc": 0.23, "test_rows": 100},
            {"model": "xgboost_gpu_stage3", "accuracy": 0.57, "macro_f1": 0.45, "mcc": 0.24, "test_rows": 100},
        ]
    ).to_csv(tables / "table_model_comparison_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"model": "sgd_stage3", "base_policy": "RSEP-full", "policy": "sgd_stage3_RSEP-full_tuned", "n_trades": 10, "net_pnl": -4.0},
            {
                "model": "xgboost_gpu_stage3",
                "base_policy": "RSEP-full",
                "policy": "xgboost_gpu_stage3_RSEP-full_tuned",
                "n_trades": 12,
                "net_pnl": -3.0,
            },
        ]
    ).to_csv(tables / "table_forecast_to_execution_tuned_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"model": "sgd_stage3", "mean_diff": 1.0, "ci_low": 0.1, "ci_high": 2.0, "n_days": 3, "n_bootstrap": 1000},
            {"model": "xgboost_gpu_stage3", "mean_diff": 0.5, "ci_low": 0.2, "ci_high": 0.8, "n_days": 3, "n_bootstrap": 1000},
        ]
    ).to_csv(tables / "table_rsep_bootstrap_tuned_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"model": "xgboost_gpu_stage3", "axis": "fee_bps", "level": 0.0, "net_pnl": 1.0},
            {"model": "xgboost_gpu_stage3", "axis": "fee_bps", "level": 1.0, "net_pnl": -3.0},
            {"model": "xgboost_gpu_stage3", "axis": "latency_events", "level": 0.0, "net_pnl": -2.0},
            {"model": "xgboost_gpu_stage3", "axis": "latency_events", "level": 1.0, "net_pnl": -3.0},
            {"model": "xgboost_gpu_stage3", "axis": "spread_multiplier", "level": 1.0, "net_pnl": -3.0},
            {"model": "xgboost_gpu_stage3", "axis": "depth_multiplier", "level": 1.0, "net_pnl": -3.0},
        ]
    ).to_csv(tables / "table_stress_grid_tuned_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"model": "sgd_stage3", "axis": "fee_bps", "level": 0.0, "net_pnl": 2.0},
            {"model": "sgd_stage3", "axis": "fee_bps", "level": 1.0, "net_pnl": -4.0},
            {"model": "sgd_stage3", "axis": "latency_events", "level": 0.0, "net_pnl": -2.5},
            {"model": "sgd_stage3", "axis": "latency_events", "level": 1.0, "net_pnl": -4.0},
            {"model": "sgd_stage3", "axis": "spread_multiplier", "level": 1.0, "net_pnl": -4.0},
            {"model": "sgd_stage3", "axis": "depth_multiplier", "level": 1.0, "net_pnl": -4.0},
        ]
    ).to_csv(tables / "table_stress_grid_tuned_stage2.csv", index=False)
    pd.DataFrame(
        [
            {"model": "xgboost_gpu_stage3", "axis": "fee_bps", "robustness_auc": -3.0},
            {"model": "xgboost_gpu_stage3", "axis": "latency_events", "robustness_auc": -2.5},
        ]
    ).to_csv(tables / "table_robustness_summary_tuned_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"model": "sgd_stage3", "axis": "fee_bps", "robustness_auc": -4.0},
            {"model": "sgd_stage3", "axis": "latency_events", "robustness_auc": -3.0},
        ]
    ).to_csv(tables / "table_robustness_summary_tuned_stage2.csv", index=False)

    artifacts = module.build_comparative_pack(root, stage="stage_3_full_scale", models=["sgd_stage3", "xgboost_gpu_stage3"])

    summary = pd.read_csv(artifacts["model_forecasting_execution_comparison"])
    stress = pd.read_csv(artifacts["model_stress_comparison"])
    robustness = pd.read_csv(artifacts["model_robustness_comparison"])
    assert set(summary["model"]) == {"sgd_stage3", "xgboost_gpu_stage3"}
    assert set(stress["model"]) == {"sgd_stage3", "xgboost_gpu_stage3"}
    assert {"fee_bps", "latency_events", "spread_multiplier", "depth_multiplier"}.issubset(set(stress["axis"]))
    assert set(robustness["model"]) == {"sgd_stage3", "xgboost_gpu_stage3"}
    assert artifacts["model_fee_stress_figure"].stat().st_size > 0
    assert artifacts["model_latency_stress_figure"].stat().st_size > 0
    assert (data_predictions / "predictions.parquet").read_bytes() == b"sgd"
    assert (data_predictions / "predictions_stage3_xgboost_gpu.parquet").read_bytes() == b"xgb"
