# MoTa.md - Cách tiếp cận của paper CryptoRegimeShift-LOB

## 1. Working title

**CryptoRegimeShift-LOB: Benchmarking Robust HFT Policy Learning under L2 Microstructure Regime Shifts**

Paper này hướng tới ICDM 2026 Main Track theo hướng **benchmark + methodology + empirical failure-analysis** cho học chính sách giao dịch tần suất cao trên dữ liệu L2 order book crypto.

Điểm cần giữ rõ: đây không phải paper tuyên bố tạo trading bot sinh lời. Mục tiêu là chỉ ra một protocol đánh giá nghiêm túc hơn cho các mô hình forecasting/HFT policy khi thị trường đổi trạng thái vi cấu trúc, chi phí thay đổi, latency tăng, spread giãn và thanh khoản suy giảm.

## 1.1 Paper này muốn chứng minh điều gì trong 1 trang

Nếu đọc paper này như một câu chuyện ngắn, luồng chính là:

```text
L2 order book snapshots
        |
        v
Causal features + cost-aware labels
        |
        v
Microstructure regime taxonomy
        |
        v
Forecasting baselines
        |
        v
Execution simulator + RSEP + stress grid
        |
        v
Evidence: forecasting tốt chưa chắc trade được sau cost/risk
```

Input của paper là chuỗi snapshot L2 order book: nhiều mức bid/ask quanh mid price, với size và price ở từng level. Từ đó pipeline tạo feature causal, gán label `UP/FLAT/DOWN` có xét cost, chia thị trường thành các regime vi cấu trúc, rồi huấn luyện các baseline forecasting.

Điểm khác biệt nằm ở nửa sau của pipeline. Paper không dừng ở câu "model dự báo đúng bao nhiêu", mà đưa forecast qua execution simulator, RSEP, stress fee/latency/spread/depth và bootstrap theo ngày. Nhờ vậy paper kiểm tra được edge dự báo có còn sống khi phải trả phí, đi qua spread, chịu latency và gặp thanh khoản xấu hay không.

Boundary cần nhớ:

- Result chính hiện đã gồm BTC-USDT full-year, ETH-USDT full-year replication và asset-held-out BTC<->ETH ở cả forecasting lẫn execution/RSEP.
- Dữ liệu là snapshot-level L2, không phải event-level L3/MBO.
- Simulator là approximation để benchmark robustness, không phải mô phỏng exact queue priority.
- Kết quả net PnL âm không làm paper vô giá trị; ngược lại, nó là bằng chứng cho forecast-to-execution degradation.
- RSEP là robust selective execution baseline, không phải chiến lược luôn thắng.

## 1.2 Contribution chính và contribution phụ

Contribution chính nên được viết như sau:

- **Benchmark/protocol:** xây pipeline đánh giá L2 crypto dưới microstructure regime shifts, cost shifts và execution stress.
- **Regime-aware evaluation:** thay vì chỉ báo cáo average metric, paper báo cáo theo regime, worst-regime, regime gap và stress axes.
- **Forecast-to-execution failure-analysis:** chỉ ra forecasting signal có thể nhìn ổn trên metric ML nhưng yếu đi mạnh khi qua execution cost/risk.
- **Claim discipline:** giữ rõ giới hạn snapshot-level L2, không claim live trading/profitability và không viết cross-asset như một policy universal winner.

Contribution phụ, vẫn hữu ích nhưng không nên viết như main claim:

- **RSEP:** một selective execution baseline dễ giải thích, dùng để kiểm tra liệu cost/risk gate có giảm exposure và giảm thiệt hại không.
- **XGBoost GPU và TCN:** các baseline mạnh hơn để kiểm tra fairness; nếu không thắng rõ execution thì vẫn là negative evidence có giá trị.
- **Paper assets/number lock:** giúp kết quả tái lập và tránh viết lệch số giữa audit, bảng và narrative.

Nói ngắn gọn: paper mạnh nhất khi được định vị là **benchmark + evaluation protocol + failure-analysis**, không phải là paper khoe một policy trading mới luôn outperform.

## 1.3 Claim nào được nói và không được nói

| Loại claim | Được nói | Không được nói |
|---|---|---|
| Benchmark | Có benchmark/evaluation protocol cho BTC L2 full-year | Đã chứng minh tổng quát cho mọi asset |
| Regime | Metric forecasting/execution thay đổi theo microstructure regime | Regime taxonomy là chân lý thị trường duy nhất |
| Execution | Forecast edge bị ăn mòn bởi fee, spread, latency, depth stress | Model tạo profit ổn định |
| RSEP | RSEP là selective execution baseline giúp phân tích robustness | RSEP là SOTA trading strategy hoặc policy luôn thắng |
| Simulator | Snapshot-level L2 market-order replay dùng cho benchmark | Exact L3 queue priority hoặc live execution realism |
| ETH/asset-held-out | Đã evaluate BTC<->ETH ở forecasting và execution/RSEP | Profitable hoặc universal cross-asset trading policy |

## 1.4 Vì sao net PnL âm vẫn có giá trị khoa học

Trong paper trading thông thường, net PnL âm có thể bị xem là thất bại. Nhưng với paper này, net PnL âm là một phần của câu hỏi nghiên cứu.

Paper đang kiểm tra một hiện tượng: **forecasting metric có thể tạo cảm giác model hữu ích, nhưng khi đưa vào điều kiện execution có cost và stress, edge có thể biến mất**. Nếu kết quả cho thấy gross PnL còn dương ở một số setting nhưng net PnL âm sau phí/spread, đó là bằng chứng trực tiếp rằng đánh giá bằng accuracy hoặc macro-F1 là chưa đủ.

Ví dụ dễ hiểu:

```text
Model dự báo đúng hướng rất ngắn hạn.
Gross edge trước cost: +1.0 bps.
Spread + fee + slippage: -1.4 bps.
Net sau execution: -0.4 bps.
```

Nếu chỉ nhìn forecasting, ta tưởng model có edge. Nếu nhìn execution, ta thấy edge quá mỏng để sống sót. Đây chính là failure mode mà benchmark muốn phơi bày.

## 1.5 Bộ dữ liệu thực nghiệm

