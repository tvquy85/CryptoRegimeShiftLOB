# supplementaryartifact_guide.md

## Hướng dẫn xây dựng Supplementary Artifact cho paper ICDM 2026 Applied Track

**Paper:** `CryptoRegimeShift-LOB: A Crypto Level-2 Benchmark for Auditing Forecast-to-Execution Degradation`  
**Mục tiêu:** tạo một supplementary artifact đủ mạnh để bảo vệ claim “artifact-backed applied benchmark” trong review ICDM Applied Track, đặc biệt với rủi ro raw Crypto Lake data là dữ liệu thương mại không thể redistribute.

---

## 0. Bối cảnh và nguyên tắc bắt buộc

Paper hiện claim một benchmark/protocol cho **forecast-to-execution degradation** trên dữ liệu Level-2 crypto order book BTC-USDT và ETH-USDT năm 2024. Điểm mạnh của paper là không claim trading profitability, mà claim một protocol audit từ prediction sang execution dưới các yếu tố spread, fee, latency, visible-depth, regime, stress test, bootstrap và cross-asset transfer.

Điểm dễ bị reviewer đánh nhất là **reproducibility**: raw Crypto Lake snapshots là dữ liệu có license, không được công khai. Vì vậy artifact phải được thiết kế theo hai lớp:

1. **Public audit layer:** chạy được không cần dữ liệu thương mại, dùng synthetic 20-level L2 sample để kiểm tra schema, pipeline, labels, regimes, replay, stress, bootstrap, transfer, checksum và table verifier.
2. **Licensed full reproduction layer:** nếu người dùng có raw Crypto Lake data đúng license, họ có thể đặt data vào đúng thư mục và chạy lại toàn bộ pipeline để reproduce các table/figure chính trong paper.

Tuyệt đối không được đưa raw commercial data, private key, credential, token, hoặc file có thể vi phạm license vào supplementary artifact.

---

## 1. Definition of Done

Codex chỉ được xem là hoàn thành khi artifact đạt tất cả tiêu chí sau:

### 1.1. Chạy được không cần raw data thương mại

- Có synthetic L2 sample nhỏ nhưng đúng schema 20 levels mỗi bên.
- Có lệnh chạy end-to-end trên synthetic sample trong dưới 5 phút CPU.
- Synthetic run phải tạo được:
  - features,
  - cost-aware ternary labels,
  - regime tags,
  - chronological purged splits,
  - baseline dummy/SGD-small predictions,
  - visible-depth replay,
  - stress test,
  - bootstrap confidence intervals,
  - transfer diagnostic placeholder,
  - artifact manifest,
  - checksum report.

### 1.2. Có đường dẫn reproduce đầy đủ nếu có licensed data

- Có README chỉ rõ người dùng đặt Crypto Lake raw snapshots vào đâu.
- Có script validate schema raw data.
- Có config cho BTC-USDT và ETH-USDT full-year 2024.
- Có lệnh chạy full pipeline bằng `make full` hoặc `python -m cryptolob_artifact.pipeline ...`.
- Nếu raw data không tồn tại, script phải fail rõ ràng với thông báo license/data path, không silently tạo kết quả giả.

### 1.3. Có mapping paper claim → artifact evidence

Phải có file `CLAIM_EVIDENCE_MAP.md` và `artifacts/claim_evidence_map.csv`, mapping từng claim trong paper sang:

- section/table/figure trong paper,
- script tạo kết quả,
- config dùng,
- input file,
- output file,
- checksum,
- full-data status,
- synthetic status,
- reproduction limitation.

### 1.4. Có verifier cho bảng/figure chính

Phải có script `scripts/09_verify_paper_tables.py` hoặc tương đương để kiểm tra các artifact CSV có đủ cột và đủ metric để support các table/figure chính:

- dataset summary,
- split summary,
- baseline coverage,
- prediction metrics,
- replay results,
- RSEP diagnostic results,
- stress tests,
- bootstrap uncertainty,
- BTC↔ETH transfer,
- claim-to-evidence map.

Nếu chưa có full data outputs, verifier vẫn phải chạy trên synthetic outputs và ghi rõ `FULL_DATA_NOT_AVAILABLE`.

### 1.5. Không hallucinate kết quả

