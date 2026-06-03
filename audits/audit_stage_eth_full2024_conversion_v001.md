# Audit convert ETH CSV sang parquet full2024

- `run_id`: `stage_eth_convert_full2024_v001`
- Mục tiêu: chuyển CSV ETH-USDT 2024 sang raw parquet tương thích `data/full2024` để mở khóa asset-held-out.
- Engine yêu cầu: `pyarrow`
- Workers: `2`
- Max rows: `None`
- Quyết định: `PASS`

## Tóm tắt

- Số tháng xử lý: `12`
- Converted: `12`
- Skipped existing: `0`
- Failed: `0`
- Tổng rows converted: `114416570`
- Tổng output size MB: `15543.3747`

## Kết quả theo tháng

| Month | Status | Rows | Engine | Duration sec | MB/s | Checks | Error |
|---|---:|---:|---|---:|---:|---|---|
| `JAN` | `converted` | `5479426` | `pyarrow` | `13.3433` | `265.1714` | `PASS,PASS,PASS,PASS,PASS` | `` |
| `FEB` | `converted` | `6821821` | `pyarrow` | `16.4332` | `268.5084` | `PASS,PASS,PASS,PASS,PASS` | `` |
| `MAR` | `converted` | `9838667` | `pyarrow` | `24.2913` | `259.0235` | `PASS,PASS,PASS,PASS,PASS` | `` |
| `APR` | `converted` | `8296326` | `pyarrow` | `19.7823` | `266.7372` | `PASS,PASS,PASS,PASS,PASS` | `` |
| `MAY` | `converted` | `8214725` | `pyarrow` | `19.5685` | `265.9788` | `PASS,PASS,PASS,PASS,PASS` | `` |
| `JUN` | `converted` | `8068908` | `pyarrow` | `19.3456` | `263.8503` | `PASS,PASS,PASS,PASS,PASS` | `` |
| `JUL` | `converted` | `8484283` | `pyarrow` | `21.7859` | `249.25` | `PASS,PASS,PASS,PASS,PASS` | `` |
| `AUG` | `converted` | `9887336` | `pyarrow` | `25.9868` | `243.7695` | `PASS,PASS,PASS,PASS,PASS` | `` |
| `SEP` | `converted` | `12372937` | `pyarrow` | `27.585` | `287.4801` | `PASS,PASS,PASS,PASS,PASS` | `` |
| `OCT` | `converted` | `12445316` | `pyarrow` | `28.0144` | `284.6015` | `PASS,PASS,PASS,PASS,PASS` | `` |
| `NOV` | `converted` | `12315143` | `pyarrow` | `29.5242` | `267.3028` | `PASS,PASS,PASS,PASS,PASS` | `` |
| `DEC` | `converted` | `12191682` | `pyarrow` | `27.6063` | `283.0347` | `PASS,PASS,PASS,PASS,PASS` | `` |

## Đánh giá ICDM/reproducibility

- Converter không thay đổi BTC parquet hiện có.
- Output giữ schema raw snapshot-level L2, chưa build feature/label/regime ETH trong bước này.
- GPU không dùng ở bước này vì conversion CSV -> Parquet là CPU/disk-bound trên Windows; RTX 3090 dành cho model training/inference sau khi ETH parquet sẵn sàng.

## Bước tiếp theo

- Nếu `PASS`: chạy audit dữ liệu ETH ở stage nhỏ trước khi mở feature/label/regime full-year.
- Nếu `FAIL`: sửa lỗi schema/data theo tháng thất bại, không mở asset-held-out cho tới khi đủ 12 parquet hợp lệ.