Phần thực nghiệm hiện tại dùng dữ liệu **BTC-USDT và ETH-USDT L2 order book snapshots trên Binance trong năm 2024**. Đây là dữ liệu dạng snapshot, tức mỗi dòng là một "ảnh chụp" trạng thái order book tại một thời điểm, không phải log event-level ghi từng lệnh thêm/hủy/khớp.

Quy mô dataset Stage 3 full-year đã được khóa trong `outputs/paper_assets/table_1_dataset_stats.csv`:

| Symbol | Exchange | Số ngày | Snapshot hợp lệ sau audit | Median interval | Mean spread | Mean depth top-10 |
|---|---|---:|---:|---:|---:|---:|
| `BTC-USDT` | `BINANCE` | `366` | `167,753,156` | `100.000256 ms` | `0.0282724554` | `9.9064246` |
| `ETH-USDT` | `BINANCE` | `366` | `114,416,283` | `200.0 ms` | `0.0107778793` | `105.1572273` |

Lưu ý về ETH: conversion raw parquet có `114,416,570` rows, còn stage audit dùng `114,416,283` snapshots nằm trong phạm vi `stage_3_full_scale`. Sau khi build feature/label, ETH còn `114,414,433` rows vì phải bỏ các điểm cuối không đủ future horizon.

Mỗi snapshot có các nhóm cột chính:

- `origin_time`, `received_time`: thời gian gốc và thời gian nhận.
- `sequence_number`: thứ tự snapshot/event từ nguồn dữ liệu.
- `bid_0_price`, `bid_0_size`, ..., `bid_19_price`, `bid_19_size`: 20 mức bid.
- `ask_0_price`, `ask_0_size`, ..., `ask_19_price`, `ask_19_size`: 20 mức ask.
- `symbol`, `exchange`: định danh thị trường.

Ví dụ dễ hiểu: một dòng snapshot cho biết tại thời điểm đó, bên mua tốt nhất đang đặt giá nào, size bao nhiêu; bên bán tốt nhất đang đặt giá nào, size bao nhiêu; và các mức sâu hơn trong order book đang dày hay mỏng. Từ chuỗi snapshot này, pipeline mới tính spread, depth, imbalance, volatility, liquidity stress và các feature causal khác.

Dữ liệu BTC sau khi build feature/label cho Stage 3 có `167,751,306` rows. Số này nhỏ hơn snapshot audit một chút vì phải bỏ các điểm cuối không đủ horizon để tạo future label. Split chronological BTC hiện tại:

- Train: `100,650,783` rows.
- Validation: `33,550,261` rows.
- Test: `33,550,262` rows.

Stage 2 là sandbox trung bình trên BTC-USDT Jan-Jun 2024, dùng để kiểm tra taxonomy, policy tuning và execution chain trước khi mở full-year. Stage 3 là kết quả BTC full-year chính cho paper.

Trạng thái ETH/cross-asset hiện tại:

- ETH-USDT full-year 2024 đã được convert sang parquet chuẩn `data/full2024`, sau đó chạy audit, feature/label, refined regime, split, SGD within-asset và execution/RSEP.
- Asset-held-out đã chạy hai hướng: BTC train/valid -> ETH test và ETH train/valid -> BTC test.
- Cross-asset hiện được claim ở mức **evaluated under BTC<->ETH**, không được viết là profitable hoặc universal policy generalization.
- Vì dữ liệu là L2 snapshot, paper không claim exact queue priority, exact cancellation, hidden liquidity hay L3/MBO realism.
- Dữ liệu phù hợp để benchmark forecast-to-execution robustness ở cấp snapshot, không phù hợp để claim live execution chính xác từng lệnh.

## 2. Bài toán đang giải quyết, nói theo cách dễ hiểu

Dữ liệu L2 order book cho ta thấy nhiều mức bid/ask quanh mid price. Có thể hình dung đây là ảnh chụp liên tục của thị trường:

- Bên mua và bên bán đang dày hay mỏng.
- Spread đang hẹp hay rộng.
- Thanh khoản nằm gần best bid/ask hay bị rút sâu xuống các mức xa hơn.
- Dòng order book đang có momentum, nhiễu mean-reverting, hay shock thanh khoản.

Một mô hình forecasting có thể dự báo hướng giá rất ngắn hạn, ví dụ "giá có khả năng tăng sau 50 snapshot". Nhưng trong thực tế execution, dự báo đúng chưa chắc có lợi:

- Nếu spread rộng, vào lệnh đã phải trả giá xấu.
- Nếu phí cao, lợi nhuận nhỏ bị ăn hết.
- Nếu latency tăng, tín hiệu có thể hết hiệu lực trước khi khớp.
- Nếu depth mỏng, market order bị slippage.
- Nếu regime đổi, mô hình có thể vẫn tự tin nhưng sai trong trạng thái thị trường mới.

Vì vậy paper không chỉ hỏi: "model dự báo đúng bao nhiêu phần trăm?". Paper hỏi câu khó hơn: **khi đưa dự báo qua execution simulator và stress test, edge còn sống không, regime nào làm nó sụp, và policy nào giảm thiệt hại tốt hơn?**

## 3. Regime shift là gì trong paper này

Regime shift ở đây là thay đổi trạng thái vi cấu trúc của order book, không chỉ là giá tăng hay giảm. Ví dụ:

- `CALM_LIQUID`: thị trường tương đối yên, spread hẹp, depth tốt.
- `LIQUIDITY_DROUGHT`: thanh khoản cạn, depth giảm, spread/depth trở nên xấu.
- `MOMENTUM_TOXIC`: hướng giá có momentum mạnh nhưng đi kèm adverse-selection risk.
- `CHOPPY_MEAN_REVERTING`: giá đảo chiều/nhiễu nhiều, tín hiệu direction dễ bị phá.
- `SHOCK_RECOVERY`: sau shock, volatility còn cao nhưng thanh khoản có thể đang hồi.
- `BALANCED_TRANSITION`: vùng trung gian có cấu trúc, không cực đoan.
- `MILD_LIQUIDITY_STRESS`: thanh khoản xấu đi vừa phải, chưa đủ cực đoan để gọi là drought.
- `UNKNOWN`: chỉ giữ cho điểm thật sự mơ hồ hoặc thiếu tín hiệu.

