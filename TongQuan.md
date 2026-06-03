# CryptoRegimeShift-LOB: Codex Experiment Specification for ICDM 2026

**Working paper title**  
**CryptoRegimeShift-LOB: Benchmarking Robust HFT Policy Learning under L2 Microstructure Regime Shifts**

**Target venue**  
IEEE ICDM 2026 Main Conference / Research Track.

**Current hard deadline**  
Main full-paper submission: **2026-06-06 AoE**.

**Current compute target**  
Single workstation with **NVIDIA RTX 3090 24GB**.

**Current paid data resource**  
Crypto Lake `book` data for:

- `BINANCE` or selected exchange: `BTC-USDT`
- `BINANCE` or selected exchange: `ETH-USDT`
- 1 full year
- L2 order book snapshots, 20 levels per side
- Parquet partitions by exchange, symbol, and day/month

This spec assumes **snapshot-level L2 order book data**, not LOBSTER-style event-level message data. Do not claim exact order-event reconstruction, exact queue priority, or exact cancellation/hidden-liquidity modeling unless `book_delta_v2`, trades, or L3/MBO data are later added.

---

## 0. Executive Objective

Build an ICDM-grade experimental pipeline showing that current LOB forecasting and HFT policy baselines can look reasonable under average chronological backtests, but collapse under:

1. **Unseen microstructure regimes**;
2. **Transaction-cost shifts**;
3. **Latency shifts**;
4. **Spread widening**;
5. **Depth/liquidity shocks**;
6. **Forecast-to-execution degradation**.

Then introduce a simple, defensible robust baseline:

> **RSEP: Robust Selective Execution Policy**, which trades only when estimated edge exceeds transaction cost, latency risk, liquidity risk, and adverse-selection risk.

The paper should be positioned as a **benchmark + methodology + empirical failure-mode study**, not as a “trading bot” paper.

---

## 1. Non-Negotiable Research Framing

### 1.1 Core gap

Existing HFT/RL work addresses non-stationarity with hierarchical routers, context agents, or memory modules, but standard evaluation still leans heavily on average chronological backtests. Existing LOB benchmarks focus mainly on forecasting or generative realism. There is still no widely accepted protocol for robust HFT policy learning under L2 microstructure regime shifts and execution stress.

### 1.2 Central claim

> We introduce a high-frequency crypto L2 order-book benchmark and evaluation protocol for robust HFT policy learning under microstructure regime shifts. Unlike average-case backtests, the protocol evaluates worst-regime performance, cost survival, latency decay, liquidity-shock resilience, and forecast-to-execution degradation.

### 1.3 What not to claim

Do **not** claim:

- LOBSTER event-level benchmark;
- exact order submission/cancellation/deletion modeling;
- exact queue priority;
- exact passive limit-order fill;
- hidden-liquidity detection;
- live-trading-ready execution;
- SOTA trading profit as the main contribution.

### 1.4 What to claim

Claim only:

- dense L2 snapshot-level order book benchmark;
- snapshot-derived microstructure regime taxonomy;
- regime-held-out and stress-OOD evaluation;
- forecast-to-execution degradation analysis;
- robust selective execution baseline;
- statistically tested robustness improvements.

---

## 2. Expected Repository Structure

Codex must create this repository structure:

```text
cryptoregimeshift_lob/
  README.md
  pyproject.toml
  requirements.txt
  configs/
    data_crypto_lake.yaml
    features.yaml
    regimes.yaml
    labels.yaml
    simulator.yaml
    models.yaml
    experiments_smoke.yaml
    experiments_full.yaml
  data/
    raw/                 # symlinks or local mount pointers only, do not commit
    interim/
    features/
    labels/
    regimes/
    splits/
    predictions/
    backtests/
    reports/
  src/
    __init__.py
    data/
      audit_schema.py
      crypto_lake_loader.py
      parquet_index.py
      resample.py
      calendar.py
    features/
      lob_features.py
      returns_labels.py
      ofi_proxy.py
      regime_features.py
      normalization.py
      feature_store.py
    regimes/
      rule_regime_labeler.py
      cluster_regime_labeler.py
      regime_diagnostics.py
      regime_splits.py
    models/
      tabular_baselines.py
      torch_datasets.py
      temporal_cnn.py
      deeplob_lite.py
      transformer_lite.py
      calibration.py
    policies/
      rule_based.py
      forecast_threshold.py
      rsep.py
      optional_dqn.py
      optional_ppo.py
    simulator/
      market_order_sim.py
      stress_engine.py
      execution_costs.py
      metrics.py
    evaluation/
      classification_eval.py
      trading_eval.py
      robustness_eval.py
      bootstrap.py
      statistical_tests.py
    reports/
      make_tables.py
      make_figures.py
      failure_case_studies.py
      result_pack.py
    utils/
      logging.py
      seed.py
      io.py
      gpu.py
      config.py
  scripts/
    00_audit_data.py
    01_build_features.py
    02_label_regimes.py
    03_make_splits.py
    04_train_forecasters.py
    05_backtest_forecasts.py
    06_run_rsep.py
    07_run_stress_grid.py
    08_generate_report_pack.py
    smoke_test.sh
    run_full_pipeline.sh
  notebooks/
    00_data_audit.ipynb
    01_regime_maps.ipynb
    02_failure_analysis.ipynb
  outputs/
    tables/
    figures/
    logs/
    checkpoints/
    paper_assets/
  tests/
    test_schema.py
    test_features.py
    test_labels_no_leakage.py
    test_simulator_sanity.py
    test_metrics.py
```

