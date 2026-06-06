import numpy as np
import pandas as pd

from artifact_lib import ReplayConfig, load_config, make_synthetic_sample, sweep_book


def test_sweep_book_buy_vwap_two_levels_manual():
    cfg = load_config("configs/synthetic.yaml")
    df = make_synthetic_sample(cfg).iloc[[0]].copy()
    row = df.iloc[0].copy()
    row["mid_price"] = 100.0
    for i in range(20):
        row[f"ask_{i}_price"] = 101.0 + i
        row[f"ask_{i}_size"] = 1.0 if i < 2 else 0.0
    rcfg = ReplayConfig(
        trade_notional=150.0,
        fee_bps=1.0,
        latency_rows=0,
        hold_rows=1,
        min_fill_ratio=0.5,
        partial_fill=True,
        spread_multiplier=1.0,
        depth_multiplier=1.0,
        cooldown_rows=0,
    )
    price, qty = sweep_book(row, side=1, cfg=rcfg)
    assert np.isclose(qty, 1.5)
    assert np.isclose(price, (1.0 * 101.0 + 0.5 * 102.0) / 1.5)


def test_partial_fill_rejected_below_min_ratio():
    cfg = load_config("configs/synthetic.yaml")
    row = make_synthetic_sample(cfg).iloc[0].copy()
    row["mid_price"] = 100.0
    for i in range(20):
        row[f"ask_{i}_price"] = 101.0 + i
        row[f"ask_{i}_size"] = 0.01
    rcfg = ReplayConfig(1000.0, 1.0, 0, 1, 0.5, True, 1.0, 1.0, 0)
    price, qty = sweep_book(row, side=1, cfg=rcfg)
    assert price == 0.0
    assert qty == 0.0

