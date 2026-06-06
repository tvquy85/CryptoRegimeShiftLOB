# Troubleshooting

## Missing licensed data

Use `make synthetic` for public verification. Full reproduction requires licensed Crypto Lake snapshots.

## Missing raw-format sample

This is allowed unless the package claims a raw-format sample is included. Place provider-public or license-permitted parquet files under `data/raw_sample/cryptolake_minimal/`.

## No `make` command

Run:

```bash
bash scripts/run_synthetic_end_to_end.sh
python scripts/09_verify_paper_tables.py --mode synthetic
```

On Windows PowerShell:

```powershell
.\scripts\run_synthetic_end_to_end.ps1
python scripts\09_verify_paper_tables.py --mode synthetic
```
