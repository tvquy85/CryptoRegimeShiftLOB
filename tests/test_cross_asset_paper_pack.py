from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


def _load_script_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "21_build_cross_asset_paper_pack.py"
    spec = importlib.util.spec_from_file_location("cross_asset_paper_pack_script", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_inputs(root: Path) -> None:
    tables = root / "outputs" / "tables"
    tables.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "direction": "btc_to_eth",
                "model": "asset_btc_to_eth_sgd",
                "source_symbol": "BTC-USDT",
                "target_symbol": "ETH-USDT",
                "accuracy": 0.43,
                "macro_f1": 0.42,
                "weighted_f1": 0.43,
                "mcc": 0.14,
                "balanced_accuracy": 0.42,
                "n_rows": 100,
            },
            {
                "direction": "eth_to_btc",
                "model": "asset_eth_to_btc_sgd",
                "source_symbol": "ETH-USDT",
                "target_symbol": "BTC-USDT",
                "accuracy": 0.54,
                "macro_f1": 0.48,
                "weighted_f1": 0.53,
                "mcc": 0.24,
                "balanced_accuracy": 0.48,
                "n_rows": 120,
            },
        ]
    ).to_csv(tables / "table_asset_heldout_forecasting_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"direction": "btc_to_eth", "policy": "naive_threshold", "n_trades": 30, "gross_pnl": 8.0, "net_pnl": -20.0, "threshold": 0.8},
            {"direction": "btc_to_eth", "policy": "cost_aware_threshold", "n_trades": 40, "gross_pnl": 9.0, "net_pnl": -30.0, "threshold": 0.1},
            {"direction": "btc_to_eth", "policy": "RSEP-full", "n_trades": 10, "gross_pnl": 4.0, "net_pnl": -8.0, "threshold": 0.2},
            {"direction": "eth_to_btc", "policy": "naive_threshold", "n_trades": 15, "gross_pnl": 3.0, "net_pnl": -10.0, "threshold": 0.6},
            {"direction": "eth_to_btc", "policy": "cost_aware_threshold", "n_trades": 11, "gross_pnl": 2.0, "net_pnl": -6.0, "threshold": 0.1},
            {"direction": "eth_to_btc", "policy": "RSEP-full", "n_trades": 5, "gross_pnl": 1.0, "net_pnl": -2.0, "threshold": 0.2},
        ]
    ).to_csv(tables / "table_asset_heldout_execution_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"direction": "btc_to_eth", "source_symbol": "BTC-USDT", "target_symbol": "ETH-USDT", "model": "asset_btc_to_eth_sgd", "mean_diff": 2.0, "ci_low": 0.5, "ci_high": 4.0, "n_days": 58, "n_bootstrap": 1000},
            {"direction": "eth_to_btc", "source_symbol": "ETH-USDT", "target_symbol": "BTC-USDT", "model": "asset_eth_to_btc_sgd", "mean_diff": 1.0, "ci_low": 0.2, "ci_high": 3.0, "n_days": 65, "n_bootstrap": 1000},
        ]
    ).to_csv(tables / "table_asset_heldout_rsep_bootstrap_stage3.csv", index=False)
    pd.DataFrame(
        [
            {"criterion_id": "C08", "criterion": "Asset-held-out", "status": "PASS"},
            {"criterion_id": "C09", "criterion": "Bootstrap", "status": "PARTIAL"},
        ]
    ).to_csv(tables / "table_acceptance_bar_stage3.csv", index=False)
    pd.DataFrame(
        [
            {
                "claim": "Cross-asset BTC<->ETH forecasting/execution duoc evaluate",
                "status": "SUPPORTED",
                "recommended_paper_wording": "Cross-asset evaluated, not profitability.",
            }
        ]
    ).to_csv(tables / "table_claim_support_matrix_stage3.csv", index=False)


def test_cross_asset_pack_builds_tables_and_narrative_without_predictions(tmp_path: Path) -> None:
    module = _load_script_module()
    root = tmp_path
    predictions = root / "data" / "predictions"
    predictions.mkdir(parents=True)
    (predictions / "predictions.parquet").write_bytes(b"keep")
    _write_inputs(root)

    paths = module.build_cross_asset_paper_pack(root=root, run_id="test_stage3_13")
    combined = pd.read_csv(paths.forecasting_execution)
    bootstrap = pd.read_csv(paths.bootstrap)
    narrative = paths.narrative.read_text(encoding="utf-8")
    audit = paths.audit.read_text(encoding="utf-8")

    assert set(combined["direction"]) == {"btc_to_eth", "eth_to_btc"}
    assert (combined["rsep_loss_reduction_vs_cost_aware"] > 0).all()
    assert set(bootstrap["direction"]) == {"btc_to_eth", "eth_to_btc"}
    assert "giao dịch cross-asset tạo lợi nhuận" in narrative
    assert "profitable cross-asset trading" not in narrative
    assert "RSEP giảm thiệt hại" in narrative
    assert "PASS cho Stage 3.13" in audit
    assert (predictions / "predictions.parquet").read_bytes() == b"keep"