- Không được tự tạo số liệu full-year 2024 nếu không có raw data hoặc outputs thật.
- Không được ghi “reproduces all paper tables” nếu chỉ mới synthetic run.
- Không được fake checksum.
- Không được fake `main_results.csv` từ paper PDF.
- Nếu chỉ có synthetic smoke test, phải ghi rõ là “pipeline verification only”.

---

## 2. Cấu trúc thư mục artifact cần tạo

Codex cần tạo thư mục `supplementary_artifact/` theo cấu trúc sau:

```text
supplementary_artifact/
  README.md
  DATA_CARD.md
  SCHEMA.md
  LICENSE_AND_DATA_ACCESS.md
  REPRODUCIBILITY_CHECKLIST.md
  CLAIM_EVIDENCE_MAP.md
  ENVIRONMENT.md
  CITATION.cff
  VERSION
  requirements.txt
  pyproject.toml                  # nếu repo dùng package structure
  Makefile
  configs/
    synthetic.yaml
    btc_usdt_2024.yaml
    eth_usdt_2024.yaml
    replay_defaults.yaml
    stress_defaults.yaml
    bootstrap_defaults.yaml
    transfer_defaults.yaml
  data/
    README.md
    synthetic/
      raw/
        book_snapshots.parquet
      expected_outputs/
        schema_report.json
        feature_summary.csv
        label_summary.csv
        regime_summary.csv
        split_manifest.csv
        replay_summary.csv
        stress_summary.csv
        bootstrap_summary.csv
        transfer_summary.csv
    external/
      README_LICENSED_CRYPTOLAKE_DATA.md
      .gitkeep
  src/
    cryptolob_artifact/
      __init__.py
      io.py
      schema.py
      features.py
      labels.py
      regimes.py
      splits.py
      baselines.py
      replay.py
      rsep.py
      stress.py
      bootstrap.py
      transfer.py
      metrics.py
      manifest.py
      utils.py
  scripts/
    00_make_synthetic_l2_sample.py
    01_validate_schema.py
    02_build_features.py
    03_make_labels_regimes_splits.py
    04_train_or_load_baselines.py
    05_run_visible_depth_replay.py
    06_run_rsep_diagnostic.py
    07_run_stress_tests.py
    08_run_bootstrap_and_transfer.py
    09_verify_paper_tables.py
    10_make_artifact_manifest.py
    run_synthetic_end_to_end.sh
    run_full_reproduction.sh
  artifacts/
    synthetic/
      manifest.json
      checksums.sha256
      logs/
      tables/
      figures/
    full_reproduction_placeholder/
      README.md
  tests/
    test_schema.py
    test_no_leakage_splits.py
    test_labels.py
    test_replay_accounting.py
    test_rsep_rules.py
    test_manifest_checksums.py
  docs/
    reviewer_quickstart.md
    troubleshooting.md
    expected_runtime.md
```

---

## 3. README.md bắt buộc viết như thế nào

File `README.md` phải giúp reviewer chạy được trong 3 mức.

### 3.1. Reviewer Quickstart, không cần commercial data

Nội dung bắt buộc:

```bash
cd supplementary_artifact
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
make synthetic
make verify
```

Expected output:

```text
[OK] synthetic L2 sample generated
[OK] schema validation passed
[OK] time-causal features built
[OK] cost-aware labels generated
[OK] regimes assigned
[OK] purged chronological splits created
[OK] visible-depth replay completed
[OK] stress tests completed
[OK] bootstrap diagnostics completed
[OK] claim-evidence manifest generated
[OK] paper table verifier completed on synthetic mode
```

### 3.2. Full reproduction, cần licensed Crypto Lake data

Nội dung bắt buộc:

```bash
# Put licensed Crypto Lake data here:
# data/external/cryptolake/BTC-USDT/book/2024/*.parquet
# data/external/cryptolake/ETH-USDT/book/2024/*.parquet

make validate-full-data
make full
make verify-full
```

Nếu data thiếu, command phải báo:

```text
[ERROR] Licensed Crypto Lake raw snapshots not found.
Full numerical reproduction requires licensed raw data.
Run `make synthetic` for public pipeline verification.
```

### 3.3. Reviewer interpretation boundary

