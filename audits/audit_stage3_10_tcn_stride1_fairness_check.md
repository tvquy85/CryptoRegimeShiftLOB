# Audit Stage 3.10: TCN Stride-1 Fairness Check

- `run_id` chính:
  - `stage3_10_tcn_stride1_btc_full2024_v001`
  - `stage3_10_tune_tcn_stride1_btc_full2024_v001`
  - `stage3_10_stress_tcn_stride1_btc_full2024_v001`
  - `stage3_10_model_comparative_with_tcn_stride1_btc_full2024_v001`
  - `stage3_10_report_tcn_stride1_btc_full2024_v001`
- Stage: `stage_3_full_scale`
- Symbol: `BTC-USDT`
- Model: `tcn_gpu_stage3_stride1`
- Device: `NVIDIA GeForce RTX 3090`

## Mục Tiêu

Stage 3.10 kiểm tra công bằng hơn cho TCN bằng cách chạy valid/test với `stride=1`, thay vì chỉ stride-10 như Stage 3.9. Mục tiêu là trả lời rủi ro reviewer: liệu TCN temporal baseline có giữ metric khi đánh giá gần full-row như SGD/XGBoost không.

## Cấu Hình Chính

- Source: `data/predictions/predictions.parquet`
- Checkpoint: `outputs/checkpoints/stage3_8_tcn_gpu_pilot_btc_full2024_v001_tcn_gpu_stage3_pilot.pt`
- Output: `data/predictions/predictions_stage3_tcn_gpu_stride1_execution_ready.parquet`
- Window: `100`
- Input: 10 LOB levels đầu, 40 features.
- Stride:
  - train `10`, sample cap `1,000,000`
  - valid `1`
  - test `1`
- Rows:
  - train `1,000,000`
  - valid `33,544,420`
  - test `33,543,827`
  - total `68,088,247`
- Inference batch windows: `16,384`
- AMP: bật.
- Pinned memory: bật.
- `torch.compile`: tắt do TorchInductor Windows đã fallback lỗi ở probe trước đó.
- Runtime inference: khoảng `21,960.35s`
- Throughput: khoảng `3,100.51` windows/s
- Output size: khoảng `10.24GB`

## Kết Quả Forecasting

TCN stride-1 trên test:

- accuracy: `0.5281`
- macro-F1: `0.4688`
- MCC: `0.2274`
- balanced accuracy: `0.4691`
- test rows: `33,543,827`

So với TCN stride-10:

- stride-10 macro-F1 `0.4689`, MCC `0.2275`, balanced accuracy `0.4692`
- stride-1 macro-F1 `0.4688`, MCC `0.2274`, balanced accuracy `0.4691`

Kết luận forecasting: TCN không collapse khi mở rộng từ stride-10 sang stride-1. Metric gần như giữ nguyên, nên TCN có thể được báo cáo như temporal baseline ổn định hơn về mặt forecasting.

So với tabular baselines:

- SGD: accuracy `0.5589`, macro-F1 `0.4652`, MCC `0.2363`, balanced accuracy `0.4637`
- XGBoost GPU: accuracy `0.5677`, macro-F1 `0.4562`, MCC `0.2364`, balanced accuracy `0.4555`
- TCN stride-1: accuracy thấp hơn, macro-F1/balanced accuracy cao hơn, MCC thấp hơn.

## Kết Quả Execution/RSEP

Policy tuning validation-only:

- naive threshold: `0.6`, valid net PnL `-855.25`
- cost-aware threshold: `3.6634694e-05`, valid net PnL `-440.99`
- RSEP-full threshold: `1.1165357e-05`, valid net PnL `-389.67`

Test execution:

- naive tuned: `19,932` trades, net PnL `-3,355.28`
- cost-aware tuned: `4,570` trades, net PnL `-787.998`
- RSEP-full tuned: `5,435` trades, gross PnL `271.73`, net PnL `-814.17`, net PnL/trade `-0.1498`

Bootstrap RSEP vs cost-aware:

- mean diff: `-0.4026`
- CI: `[-4.4605, 4.4494]`
- `n_days = 65`
- `n_bootstrap = 1000`

Diễn giải đúng: RSEP stride-1 không cải thiện có ý nghĩa so với cost-aware trên test; CI cắt qua 0 và mean diff âm. Đây là negative evidence quan trọng, cần trình bày trung thực.

