# Audit Stage 3.16 / P0-02B - H-row Purged Evidence Gate

- `run_id` chính:
  - `stage3_16_build_purged_split_sources_v001`
  - `stage3_16_split_audit_purged_v001`
  - `stage3_16_forecast_sgd_btc_purged_v001`
  - `stage3_16_forecast_sgd_eth_purged_v001`
  - `stage3_16_tune_sgd_btc_purged_v001`
  - `stage3_16_tune_sgd_eth_purged_v001`
  - `stage3_16_asset_btc_to_eth_sgd_purged_v001`
  - `stage3_16_asset_eth_to_btc_sgd_purged_v001`
  - `stage3_16_asset_btc_to_eth_execution_purged_v001`
  - `stage3_16_asset_eth_to_btc_execution_purged_v001`

## Gate split purged

`artifacts/split_audit.csv` đã được promote từ audit purged sau khi tất cả boundary pass:

- BTC-USDT train/valid: `explicit_purge_rows=50`, `horizon_overlap_rows=0`, `status=PASS`.
- ETH-USDT train/valid: `explicit_purge_rows=50`, `horizon_overlap_rows=0`, `status=PASS`.
- Test splits không có next split nên `horizon_overlap_rows=0`.

Row count purged:

- BTC purged source/prediction: `167,751,206` rows.
- ETH purged source/prediction: `114,414,333` rows.
- BTC test: `33,550,262` rows.
- ETH test: `22,882,887` rows.

## Within-asset SGD purged

Forecasting:

- `sgd_btc_stage3_purged`: accuracy `0.559402`, macro-F1 `0.465001`, MCC `0.236376`, test rows `33,550,262`.
- `sgd_eth_stage3_purged`: accuracy `0.436062`, macro-F1 `0.431334`, MCC `0.149705`, test rows `22,882,887`.

Execution tuned on validation only:

- BTC `naive_threshold`: `30,753` trades, net PnL `-4,221.64`, net/trade `-0.137276`.
- BTC `cost_aware_threshold`: `66,552` trades, net PnL `-8,854.40`, net/trade `-0.133045`.
- BTC `RSEP-full`: `32,766` trades, net PnL `-4,321.47`, net/trade `-0.131889`.
- ETH `naive_threshold`: `164,264` trades, net PnL `-29,750.12`, net/trade `-0.181112`.
- ETH `cost_aware_threshold`: `45,473` trades, net PnL `-7,229.02`, net/trade `-0.158974`.
- ETH `RSEP-full`: `42,889` trades, net PnL `-6,030.34`, net/trade `-0.140603`.

Interpretation: net execution remains negative after fee/spread/depth replay. RSEP is useful as a selective-execution diagnostic and reduces degradation versus cost-aware on ETH; on BTC it improves net/trade and cost-aware loss but does not beat the naive policy in total net PnL.

## Asset-held-out purged

Forecasting target-test:

- `BTC -> ETH`: accuracy `0.434243`, macro-F1 `0.432749`, MCC `0.148781`, target rows `22,882,887`.
- `ETH -> BTC`: accuracy `0.539391`, macro-F1 `0.483708`, MCC `0.242123`, target rows `33,550,262`.

Execution target-test, source-validation-only tuning:

- `BTC -> ETH` naive: `1,481,428` trades, net PnL `-230,570.83`, net/trade `-0.155641`.
- `BTC -> ETH` cost-aware: `1,925,421` trades, net PnL `-293,544.15`, net/trade `-0.152457`.
- `BTC -> ETH` RSEP: `517,363` trades, net PnL `-76,822.20`, net/trade `-0.148488`.
- `ETH -> BTC` naive: `54,006` trades, net PnL `-9,288.17`, net/trade `-0.171984`.
- `ETH -> BTC` cost-aware: `34,985` trades, net PnL `-4,875.61`, net/trade `-0.139363`.
- `ETH -> BTC` RSEP: `33,827` trades, net PnL `-4,308.40`, net/trade `-0.127366`.

Bootstrap RSEP vs cost-aware:

- `BTC -> ETH`: mean daily diff `3,736.59`, CI `[3,365.27, 4,109.07]`, `n_days=58`, `n_bootstrap=1000`.
- `ETH -> BTC`: mean daily diff `8.73`, CI `[-0.30, 17.38]`, `n_days=65`, `n_bootstrap=1000`.

Interpretation: cross-asset execution is evaluated under purged splits. BTC->ETH supports RSEP loss mitigation versus cost-aware under the saved simulator assumptions. ETH->BTC is partial/mixed because the CI touches zero. Neither direction supports profitability or universal transfer.

## Principal ML Scientist view

- The original h-row boundary leakage blocker is cleared for the SGD paper-core evidence.
- The core empirical claim is preserved: prediction quality and execution usefulness diverge after costs, replay, stress, and asset transfer.
- Purged evidence weakens any broad "RSEP always wins" wording; RSEP should remain diagnostic/selective, not the main optimization claim.
- XGBoost/TCN/DeepLOB results are not rerun under purged protocol and should not be used as main quantitative claims unless rerun later.

## Reviewer ICDM view

- The split protocol is now auditable and purged for the core SGD BTC/ETH and BTC<->ETH evidence.
- The paper can remove the "missing h-row purged results" blocker, but it is still not submission-ready until the PDF is reduced to at most 10 pages and the main tables/narrative point to purged artifacts.
- It remains essential to keep negative net PnL visible and avoid any live-trading or profitability claim.

## Decision

- **Purged evidence gate:** PASS for SGD within-asset and asset-held-out core evidence.
- **Submission readiness:** still **NOT submission-ready** until the 10-page Applied Track cut is done and the paper references only purged main evidence.

