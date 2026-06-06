# Regime taxonomy specification

## Purpose

The regime taxonomy is a diagnostic grouping of observable L2 microstructure states. It is not a claim about true latent market states. Regimes are used to audit whether forecasting and execution metrics vary across liquidity, volatility, momentum, choppiness, and adverse-selection conditions.

## Causal inputs

All inputs are computed from information available at decision time `t`. Future returns, labels, predicted probabilities, execution PnL, validation outcomes, and test outcomes are not regime inputs.

Primary feature inputs:

- `rel_spread`
- `total_depth_10`
- `vol_score`
- `depth_drop_top10`
- `spread_z_1m`
- `depth_z_1m`
- `momentum_score`
- `choppiness_score`
- `adverse_selection_score`
- `liquidity_drought_score`

Derived diagnostic scores:

```text
liquidity_score = depth_z_1m - spread_z_1m
stress_score = vol_score + spread_z_1m - depth_z_1m
directional_toxicity_score = abs(momentum_score) + adverse_selection_score
```

## Threshold fitting

Thresholds are fitted on the first `train_fraction_for_thresholds = 0.6` chronological prefix only. This corresponds to the training prefix used by the locked Stage 3 split. Validation and test rows are not used to fit quantiles or choose the taxonomy.

Default quantiles:

```text
low = 0.40
mid = 0.50
high = 0.70
very_high = 0.80
very_low = 0.10
```

The main threshold artifacts are:

- BTC: `data/regimes/regime_thresholds.json`
- ETH: `data/regimes/regime_thresholds_eth_stage3.json`

## Priority order

Rules are applied in this exact order. A row assigned by an earlier rule is not reassigned by later rules.

1. `LIQUIDITY_DROUGHT`
2. `MOMENTUM_TOXIC`
3. `VOLATILE_ILLIQUID`
4. `CHOPPY_MEAN_REVERTING`
5. `SHOCK_RECOVERY`
6. `VOLATILE_LIQUID`
7. `CALM_ILLIQUID`
8. `CALM_LIQUID`
9. `MILD_LIQUIDITY_STRESS`
10. `BALANCED_TRANSITION`
11. `UNKNOWN` fallback

## Rule definitions

- `LIQUIDITY_DROUGHT`: `depth_drop_top10 <= depth_drop_q10` and `spread_z_1m >= spread_z_q80`.
- `MOMENTUM_TOXIC`: `abs(momentum_score) >= momentum_abs_q80` and `adverse_selection_score >= adverse_q70`.
- `VOLATILE_ILLIQUID`: `vol_score >= vol_q70`, `rel_spread >= spread_q70`, and `total_depth_10 <= depth_q40`.
- `CHOPPY_MEAN_REVERTING`: `choppiness_score >= flip_q70` and `abs(momentum_score) <= momentum_abs_q50`.
- `SHOCK_RECOVERY`: `vol_score >= vol_q70`, `depth_drop_top10 > depth_drop_q10`, and `spread_z_1m < spread_z_q80`.
- `VOLATILE_LIQUID`: `vol_score >= vol_q70`, `rel_spread <= spread_q40`, and `total_depth_10 >= depth_q60`.
- `CALM_ILLIQUID`: `vol_score <= vol_q40`, `rel_spread >= spread_q70`, and `total_depth_10 <= depth_q40`.
- `CALM_LIQUID`: `vol_score <= vol_q40`, `rel_spread <= spread_q40`, and `total_depth_10 >= depth_q60`.
- `MILD_LIQUIDITY_STRESS`: moderate liquidity deterioration based on `liquidity_score`, `stress_score`, and `liquidity_drought_score`, bounded below the strict drought priority.
- `BALANCED_TRANSITION`: residual structured state with low to moderate `stress_score`, low `directional_toxicity_score`, and not-severely-bad `liquidity_score`.
- `UNKNOWN`: no rule matched. UNKNOWN observations are retained and reported; they are not redistributed into more favorable regimes.

## Sensitivity protocol

The audit script evaluates three quantile settings on deterministic samples:

- `baseline`: `low=0.40`, `high=0.70`, `very_low=0.10`, `very_high=0.80`.
- `strict_extremes`: `low=0.45`, `high=0.75`, `very_low=0.05`, `very_high=0.85`.
- `relaxed_extremes`: `low=0.35`, `high=0.65`, `very_low=0.15`, `very_high=0.75`.

Sensitivity results are diagnostic only. They are not used to retune the taxonomy on test data.
