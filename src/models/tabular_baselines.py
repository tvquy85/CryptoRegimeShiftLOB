from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.base import clone
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler


@dataclass
class TabularModelBundle:
    pipeline: Pipeline
    label_encoder: LabelEncoder
    features: list[str]
    model_name: str

    def save(self, path: str) -> None:
        joblib.dump(self, path)


class NanToZeroTransformer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        values = np.asarray(X, dtype=np.float32)
        return np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)


def train_tabular_model(
    train: pd.DataFrame,
    valid: pd.DataFrame,
    features: list[str],
    model_name: str,
    config: dict[str, object],
) -> TabularModelBundle:
    label_encoder = LabelEncoder()
    label_encoder.fit(["DOWN", "FLAT", "UP"])
    y_train = label_encoder.transform(train["label"])
    if len(set(y_train.tolist())) < 2:
        pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", DummyClassifier(strategy="most_frequent")),
            ]
        )
        pipeline.fit(train[features], y_train)
        return TabularModelBundle(pipeline=pipeline, label_encoder=label_encoder, features=features, model_name="dummy")

    if model_name == "xgboost":
        try:
            from xgboost import XGBClassifier

            model_cfg = config.get("xgboost", {})
            estimator = _xgboost_estimator(config, use_gpu=bool(model_cfg.get("use_gpu", False)))
            pipeline = Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", estimator)])
            try:
                pipeline.fit(train[features], y_train)
            except Exception:
                if not bool(model_cfg.get("use_gpu", False)):
                    raise
                cpu_pipeline = Pipeline(
                    [
                        ("imputer", clone(pipeline.named_steps["imputer"])),
                        ("model", _xgboost_estimator(config, use_gpu=False)),
                    ]
                )
                cpu_pipeline.fit(train[features], y_train)
                return TabularModelBundle(
                    pipeline=cpu_pipeline,
                    label_encoder=label_encoder,
                    features=features,
                    model_name="xgboost_cpu_fallback",
                )
            return TabularModelBundle(pipeline=pipeline, label_encoder=label_encoder, features=features, model_name="xgboost_gpu" if bool(model_cfg.get("use_gpu", False)) else "xgboost")
        except ImportError:
            pipeline = _sgd_pipeline(config)
            model_name = "sgd"
    else:
        pipeline = _sgd_pipeline(config)
        model_name = "sgd"

    pipeline.fit(train[features], y_train)
    return TabularModelBundle(pipeline=pipeline, label_encoder=label_encoder, features=features, model_name=model_name)


def train_streaming_sgd(
    split_path: str | Path,
    features: list[str],
    config: dict[str, object],
    *,
    batch_size: int = 250_000,
) -> TabularModelBundle:
    label_encoder = LabelEncoder()
    label_encoder.fit(["DOWN", "FLAT", "UP"])
    scaler = StandardScaler()
    counts = np.zeros(len(label_encoder.classes_), dtype=np.int64)
    total_train = 0
    columns = [*features, "label", "split"]
    parquet = pq.ParquetFile(split_path)

    for batch in parquet.iter_batches(batch_size=batch_size, columns=columns):
        frame = batch.to_pandas()
        train = frame[frame["split"] == "train"]
        if train.empty:
            continue
        X = _clean_feature_matrix(train, features)
        y = label_encoder.transform(train["label"])
        scaler.partial_fit(X)
        counts += np.bincount(y, minlength=len(counts))
        total_train += int(len(train))

    if total_train == 0:
        raise RuntimeError("Train split rỗng, không thể train SGD streaming.")

    model_cfg = config.get("sgd", {})
    estimator = SGDClassifier(
        loss="log_loss",
        alpha=float(model_cfg.get("alpha", 0.0001)),
        max_iter=1,
        tol=None,
        random_state=int(config.get("random_seed", 7)),
    )
    active_classes = np.maximum(counts, 1)
    class_weights = total_train / (len(counts) * active_classes.astype("float64"))
    classes = np.arange(len(label_encoder.classes_))
    epochs = int(model_cfg.get("streaming_epochs", 1))
    fitted = False

    for _ in range(max(epochs, 1)):
        for batch in parquet.iter_batches(batch_size=batch_size, columns=columns):
            frame = batch.to_pandas()
            train = frame[frame["split"] == "train"]
            if train.empty:
                continue
            X = scaler.transform(_clean_feature_matrix(train, features))
            y = label_encoder.transform(train["label"])
            sample_weight = class_weights[y]
            if not fitted:
                estimator.partial_fit(X, y, classes=classes, sample_weight=sample_weight)
                fitted = True
            else:
                estimator.partial_fit(X, y, sample_weight=sample_weight)

    pipeline = Pipeline(
        [
            ("nan_to_zero", NanToZeroTransformer()),
            ("scaler", scaler),
            ("model", estimator),
        ]
    )
    return TabularModelBundle(pipeline=pipeline, label_encoder=label_encoder, features=features, model_name="sgd")


def predict_probabilities(bundle: TabularModelBundle, frame: pd.DataFrame) -> pd.DataFrame:
    values = bundle.pipeline.predict_proba(frame[bundle.features])
    columns = [f"prob_{label.lower()}" for label in bundle.label_encoder.classes_]
    probs = pd.DataFrame(values, columns=columns, index=frame.index)
    pred_idx = np.argmax(values, axis=1)
    probs["pred_label"] = bundle.label_encoder.inverse_transform(pred_idx)
    return probs


def _clean_feature_matrix(frame: pd.DataFrame, features: list[str]) -> np.ndarray:
    values = frame[features].to_numpy(dtype=np.float32, copy=False)
    return np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)


def _sgd_pipeline(config: dict[str, object]) -> Pipeline:
    model_cfg = config.get("sgd", {})
    estimator = SGDClassifier(
        loss="log_loss",
        alpha=float(model_cfg.get("alpha", 0.0001)),
        max_iter=int(model_cfg.get("max_iter", 2000)),
        tol=float(model_cfg.get("tol", 0.001)),
        class_weight="balanced",
        random_state=int(config.get("random_seed", 7)),
    )
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", estimator),
        ]
    )


def _xgboost_estimator(config: dict[str, object], *, use_gpu: bool):
    from xgboost import XGBClassifier

    model_cfg = config.get("xgboost", {})
    kwargs = {
        "objective": "multi:softprob",
        "eval_metric": "mlogloss",
        "num_class": 3,
        "max_depth": int(model_cfg.get("max_depth", 5)),
        "n_estimators": int(model_cfg.get("n_estimators", 150)),
        "learning_rate": float(model_cfg.get("learning_rate", 0.05)),
        "subsample": float(model_cfg.get("subsample", 0.9)),
        "colsample_bytree": float(model_cfg.get("colsample_bytree", 0.9)),
        "tree_method": str(model_cfg.get("tree_method", "hist")),
        "random_state": int(config.get("random_seed", 7)),
    }
    if use_gpu:
        kwargs["device"] = "cuda"
    return XGBClassifier(**kwargs)
