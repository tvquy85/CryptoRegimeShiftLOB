# Audit Stage 3.11 - ICDM evidence hardening

- `run_id`: `stage3_11_icdm_evidence_hardening_v004`
- Muc tieu: chot evidence reviewer-facing tu artifact da co, khong train/inference them.
- Pham vi: BTC full-year Stage 3, ETH replication/asset-held-out artifacts neu da co, model tabular va temporal da co.

## Ket qua acceptance bar

- PASS: `7`
- PARTIAL: `2`
- BLOCKED: `0`
- FAIL: `0`

- `C01` `PASS` - Forecasting performance varies by regime: Co 11 regime; spread macro_f1 theo regime = 0.0935.
- `C02` `PASS` - Forecasting score does not guarantee actionable execution edge: Co bang chung gross edge bi phi/spread/latency an mon thanh net PnL am.
- `C03` `PASS` - Stress grid shows cost/latency/liquidity degradation: Fee stress lam net PnL giam cho model sgd_stage3.
- `C04` `PASS` - RSEP improves worst-regime behavior versus threshold baselines: RSEP dat worst-regime >= baseline trong 2/4 so sanh model.
- `C05` `PASS` - RSEP reduces RegimeGap without hiding average degradation: RSEP co RegimeGap <= baseline trong 2/4 so sanh model.
- `C06` `PASS` - RobustnessAUC summarizes degradation under stress: Robustness table co 5 stress axes: depth_multiplier, fee_bps, latency_events, latency_half_life, spread_multiplier.
- `C07` `PARTIAL` - Results hold across both BTC and ETH: ETH within-asset forecasting/execution da chay; net PnL van am va can doc nhu replication/failure-analysis.
- `C08` `PASS` - Asset-held-out or cross-asset generalization is evaluated: Da co asset-held-out forecasting va execution/RSEP BTC->ETH, ETH->BTC voi tuning source-validation-only.
- `C09` `PARTIAL` - Day-level bootstrap supports the statistical reading: Bootstrap hop le; SGD/XGBoost co CI duong, TCN stride-1 mixed/khong thang cost-aware.

## Model selection

- `sgd_stage3`: role `main tabular baseline`, accuracy `0.5589`, macro-F1 `0.4652`, MCC `0.2363`, caveat: Baseline don gian, de tai lap; dung lam diem neo cho failure-analysis.
- `xgboost_gpu_stage3`: role `strong GPU tabular baseline / secondary baseline`, accuracy `0.5677`, macro-F1 `0.4562`, MCC `0.2364`, caveat: Accuracy cao hon SGD nhung macro-F1/balanced accuracy thap hon; execution chi cai thien nhe.
- `tcn_gpu_stage3`: role `temporal pilot diagnostic / appendix`, accuracy `0.5282`, macro-F1 `0.4689`, MCC `0.2275`, caveat: Stride-10 sample-window khong nen so truc tiep voi full-row execution.
- `tcn_gpu_stage3_stride1`: role `main temporal fairness baseline with negative execution evidence`, accuracy `0.5281`, macro-F1 `0.4688`, MCC `0.2274`, caveat: Macro-F1 cao nhat nhung MCC thap hon SGD/XGBoost va RSEP khong thang cost-aware.

## Claim-support matrix

- `SUPPORTED` - Benchmark BTC L2 full-year cho regime-aware forecast-to-execution: Chung toi de xuat benchmark/evaluation protocol tren BTC L2 full-year.
- `SUPPORTED` - Regime shifts lam forecasting va execution metric khac nhau theo regime: Ket qua cho thay metric thay doi dang ke giua cac microstructure regimes.
- `SUPPORTED` - Forecasting tot hon khong dam bao execution tot hon: Forecasting gain can duoc kiem tra qua cost-aware execution, khong nen doc rieng accuracy/F1.
- `NOT_SUPPORTED` - RSEP la policy universal winner: RSEP la selective execution baseline/diagnostic, khong phai policy luon chien thang.
- `SUPPORTED` - Stress grid chung minh edge nhay cam voi fee, latency, spread, depth: Robustness duoc bao cao theo stress axes thay vi mot PnL aggregate.
- `SUPPORTED` - Cross-asset BTC<->ETH forecasting/execution duoc evaluate: Cross-asset BTC<->ETH da duoc evaluate o ca forecasting va execution; khong claim policy tao loi nhuan pho quat.
- `NOT_CLAIMED` - He thong san sang live trading hoac co profitability: Khong claim profitability; chi claim benchmark va failure-analysis.

## Principal ML Scientist view

- Bang chung manh nhat nam o giao diem regime-aware forecasting, forecast-to-execution degradation, stress grid va bootstrap.
- TCN stride-1 la negative evidence co gia tri: temporal model co macro-F1 tot hon nhung execution khong tu dong tot hon.
- RSEP nen duoc trinh bay nhu baseline selective execution co gate/tuning validation-only, khong phai policy universal winner.

## Reviewer ICDM view

- Diem cong: benchmark lon, split theo thoi gian, stress/OOD, bootstrap day-level, claim discipline.
- Diem manh: cross-asset BTC<->ETH da co forecasting, target-asset execution/RSEP va bootstrap; claim duoc viet la evaluated, khong viet profitability/universal policy.
- Can dua negative evidence vao paper thay vi che di: no la bang chung cho thesis forecast-to-execution gap.

## Go/no-go

- Ket luan: Evidence du de viet paper theo huong benchmark/failure-analysis va selective execution co dieu kien.
- Buoc tiep theo hop ly: khoa evidence pack va viet IEEE draft tu narrative da co cross-asset.
- Khong can mo them model ad hoc truoc khi draft paper trich ro cac bang Stage 3.11.
