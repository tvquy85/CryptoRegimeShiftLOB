# Audit stage 0 - sanity check

## Kết quả đạt được

- Đường chạy `audit -> feature/label -> regime -> split -> forecast -> backtest -> RSEP -> stress -> report` đã chạy thành công trên BTC-USDT ngày `2024-01-06 00:00:00Z` đến `2024-01-06 06:00:00Z`.
- Audit đọc được `45,769` snapshot; feature/label pipeline giữ lại `45,719` dòng hợp lệ sau loại đuôi không đủ future horizon.
- Split chronological sinh `27,431` train, `9,144` valid và `9,144` test.
- Baseline `SGD log-loss` đạt trên test:
  - accuracy `0.662`
  - macro-F1 `0.635`
  - MCC `0.485`
- Forecast-to-execution cho thấy gross PnL dương nhưng net PnL âm sau phí:
  - naive threshold: gross `108.01`, net `-157.14`
  - cost-aware threshold: gross `66.82`, net `-122.96`
- RSEP-full giảm turnover mạnh và ít lỗ hơn baseline threshold:
  - `171` trades
  - net PnL `-29.18`
  - tốt hơn cost-aware threshold khoảng `93.78` PnL trên lát cắt stage 0.
- Stress grid fee/latency/spread/depth đã sinh đủ bảng và hình trong `outputs/tables` cùng `outputs/paper_assets`.

## Đóng góp cho paper

- Xác nhận cơ chế trung tâm của paper đã quan sát được ngay ở sanity scale: forecasting khá nhưng edge bị bào mòn mạnh khi đưa qua execution cost.
- Xác nhận RSEP có hành vi đúng hướng về mặt phương pháp luận: giao dịch chọn lọc hơn, giảm thiệt hại net PnL và giữ logic stress-compatible.
- Chứng minh toàn bộ evidence pack có thể được sinh tự động, là tiền đề cho reproducibility khi mở rộng sang stage 1-3.

## Điểm còn yếu theo chuẩn ICDM 2026

- Stage 0 chỉ gồm 6 giờ trong một ngày; mọi con số hiện tại chỉ có giá trị sanity, chưa dùng để claim khoa học.
- Bootstrap day-level có đúng 1 ngày nên khoảng tin cậy suy biến, chưa đủ giá trị thống kê.
- Chưa có ETH-USDT nên chưa thể kiểm tra asset-held-out và generalization across assets.
- Chưa chạy walk-forward, regime-held-out full protocol, deep baselines, hay 3 seeds.

## Nguyên nhân và rủi ro

- Kích thước stage nhỏ là chủ đích để kiểm tra correctness trước khi scale.
- Hiệu năng net PnL âm ở stage 0 chưa phải thất bại phương pháp; ngược lại đây là tín hiệu hợp với thesis forecast-to-execution degradation, nhưng vẫn phải xác nhận trên thang lớn.
- Nếu RSEP chỉ tốt trên một lát cắt hẹp mà không giữ lợi thế ở stage 1-3, claim policy improvement phải giảm mức hoặc reposition thành benchmark/failure-analysis.

## Việc cần cải tiến tiếp theo

- Chạy `stage_1_small_scale` trên BTC tháng 1-2 để có nhiều ngày cho bootstrap, regime diversity và stress curves có ý nghĩa hơn.
- Kiểm tra lại quantile regime thresholds, phân bố label và bảng by-regime để chắc chắn chưa xuất hiện skew/bias bất thường.
- Khi dữ liệu ETH có mặt, chạy lại cùng pipeline và mở asset-held-out manifest thành thực nghiệm thật.
- Sau stage 1 pass gate, mới mở TCN/DeepLOB-lite và full ablation mạnh hơn.
