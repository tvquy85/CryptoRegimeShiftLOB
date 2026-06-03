from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, matthews_corrcoef


LABEL_ORDER = ["DOWN", "FLAT", "UP"]


def classification_summary(frame: pd.DataFrame, label_col: str = "label", pred_col: str = "pred_label") -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(frame[label_col], frame[pred_col])),
        "macro_f1": float(f1_score(frame[label_col], frame[pred_col], average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(frame[label_col], frame[pred_col], average="weighted", zero_division=0)),
        "mcc": float(matthews_corrcoef(frame[label_col], frame[pred_col])),
        "balanced_accuracy": float(balanced_accuracy_score(frame[label_col], frame[pred_col])),
    }


def classification_by_regime(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for regime, group in frame.groupby("regime", dropna=False):
        if group.empty:
            continue
        metrics = classification_summary(group)
        rows.append({"regime": regime, **metrics, "n_rows": int(len(group))})
    return pd.DataFrame(rows)


def classification_from_parquet(path, *, split: str = "test") -> tuple[dict[str, float], pd.DataFrame]:
    lazy = pl.scan_parquet(str(path)).filter(pl.col("split") == split)
    overall_counts = (
        lazy.group_by(["label", "pred_label"])
        .len()
        .collect(engine="streaming")
        .to_pandas()
    )
    by_regime_counts = (
        lazy.group_by(["regime", "label", "pred_label"])
        .len()
        .collect(engine="streaming")
        .to_pandas()
    )
    overall = classification_summary_from_counts(overall_counts)
    by_regime = classification_by_regime_from_counts(by_regime_counts)
    return overall, by_regime


def classification_summary_from_counts(counts: pd.DataFrame) -> dict[str, float]:
    matrix = _confusion_matrix(counts)
    return _metrics_from_matrix(matrix)


def classification_by_regime_from_counts(counts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for regime, group in counts.groupby("regime", dropna=False):
        matrix = _confusion_matrix(group)
        metrics = _metrics_from_matrix(matrix)
        rows.append({"regime": regime, **metrics, "n_rows": int(matrix.sum())})
    return pd.DataFrame(rows)


def _confusion_matrix(counts: pd.DataFrame) -> np.ndarray:
    count_col = "len" if "len" in counts.columns else "count"
    matrix = np.zeros((len(LABEL_ORDER), len(LABEL_ORDER)), dtype=np.int64)
    index = {label: idx for idx, label in enumerate(LABEL_ORDER)}
    for row in counts.itertuples(index=False):
        actual = getattr(row, "label")
        predicted = getattr(row, "pred_label")
        if actual not in index or predicted not in index:
            continue
        matrix[index[actual], index[predicted]] += int(getattr(row, count_col))
    return matrix


def _metrics_from_matrix(matrix: np.ndarray) -> dict[str, float]:
    total = int(matrix.sum())
    if total == 0:
        return {
            "accuracy": 0.0,
            "macro_f1": 0.0,
            "weighted_f1": 0.0,
            "mcc": 0.0,
            "balanced_accuracy": 0.0,
        }
    tp = np.diag(matrix).astype("float64")
    support = matrix.sum(axis=1).astype("float64")
    predicted = matrix.sum(axis=0).astype("float64")
    precision = np.divide(tp, predicted, out=np.zeros_like(tp), where=predicted > 0)
    recall = np.divide(tp, support, out=np.zeros_like(tp), where=support > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(tp), where=(precision + recall) > 0)
    accuracy = float(tp.sum() / total)
    macro_f1 = float(f1.mean())
    weighted_f1 = float((f1 * support).sum() / total)
    balanced_accuracy = float(recall.mean())
    covariance_ytyp = float(tp.sum() * total - (support * predicted).sum())
    covariance_ypyp = float(total**2 - (predicted**2).sum())
    covariance_ytyt = float(total**2 - (support**2).sum())
    denominator = np.sqrt(covariance_ytyt * covariance_ypyp)
    mcc = float(covariance_ytyp / denominator) if denominator > 0 else 0.0
    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "mcc": mcc,
        "balanced_accuracy": balanced_accuracy,
    }
