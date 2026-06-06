# CryptoRegimeShift-LOB Supplementary Artifact

This artifact supports the ICDM Applied Track paper by separating public auditability from full numerical reproduction. It has three layers:

1. **Raw-format minimal sample layer.** A small Crypto Lake-style L2 sample can be placed under `data/raw_sample/cryptolake_minimal/` to verify schema and loader compatibility. The package does not include commercial raw snapshots unless a provider-public sample or a license-permitted excerpt is explicitly provided.
2. **Synthetic audit layer.** A deterministic two-asset 20-level L2 sample is generated locally and runs the full smoke pipeline without any commercial data.
3. **Licensed full reproduction layer.** Full BTC-USDT and ETH-USDT 2024 reproduction requires licensed Crypto Lake snapshots under `data/external/cryptolake/`.

The public artifact is an artifact-backed evaluation protocol, not a fully public raw-data release. Synthetic and raw-format sample outputs are for pipeline verification only; they are not evidence for the paper's empirical numbers.

## Reviewer Quickstart

```bash
cd supplementary_artifact
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
make synthetic
make verify
```

Expected high-level output:

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

If `make` is unavailable, run:

```bash
bash scripts/run_synthetic_end_to_end.sh
python scripts/09_verify_paper_tables.py --mode synthetic
```

Windows PowerShell alternative:

```powershell
.\scripts\run_synthetic_end_to_end.ps1
python scripts\09_verify_paper_tables.py --mode synthetic
```

## Raw-Format Minimal Sample

The raw-format sample layer checks that the pipeline can parse Crypto Lake-style Level-2 snapshots with 20 price levels per side. It is optional because redistribution permission depends on the data license.

```bash
make validate-raw-sample
```

If no sample is packaged, the command fails clearly:

```text
[ERROR] Raw-format sample not packaged. Use `make synthetic` or place a provider-public/licensed sample under data/raw_sample/cryptolake_minimal/.
```

To create a minimal sample from user-supplied data, use:

```bash
python scripts/00_extract_minimal_raw_sample.py \
  --input-glob "PATH_TO_ALLOWED_SAMPLE/*.parquet" \
  --output-dir data/raw_sample/cryptolake_minimal \
  --source-type license_permitted_excerpt \
  --license-confirmed \
  --max-rows 20000
```

Do not use this command on commercial full-year data unless the license allows redistributing the excerpt.

## Full Reproduction With Licensed Data

Put licensed Crypto Lake data here:

```text
data/external/cryptolake/BTC-USDT/book/2024/*.parquet
data/external/cryptolake/ETH-USDT/book/2024/*.parquet
```

Then run:

```bash
make validate-full-data
make full
make verify-full
```

If data are absent, the command must fail with:

```text
[ERROR] Licensed Crypto Lake raw snapshots not found.
Full numerical reproduction requires licensed raw data.
Run `make synthetic` for public pipeline verification.
```

## Interpretation Boundary

This public artifact supports method-surface audit and pipeline verification without redistributing commercial raw data. Full numerical reproduction of the paper tables requires licensed access to Crypto Lake Level-2 snapshots. Synthetic outputs and optional raw-format sample checks do not reproduce the empirical numbers reported in the paper.
