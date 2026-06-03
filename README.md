# CryptoRegimeShift-LOB

Pipeline thực nghiệm cho benchmark và đánh giá chính sách HFT robust dưới dịch chuyển regime vi cấu trúc L2, phục vụ paper ICDM 2026.

## Mục tiêu nghiên cứu

- Audit dữ liệu L2 snapshot-level.
- Xây feature store causal, label cost-aware và taxonomy regime.
- Đánh giá forecasting baseline theo regime.
- Mô phỏng marketable execution với phí, latency và stress môi trường.
- Đánh giá forecast-to-execution degradation và RSEP.

## Giả định dữ liệu

- Dữ liệu raw hiện tại đặt ngoài project tại `../data/full2024`.
- Repo hiện đã xác nhận đủ 12 tháng `BOOK_BINANCE_BTC-USDT_*_2024.parquet`.
- Chưa thấy `ETH-USDT`; các tác vụ asset-held-out được giữ trong config nhưng là dependency mở.
- Dữ liệu là L2 snapshot, không phải message-level/L3. Không dùng để claim exact queue priority hay passive fill realism.

## Cấu hình đường dẫn

Chỉnh `configs/data_crypto_lake.yaml` nếu raw path thay đổi.

## Chạy smoke test

```powershell
cd CryptoRegimeShift
powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1
```

Smoke test dùng một lát cắt nhỏ của BTC tháng 1 để chạy audit, feature, labels, regimes, split, baseline, backtest, RSEP, report pack và unit tests.

## Chạy từng bước

```powershell
cd CryptoRegimeShift
python scripts/00_audit_data.py --config configs/data_crypto_lake.yaml --run-id manual_audit --stage stage_0_sanity_check
python scripts/01_build_features.py --config configs/features.yaml --run-id manual_features --stage stage_0_sanity_check
python scripts/02_label_regimes.py --config configs/regimes.yaml --run-id manual_regimes --stage stage_0_sanity_check
python scripts/03_make_splits.py --config configs/experiments_smoke.yaml --run-id manual_splits --stage stage_0_sanity_check
python scripts/04_train_forecasters.py --config configs/models.yaml --run-id manual_train --stage stage_0_sanity_check --model sgd
python scripts/05_backtest_forecasts.py --config configs/simulator.yaml --run-id manual_backtest --stage stage_0_sanity_check
python scripts/06_run_rsep.py --config configs/simulator.yaml --run-id manual_rsep --stage stage_0_sanity_check
python scripts/07_run_stress_grid.py --config configs/experiments_smoke.yaml --run-id manual_stress --stage stage_0_sanity_check
python scripts/08_generate_report_pack.py --config configs/experiments_smoke.yaml --run-id manual_report --stage stage_0_sanity_check
```

## Paper assets

- Bảng/tổng hợp nằm trong `outputs/tables` và `outputs/paper_assets`.
- Hình nằm trong `outputs/figures` và `outputs/paper_assets`.
- Audit stage bằng tiếng Việt nằm trong `audits/`.

## Claim boundaries

- Claim được phép: benchmark L2 snapshot, regime-held-out/stress evaluation, forecast-to-execution degradation, RSEP.
- Không claim: order-event reconstruction chính xác, queue priority, hidden liquidity, live-trading readiness.

## Dữ liệu và license

- Không commit raw paid data.
- Không commit token/API key.
- Giữ mọi raw path trong YAML config.

