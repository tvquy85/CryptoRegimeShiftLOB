from __future__ import annotations


def execution_columns(*, include_split: bool = False) -> list[str]:
    core = [
        "event_time",
        "label_horizon_events",
        "mid_price",
        "spread",
        "rel_spread",
        "label_fee_bps",
        "future_ret_h",
        "label",
        "regime",
        "prob_down",
        "prob_flat",
        "prob_up",
        "pred_label",
        "latency_sensitivity_score",
        "liquidity_drought_score",
        "adverse_selection_score",
    ]
    if include_split:
        core.append("split")
    book = []
    for level in range(20):
        book.extend(
            [
                f"bid_{level}_price",
                f"bid_{level}_size",
                f"ask_{level}_price",
                f"ask_{level}_size",
            ]
        )
    return [*core, *book]
