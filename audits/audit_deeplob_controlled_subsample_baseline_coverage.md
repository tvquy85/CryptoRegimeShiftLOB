# Audit Stage 3.8: Temporal GPU Pilot

- `run_id`: xem metadata tương ứng trong `outputs/logs`
- Model: `deeplob_cnn_lstm_purged_subsample` (`deeplob`)
- Device: `cuda`
- Mục tiêu: kiểm tra liệu temporal/deep baseline kiểu DeepLOB/TCN có cải thiện forecasting so với SGD/XGBoost full-year hay không, trước khi mở full inference/execution.

## Artifact

- Checkpoint: `D:\LOBProj\DeepLOB\CryptoRegimeShift\outputs\checkpoints\p2_deeplob_purged_subsample_v001_deeplob_cnn_lstm_purged_subsample.pt`
- Predictions: `D:\LOBProj\DeepLOB\CryptoRegimeShift\data\predictions\predictions_stage3_deeplob_purged_subsample.parquet`
- Prediction rows: `75000`

## Kết quả forecasting test pilot

- accuracy: `0.43666`
- macro-F1: `0.34834627779651867`
- weighted-F1: `0.437442466125745`
- MCC: `0.022064539763890206`
- balanced accuracy: `0.348711542375189`
- test rows: `50000`
- best epoch: `2`
- best validation macro-F1: `0.35507561265874377`

## Đánh giá Principal ML Scientist

Temporal pilot này chỉ nên được so với SGD/XGBoost bằng macro-F1, MCC và by-regime stability. Nếu chỉ tăng accuracy nhưng macro-F1 thấp, không nên xem là baseline mạnh hơn.

## Đánh giá Reviewer ICDM

Baseline temporal giúp giảm rủi ro reviewer cho rằng paper thiếu deep LOB model. Tuy nhiên pilot sample không thay thế full-year inference; nếu kết quả hứa hẹn cần mở Stage 3.9 để chạy inference đầy đủ và execution/RSEP tương ứng.

## Quyết định

- Pass kỹ thuật nếu artifact đầy đủ, không OOM và metrics sinh được.
- Go Stage 3.9 nếu macro-F1/MCC hoặc by-regime stability cải thiện rõ so với tabular baselines.
- Nếu không cải thiện, giữ làm negative baseline và không claim deep model tốt hơn.
