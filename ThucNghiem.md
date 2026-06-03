# ThucNghiem.md - Mô tả đầy đủ độ lớn thí nghiệm CryptoRegimeShift-LOB

## 1. Mục đích của file này

File này mô tả riêng phần **dữ liệu và quá trình thực nghiệm** của paper:

**CryptoRegimeShift-LOB: Benchmarking Robust HFT Policy Learning under L2 Microstructure Regime Shifts**

Mục tiêu là cung cấp đủ ngữ cảnh để một hệ thống phân tích như ChatGPT có thể đọc và tìm insight sâu hơn về:

- độ lớn dữ liệu;
- độ phức tạp pipeline;
- mức độ nghiêm túc của benchmark;
- các failure mode có giá trị khoa học;
- contribution tiềm năng cho ICDM 2026.

File này không phải abstract paper, không phải README chạy code, và không phải claim profitability. Nó là bản mô tả thực nghiệm để phân tích xem thí nghiệm hiện tại có điểm gì đủ sâu để viết thành contribution mạnh.

## 2. Câu hỏi nghiên cứu chính

Thí nghiệm không hỏi đơn giản:

```text
Model dự báo UP/FLAT/DOWN chính xác bao nhiêu?
```

Thí nghiệm hỏi câu khó hơn:

```text
Nếu một model forecasting nhìn có vẻ tốt,
thì edge đó có còn sống sau phí, spread, latency,
slippage, thanh khoản mỏng và regime shift hay không?
```

Do đó toàn bộ pipeline được thiết kế để nối từ:

```text
L2 order book snapshot
  -> causal feature
  -> cost-aware label
  -> regime taxonomy
  -> forecasting baseline
  -> execution simulator
  -> tuned policy / RSEP
  -> stress grid
  -> bootstrap
  -> paper evidence pack
```

Điểm quan trọng: nếu kết quả net PnL âm, đó không tự động là thất bại của paper. Trong bối cảnh này, net PnL âm có thể là bằng chứng rằng **forecasting metric không đủ để kết luận tín hiệu có thể trade được**.

## 3. Bộ dữ liệu thực nghiệm

### 3.1 Nguồn và phạm vi dữ liệu

Thực nghiệm chính hiện tại dùng:

| Thuộc tính | Giá trị |
|---|---:|
| Symbol | `BTC-USDT` |
| Exchange | `BINANCE` |
| Loại dữ liệu | L2 order book snapshot |
| Thời gian | `2024-01-01` đến `2024-12-31` |
| Số ngày | `366` |
| Số file raw monthly | `12` |
| Số snapshot hợp lệ sau audit | `167,753,156` |
| Median snapshot interval | khoảng `100 ms` |
| Mean spread raw | khoảng `0.028272` |
| Mean depth top-10 raw | khoảng `9.906425` |

Dữ liệu nằm trong:

```text
data/full2024
```

Tên file raw theo tháng, ví dụ:

```text
BOOK_BINANCE_BTC-USDT_JAN-2024.parquet
BOOK_BINANCE_BTC-USDT_FEB-2024.parquet
...
BOOK_BINANCE_BTC-USDT_DEC-2024.parquet
```

### 3.2 Schema ở mức dễ hiểu

Mỗi dòng là một snapshot order book tại một thời điểm. Các nhóm cột chính:

- `origin_time`: timestamp gốc của snapshot.
- `received_time`: timestamp hệ thống nhận dữ liệu.
- `sequence_number`: thứ tự snapshot/event từ nguồn dữ liệu.
- `bid_0_price`, `bid_0_size`, ..., `bid_19_price`, `bid_19_size`: 20 mức bid.
- `ask_0_price`, `ask_0_size`, ..., `ask_19_price`, `ask_19_size`: 20 mức ask.
- `symbol`: ví dụ `BTC-USDT`.
- `exchange`: ví dụ `BINANCE`.

Ví dụ trực quan:

```text
bid_0_price / bid_0_size: người mua tốt nhất đang chờ mua ở giá nào, khối lượng bao nhiêu
ask_0_price / ask_0_size: người bán tốt nhất đang chờ bán ở giá nào, khối lượng bao nhiêu
bid_1..19 / ask_1..19: các lớp sâu hơn trong order book
```

Vì đây là snapshot-level L2, paper không claim:

- exact queue priority;
- exact order cancellation;
- hidden liquidity;
- event-level LOBSTER realism;
- L3/MBO reconstruction.

### 3.3 Trạng thái ETH và cross-asset hiện tại

ETH-USDT hiện đã có đủ artifact full-year để mở rộng paper khỏi BTC-only:

- ETH-USDT đã có 12 parquet tháng trong `data/full2024`.
- ETH full-year đã chạy data audit, feature/label, refined regime, split, SGD within-asset và execution/RSEP.
- Asset-held-out đã chạy hai hướng: BTC train/valid -> ETH test và ETH train/valid -> BTC test.
- Cross-asset hiện được claim ở mức **đã evaluate forecasting và execution/RSEP**, không phải profitable hoặc universal cross-asset trading policy.

Điểm này nên được viết trung thực: ETH giúp tăng sức nặng benchmark, nhưng net PnL vẫn âm nên paper vẫn là benchmark/failure-analysis, không phải trading-profit paper.

## 4. Quy mô dữ liệu sau xử lý

### 4.1 Stage 2: BTC Jan-Jun 2024

Stage 2 là sandbox trung bình, dùng để kiểm tra taxonomy, feature engine, policy tuning và execution chain trước khi mở full-year.

| Thành phần | Giá trị |
|---|---:|
| Phạm vi | BTC-USDT Jan-Jun 2024 |
| Feature/label rows | `69,532,240` |
| Test rows | `13,906,448` |
| UNKNOWN overall | `13.37%` |
| p90 daily UNKNOWN | khoảng `15.60%` |
| SGD macro-F1 | `0.4557` |
| SGD MCC | `0.2503` |

Ý nghĩa: Stage 2 đủ lớn để thấy pattern không còn là toy example, nhưng vẫn dùng như bước kiểm tra trước full-year.

### 4.2 Stage 3: BTC full-year 2024

Stage 3 là kết quả chính hiện tại của paper.

| Thành phần | Giá trị |
|---|---:|
| Raw valid snapshots sau audit | `167,753,156` |
| Feature/label/prediction rows | `167,751,306` |
| Partition feature build | `37` partitions |
| Partition size | 10 ngày |
| Train rows | `100,650,783` |
| Validation rows | `33,550,261` |
| Test rows | `33,550,262` |

Số feature/label/prediction rows nhỏ hơn số snapshot hợp lệ một chút vì các điểm cuối chuỗi không đủ future horizon để tạo label.

Nếu nhìn theo scale ML thông thường, đây là thí nghiệm rất lớn:

- hơn 167 triệu snapshot;
- hơn 100 triệu dòng train;
- hơn 33 triệu dòng test;
- nhiều mô hình và policy cùng chạy trên cùng protocol;
- stress grid và bootstrap chạy sau forecasting, không chỉ báo cáo một metric ML.

## 5. Pipeline thực nghiệm đầy đủ

Pipeline chính:

```text
00 data audit
  -> 01 build features + labels
  -> 02 label regimes
  -> 03 make splits
  -> 04 train forecasters
  -> 09 tune execution policies
  -> 05/06/07 execution, RSEP, stress
  -> 08 report pack
  -> 15/16 evidence and paper draft pack
```

### 5.1 Audit dữ liệu

Mục tiêu:

- kiểm tra schema;
- kiểm tra timestamp;
- kiểm tra spread/depth;
- phát hiện crossed book hoặc invalid book;
- xác nhận snapshot interval;
- tạo dataset statistics.

Insight tiềm năng: phần audit giúp paper không chỉ là model paper mà là benchmark paper có data rigor.

### 5.2 Feature và label causal