README phải ghi rõ:

```text
This public artifact supports method-surface audit and pipeline verification without redistributing commercial raw data. Full numerical reproduction of the paper tables requires licensed access to Crypto Lake Level-2 snapshots. Synthetic outputs are not evidence for the reported empirical results; they only verify that the pipeline, schema, accounting, and claim-to-evidence mapping are executable.
```

---

## 4. DATA_CARD.md

`DATA_CARD.md` phải trả lời ngắn gọn nhưng đầy đủ:

### 4.1. Dataset identity

- Dataset name: CryptoRegimeShift-LOB.
- Assets: BTC-USDT, ETH-USDT.
- Venue/source: Crypto Lake licensed Level-2 order book snapshots.
- Period: full-year 2024.
- Raw data redistribution: not allowed unless license permits.
- Public sample: deterministic synthetic 20-level L2 sample.

### 4.2. What is public vs licensed

Tạo bảng:

| Component | Public in artifact | Requires Crypto Lake license | Purpose |
|---|---:|---:|---|
| Code | Yes | No | Pipeline reproduction |
| Configs | Yes | No | Exact protocol definition |
| Synthetic 20-level L2 sample | Yes | No | Smoke test and method-surface audit |
| Raw BTC/ETH 2024 snapshots | No | Yes | Full numerical reproduction |
| Split manifests/checksum templates | Yes | Full values require data | Audit chronological construction |
| Paper table verifier | Yes | Full table values require data | Claim-to-evidence validation |

### 4.3. Known limitations

- No hidden liquidity.
- No queue priority.
- No passive fill model.
- Market-order visible-depth approximation only.
- No claim of live trading profitability.
- Full-year numeric reproduction depends on raw data license.

---

## 5. SCHEMA.md

`SCHEMA.md` phải định nghĩa chính xác input columns. Tối thiểu cần:

```text
timestamp_ns or timestamp
asset
exchange or venue
bid_px_1 ... bid_px_20
bid_sz_1 ... bid_sz_20
ask_px_1 ... ask_px_20
ask_sz_1 ... ask_sz_20
```

Nếu raw data của Crypto Lake dùng tên khác, phải có mapping trong `configs/*yaml`, ví dụ:

```yaml
column_mapping:
  received_time: timestamp
  bid_0_price: bid_px_1
  bid_0_size: bid_sz_1
  ask_0_price: ask_px_1
  ask_0_size: ask_sz_1
```

Schema validation phải kiểm tra:

- timestamp monotonic trong từng asset/day,
- bid price giảm dần theo depth,
- ask price tăng dần theo depth,
- best bid < best ask,
- size không âm,
- không có duplicate timestamp nghiêm trọng,
- đủ 20 levels mỗi bên,
- timezone/UTC được ghi rõ.

Output `schema_report.json` cần có:

```json
{
  "asset": "BTC-USDT",
  "rows": 12345,
  "start_time": "...",
  "end_time": "...",
  "levels_per_side": 20,
  "checks": {
    "best_bid_less_than_best_ask": "PASS",
    "bid_depth_monotonic": "PASS",
    "ask_depth_monotonic": "PASS",
    "non_negative_size": "PASS"
  }
}
```

---

## 6. Pipeline scripts cần triển khai

### 6.1. `00_make_synthetic_l2_sample.py`

Mục tiêu: tạo deterministic synthetic L2 sample đúng schema để reviewer chạy được.

Yêu cầu:

- Seed cố định: `seed=20260606`.
- Tạo ít nhất 2 assets: `BTC-USDT`, `ETH-USDT`.
- Tạo ít nhất 2 ngày dữ liệu synthetic.
- Có 20 bid levels và 20 ask levels.
- Có biến động spread, depth, volatility để regime assignment không toàn một class.
- Có một vài edge cases nhỏ nhưng hợp lệ: spread mở rộng, depth giảm, volatility tăng.
- Không tạo data phi lý: bid >= ask, size âm, timestamp đảo.

Output:

```text
data/synthetic/raw/book_snapshots.parquet
```

### 6.2. `01_validate_schema.py`

Input:

```bash
python scripts/01_validate_schema.py --config configs/synthetic.yaml
```

Output:

