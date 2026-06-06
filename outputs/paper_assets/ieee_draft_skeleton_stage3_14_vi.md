# Stage 3.14 - IEEE draft skeleton

## Cach dung file nay

File nay la skeleton de viet ban IEEE/ICDM tu artifact da khoa. No khong thay the paper draft, nhung khoa section, claim, evidence path va wording an toan de tranh overclaim.

## Evidence lock

- Acceptance bar: `7` PASS, `2` PARTIAL, `0` BLOCKED, `0` FAIL.
- Number consistency FAIL: `0`.
- Huong paper: benchmark/failure-analysis + robust selective execution co dieu kien.
- Cross-asset status: BTC<->ETH da co forecasting, execution/RSEP va bootstrap; khong viet nhu trading system tao loi nhuan.

## Model snapshot

- `sgd_stage3`: main tabular baseline; accuracy `0.5589`, macro-F1 `0.4652`, MCC `0.2363`; caveat: Baseline don gian, de tai lap; dung lam diem neo cho failure-analysis..
- `xgboost_gpu_stage3`: strong GPU tabular baseline / secondary baseline; accuracy `0.5677`, macro-F1 `0.4562`, MCC `0.2364`; caveat: Accuracy cao hon SGD nhung macro-F1/balanced accuracy thap hon; execution chi cai thien nhe..
- `tcn_gpu_stage3`: temporal pilot diagnostic / appendix; accuracy `0.5282`, macro-F1 `0.4689`, MCC `0.2275`; caveat: Stride-10 sample-window khong nen so truc tiep voi full-row execution..
- `tcn_gpu_stage3_stride1`: main temporal fairness baseline with negative execution evidence; accuracy `0.5281`, macro-F1 `0.4688`, MCC `0.2274`; caveat: Macro-F1 cao nhat nhung MCC thap hon SGD/XGBoost va RSEP khong thang cost-aware..
- `deeplob_stage3_pilot`: DeepLOB-style CNN-LSTM smoke/pilot baseline; evidence path `outputs/paper_assets/table_21_deep_baseline_status.csv`; caveat: khong phai full-row execution-ready result.
- `lob_transformer_stage3_pilot`: lightweight LOB-Transformer smoke/pilot baseline; evidence path `outputs/paper_assets/table_21_deep_baseline_status.csv`; caveat: khong dung cho main execution claim neu chua co full artifact.

## Cross-asset snapshot

- `btc_to_eth`: macro-F1 `0.4325`, MCC `0.1486`, RSEP net `-74,466.38`, cost-aware net `-287,991.44`, bootstrap CI [`3,314.02`, `4,048.20`].
- `eth_to_btc`: macro-F1 `0.4839`, MCC `0.2424`, RSEP net `-1,144.75`, cost-aware net `-3,697.46`, bootstrap CI [`34.08`, `44.53`].

## 1. Introduction

- Claim chinh: Average forecasting metric khong du de danh gia HFT policy duoi L2 regime shifts.
- Evidence can trich:
  - `outputs/paper_assets/table_11_acceptance_bar.csv`
  - `outputs/paper_assets/table_12_claim_support_matrix.csv`
  - `outputs/paper_assets/result_narrative_stage3_11_vi.md`
- Wording duoc phep: Mo ta gap evaluation: forecasting signal co the bien mat khi qua cost, latency va liquidity stress.
- Wording khong duoc dung: Khong viet paper la trading bot hoac strategy tao loi nhuan on dinh.
- Cau viet an toan: Chung toi nghien cuu khoang cach forecast-to-execution tren L2 microstructure regimes thay vi toi uu loi nhuan giao dich.

## 2. Related Work Positioning

- Claim chinh: Paper dung DeepLOB/LOB forecasting nhu baseline context, nhung contribution nam o evaluation protocol va execution degradation.
- Evidence can trich:
  - `CryptoRegimeShift/MoTa.md`
  - `CryptoRegimeShift/ThucNghiem.md`
- Wording duoc phep: Dat SGD, XGBoost GPU va TCN nhu baseline phuc vu benchmark; khong claim model moi SOTA.
- Wording khong duoc dung: Khong viet incremental model improvement la novelty chinh.
- Cau viet an toan: Khac voi cac paper chi bao forecasting score, thuc nghiem nay noi forecasting voi cost-aware execution va stress.

## 3. Data and Benchmark

- Claim chinh: Benchmark gom BTC-USDT va ETH-USDT L2 snapshot-level full-year voi split theo thoi gian.
- Evidence can trich:
  - `CryptoRegimeShift/ThucNghiem.md`
  - `outputs/paper_assets/table_1_dataset_stats.csv`
  - `outputs/paper_assets/table_1b_eth_dataset_stats.csv`
  - `outputs/paper_assets/table_15_reproducibility_checklist.csv`
