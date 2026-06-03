# Stage 3.11 - Narrative evidence pack

## Ket luan ngan

Acceptance bar hien co 7 PASS, 2 PARTIAL, 0 BLOCKED va 0 FAIL. Cach doc phu hop nhat la benchmark/failure-analysis + robust selective execution, khong phai trading bot sinh loi.

Ve forecasting, model manh nhat theo macro-F1 trong bang hien tai la tcn_gpu_stage3 voi macro-F1 0.4689. Tuy nhien TCN stride-1 cho thay bai hoc quan trong: cai thien macro-F1 khong tu dong chuyen thanh execution/RSEP tot hon.

## Claim nen giu

- Regime-aware evaluation la can thiet vi metric forecasting/execution thay doi theo microstructure regime.
- Forecast-to-execution degradation la core evidence: gross edge co the bi phi, spread va stress an mon.
- Stress grid va bootstrap nen duoc dua vao paper de tranh doc ket qua theo mot aggregate duy nhat.

## Claim phai ha giong

- RSEP khong nen duoc viet nhu policy universal winner; voi TCN stride-1, bootstrap khong support RSEP thang cost-aware.
- Cross-asset BTC<->ETH da duoc evaluate o ca forecasting va execution/RSEP voi source-validation-only tuning; RSEP giam thiet hai so voi cost-aware nhung net PnL van am, nen khong claim profitable hoac universal policy.
- Khong claim profitability, live trading readiness, L3 queue priority hay exact execution realism.

## Bang nen dua vao paper

- `table_11_acceptance_bar.csv`: gate reviewer-facing theo 9 tieu chi.
- `table_12_claim_support_matrix.csv`: claim nao supported, partial, blocked hoac not claimed.
- `table_final_model_selection_stage3.csv`: vai tro cong bang cua SGD, XGBoost GPU, TCN pilot va TCN stride-1.

## Model selection

- `sgd_stage3`: main tabular baseline; macro-F1=0.4652, MCC=0.2363. Baseline don gian, de tai lap; dung lam diem neo cho failure-analysis.
- `xgboost_gpu_stage3`: strong GPU tabular baseline / secondary baseline; macro-F1=0.4562, MCC=0.2364. Accuracy cao hon SGD nhung macro-F1/balanced accuracy thap hon; execution chi cai thien nhe.
- `tcn_gpu_stage3`: temporal pilot diagnostic / appendix; macro-F1=0.4689, MCC=0.2275. Stride-10 sample-window khong nen so truc tiep voi full-row execution.
- `tcn_gpu_stage3_stride1`: main temporal fairness baseline with negative execution evidence; macro-F1=0.4688, MCC=0.2274. Macro-F1 cao nhat nhung MCC thap hon SGD/XGBoost va RSEP khong thang cost-aware.

## Claim matrix summary

- `SUPPORTED` - Benchmark BTC L2 full-year cho regime-aware forecast-to-execution: Chung toi de xuat benchmark/evaluation protocol tren BTC L2 full-year.
- `SUPPORTED` - Regime shifts lam forecasting va execution metric khac nhau theo regime: Ket qua cho thay metric thay doi dang ke giua cac microstructure regimes.
- `SUPPORTED` - Forecasting tot hon khong dam bao execution tot hon: Forecasting gain can duoc kiem tra qua cost-aware execution, khong nen doc rieng accuracy/F1.
- `NOT_SUPPORTED` - RSEP la policy universal winner: RSEP la selective execution baseline/diagnostic, khong phai policy luon chien thang.
- `SUPPORTED` - Stress grid chung minh edge nhay cam voi fee, latency, spread, depth: Robustness duoc bao cao theo stress axes thay vi mot PnL aggregate.
- `SUPPORTED` - Cross-asset BTC<->ETH forecasting/execution duoc evaluate: Cross-asset BTC<->ETH da duoc evaluate o ca forecasting va execution; khong claim policy tao loi nhuan pho quat.
- `NOT_CLAIMED` - He thong san sang live trading hoac co profitability: Khong claim profitability; chi claim benchmark va failure-analysis.