---

## 3. Environment Specification

### 3.1 Python version

Use Python `3.10` or `3.11`.

### 3.2 Core packages

```text
polars
pyarrow
duckdb
numpy
pandas
scipy
scikit-learn
xgboost
lightgbm
torch
torchvision
torchaudio
pytorch-lightning or lightning
tqdm
pyyaml
rich
matplotlib
plotly
statsmodels
joblib
numba
```

Optional:

```text
hdbscan
ta-lib or pandas-ta
stable-baselines3
gymnasium
wandb
mlflow
```

### 3.3 GPU policy

- Use RTX 3090 for PyTorch models and XGBoost/LightGBM GPU if stable.
- Use mixed precision for PyTorch.
- Use `float32` for feature arrays.
- Avoid loading full year into GPU memory.
- Use day-level/month-level chunking.
- Use memory-mapped arrays or Arrow/Parquet streaming.

### 3.4 Reproducibility

Every experiment must log:

- Git commit hash if available;
- config YAML;
- random seed;
- data date range;
- symbol/exchange;
- model hyperparameters;
- feature version;
- split version;
- execution simulator config;
- result artifact paths.

---

## 4. Data Assumptions

### 4.1 Crypto Lake `book` schema

Expected columns:

```text
origin_time
received_time
sequence_number

bid_0_price
bid_0_size
...
bid_19_price
bid_19_size

ask_0_price
ask_0_size
...
ask_19_price
ask_19_size

exchange
symbol
```

The loader must tolerate:

- `origin_time` missing, zero, or invalid for some rows;
- different dtypes between direct S3 and Python API outputs;
- duplicate timestamps;
- non-monotonic sequence numbers within a day;
- missing levels;
- rows with crossed books;
- bad or stale snapshots.

### 4.2 Required data audit

Implement `scripts/00_audit_data.py`.

For each `(exchange, symbol, date)` report:

```text
n_rows
first_timestamp
last_timestamp
duration_seconds
mean_snapshot_interval_ms
p50_snapshot_interval_ms
p95_snapshot_interval_ms
p99_snapshot_interval_ms
n_duplicate_timestamps
n_duplicate_sequence_numbers
n_non_monotonic_sequence
n_missing_values_by_column
n_crossed_book_rows
n_zero_or_negative_price_rows
n_zero_or_negative_size_rows
spread_stats
depth_stats
file_size_mb
```

Save:

```text
data/interim/audit/audit_by_day.parquet
outputs/tables/table_data_audit.csv
outputs/figures/snapshot_interval_distribution_{symbol}.png
outputs/figures/spread_distribution_{symbol}.png
```

### 4.3 Cleaning rules

- Remove rows where best bid or best ask is null/zero/non-positive.
- Remove rows where `bid_0_price > ask_0_price` unless explicitly retained for a “bad book” diagnostic table.
- Sort by `origin_time` if valid; otherwise use `received_time`; use `sequence_number` to break ties.
- Convert all numeric features to `float32` after audit.
- Preserve original timestamps in metadata.
- Do not forward-fill book values except inside controlled resampling modules.

---

## 5. Feature Engineering

Implement `src/features/lob_features.py`, `src/features/ofi_proxy.py`, and `src/features/regime_features.py`.

### 5.1 Basic L2 features

For each row:

```text
mid_price = (bid_0_price + ask_0_price) / 2
spread = ask_0_price - bid_0_price
rel_spread = spread / mid_price
microprice = (ask_0_price * bid_0_size + bid_0_price * ask_0_size) / (bid_0_size + ask_0_size)
microprice_deviation = (microprice - mid_price) / mid_price
```

### 5.2 Depth features

For `k in {1, 3, 5, 10, 20}`:

```text
bid_depth_k = sum(bid_i_size for i < k)
ask_depth_k = sum(ask_i_size for i < k)
total_depth_k = bid_depth_k + ask_depth_k
depth_imbalance_k = (bid_depth_k - ask_depth_k) / (bid_depth_k + ask_depth_k + eps)
depth_ratio_k = bid_depth_k / (ask_depth_k + eps)
```

### 5.3 Book slope and liquidity concentration

For both sides:

```text
bid_price_distance_i = (bid_0_price - bid_i_price) / mid_price
ask_price_distance_i = (ask_i_price - ask_0_price) / mid_price
bid_depth_weighted_distance = sum(size_i * price_distance_i) / sum(size_i)
ask_depth_weighted_distance = sum(size_i * price_distance_i) / sum(size_i)
book_slope_bid_k = depth_k / (abs(bid_0_price - bid_{k-1}_price) + eps)
book_slope_ask_k = depth_k / (abs(ask_{k-1}_price - ask_0_price) + eps)
top_depth_share_bid = bid_depth_1 / bid_depth_20
top_depth_share_ask = ask_depth_1 / ask_depth_20
```

### 5.4 Snapshot-derived OFI proxy

Because we do not have order-event messages, compute OFI proxy from book-state changes.

For level 0:

```text
delta_bid_size_cond =
  if bid_0_price_t > bid_0_price_{t-1}: bid_0_size_t
  elif bid_0_price_t == bid_0_price_{t-1}: bid_0_size_t - bid_0_size_{t-1}
  else: -bid_0_size_{t-1}

delta_ask_size_cond =
  if ask_0_price_t < ask_0_price_{t-1}: ask_0_size_t
  elif ask_0_price_t == ask_0_price_{t-1}: ask_0_size_t - ask_0_size_{t-1}
  else: -ask_0_size_{t-1}

ofi_1 = delta_bid_size_cond - delta_ask_size_cond
```

Extend to top-k by summing aligned level-wise approximations, but treat it as a **proxy**, not exact order flow.

### 5.5 Return and volatility features

Use row/event index and wall-clock windows.

Event horizons:

```text
h_events = [10, 50, 100, 500, 1000]
```

Wall-clock horizons:

```text
h_seconds = [1, 5, 10, 30, 60]
```

Features:

```text
mid_return_{h}
log_return_{h}
realized_vol_{window}
abs_return_{window}
return_autocorr_{window}
up_down_flip_rate_{window}
```

Windows:

```text
event_windows = [100, 500, 1000, 5000]
time_windows = ["10s", "1m", "5m", "15m"]
```

### 5.6 Liquidity shock features

```text
spread_z_1m
depth_z_1m
depth_drop_top5 = (depth_top5_t - rolling_median_depth_top5_5m) / rolling_median_depth_top5_5m
top_level_depletion_flag
spread_widening_flag
liquidity_drought_score
```

### 5.7 Adverse-selection proxy

For a hypothetical market buy/sell at time `t`, compute post-trade movement after horizons:

```text
buy_adverse_{h} = (mid_t - mid_{t+h}) / mid_t
sell_adverse_{h} = (mid_{t+h} - mid_t) / mid_t
```

This is a diagnostic proxy, not a trade execution guarantee.

### 5.8 Normalized LOB tensor features for deep models

For each row and level:

```text
ask_price_i_norm = (ask_i_price - mid_price) / mid_price
bid_price_i_norm = (bid_i_price - mid_price) / mid_price
ask_size_i_norm = log1p(ask_i_size) standardized by training split only
bid_size_i_norm = log1p(bid_i_size) standardized by training split only
```

Deep input tensor shape:

```text
[window_length, 80]
```

with 20 levels × 4 values.

Recommended:

```text
window_length_events = [100, 200]
levels_for_deep_models = 10 by default, 20 in ablation
```

---

## 6. Labeling Protocol

Implement `src/features/returns_labels.py`.

### 6.1 Cost-aware ternary labels

For horizon `h`:

```text
future_ret_h = (mid_{t+h} - mid_t) / mid_t
cost_threshold_t = rel_spread_t + fee_bps / 10000 + slippage_buffer_t
```

Labels:

```text
UP   if future_ret_h >  cost_threshold_t
DOWN if future_ret_h < -cost_threshold_t
FLAT otherwise
```

Default fee assumptions:

```text
fee_bps = [0, 1, 2, 5]
slippage_buffer_t = 0.5 * rel_spread_t
```

For forecasting experiments, use `fee_bps = 1` and report sensitivity.

### 6.2 Leakage control

