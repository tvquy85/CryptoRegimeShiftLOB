# Audit Stage ETH-1: Artifact isolation, data audit, feature/regime readiness

## Run context

- `run_id` audit dữ liệu: `stage_eth_audit_full2024_v001`
- `run_id` feature/label: `stage_eth_features_full2024_v001`
- `run_id` regime: `stage_eth_regimes_full2024_v001`
- `run_id` split: `stage_eth_splits_full2024_v001`
- Stage: `stage_3_full_scale`
- Symbol: `ETH-USDT`
- Config chính: `CryptoRegimeShift/configs/experiments_stage3_eth.yaml`
- Artifact namespace: `eth_usdt_stage3`

## Mục tiêu

Mục tiêu của Stage ETH-1 là mở khóa nhánh ETH mà không ghi đè artifact BTC Stage 3. Bước này chỉ kiểm tra readiness dữ liệu, feature, regime taxonomy và split. Chưa chạy forecasting, execution, RSEP hay asset-held-out.

## Artifact isolation

Các output ETH đã được tách khỏi artifact BTC:

- Feature: `CryptoRegimeShift/data/features/features_eth_stage3.parquet`
- Label: `CryptoRegimeShift/data/labels/labels_eth_stage3.parquet`
- Regime: `CryptoRegimeShift/data/regimes/regimes_eth_stage3.parquet`
- Split: `CryptoRegimeShift/data/splits/splits_eth_stage3.parquet`
- Feature parts: `CryptoRegimeShift/data/interim/feature_parts/eth_usdt_stage3/`
- Regime parts: `CryptoRegimeShift/data/interim/regime_parts/eth_usdt_stage3/`
- Data audit table: `CryptoRegimeShift/outputs/tables/table_data_audit_stage3_eth_usdt.csv`
- Regime tables/figures: `*_stage3_eth_usdt.*`

Kết luận: namespace hoạt động đúng cho audit, feature parts, regime parts, regime diagnostics và split manifest. Không ghi đè các artifact BTC generic như `predictions.parquet`.

## Data audit

ETH-USDT full-year 2024 đã có đủ 12 parquet trong `data/full2024`.

Kết quả audit:

- Số ngày: `366`
- Snapshot trong phạm vi stage: `114,416,283`
- Crossed book rows: `0`
- Zero/negative price rows: `0`
- Zero/negative size rows: `0`
- Median snapshot interval trung bình theo ngày: khoảng `205.84 ms`
- Median spread theo ngày: khoảng `0.01001`
- Depth top-10 mean trung bình theo ngày: khoảng `105.16`

Chênh lệch nhỏ giữa tổng row parquet ETH sau conversion và audit stage là do filter theo range của `stage_3_full_scale`; audit chỉ tính snapshot nằm trong phạm vi stage.

## Feature/label readiness

Feature build chạy partition 10 ngày, tổng cộng `37` partitions.

Kết quả:

- Feature rows: `114,414,433`
- Label rows: `114,414,433`
- Feature parquet size: khoảng `26.76 GB`
- Label parquet size: khoảng `26.77 GB`
- Không còn file `.tmp` ETH sau khi merge.

Số row feature/label thấp hơn audit do label horizon/drop cuối chuỗi, phù hợp với pipeline hiện tại.

## Regime readiness

Regime labeling chạy thành công trên toàn bộ feature/label ETH.

Kết quả:

- Regime rows: `114,414,433`
- Regime parquet size: khoảng `28.75 GB`
- `UNKNOWN overall`: `12.68%`
- p90 daily `UNKNOWN`: `15.59%`
- Gate taxonomy: **PASS** vì `UNKNOWN < 15%` và p90 daily `< 25%`.

Regime share chính:

- `BALANCED_TRANSITION`: `19.92%`
- `MOMENTUM_TOXIC`: `16.96%`
- `MILD_LIQUIDITY_STRESS`: `14.33%`
- `CHOPPY_MEAN_REVERTING`: `12.74%`
- `UNKNOWN`: `12.68%`
- `SHOCK_RECOVERY`: `8.82%`
- `CALM_ILLIQUID`: `4.89%`
- `CALM_LIQUID`: `3.97%`
- `VOLATILE_ILLIQUID`: `2.72%`
- `LIQUIDITY_DROUGHT`: `2.47%`
- `VOLATILE_LIQUID`: `0.49%`

Nhận xét: taxonomy refined không chỉ pass trên BTC mà còn có coverage hợp lý trên ETH. Hai residual states có support đủ lớn để phục vụ phân tích cross-asset, nhưng cần so sánh feature medians BTC vs ETH trước khi claim generalization.

## Split readiness

Chronological split ETH đã hoàn tất:

- Train: `68,648,659`
- Valid: `22,882,887`
- Test: `22,882,887`
- Tỷ lệ xấp xỉ: `60/20/20`

Split artifact: `CryptoRegimeShift/data/splits/splits_eth_stage3.parquet`.

## Resource và disk status

Sau khi hoàn tất ETH feature/regime/split, dung lượng D còn khoảng `13.01 GB`.

Intermediate parts đang chiếm:

- Feature parts ETH: khoảng `47.51 GB`
- Regime parts ETH: khoảng `25.26 GB`

Do đó, chưa nên mở ETH SGD/XGBoost/asset-held-out nếu chưa giải phóng dung lượng. Các parts này là artifact trung gian sau khi final parquet đã được merge thành công; tuy nhiên chưa xóa tự động vì đây là thao tác destructive và cần quyết định rõ.

## Đánh giá Principal ML Scientist

Stage ETH-1 đạt mục tiêu readiness: dữ liệu sạch, feature/label/regime/split chạy được ở full-year scale và taxonomy refined giữ được UNKNOWN dưới gate. Đây là bằng chứng quan trọng để chuyển từ BTC-only sang ETH replication và asset-held-out.

Điểm cần kiểm soát tiếp theo là artifact footprint. Nếu giữ cả final parquet và partition parts, pipeline ETH baseline sẽ bị disk-bound trước khi training-bound.

## Đánh giá Reviewer ICDM

ETH readiness làm giảm rủi ro lớn nhất của paper: claim chỉ dựa trên một asset. Tuy nhiên hiện mới là readiness, chưa phải evidence cross-asset. Paper chỉ được nâng claim từ BTC-only sau khi có:

- ETH within-asset forecasting/execution.
- BTC -> ETH và ETH -> BTC asset-held-out.
- So sánh regime distribution và forecast-to-execution degradation giữa hai asset.

Không được claim cross-asset generalization ở thời điểm ETH-1.

## Quyết định

- Data audit: **PASS**
- Feature/label readiness: **PASS**
- Regime taxonomy gate: **PASS**
- Split readiness: **PASS**
- ETH baseline readiness: **BLOCKED BY DISK** cho đến khi giải phóng dung lượng hoặc xác nhận dọn intermediate parts.

## Bước tiếp theo

1. Nếu được phép dọn artifact trung gian, xóa hoặc archive:
   - `CryptoRegimeShift/data/interim/feature_parts/eth_usdt_stage3/`
   - `CryptoRegimeShift/data/interim/regime_parts/eth_usdt_stage3/`
2. Chạy ETH within-asset SGD bằng `configs/models_stage3_eth_sgd.yaml`.
3. Sau ETH SGD pass, chạy tuned execution/RSEP/stress cho ETH.
4. Sau đó mới mở asset-held-out BTC↔ETH.