Taxonomy này được thiết kế causal: tại thời điểm t, label regime chỉ dùng thông tin có sẵn tại hoặc trước t, không dùng future information.

## 4. Contribution chính

### 4.1 Benchmark L2 crypto regime shift

Paper xây một benchmark từ dữ liệu L2 snapshot crypto, tập trung vào điều kiện thị trường thay đổi. Benchmark này không cố giả lập toàn bộ event-level order book như LOBSTER/L3, mà dùng snapshot-level L2 để đánh giá forecasting và execution dưới stress.

Boundary cần nói rõ:

- Dữ liệu là L2 snapshot-level, không phải event-level/L3.
- Không claim exact queue priority.
- Không claim exact order cancellation hoặc hidden liquidity.
- Không claim hệ thống sẵn sàng giao dịch live.

### 4.2 Regime taxonomy có thể diễn giải

Thay vì chia thị trường chỉ theo thời gian, paper gán mỗi snapshot vào một microstructure regime. Điều này giúp trả lời:

- Model tốt ở regime nào?
- Model sụp ở regime nào?
- Execution cost phá edge mạnh nhất ở điều kiện nào?
- Worst-regime performance có bị che bởi average metric không?

Phần refined taxonomy thêm `BALANCED_TRANSITION` và `MILD_LIQUIDITY_STRESS` để giảm `UNKNOWN` có kỷ luật, không ép mọi điểm vào extreme regime.

### 4.3 Protocol đánh giá mạnh hơn average backtest

Protocol không dừng ở accuracy. Nó đánh giá:

- Overall forecasting metrics: accuracy, macro-F1, MCC, balanced accuracy.
- Forecasting by-regime.
- Forecast-to-execution degradation.
- Worst-regime return.
- Regime gap.
- Stress theo fee, latency, spread multiplier, depth multiplier.
- Bootstrap theo ngày để kiểm tra độ ổn định thống kê.

### 4.4 RSEP: Robust Selective Execution Policy

RSEP là baseline đơn giản và dễ giải thích:

> Chỉ trade khi expected edge lớn hơn estimated cost cộng với latency risk, liquidity risk, adverse-selection risk và regime risk.

Ý nghĩa trực quan: nếu tín hiệu dự báo chỉ hơi nghiêng về UP/DOWN nhưng thị trường đang mỏng, spread cao hoặc regime rủi ro, RSEP chọn không trade. Nó không cố thắng bằng cách trade nhiều hơn, mà giảm exposure khi edge không đủ bù cost/risk.

#### Kiến trúc RSEP, nói theo từng khối

RSEP có thể hiểu như một lớp "bộ lọc quyết định trade" đặt sau mô hình forecasting và trước execution simulator.

```text
L2 snapshot + causal features
        |
        v
Forecasting model
  -> prob_down, prob_flat, prob_up
        |
        v
Expected edge estimator
  -> edge kỳ vọng nếu mua/bán
        |
        v
Risk/cost estimator
  -> phí + spread + latency risk + liquidity risk + adverse-selection risk + regime risk
        |
        v
RSEP decision gate
  -> BUY / SELL / NO-TRADE
        |
        v
Market-order replay simulator
  -> gross PnL, net PnL, cost, slippage, by-regime metrics
```

Các khối chính:

- **Forecasting input:** lấy xác suất `UP/FLAT/DOWN` từ model như SGD, XGBoost hoặc deep model sau này.
- **Expected edge:** chuyển xác suất dự báo thành lợi nhuận kỳ vọng ngắn hạn, dựa trên return trung bình của từng class trong train split.
- **Estimated cost:** ước lượng phần edge chắc chắn bị ăn mất bởi spread và fee.
- **Latency risk:** phạt thêm nếu tín hiệu nhạy với delay; latency cao làm entry/exit dễ lệch khỏi thời điểm dự báo.
- **Liquidity risk:** phạt khi depth kém, liquidity drought score cao hoặc order book mỏng.
- **Adverse-selection risk:** phạt khi tín hiệu có nguy cơ bị "đuổi theo giá", tức mua ngay trước khi giá xấu đi hoặc bán ngay trước khi bật lại.
- **Regime risk:** phạt các regime nguy hiểm như `LIQUIDITY_DROUGHT`, `VOLATILE_ILLIQUID`, `MOMENTUM_TOXIC`, `CHOPPY_MEAN_REVERTING`.
- **Decision gate:** chỉ cho trade nếu edge vượt toàn bộ cost/risk buffer; nếu không vượt, action là `NO-TRADE`.

Công thức trực quan:

```text
required_edge =
    estimated_cost
  + lambda_latency  * latency_risk
  + lambda_liquidity * liquidity_risk
  + lambda_adverse   * adverse_selection_risk
  + lambda_regime    * regime_risk
  + theta_edge

BUY  nếu expected_edge >  required_edge
SELL nếu expected_edge < -required_edge
NO-TRADE nếu nằm giữa hai ngưỡng
```

Trong đó `theta_edge` và các threshold được tune trên validation split, không dùng test split để chọn.

#### Mục tiêu thí nghiệm của RSEP

Thí nghiệm với RSEP không nhằm chứng minh "trade là có lời". Mục tiêu đúng là kiểm tra:

- Forecasting signal còn bao nhiêu giá trị sau khi đi qua cost và stress.
- Việc thêm cost/risk gate có giảm trade yếu và giảm tổn thất không.
- Risk term nào thật sự có ích qua ablation.
- RSEP có cải thiện worst-regime return hoặc regime gap không.
- RSEP có sống sót tốt hơn khi fee, latency, spread hoặc depth bị stress không.
- Kết quả có ổn định theo day-level bootstrap không.

Nếu RSEP vẫn net âm nhưng giảm thiệt hại rõ so với threshold baseline, đó vẫn là kết quả có giá trị cho paper: nó hỗ trợ luận điểm rằng robust selective execution giúp **mitigate degradation**, không phải biến dự báo thành trading strategy sinh lời.

#### Ví dụ dễ hiểu về RSEP

Giả sử tại một snapshot, model dự báo:

- `prob_up = 0.58`
- `prob_flat = 0.30`
- `prob_down = 0.12`

Naive threshold có thể nói: "prob_up lớn hơn 0.55, vậy BUY".

RSEP hỏi thêm:

- Edge kỳ vọng từ xác suất này là bao nhiêu?
- Spread hiện tại có rộng không?
- Fee hai chiều có ăn hết edge không?
- Depth top levels có đủ dày không?
- Regime hiện tại có đang là `MILD_LIQUIDITY_STRESS` hoặc `LIQUIDITY_DROUGHT` không?
- Tín hiệu có rủi ro adverse selection không?

Ví dụ số đơn giản:

```text
expected_edge      = 1.4 bps
estimated_cost     = 0.8 bps
latency_risk       = 0.2 bps
liquidity_risk     = 0.3 bps
adverse_risk       = 0.2 bps
regime_risk        = 0.2 bps
theta_edge         = 0.1 bps
required_edge      = 1.8 bps
```

Vì `expected_edge = 1.4 bps` nhỏ hơn `required_edge = 1.8 bps`, RSEP chọn `NO-TRADE`. Dù model hơi nghiêng về UP, tín hiệu này không đủ mạnh để bù cost và risk.

Nếu ở snapshot khác:

```text
expected_edge      = 2.6 bps
required_edge      = 1.8 bps
```

RSEP mới cho phép `BUY`. Điểm quan trọng là RSEP không phủ nhận forecasting model; nó chỉ yêu cầu forecast phải đủ mạnh so với điều kiện execution hiện tại.

### 4.5 Empirical failure-analysis

Một phần contribution quan trọng là chỉ ra failure mode:

- Forecasting có vẻ ổn ở metric trung bình.
- Khi đưa qua simulator có phí/spread/slippage/latency, net performance có thể âm.
- Một số regime làm model hoặc policy yếu hơn rõ rệt.
- Policy robust có thể giảm thiệt hại và giảm worst-regime exposure, dù chưa đủ để claim sinh lời.

## 5. Vì sao có khả năng cạnh tranh tại ICDM 2026 nếu làm đủ

Paper có khả năng cạnh tranh tại ICDM nếu hoàn tất bằng chứng thực nghiệm vì nó phù hợp với nhiều tiêu chí của một paper data mining mạnh:

- **Bài toán rõ và có ý nghĩa:** high-frequency crypto L2 là dữ liệu lớn, nhiễu, non-stationary và thực tế.
- **Không chỉ thêm một model:** contribution nằm ở benchmark, taxonomy, protocol và failure-analysis.
- **Empirical rigor:** có chronological split, validation-only tuning, by-regime diagnostics, stress-OOD và bootstrap.
- **Claim discipline:** không tuyên bố quá mức về live trading, exact execution realism hay profitability.
- **Có thông điệp reviewer-facing:** average forecasting/backtest có thể che giấu rủi ro; robust evaluation cần đo worst-regime, cost survival và forecast-to-execution collapse.

Điều kiện để đủ sức ICDM:

- Stage 3 full-year đã chứng minh taxonomy và kết quả ổn định hơn trên BTC; cần trình bày rõ kết quả net âm như failure-analysis.
- ETH và asset-held-out đã bổ sung evidence cross-asset, nhưng chỉ được diễn giải là evaluation/replication có kiểm soát, không phải profitability hoặc universal generalization.
- Baseline forecasting cần đủ thuyết phục: SGD, XGBoost GPU, và nếu compute cho phép thì TCN/DeepLOB-lite.
- Simulator assumptions phải được trình bày trung thực như L2 market-order replay approximation.

## 6. Happy path thí nghiệm từng bước

### Bước 1: Audit dữ liệu

Đọc raw L2 snapshot theo symbol và thời gian. Kiểm tra:

- Schema có đủ price/size 20 levels mỗi bên không.
- Timestamp có hợp lệ không.
- Spread, depth, interval snapshot có bất thường không.
- Có crossed book, giá/size <= 0, missing values không.

Ví dụ dễ hiểu: trước khi học model, cần biết order book có giống "ảnh thị trường" hợp lệ không. Nếu best bid lớn hơn best ask thường xuyên, đó là dấu hiệu dữ liệu hoặc cleaning policy cần xem lại.

### Bước 2: Build causal features

Từ snapshot L2, tạo feature tại thời điểm t:

- Spread và relative spread.
- Depth imbalance ở top levels.
- OFI proxy.
- Volatility/returns ngắn hạn.
- Liquidity drought score.
- Momentum và choppiness.
- Adverse-selection proxy.

Tất cả feature phải causal: tại thời điểm t không được dùng thông tin sau t.

### Bước 3: Tạo label cost-aware

Label không chỉ là giá tăng/giảm. Label được tạo theo hướng cost-aware:

- `UP` nếu future return đủ lớn để vượt cost threshold.
- `DOWN` nếu future return đủ âm để vượt cost threshold.
- `FLAT` nếu biến động chưa đủ bù cost.

Ví dụ: nếu giá tăng 0.5 bps nhưng tổng phí/spread/slippage proxy là 1 bps, thì không nên coi đây là tín hiệu UP có thể trade được.

### Bước 4: Gán regime refined taxonomy

Dùng feature causal để gán mỗi snapshot vào regime. Priority rules giữ các trạng thái cực trị có ý nghĩa kinh tế như liquidity drought, momentum toxic, volatile illiquid. Phần residual được chia thành balanced transition và mild liquidity stress nếu có cấu trúc đủ rõ.

Mục tiêu không phải giảm `UNKNOWN` bằng mọi giá. Mục tiêu là giảm UNKNOWN trong khi vẫn giữ interpretability.

### Bước 5: Tạo split train/valid/test

Chia chronological:

- Train: fit model, scaler, threshold, regime quantile.
- Valid: tune threshold/policy.
- Test: chỉ dùng để báo cáo kết quả cuối.

Không dùng test để chọn threshold hoặc chọn policy chính.

### Bước 6: Train forecasting baselines

Baseline chính:

- SGD/logistic-style tabular model.
- XGBoost GPU trên RTX 3090.
- TCN stride-1 để kiểm tra temporal forecasting fairness.

Baseline deep LOB canonical/pilot:

- DeepLOB-style CNN-LSTM, tương thích input `[batch, 100, 40]`, tham khảo hướng kiến trúc DeepLOB/LOBFrame nhưng cài native PyTorch trong repo.
- Lightweight LOB-Transformer, dùng convolutional stem và temporal attention để kiểm tra liệu attention-style model có đáng mở rộng không.

