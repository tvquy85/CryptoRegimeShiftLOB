from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_config, resolve_path


STRESS_AXIS_UNITS = {
    "fee_bps": "basis_points",
    "latency_events": "snapshot_events",
    "spread_multiplier": "multiplier",
    "depth_multiplier": "multiplier",
}


def load_stress_grid(config: dict[str, Any]) -> dict[str, list[float | int]]:
    """Load stress grid from canonical config, falling back to inline grid."""
    grid = config.get("stress_grid", {})
    grid_config = config.get("stress_grid_config")
    if grid_config:
        stress_config = load_config(resolve_path(config, str(grid_config)))
        grid = stress_config.get("stress_grid", {})
    return normalize_stress_grid(grid)


def normalize_stress_grid(grid: dict[str, Any]) -> dict[str, list[float | int]]:
    if not grid:
        return {}
    normalized: dict[str, list[float | int]] = {}
    unknown_axes = sorted(set(grid) - set(STRESS_AXIS_UNITS))
    if unknown_axes:
        raise ValueError(f"Unknown stress axes: {unknown_axes}")
    for axis in STRESS_AXIS_UNITS:
        if axis not in grid:
            continue
        levels = list(grid[axis] or [])
        if not levels:
            raise ValueError(f"Stress axis {axis} has no levels.")
        if axis == "latency_events":
            normalized[axis] = [int(level) for level in levels]
        else:
            normalized[axis] = [float(level) for level in levels]
    return normalized


def stress_grid_source(config: dict[str, Any]) -> str:
    grid_config = config.get("stress_grid_config")
    if not grid_config:
        return "inline stress_grid"
    return str(resolve_path(config, str(grid_config)))
