import numpy as np

from artifact_lib import build_features, load_config, make_labels_regimes_splits, make_synthetic_sample


def test_cost_aware_label_threshold_formula():
    cfg = load_config("configs/synthetic.yaml")
    make_synthetic_sample(cfg)
    build_features(cfg)
    df = make_labels_regimes_splits(cfg)
    kappa = cfg["labels"]["slippage_buffer_multiplier"]
    fee = cfg["labels"]["fee_bps"]
    expected = (1.0 + kappa) * df["rel_spread"] + fee / 10000.0
    assert np.allclose(df["cost_threshold_t"], expected)
    assert set(df["label"].unique()) <= {"UP", "DOWN", "FLAT"}

