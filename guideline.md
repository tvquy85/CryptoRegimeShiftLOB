# Guideline chuẩn bị GitHub và dùng ChatGPT viết paper

File này là entrypoint cho người chuẩn bị repo GitHub và cho ChatGPT khi viết paper ICDM 2026 của dự án **CryptoRegimeShift-LOB**.

Mục tiêu của file này là trả lời ba câu hỏi:

1. Nên đưa những file nào lên GitHub?
2. ChatGPT cần đọc những file nào, theo thứ tự nào, để có đủ ngữ cảnh viết paper?
3. Claim nào được phép viết và claim nào phải tránh?

Paper hiện nên được định vị là:

> Benchmark/failure-analysis cho L2 microstructure regime shifts, kèm robust selective execution có điều kiện. Đây không phải paper về trading bot hay hệ thống tạo lợi nhuận giao dịch.

## 1. Quick-start cho ChatGPT viết paper

Khi đưa project này vào ChatGPT khác để viết paper, hãy yêu cầu ChatGPT đọc theo thứ tự sau.

### Bước 1: đọc định hướng và boundary

Đọc các file:

- `CryptoRegimeShift/guideline.md`
- `CryptoRegimeShift/AGENTS.md`
- `CryptoRegimeShift/TongQuan.md`
- `CryptoRegimeShift/MoTa.md`
- `CryptoRegimeShift/ThucNghiem.md`

Mục đích:

- hiểu paper muốn chứng minh điều gì;
- hiểu contribution chính/phụ;
- hiểu độ lớn thí nghiệm;
- hiểu những claim không được viết quá mức.

### Bước 2: đọc skeleton paper đã khóa

Đọc file:

- `CryptoRegimeShift/outputs/paper_assets/ieee_draft_skeleton_stage3_14_vi.md`

Đây là khung chính để viết bản IEEE/ICDM. File này đã map từng section của paper tới bảng, hình, audit và claim boundary tương ứng.

Nếu chỉ có thời gian đọc một file sau guideline, hãy đọc file skeleton này.

### Bước 3: đọc claim và number lock

Đọc các file:

- `CryptoRegimeShift/outputs/paper_assets/table_11_acceptance_bar.csv`
- `CryptoRegimeShift/outputs/paper_assets/table_13_claim_to_evidence_map.csv`
- `CryptoRegimeShift/outputs/paper_assets/table_14_number_consistency_check.csv`
- `CryptoRegimeShift/outputs/paper_assets/limitation_wording_stage3_12_vi.md`

Mục đích:

- `table_11_acceptance_bar.csv`: biết tiêu chí nào PASS/PARTIAL/BLOCKED/FAIL.
- `table_13_claim_to_evidence_map.csv`: biết claim nào được phép viết và claim nào bị cấm.
- `table_14_number_consistency_check.csv`: khóa số liệu, tránh viết sai số.
- `limitation_wording_stage3_12_vi.md`: dùng để viết phần limitations an toàn.

### Bước 4: đọc kết quả cross-asset BTC<->ETH

Đọc các file:

- `CryptoRegimeShift/outputs/paper_assets/table_16_cross_asset_forecasting_execution.csv`
- `CryptoRegimeShift/outputs/paper_assets/table_17_cross_asset_bootstrap.csv`
- `CryptoRegimeShift/outputs/paper_assets/cross_asset_narrative_stage3_13_vi.md`
- `CryptoRegimeShift/audits/audit_stage3_13_cross_asset_paper_lock_v001.md`

Mục đích:

- hiểu kết quả BTC -> ETH và ETH -> BTC;
- hiểu vì sao cross-asset đã được evaluate;
- hiểu vì sao vẫn không được viết như policy tạo lợi nhuận phổ quát.

### Bước 5: đọc audit readiness cuối cùng

Đọc các file:

- `CryptoRegimeShift/audits/audit_stage3_14_paper_asset_consistency_and_draft_v001.md`
- `CryptoRegimeShift/audits/audit_stage3_12_paper_draft_readiness.md`
- `CryptoRegimeShift/audits/audit_stage3_11_icdm_evidence_hardening.md`

Mục đích:

- xác nhận paper assets đã nhất quán;
- xác nhận number consistency không có FAIL;
- hiểu quyết định cuối cùng trước khi viết bản IEEE.

## 2. Trạng thái canonical hiện tại

Trạng thái paper hiện tại:

- Acceptance bar: `7 PASS`, `2 PARTIAL`, `0 BLOCKED`, `0 FAIL`.
- BTC-USDT full-year đã hoàn tất.
- ETH-USDT full-year đã hoàn tất.
- BTC<->ETH asset-held-out đã có forecasting và execution/RSEP.
- Cross-asset được claim ở mức **đã được evaluate**, không phải policy sinh lời hay policy phổ quát.
- RSEP giảm thiệt hại so với cost-aware trong asset-held-out execution, nhưng net PnL vẫn âm.
- TCN stride-1 cho thấy negative evidence quan trọng: macro-F1 tốt hơn không tự động làm execution tốt hơn.

Cách diễn giải đúng:

> Forecasting signal tồn tại, nhưng execution edge rất mỏng và dễ bị phí, spread, latency, depth stress ăn mòn. Giá trị paper nằm ở benchmark/evaluation protocol và failure-analysis có kỷ luật.

## 3. File nên đưa lên GitHub

Nên đưa các nhóm file sau lên GitHub nếu không chứa dữ liệu lớn hoặc thông tin nhạy cảm.

### Code và cấu hình

- `CryptoRegimeShift/src/`
- `CryptoRegimeShift/scripts/`
- `CryptoRegimeShift/configs/`
- `CryptoRegimeShift/tests/`
- `CryptoRegimeShift/requirements.txt`
- `CryptoRegimeShift/pyproject.toml`
- `CryptoRegimeShift/README.md`
- `CryptoRegimeShift/AGENTS.md`

### Tài liệu định hướng paper

- `CryptoRegimeShift/TongQuan.md`
- `CryptoRegimeShift/MoTa.md`
- `CryptoRegimeShift/ThucNghiem.md`
- `CryptoRegimeShift/guideline.md`

### Audit và paper assets nhỏ

- `CryptoRegimeShift/audits/`
- `CryptoRegimeShift/outputs/paper_assets/`
- `CryptoRegimeShift/outputs/tables/`
- `CryptoRegimeShift/outputs/figures/` nếu có figure nhỏ cần dùng cho paper.

Lưu ý: nếu `outputs/tables/` có bảng quá lớn trong tương lai, chỉ giữ bảng canonical nhỏ phục vụ paper.

## 4. File không nên đưa lên GitHub

Không đưa các nhóm file sau lên GitHub:

- `CryptoRegimeShift/data/`
- `CryptoRegimeShift/outputs/checkpoints/`
- `CryptoRegimeShift/outputs/logs/`
- parquet prediction/backtest/feature/label/regime/split lớn;
- dữ liệu thô BTC/ETH;
- trọng số mô hình như `.pt`, `.ckpt`, `.joblib`;
- cache như `__pycache__/`, `.pytest_cache/`;
- file tạm như `.tmp`;
- token, API key, secret, credential.

Lý do:

- dữ liệu và model artifact rất lớn;
- có thể có ràng buộc data/license;
- paper chỉ cần code, config, audit, table/figure canonical nhỏ để tái hiện protocol và đọc kết quả.

## 5. Bản đồ paper assets quan trọng

### Skeleton và narrative

- `outputs/paper_assets/ieee_draft_skeleton_stage3_14_vi.md`
  - Khung chính để viết bản IEEE/ICDM.
- `outputs/paper_assets/result_narrative_stage3_11_vi.md`
  - Narrative evidence pack tổng hợp Stage 3.11.
- `outputs/paper_assets/cross_asset_narrative_stage3_13_vi.md`
  - Narrative riêng cho BTC<->ETH cross-asset.
- `outputs/paper_assets/paper_outline_stage3_12_vi.md`
  - Outline paper trước khi có skeleton Stage 3.14.
- `outputs/paper_assets/limitation_wording_stage3_12_vi.md`
  - Cách viết limitations an toàn.

### Bảng claim và consistency

- `outputs/paper_assets/table_11_acceptance_bar.csv`
  - 9 tiêu chí acceptance reviewer-facing.
- `outputs/paper_assets/table_12_claim_support_matrix.csv`
  - Claim support matrix Stage 3.11.
- `outputs/paper_assets/table_13_claim_to_evidence_map.csv`
  - Mapping claim -> evidence -> wording được phép -> wording bị cấm.
- `outputs/paper_assets/table_14_number_consistency_check.csv`
  - Number lock; trước khi viết paper cần kiểm tra không có dòng `FAIL`.
- `outputs/paper_assets/table_15_reproducibility_checklist.csv`
  - Checklist reproducibility.

### Bảng dữ liệu và kết quả chính

- `outputs/paper_assets/table_1_dataset_stats.csv`
  - Dataset stats.
- `outputs/paper_assets/table_2_regime_distribution.csv`
  - Regime distribution.
- `outputs/paper_assets/table_3_forecasting_by_regime.csv`
  - Forecasting by-regime.