```text
artifacts/synthetic/schema_report.json
artifacts/synthetic/logs/01_validate_schema.log
```

Fail nếu:

- thiếu cột,
- bid/ask invalid,
- timestamp không parse được,
- levels không đủ.

### 6.3. `02_build_features.py`

Tạo time-causal features. Không dùng future data.

Feature tối thiểu:

- midprice,
- spread,
- relative spread,
- top-k imbalance,
- depth imbalance,
- microprice,
- short-horizon realized volatility dùng past window,
- rolling volume/depth dùng past window,
- return lag features.

Bắt buộc có test chống leakage:

- rolling windows chỉ dùng `shift(1)` hoặc strictly past data nếu cần.
- không dùng future midprice trong features.

Output:

```text
artifacts/synthetic/features.parquet
artifacts/synthetic/tables/feature_summary.csv
```

### 6.4. `03_make_labels_regimes_splits.py`

Tạo labels, regimes và splits.

Labels:

- future mid-price return horizon theo config.
- cost-aware ternary labels: `BUY`, `SELL`, `ABSTAIN/HOLD` hoặc `UP`, `DOWN`, `FLAT`.
- threshold dựa trên local spread và fee proxy.

Regimes:

- volatility regime,
- spread regime,
- depth/liquidity regime,
- imbalance regime,
- combined microstructure regime nếu paper dùng.

Splits:

- chronological split.
- purging/embargo giữa train/validation/test.
- không random shuffle.

Output:

```text
artifacts/synthetic/labels.parquet
artifacts/synthetic/regimes.parquet
artifacts/synthetic/split_manifest.csv
artifacts/synthetic/tables/label_summary.csv
artifacts/synthetic/tables/regime_summary.csv
```

### 6.5. `04_train_or_load_baselines.py`

Public synthetic run không cần train nặng. Cần tạo baseline tối thiểu để pipeline chạy:

- naive baseline,
- logistic/SGD small,
- optional small XGBoost nếu package có sẵn,
- optional tiny TCN nếu PyTorch có sẵn.

Full reproduction mode:

- load hoặc train baselines theo config.
- save fixed full-test predictions trước replay.
- mọi prediction artifact phải có checksum.

Output:

```text
artifacts/synthetic/predictions/sgd_predictions.parquet
artifacts/synthetic/tables/prediction_metrics.csv
```

Prediction file schema:

```text
asset
timestamp
split
model
pred_label
prob_buy
prob_sell
prob_hold
true_label
midprice
spread
fee_bps
regime
```

### 6.6. `05_run_visible_depth_replay.py`

Mục tiêu: map fixed predictions sang visible-depth replay.

Replay phải ghi rõ:

- market-order approximation,
- no queue priority,
- no hidden liquidity,
- no passive fill,
- visible-depth only,
- fee model,
- spread crossing,
- depth cap,
- latency shift nếu có.

Output:

```text
artifacts/synthetic/replay/replay_trades.parquet
artifacts/synthetic/tables/replay_summary.csv
```

Replay summary columns:

```text
asset
model
policy
n_trades
gross_pnl
fees
net_pnl
mean_trade_pnl
sharpe_like
max_drawdown
turnover
hit_rate
coverage
```

### 6.7. `06_run_rsep_diagnostic.py`

RSEP chỉ là diagnostic gate, không phải trading algorithm.

Script phải implement đúng logic paper:

- expected edge estimate,
- explicit cost term,
- risk penalty,
- abstain rule,
- buy/sell rule,
- no oracle regime information.

Output:

```text
artifacts/synthetic/rsep/rsep_decisions.parquet
artifacts/synthetic/tables/rsep_summary.csv
```

README phải ghi:

```text
RSEP is included to make the diagnostic decision rule reproducible. It is not presented as a deployable trading strategy or a profitability claim.
```

### 6.8. `07_run_stress_tests.py`

Stress axes:

- fee multiplier,
- latency shift,
- spread widening,
- depth haircut.

Output:

```text
artifacts/synthetic/stress/stress_results.csv
artifacts/synthetic/tables/stress_summary.csv
artifacts/synthetic/figures/fee_stress.png
artifacts/synthetic/figures/latency_stress.png
```

Stress summary columns:

```text
asset
model
policy
stress_axis
stress_level
net_pnl
relative_degradation
coverage
n_trades
```

### 6.9. `08_run_bootstrap_and_transfer.py`

Bootstrap:

- day-level bootstrap, not row-level bootstrap.
- report confidence intervals for net PnL, Sharpe-like metric, hit rate, coverage.

Transfer:

- BTC→ETH,
- ETH→BTC,
- source validation only,
- no target test tuning.

Output:

```text
artifacts/synthetic/tables/bootstrap_summary.csv
artifacts/synthetic/tables/transfer_summary.csv
```

### 6.10. `09_verify_paper_tables.py`

Verifier phải kiểm tra các artifact có đủ evidence cho paper.

Output:

```text
artifacts/synthetic/verification_report.json
artifacts/synthetic/tables/verification_report.csv
```

Report format:

```json
{
  "mode": "synthetic",
  "full_data_available": false,
  "tables_checked": {
    "Table_I_dataset_summary": "PASS_SCHEMA_ONLY",
    "Table_V_prediction_metrics": "PASS_SYNTHETIC",
    "Table_VII_replay": "PASS_SYNTHETIC",
    "Table_XI_claim_evidence_map": "PASS"
  },
  "limitations": [
    "Synthetic outputs do not reproduce paper numerical results.",
    "Full numerical reproduction requires licensed Crypto Lake snapshots."
  ]
}
```

### 6.11. `10_make_artifact_manifest.py`

Tạo manifest và checksum.

Output:

```text
artifacts/synthetic/manifest.json
artifacts/synthetic/checksums.sha256
```

Manifest cần chứa:

- git commit hash nếu có,
- Python version,
- package versions,
- OS,
- command line used,
- config hash,
- input hash,
- output hash,
- timestamp run,
- mode: synthetic/full.

---

## 7. CLAIM_EVIDENCE_MAP.md

File này rất quan trọng vì nó giúp reviewer thấy paper không hallucinate. Cần viết bảng như sau:

| Paper claim | Paper location | Evidence artifact | Script | Config | Public synthetic status | Full reproduction status | Limitation |
|---|---|---|---|---|---|---|---|
| Full-year BTC/ETH L2 benchmark | Abstract, Sec. III | `artifacts/full/dataset_summary.csv` | `01_validate_schema.py` | `btc_usdt_2024.yaml`, `eth_usdt_2024.yaml` | schema only | requires licensed data | raw data not redistributed |
| Time-causal feature construction | Sec. III-B | `feature_summary.csv`, `test_no_leakage_splits.py` | `02_build_features.py` | `synthetic.yaml` | pass | pass if full data present | rolling windows must use past only |
| Cost-aware ternary labels | Sec. III-C | `label_summary.csv` | `03_make_labels_regimes_splits.py` | `synthetic.yaml` | pass | pass if full data present | thresholds config-defined |
| Visible-depth replay | Sec. V | `replay_summary.csv` | `05_run_visible_depth_replay.py` | `replay_defaults.yaml` | pass | pass if predictions present | not live execution |
| RSEP diagnostic gate | Sec. V | `rsep_summary.csv` | `06_run_rsep_diagnostic.py` | `replay_defaults.yaml` | pass | pass if predictions present | not a trading algorithm |
| Fee/latency/spread/depth stress | Sec. VI | `stress_summary.csv` | `07_run_stress_tests.py` | `stress_defaults.yaml` | pass | pass if replay outputs present | stress axes are diagnostic |
| Day-level bootstrap | Sec. VI | `bootstrap_summary.csv` | `08_run_bootstrap_and_transfer.py` | `bootstrap_defaults.yaml` | pass | pass if replay outputs present | day bootstrap, not row bootstrap |
| BTC↔ETH transfer | Sec. VII | `transfer_summary.csv` | `08_run_bootstrap_and_transfer.py` | `transfer_defaults.yaml` | pass synthetic | pass if both assets present | source-validation-only tuning |

---

## 8. REPRODUCIBILITY_CHECKLIST.md

Tạo checklist theo tinh thần reviewer ICDM/IEEE. Nội dung cần có:

