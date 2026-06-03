from __future__ import annotations


def build_rsep_variants(base_policy_cfg: dict[str, float], *, include_no_cost_gate: bool = False) -> dict[str, dict[str, float]]:
    variants = {
        "RSEP-full": base_policy_cfg,
        "RSEP-no-latency-risk": {**base_policy_cfg, "lambda_latency": 0.0},
        "RSEP-no-liquidity-risk": {**base_policy_cfg, "lambda_liquidity": 0.0},
        "RSEP-no-adverse-risk": {**base_policy_cfg, "lambda_adverse": 0.0},
        "RSEP-no-regime-penalty": {**base_policy_cfg, "lambda_regime": 0.0},
    }
    if include_no_cost_gate:
        variants["RSEP-no-cost-gate"] = {**base_policy_cfg, "theta_edge": -1.0}
    return variants
