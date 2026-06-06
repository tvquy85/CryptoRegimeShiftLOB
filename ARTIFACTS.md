# ARTIFACTS.md

File này là entrypoint artifact cho reviewer. Mục tiêu là cho phép kiểm tra pipeline, schema, config, claim boundary và paper assets mà không cần raw L2 thương mại.

## Artifact public nên đưa lên GitHub

- `src/`, `scripts/`, `configs/`, `tests/`: code, CLI và cấu hình tái lập.
- `sample_data/l2_synthetic_sample.parquet`: dữ liệu L2 synthetic nhỏ, cùng schema raw 20 levels.
- `sample_data/BOOK_BINANCE_SYNTH-USDT_JAN-2024.parquet`: bản copy cùng nội dung, đặt tên theo pattern loader thật.
- `ARTIFACTS.md`, `DATA_CARD.md`, `SCHEMA.md`, `REPRODUCIBILITY.md`, `guideline.md`, `rule.md`, `MoTa.md`, `ThucNghiem.md`.
- `outputs/paper_assets/*.csv`, `outputs/paper_assets/*.md`, `outputs/paper_assets/*.png` loại nhỏ và đã khóa số.
- `artifacts/split_audit.csv`, `artifacts/split_audit.md`.
- `checksums.json`.

## Artifact không public

- Raw commercial BTC/ETH: `data/full2024/`, `data/eth/`, hoặc raw root ngoài repo như `../data/full2024/`.
- Derived parquet lớn: `data/features/`, `data/labels/`, `data/regimes/`, `data/splits/`, `data/predictions/`, `data/backtests/`.
- Model weights/checkpoints/logs: `outputs/checkpoints/`, `outputs/logs/`, `*.pt`, `*.ckpt`, `*.joblib`.
- File tạm/cache: `*.tmp`, `__pycache__/`, `.pytest_cache/`.

## Artifact chính cho paper

- `outputs/paper_assets/table_1_dataset_stats.csv`: dataset stats BTC/ETH.
- `outputs/paper_assets/table_11_acceptance_bar.csv`: acceptance bar paper.
- `outputs/paper_assets/table_13_claim_to_evidence_map.csv`: claim-to-evidence map.
- `outputs/paper_assets/table_14_number_consistency_check.csv`: number consistency lock.
- `outputs/paper_assets/table_18_default_benchmark_configuration.csv`: cấu hình benchmark mặc định.
- `outputs/paper_assets/table_19_chronological_split_audit.csv`: audit split train/validation/test.
- `outputs/paper_assets/artifact_availability_statement_p0_03.md`: đoạn Data/Artifact Availability đưa vào paper.

## Smoke artifact

Smoke pipeline dùng `configs/repro_smoke.yaml` và synthetic symbol `SYNTH-USDT`. Output smoke nằm ở các path namespaced như:

- `data/features/features_synthetic_smoke.parquet`
- `data/labels/labels_synthetic_smoke.parquet`
- `data/regimes/regimes_synthetic_smoke.parquet`
- `data/splits/splits_synthetic_smoke.parquet`
- `data/predictions/predictions_synthetic_smoke.parquet`
- `outputs/smoke/paper_assets/`

Các file smoke output là bằng chứng pipeline chạy được, không dùng để báo cáo kết quả khoa học.