Feature được tạo tại thời điểm `t`, chỉ dùng thông tin tại hoặc trước `t`.

Nhóm feature chính:

- spread và relative spread;
- depth top levels;
- imbalance;
- OFI proxy;
- returns và volatility;
- liquidity stress;
- momentum/choppiness;
- adverse-selection proxy.

Label là cost-aware ternary:

- `UP`: future return đủ lớn để vượt cost threshold;
- `DOWN`: future return đủ âm để vượt cost threshold;
- `FLAT`: biến động không đủ bù cost.

Insight tiềm năng: cách tạo label này đặt câu hỏi gần execution hơn so với label direction thuần túy.

### 5.3 Regime taxonomy

Regime taxonomy dùng causal microstructure features để gán trạng thái thị trường.

Các regime chính:

- `BALANCED_TRANSITION`
- `MILD_LIQUIDITY_STRESS`
- `MOMENTUM_TOXIC`
- `LIQUIDITY_DROUGHT`
- `CHOPPY_MEAN_REVERTING`
- `SHOCK_RECOVERY`
- `CALM_LIQUID`
- `CALM_ILLIQUID`
- `VOLATILE_ILLIQUID`
- `VOLATILE_LIQUID`
- `UNKNOWN`

Stage 3 regime distribution:

| Regime | Share |
|---|---:|
| `BALANCED_TRANSITION` | `21.26%` |
| `MOMENTUM_TOXIC` | `17.55%` |
| `MILD_LIQUIDITY_STRESS` | `16.34%` |
| `UNKNOWN` | `13.19%` |
| `CHOPPY_MEAN_REVERTING` | `10.47%` |
| `SHOCK_RECOVERY` | `8.66%` |
| `CALM_LIQUID` | `4.66%` |
| `CALM_ILLIQUID` | `3.39%` |
| `LIQUIDITY_DROUGHT` | `2.65%` |
| `VOLATILE_ILLIQUID` | `1.79%` |
| `VOLATILE_LIQUID` | `0.03%` |

UNKNOWN overall ở Stage 3 là `13.19%`, daily p90 UNKNOWN khoảng `15.43%`.

Insight tiềm năng: taxonomy không chỉ chia thị trường thành bull/bear, mà phân tích cấu trúc thanh khoản, volatility, toxicity và transition state.

### 5.4 Chronological split

Split chính là chronological:

```text
Train -> Validation -> Test
```

Vai trò:

- train: fit model, scaler, class return means;
- validation: tune threshold/policy;
- test: báo cáo kết quả cuối.

Điểm quan trọng: threshold không được tune trên test. Điều này giúp paper tránh overfit policy vào giai đoạn test.

## 6. Forecasting baselines

### 6.1 SGD full-year

`sgd_stage3` là main tabular baseline vì đơn giản, dễ tái lập và là điểm neo tốt cho failure-analysis.

| Metric | Giá trị |
|---|---:|
| accuracy | `0.5589` |
| macro-F1 | `0.4652` |
| MCC | `0.2363` |
| balanced accuracy | `0.4637` |
| test rows | `33,550,262` |

### 6.2 XGBoost GPU full-year

`xgboost_gpu_stage3` chạy trên RTX 3090, dùng như strong tabular baseline phụ.

| Metric | Giá trị |
|---|---:|
| accuracy | `0.5677` |
| macro-F1 | `0.4562` |
| MCC | `0.2364` |
| balanced accuracy | `0.4555` |
| test rows | `33,550,262` |

Insight: XGBoost accuracy cao hơn SGD, nhưng macro-F1/balanced accuracy thấp hơn. Điều này cho thấy metric selection rất quan trọng trong LOB forecasting.

### 6.3 TCN temporal baselines

TCN được dùng để kiểm tra liệu temporal window model có tạo lợi thế rõ hơn không.

`tcn_gpu_stage3` là temporal pilot diagnostic, không nên so trực tiếp như full-row baseline vì dùng stride/sample scope khác.

