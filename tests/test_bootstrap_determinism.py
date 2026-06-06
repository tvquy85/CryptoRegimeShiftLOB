from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


def _load_bootstrap_script():
    script = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_execution_ci.py"
    spec = importlib.util.spec_from_file_location("bootstrap_execution_ci", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _trades(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_time": [item[0] for item in rows],
            "gross_pnl": [item[1] + 0.1 for item in rows],
            "net_pnl": [item[1] for item in rows],
            "total_cost": [0.1 for _ in rows],
        }
    )


def _write_policy(path: Path, rows: list[tuple[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _trades(rows).to_parquet(path, index=False)


def test_execution_bootstrap_is_deterministic_under_fixed_seed(tmp_path: Path) -> None:
    module = _load_bootstrap_script()
    backtests = tmp_path / "backtests"
    _write_policy(
        backtests / "demo_rsep_full_tuned_trades.parquet",
        [
            ("2024-01-01T00:00:00Z", 1.0),
            ("2024-01-01T00:01:00Z", 2.0),
            ("2024-01-02T00:00:00Z", -1.0),
        ],
    )
    _write_policy(
        backtests / "demo_cost_aware_threshold_tuned_trades.parquet",
        [
            ("2024-01-01T00:00:00Z", 0.5),
            ("2024-01-03T00:00:00Z", -0.5),
        ],
    )
    _write_policy(
        backtests / "demo_naive_threshold_tuned_trades.parquet",
        [
            ("2024-01-02T00:00:00Z", -2.0),
        ],
    )

    first = module.build_bootstrap_table(
        backtests_dir=backtests,
        models=["demo"],
        policies=["naive_threshold", "cost_aware_threshold", "RSEP-full"],
        seed=7,
        n_bootstrap=200,
    )
    second = module.build_bootstrap_table(
        backtests_dir=backtests,
        models=["demo"],
        policies=["naive_threshold", "cost_aware_threshold", "RSEP-full"],
        seed=7,
        n_bootstrap=200,
    )
    pd.testing.assert_frame_equal(first, second)


def test_execution_bootstrap_unit_is_day_not_trade(tmp_path: Path) -> None:
    module = _load_bootstrap_script()
    rows = [("2024-01-01T00:00:00Z", 0.1)] * 100 + [("2024-01-02T00:00:00Z", -5.0)]
    trades = _trades(rows)
    daily = module.daily_execution_frame(module.read_trade_artifact(_write_temp_parquet(tmp_path, trades)))
    assert len(daily) == 2
    assert daily.loc["2024-01-01", "n_trades"] == 100
    assert daily.loc["2024-01-01", "net_pnl"] == pytest.approx(10.0)


def test_paired_differences_use_union_days_and_zero_fill(tmp_path: Path) -> None:
    module = _load_bootstrap_script()
    left = module.daily_execution_frame(
        _trades(
            [
                ("2024-01-01T00:00:00Z", 3.0),
                ("2024-01-02T00:00:00Z", -1.0),
            ]
        ),
        all_days=["2024-01-01", "2024-01-02", "2024-01-03"],
    )
    right = module.daily_execution_frame(
        _trades(
            [
                ("2024-01-01T00:00:00Z", 1.0),
                ("2024-01-03T00:00:00Z", 4.0),
            ]
        ),
        all_days=["2024-01-01", "2024-01-02", "2024-01-03"],
    )
    row = module.bootstrap_difference_row(
        model="demo",
        left_policy="RSEP-full",
        right_policy="cost_aware_threshold",
        left_daily=left,
        right_daily=right,
        seed=7,
        n_bootstrap=200,
    )
    assert row["diff_target"] == "rsep_minus_cost_aware"
    assert row["n_days"] == 3
    assert row["net_pnl_mean"] == -3.0


def test_net_per_trade_handles_no_trade_policy() -> None:
    module = _load_bootstrap_script()
    daily = module.daily_execution_frame(
        pd.DataFrame(columns=["event_time", "gross_pnl", "net_pnl", "total_cost", "day"]),
        all_days=["2024-01-01", "2024-01-02"],
    )
    row = module.bootstrap_policy_row(
        model="demo",
        policy="RSEP-full",
        daily=daily,
        source_artifact=Path("empty.parquet"),
        seed=7,
        n_bootstrap=100,
    )
    assert row["n_trades"] == 0
    assert row["net_per_trade_mean"] == 0.0
    assert row["net_per_trade_ci_low"] == 0.0
    assert row["net_per_trade_ci_high"] == 0.0


def test_bootstrap_builder_reads_only_saved_trade_artifacts(tmp_path: Path) -> None:
    module = _load_bootstrap_script()
    backtests = tmp_path / "only_backtests"
    for policy, token in module.POLICY_FILE_TOKENS.items():
        _write_policy(backtests / f"demo_{token}_tuned_trades.parquet", [("2024-01-01T00:00:00Z", -1.0)])
    table = module.build_bootstrap_table(
        backtests_dir=backtests,
        models=["demo"],
        policies=list(module.DEFAULT_POLICIES),
        seed=7,
        n_bootstrap=50,
    )
    assert not table.empty
    assert set(table["row_type"]) == {"policy", "difference"}


def _write_temp_parquet(tmp_path: Path, frame: pd.DataFrame) -> Path:
    path = tmp_path / "trades.parquet"
    frame.to_parquet(path, index=False)
    return path
