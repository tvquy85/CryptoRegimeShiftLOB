# Audit Stage 3.5 Reproducibility Hardening v001

## 1. Phạm vi

Stage 3.5 không thay đổi taxonomy, label, simulator core hay kết quả Stage 3. Mục tiêu là hardening reproducibility trước khi mở baseline mạnh hơn.

Các việc đã thực hiện:

- Thêm helper artifact naming theo stage/model.
- Cập nhật scripts tuning, stress, RSEP và report pack để ưu tiên canonical Stage 3 outputs.
- Chặn `RSEP-no-cost-gate` khỏi ablation mặc định; chỉ chạy khi bật explicit opt-in.
- Materialize các CSV canonical Stage 3 từ kết quả đã có, không chạy lại full-year simulation.
- Regenerate report pack bằng `model_label=sgd_stage3`.
- Cập nhật `MoTa.md` để phản ánh Stage 3 đã hoàn tất.

## 2. Artifact naming và reproducibility

Các artifact Stage 3 canonical đã có dạng rõ ràng hơn:

- `table_policy_tuning_stage3.csv`
- `table_forecast_to_execution_tuned_stage3.csv`
- `table_forecast_to_execution_tuned_by_regime_stage3.csv`
- `table_rsep_bootstrap_tuned_stage3.csv`
- `table_model_comparison_stage3.csv`
- `table_stress_grid_tuned_stage3.csv`
- `table_robustness_summary_tuned_stage3.csv`
- `table_robust_policy_stage3.csv`
- `table_rsep_ablation_stage3.csv`
- `table_rsep_by_regime_stage3.csv`
- `table_regime_share_stage3.csv`
- `table_unknown_monthly_share_stage3.csv`

Các legacy files có hậu tố `stage2` vẫn được giữ lại vì chúng là artifact lịch sử/compatibility. Tuy nhiên code mới không ghi thêm `stage2` khi stage hiện tại là `stage_3_full_scale`. Report pack mới ưu tiên canonical stage-specific files.

## 3. Report pack

Report pack đã regenerate với:

- run_id: `stage3_5_report_sgd_hardened_v001`
- stage: `stage_3_full_scale`
- model label: `sgd_stage3`

Paper assets hiện có bảng model comparison stage-neutral:

- `outputs/paper_assets/table_7_model_comparison.csv`

Bảng forecast-to-execution trong report pack hiện chỉ chứa rows của `sgd_stage3`, gồm:

- `sgd_stage3_naive_threshold_tuned`
- `sgd_stage3_cost_aware_threshold_tuned`
- `sgd_stage3_RSEP-full_tuned`

Điều này giảm rủi ro reviewer hiểu nhầm rằng Stage 3 đang dùng bảng Stage 2/2.5.

## 4. RSEP ablation policy

`RSEP-no-cost-gate` không còn nằm trong ablation mặc định. Lý do:

- Ở full-year, biến thể này có xu hướng trade quá dày.
- Runtime và dung lượng trade artifact dễ tăng bất thường.
- Kết quả không còn là diagnostic sạch nếu không có trade cap hoặc sampling rule rõ ràng.

Từ Stage 3.5 trở đi, biến thể này chỉ chạy khi dùng explicit flag/config. Trong paper main table, nên giữ các ablation có ý nghĩa ổn định:

- no latency risk
- no liquidity risk
- no adverse-selection risk
- no regime penalty

Nếu muốn đưa `no-cost-gate` vào appendix, cần định nghĩa diagnostic sampling hoặc trade cap trước.

## 5. Cập nhật MoTa.md

`MoTa.md` đã được sửa để không còn ghi Stage 3 bị chặn bởi disk gate.

Nội dung hiện tại phản ánh:

- Stage 3 full-year BTC đã hoàn tất.
- Taxonomy full-year pass: `UNKNOWN = 13.19%`, daily p90 UNKNOWN khoảng `15.43%`.
- SGD full-year đạt macro-F1 `0.4652`, MCC `0.2363`.
- RSEP tuned giảm thiệt hại nhưng vẫn net âm ở fee `1 bps`.
- Paper tiếp tục được định vị là benchmark/failure-analysis + robust selective execution, không claim profitability.

## 6. Kiểm thử

Đã chạy:

- `python -m compileall CryptoRegimeShift\src CryptoRegimeShift\scripts CryptoRegimeShift\tests`
- `pytest CryptoRegimeShift\tests`

Kết quả:

- Compile pass.
- Pytest pass: `24 passed`.

Tests mới bao phủ:

- Stage artifact naming helper.
- Report pack ưu tiên stage-specific tables thay vì legacy `stage2`.
- `RSEP-no-cost-gate` là explicit opt-in, không nằm trong default variants.

## 7. Góc nhìn Principal ML Scientist

Điểm mạnh:

- Stage 3 result now có đường artifact rõ hơn, giảm rủi ro lẫn kết quả giữa Stage 2, Stage 2.5 và Stage 3.
- RSEP ablation được làm kỷ luật hơn; biến thể pathological không còn làm nhiễu main protocol.
- Report pack hiện phản ánh đúng model `sgd_stage3`, phù hợp hơn cho paper narrative.

Điểm còn yếu:

- Canonical Stage 3 CSV lần này được materialize từ kết quả đã chạy, chưa phải do toàn bộ scripts mới chạy lại end-to-end.
- Legacy files vẫn tồn tại để giữ compatibility; trước release public có thể cần thư mục `archive/legacy_stage2` hoặc manifest rõ hơn.
- Chưa mở baseline GPU/deep full-year.

## 8. Góc nhìn Reviewer ICDM

Stage 3.5 làm tăng reproducibility và clarity, nhưng chưa tăng empirical strength về model. Reviewer sẽ đánh giá cao việc:

- đặt tên artifact rõ theo stage;
- không claim bằng bảng lẫn stage;
- bỏ biến thể ablation không ổn định khỏi main protocol;
- cập nhật narrative để phản ánh kết quả full-year.

Rủi ro còn lại:

- Single-asset BTC vẫn là giới hạn lớn.
- Chưa có DeepLOB/TCN full-year hoặc ít nhất một strong deep baseline trên protocol mới.
- Cần trình bày rõ rằng Stage 3.5 là hardening/reproducibility, không phải stage kết quả khoa học mới.

## 9. Kết luận và bước tiếp theo

Gate Stage 3.5 hardening: pass.

Bước tiếp theo nên là một trong hai nhánh:

- **Stage 3.6 XGBoost GPU full-year:** tận dụng RTX 3090, chạy baseline mạnh hơn nhưng vẫn tabular/kiểm soát compute.
- **Stage 4 asset-held-out ETH:** nếu có ETH data, mở claim generalization across assets.

Không nên mở TCN/DeepLOB-lite trước khi quyết định rõ compute budget và lưu trữ artifact, vì full-year deep baseline có rủi ro tốn thời gian/đĩa cao hơn XGBoost GPU.
