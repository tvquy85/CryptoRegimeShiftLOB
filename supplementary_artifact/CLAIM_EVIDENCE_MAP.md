# Claim-to-Evidence Map

| Paper claim | Paper location | Evidence artifact | Script | Config | Public synthetic status | Raw-format sample status | Full reproduction status | Limitation |
|---|---|---|---|---|---|---|---|---|
| Full-year BTC/ETH L2 benchmark | Abstract, Sec. III | `artifacts/full/dataset_summary.csv` | `01_validate_schema.py` | `btc_usdt_2024.yaml`, `eth_usdt_2024.yaml` | schema only | schema only if sample present | requires licensed data | raw data not redistributed |
| Pipeline can parse Crypto Lake-style L2 snapshots | Sec. VIII | `artifacts/raw_sample/schema_report.json` | `01_validate_schema.py` | `raw_sample.yaml` | pass by construction | pass if provider-public/minimal sample included | not full reproduction | sample is not paper evidence |
| Time-causal feature construction | Sec. III-B | `feature_summary.csv` | `02_build_features.py` | `synthetic.yaml` | pass | not required | pass if full data present | rolling windows use past/current rows only |
| Cost-aware ternary labels | Sec. III-C | `label_summary.csv` | `03_make_labels_regimes_splits.py` | `synthetic.yaml` | pass | not required | pass if full data present | thresholds are config-defined |
| Visible-depth replay | Sec. V | `replay_summary.csv` | `05_run_visible_depth_replay.py` | `replay_defaults.yaml` | pass | not required | pass if predictions present | L2 approximation, not live execution |
| RSEP diagnostic gate | Sec. V | `rsep_summary.csv` | `06_run_rsep_diagnostic.py` | `replay_defaults.yaml` | pass | not required | pass if predictions present | diagnostic, not trading strategy |
| Fee/latency/spread/depth stress | Sec. VI | `stress_summary.csv` | `07_run_stress_tests.py` | `stress_defaults.yaml` | pass | not required | pass if replay outputs present | one-axis diagnostic stress |
| Day-level bootstrap | Sec. VI | `bootstrap_summary.csv` | `08_run_bootstrap_and_transfer.py` | `bootstrap_defaults.yaml` | pass | not required | pass if replay outputs present | day bootstrap, not row bootstrap |
| BTC<->ETH transfer | Sec. VII | `transfer_summary.csv` | `08_run_bootstrap_and_transfer.py` | `transfer_defaults.yaml` | pass synthetic | not required | pass if both assets present | BTC/ETH only |

