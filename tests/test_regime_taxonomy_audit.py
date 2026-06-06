from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from regimes.rule_regime_labeler import fit_thresholds


def _load_regime_audit_script():
    script = Path(__file__).resolve().parents[1] / "scripts" / "24_build_regime_audit.py"
    spec = importlib.util.spec_from_file_location("regime_audit_script", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _frame(rows: int = 30) -> pd.DataFrame:
    regimes = ["UNKNOWN", "CALM_LIQUID", "MOMENTUM_TOXIC", "MILD_LIQUIDITY_STRESS", "BALANCED_TRANSITION"]
    frame = pd.DataFrame(
        {
            "symbol": ["SYNTH-USDT"] * rows,
            "split": (["train"] * (rows // 2)) + (["valid"] * (rows // 4)) + (["test"] * (rows - rows // 2 - rows // 4)),
            "event_time": pd.date_range("2024-01-01", periods=rows, freq="1min", tz="UTC"),
            "regime": [regimes[idx % len(regimes)] for idx in range(rows)],
            "rel_spread": np.linspace(0.001, 0.003, rows),
            "total_depth_10": np.linspace(10.0, 40.0, rows),
            "vol_score": np.linspace(-1.0, 1.0, rows),
            "depth_drop_top10": np.linspace(-0.3, 0.3, rows),
            "spread_z_1m": np.linspace(-1.0, 1.0, rows),
            "momentum_score": np.sin(np.linspace(0, 3.14, rows)),
            "adverse_selection_score": np.linspace(0.0, 1.0, rows),
            "choppiness_score": np.linspace(0.0, 0.5, rows),
            "depth_z_1m": np.linspace(1.0, -1.0, rows),
            "liquidity_drought_score": np.linspace(0.0, 1.0, rows),
        }
    )
    return frame


def test_threshold_fitting_ignores_extreme_rows_after_train_prefix() -> None:
    base = _frame(30)
    changed = base.copy()
    changed.loc[18:, ["vol_score", "rel_spread", "total_depth_10", "adverse_selection_score"]] = 9999.0
    quantiles = {"low": 0.4, "mid": 0.5, "high": 0.7, "very_high": 0.8, "very_low": 0.1}
    assert fit_thresholds(base, train_fraction=0.6, quantiles=quantiles) == fit_thresholds(
        changed, train_fraction=0.6, quantiles=quantiles
    )


def test_regime_counts_by_split_keeps_unknown(tmp_path: Path) -> None:
    module = _load_regime_audit_script()
    path = tmp_path / "predictions.parquet"
    _frame(30).to_parquet(path, index=False)
    counts = module.regime_counts_by_split(path, "SYNTH-USDT")
    assert {"train", "valid", "test"}.issubset(set(counts["split"]))
    assert "UNKNOWN" in set(counts["regime"])
    assert counts["n_rows"].sum() == 30


def test_regime_audit_summary_reports_unknown_share(tmp_path: Path) -> None:
    module = _load_regime_audit_script()
    prediction = tmp_path / "predictions.parquet"
    thresholds = tmp_path / "thresholds.json"
    _frame(20).to_parquet(prediction, index=False)
    thresholds.write_text('{"vol_q40": 0.0, "vol_q70": 1.0}', encoding="utf-8")
    audit = module.regime_audit_summary(prediction, "SYNTH-USDT", thresholds)
    assert audit.loc[0, "unknown_rows"] > 0
    assert audit.loc[0, "unknown_share"] > 0.0
    assert audit.loc[0, "threshold_source"] == "first_60pct_chronological_train_prefix"


def test_regime_sensitivity_is_deterministic() -> None:
    module = _load_regime_audit_script()
    sample = _frame(100)
    first = module.sensitivity_table(sample, "SYNTH-USDT")
    second = module.sensitivity_table(sample, "SYNTH-USDT")
    pd.testing.assert_frame_equal(first, second)
    assert {"baseline", "strict_extremes", "relaxed_extremes"}.issubset(set(first["setting"]))


def test_taxonomy_input_table_excludes_future_or_outcome_columns() -> None:
    module = _load_regime_audit_script()
    table = module.taxonomy_input_table()
    joined = " ".join(table["causal_inputs"].astype(str).tolist()).lower()
    banned = ["future_ret", "label", "prob_", "pnl", "test outcome"]
    assert all(term not in joined for term in banned)
