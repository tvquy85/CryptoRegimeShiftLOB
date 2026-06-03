# Audit regime refinement v001 - Hybrid taxonomy

## Kết luận gate

- **Gate refine taxonomy: PASS.**
- Taxonomy hybrid mới đã đạt:
  - `UNKNOWN = 12.60%` tổng stage 1, thấp hơn ngưỡng `< 15%`.
  - p90 daily unknown share `14.20%`, thấp hơn ngưỡng `< 25%`.
  - daily max unknown share `16.38%`, không còn tình trạng nửa dữ liệu rơi vào residual mơ hồ như taxonomy cũ.
- Hai regime residual mới có profile feature khác nhau đủ rõ để giữ lại:
  - `BALANCED_TRANSITION`
  - `MILD_LIQUIDITY_STRESS`

## Thay đổi đã thực hiện

- Giữ nguyên priority cực trị:
  - `LIQUIDITY_DROUGHT`
  - `MOMENTUM_TOXIC`
  - `VOLATILE_ILLIQUID`
  - `CHOPPY_MEAN_REVERTING`
  - `SHOCK_RECOVERY`
  - các regime calm/volatile liquid cũ
- Bổ sung score-based residual assignment train-only:
  - `liquidity_score`
  - `stress_score`
  - `directional_toxicity_score`
- Thêm hai regime mới:
  - `BALANCED_TRANSITION`
  - `MILD_LIQUIDITY_STRESS`
- Bổ sung diagnostics:
  - regime share refined;
  - daily unknown share;
  - regime run-length;
  - refined feature medians;
  - residual cluster alignment bằng `KMeans` và `GMM`;
  - scatter/projection figures cho residual map.
- `HDBSCAN` không có sẵn trong môi trường hiện tại; đúng policy project, không cài mới tùy tiện trong vòng này.

## Kết quả taxonomy sau refine

### Phân bố regime

- `BALANCED_TRANSITION`: `20.77%`
- `MOMENTUM_TOXIC`: `17.21%`
- `MILD_LIQUIDITY_STRESS`: `17.00%`
- `UNKNOWN`: `12.60%`
- `SHOCK_RECOVERY`: `10.02%`
- `CHOPPY_MEAN_REVERTING`: `9.81%`
- `CALM_LIQUID`: `7.31%`
- Các extreme/rare regimes còn lại giữ nguyên support so với stage 1 trước refine:
  - `LIQUIDITY_DROUGHT`: `1.66%`
  - `VOLATILE_ILLIQUID`: `1.36%`
  - `VOLATILE_LIQUID`: `0.21%`

### So với taxonomy cũ

- `UNKNOWN` giảm từ `50.37%` xuống `12.60%`.
- Daily unknown share trước refine có median gần `48.75%`; sau refine p90 chỉ còn `14.20%`.
- Đây là cải thiện về **coverage và interpretability**, không phải thay đổi dữ liệu hay label.

## Hai residual regimes có khác biệt thực sự hay không?

### `BALANCED_TRANSITION`

- median `stress_score = -1.36`
- median `liquidity_score = +0.51`
- median `liquidity_drought_score = -0.51`
- median `directional_toxicity_score ≈ -0.07`

Diễn giải:
- trạng thái trung gian nhưng thiên ổn định;
- thanh khoản tương đối tốt;
- không có tín hiệu toxicity mạnh.

### `MILD_LIQUIDITY_STRESS`

- median `stress_score = +0.31`
- median `liquidity_score = -0.82`
- median `liquidity_drought_score = +0.82`
- median `directional_toxicity_score ≈ 0.00`

Diễn giải:
- chưa tới drought extreme;
- nhưng liquidity deteriorate vừa phải đã hiện rõ;
- đây là vùng trung gian mà taxonomy cũ bỏ vào `UNKNOWN`.

### `UNKNOWN` sau refine

- median `stress_score = +0.19`
- median `liquidity_score = -0.20`
- median `directional_toxicity_score = +1.22`

Diễn giải:
- phần còn lại thực sự là vùng pha trộn/conflicted hơn;
- hợp lý khi giữ lại làm fallback thay vì ép gán.

## Diagnostic clustering

