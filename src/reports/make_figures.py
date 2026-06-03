from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_stress_curve(stress: pd.DataFrame, axis: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subset = stress[stress["axis"] == axis].sort_values("level")
    plt.figure(figsize=(6.5, 4))
    if not subset.empty:
        plt.plot(subset["level"], subset["net_pnl"], marker="o")
    plt.xlabel(axis)
    plt.ylabel("Net PnL")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path


def plot_model_stress_comparison(stress: pd.DataFrame, axis: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    required_columns = {"model", "axis", "level", "net_pnl"}
    subset = (
        stress[stress["axis"] == axis].sort_values(["model", "level"])
        if required_columns.issubset(stress.columns)
        else pd.DataFrame()
    )
    plt.figure(figsize=(7, 4))
    if not subset.empty:
        for model, model_curve in subset.groupby("model", sort=False):
            plt.plot(model_curve["level"], model_curve["net_pnl"], marker="o", label=str(model))
        plt.legend()
    plt.xlabel(axis)
    plt.ylabel("Net PnL")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path


def plot_worst_regime(by_regime: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 4))
    if not by_regime.empty:
        subset = by_regime.sort_values("net_pnl")
        plt.bar(subset["regime"].astype(str), subset["net_pnl"])
        plt.xticks(rotation=45, ha="right")
    plt.ylabel("Net PnL")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return output_path
