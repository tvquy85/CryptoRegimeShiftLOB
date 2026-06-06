from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from models.tabular_baselines import train_streaming_sgd


def _load_script_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "25_build_cross_asset_asymmetry_audit.py"
    spec = importlib.util.spec_from_file_location("cross_asset_asymmetry", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prediction_frame(symbol: str, *, scale: float = 1.0, rows: int = 18) -> pd.DataFrame:
    splits = ["train"] * (rows // 3) + ["valid"] * (rows // 3) + ["test"] * (rows - 2 * (rows // 3))
    labels = ["DOWN", "FLAT", "UP"] * (rows // 3)
    regimes = ["UNKNOWN", "CALM_LIQUID", "MOMENTUM_TOXIC"] * (rows // 3)
    frame = pd.DataFrame(
        {
            "symbol": [symbol] * rows,
            "split": splits,
            "label": labels[:rows],
            "regime": regimes[:rows],
            "mid_price": np.linspace(100.0, 118.0, rows) * scale,
            "spread": np.linspace(0.01, 0.03, rows) * scale,
            "rel_spread": np.linspace(0.0001, 0.0003, rows) / scale,
            "bid_0_size": np.linspace(1.0, 2.0, rows) * scale,
            "ask_0_size": np.linspace(1.5, 2.5, rows) * scale,
            "total_depth_10": np.linspace(10.0, 30.0, rows) * scale,
            "realized_vol_20": np.linspace(0.001, 0.003, rows) * scale,
            "realized_vol_100": np.linspace(0.0015, 0.0035, rows) * scale,
            "vol_score": np.linspace(-1.0, 1.0, rows) * scale,
            "future_ret_h": np.linspace(-0.001, 0.001, rows),
            "pred_label": labels[:rows],
            "prob_down": [0.8, 0.1, 0.1] * (rows // 3),
            "prob_flat": [0.1, 0.8, 0.1] * (rows // 3),
            "prob_up": [0.1, 0.1, 0.8] * (rows // 3),
        }
    )
    return frame


def test_distribution_shift_label_and_regime_outputs_keep_unknown(tmp_path: Path) -> None:
    module = _load_script_module()
    btc_path = tmp_path / "btc.parquet"
    eth_path = tmp_path / "eth.parquet"
    _prediction_frame("BTC-USDT", scale=1.0).to_parquet(btc_path, index=False)
    _prediction_frame("ETH-USDT", scale=2.0).to_parquet(eth_path, index=False)

    btc_sample = module.deterministic_sample(btc_path, max_rows=100, seed=7)
    eth_sample = module.deterministic_sample(eth_path, max_rows=100, seed=7)
    distribution = module.add_eth_btc_ratios(
        pd.concat(
            [
                module.distribution_stats_from_sample(btc_sample, symbol="BTC-USDT", sample_seed=7),
                module.distribution_stats_from_sample(eth_sample, symbol="ETH-USDT", sample_seed=7),
            ],
            ignore_index=True,
        )
    )
    paper_distribution = module.paper_distribution_shift(distribution)
    labels = module.exact_label_balance(btc_path, symbol="BTC-USDT", scope="within_asset")
    regimes = module.exact_regime_counts(btc_path, symbol="BTC-USDT", scope="within_asset")

    assert not paper_distribution.empty
    assert "top_of_book_depth" in set(distribution["feature"])
    assert set(labels["label"]) == {"DOWN", "FLAT", "UP"}
    assert "UNKNOWN" in set(regimes["regime"])
    assert regimes["n_rows"].sum() == len(_prediction_frame("BTC-USDT", scale=1.0))


def test_calibration_is_deterministic_and_uses_target_test(tmp_path: Path) -> None:
    module = _load_script_module()
    path = tmp_path / "target.parquet"
    frame = _prediction_frame("ETH-USDT", scale=1.0, rows=18)
    frame.loc[frame["split"] != "test", ["prob_down", "prob_flat", "prob_up"]] = [0.34, 0.33, 0.33]
    frame.to_parquet(path, index=False)

    first = module.calibration_from_parquet(path, direction="btc_to_eth", bins=10)
    second = module.calibration_from_parquet(path, direction="btc_to_eth", bins=10)

    assert first == second
    assert first["n_rows"] == int((frame["split"] == "test").sum())
    assert 0.0 <= first["ece_10bin"] <= 1.0
    assert first["brier_score"] >= 0.0


def test_streaming_sgd_scaler_uses_train_rows_only(tmp_path: Path) -> None:
    source = pd.DataFrame(
        {
            "feature_a": [0.0, 1.0, 2.0, 3.0, 10000.0, 20000.0],
            "feature_b": [1.0, 1.0, 2.0, 2.0, -9999.0, -9999.0],
            "label": ["DOWN", "FLAT", "UP", "DOWN", "FLAT", "UP"],
            "split": ["train", "train", "train", "train", "valid", "test"],
        }
    )
    path = tmp_path / "source.parquet"
    source.to_parquet(path, index=False)

    bundle = train_streaming_sgd(
        path,
        ["feature_a", "feature_b"],
        {"sgd": {"alpha": 0.0001, "streaming_epochs": 1}, "random_seed": 7},
        batch_size=2,
    )
    scaler = bundle.pipeline.named_steps["scaler"]

    np.testing.assert_allclose(scaler.mean_, source[source["split"] == "train"][["feature_a", "feature_b"]].mean().to_numpy())


def test_source_only_protocol_audit_has_no_target_validation_tuning(tmp_path: Path) -> None:
    module = _load_script_module()
    config = tmp_path / "tuned_policy_asset_heldout_stage3.yaml"
    config.write_text(
        """
directions:
  btc_to_eth:
    source_symbol: BTC-USDT
    target_symbol: ETH-USDT
    validation_objective: source_valid_max_net_pnl_with_min_trades_and_min_trade_days
    valid_rows_used_for_tuning: 123
    target_test_rows: 456
    selected_thresholds:
      RSEP-full: 0.01
""",
        encoding="utf-8",
    )
    audit = module.source_only_protocol_audit(config)

    assert audit.loc[0, "validation_objective"].startswith("source_valid")
    assert "source validation only" in audit.loc[0, "policy_tuning_protocol"]
    assert "target test used only" in audit.loc[0, "target_protocol"]
