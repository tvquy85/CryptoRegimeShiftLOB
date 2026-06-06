# Audit Stage 3.18: `main.tex` full 10-page Fix v1 candidate

Date: 2026-06-06

## Scope

This audit records the paper-editing pass that rewrote `Paper_ICDM_2026/main.tex` into a full ICDM 2026 Applied Track candidate using the purged Stage 3.16 evidence gate.

The edit targets the main manuscript only. It does not regenerate experiments, change benchmark constants, or introduce new numerical results.

## Submission status

Status: PASS for the local 10-page manuscript gate.

The previous blocker was the missing h-row purged split result. The current `main.tex` now uses the purged split evidence:

- 50-row purge at train-validation and validation-test boundaries.
- `horizon_overlap_rows=0`.
- Boundary status reported as `PASS`.
- BTC split rows: train `100,650,733`, validation `33,550,211`, test `33,550,262`.
- ETH split rows: train `68,648,609`, validation `22,882,837`, test `22,882,887`.

## Main paper changes

- Replaced the old 13-page manuscript with a compact 10-page Applied Track candidate.
- Kept the full-paper structure rather than using the 4-page fallback.
- Used single-blind placeholder author fields: `TODO_AUTHOR_NAME`, `TODO_AFFILIATION`, `TODO_EMAIL`.
- Kept purged SGD as the only main quantitative forecasting baseline.
- Treated XGBoost, TCN, DeepLOB-style, and LOB-Transformer evidence as artifact/pilot coverage unless regenerated under the same purged protocol.
- Preserved core claims:
  - cost-aware L2 benchmark,
  - forecast-to-execution degradation,
  - RSEP as diagnostic selective execution,
  - net-negative execution after costs,
  - stress sensitivity,
  - BTC<->ETH-only transfer.
- Moved detailed claim maps, reproducibility checklist, sensitivity, model-selection ledger, and detailed ablation content out of the main PDF narrative and into artifact references.

## Build verification

Command:

```powershell
cd CryptoRegimeShift\Paper_ICDM_2026
..\tectonic.exe main.tex
```

Result:

- Build completed and wrote `main.pdf`.
- Page count: `10`.
- Output size: approximately `171.7 KiB`.
- Remaining TeX warnings are layout warnings (`Underfull \hbox`, minor `Overfull \hbox`, and Tectonic BibTeX rerun consistency warnings). No build failure occurred.

## Wording checks

Manual grep checked for stale or prohibited wording:

- No `Anonymous Authors`.
- No `0-row purge`.
- No `WARN_BOUNDARY`.
- No `50-event horizon overlap audited`.
- No old `NOT submission-ready` marker in `main.tex`.
- No main quantitative claim for non-purged XGBoost/TCN/DeepLOB/Transformer.
- Boundary wording remains explicit: the paper does not claim profitability, live trading readiness, exact queue reconstruction, or universal transfer.

Matches such as “does not support profitable cross-asset trading or universal policy generalization” are intentional boundary statements, not overclaims.

## Repo checks

Commands:

```powershell
python -m compileall CryptoRegimeShift\src CryptoRegimeShift\scripts CryptoRegimeShift\tests
pytest CryptoRegimeShift\tests -q
```

Results:

- `compileall`: PASS.
- `pytest`: PASS, `135` tests passed.
- Warnings were third-party deprecation warnings from scikit-learn/pandas sparse dtype checks.

## Remaining actions before actual submission

- Replace author placeholders with real single-blind author information before uploading to the Applied Track portal.
- Review final PDF visually for table/figure placement and IEEE page-budget comfort.
- If any non-SGD model is promoted to the main quantitative table later, rerun that model under the same purged split protocol first.