```markdown
# Reproducibility Checklist

## Data availability
- [x] Code is public in the supplementary artifact.
- [x] Synthetic sample is public and deterministic.
- [ ] Raw Crypto Lake full-year snapshots are not redistributed because they require a commercial license.
- [x] Instructions are provided for licensed-data users to reproduce full numerical results.

## Code availability
- [x] All pipeline scripts are included.
- [x] Commands are documented.
- [x] Package versions are pinned.
- [x] Smoke tests run without commercial data.

## Experimental protocol
- [x] Chronological splits are specified.
- [x] Purging/embargo is specified.
- [x] Feature construction is time-causal.
- [x] Label thresholds are config-defined.
- [x] Replay assumptions are documented.
- [x] Stress axes are documented.
- [x] Bootstrap unit is day-level.

## Claim boundaries
- [x] Synthetic outputs are not claimed to reproduce paper numbers.
- [x] Replay is not live trading.
- [x] RSEP is not a deployable trading strategy.
- [x] Full numerical reproduction requires licensed raw data.
```

---

## 9. Makefile yêu cầu

Tạo `Makefile` với các target:

```makefile
.PHONY: synthetic verify clean validate-full-data full verify-full manifest test

synthetic:
	python scripts/00_make_synthetic_l2_sample.py --config configs/synthetic.yaml
	python scripts/01_validate_schema.py --config configs/synthetic.yaml --mode synthetic
	python scripts/02_build_features.py --config configs/synthetic.yaml --mode synthetic
	python scripts/03_make_labels_regimes_splits.py --config configs/synthetic.yaml --mode synthetic
	python scripts/04_train_or_load_baselines.py --config configs/synthetic.yaml --mode synthetic
	python scripts/05_run_visible_depth_replay.py --config configs/synthetic.yaml --mode synthetic
	python scripts/06_run_rsep_diagnostic.py --config configs/synthetic.yaml --mode synthetic
	python scripts/07_run_stress_tests.py --config configs/synthetic.yaml --mode synthetic
	python scripts/08_run_bootstrap_and_transfer.py --config configs/synthetic.yaml --mode synthetic
	python scripts/10_make_artifact_manifest.py --mode synthetic

verify:
	python scripts/09_verify_paper_tables.py --mode synthetic
	pytest -q

validate-full-data:
	python scripts/01_validate_schema.py --config configs/btc_usdt_2024.yaml --mode full
	python scripts/01_validate_schema.py --config configs/eth_usdt_2024.yaml --mode full

full:
	bash scripts/run_full_reproduction.sh

verify-full:
	python scripts/09_verify_paper_tables.py --mode full

manifest:
	python scripts/10_make_artifact_manifest.py --mode synthetic

clean:
	rm -rf artifacts/synthetic artifacts/full
```

---

## 10. Tests bắt buộc

### 10.1. `test_schema.py`

Kiểm tra:

- đủ 20 bid/ask levels,
- best bid < best ask,
- size không âm,
- timestamp tăng dần.

### 10.2. `test_no_leakage_splits.py`

Kiểm tra:

- train end < validation start,
- validation end < test start,
- embargo > 0 nếu config yêu cầu,
- feature rolling không dùng future rows.

### 10.3. `test_labels.py`

Kiểm tra:

- label chỉ thuộc tập hợp hợp lệ,
- threshold có spread/fee proxy,
- future return chỉ dùng cho label, không lọt vào features.

### 10.4. `test_replay_accounting.py`

Kiểm tra:

- net_pnl = gross_pnl - fees - slippage/cost terms nếu có,
- n_trades khớp replay_trades,
- coverage trong [0,1],
- không trade nếu prediction là hold/abstain.

### 10.5. `test_rsep_rules.py`

Kiểm tra:

- nếu expected_edge <= cost + risk penalty thì abstain,
- buy/sell decision không dùng true future label,
- thresholds lấy từ config.

### 10.6. `test_manifest_checksums.py`

Kiểm tra:

- mọi output chính có checksum,
- manifest parse được,
- config hash tồn tại.

---

## 11. Các file config mẫu

### 11.1. `configs/synthetic.yaml`