- `KMeans`:
  - `BALANCED_TRANSITION` chủ yếu vào cluster `1` (`67.31%` của regime).
  - `MILD_LIQUIDITY_STRESS` chủ yếu vào cluster `0` (`76.16%`).
  - `UNKNOWN` tách giữa cluster `0` và `2`, phù hợp với diễn giải residual mơ hồ.
- `GMM`:
  - `BALANCED_TRANSITION` chủ yếu vào cluster `1` (`76.12%`).
  - `MILD_LIQUIDITY_STRESS` gần như tập trung vào cluster `0` (`99.27%`).
  - `UNKNOWN` vẫn phân tán trên nhiều cụm.

Đánh giá:
- Clustering diagnostic **ủng hộ** việc thêm 2 residual states.
- Nó không chứng minh taxonomy là duy nhất, nhưng cho thấy hai state mới không phải chia ngẫu nhiên.

## Downstream sau taxonomy mới

### Forecasting

- Aggregate forecasting metrics giữ nguyên về bản chất vì data/model/labels không đổi:
  - accuracy `0.594`
  - macro-F1 `0.498`
  - MCC `0.303`
- By-regime view rõ hơn:
  - `BALANCED_TRANSITION` macro-F1 `0.456`
  - `MILD_LIQUIDITY_STRESS` macro-F1 `0.455`
  - `UNKNOWN` macro-F1 `0.484`

### RSEP / execution

- Aggregate RSEP-full **không đổi**:
  - net PnL `-76.19`
  - bootstrap vs cost-aware threshold vẫn `+491.31` mean daily diff, CI `[+214.65, +794.02]`
- By-regime decomposition dễ đọc hơn:
  - `BALANCED_TRANSITION`: net `-29.84`
  - `MILD_LIQUIDITY_STRESS`: net `-3.61`
  - `UNKNOWN`: net `-7.22`
- `worst_regime_return` trong bảng RSEP thay đổi từ khoảng `-40.68` ở taxonomy cũ sang `-29.84` ở taxonomy mới vì **định nghĩa bucket regime đã hợp lý hơn**, không phải vì policy cải thiện aggregate.

## Góc nhìn Principal ML Scientist

- Refine lần này giải đúng vấn đề cốt lõi của stage 1:
  - giảm coverage hole lớn;
  - không phá các extreme regimes có ý nghĩa kinh tế;
  - residual states có profile feature và clustering support hợp lý.
- Đây là cải thiện methodology thật, không phải cosmetic relabeling.
- Tuy nhiên, score thresholds vẫn là heuristic train-fitted; cần kiểm tra stability ở stage 2 và khi có ETH.

## Góc nhìn Reviewer ICDM

- Điểm mạnh:
  - Taxonomy giờ có coverage tốt hơn, giảm rõ nguy cơ reviewer phê bình “nửa dữ liệu bị bỏ ngoài mô hình”.
  - Residual states được hỗ trợ bằng cả feature diagnostics lẫn unsupervised alignment.
  - Claims vẫn kỷ luật: không nói clustering xác nhận tuyệt đối taxonomy.
- Điểm còn yếu:
  - `VOLATILE_LIQUID` vẫn cực hiếm (`0.21%`), có thể không đủ mạnh cho regime-held-out nếu giữ nguyên.
  - `HDBSCAN` chưa chạy; hiện mới có `KMeans/GMM`.
  - Cần kiểm tra taxonomy stability trên stage 2 dài hơn và trên asset khác.

## Quyết định tiếp theo

- **Được phép mở stage 2 taxonomy evaluation trên BTC 6 tháng**, với điều kiện:
  - giữ nguyên audit chặt;
  - theo dõi xem `UNKNOWN` có tiếp tục < `15%` không;
  - kiểm tra residual states có ổn định theo tháng hay không.
- **Chưa nên dùng taxonomy này để claim final-paper một cách tuyệt đối** cho tới khi:
  - stage 2 BTC ổn;
  - tốt nhất có thêm ETH hoặc một asset-held-out check.

## Artifact chính

- `outputs/tables/table_regime_share_refined.csv`
- `outputs/tables/table_unknown_daily_share_refined.csv`
- `outputs/tables/table_regime_run_lengths_refined.csv`
- `outputs/tables/table_regime_feature_medians_refined.csv`
- `outputs/tables/table_residual_cluster_alignment.csv`
- `outputs/figures/regime_transition_map_refined.png`
- `outputs/figures/residual_cluster_projection.png`

