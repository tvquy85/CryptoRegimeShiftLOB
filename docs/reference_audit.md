# Reference audit P1-12

- `run_id`: `p1_12_reference_audit_v004`
- Muc tieu: kiem tra DOI/title/venue/year, arXiv-only risk, URL/report sources, va coverage citation canonical.
- Pham vi: `Paper_ICDM_2026/custom.bib` va cite keys trong `main.tex`.

## Summary

- Total entries: `42`.
- Cited entries: `32`.
- PASS: `31`.
- QUESTIONABLE: `1`.
- ARXIV_ONLY: `1`.
- VERIFY_TIMEOUT: `0`.
- UNUSED: `9`.

## Missing or weak coverage

- Khong co category canonical bi thieu citation.

## QUESTIONABLE

- `bieganowski2026cryptoexplainable` (misc, cited=False): ARXIV_HAS_PEER_REVIEWED_ALTERNATIVE;UNUSED_ENTRY; Consider replacing/augmenting with DOI 10.2139/ssrn.6159346.

## ARXIV_ONLY

- `bai2018tcn` (misc, cited=True): ARXIV_ONLY_ACCEPTABLE_IF_CANONICAL; Keep only if this is the canonical source for the model/protocol.

## VERIFY_TIMEOUT

- Khong co.

## UNUSED

- `angerer2025cryptoorderbook` (article, cited=False): UNUSED_ENTRY; No action required.
- `arroyo2024survival` (article, cited=False): UNUSED_ENTRY; No action required.
- `briola2025hlob` (article, cited=False): UNUSED_ENTRY; No action required.
- `cont2001stylizedfacts` (article, cited=False): UNUSED_ENTRY; No action required.
- `easley2026cryptomicrostructure` (article, cited=False): UNUSED_ENTRY; No action required.
- `iosco2025implementation` (techreport, cited=False): UNUSED_ENTRY; No action required.
- `ke2017lightgbm` (inproceedings, cited=False): UNUSED_ENTRY; No DOI found; canonical proceedings URL verified.
- `maglaras2022fillprob` (article, cited=False): UNUSED_ENTRY; No action required.
- `schnaubelt2019bitcoinlob` (article, cited=False): UNUSED_ENTRY; No action required.

## Principal ML Scientist view

Coverage citation hien co bao phu cac truc quan trong: FI-2010, DeepLOB, LOB benchmark, market microstructure, crypto microstructure, time-series validation, bootstrap va backtest-overfitting. Dataset documentation phai duoc cite ro de reviewer truy vet nguon L2 snapshots.

## Reviewer ICDM view

Truoc submission, nen review cac entry QUESTIONABLE, ARXIV_ONLY va UNUSED. ARXIV_ONLY co the chap nhan neu la nguon canonical; UNUSED co the giu trong draft nhung nen prune neu khong con duoc cite.

