from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class CommonArgs:
    config: str
    run_id: str
    stage: str
    symbol: str | None
    start: str | None
    end: str | None


def common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stage", default="stage_0_sanity_check")
    parser.add_argument("--symbol")
    parser.add_argument("--start")
    parser.add_argument("--end")
    return parser


def as_common_args(namespace: argparse.Namespace) -> CommonArgs:
    return CommonArgs(
        config=namespace.config,
        run_id=namespace.run_id,
        stage=namespace.stage,
        symbol=getattr(namespace, "symbol", None),
        start=getattr(namespace, "start", None),
        end=getattr(namespace, "end", None),
    )