Các deep baseline mới chỉ được đưa vào bảng kết quả chính nếu có artifact generated tương ứng. Nếu chỉ smoke/pilot thì ghi rõ scope, không tự chèn số thủ công.

Đánh giá forecasting bằng accuracy, macro-F1, MCC, balanced accuracy. Quan trọng là báo cáo cả overall và by-regime.

### Bước 7: Chuyển forecast sang execution

Dự báo xác suất `UP/FLAT/DOWN` được biến thành action:

- Mua nếu xác suất/edge đủ mạnh.
- Bán nếu xác suất/edge đủ âm.
- Không trade nếu tín hiệu yếu.

Sau đó chạy market-order replay simulator trên snapshot L2:

- Sweep depth để tính fill price.
- Tính phí.
- Tính slippage.
- Có latency theo số event.
- Có partial fill rule.

### Bước 8: Tune policy trên validation

Tune threshold chỉ trên validation:

- Naive threshold.
- Cost-aware threshold.
- RSEP threshold.

Ý nghĩa của bước này là chọn "mức khó tính" của policy trước khi nhìn test. Forecasting model cho ra xác suất hoặc edge liên tục, nhưng policy cần quyết định có trade hay không. Nếu threshold quá thấp, policy trade quá nhiều và phí ăn hết edge. Nếu threshold quá cao, policy bỏ qua gần hết cơ hội. Validation split đóng vai trò như khu vực thử tham số công bằng: dùng để chọn threshold, sau đó khóa lại và chỉ báo cáo kết quả cuối trên test.

#### Naive threshold

Naive threshold chỉ nhìn xác suất dự báo.

Ví dụ:

```text
Nếu prob_up > theta_naive  -> BUY
Nếu prob_down > theta_naive -> SELL
Ngược lại                  -> NO-TRADE
```

Giả sử thử các threshold trên validation:

| `theta_naive` | Số trade | Validation net PnL | Diễn giải |
|---:|---:|---:|---|
| `0.50` | rất nhiều | rất âm | trade quá dễ, phí ăn nhiều |
| `0.60` | vừa phải | ít âm hơn | cân bằng hơn |
| `0.80` | rất ít | không ổn định | bỏ qua quá nhiều tín hiệu |

Nếu validation cho thấy `theta_naive = 0.60` ít tệ nhất và có đủ số ngày giao dịch, thì khóa `0.60`, sau đó mới chạy test.

Điểm yếu của naive threshold: nó không biết spread, fee, depth hay regime hiện tại. `prob_up = 0.58` trong thị trường thanh khoản tốt và `prob_up = 0.58` trong liquidity drought bị xử lý gần như giống nhau.

#### Cost-aware threshold

Cost-aware threshold không chỉ hỏi "xác suất UP/DOWN có cao không", mà hỏi "expected edge có vượt cost không".

Trực quan:

```text
edge = lợi nhuận kỳ vọng từ xác suất forecast
cost = spread + fee + cost buffer

BUY  nếu edge > cost + theta_cost
SELL nếu edge < -(cost + theta_cost)
NO-TRADE nếu edge chưa đủ vượt cost
```

Ví dụ:

```text
expected_edge = 1.3 bps
estimated_cost = 0.9 bps
theta_cost = 0.2 bps
required_edge = 1.1 bps
```

Vì `1.3 bps > 1.1 bps`, cost-aware policy có thể cho phép `BUY`.

Nhưng nếu:

```text
expected_edge = 1.0 bps
estimated_cost = 0.9 bps
theta_cost = 0.2 bps
required_edge = 1.1 bps
```

Thì policy chọn `NO-TRADE`, dù dự báo có vẻ đúng hướng. Lý do là edge chưa đủ dày để bù cost.

#### RSEP threshold

RSEP threshold còn khó tính hơn cost-aware threshold. Nó cộng thêm các risk buffer:

```text
required_edge =
    estimated_cost
  + latency_risk_penalty
  + liquidity_risk_penalty
  + adverse_selection_penalty
  + regime_risk_penalty
  + theta_edge
```

Ví dụ:

```text
expected_edge = 1.6 bps
estimated_cost = 0.8 bps
latency penalty = 0.2 bps
liquidity penalty = 0.2 bps
adverse penalty = 0.1 bps
regime penalty = 0.2 bps
theta_edge = 0.1 bps
required_edge = 1.6 bps
```

Trường hợp này vừa đủ sát ngưỡng. Nếu implement rule dùng điều kiện strict `expected_edge > required_edge`, RSEP vẫn có thể chọn `NO-TRADE`. Nếu expected edge tăng lên `1.8 bps`, RSEP mới cho `BUY`.

Điểm quan trọng: RSEP threshold không chỉ lọc theo độ tự tin của model, mà lọc theo "độ dày của edge sau khi trừ rủi ro execution".

#### Vì sao không tune trên test

Nếu dùng test để chọn threshold, kết quả test không còn là kiểm tra độc lập nữa. Khi đó paper dễ bị reviewer xem là overfit vào giai đoạn test.

Happy path đúng là:

```text
Train split:
  fit forecasting model, scaler, class return means

Validation split:
  thử nhiều threshold
  chọn threshold theo validation objective

Test split:
  dùng threshold đã khóa
  báo cáo kết quả cuối
```

Ví dụ dễ hiểu: validation giống đề thi thử để chọn chiến thuật làm bài; test là đề thi thật. Nếu xem đáp án test trước rồi mới chọn chiến thuật, kết quả không còn đáng tin.

### Bước 9: RSEP, ablation, stress và bootstrap

Chạy RSEP full và các ablation:

- Bỏ latency risk.
- Bỏ liquidity risk.
- Bỏ adverse risk.
- Bỏ regime penalty.
- Bỏ cost gate.

Chạy stress:

- Fee tăng.
- Latency tăng.
- Spread multiplier tăng.
- Depth multiplier giảm.

Chạy day-level bootstrap để so sánh RSEP với baseline mạnh nhất theo đơn vị ngày, tránh kết luận dựa trên từng trade/snapshot phụ thuộc nhau.

### Bước 10: Report pack và audit khoa học

Sinh bảng/figure cho paper:

