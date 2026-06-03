# Audit Stage 3.8A: Temporal GPU Pilot

- `run_id` chính:
  - `stage3_8_tcn_gpu_smoke_btc_full2024_v002`
  - `stage3_8_tcn_gpu_pilot_btc_full2024_v001`
  - `stage3_8_deeplob_faithful_lite_gpu_pilot_btc_full2024_v001`
- Stage: `stage_3_full_scale`
- Symbol: `BTC-USDT`
- Device: `NVIDIA GeForce RTX 3090`
- Mục tiêu: kiểm tra baseline temporal/deep LOB trên full-year prediction source mà không rebuild feature/regime/split và không ghi đè SGD/XGBoost artifacts.

## Cấu hình chính

- Source: `data/predictions/predictions.parquet`
- Input temporal: 10 LOB levels đầu, 40 features theo thứ tự `ask_price_rel`, `ask_size_log`, `bid_price_rel`, `bid_size_log`.
- Window: `100`
- Train stride: `5`
- Valid/test stride: `10`
- Pilot cap:
  - train `1,000,000` windows
  - valid `250,000` windows
  - test `500,000` windows
- Scaler fit train-only.
- Mixed precision bật trên CUDA.
- Không chạy execution/RSEP cho temporal model trong Stage 3.8A.

## Artifact đã sinh

- `data/predictions/predictions_stage3_tcn_gpu_pilot.parquet`
- `data/predictions/predictions_stage3_deeplob_faithful_lite_pilot.parquet`
- `outputs/tables/table_forecasting_overall_stage3_temporal_pilot_stage3.csv`
- `outputs/tables/table_forecasting_by_regime_stage3_temporal_pilot_stage3.csv`
- `outputs/tables/table_temporal_vs_tabular_comparison_stage3.csv`
- Checkpoints:
  - `outputs/checkpoints/stage3_8_tcn_gpu_pilot_btc_full2024_v001_tcn_gpu_stage3_pilot.pt`
  - `outputs/checkpoints/stage3_8_deeplob_faithful_lite_gpu_pilot_btc_full2024_v001_deeplob_faithful_lite_stage3_pilot.pt`

## Kết quả chính

Baseline full-year để đối chiếu:

- `sgd_stage3`: macro-F1 `0.4652`, MCC `0.2363`, balanced accuracy `0.4637`.
- `xgboost_gpu_stage3`: macro-F1 `0.4562`, MCC `0.2364`, balanced accuracy `0.4555`.

Temporal pilot:

- `tcn_gpu_stage3_pilot`:
  - test windows `500,000`
  - accuracy `0.5645`
  - macro-F1 `0.4726`
  - MCC `0.2388`
  - balanced accuracy `0.4741`
  - best validation macro-F1 `0.4572` ở epoch `5`
- `deeplob_faithful_lite_stage3_pilot`:
  - test windows `500,000`
  - accuracy `0.5198`
  - macro-F1 `0.4337`
  - MCC `0.1606`
  - balanced accuracy `0.4421`
  - best validation macro-F1 `0.4416` ở epoch `1`, sau đó giảm và early-stopped.

## By-regime observations

- TCN không collapse một class: MCC by-regime dương ở hầu hết regime lớn.
- TCN yếu nhất ở `CHOPPY_MEAN_REVERTING` nhưng vẫn có macro-F1 `0.3571`; các regime như `MOMENTUM_TOXIC`, `SHOCK_RECOVERY`, `UNKNOWN`, `VOLATILE_ILLIQUID` có macro-F1 quanh `0.456-0.471`.
- DeepLOB-faithful-lite ổn định hơn smoke nhưng thấp hơn TCN ở hầu hết metric tổng thể; chỉ có một số regime nhỏ như `CALM_LIQUID`/`CHOPPY_MEAN_REVERTING` không thua quá xa.
- `VOLATILE_LIQUID` chỉ có `40` test windows trong pilot, không nên diễn giải mạnh.

## Vấn đề phát hiện

- Stage 3.8A là sample-window pilot, chưa phải full-year stride-1 inference. Không được claim temporal model đã thắng full-year benchmark hoàn chỉnh.
- TCN pilot vượt nhẹ SGD/XGBoost về macro-F1/MCC trên sample pilot, nhưng cần kiểm chứng bằng full temporal inference hoặc ít nhất resample nhiều window blocks.
- DeepLOB-faithful-lite không vượt TCN; kết quả cho thấy kiến trúc sát DeepLOB hơn chưa chắc tốt hơn trong protocol hiện tại nếu chưa tune sâu.
- TCN có thể là baseline temporal thực dụng hơn cho Stage 3.9 vì rẻ hơn, ổn định hơn và đạt metric tốt hơn DeepLOB-faithful-lite trong pilot.

## Đánh giá Principal ML Scientist

- TCN pilot là tín hiệu tích cực: macro-F1 `0.4726` và MCC `0.2388` nhỉnh hơn tabular baselines, dù chỉ trên 500k test windows.
- DeepLOB-faithful-lite là evidence cần thiết cho reviewer vì sát literature, nhưng hiện không đáng làm model chính.
- Không nên tối ưu ad hoc DeepLOB để làm đẹp số; nếu tiếp tục, cần ablation có kỷ luật: learning rate, class weights, dropout, và balanced sampling theo regime.
- Bước khoa học tốt nhất là mở Stage 3.9 cho **TCN full temporal inference + tuned execution**, còn DeepLOB giữ làm baseline phụ/negative baseline.

## Đánh giá Reviewer ICDM

- Điểm mạnh: paper giờ có baseline temporal/deep LOB chạy trên RTX 3090, có by-regime diagnostics và không đụng vào test để tune execution.
- Rủi ro: temporal pilot chưa phải full-year inference; reviewer có thể hỏi liệu kết quả sample có ổn định trên toàn bộ test set không.
- DeepLOB-faithful-lite không thắng có thể được trình bày trung thực như negative baseline: canonical LOB-style CNN+temporal model không tự động giải quyết forecast-to-execution degradation.
- TCN nên được đưa vào candidate main forecasting table chỉ sau Stage 3.9 full inference hoặc một validation protocol sampling lặp lại.

## Quyết định

- Pass gate kỹ thuật Stage 3.8A.
- Không chạy execution/RSEP cho DeepLOB-faithful-lite ở bước này.
- Bước tiếp theo khuyến nghị:
  1. Mở Stage 3.9 cho `tcn_gpu_stage3_pilot` full temporal inference hoặc larger deterministic inference trên toàn bộ test split.
  2. Sau khi có TCN predictions đủ lớn, chạy validation-only policy tuning, RSEP và stress giống SGD/XGBoost.
  3. Giữ DeepLOB-faithful-lite trong paper như baseline phụ/negative evidence, không claim nó là model mạnh nhất.
