# Audit Stage 3.7: Model-Comparative Stress Pack

- `run_id`: `stage3_7_model_comparative_stress_pack_v001`
- Stage: `stage_3_full_scale`
- Symbol: `BTC-USDT`
- Mục tiêu: gom bằng chứng so sánh `sgd_stage3` và `xgboost_gpu_stage3` trong cùng một pack forecasting, tuned execution, bootstrap, stress và robustness để paper assets không phụ thuộc vào model vừa chạy gần nhất.

## Cấu hình chính

- Không rebuild feature, label, regime, split hoặc prediction.
- Không train lại XGBoost GPU.
- Nguồn SGD stress: bảng tuned stress legacy có `model=sgd_stage3`.
- Nguồn XGBoost stress: bảng tuned stress Stage 3 có `model=xgboost_gpu_stage3`.
- Policy so sánh: tuned `RSEP-full` trên test full-year.
- Fee mặc định trong simulator: `1 bps`.

## Artifact đã sinh

- `outputs/tables/table_model_forecasting_execution_comparison_stage3.csv`
- `outputs/tables/table_model_stress_comparison_stage3.csv`
- `outputs/tables/table_model_robustness_comparison_stage3.csv`
- `outputs/figures/model_fee_stress_stage3.png`
- `outputs/figures/model_latency_stress_stage3.png`
- `outputs/paper_assets/table_8_model_forecasting_execution_comparison.csv`
- `outputs/paper_assets/table_9_model_stress_comparison.csv`
- `outputs/paper_assets/table_10_model_robustness_comparison.csv`
- `outputs/paper_assets/fig_7_model_fee_stress.png`
- `outputs/paper_assets/fig_8_model_latency_stress.png`

## Kết quả chính

Forecasting full-year:

- `sgd_stage3`: accuracy `0.5589`, macro-F1 `0.4652`, MCC `0.2363`, balanced accuracy `0.4637`.
- `xgboost_gpu_stage3`: accuracy `0.5677`, macro-F1 `0.4562`, MCC `0.2364`, balanced accuracy `0.4555`.
- XGBoost tăng accuracy và MCC rất nhẹ, nhưng thua SGD ở macro-F1 và balanced accuracy.

Tuned execution với `RSEP-full`:

- `sgd_stage3`: gross PnL `+2,300.82`, net PnL `-4,437.49`, `33,713` trades.
- `xgboost_gpu_stage3`: gross PnL `+2,953.00`, net PnL `-4,303.19`, `36,360` trades.
- XGBoost cải thiện net loss khoảng `134.30`, nhưng cả hai vẫn âm ở fee `1 bps`.

Bootstrap RSEP so với cost-aware:

- `sgd_stage3`: mean diff `68.53`, CI `[59.68, 77.23]`, `65` ngày, `1000` bootstrap.
- `xgboost_gpu_stage3`: mean diff `2.94`, CI `[1.07, 4.93]`, `65` ngày, `1000` bootstrap.
- SGD cho tín hiệu RSEP-vs-cost-aware mạnh hơn nhiều về bootstrap margin, dù XGBoost có net PnL cuối tốt hơn nhẹ.

Stress:

- Fee `0 bps`: SGD `+2,300.82`, XGBoost `+2,953.00`.
- Fee `1 bps`: SGD `-4,437.49`, XGBoost `-4,303.19`.
- Fee `10 bps`: SGD `-65,082.32`, XGBoost `-69,608.93`.
- Latency `0`: SGD `-3,569.73`, XGBoost `-3,540.18`.
- Latency `10`: SGD `-6,096.92`, XGBoost `-5,761.12`.

Diễn giải: XGBoost nhỉnh hơn ở latency stress và baseline fee `1 bps`, nhưng xấu hơn khi fee tăng mạnh. Điều này củng cố luận điểm edge execution rất mỏng và sensitivity theo cost quan trọng hơn chênh lệch accuracy nhỏ.

## Vấn đề phát hiện

- Một phần kết quả SGD stress vẫn đến từ bảng legacy có hậu tố `stage2`, dù dòng model là `sgd_stage3`. Stage 3.7 đã gom lại thành bảng canonical `table_model_stress_comparison_stage3.csv`, nhưng audit paper cần mô tả rõ đây là normalization artifact naming, không phải chạy Stage 2.
- XGBoost không tạo bước nhảy rõ về macro-F1/balanced accuracy. Nếu đưa vào main table, nên gọi là strong tabular baseline phụ hoặc negative baseline, không phải model chính.
- Net PnL vẫn âm ở fee `1 bps`; kết quả phải được trình bày như forecast-to-execution degradation và mitigation, không phải profitability.

## Đánh giá Principal ML Scientist

- Pack mới giúp so sánh model công bằng hơn vì cùng đặt SGD và XGBoost dưới một stress grid.
- XGBoost cho thấy accuracy cao hơn không đồng nghĩa cải thiện robustness một cách nhất quán.
- Bootstrap margin của SGD RSEP so với cost-aware mạnh hơn đáng kể, hỗ trợ việc giữ SGD làm baseline chính cho narrative robust selective execution.
- Cần deep baseline chỉ khi muốn kiểm tra liệu temporal representation học được tín hiệu by-regime tốt hơn, không phải để tối ưu ad hoc cho PnL.

## Đánh giá Reviewer ICDM

- Điểm mạnh: có comparison table, stress curves, bootstrap, và artifact naming rõ hơn. Đây là cải thiện reproducibility cần thiết cho paper.
- Rủi ro: chưa có asset-held-out vì thiếu ETH; chưa có deep temporal baseline full-year.
- Cách trình bày nên nhấn mạnh benchmark/protocol và failure-analysis. XGBoost là bằng chứng rằng model mạnh hơn về accuracy vẫn có thể không giải quyết forecast-to-execution degradation.
- Không nên claim trading-ready hoặc exact execution realism vì simulator là snapshot-level L2 approximation.

## Quyết định

- Pass Stage 3.7 cho mục tiêu reproducibility và model-comparative evidence.
- Có thể đưa `xgboost_gpu_stage3` vào main comparison table, nhưng không thay `sgd_stage3` làm narrative chính.
- Bước tiếp theo hợp lý:
  1. Nếu ưu tiên model strength: mở TCN/DeepLOB-lite GPU ở scale kiểm soát.
  2. Nếu ưu tiên generalization: chuẩn bị ETH data để mở asset-held-out.
  3. Nếu ưu tiên paper writing: dùng Stage 3.7 pack để viết phần empirical evidence và limitations.
