from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler


def fit_kmeans_regimes(frame: pd.DataFrame, columns: list[str], n_clusters: int = 6, random_state: int = 7) -> pd.Series:
    scaler = StandardScaler()
    values = scaler.fit_transform(frame[columns].fillna(0.0))
    labels = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10).fit_predict(values)
    return pd.Series(labels, index=frame.index, name="cluster_regime")


def residual_cluster_alignment(
    frame: pd.DataFrame,
    columns: list[str],
    sample_size: int = 200000,
    random_state: int = 7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    residual = frame[frame["regime"].isin(["BALANCED_TRANSITION", "MILD_LIQUIDITY_STRESS", "UNKNOWN"])].copy()
    if residual.empty:
        return pd.DataFrame(), pd.DataFrame()
    sample = residual.sample(n=min(sample_size, len(residual)), random_state=random_state).copy()
    scaler = StandardScaler()
    values = scaler.fit_transform(sample[columns].fillna(0.0))
    kmeans_labels = KMeans(n_clusters=3, random_state=random_state, n_init=10).fit_predict(values)
    gmm_labels = GaussianMixture(n_components=3, covariance_type="diag", random_state=random_state).fit_predict(values)
    projected = PCA(n_components=2, random_state=random_state).fit_transform(values)

    sample["kmeans_cluster"] = kmeans_labels
    sample["gmm_cluster"] = gmm_labels
    sample["pca_x"] = projected[:, 0]
    sample["pca_y"] = projected[:, 1]
    alignment = []
    for algo in ["kmeans_cluster", "gmm_cluster"]:
        pivot = sample.groupby(["regime", algo], dropna=False).size().reset_index(name="n_rows")
        pivot["algorithm"] = algo.replace("_cluster", "")
        pivot = pivot.rename(columns={algo: "cluster"})
        pivot["within_regime_share"] = pivot["n_rows"] / pivot.groupby("regime")["n_rows"].transform("sum")
        pivot["within_cluster_share"] = pivot["n_rows"] / pivot.groupby("cluster")["n_rows"].transform("sum")
        alignment.append(pivot[["algorithm", "regime", "cluster", "n_rows", "within_regime_share", "within_cluster_share"]])
    return pd.concat(alignment, ignore_index=True), sample[["regime", "kmeans_cluster", "gmm_cluster", "pca_x", "pca_y"]]
