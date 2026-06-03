# Audit Stage 2.5 Policy/Model Hardening v001

## 1. Tóm tắt điều hành

Stage 2.5 xử lý hai điểm yếu còn lại sau Stage 2:

- `cost-aware threshold` cũ phản trực giác: trade count cao hơn naive và net PnL tệ hơn.
- Forecasting mới có `SGD`, chưa đủ mạnh nếu reviewer yêu cầu baseline phi tuyến.

Kết quả chính:

- Validation-only tuning đã sửa được policy baseline: cost-aware tuned giảm trade count và test net PnL tốt hơn naive tuned.
- RSEP tuned trên SGD giảm thiệt hại mạnh so với Stage 2 cũ: test net PnL từ `-4,042.46` xuống `-1,898.19`.
- XGBoost GPU chạy thành công trên RTX 3090, accuracy tăng nhẹ nhưng macro-F1, MCC và balanced accuracy kém SGD.
- XGBoost cost-aware tuned có test net PnL tốt nhất (`-1,045.75`), nhưng validation selection không đủ rõ để chọn XGBoost bằng test-only evidence.
- Kết luận: **GO có điều kiện cho Stage 3**, nhưng nên mang cả `SGD tuned` và `XGBoost GPU tuned` vào Stage 3 nếu tài nguyên cho phép; nếu chỉ chọn một baseline chính theo tính kỷ luật validation/forecasting, dùng `SGD + tuned RSEP/cost-aware`.

## 2. Thay đổi đã triển khai

Đã thêm validation-only policy tuning:

- script: `scripts/09_tune_execution_policies.py`
- module: `src/policies/tuning.py`
- artifact:
  - `outputs/tables/table_policy_tuning_stage2.csv`
  - `outputs/tables/table_forecast_to_execution_tuned_stage2.csv`
  - `outputs/tables/table_rsep_bootstrap_tuned_stage2.csv`
  - `outputs/tables/table_model_comparison_stage2_5.csv`
  - `configs/tuned_policy_stage2.yaml`

Đã bật XGBoost GPU:

- `configs/models.yaml` bật `xgboost.use_gpu: true`.
- `src/models/tabular_baselines.py` dùng `tree_method="hist"` và `device="cuda"` khi bật GPU.
- Có fallback CPU nếu fit GPU lỗi.

Đã harden execution/report:

- `simulate_signals` chỉ lặp qua non-zero signals, giữ semantics nhưng giảm runtime khi tuning nhiều candidate.
- `07_run_stress_grid.py` hỗ trợ `--use-tuned-policy --model-label`.
- `08_generate_report_pack.py` hỗ trợ report theo tuned model label.
- `outputs/paper_assets` đã regenerate sau stress tuned SGD.

## 3. Tuning policy trên validation

Grid tuning:

- naive theta: `0.50` đến `0.95`, bước `0.05`.
- cost-aware/RSEP theta: quantile của positive edge margin trên validation.
- Constraint: `n_trades >= max(1000, 0.0005 * valid_rows)` và có trade ít nhất `5` ngày.
- Objective: tối đa hóa validation net PnL, không dùng test để chọn threshold.

Threshold được chọn:

| Model | Policy | Threshold | Valid net PnL | Valid trades |
|---|---:|---:|---:|---:|
| SGD | naive | `0.60` | `-3,296.51` | `25,502` |
| SGD | cost-aware | `2.7554975e-05` | `-816.92` | `8,031` |
| SGD | RSEP-full | `8.597223e-06` | `-900.66` | `8,512` |
| XGBoost GPU | naive | `0.50` | `-14,465.96` | `133,694` |
| XGBoost GPU | cost-aware | `4.8199841e-05` | `-1,220.83` | `11,415` |
| XGBoost GPU | RSEP-full | `4.0323267e-05` | `-1,190.95` | `11,888` |

Đánh giá: tuning đã sửa baseline cost-aware. Với SGD, cost-aware tuned tốt nhất trên validation, còn RSEP gần sát nhưng có profile risk-control tốt hơn trên test. Với XGBoost, RSEP tốt hơn cost-aware trên validation nhưng chênh lệch nhỏ.

## 4. Forecasting comparison

SGD test:

- accuracy: `0.6985`
- macro-F1: `0.4557`
- weighted-F1: `0.6541`
- MCC: `0.2503`
- balanced accuracy: `0.4413`

XGBoost GPU test:

- accuracy: `0.7033`
- macro-F1: `0.4440`
- weighted-F1: `0.6499`
- MCC: `0.2449`
- balanced accuracy: `0.4311`

Đánh giá: XGBoost tăng accuracy nhẹ nhưng làm giảm macro-F1/MCC/balanced accuracy. Vì label ternary và regime imbalance, macro-F1/MCC quan trọng hơn accuracy đơn thuần. Do đó XGBoost chưa đủ để thay SGD làm forecasting baseline chính.

## 5. Execution tuned trên test

SGD tuned:

- naive tuned: `26,076` trades, net PnL `-3,361.70`.
- cost-aware tuned: `21,469` trades, net PnL `-2,582.29`.
- RSEP tuned: `16,693` trades, net PnL `-1,898.19`.