- Labels may use future `mid_{t+h}`.
- Features must use only data up to and including `t`.
- Regime features used for training must be causal rolling features.
- Ex-post regime labels may be used only for evaluation/failure diagnostics.

Implement test:

```text
tests/test_labels_no_leakage.py
```

---

## 7. Regime Taxonomy

Implement both a rule-based regime labeler and an optional clustering labeler.

### 7.1 Causal regime features

Use trailing windows only:

```text
vol_score
spread_score
depth_score
imbalance_score
ofi_proxy_score
liquidity_drought_score
momentum_score
choppiness_score
latency_sensitivity_score
adverse_selection_score
```

### 7.2 Rule-based regimes

Create at minimum these regimes:

```text
CALM_LIQUID
CALM_ILLIQUID
VOLATILE_LIQUID
VOLATILE_ILLIQUID
MOMENTUM_TOXIC
CHOPPY_MEAN_REVERTING
LIQUIDITY_DROUGHT
SHOCK_RECOVERY
UNKNOWN
```

Example logic:

```text
CALM_LIQUID:
  vol_score <= q40 AND rel_spread <= q40 AND total_depth_10 >= q60

VOLATILE_ILLIQUID:
  vol_score >= q70 AND rel_spread >= q70 AND total_depth_10 <= q40

LIQUIDITY_DROUGHT:
  depth_drop_top10 <= q10 AND spread_z_1m >= q80

MOMENTUM_TOXIC:
  abs(momentum_score) >= q80 AND adverse_selection_score >= q70

CHOPPY_MEAN_REVERTING:
  flip_rate >= q70 AND abs(momentum_score) <= q50
```

Quantiles must be computed on the **training split only** and then applied to validation/test.

### 7.3 Clustering regimes

Optional but recommended for paper credibility:

- Standardize causal regime features on training data.
- Fit `KMeans`, `GMM`, or `HDBSCAN`.
- Select cluster count using stability + interpretability, not only silhouette.
- Map clusters to human-readable names using feature medians.
- Compare rule-based vs clustering regimes.

### 7.4 Regime diagnostics

Save:

```text
outputs/tables/table_regime_counts_by_symbol_month.csv
outputs/tables/table_regime_feature_medians.csv
outputs/figures/regime_calendar_{symbol}.png
outputs/figures/regime_umap_or_pca_{symbol}.png
outputs/figures/regime_spread_depth_vol_boxplots.png
```

---

## 8. Experimental Splits

Implement `src/regimes/regime_splits.py`.

### 8.1 Chronological split

Default:

```text
Train: first 8 months
Validation: next 2 months
Test: last 2 months
```

### 8.2 Walk-forward monthly split

For each test month:

```text
train_window = previous 3 or 6 months
valid_window = previous 2 weeks
test_window = current month
```

Report mean ± std across test months.

### 8.3 Asset-held-out split

```text
Train BTC-USDT -> Test ETH-USDT
Train ETH-USDT -> Test BTC-USDT
Train BTC+ETH mixed -> Test BTC and ETH separately
```

### 8.4 Regime-held-out split

For each target regime `r`:

```text
Train: all windows excluding regime r
Validation: non-r validation windows
Test: only regime r windows
```

At least run:

```text
LIQUIDITY_DROUGHT
VOLATILE_ILLIQUID
MOMENTUM_TOXIC
CHOPPY_MEAN_REVERTING
```

### 8.5 Stress-OOD split

Do not alter features. Alter execution environment in simulator:

```text
fee_bps_grid = [0, 1, 2, 5, 10]
latency_events_grid = [0, 1, 5, 10, 20, 50]
spread_multiplier_grid = [1.0, 1.5, 2.0]
depth_multiplier_grid = [1.0, 0.75, 0.5, 0.25]
trade_size_grid = ["small", "medium", "large"]
```

---

## 9. Forecasting Models

Implement `scripts/04_train_forecasters.py`.

### 9.1 Baseline 1: Logistic/SGD

- Input: tabular causal features.
- Model: multinomial logistic regression or `SGDClassifier(loss="log_loss")`.
- Class weights for imbalance.
- Calibrated probability output.

### 9.2 Baseline 2: XGBoost / LightGBM

- Input: tabular causal features.
- Use GPU if stable.
- Objective: multiclass.
- Early stopping on validation macro-F1 or MCC.
- Save feature importance and SHAP sample if feasible.

### 9.3 Baseline 3: TCN / Temporal CNN

- Input: `[window, features]`.
- Levels: top-10 by default.
- Use mixed precision.
- Early stopping.
- Keep model small enough for RTX 3090.

### 9.4 Baseline 4: DeepLOB-lite

Simplified architecture:

```text
Conv2D/Conv1D blocks over LOB levels and time
Inception-style temporal block optional
LSTM/GRU or temporal pooling
Dense classifier
```

Keep training tractable.

### 9.5 Optional baseline 5: Transformer-lite

Only run if time permits:

```text
2-4 layers
4-8 heads
embedding dim 64/128
sequence length <= 200
```

### 9.6 Forecasting metrics

Overall and by regime:

```text
accuracy
macro_f1
weighted_f1
MCC
balanced_accuracy
AUC one-vs-rest if feasible
ECE calibration
class distribution
confusion matrix
```

Save:

```text
outputs/tables/table_forecasting_overall.csv
outputs/tables/table_forecasting_by_regime.csv
outputs/figures/confusion_by_regime_{model}.png
outputs/figures/calibration_{model}.png
```

---

## 10. Execution Simulator

Implement `src/simulator/market_order_sim.py`.

### 10.1 Scope

The simulator is an L2 snapshot replay simulator. It supports marketable order execution through visible order book depth. It does not simulate true passive queue priority.

### 10.2 Actions

Minimum action space:

```text
-1 = sell / short exposure
 0 = flat / no trade
+1 = buy / long exposure
```

Policy output can be:

```text
target_position in {-1, 0, +1}
```

Optional execution-aware action:

```text
MARKET_BUY
MARKET_SELL
CLOSE_POSITION
HOLD
NO_TRADE
```

### 10.3 Marketable execution

For buy:

```text
consume ask levels from ask_0 upward until target notional or size is filled
execution_price = volume_weighted_price
slippage = execution_price - ask_0_price
```

For sell:

```text
consume bid levels from bid_0 downward
execution_price = volume_weighted_price
slippage = bid_0_price - execution_price
```

If requested size exceeds visible top-20 depth:

```text
partial fill if partial_fill=True
or reject trade if partial_fill=False
```

Default:

```text
partial_fill=True
min_fill_ratio=0.5
```

### 10.4 Latency

If policy generates action at row `t`, execute at:

```text
t_exec = t + latency_events
```

Also implement wall-clock latency later if timestamps are reliable.

### 10.5 Costs

```text
fee = notional * fee_bps / 10000
spread_cost implicit through bid/ask execution
slippage_cost from depth sweep
```

### 10.6 Stress transforms

At execution time only:

```text
spread_multiplier:
  widen ask and bid away from mid

depth_multiplier:
  multiply all visible sizes by factor

fill_probability:
  Bernoulli fill; if unfilled, action becomes no-trade or delayed retry

trade_size_multiplier:
  small/medium/large notional relative to rolling top-10 depth
```

### 10.7 Simulator sanity tests

Implement `tests/test_simulator_sanity.py`.

Required tests:

- No trade => zero transaction cost and flat PnL.
- Buy then immediate sell with zero price movement => negative PnL due to spread/fee.
- Higher fee must not increase net PnL.
- Higher latency must alter execution timestamp.
- Lower depth must weakly increase slippage or reduce fill.
- Crossed/invalid book rows are skipped.

---

## 11. Forecast-to-Execution Degradation

Implement `scripts/05_backtest_forecasts.py`.

Convert model probabilities to actions.

### 11.1 Naive threshold policy

```text
buy if P(UP) > theta
sell if P(DOWN) > theta
flat otherwise
```

Tune `theta` on validation.

### 11.2 Cost-aware threshold policy

```text
expected_edge = E[return | model probabilities]
trade if expected_edge > estimated_cost
```

### 11.3 Degradation metrics

For every model and regime:

```text
forecast_macro_f1
gross_pnl
net_pnl
gross_to_net_survival = net_pnl / gross_pnl
cost_to_gross_ratio = total_cost / abs(gross_pnl)
turnover
net_pnl_per_trade
latency_decay
fee_decay
worst_regime_return
regime_gap
```

Main expected insight:

> High forecasting score often does not survive execution costs, especially under volatile-illiquid and liquidity-drought regimes.

---

## 12. RSEP: Robust Selective Execution Policy

Implement `src/policies/rsep.py` and `scripts/06_run_rsep.py`.

### 12.1 Decision rule

```text
trade if:
  estimated_edge_t >
    estimated_cost_t
    + lambda_latency * latency_risk_t
    + lambda_liquidity * liquidity_risk_t
    + lambda_adverse * adverse_selection_risk_t
    + lambda_regime * regime_risk_t
```

### 12.2 Estimated edge

Use one of:

```text
edge_from_prob = P(UP) * up_return_mean - P(DOWN) * down_return_mean
edge_from_return_model = predicted_return
edge_from_calibrated_score = calibrated expected class return
```