- Data stats.
- Regime distribution.
- Forecasting by-regime.
- Forecast-to-execution.
- Robust policy.
- Ablation.
- Stress curves.
- Failure case studies.

Sau mỗi stage phải có audit tiếng Việt: kết quả có gì mạnh, yếu ở đâu, có đủ chuẩn ICDM không, bước tiếp theo là gì.

## 7. Ví dụ minh họa trực quan

### Ví dụ 1: Dự báo đúng nhưng vẫn lỗ

Giả sử model dự báo giá sẽ tăng rất ngắn hạn. Giá thật sự tăng nhẹ, nên về forecasting có thể xem là đúng. Nhưng khi trade:

- Mua phải trả ask.
- Bán ra phải nhận bid.
- Phải trả fee hai chiều.
- Có thể bị latency làm entry xấu hơn.

Nếu lợi nhuận gross là `+0.8 bps` nhưng tổng cost là `1.2 bps`, trade đó net âm. Đây là lý do paper nhấn mạnh forecast-to-execution degradation.

### Ví dụ 2: Cùng một model, regime khác nhau cho kết quả khác nhau

Trong regime `CALM_LIQUID`, spread hẹp và depth tốt, dự báo nhỏ có thể còn usable.

Trong regime `CHOPPY_MEAN_REVERTING`, giá đảo chiều liên tục, tín hiệu direction dễ bị nhiễu.

Trong regime `LIQUIDITY_DROUGHT`, model có thể dự báo đúng hướng nhưng market order bị slippage hoặc fill kém.

Nếu chỉ nhìn average metric, ta có thể không thấy model đang thất bại ở một số regime quan trọng.

### Ví dụ 3: RSEP bỏ qua tín hiệu yếu

Naive policy có thể trade khi `prob_up > 0.55`. Điều này dễ tạo nhiều trade.

RSEP hỏi thêm:

- Expected edge có đủ lớn không?
- Spread và fee có ăn hết edge không?
- Liquidity risk có cao không?
- Adverse-selection risk có cao không?
- Regime hiện tại có đáng bị phạt không?

Nếu câu trả lời xấu, RSEP không trade. Vì vậy RSEP thường giảm trade count và giảm tổn thất, thay vì cố giao dịch mọi tín hiệu yếu.

### Ví dụ 4: TCN dự báo tốt hơn nhưng execution không tốt hơn

Temporal model như TCN nhìn một cửa sổ nhiều snapshot liên tiếp, nên có thể học được pattern động mà tabular model bỏ lỡ. Vì vậy TCN có thể cải thiện macro-F1 hoặc balanced accuracy trên forecasting.

Nhưng execution lại hỏi một câu khác: các dự báo đúng đó có xuất hiện ở nơi có thể trade được không?

Ví dụ dễ hiểu:

```text
TCN dự báo đúng hơn ở nhiều đoạn thị trường nhiễu.
Nhưng các đoạn đó có spread rộng, depth mỏng hoặc giá đảo chiều nhanh.
Forecasting metric tăng.
Execution net PnL không tăng, thậm chí RSEP không thắng cost-aware baseline.
```

Điều này không làm TCN trở nên vô dụng. Nó cho thấy temporal signal có ích cho forecasting, nhưng muốn biến thành execution edge thì còn phải vượt qua cost, latency, liquidity và regime risk. Đây là negative evidence quan trọng cho paper: **model mạnh hơn về ML metric chưa chắc mạnh hơn về robust execution**.

### Ví dụ 5: RSEP bỏ qua trade trong liquidity drought dù xác suất UP cao

Giả sử model nói `UP` khá tự tin, nhưng order book đang trong trạng thái `LIQUIDITY_DROUGHT`:

```text
prob_up cao
spread rộng
depth top levels mỏng
liquidity risk cao
adverse-selection risk cao
```

Naive policy có thể vẫn mua vì chỉ nhìn xác suất. RSEP thì cộng thêm liquidity penalty và regime penalty. Nếu required edge sau penalty lớn hơn expected edge, RSEP chọn `NO-TRADE`.

Thông điệp cho domain expert: RSEP không cố đoán giá giỏi hơn model. Nó kiểm tra xem tín hiệu dự báo có đủ "dày" để chịu điều kiện thị trường hiện tại hay không.

## 8. Hiện trạng thí nghiệm hiện tại

### Stage 2: BTC Jan-Jun 2024

Stage 2 đã hoàn tất end-to-end trên BTC-USDT Jan-Jun 2024:

- Tổng feature/label rows: `69,532,240`.
- Split test: `13,906,448` rows.
- Taxonomy refined pass gate:
  - `UNKNOWN overall = 13.37%`.
  - p90 daily UNKNOWN khoảng `15.60%`.
- SGD forecasting:
  - accuracy `0.6985`.
  - macro-F1 `0.4557`.
  - MCC `0.2503`.
  - balanced accuracy `0.4413`.

Kết quả execution Stage 2 ban đầu cho thấy gross edge có tồn tại nhưng net PnL âm sau cost. Đây là evidence chính cho forecast-to-execution degradation.

### Stage 2.5: hardening policy và model

Stage 2.5 đã sửa điểm yếu cost-aware baseline bằng validation-only tuning.

Kết quả đáng chú ý:

- SGD tuned RSEP test net PnL cải thiện từ `-4,042.46` xuống `-1,898.19`.
- SGD tuned RSEP vẫn âm ở fee `1 bps`, nên không claim sinh lời.
- XGBoost GPU chạy được trên RTX 3090:
  - accuracy `0.7033`, cao hơn SGD một chút.
  - macro-F1 `0.4440`, thấp hơn SGD.
  - MCC `0.2449`, thấp hơn SGD.
- XGBoost cost-aware tuned có test net PnL tốt nhất trong bảng hiện tại (`-1,045.75`), nhưng không nên chọn model chính chỉ vì test tốt nếu validation/forecasting không ủng hộ rõ.

Diễn giải hiện tại: SGD tuned là baseline kỷ luật hơn để mang sang Stage 3. XGBoost GPU nên được giữ như baseline phụ nếu tài nguyên cho phép.

### Stage 3: full-year BTC 2024

Stage 3 full-year BTC 2024 đã hoàn tất theo pipeline `audit -> feature/label -> regime -> split -> SGD forecast -> tuned execution/RSEP/stress/report`.