```yaml
mode: synthetic
seed: 20260606
assets: [BTC-USDT, ETH-USDT]
levels_per_side: 20
synthetic:
  days: 2
  rows_per_day: 5000
  base_prices:
    BTC-USDT: 60000
    ETH-USDT: 3000
  spread_bps_range: [1, 8]
  volatility_regimes: [low, medium, high]
paths:
  raw: data/synthetic/raw/book_snapshots.parquet
  artifact_dir: artifacts/synthetic
features:
  past_windows: [10, 50, 100]
  top_k_depth: [1, 5, 10, 20]
labels:
  horizon_rows: 50
  fee_bps: 5
  spread_multiplier: 1.0
splits:
  train_ratio: 0.5
  val_ratio: 0.25
  test_ratio: 0.25
  embargo_rows: 100
replay:
  initial_cash: 100000
  fee_bps: 5
  latency_rows: 0
  depth_levels: 20
stress:
  fee_multipliers: [0, 0.5, 1, 2]
  latency_rows: [0, 1, 5, 10]
  spread_multipliers: [1, 1.5, 2]
  depth_haircuts: [0, 0.25, 0.5]
bootstrap:
  unit: day
  n_bootstrap: 200
```

### 11.2. `configs/btc_usdt_2024.yaml`

```yaml
mode: full
asset: BTC-USDT
source: Crypto Lake licensed Level-2 snapshots
period: 2024-01-01 to 2024-12-31
levels_per_side: 20
paths:
  raw_glob: data/external/cryptolake/BTC-USDT/book/2024/*.parquet
  artifact_dir: artifacts/full/BTC-USDT
license:
  raw_data_redistributed: false
  user_must_provide_data: true
column_mapping:
  timestamp: timestamp
  bid_px_1: bid_px_1
  bid_sz_1: bid_sz_1
  ask_px_1: ask_px_1
  ask_sz_1: ask_sz_1
features:
  past_windows: [10, 50, 100, 500]
labels:
  horizon_rows: 50
  fee_bps: 5
  spread_multiplier: 1.0
splits:
  train_ratio: 0.5
  val_ratio: 0.25
  test_ratio: 0.25
  embargo_rows: 1000
```

---

## 12. Paper-facing artifact note nên thêm vào supplementary README

Dùng nguyên văn đoạn này trong README hoặc `LICENSE_AND_DATA_ACCESS.md`:

```text
The artifact intentionally separates public auditability from full numerical reproduction. The public release contains code, configurations, schema documentation, deterministic synthetic Level-2 samples, tests, manifest generation, and claim-to-evidence mapping. It does not redistribute the full BTC-USDT or ETH-USDT Crypto Lake snapshots because those data require a separate license. Users with licensed access can place the raw snapshots under `data/external/cryptolake/` and run the documented full reproduction commands. Without licensed raw data, the synthetic mode verifies the method surface and pipeline accounting but must not be interpreted as reproducing the empirical numbers reported in the paper.
```

---

## 13. Những lỗi Codex tuyệt đối không được mắc

1. Không được tạo fake full-year outputs.
2. Không được hard-code paper numbers vào verifier rồi báo pass.
3. Không được đưa raw data thương mại vào artifact.
4. Không được ghi synthetic result là evidence cho empirical claim.
5. Không được dùng random split.
6. Không được để feature dùng future label/midprice.
7. Không được để replay dùng true future return.
8. Không được claim RSEP là profitable trading strategy.
9. Không được bỏ qua checksum/manifest.
10. Không được để command fail mơ hồ khi thiếu licensed data.

---

## 14. Kế hoạch triển khai cho Codex theo thứ tự ưu tiên

### Phase 1: Artifact skeleton và documentation

- Tạo `supplementary_artifact/` theo cấu trúc.
- Viết README, DATA_CARD, SCHEMA, LICENSE, CHECKLIST, CLAIM_EVIDENCE_MAP.
- Tạo configs synthetic/full.
- Tạo Makefile.

Deliverable:

```text
supplementary_artifact/README.md
supplementary_artifact/DATA_CARD.md
supplementary_artifact/SCHEMA.md
supplementary_artifact/CLAIM_EVIDENCE_MAP.md
supplementary_artifact/Makefile
```

### Phase 2: Synthetic executable pipeline

- Implement synthetic generator.
- Implement schema validation.
- Implement feature/label/regime/split.
- Implement small baseline.
- Implement replay/RSEP/stress/bootstrap/transfer.

Deliverable:

```bash
make synthetic
make verify
```

must pass.

### Phase 3: Manifest/checksum/verifier

- Implement manifest generator.
- Implement SHA256 checksum.
- Implement table verifier.
- Implement tests.

Deliverable:

```text
artifacts/synthetic/manifest.json
artifacts/synthetic/checksums.sha256
artifacts/synthetic/verification_report.json
```

### Phase 4: Full reproduction interface

- Implement full data path validation.
- Implement clear error if licensed data missing.
- Ensure same scripts work with full configs.
- Add placeholder README for outputs not shipped.

Deliverable:

```bash
make validate-full-data
make full
make verify-full
```

Full commands may fail only if raw data missing, but must fail with an explicit licensed-data message.

### Phase 5: Final packaging

- Zip `supplementary_artifact/`.
- Add `ARTIFACT_MANIFEST_TOPLEVEL.md`.
- Run clean install in a fresh environment.
- Save terminal output to `artifacts/synthetic/logs/reviewer_quickstart.log`.

---

## 15. Final quality gate trước khi nộp ICDM

Chạy:

```bash
cd supplementary_artifact
make clean
make synthetic
make verify
python scripts/10_make_artifact_manifest.py --mode synthetic
sha256sum -c artifacts/synthetic/checksums.sha256
```

Sau đó kiểm tra bằng tay:

- README chạy đúng từng lệnh.
- Không có raw commercial data.
- Synthetic outputs ghi rõ không reproduce paper numbers.
- Full reproduction requires licensed data được nhắc ít nhất trong README, DATA_CARD, LICENSE file và verification report.
- CLAIM_EVIDENCE_MAP có đủ claim chính của paper.
- Logs không chứa path nhạy cảm hoặc credential.
- Zip cuối cùng mở ra có cấu trúc rõ, không lẫn file tạm.

---

## 16. Gợi ý prompt giao trực tiếp cho Codex

Dùng prompt sau trong Codex:

```text
You are implementing the supplementary artifact for an ICDM 2026 Applied Track benchmark paper titled “CryptoRegimeShift-LOB: A Crypto Level-2 Benchmark for Auditing Forecast-to-Execution Degradation.”

Your goal is to create a reviewer-ready supplementary_artifact/ directory that supports public pipeline audit without redistributing commercial Crypto Lake raw data, while also providing a licensed-data path for full numerical reproduction.

Read supplementaryartifact_guide.md completely. Implement the artifact exactly according to the guide. Prioritize correctness, transparency, no data leakage, no fake results, and clear reviewer-facing documentation.

Do not fabricate full-year paper results. Do not hard-code paper table numbers. Synthetic outputs are only for method-surface audit. Full numerical reproduction must require licensed Crypto Lake snapshots under data/external/cryptolake/.

Required final commands:
make synthetic
make verify

Both must pass in a clean environment without commercial data. Also implement make validate-full-data so it fails clearly if licensed raw data are absent.

At the end, provide:
1. tree of supplementary_artifact/
2. command outputs for make synthetic and make verify
3. list of generated artifact files
4. statement confirming no raw commercial data are included
5. any limitations or TODOs that remain
```

---

## 17. Tiêu chí nâng tầm paper sau khi artifact hoàn thành

Khi artifact hoàn thành đúng guide này, paper sẽ được nâng ở 4 điểm reviewer quan tâm:

1. **Reproducibility:** reviewer có thể chạy pipeline audit ngay cả khi không có raw data.
2. **Claim discipline:** paper không bị nghi hallucinate benchmark vì mỗi claim có artifact mapping.
3. **Applied significance:** benchmark không chỉ là mô tả, mà có release structure dùng được.
4. **Trustworthiness:** commercial-data boundary được nói rõ, không overclaim public reproducibility.

Nếu Codex hoàn thành đủ, có thể bổ sung vào paper hoặc supplementary note một câu:

```text
The supplementary artifact provides a deterministic synthetic Level-2 sample, executable pipeline scripts, schema checks, manifest/checksum generation, and a claim-to-evidence map. Full numerical reproduction of the reported BTC/ETH 2024 results requires licensed Crypto Lake snapshots, while the public artifact verifies the method surface and replay accounting without redistributing commercial data.
```
