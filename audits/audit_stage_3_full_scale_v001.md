# Audit Stage 3 Full Scale v001

## 1. Phạm vi và kết luận ngắn

Stage 3 đã chạy pipeline BTC-USDT full-year 2024 theo hướng benchmark/failure-analysis:

- Data audit: 167,753,156 snapshot hợp lệ trên 366 ngày.
- Feature/label/prediction scale: 167,751,306 row sau khi trừ horizon/drop của label.
- Split chronological: train 100,650,783; valid 33,550,261; test 33,550,262.
- Forecasting baseline: SGD streaming, không mở deep baseline trong vòng này.
- Execution chain: policy tuning validation-only, backtest, RSEP, ablation, stress grid, report pack.

Kết luận chính: Stage 3 đủ mạnh để củng cố thesis benchmark rằng forecasting ngắn hạn có tín hiệu nhưng edge bị phí, spread, latency và regime risk bào mòn rất mạnh. RSEP giúp giảm forecast-to-execution collapse so với baseline threshold/cost-aware, nhưng net PnL vẫn âm ở fee 1 bps. Vì vậy claim phù hợp vẫn là robust selective execution và failure-analysis, không phải trading bot sinh lời.

## 2. Data và artifact

Audit data full-year cho thấy dataset đủ lớn cho paper-scale benchmark:

- Số ngày: 366.
- Median snapshot interval: khoảng 100.000 ms.
- Mean spread: 0.02827.
- Mean depth top10: 9.9064.
- 37 partition 10 ngày đã được dùng để tránh giữ toàn bộ năm trong RAM.

Ghi chú vận hành: các parquet trung gian rất lớn như `features.parquet`, `labels.parquet`, `regimes.parquet` và `splits.parquet` đã được xác minh rồi dọn sau khi tạo predictions và tables để giữ dung lượng đĩa. Artifact còn giữ gồm predictions, backtest trades, tables, paper assets, metadata logs và audit. Nếu cần tái lập từ giữa pipeline, nên chạy lại từ feature/regime/split hoặc cải tiến checkpoint partitioned trước.

## 3. Taxonomy stability

Taxonomy refined tiếp tục pass gate ở full-year:

- UNKNOWN overall: 13.19%, đạt yêu cầu `< 15%`.
- Daily UNKNOWN p90: 15.43%, đạt yêu cầu `< 25%`.
- Daily UNKNOWN max: 16.64%, vẫn không tạo tháng/ngày mất ổn định nghiêm trọng.
- Monthly UNKNOWN thấp nhất ở 2024-08: 11.32%; cao nhất ở 2024-12: 15.27%.

Regime distribution full-year:

- `BALANCED_TRANSITION`: 21.26%.
- `MOMENTUM_TOXIC`: 17.55%.
- `MILD_LIQUIDITY_STRESS`: 16.34%.
- `UNKNOWN`: 13.19%.
- `CHOPPY_MEAN_REVERTING`: 10.47%.
- `SHOCK_RECOVERY`: 8.66%.
- Các extreme liquidity/volatility regimes vẫn có support nhưng không chiếm quá lớn.

Đánh giá: hai residual states mới không bị collapse khi mở ra full-year. `BALANCED_TRANSITION` và `MILD_LIQUIDITY_STRESS` hấp thụ vùng trung gian có kỷ luật, giúp giảm UNKNOWN mà không ép toàn bộ dữ liệu vào extreme regimes. Điểm cần theo dõi là drift cuối năm, đặc biệt tháng 12 có UNKNOWN cao hơn ngưỡng 15% một chút nếu xét riêng theo tháng.

## 4. Forecasting full-year

SGD streaming trên test full-year đạt:

- Accuracy: 0.5589.
- Macro-F1: 0.4652.
- MCC: 0.2363.
- Balanced accuracy: 0.4637.
- Test rows: 33,550,262.

By-regime cho thấy heterogeneity rõ:

- Tốt nhất theo macro-F1: `VOLATILE_ILLIQUID` 0.4888, `SHOCK_RECOVERY` 0.4802, `MOMENTUM_TOXIC` 0.4704.
- Yếu hơn: `BALANCED_TRANSITION` 0.3953, `VOLATILE_LIQUID` 0.4040, `MILD_LIQUIDITY_STRESS` 0.4070.

Đánh giá: forecasting có tín hiệu thống kê đủ để tiếp tục evaluation by-regime, nhưng chưa đủ để claim execution profitability. Kết quả tốt hơn ở một số regime biến động giúp củng cố luận điểm microstructure regime shift có ảnh hưởng thực tế tới khả năng dự báo.

## 5. Forecast-to-execution degradation

Backtest threshold mặc định trên test full-year cho thấy collapse rất mạnh:

- `naive_threshold`: 2,490,903 trades; gross PnL 133,294.97; net PnL -364,583.25; total cost 497,878.23.
- `cost_aware_threshold`: 4,686,186 trades; gross PnL 263,030.22; net PnL -673,650.57; total cost 936,680.80.

Kết quả này là bằng chứng quan trọng cho paper: metric forecasting trung bình không đủ để đánh giá HFT policy. Khi qua cost model, turnover và phí có thể đảo hoàn toàn gross edge.

## 6. Validation-only tuning và RSEP tuned

Policy tuning dùng validation sample deterministic, không dùng test để chọn threshold. Với model label `sgd_stage3`, policy tốt nhất trên validation là `RSEP-full`.

Kết quả test tuned:

- `sgd_stage3_naive_threshold_tuned`: 32,891 trades; net PnL -4,557.58.
- `sgd_stage3_cost_aware_threshold_tuned`: 67,165 trades; net PnL -8,891.63.
- `sgd_stage3_RSEP-full_tuned`: 33,713 trades; gross PnL 2,300.82; net PnL -4,437.49.

Bootstrap day-level cho RSEP tuned so với cost-aware tuned:

- Mean diff: 68.53.
- 95% CI: [59.68, 77.23].
- n_days: 65.
- n_bootstrap: 1000.

Đánh giá: tuning làm baseline công bằng hơn rất nhiều so với threshold mặc định. RSEP tuned không tạo profit sau fee 1 bps, nhưng cải thiện có ý nghĩa thống kê so với cost-aware tuned và giảm số trade về mức có kiểm soát.

## 7. RSEP ablation

Ablation RSEP trên full-year cho thấy các risk terms có giá trị:

- `RSEP-full`: 873,770 trades; net PnL -122,646.73; worst-regime return -64,999.54.
- `RSEP-no-latency-risk`: net PnL -131,038.20.
- `RSEP-no-liquidity-risk`: net PnL -192,136.81.
- `RSEP-no-adverse-risk`: net PnL -217,306.21.
- `RSEP-no-regime-penalty`: net PnL -190,460.37.

Bootstrap của RSEP-full so với default cost-aware:

- Mean diff: 8,476.98.
- 95% CI: [7,948.04, 8,997.05].
- n_days: 65.
- n_bootstrap: 1000.

Đánh giá: full RSEP vẫn âm net, nhưng các risk components giúp giảm exposure và giảm thiệt hại so với ablations. Biến thể `no-cost-gate` có xu hướng trade quá dày và không nên đưa vào main ablation nếu chưa tối ưu lại theo streaming/sampling hoặc định nghĩa lại constraint trade count.

## 8. Stress grid

Stress grid trên `sgd_stage3_RSEP-full_tuned` cho thấy fee là trục phá edge mạnh nhất:

- Fee 0 bps: net PnL +2,300.82.
- Fee 1 bps: net PnL -4,437.49.
- Fee 2 bps: net PnL -11,175.81.
- Fee 5 bps: net PnL -31,390.75.
- Fee 10 bps: net PnL -65,082.32.

Latency cũng làm kết quả xấu dần:

- Latency 0 event: net PnL -3,569.73.
- Latency 1 event: net PnL -4,437.49.
- Latency 5 events: net PnL -5,567.37.
- Latency 10 events: net PnL -6,096.92.

