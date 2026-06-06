# DATA_CARD.md

## Mục tiêu dữ liệu

CryptoRegimeShift-LOB dùng dữ liệu snapshot L2 order book để đánh giá forecast-to-execution degradation dưới microstructure regime shifts. Bài toán không phải xây trading bot sinh lời; mục tiêu là benchmark/failure-analysis có kiểm soát.

## Dữ liệu thực nghiệm chính

- Venue/exchange: Binance.
- Assets: `BTC-USDT` và `ETH-USDT`.
- Năm: 2024.
- Độ sâu: 20 bid levels và 20 ask levels.
- Dạng quan sát: snapshot-level L2, không phải message-level L3.
- Cột chính: timestamp, sequence number, symbol/exchange, giá và size từng level.

Số khóa dùng trong paper nằm ở `outputs/paper_assets/table_1_dataset_stats.csv`. Raw data thương mại không được redistributable trong artifact public.

## Synthetic sample public

`sample_data/l2_synthetic_sample.parquet` là dữ liệu synthetic nhỏ để reviewer chạy smoke pipeline. Nó giữ schema giống raw L2:

- `origin_time`, `received_time`, `sequence_number`, `symbol`, `exchange`.
- `bid_0_price` ... `bid_19_price`, `bid_0_size` ... `bid_19_size`.
- `ask_0_price` ... `ask_19_price`, `ask_0_size` ... `ask_19_size`.
- Book không crossed ở best level.
- Interval khoảng 100 ms.

Synthetic sample không phản ánh phân phối thị trường thật và không được dùng để claim kết quả paper.

## Hạn chế dữ liệu

- Không có queue priority, hidden liquidity, cancellation stream, passive fill, routing hoặc matching-engine detail.
- Simulator là L2 market-order replay approximation.
- Cross-asset claim chỉ là BTC<->ETH đã được evaluate trong phạm vi dữ liệu này, không phải universal policy generalization.
- Net PnL trong paper là diagnostic quantity, không phải live trading profitability.

## Data availability

Raw BTC/ETH snapshots bị hạn chế bởi license/kích thước. Artifact public thay thế bằng schema, synthetic sample, code, configs, checksums, audit tables và exact commands.
