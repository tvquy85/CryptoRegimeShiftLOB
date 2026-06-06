# P0-06 - Audit baseline DeepLOB/LOB-Transformer

## Mục tiêu

P0-06 bổ sung baseline deep LOB canonical để reviewer không thấy benchmark chỉ có tabular model và TCN. Hai model mới được cài native PyTorch trong `CryptoRegimeShift`, lấy cảm hứng kiến trúc từ `LOBFrame/models` nhưng không port nguyên code PyTorch Lightning hoặc các dependency/phụ thuộc input layout không khớp.

## Model đã bổ sung

- `deeplob_stage3_pilot`: DeepLOB-style CNN + inception + LSTM.
- `lob_transformer_stage3_pilot`: convolutional LOB stem + `TransformerEncoder`.

Cả hai nhận input chuẩn `[batch, 100, 40]`, trong đó 40 feature là 10 LOB levels đầu với thứ tự per level: relative ask price, log ask size, relative bid price, log bid size. Output là logits `[batch, 3]` cho `DOWN/FLAT/UP`.

## Smoke training

Smoke chạy trên `NVIDIA GeForce RTX 3090`, dùng source `data/predictions/predictions.parquet`, cap nhỏ:

- train windows: `20,000`
- validation windows: `5,000`
- test windows: `10,000`
- epochs: `1`

Kết quả artifact:

- `data/predictions/predictions_stage3_deeplob_pilot.parquet`
- `data/predictions/predictions_stage3_lob_transformer_pilot.parquet`
- `outputs/paper_assets/table_21_deep_baseline_status.csv`

## Kết luận kỹ thuật

Smoke pass: loader, GPU forward/backward, mixed precision, prediction writer và table generation đều chạy được. Unit tests forward-shape cũng pass cho DeepLOB và LOB-Transformer.

Tuy nhiên smoke metric cho thấy DeepLOB/Transformer tiny-run đang gần collapse majority class:

- DeepLOB smoke: macro-F1 `0.2445`, MCC `0.0000`, balanced accuracy `0.3333`.
- LOB-Transformer smoke: macro-F1 `0.2444`, MCC `-0.0102`, balanced accuracy `0.3332`.

Vì vậy không đưa hai smoke result này vào main execution claim. Nếu cần baseline deep LOB full evidence, nên mở follow-up riêng với ngân sách compute rõ ràng: train/pilot lớn hơn, kiểm tra class collapse, rồi mới quyết định có chạy full-row execution-ready inference hay không.

## Góc nhìn reviewer ICDM

Điểm mạnh: benchmark hiện có baseline deep LOB canonical và attention-style ở mức implementation-validated, không còn chỉ dựa vào SGD/XGBoost/TCN.

Điểm yếu còn lại: DeepLOB/Transformer chưa có full-row execution-ready artifact, nên paper không được dùng chúng để claim execution robustness. Cách viết an toàn là: các model này nằm trong artifact suite và smoke/pilot baseline; main evidence vẫn dựa trên SGD, XGBoost GPU và TCN stride-1 đã có full-row/comparative artifacts.

## Quyết định

Không mở full default pilot trong P0-06 vì smoke đã cho tín hiệu collapse và default run sẽ tốn thêm nhiều lượt đọc file prediction khoảng 46 GB cùng training nhiều epoch. Bước tiếp theo chỉ nên mở DeepLOB/Transformer full pilot nếu paper draft/reviewer thật sự yêu cầu baseline deep LOB có metric mạnh hơn smoke.
