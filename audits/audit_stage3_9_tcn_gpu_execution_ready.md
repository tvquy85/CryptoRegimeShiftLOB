# Audit Stage 3.9: TCN GPU Execution-Ready Inference + RSEP

- `run_id` chính:
  - `stage3_9_tcn_gpu_execution_ready_btc_full2024_v001`
  - `stage3_9_tune_tcn_gpu_btc_full2024_v001`
  - `stage3_9_stress_tcn_gpu_btc_full2024_v002`
  - `stage3_9_model_comparative_with_tcn_btc_full2024_v002`
  - `stage3_9_report_tcn_gpu_btc_full2024_v002`
- Stage: `stage_3_full_scale`
- Symbol: `BTC-USDT`
- Model: `tcn_gpu_stage3`
- Device: `NVIDIA GeForce RTX 3090`

## Mục Tiêu

Nối TCN temporal pilot sang cùng execution protocol với SGD/XGBoost: sinh prediction artifact đủ cột L2 execution, tune policy trên validation, chạy RSEP/stress, và cập nhật model-comparative report pack. Không train lại model và không claim profitability.

## Cấu Hình Chính

- Source: `data/predictions/predictions.parquet`
- Checkpoint: `outputs/checkpoints/stage3_8_tcn_gpu_pilot_btc_full2024_v001_tcn_gpu_stage3_pilot.pt`
- Output: `data/predictions/predictions_stage3_tcn_gpu_execution_ready.parquet`
- Window: `100`
- Input: 10 LOB levels đầu, 40 features.
- Stride: train/valid/test đều `10`.
- Rows:
  - train `1,000,000`
  - valid `3,354,576`
  - test `3,354,594`
  - total `7,709,170`
- Inference batch windows: `16,384`
- AMP: bật.
- Pinned memory: bật.
- `torch.compile`: đã probe nhưng fallback eager do lỗi TorchInductor trên Windows; production config đặt `compile_model: false`.
- Runtime inference: khoảng `1,961.66s`, throughput khoảng `3,929.93` windows/s.

## Kết Quả Forecasting

Trên test windows stride-10:

- accuracy: `0.5282`
- macro-F1: `0.4689`
- MCC: `0.2275`
- balanced accuracy: `0.4692`

So với baseline full-year:

- SGD: macro-F1 `0.4652`, MCC `0.2363`, balanced accuracy `0.4637`.
- XGBoost GPU: macro-F1 `0.4562`, MCC `0.2364`, balanced accuracy `0.4555`.
- TCN stride-10: macro-F1 và balanced accuracy nhỉnh hơn, nhưng MCC thấp hơn SGD/XGBoost.

## Kết Quả Execution/RSEP

Policy tuning validation-only cho TCN stride-10:

- naive threshold: `0.6`, valid net PnL `-460.40`
- cost-aware threshold: `3.6714177e-05`, valid net PnL `-257.64`
- RSEP-full threshold: `1.4391646e-05`, valid net PnL `-244.41`

Test execution:

- naive tuned: `3,100` trades, net PnL `-1,231.72`
- cost-aware tuned: `656` trades, net PnL `-224.11`
- RSEP-full tuned: `619` trades, gross PnL `-4.66`, net PnL `-128.43`, net PnL/trade `-0.2075`

Bootstrap RSEP vs cost-aware:

- mean diff: `1.4951`
- CI: `[0.0229, 3.5550]`
- `n_days = 64`
- `n_bootstrap = 1000`

## Stress

Stress tuned RSEP có đủ axes: `fee_bps`, `latency_events`, `spread_multiplier`, `depth_multiplier`.

Fee curve:

- fee `0 bps`: net PnL `-4.66`
- fee `1 bps`: net PnL `-128.43`
- fee `2 bps`: net PnL `-252.19`
- fee `5 bps`: net PnL `-623.49`
- fee `10 bps`: net PnL `-1242.31`

## Vấn Đề Phát Hiện Và Sửa

- Temporal writer pilot trước đó không đủ cột execution/RSEP. Stage 3.9 đã tạo artifact mới đủ `execution_columns(include_split=True)`.
- Generator temporal ban đầu quét parquet từ đầu cho từng split; smoke 300 rows mất hơn 70s. Đã thêm row-group pruning theo `split`, smoke giảm còn khoảng 10s.
- `07_run_stress_grid.py` trước đó overwrite bảng stress tuned theo model chạy cuối. Đã harden sang upsert theo `model` và rerun stress cho SGD/XGBoost/TCN.

## Đánh Giá Principal ML Scientist

TCN stride-10 là temporal baseline có giá trị: không collapse class và cải thiện macro-F1/balanced accuracy so với tabular trên sample stride-10. Tuy nhiên MCC thấp hơn và execution per-trade không tốt hơn, nên không nên diễn giải thành “deep temporal solves LOB execution”.

## Đánh Giá Reviewer ICDM

Stage 3.9 tăng độ thuyết phục vì paper có baseline temporal GPU, artifact đủ execution/RSEP/stress, model comparison có SGD/XGBoost/TCN, bootstrap nhiều ngày và stress curves. Rủi ro còn lại là stride-10 chưa công bằng hoàn toàn với tabular full-row.

## Quyết Định

- Pass kỹ thuật Stage 3.9.
- Đưa TCN stride-10 vào paper như temporal/deep baseline có kỷ luật.
- Không claim profitability.
- Bước tiếp theo hợp lý là Stage 3.10 TCN stride-1 fairness check.
