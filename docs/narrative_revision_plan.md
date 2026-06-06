# P2-13 narrative revision plan

## Muc tieu

Chuyen narrative cua paper tu phong thu qua nhieu bang cum "khong claim" sang gia tri applied benchmark: nguoi dung co the lam gi voi benchmark, failure mode nao duoc phoi bay, va evaluation path nao co the tai lap. Boundary van giu nguyen: khong claim profitability, khong live trading, khong exact L3/queue priority, va cross-asset chi trong pham vi BTC-USDT <-> ETH-USDT.

## Defensive wording lap lai

| Section | Defensive wording hien tai | Rui ro reviewer |
| --- | --- | --- |
| Introduction | "not as a trading bot", "does not claim exact queue priority", "not live-trading readiness" | Lam contribution nghe nhu chu yeu la disclaimers |
| Introduction | "avoids two common overclaims", "does not infer..." | Lam contribution paragraph mat luc applied |
| Execution/Results | "not profitability evidence", "not a universal trading policy" | Can giu, nhung nen gan voi utility cua degradation diagnostic |
| Discussion | "This does not mean LOB forecasting is useless" | Coi nhu dang phan bua thay vi neu insight |
| Limitations | Nhieu cau rieng le ve hidden liquidity, cancellations, passive fill, live deployment | Lap lai boundary da co trong Methods |
| Conclusion | "not a universal winner", "does not convert negative net PnL..." | Ket bai phong thu, chua chot duoc benchmark utility |

## Mapping rewrite

| Defensive wording | Utility wording duoc dung |
| --- | --- |
| "not a trading bot" | "a reproducible evaluation path from prediction to degradation" |
| "does not claim profitability" | "net PnL is used as a controlled degradation diagnostic" |
| "not exact L3 replay" | "snapshot-level visible-depth replay standardizes comparable stress analysis" |
| "not universal transfer" | "BTC<->ETH transfer is reported directionally to expose asymmetry" |
| "RSEP is not a universal winner" | "RSEP is a diagnostic probe for when selective gates mitigate or fail" |
| "negative net PnL is not failure" | "negative net PnL localizes where apparent signal is destroyed" |

## Boundary can giu

- Khong dung cac cum: profitable strategy, live-ready system, exact queue replay, universal profitable policy, deployment-ready trading.
- Duoc noi: loss mitigation, degradation diagnostic, visible-depth approximation, source-validation-only tuning, BTC<->ETH evaluated.
- RSEP phai duoc mo ta la selective-execution diagnostic/probe, khong phai trading strategy.
- L2 replay phai duoc mo ta la snapshot-level visible-depth approximation, khong phai venue-specific live execution.

## Reviewer-facing checklist

- Benchmark utility: paper noi ro nguoi dung co the so sanh model ranking tu forecasting sang execution.
- Exposed failure modes: cost, latency, spread, depth, regime, calibration, cross-asset shift.
- Reproducible path: causal features -> labels -> regimes -> chronological split -> forecasts -> replay -> stress -> bootstrap -> claim-evidence map.
- Applied insight: forecasting signal va execution usefulness co the diverge, va benchmark lam divergence do do duoc.
- Claim discipline: boundary van co, nhung nam trong Responsible Use/Limitations thay vi lap lai o moi section.
