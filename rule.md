# Rule cho các lần làm việc sau

File này là nguồn thông tin nhanh cần đọc đầu tiên khi quay lại viết, sửa hoặc kiểm tra paper ICDM 2026.

## 1. Vị trí paper hiện tại

Paper hiện nằm trong:

```text
CryptoRegimeShift\Paper_ICDM_2026
```

Các file chính trong thư mục paper:

- `main.tex`: file LaTeX chính của paper.
- `main.pdf`: bản PDF đã build gần nhất.
- `custom.bib`: bibliography.
- `IEEEtran.cls`: class IEEE đang dùng.
- `fig_6_worst_regime.png`, `fig_7_model_fee_stress.png`, `fig_8_model_latency_stress.png`: figure đang được copy vào paper folder.
- `audit_report.md`: audit/check notes của bản paper hiện tại.
- `latex_patch.diff`: patch hoặc diff LaTeX gần nhất nếu cần rà lại thay đổi.

## 2. Công cụ build PDF

Dùng Tectonic local tại:

```text
CryptoRegimeShift\tectonic.exe
```

Command mặc định để kiểm tra build PDF:

```powershell
cd CryptoRegimeShift\Paper_ICDM_2026
..\tectonic.exe main.tex
```

Mục tiêu build:

- kiểm tra LaTeX compile được;
- kiểm tra PDF sinh ra thành công;
- kiểm tra format theo hướng ICDM Applied Track 2026;
- không dùng build PDF để claim kết quả khoa học mới.

## 3. Thứ tự đọc context trước khi sửa paper

Trước khi sửa `main.tex`, đọc theo thứ tự:

1. `CryptoRegimeShift\AGENTS.md`
2. `CryptoRegimeShift\rule.md`
3. `CryptoRegimeShift\guideline.md`
4. `CryptoRegimeShift\outputs\paper_assets\ieee_draft_skeleton_stage3_14_vi.md`
5. `CryptoRegimeShift\outputs\paper_assets\table_13_claim_to_evidence_map.csv`
6. `CryptoRegimeShift\outputs\paper_assets\table_14_number_consistency_check.csv`
7. `CryptoRegimeShift\audits\audit_stage3_15_dataset_stats_btc_eth_lock_v001.md`

Nếu chỉ cần sửa wording paper, ưu tiên đọc `guideline.md` và `ieee_draft_skeleton_stage3_14_vi.md`.

Nếu cần sửa số liệu, luôn đối chiếu với `table_14_number_consistency_check.csv` và các bảng trong `outputs\paper_assets`.

## 4. Nguồn số liệu dataset đã khóa

Dataset stats BTC/ETH đã khóa tại:

```text
CryptoRegimeShift\outputs\paper_assets\table_1_dataset_stats.csv
CryptoRegimeShift\outputs\paper_assets\table_1b_eth_dataset_stats.csv
```

Số chính:

- BTC-USDT: `167,753,156` audit snapshots, `366` ngày, median interval `100.000256 ms`.
- ETH-USDT: `114,416,283` audit snapshots, `366` ngày, median interval `200.0 ms`.

Không để placeholder cần kiểm chứng cho ETH dataset stats trong Section 3.

## 5. Claim boundary bắt buộc

Được viết:

- benchmark/evaluation protocol cho L2 order book;
- regime-aware forecasting và execution evaluation;
- forecast-to-execution degradation;
- stress sensitivity;
- BTC<->ETH cross-asset evaluation;
- RSEP giảm thiệt hại trong một số setting.

Không được viết:

- paper là trading bot;
- hệ thống tạo lợi nhuận giao dịch;
- model hoặc RSEP luôn thắng;
- hệ thống sẵn sàng giao dịch live;
- exact queue priority hoặc L3/MBO realism;
- policy phổ quát cho mọi asset.

## 6. Quy tắc khi sửa paper

- Sửa trực tiếp trong `CryptoRegimeShift\Paper_ICDM_2026\main.tex`.
- Không sửa số liệu nếu chưa đối chiếu paper assets canonical.
- Không thêm claim mới nếu không có evidence path.
- Sau khi sửa LaTeX, build lại bằng `..\tectonic.exe main.tex`.
- Nếu build lỗi, sửa LaTeX trước; không thay đổi kết quả thí nghiệm để làm paper compile.
- Nếu thay đổi narrative quan trọng, cập nhật audit hoặc note tương ứng.

## 7. Checklist trước khi kết thúc một lượt sửa paper

Chạy build:

```powershell
cd CryptoRegimeShift\Paper_ICDM_2026
..\tectonic.exe main.tex
```

Kiểm tra:

- `main.pdf` được cập nhật.
- Không còn placeholder cần kiểm chứng cho số BTC/ETH đã khóa.
- Không có claim profitability/live trading/exact queue priority.
- Bảng và figure được gọi đúng file đang có trong `Paper_ICDM_2026`.
- Nếu có số mới trong paper, số đó phải có nguồn trong `outputs\paper_assets` hoặc audit tương ứng.
