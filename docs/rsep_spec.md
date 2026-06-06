# RSEP Executable Specification

RSEP is a selective-execution gate. It is not a forecasting model, not a live trading system, and not a profitability claim.

## Inputs at decision time `t`

- Forecast probabilities: `prob_up`, `prob_flat`, `prob_down`.
- Train-split class-return means: `mu_UP`, `mu_FLAT`, `mu_DOWN`.
- Cost inputs: `rel_spread`, simulator `fee_bps`.
- Risk inputs: `latency_sensitivity_score`, `liquidity_drought_score`, `adverse_selection_score`, `regime`.
- Config constants: `lambda_latency`, `lambda_liquidity`, `lambda_adverse`, `lambda_regime`.
- Validation-selected threshold: `theta_edge`.

## Edge and cost

Expected edge:

```text
estimated_edge_t =
    prob_up_t   * mu_UP
  + prob_flat_t * mu_FLAT
  + prob_down_t * mu_DOWN
```

The class-return means are estimated from the train split only by `class_return_means_from_parquet(..., split="train")`.

Estimated cost:

```text
estimated_cost_t = rel_spread_t + fee_bps / 10000
```

The spread term is unitless relative spread. `fee_bps / 10000` converts basis points to return units.

## Risk terms

| Risk term | Code variable | Feature source | Formula / normalization |
|---|---|---|---|
| Latency risk | `latency_risk` | `latency_sensitivity_score` | `abs(latency_sensitivity_score)` |
| Liquidity risk | `liquidity_risk` | `liquidity_drought_score` | `max(liquidity_drought_score, 0)` |
| Adverse-selection risk | `adverse_risk` | `adverse_selection_score` | `max(adverse_selection_score, 0)` |
| Regime risk | `regime_risk` | `regime` | map: `LIQUIDITY_DROUGHT=1.0`, `VOLATILE_ILLIQUID=0.75`, `MOMENTUM_TOXIC=0.5`, `CHOPPY_MEAN_REVERTING=0.25`, otherwise `0.0` |

Feature construction is causal: all risk features are computed from current or trailing L2 information before the label horizon.

## Gate

```text
required_edge_t =
    estimated_cost_t
  + lambda_latency  * latency_risk_t
  + lambda_liquidity * liquidity_risk_t
  + lambda_adverse   * adverse_risk_t
  + lambda_regime    * regime_risk_t
  + theta_edge

if estimated_edge_t > required_edge_t:
    action_t = +1
elif estimated_edge_t < -required_edge_t:
    action_t = -1
else:
    action_t = 0
```

Equality abstains because the comparisons are strict.

## Default benchmark configuration

`configs/rsep_grid.yaml` defines the paper-facing default:

- `lambda_latency = 0.25`
- `lambda_liquidity = 0.25`
- `lambda_adverse = 0.25`
- `lambda_regime = 0.15`
- `theta_edge` candidates are `[0, q50, q60, q70, q80, q90, q95, q97.5, q99]` of positive validation margins.

The lambda values are singleton benchmark constants in the current evidence pack. Only `theta_edge` is selected from validation in the default experiments.

## Validation-only tuning

For RSEP, the validation margin is:

```text
positive_margin_t = max(abs(estimated_edge_t) - required_edge_t(theta_edge=0), 0)
```

Candidates are quantiles of strictly positive validation margins plus zero. The selected threshold maximizes validation `net_pnl` subject to:

```text
n_trades >= max(1000, floor(0.0005 * n_valid_rows_used))
n_trade_days >= 5
```

If no candidate satisfies the constraints, the code selects the best candidate by validation net PnL from the full candidate pool. Test rows are never used to select `theta_edge`, lambdas, class-return means, or ablation parameters.

## Ablations

- `RSEP-no-latency-risk`: set `lambda_latency=0`.
- `RSEP-no-liquidity-risk`: set `lambda_liquidity=0`.
- `RSEP-no-adverse-risk`: set `lambda_adverse=0`.
- `RSEP-no-regime-penalty`: set `lambda_regime=0`.
- `RSEP-no-cost-gate`: explicit opt-in diagnostic only; excluded from the default main ablation because it can create pathological turnover.