Default: calibrated expected class return.

### 12.3 Estimated cost

```text
estimated_cost =
  rel_spread
  + fee_bps / 10000
  + expected_depth_slippage
```

### 12.4 Risk terms

```text
latency_risk = rolling std / expected absolute slippage after latency_events
liquidity_risk = z(rel_spread) - z(depth_top10)
adverse_selection_risk = predicted or trailing adverse_selection_proxy
regime_risk = learned penalty for target regime from validation performance
```

### 12.5 Training/tuning

Tune on validation only:

```text
theta_edge
lambda_latency
lambda_liquidity
lambda_adverse
lambda_regime
max_turnover
cooldown_events
max_position_holding_events
```

Use grid search or Optuna.

Primary tuning objective:

```text
maximize:
  validation_mean_net_return
  - alpha * validation_regime_gap
  - beta * validation_max_drawdown
  - gamma * turnover
```

Also report alternative objective:

```text
maximize worst_regime_return
```

### 12.6 Ablations

Run:

```text
RSEP-full
RSEP-no-latency-risk
RSEP-no-liquidity-risk
RSEP-no-adverse-risk
RSEP-no-regime-penalty
RSEP-no-cost-gate
naive-threshold
cost-aware-threshold
```

---

## 13. Optional RL Policy Learning

This is optional. Do not let it block the core benchmark.

### 13.1 DQN/PPO-lite

If implemented:

- Downsample to 1s or event stride 10/50.
- State: compact feature vector, not full tensor.
- Actions: {-1, 0, +1}.
- Reward: net change in equity after costs.
- Use chronological train/validation/test only initially.
- Report as a baseline, not as the main method.

### 13.2 Simplified regime router

Optional:

- Train separate threshold/RSEP configs per regime.
- Router selects config based on current causal regime.
- Compare with global RSEP.

This is safer than full hierarchical RL.

---

## 14. Robustness Metrics

Implement `src/evaluation/robustness_eval.py`.

### 14.1 Worst-regime return

```text
WRR = min_r Return_r
```

### 14.2 Regime performance gap

```text
RegimeGap = max_r Return_r - min_r Return_r
```

### 14.3 Robustness AUC

For each stress axis `s` with levels `l`:

```text
RobustnessAUC_s = normalized area under NetReturn(l)
```

Report for:

```text
fee
latency
spread_multiplier
depth_multiplier
fill_probability
```

### 14.4 Cost survival rate

```text
CostSurvival = NetPnL / GrossPnL
```

Handle sign carefully. If gross PnL <= 0, report separately.

### 14.5 Latency half-life

Smallest latency level where:

```text
NetReturn(latency) <= 0.5 * NetReturn(latency=0)
```

If initial return <= 0, mark as invalid.

### 14.6 Forecast-to-execution edge survival

```text
EdgeSurvival = profitable_signals_after_cost / profitable_signals_before_cost
```

### 14.7 Adverse-selection loss

For executed buys/sells:

```text
buy_adverse_loss_h = max(0, entry_mid - mid_{t+h})
sell_adverse_loss_h = max(0, mid_{t+h} - entry_mid)
```

Normalize by notional.

---

## 15. Statistical Testing

Implement `src/evaluation/bootstrap.py`.

### 15.1 Unit of resampling

Use **day-level paired bootstrap**, not row-level bootstrap.

### 15.2 Confidence intervals

For key metrics:

```text
mean net return
worst-regime return
regime gap
robustness AUC
cost survival rate
```

Use:

```text
1000 bootstrap samples
95% confidence intervals
```

### 15.3 Significance

Compare RSEP-full vs strongest baseline using paired bootstrap differences.

Optional correction:

```text
Holm-Bonferroni
```

### 15.4 Seeds

For deep models:

```text
seeds = [1, 2, 3]
```

Minimum if time-limited:

```text
seeds = [1]
```

But final ICDM paper should include at least 3 seeds for deep models or justify deterministic tabular baselines.

---

## 16. Required Paper Tables and Figures

### 16.1 Main tables

1. **Dataset statistics**  
   Rows, duration, median snapshot interval, spread, depth, volatility.

2. **Regime distribution**  
   Counts and duration by symbol/month/regime.

3. **Forecasting performance by regime**  
   Accuracy, macro-F1, MCC overall and by regime.

4. **Forecast-to-execution degradation**  
   Forecast metrics vs gross/net PnL, cost survival, turnover.

5. **Robust policy comparison**  
   Net return, MDD, turnover, WRR, RegimeGap, RobustnessAUC.

6. **Ablation table**  
   RSEP variants.

7. **Stress-test table**  
   Fee/latency/depth/spread performance.

