# Audit P1-09: Cross-Asset Transfer Asymmetry

- run_id: `p1_09_cross_asset_asymmetry_v001`
- Muc tieu: giai thich directional asymmetry BTC->ETH va ETH->BTC bang distribution, label/regime mix va calibration evidence.
- Pham vi: chi doc saved artifacts; khong train lai, khong inference lai, khong target-validation tuning.

## Ket qua chinh

- BTC->ETH: macro-F1=0.4325, MCC=0.1486, ECE=0.1835, RSEP net=-74466.38.
- ETH->BTC: macro-F1=0.4839, MCC=0.2424, ECE=0.1051, RSEP net=-1144.75.
- Source-only protocol: scaler/model fit tren source train; policy/RSEP threshold tune tren source validation; target test chi dung de report.

## Principal ML Scientist view

Asymmetry khong nen duoc doc nhu noise. No consistent with domain shift trong scale gia, liquidity, volatility, label/regime distribution va calibration. Dieu nay lam asset-held-out tro thanh diagnostic quan trong hon mot average transfer score.

## Reviewer ICDM view

Bang va narrative moi giup giam nghi ngo ve viec paper chi bao cao hai huong ma khong giai thich. Claim van phai hep: BTC<->ETH duoc evaluate, khong claim universal transfer hay profitability.

## Decision

PASS cho paper hardening. Dua bang diagnostic vao appendix/main discussion va giu cross-asset results theo tung huong.
