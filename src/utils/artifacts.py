from __future__ import annotations

import re
from pathlib import Path


_KNOWN_STAGE_SLUGS = {
    "stage_0_sanity_check": "stage0",
    "stage_1_small_scale": "stage1",
    "stage_2_medium_scale": "stage2",
    "stage_3_full_scale": "stage3",
}


def stage_slug(stage: str | None) -> str:
    if not stage:
        return "unknown_stage"
    if stage in _KNOWN_STAGE_SLUGS:
        return _KNOWN_STAGE_SLUGS[stage]
    return safe_slug(stage)


def safe_slug(value: str | None) -> str:
    if not value:
        return "unknown"
    slug = re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip()).strip("_").lower()
    return slug or "unknown"


def artifact_namespace(config_or_namespace: object | None) -> str:
    if isinstance(config_or_namespace, dict):
        value = config_or_namespace.get("artifact_namespace")
    else:
        value = config_or_namespace
    return "" if value in (None, "") else safe_slug(str(value))


def stage_namespace_slug(stage: str | None, namespace: object | None = None) -> str:
    current_stage = stage_slug(stage)
    current_namespace = artifact_namespace(namespace)
    if not current_namespace:
        return current_stage
    duplicate_suffix = f"_{current_stage}"
    if current_namespace.endswith(duplicate_suffix):
        current_namespace = current_namespace[: -len(duplicate_suffix)]
    elif current_namespace == current_stage:
        current_namespace = ""
    return f"{current_stage}_{current_namespace}" if current_namespace else current_stage


def namespaced_name(stem: str, namespace: object | None = None, *, suffix: str = "") -> str:
    current_namespace = artifact_namespace(namespace)
    return f"{stem}_{current_namespace}{suffix}" if current_namespace else f"{stem}{suffix}"


def namespaced_dir(path: Path, namespace: object | None = None) -> Path:
    current_namespace = artifact_namespace(namespace)
    return path / current_namespace if current_namespace else path


def stage_table_path(tables_dir: Path, stem: str, stage: str | None, *, namespace: object | None = None, suffix: str = ".csv") -> Path:
    return tables_dir / f"{stem}_{stage_namespace_slug(stage, namespace)}{suffix}"


def model_stage_table_path(
    tables_dir: Path,
    stem: str,
    stage: str | None,
    model_label: str | None,
    *,
    namespace: object | None = None,
    suffix: str = ".csv",
) -> Path:
    model = safe_slug(model_label)
    return tables_dir / f"{stem}_{stage_namespace_slug(stage, namespace)}_{model}{suffix}"


def stage_config_path(config_dir: Path, stem: str, stage: str | None, *, namespace: object | None = None, suffix: str = ".yaml") -> Path:
    return config_dir / f"{stem}_{stage_namespace_slug(stage, namespace)}{suffix}"


def is_stage2(stage: str | None) -> bool:
    return stage_slug(stage) == "stage2"