- `outputs/paper_assets/table_4_forecast_to_execution.csv`
  - Forecast-to-execution.
- `outputs/paper_assets/table_8_model_forecasting_execution_comparison.csv`
  - So sánh model forecasting/execution.
- `outputs/paper_assets/table_9_model_stress_comparison.csv`
  - Stress comparison.
- `outputs/paper_assets/table_10_model_robustness_comparison.csv`
  - Robustness comparison.
- `outputs/paper_assets/table_16_cross_asset_forecasting_execution.csv`
  - BTC->ETH và ETH->BTC forecasting + execution.
- `outputs/paper_assets/table_17_cross_asset_bootstrap.csv`
  - Bootstrap cross-asset.

### Figures

- `outputs/paper_assets/fig_4_fee_stress.png`
- `outputs/paper_assets/fig_5_latency_decay.png`
- `outputs/paper_assets/fig_6_worst_regime.png`
- `outputs/paper_assets/fig_7_model_fee_stress.png`
- `outputs/paper_assets/fig_8_model_latency_stress.png`

Các figure này nên dùng để minh họa degradation dưới fee/latency/stress, không dùng để claim hệ thống giao dịch sinh lời.

## 6. Bản đồ audit nên đọc

### Audit paper readiness

- `audits/audit_stage3_14_paper_asset_consistency_and_draft_v001.md`
  - Audit mới nhất; xác nhận skeleton IEEE đã sẵn sàng.
- `audits/audit_stage3_13_cross_asset_paper_lock_v001.md`
  - Audit cross-asset BTC<->ETH.
- `audits/audit_stage3_12_paper_draft_readiness.md`
  - Audit number lock và paper draft readiness.
- `audits/audit_stage3_11_icdm_evidence_hardening.md`
  - Audit evidence pack reviewer-facing.

### Audit model và robustness

- `audits/audit_stage3_10_tcn_stride1_fairness_check.md`
  - TCN stride-1 fairness và negative evidence.
- `audits/audit_stage3_9_tcn_gpu_execution_ready.md`
  - TCN execution-ready inference.
- `audits/audit_stage3_7_model_comparative_stress_pack.md`
  - SGD vs XGBoost vs TCN stress comparison.
- `audits/audit_stage3_6_xgboost_gpu_btc_full2024_model_comparison.md`
  - XGBoost GPU full-year baseline.

### Audit ETH và cross-asset

- `audits/audit_stage_eth_full2024_conversion_v001.md`
- `audits/audit_stage_eth_1_artifact_data_feature_regime_readiness_v001.md`
- `audits/audit_stage_eth_2_within_asset_sgd_execution_v001.md`
- `audits/audit_stage_eth_3_asset_heldout_btc_eth_sgd_v001.md`
- `audits/audit_stage_eth_4_asset_heldout_execution_rsep_v001.md`

Đọc nhóm audit này khi cần hiểu ETH data, ETH within-asset, asset-held-out forecasting và asset-held-out execution/RSEP.

## 7. Claim được phép và không được phép

### Được phép viết

- Paper đề xuất một benchmark/evaluation protocol cho L2 crypto order book dưới microstructure regime shifts.
- Evaluation cần đi từ forecasting sang execution, vì metric dự báo trung bình không đủ.
- Regime-aware evaluation cho thấy performance thay đổi theo trạng thái thanh khoản/volatility/momentum/shock.
- Stress grid cho thấy edge nhạy với fee, latency, spread và depth.
- RSEP là selective execution baseline giúp giảm exposure và giảm thiệt hại trong một số setting.
- BTC<->ETH đã được evaluate ở forecasting và execution/RSEP với tuning chỉ trên source validation.
- Kết quả âm net PnL là evidence khoa học cho forecast-to-execution degradation.

### Không được phép viết

- Không viết paper như một hệ thống giao dịch tạo lợi nhuận.
- Không viết RSEP là policy luôn thắng.
- Không viết model đã sẵn sàng giao dịch live.
- Không viết simulator có thứ tự hàng đợi chính xác hoặc L3/MBO realism.
- Không viết cross-asset như policy phổ quát áp dụng cho mọi asset.
- Không che negative evidence của TCN stride-1 hoặc net PnL âm.

## 8. Prompt gợi ý cho ChatGPT viết paper

### Prompt tổng quát

```text
Bạn là chuyên gia viết paper ICDM. Hãy đọc guideline.md trước, sau đó đọc MoTa.md, ThucNghiem.md và outputs/paper_assets/ieee_draft_skeleton_stage3_14_vi.md. Hãy viết bản paper draft theo hướng benchmark/failure-analysis + robust selective execution có điều kiện. Không claim hệ thống giao dịch tạo lợi nhuận, không claim live execution, không claim thứ tự hàng đợi chính xác. Mỗi claim phải trỏ tới evidence table/figure/audit tương ứng.
```