- BTC-USDT full 2024 có `167,753,156` snapshots.
- Có `12` raw monthly files.
- Stage 3 được cấu hình partition 10 ngày, tổng `37` partitions.
- Feature/label/prediction scale: `167,751,306` rows.
- Split chronological:
  - train `100,650,783` rows.
  - valid `33,550,261` rows.
  - test `33,550,262` rows.

Taxonomy refined vẫn pass trên full-year:

- `UNKNOWN overall = 13.19%`.
- daily p90 UNKNOWN khoảng `15.43%`.
- `BALANCED_TRANSITION = 21.26%`.
- `MILD_LIQUIDITY_STRESS = 16.34%`.

SGD full-year:

- accuracy `0.5589`.
- macro-F1 `0.4652`.
- MCC `0.2363`.
- balanced accuracy `0.4637`.

Execution full-year cho thấy forecast-to-execution degradation rất rõ:

- Default `naive_threshold`: net PnL `-364,583.25`.
- Default `cost_aware_threshold`: net PnL `-673,650.57`.
- Tuned `sgd_stage3_RSEP-full`: gross PnL `+2,300.82`, net PnL `-4,437.49` ở fee `1 bps`.
- Fee stress cho thấy ở `0 bps` RSEP tuned dương `+2,300.82`, nhưng chỉ cần `1 bps` đã âm `-4,437.49`.

Stage 3.6 đã mở thêm XGBoost GPU full-year trên RTX 3090 mà không rebuild feature/regime/split:

- XGBoost accuracy `0.5677`, cao hơn SGD `0.5589`.
- XGBoost macro-F1 `0.4562`, thấp hơn SGD `0.4652`.
- MCC gần như ngang: XGBoost `0.23637`, SGD `0.23633`.
- Tuned `xgboost_gpu_stage3_RSEP-full`: gross PnL `+2,953.00`, net PnL `-4,303.19` ở fee `1 bps`.
- XGBoost giảm net loss nhẹ so với SGD tuned RSEP, nhưng naive threshold overtrade rất mạnh (`880,927` trades, net PnL `-115,238.26`).

Diễn giải hiện tại: Stage 3 củng cố rất mạnh narrative của paper. Forecasting có tín hiệu và taxonomy ổn định hơn, nhưng edge execution rất mỏng và dễ bị cost phá. XGBoost là strong tabular baseline phụ: accuracy cao hơn và execution RSEP nhỉnh hơn nhẹ, nhưng macro-F1/balanced accuracy không vượt SGD nên chưa nên thay SGD làm narrative chính. RSEP có vai trò giảm thiệt hại/giảm exposure, không phải chứng minh profitability.

Ghi chú reproducibility: Stage 3.5 đã chuẩn hóa naming theo stage/model. Stage 3.7 tiếp tục gom bảng và hình so sánh trực tiếp SGD với XGBoost dưới stress để paper assets không phụ thuộc vào model vừa chạy gần nhất.

### Stage 3.10 và Stage 3.11: fairness cho temporal baseline và khóa evidence paper

Stage 3.10 đã chạy TCN stride-1 để giảm rủi ro so sánh không công bằng giữa temporal model và tabular full-year baseline. Kết quả quan trọng không phải là "TCN thắng trading", mà là một negative evidence có giá trị:

- TCN stride-1 có macro-F1 cao hơn nhóm tabular, cho thấy temporal information có ích cho forecasting.
- MCC của TCN vẫn thấp hơn hoặc không vượt rõ SGD/XGBoost, nên cải thiện không đồng đều theo metric.
- Khi đưa qua execution, RSEP không thắng cost-aware trên TCN stride-1; bootstrap day-level có CI giao qua 0.
- Điều này củng cố thesis chính: metric forecasting tốt hơn không tự động chuyển thành edge execution tốt hơn.

Stage 3.11 vì vậy chuyển trọng tâm sang evidence hardening cho paper:

- tạo acceptance bar theo tiêu chí trong `TongQuan.md`;
- tạo claim-support matrix để claim nào có bằng chứng thì giữ, claim nào chỉ partial thì hạ giọng, và claim nào không được phép như profitability/live trading thì ghi rõ;
- chọn vai trò công bằng cho từng model: SGD làm baseline tabular chính, XGBoost GPU làm strong tabular baseline phụ, TCN stride-1 làm temporal fairness baseline/negative evidence;
- giữ định vị paper là benchmark/failure-analysis + robust selective execution, không phải profitability hoặc live trading.

### Stage 3.12: cách đọc evidence hiện tại cho paper

Stage 3.12 đã khóa paper draft pack và number consistency. Cách đọc kết quả hiện tại:

- Acceptance bar hiện là `7 PASS`, `2 PARTIAL`, `0 BLOCKED`, `0 FAIL`.
- `SUPPORTED`: BTC full-year benchmark, ETH replication/cross-asset evaluation, regime heterogeneity, forecast-to-execution degradation, stress sensitivity.
- `PARTIAL`: RSEP/statistical support, vì TCN stride-1 cho thấy RSEP không thắng cost-aware một cách universal; ETH within-asset vẫn cần đọc như replication/failure-analysis vì net PnL âm.
- `BLOCKED`: không còn tiêu chí bị chặn trong acceptance bar hiện tại.
- `NOT_CLAIMED`: profitability, live trading readiness, exact queue priority.

Khi viết paper, nên dùng các artifact Stage 3.12:

- `paper_outline_stage3_12_vi.md`: khung viết paper theo ICDM.
- `table_13_claim_to_evidence_map.csv`: claim nào được nói, dựa trên bảng/hình nào.
- `table_14_number_consistency_check.csv`: kiểm tra các số chính giữa bảng, audit, narrative và `MoTa.md`.
- `limitation_wording_stage3_12_vi.md`: câu chữ limitation nên dùng và câu chữ không được dùng.

Ví dụ cách dùng claim map:

```text
Nếu viết: "forecasting tốt hơn không đảm bảo execution tốt hơn"
-> phải trích bảng model forecasting/execution comparison.

Nếu muốn viết: "đã có BTC<->ETH cross-asset forecasting và execution evaluation"
-> được viết nếu trích bảng cross-asset Stage 3.13.

Nếu muốn viết: "policy generalize có lợi nhuận qua BTC và ETH"
-> không được viết, vì net PnL vẫn âm và simulator không phải live trading.
```

