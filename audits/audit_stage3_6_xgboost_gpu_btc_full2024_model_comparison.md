# Audit Stage 3.6 XGBoost GPU BTC Full-Year Model Comparison

## run_id

- Forecast: `stage3_6_forecast_xgboost_gpu_btc_full2024_v002`
- Policy tuning: `stage3_6_tune_xgboost_gpu_btc_full2024_v001`
- Stress grid: `stage3_6_stress_xgboost_gpu_btc_full2024_v001`
- Report pack: `stage3_6_report_xgboost_gpu_btc_full2024_v001`

## Mục tiêu thí nghiệm

Mục tiêu của Stage 3.6 là kiểm tra một baseline tabular mạnh hơn SGD trên BTC-USDT full-year 2024 bằng XGBoost GPU, sau đó đánh giá liệu cải thiện forecasting có chuyển thành cải thiện execution hay không.

Thí nghiệm này không nhằm claim profitability. Nó nhằm tăng độ nghiêm túc của benchmark trước reviewer ICDM bằng cách tránh chỉ dựa vào SGD.

## Cấu hình chính

- Data source: `data/predictions/predictions.parquet`
- XGBoost output: `data/predictions/predictions_stage3_xgboost_gpu.parquet`
- Model label: `xgboost_gpu_stage3`
- Backend: `xgboost_gpu`
- Train sample: `4,792,895 / 100,650,783` train rows
- Valid sample: `986,773 / 33,550,261` valid rows
- Test rows: `33,550,262`
- Features: 15 tabular causal microstructure features giống SGD Stage 3
- GPU: NVIDIA RTX 3090
- Execution config: fee `1 bps`, latency `1` event, market-order replay snapshot L2

## Kết quả forecasting

So với `sgd_stage3`:

| model | accuracy | macro-F1 | MCC | balanced accuracy |
|---|---:|---:|---:|---:|
| `sgd_stage3` | 0.5589 | 0.4652 | 0.2363 | 0.4637 |
| `xgboost_gpu_stage3` | 0.5677 | 0.4562 | 0.2364 | 0.4555 |

Diễn giải:

- XGBoost GPU tăng accuracy khoảng `+0.0087`.
- Macro-F1 thấp hơn SGD khoảng `-0.0090`.
- MCC gần như ngang SGD.
- Balanced accuracy thấp hơn SGD.

By-regime:

- XGBoost tốt hơn SGD ở một vài regime như `CHOPPY_MEAN_REVERTING`, `MILD_LIQUIDITY_STRESS`, `VOLATILE_LIQUID`.
- XGBoost yếu hơn SGD ở các vùng quan trọng như `BALANCED_TRANSITION`, `CALM_LIQUID`, `UNKNOWN`, và thấp hơn nhẹ ở `SHOCK_RECOVERY`.
- Vì macro-F1 thấp hơn, không nên claim XGBoost là forecasting baseline tổng thể mạnh hơn SGD. Nó là baseline phụ có accuracy cao hơn nhưng class/regime balance kém hơn.

## Kết quả execution tuned

Validation-only tuning chọn `RSEP-full` là best validation policy cho XGBoost:

- Best validation policy: `RSEP-full`
- Validation net PnL: `-492.45`
- Validation trades: `4,050`

Test tuned results:

| policy | trades | gross PnL | net PnL | total cost |
|---|---:|---:|---:|---:|
| `xgboost_gpu_stage3_naive_threshold_tuned` | 880,927 | 60,722.27 | -115,238.26 | 175,960.53 |
| `xgboost_gpu_stage3_cost_aware_threshold_tuned` | 37,945 | 3,078.89 | -4,494.39 | 7,573.28 |
| `xgboost_gpu_stage3_RSEP-full_tuned` | 36,360 | 2,953.00 | -4,303.19 | 7,256.19 |

So với `sgd_stage3_RSEP-full_tuned`:

- SGD tuned RSEP net PnL: `-4,437.49`
- XGBoost tuned RSEP net PnL: `-4,303.19`
- XGBoost cải thiện khoảng `+134.30`, nhưng vẫn âm ở fee `1 bps`.

Bootstrap RSEP vs cost-aware trong riêng XGBoost:

- Mean diff: `2.94`
- 95% CI: `[1.07, 4.93]`
- n_days: `65`
- n_bootstrap: `1000`

Diễn giải:

- RSEP vẫn tốt hơn cost-aware cho XGBoost, nhưng biên cải thiện nhỏ hơn nhiều so với SGD.
- XGBoost naive threshold trade quá nhiều và sụp mạnh sau cost, đây là bằng chứng tiếp tục ủng hộ forecast-to-execution degradation.

## Stress grid

Stress tuned XGBoost RSEP-full:

- Fee 0 bps: net PnL `+2,953.00`
- Fee 1 bps: net PnL `-4,303.19`
- Fee 2 bps: net PnL `-11,559.39`
- Fee 5 bps: net PnL `-33,327.97`
- Fee 10 bps: net PnL `-69,608.93`

