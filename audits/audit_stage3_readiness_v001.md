# Audit Stage 3 Readiness v001

## Tóm tắt

- Symbol: `BTC-USDT`
- Khoảng thời gian Stage 3: `2024-01-01 00:00:00+00:00` đến `2024-12-31 23:59:59+00:00`
- Số raw file Stage 3: `12`
- Số partition Stage 3: `37` partition, mỗi partition `10` ngày
- Gate dung lượng: **FAIL**

## Ước lượng quy mô

- Stage 2 rows: `69,532,240`
- Stage 3 rows ước lượng: `167,753,156`
- Stage 3 audit rows thực tế: `167,753,156`
- Raw size ratio Stage 3 / Stage 2: `2.31`
- Free disk hiện tại: `37.49 GB`
- Lower-bound dung lượng cần cho core artifacts: `132.21 GB`

## Artifact size estimates

- `predictions`: stage2 `18.34 GB`, ước lượng stage3 `44.24 GB`
- `regimes`: stage2 `16.35 GB`, ước lượng stage3 `39.44 GB`
- `splits`: stage2 `9.15 GB`, ước lượng stage3 `22.08 GB`

## Kết luận

Chưa nên mở Stage 3 feature build. Cần giải phóng hoặc chuyển bớt artifact lớn trước khi build full-year.

Ghi chú: lower-bound trên chưa tính đủ feature/label intermediates và temp parquet merge. Vì vậy nếu gate FAIL ở lower-bound thì Stage 3 full-year chắc chắn rủi ro; nếu gate PASS thì vẫn cần theo dõi disk sau từng bước.

## Bước tiếp theo

- Nếu chưa đủ dung lượng: snapshot các bảng/audit quan trọng, sau đó xóa hoặc di chuyển `predictions.parquet`, `regimes.parquet`, `splits.parquet` và regime parts Stage 2 khi không còn cần rerun trực tiếp.
- Sau khi đủ dung lượng: build features Stage 3 theo partition 10 ngày.
- Không mở XGBoost/TCN Stage 3 trước khi feature/regime/split full-year pass.