### Stage 3.13: cross-asset evidence lock

Stage 3.13 đã khóa thêm evidence BTC<->ETH. Điểm quan trọng là cross-asset không còn chỉ là kế hoạch hoặc limitation; nó đã được evaluate bằng forecasting, target-asset execution, RSEP, stress và day-level bootstrap.

| Hướng | Macro-F1 | MCC | Cost-aware net PnL | RSEP net PnL | Bootstrap RSEP - cost-aware |
|---|---:|---:|---:|---:|---:|
| BTC -> ETH | `0.4325` | `0.1486` | `-287,991.44` | `-74,466.38` | CI [`3,314.02`, `4,048.20`] |
| ETH -> BTC | `0.4839` | `0.2424` | `-3,697.46` | `-1,144.75` | CI [`34.08`, `44.53`] |

Cách đọc đúng:

- Forecasting asset-held-out không collapse ở cả hai hướng.
- RSEP giảm thiệt hại rõ so với cost-aware threshold ở cả hai hướng.
- Net PnL vẫn âm, nên đây không phải bằng chứng trading profitability.
- Claim paper nên là: **cross-asset forecasting/execution was evaluated under source-validation-only tuning, and selective execution mitigates degradation but does not create universal profitability**.

## 9. Cách nên định vị paper trong phần viết

Nên viết:

- "Chúng tôi giới thiệu benchmark và evaluation protocol cho robust HFT policy learning dưới L2 microstructure regime shifts."
- "Kết quả cho thấy average forecasting/backtest che giấu forecast-to-execution degradation."
- "RSEP là robust selective execution baseline giúp giảm exposure và giảm tổn thất trong điều kiện stress."
- "Các kết quả được kiểm tra bằng by-regime diagnostics, stress grid, ablation và day-level bootstrap."
- "BTC<->ETH cross-asset forecasting và execution đã được đánh giá bằng source-validation-only tuning."

Không nên viết:

- "Model tạo profit ổn định."
- "Policy sẵn sàng live trading."
- "Simulator tái hiện chính xác queue priority."
- "Dữ liệu tương đương event-level LOBSTER."
- "RSEP là SOTA trading strategy."
- "Cross-asset policy tạo lợi nhuận ổn định hoặc generalize universal qua mọi asset."

## 10. Checklist để domain expert review

### Regime taxonomy

- Các regime hiện tại có phản ánh đúng intuition thị trường crypto không?
- `BALANCED_TRANSITION` và `MILD_LIQUIDITY_STRESS` có thật sự khác nghĩa không?
- `VOLATILE_LIQUID` quá hiếm thì nên giữ, gom, hay bỏ khỏi bảng chính?
- Regime priority order có hợp lý không, đặc biệt giữa `MOMENTUM_TOXIC`, `VOLATILE_ILLIQUID`, `SHOCK_RECOVERY`?

### Label và feature

- Horizon label hiện tại có hợp lý với snapshot interval và HFT setting không?
- Cost-aware label threshold có quá dễ hoặc quá khó tạo `UP/DOWN` không?
- OFI proxy và adverse-selection proxy từ snapshot L2 có đủ defensible không?
- Có feature nào dễ bị leakage hoặc dùng future information không?

### Simulator và execution

- Market-order replay trên L2 snapshot có đủ hợp lý cho benchmark claim không?
- Fee `1 bps`, latency events, trade notional và cooldown có hợp lý không?
- Partial fill và depth sweep có phản ánh tốt enough execution stress không?
- Stress grid fee/latency/spread/depth nên mở rộng thế nào để thuyết phục reviewer?

### RSEP

- Các risk terms trong RSEP có diễn giải được về mặt market microstructure không?
- Regime penalty có nên learned từ validation hay giữ rule-based?
- RSEP nên được trình bày như policy mới hay như robust baseline?
- Bootstrap theo ngày đã đủ chưa, hay cần block bootstrap theo tuần/tháng?

### Paper claim

- Kết quả net PnL âm nên được trình bày như failure-analysis như thế nào?
- Cần Stage 3 full-year đến mức nào để claim stability?
- Cần ETH/asset-held-out đến mức nào để claim generalization?
- Nếu deep baselines không thắng rõ, paper nên định vị là benchmark/protocol mạnh hay model paper?

## 11. Kết luận ngắn

Paper này có hướng tốt nếu giữ đúng trọng tâm: **không bán câu chuyện trading profit**, mà bán câu chuyện **robust evaluation under microstructure regime shifts**.

Điểm có sức nặng hiện tại là pipeline đã cho thấy:

- Taxonomy regime có coverage ổn từ Stage 2 tới Stage 3 full-year.
- Forecasting có heterogeneity theo regime trên test full-year.
- Forecast-to-execution degradation là rõ và mạnh hơn khi scale full-year.
- Validation-only tuning làm baseline công bằng hơn.
- RSEP giảm thiệt hại nhưng chưa biến strategy thành profitable ở fee `1 bps`.

Stage 3.12 đã khóa thêm paper draft pack và number consistency lock:

- `paper_outline_stage3_12_vi.md` là khung viết paper theo hướng ICDM.
- `table_13_claim_to_evidence_map.csv` nối từng claim với artifact được phép trích.
- `table_14_number_consistency_check.csv` kiểm tra các số chính giữa bảng Stage 3.11, audit, narrative và `MoTa.md`; hiện không có mismatch.
- `limitation_wording_stage3_12_vi.md` ghi rõ cách viết limitation: BTC<->ETH đã được evaluate nhưng không claim profitable/universal policy, snapshot-level simulator, không claim live trading/profitability.
- `cross_asset_narrative_stage3_13_vi.md` và `table_16/17` khóa riêng kết quả cross-asset forecasting/execution/bootstrap.

Để tăng khả năng cạnh tranh tại ICDM 2026, bước quan trọng tiếp theo là viết bản IEEE draft từ outline Stage 3.12 và trích số trực tiếp từ các paper assets đã khóa, bao gồm cross-asset pack Stage 3.13. Sau đó mới nên quyết định mở thêm mixed BTC+ETH hoặc baseline GPU mới nếu paper draft cho thấy reviewer thật sự cần.