Spread/depth stress làm net PnL xấu hơn nhưng nhẹ hơn fee trong simulator hiện tại. Điều này hợp lý với policy đã được chọn lọc khá mạnh, nhưng cần trình bày rõ simulator là snapshot-level L2, không phải queue-priority event-level.

## 9. Report pack

Report pack đã sinh 11 artifact trong `outputs/paper_assets`:

- Dataset statistics.
- Regime distribution.
- Forecasting by-regime.
- Forecast-to-execution.
- Robust policy và ablation.
- Model comparison.
- Fee stress, latency decay, worst-regime figure.
- Failure case studies.

Lưu ý: một số bảng còn dùng tên file `stage2` do script tái sử dụng output cũ, dù nội dung đã được Stage 3 ghi lại. Trước khi đóng paper artifact, cần đổi tên output theo stage/model để tránh nhầm lẫn reproducibility.

## 10. Góc nhìn Principal ML Scientist

Điểm mạnh:

- Full-year scale đã xác nhận taxonomy refined không chỉ tốt trên Jan-Feb hoặc Jan-Jun.
- Streaming SGD và streaming metrics giúp pipeline chạy được ở 167M rows, phù hợp với dữ liệu HFT lớn.
- Forecasting by-regime và execution by-policy tạo được mạch luận điểm rõ: predictability không đồng nghĩa tradability.
- Bootstrap theo ngày không suy biến, có nhiều ngày resample hơn Stage 1/2.

Điểm yếu:

- Chưa có ETH hoặc asset-held-out, nên claim generalization across assets vẫn bị chặn.
- Chưa có deep baseline full-year, nên phần model comparison chưa đủ mạnh nếu reviewer kỳ vọng DeepLOB/TCN ở scale lớn.
- Validation tuning dùng sample deterministic để kiểm soát RAM; cần ghi rõ và cân nhắc thêm full-validation streaming objective.
- Một số execution scripts vẫn cần hardening thêm để mọi ablation chạy streaming triệt để.

## 11. Góc nhìn Reviewer ICDM

Điểm có sức thuyết phục:

- Bài toán data mining rõ ràng: non-stationary crypto L2, regime shift, forecast-to-execution degradation.
- Protocol có tính benchmark: chronological split, train-only thresholds, validation-only policy tuning, by-regime reporting, stress-OOD, bootstrap.
- Negative net PnL không làm yếu paper nếu định vị đúng là failure-analysis và robust selective execution.

Rủi ro review:

- Nếu chỉ có BTC, reviewer có thể xem đây là single-asset case study hơn là benchmark tổng quát.
- Nếu không có baseline deep model full-year hoặc ít nhất medium-scale strong baseline, phần ML novelty có thể bị xem là chưa đủ.
- Simulator snapshot-level cần boundary rõ: không exact queue priority, không event-level L3, không live-trading-ready.
- Artifact naming còn lẫn `stage2` có thể làm reviewer nghi ngờ reproducibility nếu không sửa trước khi release.

## 12. Gate và bước kế tiếp

Gate Stage 3 BTC full-year: pass cho hướng benchmark/failure-analysis và RSEP mitigation.

Chưa nên claim:

- Profitability.
- Live trading readiness.
- Generalization across assets.
- Exact execution realism.

Bước kế tiếp nên là Stage 3.5 hardening:

- Chuẩn hóa tên artifact theo `stage` và `model_label`.
- Làm execution/RSEP ablation streaming hoàn chỉnh, đặc biệt quyết định lại `no-cost-gate`.
- Chạy XGBoost GPU full-year hoặc TCN/DeepLOB-lite nếu tài nguyên cho phép.
- Khi có ETH, chạy asset-held-out để mở claim generalization.
- Cập nhật `MoTa.md` và paper narrative theo kết quả âm net PnL: đây là bằng chứng cost-aware failure-analysis, không phải kết quả thất bại của paper.
