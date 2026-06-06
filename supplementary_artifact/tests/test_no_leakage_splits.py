from artifact_lib import build_features, load_config, make_labels_regimes_splits, make_synthetic_sample


def test_purged_split_has_gap_and_no_horizon_crossing():
    cfg = load_config("configs/synthetic.yaml")
    make_synthetic_sample(cfg)
    build_features(cfg)
    df = make_labels_regimes_splits(cfg)
    horizon = cfg["labels"]["horizon_rows"]
    for symbol, g in df.groupby("symbol"):
        g = g.sort_values("origin_time")
        train_end = g.loc[g["split"] == "train", "row_in_symbol"].max()
        valid_start = g.loc[g["split"] == "valid", "row_in_symbol"].min()
        valid_end = g.loc[g["split"] == "valid", "row_in_symbol"].max()
        test_start = g.loc[g["split"] == "test", "row_in_symbol"].min()
        assert valid_start - train_end >= horizon
        assert test_start - valid_end >= horizon
        assert train_end + horizon < valid_start + horizon
        assert valid_end + horizon < test_start + horizon