### 16.2 Main figures

1. Regime calendar heatmap.
2. Spread-depth-volatility regime map.
3. Forecasting score vs net PnL scatter.
4. Fee stress curve.
5. Latency decay curve.
6. Depth shock robustness curve.
7. Worst-regime bar plot.
8. Case study: liquidity drought failure window.

### 16.3 Paper-ready output paths

```text
outputs/paper_assets/table_1_dataset_stats.csv
outputs/paper_assets/table_2_regime_distribution.csv
outputs/paper_assets/table_3_forecasting_by_regime.csv
outputs/paper_assets/table_4_forecast_to_execution.csv
outputs/paper_assets/table_5_robust_policy.csv
outputs/paper_assets/table_6_ablation.csv

outputs/paper_assets/fig_1_regime_calendar.pdf
outputs/paper_assets/fig_2_regime_feature_map.pdf
outputs/paper_assets/fig_3_forecast_vs_execution.pdf
outputs/paper_assets/fig_4_fee_stress.pdf
outputs/paper_assets/fig_5_latency_decay.pdf
outputs/paper_assets/fig_6_worst_regime.pdf
```

---

## 17. Experiment Commands

### 17.1 Setup

```bash
conda create -n crlob python=3.10 -y
conda activate crlob
pip install -r requirements.txt
```

### 17.2 Smoke test

Use one week of BTC and one week of ETH.

```bash
bash scripts/smoke_test.sh
```

Expected:

```text
data audit completes
features generated
regimes labeled
one tabular model trained
one backtest runs
RSEP runs
report pack generated
all tests pass
```

### 17.3 Full feature pipeline

```bash
python scripts/00_audit_data.py --config configs/data_crypto_lake.yaml
python scripts/01_build_features.py --config configs/features.yaml
python scripts/02_label_regimes.py --config configs/regimes.yaml
python scripts/03_make_splits.py --config configs/experiments_full.yaml
```

### 17.4 Models

```bash
python scripts/04_train_forecasters.py --config configs/models.yaml --model sgd
python scripts/04_train_forecasters.py --config configs/models.yaml --model xgboost
python scripts/04_train_forecasters.py --config configs/models.yaml --model tcn
python scripts/04_train_forecasters.py --config configs/models.yaml --model deeplob_lite
```

### 17.5 Backtest and robustness

```bash
python scripts/05_backtest_forecasts.py --config configs/simulator.yaml
python scripts/06_run_rsep.py --config configs/simulator.yaml
python scripts/07_run_stress_grid.py --config configs/experiments_full.yaml
python scripts/08_generate_report_pack.py --config configs/experiments_full.yaml
```

---

## 18. 5-7 Day Initial Experiment Plan

This plan is for generating the first credible result pack.

### Day 1 — Data audit and feature store

Deliverables:

```text
audit_by_day.parquet
feature_parquet for one month BTC + one month ETH
dataset stats table
basic spread/depth figures
```

### Day 2 — Regime labeling

Deliverables:

```text
rule-based regime labels
regime feature medians
regime calendar heatmap
regime counts by month/symbol
```

### Day 3 — Forecasting baselines

Deliverables:

```text
SGD/logistic baseline
XGBoost/LightGBM baseline
TCN small baseline if time permits
forecasting by regime table
```

### Day 4 — Execution simulator and degradation

Deliverables:

```text
market order simulator
fee/latency/depth stress
forecast-to-execution degradation table
sanity tests passing
```

### Day 5 — RSEP

Deliverables:

```text
RSEP-full
RSEP ablations
policy comparison table
worst-regime metrics
```

### Day 6 — Full-symbol/full-period scale-up

Deliverables:

```text
run on 1-year BTC and ETH if compute permits
walk-forward splits
asset-held-out split
stress curves
```

### Day 7 — Paper result pack

Deliverables:

```text
all paper tables/figures
failure case studies
logs/configs zipped
README updated
```

---

## 19. ICDM Submission Roadmap After 7-Day Result Pack

Assume current date is close to May 2026 and ICDM full-paper deadline is June 6, 2026.

### Week 1

- Complete full 1-year BTC/ETH feature and regime pipeline.
- Validate no leakage.
- Run tabular baselines and RSEP.

### Week 2

- Run TCN/DeepLOB-lite with 3 seeds.
- Run full stress grid.
- Run bootstrap significance tests.
- Write Section 3-5 of paper.

### Week 3

- Add optional RL-lite or regime-router baseline if time remains.
- Complete ablation and failure case studies.
- Finalize figures/tables.
- Draft full paper.

### Final 3-4 days