Latency:

- 0 event: `-3,540.18`
- 1 event: `-4,303.19`
- 5 events: `-5,212.98`
- 10 events: `-5,761.12`

Spread/depth stress làm net PnL xấu hơn nhưng nhẹ hơn fee và latency trong simulator hiện tại.

Diễn giải:

- XGBoost có gross edge dương ở zero fee nhưng không sống sót qua fee `1 bps`.
- Trục fee vẫn là failure mode chính; kết quả này phù hợp với narrative paper hơn là mâu thuẫn.

## Vấn đề phát hiện

1. XGBoost cải thiện accuracy nhưng không cải thiện macro-F1.
2. XGBoost execution tốt hơn SGD tuned RSEP một chút, nhưng biên cải thiện nhỏ và vẫn net âm.
3. Naive threshold của XGBoost trade quá dày, tạo net loss rất lớn.
4. Stress report pack hiện phản ánh model được regenerate sau cùng; nếu muốn paper assets chứa stress của cả SGD và XGBoost, cần thêm bảng/figure model-comparative stress thay vì single-model stress.

## Nguyên nhân khả dĩ

- XGBoost tối ưu logloss/multiclass probability tốt hơn cho majority/average accuracy, nhưng không nhất thiết cải thiện minority regimes/classes.
- Cost-aware label và execution edge rất mỏng; tăng một chút accuracy không đủ để vượt fee/spread.
- Naive threshold không xét cost/risk nên đặc biệt dễ overtrade khi XGBoost tạo nhiều xác suất vượt ngưỡng thấp `0.5`.
- Sampling train/valid deterministic giúp chạy được full-year, nhưng vẫn có thể làm XGBoost chưa khai thác hết dữ liệu như một online/streaming learner.

## Mức độ ảnh hưởng đến paper

Tác động tích cực:

- Paper không còn chỉ có SGD làm full-year baseline.
- XGBoost GPU tạo baseline tabular mạnh hơn về accuracy và hơi tốt hơn về tuned execution.
- Kết quả tiếp tục củng cố thesis: forecasting score tốt hơn không bảo đảm execution profitability.

Tác động hạn chế:

- XGBoost không đủ để claim model improvement mạnh.
- Kết quả nên được trình bày là stronger baseline / robustness check, không phải contribution chính.

## Đánh giá theo chuẩn ICDM 2026

### Principal ML Scientist

Stage 3.6 làm benchmark nghiêm túc hơn vì có baseline phi tuyến GPU trên full-year. Tuy nhiên kết quả cho thấy bottleneck không chỉ là forecasting model mà là cost/execution regime. Đây là điểm khoa học quan trọng: model mạnh hơn theo accuracy vẫn bị bào mòn bởi phí và stress.

Không nên tối ưu ad hoc XGBoost để làm đẹp số. Nếu muốn cải thiện thực chất, hướng đúng hơn là:

- thêm objective calibration / macro-F1 hoặc class-balanced tuning;
- thêm model deep temporal có kiểm soát;
- hoặc mở ETH/asset-held-out để tăng sức nặng generalization.

### Reviewer ICDM

Reviewer sẽ đánh giá cao việc có thêm XGBoost GPU full-year. Nhưng nếu paper chỉ nói “XGBoost tốt hơn” thì sẽ yếu vì macro-F1 thấp hơn SGD. Cách trình bày thuyết phục hơn là:

- XGBoost kiểm tra tính robust của benchmark với baseline mạnh hơn SGD.
- Kết quả mixed: accuracy tăng, macro-F1 giảm, execution chỉ cải thiện nhẹ.
- Điều này làm nổi bật lý do cần evaluation protocol đa chiều thay vì chọn model theo một metric.

## Quyết định

Pass Stage 3.6 với vai trò **baseline phụ / robustness check**.

Không đưa XGBoost GPU làm model chính thay SGD trong narrative forecasting, vì macro-F1 và balanced accuracy thấp hơn SGD. Có thể đưa vào main model comparison table vì:

- accuracy tốt hơn;
- MCC ngang;
- tuned RSEP net PnL tốt hơn SGD nhẹ;
- giúp chứng minh kết luận paper không phụ thuộc vào một model tuyến tính.

Không claim profitability:

- Best XGBoost tuned RSEP vẫn net PnL `-4,303.19` ở fee `1 bps`.

## Bước tiếp theo

Ưu tiên tiếp theo:

1. Tạo model-comparative stress table/figure nếu muốn paper assets so sánh trực tiếp SGD vs XGBoost dưới stress.
2. Chuẩn bị narrative paper: “accuracy improvement does not guarantee execution survival”.
3. Nếu còn compute, chạy TCN/DeepLOB-lite ở scale kiểm soát trước, không full-year ngay.
4. Nếu có ETH data, ưu tiên ETH/asset-held-out hơn deep baseline vì generalization sẽ tăng sức thuyết phục ICDM mạnh hơn.
