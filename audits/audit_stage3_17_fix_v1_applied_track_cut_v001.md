# Audit Stage 3.17 - fix_v1 Applied Track Cut

## Scope

This audit records the first post-purged cut of the ICDM 2026 Applied Track manuscript.

- Target file: `Paper_ICDM_2026/paper_applied_singleblind.tex`
- Built PDF: `Paper_ICDM_2026/paper_applied_singleblind.pdf`
- Build tool: `tectonic.exe`
- Date: 2026-06-06

## Gate Results

- H-row purged evidence gate: PASS.
  - Source audit: `artifacts/split_audit.csv`
  - BTC/ETH train and validation boundaries: `explicit_purge_rows=50`, `horizon_overlap_rows=0`, `status=PASS`.
  - Detailed audit: `audits/audit_stage3_16_purged_evidence_gate_v001.md`.
- Page limit: PASS.
  - Built PDF page count: `4`.
  - ICDM Applied Track limit: `<=10` pages including references.
- Build: PASS.
  - `tectonic.exe paper_applied_singleblind.tex` completed successfully.
  - Remaining warnings are layout warnings: underfull boxes and small overfull vbox; no missing citation or fatal TeX error.

## Content Changes

- The candidate manuscript now uses purged SGD core evidence rather than the old non-purged evidence.
- XGBoost/TCN/DeepLOB/Transformer are no longer used as main quantitative claims because they have not been rerun under the purged protocol.
- Claim maps, full reproducibility checklist, regime sensitivity details, model-selection ledger, and ablation details are moved out of the main PDF narrative and kept as artifact text.
- Core claims are preserved:
  - cost-aware L2 benchmark;
  - forecast-to-execution degradation;
  - RSEP as diagnostic/selective gate only;
  - net-negative execution;
  - stress sensitivity;
  - BTC<->ETH-only transfer evaluation.

## Remaining Submission Blockers

- Author placeholders remain in `paper_applied_singleblind.tex`:
  - `TODO_AUTHOR_NAME`
  - `TODO_AFFILIATION`
  - `TODO_CITY`
  - `TODO_COUNTRY`
  - `TODO_EMAIL`
- The current PDF is intentionally concise at 4 pages. It passes the page limit, but the authors should review whether the Applied Track narrative needs more explanatory detail before final submission.
- `main.tex` remains the long working draft and should not be treated as the submission file unless it is cut separately.

## Decision

- **Format/page gate:** PASS for `paper_applied_singleblind.tex`.
- **Scientific h-row gate:** PASS for purged SGD core evidence.
- **Final upload readiness:** PARTIAL. Replace author placeholders and do a final human review before submission.

