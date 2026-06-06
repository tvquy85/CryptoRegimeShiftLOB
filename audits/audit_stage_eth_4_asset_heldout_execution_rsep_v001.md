# Audit Stage ETH-4 - Asset-held-out execution/RSEP

- `run_id`: `stage3_16_asset_eth_to_btc_execution_purged_v001`
- Mục tiêu: kiểm tra cross-asset execution/RSEP khi policy được tune trên source validation và evaluate trên target test.
- Phạm vi: BTC->ETH và ETH->BTC với checkpoint SGD asset-held-out đã có; không train thêm model và không dùng target test để tune.
- Boundary: không claim profitability, không claim universal policy generalization.

## Kết quả execution theo hướng

### `btc_to_eth`
- `RSEP-full`: trades `500819`, gross `25679.52`, net `-74466.38`, turnover `147730.20`.
- `RSEP-full`: trades `517363`, gross `26632.08`, net `-76822.20`, turnover `152594.32`.
- `cost_aware_threshold`: trades `1887016`, gross `89326.52`, net `-287991.44`, turnover `557704.00`.
- `cost_aware_threshold`: trades `1925421`, gross `91453.76`, net `-293544.15`, turnover `568907.55`.
- `naive_threshold`: trades `1498862`, gross `66691.33`, net `-233008.45`, turnover `444038.62`.
- `naive_threshold`: trades `1481428`, gross `65642.00`, net `-230570.83`, turnover `438926.08`.
### `eth_to_btc`
- `RSEP-full`: trades `9129`, gross `677.22`, net `-1144.75`, turnover `99.57`.
- `RSEP-full`: trades `33827`, gross `2443.78`, net `-4308.40`, turnover `372.63`.
- `cost_aware_threshold`: trades `27052`, gross `1708.33`, net `-3697.46`, turnover `300.80`.
- `cost_aware_threshold`: trades `34985`, gross `2115.15`, net `-4875.61`, turnover `388.44`.
- `naive_threshold`: trades `47235`, gross `1223.43`, net `-8215.68`, turnover `519.16`.
- `naive_threshold`: trades `54006`, gross `1504.21`, net `-9288.17`, turnover `594.07`.

## Bootstrap RSEP vs cost-aware

- `btc_to_eth`: mean diff `3681.47`, CI [`3314.02`, `4048.20`], n_days `58`, n_bootstrap `1000`.
- `eth_to_btc`: mean diff `39.27`, CI [`34.08`, `44.53`], n_days `65`, n_bootstrap `1000`.
- `btc_to_eth`: mean diff `3736.59`, CI [`3365.27`, `4109.07`], n_days `58`, n_bootstrap `1000`.
- `eth_to_btc`: mean diff `8.73`, CI [`-0.30`, `17.38`], n_days `65`, n_bootstrap `1000`.

## Stress/RSEP

- Stress axes đã chạy: depth_multiplier, fee_bps, latency_events, spread_multiplier.
- `btc_to_eth` fee stress: net từ `52926.25` ở level `0.00` xuống `-1007910.67` ở level `10.00`.
- `eth_to_btc` fee stress: net từ `86958.55` ở level `0.00` xuống `-65078.06` ở level `10.00`.

## Principal ML Scientist view

- Thiết kế tune source-validation-only là đúng để tránh leakage cross-asset.
- Nếu net PnL âm, kết quả vẫn có giá trị vì nó kiểm tra liệu forecasting generalization có chuyển thành execution edge hay không.
- Nếu RSEP chỉ thắng một hướng hoặc CI mixed, nên trình bày là partial cross-asset execution evidence.

## Reviewer ICDM view

- Điểm mạnh: cross-asset không còn dừng ở forecasting; có execution, bootstrap và stress theo target asset.
- Điểm cần hạ giọng: không được viết như universal profitable cross-asset policy.
- Evidence này nên dùng để nâng claim từ `forecasting-only` lên `forecasting + execution evaluated`.

## Quyết định

- PASS kỹ thuật nếu cả hai hướng có execution table, bootstrap n_days > 1 và stress không rỗng.
- Kết luận khoa học phụ thuộc CI/stress: SUPPORTED nếu ổn định, PARTIAL nếu mixed hoặc net âm nặng.
