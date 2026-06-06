# Reference Audit for CryptoRegimeShift-LOB / ICDM Applied Track

Date: 2026-06-06

## Summary

- Checked `main.tex`, `custom.bib`, generated `main.bbl`, and recompiled `main.pdf`.
- Removed stale bibliography state: the uploaded `main.bbl` had 32 items while `main.tex` cited 30 keys. The corrected version now regenerates the bibliography from current citations.
- Added explicit citations for XGBoost and TCN baselines in the text.
- Removed redundant citation to the BIS working-paper version of the Aquilina--Budish--O'Neill HFT arms-race paper where the published QJE version is already cited.
- Cleaned `custom.bib` to retain only cited entries.
- Corrected incomplete/updated metadata for recent references.
- Recompiled successfully to 10 pages.

## Metadata Corrections

1. `briola2025lobframe`
   - Updated Quantitative Finance metadata from `pages = {1--31}` to `volume = {25}`, `number = {7}`, `pages = {1101--1131}`.

2. `xiao2025lit`
   - Added article identifier as `pages = {1616485}` for Frontiers in Artificial Intelligence.

3. `iosco_crypto2023`, `fsb2023crypto`, `aquilina2025speedpremium`, `cryptolake_data`
   - Added official online URLs in `note`/`howpublished` fields.

4. `chen2016xgboost`, `bai2018tcn`
   - Added/retained because the manuscript reports XGBoost and TCN baselines.

## Current Bibliography Status

- `main.tex` cited keys: 31
- `custom.bib` entries retained: 31
- regenerated `main.bbl` items: 31
- unresolved citations: none detected after compilation
- unresolved references: none detected after final compilation
- page count: 10

## Remaining Notes

- IEEEtran.bst does not print DOI fields in the final bibliography by default. The DOI metadata is retained in `custom.bib` for journal/conference references.
- Books, institutional reports, arXiv/preprint entries, and documentation entries are represented with ISBN, eprint, or official URL as appropriate.
- The bibliography is now aligned with cited content and should not contain stale uncited references.
