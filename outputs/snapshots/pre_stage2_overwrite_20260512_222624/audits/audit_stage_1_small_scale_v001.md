# Audit stage 1 - BTC Jan-Feb 2024

## Kết luận gate

- **Pipeline kỹ thuật: PASS.**
- **Gate khoa học để mở `stage_2_medium_scale`: CHƯA PASS.**
- Lý do chính: kết quả đã củng cố thesis forecast-to-execution degradation và cho thấy RSEP giảm lỗ rõ so với threshold baselines, nhưng taxonomy regime hiện chưa đủ mạnh để nâng cấp claim paper vì:
  - `UNKNOWN` chiếm `50.37%` toàn bộ Jan-Feb.
  - Một số regime trọng tâm quá hiếm: `VOLATILE_LIQUID 0.21%`, `VOLATILE_ILLIQUID 1.36%`, `LIQUIDITY_DROUGHT 1.66%`.
  - Reviewer có thể kết luận regime taxonomy đang thiếu coverage hoặc threshold rule quá bảo thủ.

## Kết quả đạt được

- Đã chạy end-to-end `stage_1_small_scale` trên `BTC-USDT` từ `2024-01-01` đến `2024-02-29`.
- Audit dữ liệu:
  - `13,235,742` snapshot raw trên `60` ngày.
  - `13,235,692` dòng đi tiếp vào feature/label sau khi loại phần đuôi thiếu future horizon.
  - `0` crossed book row, `0` non-monotonic sequence, `0` duplicate timestamp trong audit tổng hợp.
  - Snapshot interval trung bình theo median ngày khoảng `400.15 ms`; p95 ngày trung bình khoảng `1955.93 ms`.
  - Spread mean theo ngày khoảng `0.0362`; depth top-10 mean theo ngày khoảng `11.60`.
- Split chronological:
  - train `7,941,415` rows, `47` ngày;
  - valid `2,647,138` rows, `8` ngày;
  - test `2,647,139` rows, `7` ngày.
- Label base ở `fee_bps = 1`:
  - `DOWN 26.26%`
  - `FLAT 47.04%`
  - `UP 26.70%`
- Label sensitivity theo fee:
  - `0 bps`: FLAT `23.47%`
  - `1 bps`: FLAT `47.04%`
  - `2 bps`: FLAT `65.78%`
  - `5 bps`: FLAT `89.45%`
- Forecast baseline `SGD log-loss` trên test:
  - accuracy `0.594`
  - macro-F1 `0.498`
  - MCC `0.303`
  - balanced accuracy `0.495`
- Forecast theo regime có độ chênh đáng kể:
  - macro-F1 thấp ở `CHOPPY_MEAN_REVERTING` (`0.333`) và `VOLATILE_ILLIQUID` (`0.373`);
  - cao hơn ở `SHOCK_RECOVERY` (`0.503`) và `MOMENTUM_TOXIC` (`0.495`).
- Forecast-to-execution:
  - naive threshold: gross `1938.03`, net `-6141.39`
  - cost-aware threshold: gross `1900.38`, net `-3515.36`
  - cost-aware giảm lỗ rõ, nhưng vẫn không sống sót sau cost.
- RSEP:
  - `RSEP-full`: `765` trades, gross `76.78`, net `-76.19`
  - Bootstrap day-level so với cost-aware threshold:
    - mean daily diff `+491.31`
    - 95% CI `[+214.65, +794.02]`
  - Test window có `7` ngày trade cho cả cost-aware và RSEP, nên bootstrap không còn suy biến như stage 0.
- Stress:
  - fee tăng từ `0` lên `10 bps` kéo net PnL RSEP từ `+76.78` xuống `-1452.98`.
  - latency `0 -> 10 events` kéo net PnL từ `-52.95` xuống `-123.07`.
  - spread/depth shock cũng làm xấu dần net PnL.

## Đóng góp cho paper

### Góc nhìn Principal ML Scientist

- Thesis trung tâm được hỗ trợ tốt hơn stage 0:
  - forecast có vẻ “ổn” ở metric classification nhưng bị execution cost làm gãy nghiêm trọng;
  - gating theo cost/risk của RSEP làm giảm overtrading và giảm thiệt hại net PnL.
