from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import torch

from models.deeplob import DeepLOB
from models.lob_transformer import LOBTransformerLite


def _load_temporal_script():
    script = Path(__file__).resolve().parents[1] / "scripts" / "13_train_temporal_baseline_from_predictions.py"
    spec = importlib.util.spec_from_file_location("temporal_train_script", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_deeplob_forward_shape_matches_lob_window_contract() -> None:
    model = DeepLOB(input_dim=40, conv_channels=4, inception_channels=8, hidden_dim=8)
    logits = model(torch.zeros((2, 100, 40), dtype=torch.float32))
    assert logits.shape == (2, 3)


def test_lob_transformer_forward_shape_matches_lob_window_contract() -> None:
    model = LOBTransformerLite(
        input_dim=40,
        conv_channels=4,
        inception_channels=8,
        n_heads=4,
        n_layers=1,
        dropout=0.0,
    )
    logits = model(torch.zeros((2, 100, 40), dtype=torch.float32))
    assert logits.shape == (2, 3)


def test_lob_deep_models_fail_clearly_on_incompatible_feature_count() -> None:
    with pytest.raises(ValueError, match="40"):
        DeepLOB(input_dim=39)
    with pytest.raises(ValueError, match="40"):
        LOBTransformerLite(input_dim=39)

    deeplob = DeepLOB(input_dim=40, conv_channels=4, inception_channels=8, hidden_dim=8)
    transformer = LOBTransformerLite(input_dim=40, conv_channels=4, inception_channels=8, n_heads=4)
    with pytest.raises(ValueError, match="40 LOB features"):
        deeplob(torch.zeros((2, 100, 39), dtype=torch.float32))
    with pytest.raises(ValueError, match="40 LOB features"):
        transformer(torch.zeros((2, 100, 39), dtype=torch.float32))


def test_temporal_model_factory_resolves_canonical_lob_keys() -> None:
    module = _load_temporal_script()
    cfg = {
        "hidden_dim": 8,
        "deeplob_conv_channels": 4,
        "deeplob_inception_channels": 8,
        "transformer_conv_channels": 4,
        "transformer_inception_channels": 8,
        "transformer_heads": 4,
        "transformer_layers": 1,
        "transformer_dropout": 0.0,
    }
    assert isinstance(module.build_temporal_model("deeplob", cfg, input_dim=40), DeepLOB)
    assert isinstance(module.build_temporal_model("deeplob_faithful_lite", cfg, input_dim=40), DeepLOB)
    assert isinstance(module.build_temporal_model("lob_transformer", cfg, input_dim=40), LOBTransformerLite)


def test_temporal_prediction_outputs_do_not_target_tabular_artifacts() -> None:
    module = _load_temporal_script()
    assert module.PREDICTION_OUTPUTS["deeplob"] != "data/predictions/predictions.parquet"
    assert module.PREDICTION_OUTPUTS["lob_transformer"] != "data/predictions/predictions.parquet"
    assert module.PREDICTION_OUTPUTS["deeplob"] != module.PREDICTION_OUTPUTS["lob_transformer"]
    assert module.PREDICTION_OUTPUTS["deeplob"] != module.PREDICTION_OUTPUTS["tcn"]
