# Audit Stage ETH-3: Asset-held-out BTC↔ETH SGD

## Run context

- BTC -> ETH run_id: `stage_eth_asset_btc_to_eth_sgd_v001`
- ETH -> BTC run_id: `stage_eth_asset_eth_to_btc_sgd_v001`
- Stage: `stage_3_full_scale`
- Model family: streaming SGD
- Output table: `CryptoRegimeShift/outputs/tables/table_asset_heldout_forecasting_stage3.csv`
- By-regime table: `CryptoRegimeShift/outputs/tables/table_asset_heldout_forecasting_by_regime_stage3.csv`

## Mục tiêu

Mục tiêu là kiểm tra generalization qua asset ở mức forecasting, không dùng target test để train hoặc tune. Đây là bước đầu để nâng claim từ BTC-only sang cross-asset evidence. Execution/RSEP cross-asset chưa chạy trong audit này.

## Thiết kế

Hai hướng đánh giá:

1. `BTC-USDT` train/valid -> `ETH-USDT` test.
2. `ETH-USDT` train/valid -> `BTC-USDT` test.

Script mới:

- `CryptoRegimeShift/scripts/18_train_asset_heldout_sgd.py`

Nguyên tắc:

- Train streaming SGD chỉ đọc source `split == train`.
- Target chỉ dùng `split == test` để báo cáo.
- BTC source/target dùng fallback `data/predictions/predictions.parquet` vì `splits.parquet` generic không còn.
- ETH source/target dùng `data/splits/splits_eth_stage3.parquet` khi có sẵn.
- Không tạo combined BTC+ETH parquet lớn.

## Kết quả chính

| Direction | Target rows | Accuracy | Macro-F1 | MCC | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| BTC -> ETH | 22,882,887 | 0.4341 | 0.4325 | 0.1486 | 0.4326 |
| ETH -> BTC | 33,550,262 | 0.5394 | 0.4839 | 0.2424 | 0.4835 |

Prediction artifacts:

- `CryptoRegimeShift/data/predictions/predictions_asset_btc_to_eth_sgd.parquet`
- `CryptoRegimeShift/data/predictions/predictions_asset_eth_to_btc_sgd.parquet`

## Diễn giải

BTC -> ETH:

- Macro-F1 `0.4325`, rất gần ETH within-asset SGD `0.4312`.
- Đây là evidence tích cực: model học từ BTC vẫn chuyển được một phần signal microstructure sang ETH ở forecasting.
- Tuy nhiên MCC vẫn thấp (`0.1486`), nên không nên claim generalization mạnh.

ETH -> BTC:

- Macro-F1 `0.4839`, cao hơn BTC Stage 3 SGD trước đó theo macro-F1.
- MCC `0.2424`, cùng mức với các tabular baseline BTC đã có.
- Đây là evidence khá mạnh rằng ETH source không chỉ là replication mà có thể học signal dùng được trên BTC test.

By-regime:

- Hai hướng đều có kết quả theo đầy đủ regime chính.
- `CHOPPY_MEAN_REVERTING` vẫn là regime khó, đặc biệt trong ETH -> BTC.
- `BALANCED_TRANSITION`, `MILD_LIQUIDITY_STRESS`, `MOMENTUM_TOXIC` có support lớn và hữu ích cho bảng paper.

## Giới hạn

- Đây mới là forecasting asset-held-out, chưa phải execution asset-held-out.
- Không dùng kết quả này để claim cross-asset profitability.
- Vì BTC target dùng prediction artifact làm source dữ liệu feature/split thay vì `splits.parquet`, cần ghi rõ trong reproducibility notes rằng file này chứa đủ feature/label/regime/split và không dùng probability cũ để train.

## Đánh giá Principal ML Scientist

Asset-held-out forecasting có giá trị rõ: cả hai hướng không collapse, và kết quả ETH -> BTC đặc biệt tốt. Điều này làm paper mạnh hơn so với BTC-only. Tuy nhiên để claim robust policy generalization across assets, cần thêm execution/RSEP asset-held-out hoặc giữ claim ở mức forecasting/regime benchmark.

## Đánh giá Reviewer ICDM

Reviewer sẽ đánh giá cao việc có asset-held-out thật thay vì chỉ within-asset split. Evidence hiện tại đủ để đổi ETH/asset-held-out từ `BLOCKED` sang ít nhất `PARTIAL`. Để lên `SUPPORTED` mạnh, cần bổ sung:

- execution degradation asset-held-out;
- RSEP target-asset evaluation với threshold tuned trên source validation;
- so sánh stress sensitivity target asset.

## Quyết định

- Asset-held-out forecasting: **PASS**
- Cross-asset generalization claim: **PARTIAL**, không phải full support.
- Cross-asset execution claim: **NOT YET TESTED**
- Profitability/live trading: **NOT CLAIMED**

## Bước tiếp theo

1. Cập nhật evidence pack/claim matrix: ETH/asset-held-out từ `BLOCKED` sang `PARTIAL`.
2. Nếu cần claim mạnh hơn cho ICDM, chạy execution/RSEP asset-held-out với threshold chỉ tune trên source validation.
3. Sau đó mới cân nhắc ETH XGBoost GPU hoặc TCN nếu muốn strong model baseline cross-asset.