- Tighten claims.
- Remove overclaiming.
- Verify reproducibility.
- Check all paper numbers match result files.
- Prepare IEEE format.

---

## 20. Acceptance Bar / Go-No-Go Criteria

The result pack is submission-worthy only if at least 4 of the following hold:

1. Forecasting performance varies significantly by regime.
2. High forecasting score does not reliably translate to net PnL after costs.
3. Latency/stress curves show meaningful degradation for naive policies.
4. RSEP improves worst-regime return vs naive forecast threshold.
5. RSEP reduces RegimeGap without destroying average return.
6. RSEP improves RobustnessAUC under fee/latency/depth stress.
7. Results hold across both BTC and ETH.
8. At least one asset-held-out or walk-forward result supports generalization.
9. Bootstrap confidence intervals support the main claim.

If fewer than 4 hold, reposition as a benchmark/failure-analysis paper and remove claims about policy improvement.

---

## 21. Code Quality Requirements

### 21.1 Tests

At minimum:

```bash
pytest tests/
```

Must pass.

### 21.2 Determinism

- Set seeds.
- Log seeds.
- For GPU models, enable deterministic mode where practical, but do not sacrifice training feasibility.

### 21.3 Data safety

- Do not commit raw paid data.
- Do not commit API keys.
- Put all raw-data paths in YAML config.
- Add `.gitignore` for `data/raw`, `outputs/checkpoints`, and large artifacts.

### 21.4 Performance

- All heavy functions must process per day/per partition.
- Use lazy scanning where possible.
- Avoid pandas for full-year operations unless data is already reduced.
- Store intermediate features as partitioned Parquet.

---

## 22. Minimum README Contents

README must explain:

```text
1. Research goal
2. Data assumptions
3. How to configure local Crypto Lake paths
4. How to run smoke test
5. How to run full pipeline
6. How to regenerate tables and figures
7. What claims are intentionally not made
8. License/data restrictions
```

---

## 23. Suggested Paper Abstract Draft

> We introduce CryptoRegimeShift-LOB, a benchmark and evaluation protocol for robust high-frequency trading policy learning under L2 microstructure regime shifts. Existing LOB benchmarks primarily focus on forecasting or generative realism, while HFT policy evaluations often rely on average chronological backtests that obscure catastrophic failures under liquidity and execution shifts. Using one year of high-frequency BTC-USDT and ETH-USDT L2 order book snapshots with 20 price levels per side, we define a causal microstructure regime taxonomy, regime-held-out splits, and execution-stress tests covering transaction costs, latency, spread widening, and depth shocks. We evaluate forecasting models, forecast-to-execution conversion strategies, and robust selective execution policies using robustness-oriented metrics including worst-regime return, regime performance gap, cost survival, latency decay, and robustness AUC. Our results are designed to test whether predictive edge survives realistic execution stress and whether cost-aware selective execution improves worst-regime stability.

---

## 24. Source Notes for Paper Writing

Use these sources in the paper introduction and related work:

1. Crypto Lake data schema and coverage:
   - `book` contains high-frequency market depth snapshots, at least once per 100ms depending on exchange support, with 20 price levels per side.
   - `book_delta_v2` provides high-frequency updates with potentially 1000+ levels but requires reconstructing the book.
   - Data are partitioned by exchange, symbol, and day.
   - `origin_time` means exchange event time; `received_time` means server receipt/processing time.

2. LOB-Bench:
   - Financial sequence modelling is hard because of noise, heavy tails, and strategic interactions.
   - Lack of consensus on quantitative evaluation paradigms motivates benchmarking.
   - LOB-Bench evaluates generative LOB data, not robust policy learning.

3. EarnHFT:
   - HFT RL has extremely long trajectories.
   - Crypto trend changes make existing algorithms fail to maintain satisfactory performance.
   - Hierarchical RL is an important baseline but not the same as regime-stress benchmarking.

4. MacroHFT:
   - Standard RL agents can overfit and fail to adapt to financial context.
   - Individual agents can be one-sided and biased in extreme markets.
   - Memory/context-aware HFT is a close related baseline.

5. ICDM 2026:
   - Full paper deadline: June 6, 2026.
   - Treat the timeline as strict.

---

## 25. Final Instruction to Codex

Build the pipeline in this order:

1. Data audit.
2. Feature store.
3. Regime labels.
4. Splits.
5. Forecast baselines.
6. Simulator.
7. Forecast-to-execution degradation.
8. RSEP.
9. Stress grid.
10. Tables/figures/report pack.

Do not implement complicated RL until the benchmark, simulator, and RSEP are stable.

The primary deliverable is a reproducible experimental evidence pack, not an over-engineered trading model.
