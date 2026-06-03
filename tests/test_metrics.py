from __future__ import annotations

import pandas as pd

from evaluation.robustness_eval import latency_half_life, regime_gap, robustness_auc, worst_regime_return


def test_robustness_metrics_basic() -> None:
    by_regime = pd.DataFrame({"regime": ["A", "B"], "net_pnl": [10.0, -2.0]})
    assert worst_regime_return(by_regime) == -2.0
    assert regime_gap(by_regime) == 12.0
    curve = pd.DataFrame({"level": [0.0, 1.0, 2.0], "net_pnl": [10.0, 5.0, 0.0]})
    assert robustness_auc(curve, "level") == 5.0
    latency = pd.DataFrame({"latency_events": [0, 1, 5], "net_pnl": [10.0, 7.0, 4.0]})
    assert latency_half_life(latency) == 5.0

