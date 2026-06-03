# Audit Stage 3.13 - Cross-asset paper lock

- `run_id`: `stage3_13_cross_asset_paper_lock_v004`
- Mục tiêu: khóa narrative cross-asset sau khi BTC<->ETH đã có forecasting, execution/RSEP và bootstrap.
- Phạm vi: chỉ đọc artifact hiện có; không train, không inference, không dùng GPU.

## Acceptance impact

- PASS: `7`
- PARTIAL: `2`
- BLOCKED: `0`
- FAIL: `0`
- Cross-asset claim: `SUPPORTED`

## Kết quả chính

- `btc_to_eth`: macro-F1 `0.4325`, MCC `0.1486`, RSEP net `-74,466.38`, cost-aware net `-287,991.44`, bootstrap CI [`3,314.02`, `4,048.20`].
- `eth_to_btc`: macro-F1 `0.4839`, MCC `0.2424`, RSEP net `-1,144.75`, cost-aware net `-3,697.46`, bootstrap CI [`34.08`, `44.53`].

## Principal ML Scientist view

- Cross-asset forecasting không collapse ở cả hai hướng, nhưng execution cho thấy edge vẫn rất mỏng.
- RSEP là evidence giảm thiệt hại có ý nghĩa vì CI RSEP minus cost-aware dương ở cả hai hướng.
- Net PnL âm là negative evidence quan trọng: generalization của forecast không đồng nghĩa với profitable execution.

## Reviewer ICDM view

- Điểm mạnh: claim cross-asset không còn chỉ là future work; đã có target-asset execution và bootstrap.
- Điểm cần hạ giọng: không dùng chữ universal generalization hoặc trading profit.
- Nên đưa bảng cross-asset vào main paper hoặc appendix gần main results để tăng độ tin cậy benchmark.

## Quyết định

- PASS cho Stage 3.13 paper lock.
- Bước tiếp theo nên là viết bản IEEE draft từ paper assets đã khóa, không mở thêm baseline ad hoc trước.
