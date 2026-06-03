# Audit Stage 2 Medium Scale v001 - BTC-USDT Jan-Jun 2024

## 1. Tóm tắt điều hành

Stage 2 đã hoàn tất chuỗi `audit -> features/labels -> refined regimes -> splits -> forecasting -> backtest -> RSEP -> stress -> report pack` trên `BTC-USDT` từ `2024-01-01` đến `2024-06-30`.

Kết luận chính:

- Taxonomy refined pass gate ổn định: `UNKNOWN overall = 13.37%`, p90 daily UNKNOWN khoảng `15.60%`, dưới ngưỡng `25%`.
- Forecasting SGD có tín hiệu nhưng chưa mạnh: macro-F1 test `0.4557`, MCC `0.2503`, balanced accuracy `0.4413`.
- Forecast-to-execution xác nhận thesis degradation: cả naive threshold và cost-aware threshold đều có gross PnL dương nhưng net PnL âm sau chi phí.
- RSEP-full giảm thiệt hại rõ so với cost-aware baseline và ablation; bootstrap day-level có CI dương, nhưng RSEP-full vẫn net âm ở fee `1 bps`.
- Gate stage 2: **GO có điều kiện cho stage 3 full-year theo hướng benchmark/failure-analysis + robust selective execution**, nhưng **NO-GO cho claim trading profitability hoặc policy improvement tuyệt đối**.

## 2. Run và artifact

Các run chính:

- `stage2_features_btc_jan_jun_v007`
- `stage2_regimes_btc_jan_jun_v001`
- `stage2_splits_btc_jan_jun_v001`
- `stage2_forecast_sgd_btc_jan_jun_v001`
- `stage2_backtest_btc_jan_jun_v001`
- `stage2_rsep_btc_jan_jun_v001`
- `stage2_stress_btc_jan_jun_v001`
- `stage2_report_btc_jan_jun_v001`

Artifact bắt buộc đã sinh:

- `outputs/tables/table_regime_share_stage2.csv`
- `outputs/tables/table_unknown_monthly_share_stage2.csv`
- `outputs/tables/table_regime_feature_medians_stage2.csv`
- `outputs/tables/table_forecasting_by_regime_stage2.csv`
- `outputs/tables/table_forecast_to_execution.csv`
- `outputs/tables/table_forecast_to_execution_by_regime.csv`
- `outputs/tables/table_robust_policy.csv`
- `outputs/tables/table_rsep_ablation.csv`
- `outputs/tables/table_rsep_by_regime.csv`
- `outputs/tables/table_rsep_bootstrap_stage2.csv`
- `outputs/tables/table_stress_grid.csv`
- `outputs/tables/table_robustness_summary.csv`
- `outputs/figures/regime_share_by_month_stage2.png`
- `outputs/figures/unknown_share_by_day_stage2.png`
- `outputs/paper_assets/*`

## 3. Data quality và feature pipeline

Stage 2 dùng `69,532,240` feature/label rows sau khi build theo partition Jan-May và ba cửa sổ tháng Jun. Split cuối:

- train: `41,719,344`
- valid: `13,906,448`
- test: `13,906,448`

Feature engine đã được tối ưu trước khi resume stage 2: `add_return_features` chuyển từ rolling UDF sang rolling vectorized. Benchmark 200k APR giảm từ khoảng `25.86s` xuống khoảng `0.25s`, giúp hoàn tất Jan-Jun mà không đổi semantics feature. Test regression/causal đã pass.

Rủi ro còn lại: stage 3 full-year vẫn có nguy cơ I/O và disk pressure vì `predictions.parquet` stage 2 đã khoảng `18.34 GB`. Trước stage 3 nên giữ partitioned/streaming path và tránh materialize các bảng lớn không cần thiết.

## 4. Taxonomy stability

Regime share stage 2:

- `BALANCED_TRANSITION`: `21.12%`
- `MILD_LIQUIDITY_STRESS`: `17.22%`
- `MOMENTUM_TOXIC`: `16.85%`
- `UNKNOWN`: `13.37%`
- `SHOCK_RECOVERY`: `9.53%`
- `CHOPPY_MEAN_REVERTING`: `8.64%`
- `CALM_LIQUID`: `8.51%`
- `LIQUIDITY_DROUGHT`: `1.87%`
- `CALM_ILLIQUID`: `1.71%`
- `VOLATILE_ILLIQUID`: `1.10%`
- `VOLATILE_LIQUID`: `0.06%`

UNKNOWN theo tháng:

- Jan: `12.29%`
- Feb: `14.38%`
- Mar: `12.63%`
- Apr: `13.32%`
- May: `13.78%`
- Jun: `13.51%`

