# Audit Stage ETH-2: ETH within-asset SGD forecasting và execution

## Run context

- Forecast run_id: `stage_eth_forecast_sgd_full2024_v001`
- Policy tuning run_id: `stage_eth_tune_sgd_full2024_v001`
- Stress run_id: `stage_eth_stress_sgd_full2024_v001`
- Report run_id: `stage_eth_report_sgd_full2024_v001`
- Stage: `stage_3_full_scale`
- Symbol: `ETH-USDT`
- Model label: `sgd_eth_stage3`
- Config chính: `CryptoRegimeShift/configs/models_stage3_eth_sgd.yaml`
- Simulator config: `CryptoRegimeShift/configs/simulator_stage3_eth_sgd.yaml`

## Mục tiêu

Mục tiêu của ETH-2 là kiểm tra liệu thesis BTC có lặp lại trên ETH hay không: forecasting có signal, nhưng khi đưa qua phí, spread, latency và depth stress thì execution edge bị bào mòn. Đây là within-asset baseline, chưa phải asset-held-out generalization.

## Forecasting

Artifact prediction:

- `CryptoRegimeShift/data/predictions/predictions_eth_stage3_sgd.parquet`
- Rows: `114,414,433`
- Test rows: `22,882,887`

Forecasting test metrics:

- Accuracy: `0.4361`
- Macro-F1: `0.4312`
- Weighted-F1: `0.4331`
- MCC: `0.1497`
- Balanced accuracy: `0.4321`

Nhận xét: ETH có signal forecasting yếu hơn BTC Stage 3 SGD trước đó. Điều này có giá trị paper vì cho thấy benchmark không chỉ dựa trên một asset dễ hơn.

## Policy tuning và execution

Tuning chỉ dùng validation split.

Validation chọn:

- Naive threshold: `0.6`, validation net PnL `-2160.97`
- Cost-aware threshold: `4.6384324e-05`, validation net PnL `-792.92`
- RSEP-full threshold: `2.3792219e-05`, validation net PnL `-586.09`

Test execution:

| Policy | Trades | Gross PnL | Net PnL | Total cost |
|---|---:|---:|---:|---:|
| Naive tuned | 163,049 | 3,879.60 | -28,716.00 | 32,595.60 |
| Cost-aware tuned | 39,299 | 1,907.66 | -5,950.42 | 7,858.09 |
| RSEP-full tuned | 30,216 | 1,753.09 | -4,288.77 | 6,041.85 |

Bootstrap day-level RSEP vs cost-aware:

- Mean diff: `28.65`
- CI low/high: `[16.48, 43.24]`
- Days: `58`
- Bootstrap samples: `1000`

Nhận xét: RSEP-full giảm số trade và giảm thiệt hại so với cost-aware/naive trên ETH, nhưng net PnL vẫn âm ở fee `1 bps`. Đây là robust selective execution có điều kiện, không phải trading profitability.

## Stress

Stress grid tuned RSEP-full:

- Fee `0 bps`: net PnL `1,753.09`
- Fee `1 bps`: net PnL `-4,288.77`
- Fee `2 bps`: net PnL `-10,330.62`
- Fee `5 bps`: net PnL `-28,456.17`
- Fee `10 bps`: net PnL `-58,665.43`

Latency stress:

- Latency `0`: net PnL `-3,449.48`
- Latency `1`: net PnL `-4,288.77`
- Latency `5`: net PnL `-5,291.37`
- Latency `10`: net PnL `-5,675.82`

Nhận xét: ETH tiếp tục củng cố luận điểm forecast-to-execution degradation. Gross edge tồn tại ở điều kiện fee bằng 0, nhưng bị phí và latency làm sụp nhanh.

## Đánh giá Principal ML Scientist

ETH within-asset pass ở góc benchmark: forecasting không collapse, execution pipeline tái lập được, RSEP giảm thiệt hại có ý nghĩa bootstrap so với cost-aware. Tuy nhiên signal ETH yếu hơn BTC, và net PnL âm cho thấy không nên claim policy improvement theo nghĩa profitability.

## Đánh giá Reviewer ICDM

ETH-2 giúp paper mạnh hơn vì thesis không chỉ là BTC-only. Evidence tốt nhất để đưa vào paper là:

- ETH forecasting yếu hơn BTC nhưng vẫn có signal.
- Forecast-to-execution degradation lặp lại.
- RSEP giảm thiệt hại nhưng không biến benchmark thành profitable trading.

Reviewer vẫn có thể hỏi cross-asset generalization; câu trả lời cần dựa vào audit ETH-3 asset-held-out, không dựa vào ETH within-asset.

## Quyết định

- ETH within-asset SGD: **PASS**
- ETH tuned execution/RSEP: **PASS for failure-analysis + conditional robust execution**
- Claim profitability: **NOT CLAIMED**
- Bước tiếp theo: dùng asset-held-out BTC↔ETH để cập nhật claim matrix cross-asset.