### Prompt viết abstract

```text
Dựa trên guideline.md, ieee_draft_skeleton_stage3_14_vi.md, table_11_acceptance_bar.csv và table_13_claim_to_evidence_map.csv, hãy viết abstract cho ICDM. Abstract phải nhấn mạnh forecast-to-execution degradation, regime-aware evaluation, stress robustness và BTC<->ETH cross-asset evaluation. Không dùng ngôn ngữ trading-profit.
```

### Prompt viết introduction

```text
Hãy viết Introduction cho paper. Dùng MoTa.md để lấy intuition, ThucNghiem.md để lấy độ lớn thực nghiệm, và ieee_draft_skeleton_stage3_14_vi.md để giữ claim boundary. Introduction cần nêu gap: forecasting score trong LOB/HFT không đủ nếu không kiểm tra execution cost, regime shifts và stress.
```

### Prompt viết methodology

```text
Hãy viết Methodology. Mô tả data audit, causal features, cost-aware labels, refined regime taxonomy, chronological split, forecasting baselines, execution simulator, RSEP, stress grid và bootstrap. Chỉ mô tả ở mức paper, không kể lịch sử debug/fail/retry.
```

### Prompt viết experiments

```text
Hãy viết Experiments/Results dựa trên table_1 tới table_17 trong outputs/paper_assets. Hãy trình bày kết quả theo flow: dataset -> regime -> forecasting -> forecast-to-execution -> stress -> model comparison -> cross-asset. Khi có net PnL âm, hãy diễn giải là forecast-to-execution degradation/failure-analysis.
```

### Prompt viết limitations

```text
Hãy viết Limitations dựa trên limitation_wording_stage3_12_vi.md. Phải nêu rõ snapshot-level L2, không có L3 queue priority, không có hidden liquidity/passive fill realism, net PnL âm, và RSEP không phải policy luôn thắng.
```

### Prompt kiểm tra overclaim

```text
Hãy review draft paper và liệt kê mọi câu có nguy cơ overclaim. So sánh từng câu với table_13_claim_to_evidence_map.csv. Nếu câu nào claim vượt quá evidence, hãy sửa lại theo wording an toàn.
```

### Prompt chuẩn bị rebuttal

```text
Hãy đóng vai reviewer ICDM khó tính. Dựa trên guideline.md, audit_stage3_14_paper_asset_consistency_and_draft_v001.md và table_13_claim_to_evidence_map.csv, hãy dự đoán 10 criticism mạnh nhất và viết phản hồi trung thực, không overclaim.
```

## 9. Checklist trước khi đưa lên GitHub

Trước khi push repo hoặc đưa cho ChatGPT khác, kiểm tra:

- `CryptoRegimeShift/guideline.md` tồn tại.
- `CryptoRegimeShift/MoTa.md` và `CryptoRegimeShift/ThucNghiem.md` đã cập nhật cross-asset.
- `outputs/paper_assets/ieee_draft_skeleton_stage3_14_vi.md` tồn tại.
- `outputs/paper_assets/table_14_number_consistency_check.csv` không có `FAIL`.
- Không commit `CryptoRegimeShift/data/`.
- Không commit checkpoints/logs/trọng số mô hình.
- Không commit prediction/backtest parquet lớn.
- Chạy được:

```powershell
python -m compileall CryptoRegimeShift\src CryptoRegimeShift\scripts CryptoRegimeShift\tests
pytest CryptoRegimeShift\tests -q
```

Nếu chỉ thêm/sửa tài liệu, có thể không cần chạy full pytest, nhưng trước khi public GitHub nên chạy đầy đủ.

## 10. Checklist cho người viết paper

Khi viết paper, luôn tự kiểm tra:

- Mỗi claim có evidence path chưa?
- Có câu nào biến kết quả net PnL âm thành claim sinh lời không?
- Có câu nào bỏ qua TCN stride-1 negative evidence không?
- Có câu nào nói RSEP luôn thắng không?
- Có câu nào nói cross-asset generalization vượt quá BTC<->ETH không?
- Có dùng `table_14_number_consistency_check.csv` để khóa số chưa?
- Có đưa limitations đủ rõ chưa?

Nếu câu trả lời cho bất kỳ mục nào là “chưa”, quay lại đọc:

- `outputs/paper_assets/table_13_claim_to_evidence_map.csv`
- `outputs/paper_assets/limitation_wording_stage3_12_vi.md`
- `audits/audit_stage3_14_paper_asset_consistency_and_draft_v001.md`