`tcn_gpu_stage3_stride1` là temporal fairness check quan trọng hơn.

| Model | macro-F1 | MCC | Vai trò |
|---|---:|---:|---|
| `tcn_gpu_stage3` | `0.4689` | `0.2275` | temporal pilot / appendix |
| `tcn_gpu_stage3_stride1` | `0.4688` | `0.2274` | temporal fairness baseline |

Insight: TCN có macro-F1 cao nhất nhưng MCC thấp hơn SGD/XGBoost. Khi đưa qua execution, RSEP không thắng cost-aware trên TCN stride-1. Đây là negative evidence có giá trị.

### 6.4 DeepLOB-lite pilot

DeepLOB-lite đã được xem như baseline phụ theo hướng literature LOB. Kết quả không được chọn làm narrative chính hiện tại.

Insight: Không nên mở rộng deep baseline chỉ để làm đẹp số nếu evidence đã đủ cho benchmark/failure-analysis.

## 7. Execution simulator, policy tuning và RSEP

### 7.1 Vì sao cần execution simulator

Forecasting đúng hướng không đồng nghĩa với trade có lời. Khi dùng market order, ta phải chịu:

- vào lệnh qua ask/bid;
- spread;
- fee;
- slippage khi depth mỏng;
- latency;
- partial fill;
- regime-specific risk.

Simulator hiện là L2 snapshot market-order replay approximation, không phải live trading engine.

### 7.2 Policy tuning

Các policy được tune trên validation:

- naive threshold;
- cost-aware threshold;
- RSEP threshold.

Validation-only tuning giúp tránh chọn threshold dựa trên test.

### 7.3 RSEP

RSEP là:

```text
expected edge > estimated cost + latency risk + liquidity risk + adverse risk + regime risk + theta
```

Nếu không vượt ngưỡng này, policy chọn `NO-TRADE`.

RSEP không phải model dự báo mới. Nó là decision gate sau forecasting model.

## 8. Execution và stress results

### 8.1 Forecast-to-execution degradation

Stage 3 cho thấy degradation rất rõ:

| Model | Gross PnL ở fee 0 bps | Net PnL ở fee 1 bps | N trades |
|---|---:|---:|---:|
| `sgd_stage3` RSEP tuned | `+2,300.82` | `-4,437.49` | `33,713` |
| `xgboost_gpu_stage3` RSEP tuned | `+2,953.00` | `-4,303.19` | `36,360` |
| `tcn_gpu_stage3_stride1` RSEP tuned | `+271.73` | `-814.17` | `5,435` |

Insight: gross edge có thể tồn tại, nhưng chỉ cần fee `1 bps` đã làm net PnL âm. Đây là evidence mạnh cho forecast-to-execution degradation.

### 8.2 Fee stress

Ví dụ với `sgd_stage3` RSEP tuned:

| Fee bps | Net PnL |
|---:|---:|
| `0` | `+2,300.82` |
| `1` | `-4,437.49` |
| `2` | `-11,175.81` |
| `5` | `-31,390.75` |
| `10` | `-65,082.32` |

Insight: edge cực kỳ mỏng. Đây là một câu chuyện hay cho paper: nếu chỉ report forecasting metric, ta bỏ qua độ nhạy rất mạnh với cost.

### 8.3 Stress axes

Stress grid hiện có:

- `fee_bps`: 5 levels mỗi model;
- `latency_events`: 4 levels mỗi model;
- `spread_multiplier`: 3 levels mỗi model;
- `depth_multiplier`: 3 levels mỗi model.

Các model có stress comparison:

- `sgd_stage3`;
- `xgboost_gpu_stage3`;
- `tcn_gpu_stage3`;
- `tcn_gpu_stage3_stride1`.

Ngoài ra có RobustnessAUC và day-level bootstrap.

### 8.4 Bootstrap

Day-level bootstrap tuned Stage 3:

| Model | Mean diff vs cost-aware | CI low | CI high | n_days | n_bootstrap |
|---|---:|---:|---:|---:|---:|
| `sgd_stage3` | `68.53` | `59.68` | `77.23` | `65` | `1000` |
| `xgboost_gpu_stage3` | `2.94` | `1.07` | `4.93` | `65` | `1000` |
| `tcn_gpu_stage3` | `1.50` | `0.02` | `3.55` | `64` | `1000` |
| `tcn_gpu_stage3_stride1` | `-0.40` | `-4.46` | `4.45` | `65` | `1000` |

Insight: RSEP support không universal. SGD/XGBoost có CI dương, nhưng TCN stride-1 mixed và không support RSEP thắng cost-aware. Đây là lý do claim phải hạ giọng.

## 9. Evidence pack và acceptance bar

Stage 3.11 evidence hardening:

| Trạng thái | Số tiêu chí |
|---|---:|
| PASS | `7` |
| PARTIAL | `2` |
| BLOCKED | `0` |
| FAIL | `0` |

Các claim supported:

- BTC L2 full-year benchmark;
- regime heterogeneity;
- forecast-to-execution degradation;
- stress sensitivity;
- robustness-oriented reporting.

Các claim partial hoặc phải hạ giọng:

- RSEP không phải universal winner;
- ETH/cross-asset đã được evaluate nhưng không được viết như profitable hoặc universal policy generalization;
- live trading/profitability là `NOT_CLAIMED`.

Stage 3.12 paper draft pack:

- `paper_outline_stage3_12_vi.md`: outline paper;
- `table_13_claim_to_evidence_map.csv`: claim-to-evidence map;
- `table_14_number_consistency_check.csv`: number consistency lock;
- `limitation_wording_stage3_12_vi.md`: limitation wording;
- `table_15_reproducibility_checklist.csv`: reproducibility checklist.

Number consistency hiện không có `FAIL`.

## 10. Vì sao thí nghiệm này lớn và đáng phân tích insight

Thí nghiệm này không chỉ lớn vì có hơn 167 triệu rows. Nó lớn vì nhiều tầng đánh giá nối tiếp nhau:

1. Raw L2 data audit.
2. Causal feature generation.
3. Cost-aware labeling.
4. Regime taxonomy.
5. Chronological split.
6. Tabular forecasting baselines.
7. GPU XGBoost baseline.
8. Temporal TCN baseline.
9. Validation-only execution policy tuning.
10. RSEP and ablations.
11. Stress grid.
12. Day-level bootstrap.
13. Model-comparative evidence pack.
14. Claim-support matrix.
15. Number consistency lock.

Độ lớn thực nghiệm nằm ở chỗ paper đo được một chuỗi chuyển hóa:

```text
forecasting score
  -> expected edge
  -> execution cost
  -> regime risk
  -> stress robustness
  -> statistical support
  -> claim discipline
```

Đây là điểm có thể tạo contribution sâu hơn: không phải model nào tốt hơn, mà là **một protocol để chứng minh khi nào predictive edge không còn actionable**.

## 11. Insight ban đầu cho contribution sâu hơn

Các insight có thể khai thác:

### Insight 1: Forecasting metric và execution utility bị tách rời

TCN có macro-F1 tốt hơn nhưng execution/RSEP không thắng cost-aware. Điều này cho thấy cải thiện ML metric không đủ để claim HFT usefulness.

### Insight 2: Cost sensitivity là failure mode trung tâm

Gross edge có thể dương ở fee `0 bps`, nhưng âm ngay ở fee `1 bps`. Đây là bằng chứng rằng nhiều LOB forecasting result có thể không sống sót qua realistic cost.

### Insight 3: Regime-aware evaluation làm lộ rủi ro bị average che giấu

Spread macro-F1 theo regime và execution by-regime cho thấy average metric không đủ. Worst-regime, RegimeGap và stress axes cần được xem là first-class evaluation metrics.

### Insight 4: RSEP hữu ích như diagnostic, không nên đóng gói như trading strategy

