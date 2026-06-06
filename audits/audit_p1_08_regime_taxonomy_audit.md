# Audit P1-08 - Microstructure regime taxonomy

## Run ID

`p1_08_regime_taxonomy_audit_v001`

## Mục tiêu

Khóa regime taxonomy ở dạng reviewer-facing: input causal, threshold source, coverage theo asset/split, tỷ lệ `UNKNOWN`, và sensitivity dưới các quantile settings khác. Audit này không rebuild feature/regime/model; chỉ đọc prediction artifacts Stage 3 đã khóa.

## Cấu hình chính

- BTC source: `data/predictions/predictions.parquet`
- ETH source: `data/predictions/predictions_eth_stage3_sgd.parquet`
- BTC thresholds: `data/regimes/regime_thresholds.json`
- ETH thresholds: `data/regimes/regime_thresholds_eth_stage3.json`
- Threshold source: first 60% chronological train prefix.
- Sensitivity sample: `1,000,000` rows per asset, seed `7`.
- Sensitivity settings:
  - baseline: `low=0.40`, `high=0.70`, `very_low=0.10`, `very_high=0.80`
  - strict_extremes: `low=0.45`, `high=0.75`, `very_low=0.05`, `very_high=0.85`
  - relaxed_extremes: `low=0.35`, `high=0.65`, `very_low=0.15`, `very_high=0.75`

## Artifact sinh ra

- `artifacts/regime_audit.csv`
- `artifacts/regime_counts_by_split.csv`
- `outputs/paper_assets/table_23_regime_taxonomy_inputs.csv`
- `outputs/paper_assets/table_24_regime_counts_by_asset_split.csv`
- `outputs/paper_assets/table_25_regime_sensitivity.csv`
- `docs/regime_taxonomy_spec.md`

## Kết quả chính

| Asset | Rows | UNKNOWN share | Daily UNKNOWN p90 | Status |
|---|---:|---:|---:|---|
| BTC-USDT | 167,751,306 | 13.19% | 15.42% | PASS |
| ETH-USDT | 114,414,433 | 12.68% | 15.59% | PASS |

Sensitivity trên sample 1M rows/asset:

| Asset | Setting | UNKNOWN share | Agreement vs baseline |
|---|---|---:|---:|
| BTC-USDT | strict_extremes | 16.27% | 86.48% |
| BTC-USDT | relaxed_extremes | 10.57% | 86.85% |
| ETH-USDT | strict_extremes | 15.78% | 85.75% |
| ETH-USDT | relaxed_extremes | 10.18% | 86.31% |

## Vấn đề phát hiện

- Taxonomy sensitivity không nhỏ: strict/relaxed quantiles thay đổi `UNKNOWN` khoảng 5-6 điểm phần trăm và agreement với baseline khoảng 86%.
- Đây không phải lỗi nếu paper trình bày taxonomy là diagnostic grouping, không phải latent-state discovery.
- Một số regime hiếm như `VOLATILE_LIQUID` có support rất thấp, nên không nên dùng làm claim chính.

## Đánh giá Principal ML Scientist

Taxonomy đủ dùng cho regime-aware benchmark vì input causal, threshold train-prefix, `UNKNOWN` được giữ lại và coverage được báo theo asset/split. Sensitivity cho thấy taxonomy có cấu trúc nhưng vẫn phụ thuộc threshold, nên cần tránh claim trạng thái thị trường “thật”.

## Đánh giá Reviewer ICDM

Audit này xử lý rủi ro reviewer cho rằng taxonomy tùy tiện: có spec, threshold artifacts, counts by split, UNKNOWN share, và sensitivity table. Wording trong paper phải giữ “diagnostic regimes, not true latent states”.

## Quyết định

PASS cho paper readiness. Không chỉnh taxonomy ad hoc. Nếu reviewer yêu cầu mạnh hơn, bước tiếp theo là appendix về residual clustering/sensitivity, không retune theo test.
