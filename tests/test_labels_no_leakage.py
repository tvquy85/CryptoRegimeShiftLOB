from __future__ import annotations

import pandas as pd

from features.returns_labels import add_cost_aware_labels


def test_label_uses_future_mid_but_not_future_for_current_cost() -> None:
    frame = pd.DataFrame(
        {
            "mid_price": [100.0, 100.0, 101.0, 102.0],
            "rel_spread": [0.001, 0.001, 0.001, 0.001],
        }
    )
    labeled = add_cost_aware_labels(frame, horizon_events=1, fee_bps=0.0, slippage_buffer_multiplier=0.0)
    assert labeled.loc[0, "future_ret_h"] == 0.0
    assert labeled.loc[1, "future_ret_h"] > 0.0
    assert labeled.loc[1, "cost_threshold_t"] == labeled.loc[0, "cost_threshold_t"]