Đánh giá: taxonomy không chỉ tốt ở Jan-Feb mà giữ được coverage ổn định trong 6 tháng. `BALANCED_TRANSITION` và `MILD_LIQUIDITY_STRESS` có profile khác nhau: Balanced có `liquidity_score` dương và `stress_score` âm mạnh; Mild stress có `liquidity_score` âm và `stress_score` dương nhẹ. Điều này ủng hộ quyết định thêm residual regimes thay vì đẩy toàn bộ vào UNKNOWN.

Điểm yếu: `VOLATILE_LIQUID` quá hiếm (`0.06%`), không nên dùng làm điểm nhấn chính trong regime-held-out nếu không gom hoặc tái định nghĩa ở stage 3.

## 5. Forecasting heterogeneity

SGD overall trên test:

- accuracy: `0.6985`
- macro-F1: `0.4557`
- weighted-F1: `0.6541`
- MCC: `0.2503`
- balanced accuracy: `0.4413`
- test rows: `13,906,448`

Macro-F1 thấp nhất theo regime:

- `CHOPPY_MEAN_REVERTING`: `0.3382`
- `CALM_LIQUID`: `0.3542`
- `MILD_LIQUIDITY_STRESS`: `0.4008`
- `BALANCED_TRANSITION`: `0.4051`
- `UNKNOWN`: `0.4444`

Macro-F1 cao hơn:

- `VOLATILE_ILLIQUID`: `0.5086`
- `SHOCK_RECOVERY`: `0.4860`
- `MOMENTUM_TOXIC`: `0.4734`

Đánh giá: có heterogeneity by-regime rõ ràng, nhưng model tabular tuyến tính vẫn yếu ở các vùng choppy/calm và residual. Đây là evidence tốt cho paper theo hướng regime-conditioned evaluation, nhưng chưa đủ để claim model mạnh.

## 6. Forecast-to-execution degradation

Backtest threshold:

- naive threshold: `87,524` trades, gross PnL `5,936.09`, net PnL `-11,563.02`, total cost `17,499.11`.
- cost-aware threshold: `237,158` trades, gross PnL `19,371.77`, net PnL `-28,050.37`, total cost `47,422.14`.

Kết quả này rất quan trọng: forecast có gross edge nhưng chi phí phá hủy edge khi đi qua simulator. Cost-aware threshold hiện tại tăng số trade và gross PnL, nhưng cũng tăng turnover và total cost quá mạnh, dẫn đến net PnL tệ hơn naive.

By-regime degradation cũng rõ:

- cost-aware âm mạnh ở `MOMENTUM_TOXIC` (`-8,008.90`), `CHOPPY_MEAN_REVERTING` (`-5,370.94`), `SHOCK_RECOVERY` (`-3,986.00`), `UNKNOWN` (`-3,805.61`).
- naive cũng âm ở hầu hết regime, nhưng ít turnover hơn.

Diễn giải: thesis paper nên nhấn vào forecast-to-execution collapse dưới microstructure cost, không nhấn vào profitability.

## 7. RSEP, ablation và bootstrap

RSEP-full:

- trades: `35,664`
- gross PnL: `3,089.52`
- net PnL: `-4,042.46`
- total cost: `7,131.97`
- worst-regime return: `-1,533.55`

So với threshold baselines:

- tốt hơn naive threshold về net PnL: `-4,042.46` so với `-11,563.02`.
- tốt hơn cost-aware threshold về net PnL: `-4,042.46` so với `-28,050.37`.
- giảm turnover/trade count mạnh so với cost-aware.

Ablation:

- bỏ latency risk: net `-5,655.35`
- bỏ liquidity risk: net `-5,736.85`
- bỏ adverse risk: net `-7,073.57`
- bỏ regime penalty: net `-6,158.41`
- bỏ cost gate: net `-888,163.69`

Bootstrap stage 2:

- mean diff RSEP-full minus cost-aware: `827.86`
- 95% CI: `[620.29, 1054.83]`
- `n_days = 29`
- `n_bootstrap = 1000`

Đánh giá: RSEP có evidence tốt như cơ chế selective execution giảm thiệt hại và giảm exposure trong regime xấu. Tuy nhiên net PnL vẫn âm ở fee `1 bps`, nên claim hợp lý là "robust selective execution mitigates degradation", không phải "profitable trading policy".

## 8. Stress sensitivity

Stress fee:

- fee `0 bps`: net `3,089.52`
- fee `1 bps`: net `-4,042.46`
- fee `2 bps`: net `-11,174.43`
- fee `5 bps`: net `-32,570.35`
- fee `10 bps`: net `-68,230.23`

Stress latency:

- latency `0`: net `-3,382.84`
- latency `1`: net `-4,042.46`
- latency `5`: net `-5,080.90`
- latency `10`: net `-5,684.69`

