# Stage 3.13 - Cross-asset evidence lock

## Kết luận ngắn

BTC<->ETH đã được đánh giá ở cả forecasting và execution/RSEP với tuning chỉ trên source validation. Điểm đọc đúng là cross-asset evaluation + failure-analysis: RSEP giảm thiệt hại so với cost-aware, nhưng net PnL vẫn âm nên không được claim profitability hoặc universal policy generalization.

## Acceptance bar sau khi thêm cross-asset execution

- PASS: `7`
- PARTIAL: `2`
- BLOCKED: `0`
- FAIL: `0`
- Cross-asset claim status: `SUPPORTED`

## Kết quả BTC<->ETH

### `btc_to_eth`

- Forecasting: accuracy `0.4341`, macro-F1 `0.4325`, MCC `0.1486` trên `22,882,887` target rows.
- RSEP-full: gross PnL `25,679.52`, net PnL `-74,466.38`, trades `500,819`.
- Cost-aware net PnL `-287,991.44`; naive net PnL `-233,008.45`.
- RSEP giảm thiệt hại so với cost-aware `213,525.07`.
- Bootstrap RSEP minus cost-aware: mean diff `3,681.47`, CI [`3,314.02`, `4,048.20`], `58` ngày, `1000` bootstrap.

### `eth_to_btc`

- Forecasting: accuracy `0.5394`, macro-F1 `0.4839`, MCC `0.2424` trên `33,550,262` target rows.
- RSEP-full: gross PnL `677.22`, net PnL `-1,144.75`, trades `9,129`.
- Cost-aware net PnL `-3,697.46`; naive net PnL `-8,215.68`.
- RSEP giảm thiệt hại so với cost-aware `2,552.71`.
- Bootstrap RSEP minus cost-aware: mean diff `39.27`, CI [`34.08`, `44.53`], `65` ngày, `1000` bootstrap.

## Paper wording

- Được nói: BTC<->ETH cross-asset forecasting and execution were evaluated under source-validation-only tuning.
- Được nói: RSEP reduces losses versus cost-aware in asset-held-out execution.
- Không được nói: giao dịch cross-asset tạo lợi nhuận, policy phổ quát qua mọi asset, hoặc hệ thống sẵn sàng giao dịch live.

## Reviewer-facing interpretation

Cross-asset evidence bây giờ không còn bị chặn bởi thiếu ETH. Tuy nhiên kết quả không biến paper thành trading-profit paper. Giá trị khoa học nằm ở việc cho thấy forecast generalization vẫn phải đi qua execution stress, và selective execution có thể giảm thiệt hại nhưng không tự động tạo net profitability.
