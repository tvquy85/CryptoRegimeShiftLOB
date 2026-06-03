# Stage 3.12 - Paper outline draft

## One-sentence positioning

CryptoRegimeShift-LOB la benchmark/evaluation protocol cho forecast-to-execution robustness duoi L2 microstructure regime shifts, khong phai trading-profit paper.

## Evidence status

- Acceptance bar: `7` PASS, `2` PARTIAL, `0` BLOCKED, `0` FAIL.
- Main claim duoc phep: BTC full-year benchmark, regime heterogeneity, forecast-to-execution degradation, stress sensitivity.
- Main claim duoc phep co dieu kien: cross-asset BTC<->ETH forecasting/execution evaluated.
- Main claim khong duoc phep: profitable/universal cross-asset policy generalization, live trading, exact queue priority, RSEP universal winner.

## De cuong paper

1. Introduction: neu gap trong LOB/HFT evaluation va vi sao average forecasting/backtest khong du.
2. Data and benchmark: BTC-USDT L2 snapshot-level, 20 levels, causal features, chronological split.
3. Regime taxonomy: refined causal taxonomy, residual states, UNKNOWN control, by-regime diagnostics.
4. Forecasting baselines: SGD, XGBoost GPU, TCN stride-1; giai thich vai tro tung model.
5. Forecast-to-execution: gross-to-net degradation, validation-only tuning, RSEP.
6. Stress and robustness: fee, latency, spread, depth, RobustnessAUC, day-level bootstrap.
7. Negative evidence: TCN macro-F1 tot hon nhung RSEP khong thang cost-aware.
8. Limitations: cross-asset BTC<->ETH da duoc evaluate nhung khong claim profitability/universal policy; snapshot-level simulator, khong L3/queue priority.

## Model roles

- `sgd_stage3`: main tabular baseline; macro-F1 `0.4652`, MCC `0.2363`.
- `xgboost_gpu_stage3`: strong GPU tabular baseline / secondary baseline; macro-F1 `0.4562`, MCC `0.2364`.
- `tcn_gpu_stage3`: temporal pilot diagnostic / appendix; macro-F1 `0.4689`, MCC `0.2275`.
- `tcn_gpu_stage3_stride1`: main temporal fairness baseline with negative execution evidence; macro-F1 `0.4688`, MCC `0.2274`.

## Claim-to-evidence map

- `SUPPORTED` Benchmark BTC L2 full-year cho regime-aware forecast-to-execution: outputs/tables/table_model_forecasting_execution_comparison_stage3.csv
- `SUPPORTED` Regime shifts lam forecasting va execution metric khac nhau theo regime: outputs/tables/table_forecasting_by_regime_stage3.csv
- `SUPPORTED` Forecasting tot hon khong dam bao execution tot hon: outputs/tables/table_model_forecasting_execution_comparison_stage3.csv
- `NOT_SUPPORTED` RSEP la policy universal winner: outputs/tables/table_rsep_bootstrap_tuned_stage3.csv
- `SUPPORTED` Stress grid chung minh edge nhay cam voi fee, latency, spread, depth: outputs/tables/table_model_stress_comparison_stage3.csv
- `SUPPORTED` Cross-asset BTC<->ETH forecasting/execution duoc evaluate: outputs/tables/table_asset_heldout_execution_stage3.csv
- `NOT_CLAIMED` He thong san sang live trading hoac co profitability: nan
