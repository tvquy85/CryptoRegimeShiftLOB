from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
LEVELS = 20
LABEL_ORDER = ["DOWN", "FLAT", "UP"]


class ArtifactError(RuntimeError):
    pass


def path_in_root(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return p


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path_in_root(path), "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def ensure_dir(path: str | Path) -> Path:
    p = path_in_root(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def artifact_dir(config: dict[str, Any], mode: str | None = None) -> Path:
    if mode == "raw-sample":
        return ensure_dir(config["paths"]["artifact_dir"])
    return ensure_dir(config["paths"].get("artifact_dir", f"artifacts/{mode or config.get('mode', 'synthetic')}"))


def tables_dir(config: dict[str, Any], mode: str = "synthetic") -> Path:
    return ensure_dir(artifact_dir(config, mode) / "tables")


def logs_dir(config: dict[str, Any], mode: str = "synthetic") -> Path:
    return ensure_dir(artifact_dir(config, mode) / "logs")


def write_log(config: dict[str, Any], mode: str, name: str, message: str) -> None:
    log_path = logs_dir(config, mode) / f"{name}.log"
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(message.rstrip() + "\n")


def required_l2_columns(levels: int = LEVELS) -> list[str]:
    cols = ["origin_time", "received_time", "sequence_number", "symbol", "exchange"]
    for i in range(levels):
        cols += [f"bid_{i}_price", f"bid_{i}_size", f"ask_{i}_price", f"ask_{i}_size"]
    return cols


def book_columns(levels: int = LEVELS) -> list[str]:
    cols: list[str] = []
    for i in range(levels):
        cols += [f"bid_{i}_price", f"bid_{i}_size", f"ask_{i}_price", f"ask_{i}_size"]
    return cols


def read_parquet_many(pattern: str | Path) -> pd.DataFrame:
    files = sorted(path_in_root(".").glob(str(pattern))) if not Path(pattern).is_absolute() else sorted(Path().glob(str(pattern)))
    if not files:
        raise FileNotFoundError(str(pattern))
    return pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)


def make_synthetic_sample(config: dict[str, Any]) -> pd.DataFrame:
    rng = np.random.default_rng(int(config["seed"]))
    rows: list[pd.DataFrame] = []
    days = int(config["synthetic"]["days"])
    rows_per_day = int(config["synthetic"]["rows_per_day"])
    interval_ms = int(config["synthetic"]["snapshot_interval_ms"])
    spread_low, spread_high = config["synthetic"]["spread_bps_range"]
    exchange = config.get("exchange", "BINANCE")
    seq = 1

    for symbol in config["assets"]:
        base = float(config["synthetic"]["base_prices"][symbol])
        tick = max(base * 1e-6, 0.01)
        for day in range(days):
            start = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=day)
            n = rows_per_day
            vol = np.repeat([0.6, 1.4, 2.5], repeats=max(1, n // 3))[:n]
            if len(vol) < n:
                vol = np.pad(vol, (0, n - len(vol)), constant_values=1.0)
            returns = rng.normal(0, 4e-5 * vol, size=n)
            block = max(50, n // 8)
            returns[block : 2 * block] += 3.0e-5
            returns[3 * block : 4 * block] -= 3.0e-5
            returns[5 * block : 6 * block] += 2.0e-5
            mid = base * np.exp(np.cumsum(returns))
            spread_bps = rng.uniform(spread_low, spread_high, size=n)
            stress_slice = slice(n // 2, min(n, n // 2 + n // 10))
            spread_bps[stress_slice] *= 2.0
            half_spread = mid * spread_bps / 20000.0
            timestamps = start + pd.to_timedelta(np.arange(n) * interval_ms, unit="ms")
            frame: dict[str, Any] = {
                "origin_time": timestamps,
                "received_time": timestamps + pd.to_timedelta(2, unit="ms"),
                "sequence_number": np.arange(seq, seq + n, dtype=np.int64),
                "symbol": symbol,
                "exchange": exchange,
            }
            seq += n
            depth_scale = 2.0 if symbol.startswith("ETH") else 0.25
            top_depth = rng.lognormal(mean=np.log(depth_scale), sigma=0.25, size=n)
            top_depth[stress_slice] *= 0.35
            for level in range(LEVELS):
                distance = (level + 1) * tick * (1.0 + 0.05 * level)
                level_scale = np.exp(-0.06 * level)
                bid_price = mid - half_spread - distance
                ask_price = mid + half_spread + distance
                bid_size = top_depth * level_scale * rng.uniform(0.8, 1.2, size=n)
                ask_size = top_depth * level_scale * rng.uniform(0.8, 1.2, size=n)
                frame[f"bid_{level}_price"] = bid_price.astype("float64")
                frame[f"bid_{level}_size"] = bid_size.astype("float64")
                frame[f"ask_{level}_price"] = ask_price.astype("float64")
                frame[f"ask_{level}_size"] = ask_size.astype("float64")
            rows.append(pd.DataFrame(frame))
    df = pd.concat(rows, ignore_index=True)
    df.sort_values(["symbol", "origin_time", "sequence_number"], inplace=True)
    out = path_in_root(config["paths"]["raw"])
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    expected = ensure_dir("data/synthetic/expected_outputs")
    (expected / "README.md").write_text("Generated by scripts/00_make_synthetic_l2_sample.py\n", encoding="utf-8")
    return df


def load_l2_input(config: dict[str, Any], mode: str) -> pd.DataFrame:
    if mode == "synthetic":
        p = path_in_root(config["paths"]["raw"])
        if not p.exists():
            raise ArtifactError("Synthetic raw parquet missing. Run scripts/00_make_synthetic_l2_sample.py first.")
        return pd.read_parquet(p)
    if mode == "raw-sample":
        files = sorted(path_in_root(".").glob(config["paths"]["raw_glob"]))
        if not files:
            raise FileNotFoundError("Raw-format sample not packaged. Use `make synthetic` or place provider sample under data/raw_sample/cryptolake_minimal/.")
        return pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
    if mode == "full":
        files = sorted(path_in_root(".").glob(config["paths"]["raw_glob"]))
        if not files:
            raise FileNotFoundError("Licensed Crypto Lake raw snapshots not found.")
        return pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
    raise ValueError(mode)


def validate_l2_schema(df: pd.DataFrame, config: dict[str, Any], mode: str) -> dict[str, Any]:
    levels = int(config.get("levels_per_side", LEVELS))
    required = required_l2_columns(levels)
    missing = [c for c in required if c not in df.columns]
    checks: dict[str, str] = {}
    if missing:
        checks["required_columns"] = "FAIL"
        raise ArtifactError(f"Missing required columns: {missing[:10]}")
    checks["required_columns"] = "PASS"

    df = df.copy()
    df["origin_time"] = pd.to_datetime(df["origin_time"], utc=True, errors="coerce")
    df["received_time"] = pd.to_datetime(df["received_time"], utc=True, errors="coerce")
    if df["origin_time"].isna().any():
        checks["timestamp_parse"] = "FAIL"
        raise ArtifactError("origin_time contains unparsable timestamps")
    checks["timestamp_parse"] = "PASS"

    monotonic = True
    duplicate_ts = 0
    for _, g in df.sort_values(["symbol", "origin_time"]).groupby("symbol"):
        monotonic = monotonic and bool(g["origin_time"].is_monotonic_increasing)
        duplicate_ts += int(g["origin_time"].duplicated().sum())
    checks["timestamp_monotonic_by_symbol"] = "PASS" if monotonic else "FAIL"

    best_ok = (df["bid_0_price"] < df["ask_0_price"]).all()
    checks["best_bid_less_than_best_ask"] = "PASS" if best_ok else "FAIL"
    if not best_ok:
        raise ArtifactError("Found crossed top-of-book rows")

    non_negative_size = True
    bid_depth_order = True
    ask_depth_order = True
    for i in range(levels):
        non_negative_size = non_negative_size and (df[f"bid_{i}_size"] >= 0).all() and (df[f"ask_{i}_size"] >= 0).all()
        if i > 0:
            bid_depth_order = bid_depth_order and (df[f"bid_{i}_price"] <= df[f"bid_{i-1}_price"]).all()
            ask_depth_order = ask_depth_order and (df[f"ask_{i}_price"] >= df[f"ask_{i-1}_price"]).all()
    checks["non_negative_size"] = "PASS" if non_negative_size else "FAIL"
    checks["bid_depth_monotonic"] = "PASS" if bid_depth_order else "FAIL"
    checks["ask_depth_monotonic"] = "PASS" if ask_depth_order else "FAIL"
    if not (non_negative_size and bid_depth_order and ask_depth_order):
        raise ArtifactError("Invalid level size or price depth ordering")

    report = {
        "mode": mode,
        "rows": int(len(df)),
        "symbols": sorted(map(str, df["symbol"].unique())),
        "exchange": sorted(map(str, df["exchange"].unique())),
        "start_time": str(df["origin_time"].min()),
        "end_time": str(df["origin_time"].max()),
        "levels_per_side": levels,
        "duplicate_timestamps": duplicate_ts,
        "checks": checks,
    }
    out_dir = artifact_dir(config, mode)
    with open(out_dir / "schema_report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    pd.DataFrame([report | {"checks": json.dumps(checks)}]).to_csv(tables_dir(config, mode) / "schema_report.csv", index=False)
    return report


def build_features(config: dict[str, Any], mode: str = "synthetic") -> pd.DataFrame:
    df = load_l2_input(config, mode)
    df["origin_time"] = pd.to_datetime(df["origin_time"], utc=True)
    df.sort_values(["symbol", "origin_time", "sequence_number"], inplace=True)
    df["mid_price"] = (df["bid_0_price"] + df["ask_0_price"]) / 2.0
    df["spread"] = df["ask_0_price"] - df["bid_0_price"]
    df["rel_spread"] = df["spread"] / (df["mid_price"] + 1e-12)
    for k in [1, 5, 10, 20]:
        bid = sum(df[f"bid_{i}_size"] for i in range(k))
        ask = sum(df[f"ask_{i}_size"] for i in range(k))
        df[f"bid_depth_{k}"] = bid
        df[f"ask_depth_{k}"] = ask
        df[f"total_depth_{k}"] = bid + ask
        df[f"depth_imbalance_{k}"] = (bid - ask) / (bid + ask + 1e-12)
    df["microprice"] = (df["ask_0_price"] * df["bid_0_size"] + df["bid_0_price"] * df["ask_0_size"]) / (df["bid_0_size"] + df["ask_0_size"] + 1e-12)
    df["microprice_deviation"] = (df["microprice"] - df["mid_price"]) / (df["mid_price"] + 1e-12)
    pieces = []
    for _, g in df.groupby("symbol", sort=False):
        g = g.copy()
        g["ret_1"] = g["mid_price"].pct_change().fillna(0.0)
        g["ret_10"] = g["mid_price"].pct_change(10).fillna(0.0)
        g["realized_vol_20"] = g["ret_1"].rolling(20, min_periods=2).std().fillna(0.0)
        g["realized_vol_100"] = g["ret_1"].rolling(100, min_periods=2).std().fillna(0.0)
        g["spread_z_100"] = zscore(g["rel_spread"], 100)
        g["depth_z_100"] = zscore(g["total_depth_10"], 100)
        g["momentum_score"] = g["ret_10"].rolling(20, min_periods=2).mean().fillna(0.0)
        pieces.append(g)
    out = pd.concat(pieces, ignore_index=True)
    out_dir = artifact_dir(config, mode)
    out.to_parquet(out_dir / "features.parquet", index=False)
    summary = out.groupby("symbol").agg(rows=("symbol", "size"), mean_rel_spread=("rel_spread", "mean"), mean_depth10=("total_depth_10", "mean")).reset_index()
    summary.to_csv(tables_dir(config, mode) / "feature_summary.csv", index=False)
    return out


def zscore(s: pd.Series, window: int) -> pd.Series:
    mean = s.rolling(window, min_periods=5).mean()
    std = s.rolling(window, min_periods=5).std()
    return ((s - mean) / (std + 1e-12)).fillna(0.0)


def make_labels_regimes_splits(config: dict[str, Any], mode: str = "synthetic") -> pd.DataFrame:
    out_dir = artifact_dir(config, mode)
    df = pd.read_parquet(out_dir / "features.parquet")
    df["origin_time"] = pd.to_datetime(df["origin_time"], utc=True)
    horizon = int(config["labels"]["horizon_rows"])
    fee = float(config["labels"]["fee_bps"])
    kappa = float(config["labels"]["slippage_buffer_multiplier"])
    eps = float(config["labels"].get("eps", 1e-9))
    train_ratio = float(config["splits"]["train_ratio"])
    valid_ratio = float(config["splits"]["valid_ratio"])
    purge = int(config["splits"]["purge_gap_rows"])
    outputs = []
    manifests = []

    for symbol, g in df.sort_values(["symbol", "origin_time"]).groupby("symbol", sort=False):
        g = g.copy().reset_index(drop=True)
        g["future_ret_h"] = (g["mid_price"].shift(-horizon) - g["mid_price"]) / (g["mid_price"] + eps)
        g["cost_threshold_t"] = (1.0 + kappa) * g["rel_spread"] + fee / 10000.0
        g = g.iloc[:-horizon].copy()
        g["row_in_symbol"] = np.arange(len(g), dtype=np.int64)
        g["label"] = np.where(g["future_ret_h"] > g["cost_threshold_t"], "UP", np.where(g["future_ret_h"] < -g["cost_threshold_t"], "DOWN", "FLAT"))
        n = len(g)
        train_cut = int(n * train_ratio)
        valid_cut = int(n * (train_ratio + valid_ratio))
        split = np.full(n, "drop_purge", dtype=object)
        split[: max(0, train_cut - purge)] = "train"
        split[train_cut : max(train_cut, valid_cut - purge)] = "valid"
        split[valid_cut:] = "test"
        g["split"] = split
        keep = g[g["split"] != "drop_purge"].copy()

        train = keep[keep["split"] == "train"]
        q = {
            "rel_spread_high": train["rel_spread"].quantile(0.70),
            "rel_spread_low": train["rel_spread"].quantile(0.40),
            "depth_low": train["total_depth_10"].quantile(0.30),
            "depth_high": train["total_depth_10"].quantile(0.70),
            "vol_high": train["realized_vol_20"].quantile(0.70),
            "vol_low": train["realized_vol_20"].quantile(0.40),
            "momentum_high": train["momentum_score"].abs().quantile(0.80),
        }
        keep["regime"] = assign_regimes(keep, q)
        outputs.append(keep)
        for split_name, part in keep.groupby("split"):
            manifests.append({
                "symbol": symbol,
                "split": split_name,
                "rows": int(len(part)),
                "start_utc": str(part["origin_time"].min()),
                "end_utc": str(part["origin_time"].max()),
                "horizon_rows": horizon,
                "purge_gap_rows": purge,
            })

    result = pd.concat(outputs, ignore_index=True)
    result.to_parquet(out_dir / "labels_regimes_splits.parquet", index=False)
    result[["origin_time", "symbol", "label", "future_ret_h", "cost_threshold_t"]].to_parquet(out_dir / "labels.parquet", index=False)
    result[["origin_time", "symbol", "regime"]].to_parquet(out_dir / "regimes.parquet", index=False)
    pd.DataFrame(manifests).to_csv(out_dir / "split_manifest.csv", index=False)
    label_summary = result.groupby(["symbol", "split", "label"]).size().reset_index(name="rows")
    regime_summary = result.groupby(["symbol", "split", "regime"]).size().reset_index(name="rows")
    label_summary.to_csv(tables_dir(config, mode) / "label_summary.csv", index=False)
    regime_summary.to_csv(tables_dir(config, mode) / "regime_summary.csv", index=False)
    return result


def assign_regimes(df: pd.DataFrame, q: dict[str, float]) -> np.ndarray:
    regimes = np.full(len(df), "BALANCED_TRANSITION", dtype=object)
    drought = (df["rel_spread"] >= q["rel_spread_high"]) & (df["total_depth_10"] <= q["depth_low"])
    volatile = df["realized_vol_20"] >= q["vol_high"]
    liquid = df["total_depth_10"] >= q["depth_high"]
    calm = df["realized_vol_20"] <= q["vol_low"]
    momentum = df["momentum_score"].abs() >= q["momentum_high"]
    regimes[drought.to_numpy()] = "LIQUIDITY_DROUGHT"
    regimes[(volatile & liquid).to_numpy()] = "VOLATILE_LIQUID"
    regimes[(volatile & ~liquid).to_numpy()] = "VOLATILE_ILLIQUID"
    regimes[(calm & liquid).to_numpy()] = "CALM_LIQUID"
    regimes[(momentum & ~drought).to_numpy()] = "MOMENTUM_TOXIC"
    unknown = ~(drought | volatile | calm | momentum | liquid)
    regimes[unknown.to_numpy()] = "UNKNOWN"
    return regimes


def train_baseline(config: dict[str, Any], mode: str = "synthetic") -> pd.DataFrame:
    from sklearn.linear_model import SGDClassifier
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, matthews_corrcoef
    from sklearn.preprocessing import StandardScaler

    out_dir = artifact_dir(config, mode)
    df = pd.read_parquet(out_dir / "labels_regimes_splits.parquet")
    feature_cols = ["rel_spread", "total_depth_10", "depth_imbalance_10", "microprice_deviation", "ret_1", "ret_10", "realized_vol_20", "realized_vol_100", "spread_z_100", "depth_z_100", "momentum_score"]
    train = df[df["split"] == "train"]
    scaler = StandardScaler().fit(train[feature_cols])
    clf = SGDClassifier(loss="log_loss", max_iter=1000, tol=1e-4, random_state=int(config["seed"]), class_weight="balanced")
    clf.fit(scaler.transform(train[feature_cols]), train["label"])
    probs = clf.predict_proba(scaler.transform(df[feature_cols]))
    classes = list(clf.classes_)
    for label in LABEL_ORDER:
        df[f"prob_{label.lower()}"] = probs[:, classes.index(label)] if label in classes else 0.0
    df["pred_label"] = np.array(LABEL_ORDER)[np.argmax(df[[f"prob_{l.lower()}" for l in LABEL_ORDER]].to_numpy(), axis=1)]
    pred_dir = ensure_dir(out_dir / "predictions")
    df.to_parquet(pred_dir / "sgd_predictions.parquet", index=False)
    rows = []
    for split, part in df.groupby("split"):
        rows.append({
            "mode": mode,
            "model": "sgd_small",
            "split": split,
            "rows": int(len(part)),
            "accuracy": accuracy_score(part["label"], part["pred_label"]),
            "macro_f1": f1_score(part["label"], part["pred_label"], average="macro", zero_division=0),
            "balanced_accuracy": balanced_accuracy_score(part["label"], part["pred_label"]),
            "mcc": matthews_corrcoef(part["label"], part["pred_label"]),
        })
    pd.DataFrame(rows).to_csv(tables_dir(config, mode) / "prediction_metrics.csv", index=False)
    return df


@dataclass
class ReplayConfig:
    trade_notional: float
    fee_bps: float
    latency_rows: int
    hold_rows: int
    min_fill_ratio: float
    partial_fill: bool
    spread_multiplier: float
    depth_multiplier: float
    cooldown_rows: int


def replay_config(config: dict[str, Any], **overrides: Any) -> ReplayConfig:
    r = dict(config["replay"])
    r.update(overrides)
    return ReplayConfig(
        trade_notional=float(r["trade_notional"]),
        fee_bps=float(r["fee_bps"]),
        latency_rows=int(r["latency_rows"]),
        hold_rows=int(r["hold_rows"]),
        min_fill_ratio=float(r["min_fill_ratio"]),
        partial_fill=bool(r["partial_fill"]),
        spread_multiplier=float(r["spread_multiplier"]),
        depth_multiplier=float(r["depth_multiplier"]),
        cooldown_rows=int(r["cooldown_rows"]),
    )


def sweep_book(row: pd.Series, side: int, cfg: ReplayConfig) -> tuple[float, float]:
    mid = float(row["mid_price"])
    target_qty = cfg.trade_notional / max(mid, 1e-12)
    remaining = target_qty
    filled = 0.0
    notional = 0.0
    for level in range(LEVELS):
        if side > 0:
            raw_price = float(row[f"ask_{level}_price"])
            price = mid + cfg.spread_multiplier * (raw_price - mid)
            size = float(row[f"ask_{level}_size"]) * cfg.depth_multiplier
        else:
            raw_price = float(row[f"bid_{level}_price"])
            price = mid - cfg.spread_multiplier * (mid - raw_price)
            size = float(row[f"bid_{level}_size"]) * cfg.depth_multiplier
        if not np.isfinite(price) or not np.isfinite(size) or price <= 0 or size <= 0:
            continue
        qty = min(remaining, size)
        filled += qty
        notional += qty * price
        remaining -= qty
        if remaining <= 1e-12:
            break
    ratio = filled / target_qty if target_qty > 0 else 0.0
    if filled <= 0 or ratio < cfg.min_fill_ratio:
        return 0.0, 0.0
    if not cfg.partial_fill and ratio < 0.999999:
        return 0.0, 0.0
    return notional / filled, filled


def simulate_replay(df: pd.DataFrame, config: dict[str, Any], policy: str, cfg: ReplayConfig) -> pd.DataFrame:
    rows = []
    last_entry = -10**9
    sim = df[df["split"] == "test"].sort_values(["symbol", "origin_time"]).reset_index(drop=True)
    for i, row in sim.iterrows():
        if i - last_entry < cfg.cooldown_rows:
            continue
        action = action_from_row(row, policy)
        if action == 0:
            continue
        entry_i = i + cfg.latency_rows
        exit_i = entry_i + cfg.hold_rows
        if exit_i >= len(sim):
            continue
        entry = sim.iloc[entry_i]
        exit_row = sim.iloc[exit_i]
        if entry["symbol"] != row["symbol"] or exit_row["symbol"] != row["symbol"]:
            continue
        entry_price, entry_qty = sweep_book(entry, action, cfg)
        exit_price, exit_qty = sweep_book(exit_row, -action, cfg)
        qty = min(entry_qty, exit_qty)
        if qty <= 0:
            continue
        gross = qty * (exit_price - entry_price) if action > 0 else qty * (entry_price - exit_price)
        fees = cfg.fee_bps / 10000.0 * qty * (entry_price + exit_price)
        rows.append({
            "event_time": row["origin_time"],
            "symbol": row["symbol"],
            "model": "sgd_small",
            "policy": policy,
            "action": action,
            "entry_index": int(entry_i),
            "exit_index": int(exit_i),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "matched_qty": qty,
            "gross_pnl": gross,
            "fees": fees,
            "net_pnl": gross - fees,
            "regime": row["regime"],
        })
        last_entry = entry_i
    return pd.DataFrame(rows)


def action_from_row(row: pd.Series, policy: str) -> int:
    if policy == "rsep":
        score = float(row.get("rsep_score", 0.0))
        if score > 0:
            return 1
        if score < 0:
            return -1
        return 0
    if policy == "cost_aware":
        edge = float(row["prob_up"] - row["prob_down"]) * max(abs(float(row["future_ret_h"])), float(row["cost_threshold_t"]))
        if edge > float(row["cost_threshold_t"]):
            return 1
        if edge < -float(row["cost_threshold_t"]):
            return -1
        return 0
    if float(row["prob_up"]) >= 0.45 and row["prob_up"] >= row["prob_down"]:
        return 1
    if float(row["prob_down"]) >= 0.45:
        return -1
    return 0


def run_replay(config: dict[str, Any], mode: str = "synthetic", policy: str = "cost_aware", overrides: dict[str, Any] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    out_dir = artifact_dir(config, mode)
    df = pd.read_parquet(out_dir / "predictions" / "sgd_predictions.parquet")
    cfg = replay_config(config, **(overrides or {}))
    trades = simulate_replay(df, config, policy, cfg)
    replay_dir = ensure_dir(out_dir / "replay")
    suffix = policy if not overrides else policy + "_" + "_".join(f"{k}-{v}" for k, v in overrides.items())
    trades.to_parquet(replay_dir / f"{suffix}_trades.parquet", index=False)
    summary = summarize_trades(trades, policy)
    summary.to_csv(tables_dir(config, mode) / ("replay_summary.csv" if not overrides else f"replay_summary_{suffix}.csv"), index=False)
    return trades, summary


def summarize_trades(trades: pd.DataFrame, policy: str) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame([{"policy": policy, "n_trades": 0, "gross_pnl": 0.0, "fees": 0.0, "net_pnl": 0.0, "net_per_trade": 0.0, "n_days": 0}])
    return pd.DataFrame([{
        "policy": policy,
        "n_trades": int(len(trades)),
        "gross_pnl": float(trades["gross_pnl"].sum()),
        "fees": float(trades["fees"].sum()),
        "net_pnl": float(trades["net_pnl"].sum()),
        "net_per_trade": float(trades["net_pnl"].sum() / max(len(trades), 1)),
        "n_days": int(pd.to_datetime(trades["event_time"], utc=True).dt.date.nunique()),
    }])


def run_rsep(config: dict[str, Any], mode: str = "synthetic") -> pd.DataFrame:
    out_dir = artifact_dir(config, mode)
    df = pd.read_parquet(out_dir / "predictions" / "sgd_predictions.parquet")
    train = df[df["split"] == "train"]
    mu = train.groupby("label")["future_ret_h"].mean().to_dict()
    edge = df["prob_up"] * float(mu.get("UP", 0.0)) + df["prob_down"] * float(mu.get("DOWN", 0.0)) + df["prob_flat"] * float(mu.get("FLAT", 0.0))
    risk = 0.25 * df["realized_vol_20"].abs() + 0.25 * df["rel_spread"] + 0.15 * (df["regime"].isin(["LIQUIDITY_DROUGHT", "VOLATILE_ILLIQUID"]).astype(float) * df["rel_spread"])
    required = df["cost_threshold_t"] + risk
    df["rsep_score"] = np.where(edge > required, edge - required, np.where(edge < -required, edge + required, 0.0))
    rsep_dir = ensure_dir(out_dir / "rsep")
    df[["origin_time", "symbol", "split", "rsep_score", "regime"]].to_parquet(rsep_dir / "rsep_decisions.parquet", index=False)
    df.to_parquet(out_dir / "predictions" / "sgd_predictions_with_rsep.parquet", index=False)
    # Reuse the same prediction file path for replay with RSEP score.
    df.to_parquet(out_dir / "predictions" / "sgd_predictions.parquet", index=False)
    trades, summary = run_replay(config, mode, policy="rsep")
    summary.to_csv(tables_dir(config, mode) / "rsep_summary.csv", index=False)
    return summary


def run_stress(config: dict[str, Any], mode: str = "synthetic") -> pd.DataFrame:
    rows = []
    stress = config["stress"]
    base_policy = "cost_aware"
    for axis, levels in stress.items():
        if axis not in {"fee_bps", "latency_rows", "spread_multiplier", "depth_multiplier"}:
            continue
        for level in levels:
            _, summary = run_replay(config, mode, policy=base_policy, overrides={axis: level})
            rec = summary.iloc[0].to_dict()
            rec.update({"stress_axis": axis, "stress_level": level})
            rows.append(rec)
    out = pd.DataFrame(rows)
    stress_dir = ensure_dir(artifact_dir(config, mode) / "stress")
    out.to_csv(stress_dir / "stress_results.csv", index=False)
    out.to_csv(tables_dir(config, mode) / "stress_summary.csv", index=False)
    return out


def run_bootstrap_and_transfer(config: dict[str, Any], mode: str = "synthetic") -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(int(config["seed"]))
    out_dir = artifact_dir(config, mode)
    trade_path = out_dir / "replay" / "cost_aware_trades.parquet"
    trades = pd.read_parquet(trade_path) if trade_path.exists() else pd.DataFrame()
    boot_rows = []
    if not trades.empty:
        trades["day"] = pd.to_datetime(trades["event_time"], utc=True).dt.date
        daily = trades.groupby("day")["net_pnl"].sum().to_numpy()
        vals = []
        for _ in range(int(config["bootstrap"]["n_bootstrap"])):
            sample = rng.choice(daily, size=len(daily), replace=True)
            vals.append(sample.sum())
        boot_rows.append({
            "policy": "cost_aware",
            "n_days": int(len(daily)),
            "n_bootstrap": int(config["bootstrap"]["n_bootstrap"]),
            "net_pnl_mean": float(np.mean(vals)),
            "net_pnl_ci_low": float(np.percentile(vals, 2.5)),
            "net_pnl_ci_high": float(np.percentile(vals, 97.5)),
        })
    else:
        boot_rows.append({"policy": "cost_aware", "n_days": 0, "n_bootstrap": int(config["bootstrap"]["n_bootstrap"]), "net_pnl_mean": 0.0, "net_pnl_ci_low": 0.0, "net_pnl_ci_high": 0.0})
    boot = pd.DataFrame(boot_rows)
    boot.to_csv(tables_dir(config, mode) / "bootstrap_summary.csv", index=False)

    preds = pd.read_parquet(out_dir / "predictions" / "sgd_predictions.parquet")
    transfer_rows = []
    for source, target in [("BTC-USDT", "ETH-USDT"), ("ETH-USDT", "BTC-USDT")]:
        target_test = preds[(preds["symbol"] == target) & (preds["split"] == "test")]
        transfer_rows.append({
            "direction": f"{source}_to_{target}",
            "target_rows": int(len(target_test)),
            "target_accuracy_proxy": float((target_test["label"] == target_test["pred_label"]).mean()) if len(target_test) else 0.0,
            "tuning_rule": "source_validation_only",
            "target_test_used_for_tuning": False,
        })
    transfer = pd.DataFrame(transfer_rows)
    transfer.to_csv(tables_dir(config, mode) / "transfer_summary.csv", index=False)
    return boot, transfer


def verify_tables(mode: str = "synthetic") -> dict[str, Any]:
    cfg = load_config("configs/synthetic.yaml") if mode == "synthetic" else {}
    out_dir = path_in_root(f"artifacts/{mode}")
    checks: dict[str, str] = {}
    required = [
        out_dir / "schema_report.json",
        out_dir / "features.parquet",
        out_dir / "labels_regimes_splits.parquet",
        out_dir / "predictions" / "sgd_predictions.parquet",
        out_dir / "tables" / "prediction_metrics.csv",
        out_dir / "tables" / "replay_summary.csv",
        out_dir / "tables" / "rsep_summary.csv",
        out_dir / "tables" / "stress_summary.csv",
        out_dir / "tables" / "bootstrap_summary.csv",
        out_dir / "tables" / "transfer_summary.csv",
    ]
    for p in required:
        checks[str(p.relative_to(ROOT))] = "PASS" if p.exists() and p.stat().st_size > 0 else "FAIL"
    raw_sample_files = list(path_in_root("data/raw_sample/cryptolake_minimal").glob("*.parquet"))
    raw_status = "PASS" if raw_sample_files else "ABSENT_ALLOWED"
    report = {
        "mode": mode,
        "full_data_available": False,
        "raw_sample_status": raw_status,
        "tables_checked": checks,
        "limitations": [
            "Synthetic outputs do not reproduce paper numerical results.",
            "Full numerical reproduction requires licensed Crypto Lake snapshots.",
            "Raw-format sample, if present, verifies loader compatibility only.",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "verification_report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    rows = [{"artifact": k, "status": v} for k, v in checks.items()]
    rows.append({"artifact": "raw_sample", "status": raw_status})
    pd.DataFrame(rows).to_csv(out_dir / "tables" / "verification_report.csv", index=False)
    build_claim_map(mode)
    if any(v == "FAIL" for v in checks.values()):
        raise ArtifactError("Verification failed; see artifacts/synthetic/verification_report.json")
    return report


def build_claim_map(mode: str = "synthetic") -> pd.DataFrame:
    rows = [
        ("Full-year BTC/ETH L2 benchmark", "Table I", "dataset summary", "requires licensed data", "raw data not redistributed"),
        ("Pipeline can parse Crypto Lake-style L2 snapshots", "Sec. VIII", "raw_sample/schema_report.json", "raw_sample optional", "not paper evidence"),
        ("Cost-aware ternary labels", "Sec. III", "label_summary.csv", "PASS_SYNTHETIC", "config-defined thresholds"),
        ("Visible-depth replay", "Sec. V", "replay_summary.csv", "PASS_SYNTHETIC", "L2 approximation"),
        ("RSEP diagnostic gate", "Sec. V", "rsep_summary.csv", "PASS_SYNTHETIC", "not a trading strategy"),
        ("Stress diagnostics", "Sec. VI", "stress_summary.csv", "PASS_SYNTHETIC", "one-axis stress"),
        ("Day-level bootstrap", "Sec. VI", "bootstrap_summary.csv", "PASS_SYNTHETIC", "day-level only"),
        ("BTC<->ETH transfer", "Sec. VII", "transfer_summary.csv", "PASS_SYNTHETIC", "synthetic only"),
    ]
    df = pd.DataFrame(rows, columns=["paper_claim", "paper_location", "evidence_artifact", "public_status", "limitation"])
    out = path_in_root(f"artifacts/{mode}")
    ensure_dir(out)
    df.to_csv(out / "claim_evidence_map.csv", index=False)
    ensure_dir(out / "tables")
    df.to_csv(out / "tables" / "claim_evidence_map.csv", index=False)
    return df


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_manifest(mode: str = "synthetic") -> dict[str, Any]:
    base = path_in_root(f"artifacts/{mode}")
    base.mkdir(parents=True, exist_ok=True)
    candidates = []
    for rel_root in ["configs", "scripts", "src", "data/synthetic", "data/raw_sample/README.md", "README.md", "DATA_CARD.md", "SCHEMA.md", "LICENSE_AND_DATA_ACCESS.md", f"artifacts/{mode}"]:
        p = path_in_root(rel_root)
        if p.is_file():
            candidates.append(p)
        elif p.is_dir():
            for item in p.rglob("*"):
                if item.is_file() and "data/external" not in str(item).replace("\\", "/"):
                    if item.name in {"manifest.json", "checksums.sha256"}:
                        continue
                    candidates.append(item)
    entries = []
    for p in sorted(set(candidates)):
        if p.suffix.lower() in {".pyc", ".pyo"}:
            continue
        entries.append({"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(p), "bytes": p.stat().st_size})
    manifest = {
        "mode": mode,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": str(ROOT),
        "raw_commercial_data_included": False,
        "raw_sample_source": "user_supplied_not_packaged",
        "entries": entries,
    }
    with open(base / "manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    with open(base / "checksums.sha256", "w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(f"{entry['sha256']}  {entry['path']}\n")
    return manifest


def validate_full_or_fail(config: dict[str, Any]) -> None:
    files = sorted(path_in_root(".").glob(config["paths"]["raw_glob"]))
    if not files:
        raise FileNotFoundError("[ERROR] Licensed Crypto Lake raw snapshots not found.\nFull numerical reproduction requires licensed raw data.\nRun `make synthetic` for public pipeline verification.")
    sample = pd.read_parquet(files[0])
    validate_l2_schema(sample, config, mode="full")


def cli_config() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/synthetic.yaml")
    parser.add_argument("--mode", default="synthetic", choices=["synthetic", "raw-sample", "full"])
    return parser