- Wording duoc phep: Ghi ro BTC/ETH dataset stats da khoa, snapshot-level L2, 20 levels, khong L3/MBO queue priority.
- Wording khong duoc dung: Khong viet simulator co exact queue position hoac live market realism.
- Cau viet an toan: Dung table_1/table_1b cho so BTC/ETH, khong de placeholder can kiem chung cho ETH dataset stats.

## 4. Regime Taxonomy

- Claim chinh: Causal refined taxonomy giam UNKNOWN co ky luat va cho phep by-regime evaluation.
- Evidence can trich:
  - `outputs/tables/table_regime_share_stage3.csv`
  - `outputs/tables/table_unknown_daily_share_stage3.csv`
  - `audits/audit_regime_refinement_v001.md`
- Wording duoc phep: Mo ta regime nhu microstructure context co the interpret duoc, khong phai oracle.
- Wording khong duoc dung: Khong viet regime label la ground truth tuyet doi cua market state.
- Cau viet an toan: Regime taxonomy duoc dung de do heterogeneity va failure modes, khong de tao nhan tuong lai.

## 5. Forecasting Baselines

- Claim chinh: SGD, XGBoost GPU va TCN stride-1 cung cap baseline tu simple den temporal.
- Evidence can trich:
  - `outputs/tables/table_final_model_selection_stage3.csv`
  - `outputs/paper_assets/table_8_model_forecasting_execution_comparison.csv`
  - `outputs/tables/table_forecasting_by_regime_stage3.csv`
- Wording duoc phep: Bao cao accuracy, macro-F1, MCC, balanced accuracy va by-regime thay vi chi mot metric.
- Wording khong duoc dung: Khong viet XGBoost/TCN luon tot hon neu macro-F1/MCC/execution mixed.
- Cau viet an toan: TCN stride-1 co macro-F1 cao hon nhung MCC va execution khong tu dong tot hon, nen la negative evidence quan trong.

## 6. Forecast-to-Execution

- Claim chinh: Forecasting edge bi phi, spread, latency va liquidity cost an mon khi dua vao simulator.
- Evidence can trich:
  - `outputs/tables/table_model_forecasting_execution_comparison_stage3.csv`
  - `outputs/paper_assets/table_4_forecast_to_execution.csv`
  - `outputs/paper_assets/table_5_robust_policy.csv`
- Wording duoc phep: RSEP la selective execution baseline/diagnostic, khong phai policy luon chien thang.
- Wording khong duoc dung: Khong viet RSEP luon chien thang hoac la strategy san sang giao dich that.
- Cau viet an toan: RSEP nen duoc doc nhu selective execution baseline: giam exposure khi edge khong du bu cost/risk.

## 7. Stress and Robustness

- Claim chinh: Stress grid do sensitivity voi fee, latency, spread va depth thay vi chi PnL aggregate.
- Evidence can trich:
  - `outputs/paper_assets/table_9_model_stress_comparison.csv`
  - `outputs/paper_assets/table_10_model_robustness_comparison.csv`
  - `outputs/paper_assets/fig_7_model_fee_stress.png`
  - `outputs/paper_assets/fig_8_model_latency_stress.png`
- Wording duoc phep: Dung stress curves de chung minh edge mong va OOD sensitivity.
- Wording khong duoc dung: Khong bien mot stress setting thuan loi thanh claim ve loi nhuan on dinh.
- Cau viet an toan: RobustnessAUC va stress curves cho thay model/policy phai duoc doc theo dieu kien cost/liquidity.

## 8. Cross-Asset BTC<->ETH

- Claim chinh: BTC<->ETH da duoc evaluate voi source-validation-only tuning o ca forecasting va target-asset execution.
- Evidence can trich:
  - `outputs/paper_assets/table_16_cross_asset_forecasting_execution.csv`
  - `outputs/paper_assets/table_17_cross_asset_bootstrap.csv`
  - `outputs/paper_assets/cross_asset_narrative_stage3_13_vi.md`
- Wording duoc phep: Cross-asset BTC<->ETH da duoc evaluate o ca forecasting va execution; khong claim policy tao loi nhuan pho quat.
- Wording khong duoc dung: Khong viet policy co loi nhuan pho quat qua asset hoac ap dung pho quat cho moi market.
- Cau viet an toan: Cross-asset evidence cho thay forecast khong collapse va RSEP giam thiet hai, nhung net PnL am nen claim dung la evaluation/failure-analysis.

## 9. Limitations

- Claim chinh: Boundary cua paper la snapshot-level L2 benchmark, khong phai live execution system.
- Evidence can trich:
  - `outputs/paper_assets/limitation_wording_stage3_12_vi.md`
  - `audits/audit_stage3_13_cross_asset_paper_lock_v001.md`
- Wording duoc phep: Ghi ro net PnL am, simulator khong co exact queue priority, va RSEP support khong universal.
- Wording khong duoc dung: Khong bo qua negative evidence cua TCN stride-1 hoac cross-asset net PnL am.
- Cau viet an toan: Ket qua am duoc trinh bay nhu bang chung khoa hoc ve forecast-to-execution gap, khong phai that bai can che giau.