- Việc sửa `adverse_selection_score` sang proxy trailing causal đã loại một nguy cơ leakage đáng kể trước khi đưa kết quả vào luận điểm khoa học.
- Label sensitivity theo fee cho thấy protocol cost-aware có tác động rõ, phù hợp với framing benchmark execution stress.

### Góc nhìn Reviewer ICDM

- Điểm mạnh:
  - Protocol đã tạo được evidence pack đủ dày hơn stage 0.
  - Degradation gross-to-net và stress response rất rõ.
  - Bootstrap nhiều ngày đã có giá trị hơn sanity stage.
- Điểm chưa đủ:
  - Regime taxonomy chưa đủ coverage để reviewer tin rằng “regime-aware benchmark” đã mature.
  - Một số regime quan trọng quá hiếm, khiến so sánh worst-regime hoặc regime-held-out về sau dễ bị chất vấn.
  - Deep baselines chưa chạy, nên claim hiện mới dừng ở tabular baseline + robust policy analysis.

## Đánh giá gate chi tiết

- **Pass**
  - End-to-end pipeline hoàn chỉnh.
  - Artifact và report pack sinh đủ.
  - Label phân bố hợp lý ở fee mặc định `1 bps`.
  - Bootstrap không còn suy biến.
  - Forecast-to-execution degradation và stress sensitivity thể hiện nhất quán.
  - RSEP-full tốt hơn cost-aware threshold về net loss với CI dương trên 7 ngày test.
- **Chưa pass**
  - Taxonomy regime lệch mạnh về `UNKNOWN`.
  - Rare regimes làm yếu giá trị của worst-regime evaluation.
  - Feature engineering pandas còn chậm và phát cảnh báo fragmentation, chưa phù hợp để đẩy thẳng sang stage 2 sáu tháng mà không tối ưu.

## Tác động tới claim paper

- **Được phép giữ**
  - Forecast-to-execution degradation là failure mode thực nghiệm có tín hiệu mạnh.
  - Stress execution làm edge suy giảm có hệ thống.
  - RSEP có tín hiệu giảm thiệt hại so với threshold baselines trên stage 1.
- **Chưa nên claim mạnh**
  - Robust regime-aware policy đã được chứng minh đầy đủ.
  - Worst-regime stability đã đủ chuẩn paper.
  - Taxonomy regime hiện tại đã đại diện tốt cho landscape microstructure.

## Việc cần làm tiếp theo trước stage 2

1. **Refine regime taxonomy**
   - Giảm tỷ trọng `UNKNOWN`.
   - Điều chỉnh rule thresholds hoặc thêm nhánh fallback có kiểm soát.
   - Kiểm tra lại phân bố theo tháng/ngày và regime overlap.
   - Nếu rule-based vẫn thiếu coverage, triển khai clustering regime labeler làm diagnostic đối chứng.
2. **Tối ưu feature pipeline**
   - Loại pandas fragmentation bằng cách gom cột trước khi concat.
   - Giảm thời gian stage 1/stage 2 và hạ rủi ro RAM.
3. **Giữ quy tắc GPU đúng chỗ**
   - Stage 1 tabular + ETL/simulator chủ yếu CPU-bound.
   - Khi taxonomy ổn, mở XGBoost GPU hoặc TCN/DeepLOB-lite và tận dụng RTX 3090 thực sự.
4. **Chỉ mở `stage_2_medium_scale` sau khi regime audit tốt hơn**
   - Đây là điểm chặn methodology, không phải compute.

## Artifact chính

- `outputs/tables/table_forecasting_overall.csv`
- `outputs/tables/table_forecasting_by_regime.csv`
- `outputs/tables/table_forecast_to_execution.csv`
- `outputs/tables/table_robust_policy.csv`
- `outputs/tables/table_rsep_bootstrap_vs_cost_aware.csv`
- `outputs/tables/table_label_fee_sensitivity_stage1.csv`
- `outputs/tables/table_regime_share_stage1.csv`
- `outputs/paper_assets/*`