RSEP giúp giảm exposure và phân tích cost/risk gate, nhưng không phải universal winner. Đây là claim discipline có thể làm paper đáng tin hơn.

### Insight 5: Cross-asset evaluation củng cố thesis nhưng không biến thành profitability claim

ETH và asset-held-out không còn bị chặn. Kết quả BTC->ETH và ETH->BTC cho thấy forecasting không collapse, và RSEP giảm thiệt hại so với cost-aware trong target-asset execution. Nhưng net PnL vẫn âm, nên insight sâu hơn là: **cross-asset forecast signal có thể tồn tại, nhưng execution edge vẫn rất mỏng và bị cost/stress ăn mòn**.

| Hướng | Macro-F1 | MCC | Cost-aware net PnL | RSEP net PnL | CI RSEP - cost-aware |
|---|---:|---:|---:|---:|---:|
| BTC -> ETH | `0.4325` | `0.1486` | `-287,991.44` | `-74,466.38` | [`3,314.02`, `4,048.20`] |
| ETH -> BTC | `0.4839` | `0.2424` | `-3,697.46` | `-1,144.75` | [`34.08`, `44.53`] |

Đây là contribution rất hợp với ICDM nếu được viết đúng: benchmark không chỉ kiểm tra model trên một asset, mà kiểm tra cả sự chuyển hóa từ cross-asset forecasting sang target-asset execution.

## 12. Những câu hỏi muốn ChatGPT phân tích tiếp

Khi đưa file này vào ChatGPT, có thể hỏi:

1. Từ mô tả thí nghiệm này, contribution sâu sắc nhất cho ICDM là gì?
2. Insight nào đủ mạnh để viết introduction?
3. Negative evidence nào nên đưa vào main paper thay vì appendix?
4. Reviewer sẽ nghi ngờ điểm nào nhất?
5. Làm sao diễn giải net PnL âm thành failure-analysis có giá trị?
6. Nên gọi RSEP là method, baseline, diagnostic policy hay selective execution filter?
7. Có nên nhấn mạnh TCN stride-1 như deep baseline negative evidence không?
8. Cross-asset BTC<->ETH nên được trình bày là supported claim, partial claim hay robustness check?
9. Paper nên được định vị là benchmark paper, method paper, hay empirical study?
10. Với acceptance bar `7 PASS`, `2 PARTIAL`, `0 BLOCKED`, claim nào nên đưa vào abstract?

## 13. Claim boundaries bắt buộc

Không được claim:

- model tạo profit ổn định;
- live trading readiness;
- exact queue priority;
- L3/MBO realism;
- event-level LOBSTER reconstruction;
- RSEP là SOTA trading strategy;
- profitable hoặc universal cross-asset policy generalization.

Được claim, nếu trích đúng artifact:

- BTC L2 full-year benchmark;
- regime-aware evaluation protocol;
- forecast-to-execution degradation;
- stress sensitivity theo fee/latency/spread/depth;
- RSEP như selective execution baseline/diagnostic;
- TCN stride-1 như temporal fairness check và negative evidence.
- BTC<->ETH cross-asset forecasting/execution evaluation, với wording cẩn trọng rằng RSEP giảm thiệt hại nhưng net PnL vẫn âm.

## 14. Kết luận ngắn

Thí nghiệm hiện tại có quy mô lớn và nhiều tầng kiểm chứng. Giá trị chính không nằm ở việc tìm ra một model trading có lời, mà ở việc xây dựng một benchmark cho thấy:

```text
Predictive signal trong LOB có thể tồn tại,
nhưng rất dễ biến mất khi đi qua execution cost,
market microstructure regime shifts và stress conditions.
```

Nếu viết đúng, đây là một paper về **robust evaluation under microstructure regime shifts**. Điểm mạnh là tính hệ thống, scale lớn, evidence nhiều tầng, có BTC<->ETH cross-asset evaluation và claim discipline. Điểm yếu cần ghi rõ là snapshot-level L2, simulator không có exact queue priority, và net PnL vẫn âm nên không claim profitability.
