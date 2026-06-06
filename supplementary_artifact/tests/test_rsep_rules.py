from artifact_lib import build_features, load_config, make_labels_regimes_splits, make_synthetic_sample, run_rsep, train_baseline


def test_rsep_outputs_diagnostic_summary():
    cfg = load_config("configs/synthetic.yaml")
    make_synthetic_sample(cfg)
    build_features(cfg)
    make_labels_regimes_splits(cfg)
    train_baseline(cfg)
    summary = run_rsep(cfg)
    assert {"policy", "n_trades", "net_pnl"}.issubset(summary.columns)
    assert summary.iloc[0]["policy"] == "rsep"

