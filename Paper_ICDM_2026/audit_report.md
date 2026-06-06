# ICDM 2026 Draft Audit Report

## Compile status
- `main.tex` compiles successfully with `pdflatex` using the included `main.bbl`.
- Output PDF: `main.pdf`.
- Page count: 13 pages in the current Tectonic check.
- Format: IEEEtran conference two-column.
- Author block: anonymous.
- Submission status: **NOT submission-ready**.

## Current submission blockers
1. ICDM 2026 Applied Track allows at most 10 pages including bibliography and appendices; the current PDF is 13 pages.
2. The locked split audit reports `explicit_purge_rows=0`, `horizon_overlap_rows=50`, and `WARN_BOUNDARY_OVERLAP` at train--validation and validation--test boundaries for BTC-USDT and ETH-USDT.
3. `fix_v1.md` requires stopping submission if h-row purged split results are not available. Therefore the paper must not be presented as submission-ready until forecasting, tuning/execution, RSEP, stress, bootstrap, and cross-asset artifacts are regenerated under the purged protocol.

## Major edits applied
1. Reframed the paper consistently as a benchmark/evaluation/failure-analysis study.
2. Removed or softened wording that could imply profitability, live trading readiness, exact replay, or universal policy transfer.
3. Added explicit L2 snapshot observational boundaries.
4. Preserved negative net PnL as evidence of forecast-to-execution degradation.
5. Preserved TCN stride-1 as negative evidence against a simplistic macro-F1 -> execution-success narrative.
6. Added claim-to-evidence and reproducibility sections.
7. Added manual `main.bbl` because the local environment does not provide BibTeX.

## Claim audit table
| Original risk area | Issue | Fix applied | Evidence path |
|---|---|---|---|
| `execution replay` | Could be read as live execution simulator | Rewritten as `L2 snapshot market-order replay approximation` | `guideline.md`, `TongQuan.md`, simulator boundary |
| `RSEP mitigates losses` | Could be read as universal winner | Rewritten as relative/diagnostic and includes TCN negative evidence | `table_13_claim_to_evidence_map.csv`, `table_14_number_consistency_check.csv` |
| `cross-asset evaluation` | Could be read as universal cross-asset transfer | Restricted to BTC-USDT <-> ETH-USDT only | `table_16_cross_asset_forecasting_execution.csv`, `table_17_cross_asset_bootstrap.csv` |
| `net PnL` | Could be read as trading success/failure | All net-negative results interpreted as degradation evidence | `table_13_claim_to_evidence_map.csv` |
| `LOB data realism` | Could imply L3/MBO reconstruction | Explicitly states no exact queue priority, hidden liquidity, passive fill, or matching engine details | `guideline.md`, `TongQuan.md` |
| `forecasting baselines` | Could imply new SOTA model | Rewritten as controlled diagnostic suite | `table_14_number_consistency_check.csv` |

## Number checks applied
- BTC audit rows: 167,753,156.
- ETH audit rows: 114,416,283.
- BTC feature rows: 167,751,306.
- ETH feature rows: 114,414,433.
- BTC test rows: 33,550,262.
- ETH target rows in asset-held-out: 22,882,887.
- SGD: accuracy 0.5589, macro-F1 0.4652, MCC 0.2363, RSEP net -4,437.49.
- XGBoost: accuracy 0.5677, macro-F1 0.4562, MCC 0.2364, RSEP net -4,303.19.
- TCN stride-1: accuracy 0.5281, macro-F1 0.4688, MCC 0.2274, cost-aware net -788.00, RSEP net -814.17.
- BTC -> ETH: macro-F1 0.4325, MCC 0.1486, RSEP net -74,466.38, cost-aware net -287,991.44.
- ETH -> BTC: macro-F1 0.4839, MCC 0.2424, RSEP net -1,144.75, cost-aware net -3,697.46.

## Remaining reviewer-facing cautions
- If submitting to Research Track, ensure full triple-blind compliance and avoid public repository links in the manuscript.
- If submitting to Applied Track, single-blind is acceptable under the current ICDM 2026 call, but keep the paper's novelty framed as a benchmark/protocol/failure-analysis contribution.
- If `custom.bib` is compiled with BibTeX on Overleaf, the generated references may differ slightly from the included `main.bbl`; re-check page count after BibTeX.
- Do not cut the current 13-page draft into a submission PDF until h-row purged results exist and the split audit reports zero boundary overlap.
