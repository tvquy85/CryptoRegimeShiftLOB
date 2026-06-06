# P1-09 Cross-Asset Transfer Asymmetry Narrative

Muc tieu cua audit nay la giai thich vi sao BTC->ETH va ETH->BTC khong nen bi average thanh mot diem transfer duy nhat.
Tat ca bang duoc tao tu artifact prediction/execution da co; khong train lai, khong tune tren target validation.

## Evidence chinh

- BTC->ETH co target/source median ratio: mid_price=0.0534, rel_spread=16.2823, top_of_book_depth=5.5300, total_depth_10=7.2804, vol_score=0.6838.
- ETH->BTC co target/source median ratio: mid_price=30.2153, rel_spread=0.0269, top_of_book_depth=0.0858, total_depth_10=0.0653, vol_score=0.8800.
- Calibration target-test: BTC->ETH ECE=0.1835, Brier=0.7133, macro-F1=0.4325, MCC=0.1486.
- Calibration target-test: ETH->BTC ECE=0.1051, Brier=0.5974, macro-F1=0.4839, MCC=0.2424.
- RSEP loss mitigation remains relative: BTC->ETH RSEP net=-74466.38, cost-aware net=-287991.44; ETH->BTC RSEP net=-1144.75, cost-aware net=-3697.46.

## Dien giai an toan cho paper

Ket qua consistent with mot multi-factor distribution shift: scale gia, spread/relative spread, visible depth, volatility, label mix, regime mix va calibration cung thay doi theo huong transfer.
Vi vay BTC->ETH va ETH->BTC phai duoc bao cao rieng. Average hai huong se che mat risk cua domain adaptation va co the tao narrative qua lac quan.
Audit nay khong chung minh universal market generalization va khong chung minh profitable cross-asset trading.
