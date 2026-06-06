import numpy as np
import pandas as pd
import pytest

from artifact_lib import ArtifactError, load_config, make_synthetic_sample, validate_l2_schema


def test_synthetic_schema_has_20_levels(tmp_path):
    cfg = load_config("configs/synthetic.yaml")
    df = make_synthetic_sample(cfg)
    report = validate_l2_schema(df, cfg, mode="synthetic")
    assert report["checks"]["required_columns"] == "PASS"
    assert report["checks"]["best_bid_less_than_best_ask"] == "PASS"
    assert report["levels_per_side"] == 20


def test_validator_rejects_crossed_best_book():
    cfg = load_config("configs/synthetic.yaml")
    df = make_synthetic_sample(cfg).head(10).copy()
    df.loc[df.index[0], "bid_0_price"] = df.loc[df.index[0], "ask_0_price"] + 1.0
    with pytest.raises(ArtifactError):
        validate_l2_schema(df, cfg, mode="synthetic")


def test_validator_rejects_negative_size():
    cfg = load_config("configs/synthetic.yaml")
    df = make_synthetic_sample(cfg).head(10).copy()
    df.loc[df.index[0], "ask_0_size"] = -1.0
    with pytest.raises(ArtifactError):
        validate_l2_schema(df, cfg, mode="synthetic")