Spread/depth stress có tác động nhẹ hơn fee trong simulator hiện tại:

- spread multiplier `1.0/1.5/2.0`: net khoảng `-4,042 / -4,059 / -4,076`.
- depth multiplier `1.0/0.75/0.5`: net khoảng `-4,042 / -4,049 / -4,061`.

Đánh giá: cost survival là điểm nghẽn chính. Stress curves diễn giải được và phù hợp intuition: phí phá edge nhanh nhất, latency làm gross edge decay, spread/depth transform hiện ít nhạy hơn do policy đã lọc mạnh và simulator dùng trade notional/cooldown cố định.

## 9. Principal ML Scientist review

Điểm mạnh:

- Taxonomy refined đã ổn định hơn stage 1 và UNKNOWN vẫn dưới gate.
- Evaluation theo regime làm lộ rõ heterogeneity của forecasting và execution.
- RSEP ablation có tín hiệu rõ: cost gate, adverse risk, regime penalty đều có giá trị.
- Bootstrap day-level không còn suy biến một ngày; `n_days=29` đủ tốt cho stage 2 sơ bộ.

Điểm yếu:

- Forecasting hiện mới dùng SGD; macro-F1 chưa đủ mạnh để làm claim model chính.
- Simulator vẫn là approximation dựa trên L2 snapshot và market-order replay; chưa được claim exact execution realism.
- Cost-aware threshold baseline đang hoạt động phản trực giác vì trade count tăng mạnh và net tệ hơn naive. Cần xem lại calibration/threshold tuning trên validation trước khi dùng làm baseline mạnh ở paper.
- `VOLATILE_LIQUID` quá hiếm, không đủ làm regime chính.

Khuyến nghị kỹ thuật:

- Stage 3 nên chạy full-year với cùng taxonomy để kiểm tra seasonality/drift.
- Sau khi stage 3 data path ổn, mở nhánh GPU hợp lý: XGBoost GPU trước, sau đó TCN/DeepLOB-lite.
- Trước khi deep model, cần cải thiện baseline policy tuning trên validation để cost-aware threshold thực sự là baseline công bằng.

## 10. Reviewer ICDM review

Điểm có sức thuyết phục:

- Study có scale đáng kể: hàng chục triệu rows, chia chronological train/valid/test.
- Có audit taxonomy, by-regime forecasting, execution, ablation, stress và bootstrap.
- Kết quả không overclaim: paper có thể kể câu chuyện forecast accuracy không đủ, execution cost làm collapse, và selective execution giúp giảm rủi ro.

Rủi ro reviewer:

- Nếu chỉ có SGD, reviewer có thể xem forecasting baseline chưa đủ mạnh.
- Nếu chỉ có BTC, reviewer có thể yêu cầu cross-asset hoặc ít nhất BTC full-year stability.
- Nếu cost-aware baseline không được tune chặt trên validation, so sánh RSEP có thể bị nghi ngờ.
- Net PnL âm dưới phí thực tế khiến mọi câu chữ về trading performance phải rất kỷ luật.

Định vị paper nên giữ:

- benchmark/failure-analysis cho LOB crypto regime shift.
- robust selective execution như mitigation mechanism.
- không claim trading bot, profitability, hoặc execution realism đầy đủ.

## 11. Gate stage 2 và bước tiếp theo

Gate taxonomy: **PASS**

- UNKNOWN overall `< 15%`: pass.
- p90 daily UNKNOWN `< 25%`: pass.
- monthly UNKNOWN ổn định: pass.
- residual regimes có profile khác biệt: pass.

Gate execution: **PASS có điều kiện**

- forecast-to-execution degradation rõ: pass.
- RSEP tốt hơn threshold baselines và ablation: pass.
- bootstrap day-level CI dương: pass.
- net PnL vẫn âm ở fee `1 bps`: không pass nếu claim profitability.

Go/no-go:

- **GO cho stage 3 full-year** để kiểm tra stability và tăng sức nặng empirical rigor.
- **GO cho nhánh GPU baseline sau stage 3 hoặc song song có kiểm soát**, ưu tiên XGBoost GPU rồi TCN.
- **NO-GO cho claim policy sinh lời**.
- **NO-GO cho asset-held-out** cho tới khi có ETH data.

Việc cần làm trước/sau stage 3:

- Rà lại cost-aware threshold tuning trên validation.
- Cân nhắc gom hoặc bỏ `VOLATILE_LIQUID` khỏi các bảng chính nếu vẫn quá hiếm.
- Giữ partitioned artifacts để tránh disk pressure.
- Thêm model mạnh hơn bằng RTX 3090 sau khi stage 3 full-year pipeline pass.
