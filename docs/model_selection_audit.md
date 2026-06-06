# Model-selection and data-snooping audit

- `run_id`: `p1_11_model_selection_audit_v001`
- Muc tieu: chung minh selection model/policy trong paper duoc trace bang artifact va khong dung test de tune.
- Pham vi: Stage 3 BTC, ETH within-asset, BTC<->ETH asset-held-out, va deep/temporal pilot da co.
- Khong train lai, khong replay lai, khong dung raw data.

## Tom tat ledger

- So row ledger: `34`.
- So model/config label duy nhat: `11`.
- Tong threshold candidates trong tuning tables: `196`.
- Selection audit FAIL rows: `0`.

- `asset_heldout_stage3`: `6` ledger rows
- `btc_full_year_model_reporting`: `4` ledger rows
- `btc_within_asset_stage3`: `12` ledger rows
- `eth_full_year_model_reporting`: `1` ledger rows
- `eth_within_asset_stage3`: `3` ledger rows
- `temporal_or_deep_pilot`: `4` ledger rows
- `temporal_tabular_comparative_reporting`: `4` ledger rows

## Quy tac selection da audit

- Forecasting models duoc bao cao theo vai tro bang chung; paper khong chon winner bang test profitability.
- Policy thresholds trong `09_tune_execution_policies.py` duoc chon tren validation net PnL voi rang buoc min-trades/min-days.
- Asset-held-out execution trong `20_run_asset_heldout_execution.py` tune tren source validation only; target test chi dung de report.
- RSEP lambda la singleton benchmark grid; `theta_edge` duoc chon tu validation margin grid.
- Stress grid khong retrain, khong recompute probabilities, khong retune thresholds/RSEP.

## PBO/Reality Check diagnostic

- Trang thai: `INFEASIBLE_FROM_CURRENT_SAVED_ARTIFACTS`.
- Ly do: Current artifacts save aggregate validation metrics for all threshold candidates and daily/trade returns only for selected policies; conservative PBO/Reality-Check diagnostics require per-candidate per-period returns.
- Conservative controls: ledger of tried candidates, validation-only selection, test-only reporting, day-level bootstrap, stress no-retuning, and negative evidence retained

## Principal ML Scientist view

Ledger nay khong loai bo hoan toan data-snooping risk trong workflow nghien cuu lap di lap lai. Tuy nhien no lam ro surface da thu, split dung de chon threshold, va giu negative evidence nhu TCN stride-1/DeepLOB/Transformer pilot thay vi chi bao cao cau hinh dep.

## Reviewer ICDM view

Diem manh la moi row selection co artifact nguon va `selection_source`. Diem can ha giong la paper khong nen claim da co Reality Check/PBO chinh thuc khi chua save per-candidate daily returns. Nen viet la validation-only controls + day-level bootstrap + full ledger, khong phai guarantee khong overfit.

## Decision

- PASS neu `selection_audit_status` khong co `FAIL_TEST_SELECTION`.
- Remaining risk: finite model family va iterative research workflow; can ghi ro trong Threats to Validity.