XGBoost GPU tuned:

- naive tuned: `108,849` trades, net PnL `-12,496.41`.
- cost-aware tuned: `9,982` trades, net PnL `-1,045.75`.
- RSEP tuned: `10,138` trades, net PnL `-1,047.17`.

So với Stage 2 cũ:

- SGD RSEP cũ: net `-4,042.46`, `35,664` trades.
- SGD RSEP tuned: net `-1,898.19`, `16,693` trades.
- Cost-aware cũ: net `-28,050.37`, `237,158` trades.
- Cost-aware tuned SGD: net `-2,582.29`, `21,469` trades.

Đánh giá: tuning giải quyết đúng điểm yếu policy. Tuy nhiên tất cả policy vẫn net âm ở fee `1 bps`, nên claim vẫn là mitigation, không phải profitability.

## 6. Bootstrap và stress

Bootstrap RSEP tuned vs cost-aware tuned:

- SGD: mean diff `23.59`, CI `[11.34, 39.22]`, `n_days=29`, `n_bootstrap=1000`.
- XGBoost GPU: mean diff `-0.05`, CI `[-2.88, 2.47]`, `n_days=29`, `n_bootstrap=1000`.

Diễn giải:

- Với SGD, RSEP tuned cải thiện nhỏ nhưng có CI dương so với cost-aware tuned.
- Với XGBoost, RSEP và cost-aware gần như hòa; RSEP không chứng minh được lợi thế thống kê.

Stress tuned SGD:

- fee `0 bps`: net `1,439.93`.
- fee `1 bps`: net `-1,898.19`.
- fee `2 bps`: net `-5,236.32`.
- fee `5 bps`: net `-15,250.69`.
- fee `10 bps`: net `-31,941.31`.
- latency `0/1/5/10`: net `-1,538.28 / -1,898.19 / -2,442.22 / -2,744.07`.

Đánh giá: stress vẫn giữ kết luận Stage 2: phí là bottleneck chính; latency làm edge suy giảm; spread/depth transform nhẹ hơn trong simulator hiện tại.

## 7. Principal ML Scientist review

Điểm mạnh:

- Tuning dùng validation-only, không dùng test để chọn threshold.
- Baseline cost-aware đã được sửa thành baseline công bằng hơn.
- XGBoost GPU đã được kiểm tra thực nghiệm, không chỉ giả định.
- Simulator runtime tốt hơn nhờ lặp qua non-zero signals.

Điểm yếu:

- XGBoost accuracy cao hơn nhưng macro-F1/MCC thấp hơn; chưa chứng minh model phi tuyến tốt hơn cho paper.
- Test net PnL của XGBoost cost-aware tốt nhất, nhưng không nên chọn policy/model chính chỉ vì test tốt.
- Cả SGD và XGBoost vẫn âm net ở fee `1 bps`; paper phải tiếp tục tránh claim sinh lời.

Khuyến nghị:

- Stage 3 nên chạy ít nhất SGD tuned vì đây là baseline ổn định và kỷ luật hơn.
- Nếu disk/compute cho phép, chạy thêm XGBoost GPU tuned như baseline phụ vì test execution tốt, nhưng phải ghi rõ selection không dựa trên test.
- Chưa mở TCN/DeepLOB-lite trước khi Stage 3 full-year path ổn định.

## 8. Reviewer ICDM review

Điểm tăng sức thuyết phục:

- Baseline threshold không còn bị reviewer bắt lỗi vì chưa tune validation.
- Có model phi tuyến GPU baseline, dù kết quả không thắng toàn diện.
- Có bảng so sánh model-policy trực tiếp và bootstrap tuned.

Rủi ro còn lại:

- Chỉ BTC, chưa có asset-held-out.
- XGBoost không cải thiện macro-F1/MCC nên chưa đủ để claim modeling advance.
- Execution vẫn là simulator approximation và net PnL âm.
- Nếu Stage 3 chỉ chạy SGD, reviewer có thể hỏi vì sao không có XGBoost full-year; cần giải thích theo compute hoặc chạy thêm nếu khả thi.

## 9. Gate và bước tiếp theo

Gate Stage 2.5: **PASS có điều kiện**

- Validation-only tuning: pass.
- Cost-aware baseline được sửa: pass.
- XGBoost GPU chạy được: pass.
- Bootstrap tuned có `n_days > 1`: pass.
- Model mạnh hơn chưa thắng forecasting: không pass cho claim model improvement.

Go/no-go:

- **GO cho Stage 3 full-year** với cấu hình tuned.
- **GO cho XGBoost GPU như baseline phụ nếu tài nguyên đủ**.
- **NO-GO cho profitability claim**.
- **NO-GO cho deep baseline ngay trong bước kế tiếp**, trừ khi Stage 3 full-year chạy ổn và disk budget đủ.

Mặc định mang sang Stage 3:

- Taxonomy refined giữ nguyên.
- Policy tuning validation-only giữ nguyên.
- SGD tuned là baseline chính.
- XGBoost GPU tuned là baseline phụ/optional nhưng nên chạy nếu còn đủ thời gian.
