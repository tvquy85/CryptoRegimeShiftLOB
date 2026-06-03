from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if key == "inherits":
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        current = yaml.safe_load(handle) or {}

    inherited = current.get("inherits")
    if not inherited:
        current["_config_path"] = str(config_path)
        return current

    parent_path = (config_path.parent.parent / inherited).resolve()
    if not parent_path.exists():
        parent_path = (config_path.parent / inherited).resolve()
    parent = load_config(parent_path)
    merged = _merge(parent, current)
    merged["_config_path"] = str(config_path)
    return merged


def project_root(config: dict[str, Any]) -> Path:
    config_path = Path(config["_config_path"])
    root = Path(config.get("project_root", config_path.parent.parent))
    if not root.is_absolute():
        root = (config_path.parent.parent / root).resolve()
    return root


def resolve_path(config: dict[str, Any], value: str | Path) -> Path:
    root = project_root(config)
    path = Path(value)
    return path if path.is_absolute() else (root / path).resolve()