## Stress

Stress tuned RSEP của TCN stride-1 có đủ axes:

- `fee_bps`
- `latency_events`
- `spread_multiplier`
- `depth_multiplier`

Fee curve:

- fee `0 bps`: net PnL `271.73`
- fee `1 bps`: net PnL `-814.17`
- fee `2 bps`: net PnL `-1,900.07`
- fee `5 bps`: net PnL `-5,157.76`
- fee `10 bps`: net PnL `-10,587.25`

Kết quả này rất phù hợp với thesis forecast-to-execution degradation: tín hiệu có gross edge dương ở fee 0, nhưng không sống sót sau fee 1 bps và cost stress.

## So Sánh Model Sau Stage 3.10

Comparative pack hiện có đủ bốn model:

- `sgd_stage3`
- `xgboost_gpu_stage3`
- `tcn_gpu_stage3`
- `tcn_gpu_stage3_stride1`

Kết luận so sánh:

- TCN stride-1 giữ forecasting macro-F1/balanced accuracy tốt nhất trong nhóm, nhưng MCC thấp hơn SGD/XGBoost.
- XGBoost vẫn có accuracy cao nhất nhưng macro-F1/balanced accuracy thấp hơn.
- SGD vẫn là baseline tabular mạnh và ổn định hơn về MCC.
- TCN stride-1 không vượt được cost-aware trong paired bootstrap execution; vì vậy không nên claim RSEP cải thiện chắc cho TCN stride-1.

## Vấn Đề Phát Hiện Và Sửa

- Script inference trước đó ghi audit path cố định `audit_stage3_9_tcn_gpu_execution_ready.md`, khiến run stride-1 có thể overwrite audit Stage 3.9. Đã thêm `temporal_inference.audit_output` trong config để các stage sau ghi audit riêng.
- Forecasting output của script inference đã chuyển sang `model_stage_table_path`, tránh ghi đè bảng TCN stride-10 khi chạy model label mới.

## Đánh Giá Principal ML Scientist

Stage 3.10 là kết quả tốt về mặt forecasting rigor: nó xác nhận TCN stride-10 không phải artifact của sampling thưa. Tuy nhiên execution evidence lại yếu hơn narrative “RSEP cải thiện policy” vì RSEP không thắng cost-aware trên TCN stride-1 theo bootstrap. Do đó contribution nên nhấn vào benchmark/failure-analysis, regime/stress protocol, và selective execution như một baseline có điều kiện, không phải method luôn thắng.

## Đánh Giá Reviewer ICDM

Điểm mạnh:

- Temporal baseline GPU đã được kiểm tra trên full-size test rows.
- Sampling fairness risk của TCN đã giảm đáng kể.
- Có negative result trung thực: forecasting tốt hơn macro-F1 không đảm bảo execution tốt hơn.
- Stress curves cho thấy edge biến mất nhanh khi phí tăng.

Rủi ro còn lại:

- ETH/asset-held-out vẫn bị chặn vì chưa có ETH data.
- Deep models mới có một seed; nếu muốn claim mạnh về deep baseline, cần thêm seed hoặc giải thích compute/time boundary.
- RSEP không consistently thắng cost-aware ở mọi model, nên main claim phải giữ kỷ luật.

## Quyết Định

- Pass Stage 3.10 fairness check.
- Đưa `tcn_gpu_stage3_stride1` vào main model comparison table.
- Không claim TCN/RSEP tạo trading profitability.
- Narrative paper nên chuyển rõ về:
  - regime/stress benchmark;
  - forecast-to-execution degradation;
  - robust selective execution có ích trong một số setting nhưng không phải universal win;
  - negative evidence dưới cost là contribution khoa học.

## Bước Tiếp Theo

Khuyến nghị không mở thêm model ad hoc ngay. Bước kế tiếp nên là **Stage 3.11 Paper Evidence Hardening**:

1. Chốt bảng/figure paper assets theo bốn model.
2. Viết result narrative tiếng Việt/outline paper theo claim discipline.
3. Tạo acceptance-bar audit đối chiếu từng tiêu chí trong `TongQuan.md`.
4. Chỉ mở ETH/asset-held-out khi có ETH data.
