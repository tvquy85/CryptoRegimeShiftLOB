# fix_v1.md — ICDM 2026 Applied Track Fix Plan

## 0. Mục tiêu của bản fix

Mục tiêu của `fix_v1` là biến bản paper hiện tại từ bản **13 trang / chưa đúng submission compliance** thành bản **submission-ready, đúng chuẩn ICDM 2026 Applied Track, tối đa 10 trang gồm cả references và appendices**.

Bản hiện tại đã cải thiện mạnh về nội dung khoa học: đã có công thức cost-aware label, split table, replay specification, RSEP pseudo-code, bootstrap confidence intervals, stress grid, cross-asset diagnostics và reproducibility narrative. Tuy nhiên, bản này vẫn **chưa được nộp ngay** vì còn các lỗi blocker:

1. PDF hiện tại dài **13 trang**.
2. ICDM 2026 Applied Track yêu cầu **tối đa 10 trang gồm bibliography và appendices**.
3. Applied Track là **single-blind**, nhưng paper vẫn để `Anonymous Authors`.
4. Split audit đang có câu rủi ro: `0-row purge; 50-event horizon overlap audited`.
5. Ký hiệu `\rho_t` đang bị dùng cho cả relative spread và regime assignment.
6. Cost threshold dùng one-way fee proxy nhưng execution PnL tính entry + exit fee; cần giải thích hoặc recompute.
7. DeepLOB/Transformer chỉ là smoke/pilot baseline nhưng wording có thể làm reviewer tưởng là full evaluated baseline.
8. Artifact/reproducibility sections hiện quá dài, nên phải chuyển phần checklist/claim map ra artifact package.

**Definition of done:** bản LaTeX cuối cùng compile ra PDF **không quá 10 trang**, có author block đúng single-blind, không còn notation conflict, không còn split-overlap ambiguity, không còn overclaim về DeepLOB/Transformer, và các bảng/figures còn lại đều trực tiếp phục vụ claim chính.

---

## 1. Quy tắc bắt buộc khi sửa

### 1.1. Page-limit rule

Paper phải nằm trong **10 trang IEEE two-column**, tính cả:

- Abstract
- Main text
- Figures
- Tables
- References
- Any appendix, nếu có

Không dùng appendix trong main PDF nếu làm vượt trang. Tất cả appendix-style content phải đưa sang artifact/repo.

### 1.2. Single-blind rule

Applied Track là single-blind. Bản submission phải có:

- Author names
- Affiliations
- Emails, nếu template yêu cầu

Không để:

```latex
Anonymous Authors
```

trừ khi submission system yêu cầu riêng. Nếu chưa chắc, chuẩn bị 2 bản:

- `main_applied_singleblind.tex`
- `main_anonymous_backup.tex`

Bản để nộp Applied Track mặc định là `main_applied_singleblind.tex`.

### 1.3. Không hy sinh các điểm reviewer cần

Khi rút gọn, **không được xóa** các thành phần sau:

- Exact cost-aware label formula.
- Chronological train/validation/test split table.
- Clear leakage/purge statement.
- L2 replay specification at sufficient detail.
- RSEP gate definition.
- Main forecast-to-execution table with bootstrap CI.
- Stress-grid endpoint or compact stress summary.
- BTC↔ETH cross-asset table.
- Responsible-use boundary: no profitability, no live trading, no exact queue priority.

---

## 2. Target page budget cho bản 10 trang

Bản hiện tại 13 trang. Cần cắt ít nhất 3 trang. Target phân bổ:

| Section | Target length | Action |
|---|---:|---|
| Abstract + Index Terms | 0.35 page | Giữ, chỉ rút nhẹ 10–15%. |
| I. Introduction | 1.00 page | Rút còn 5 đoạn ngắn. |
| II. Related Work | 0.55 page | Gộp 3 subsection thành 3 paragraph. |
| III. Data + Labels + Splits | 1.15 pages | Giữ Table I + Table II; cắt audit prose. |
| IV. Regimes + Forecasting | 1.00 page | Gộp Table III/IV; giữ Table V. |
| V. Forecast-to-Execution | 1.55 pages | Giữ replay + RSEP + main results; merge Algorithm/Table VII. |
| VI. Stress + Failure Analysis | 0.90 page | Giữ 1 figure hoặc 1 compact table, không giữ cả nhiều figure. |
| VII. Cross-Asset | 0.75 page | Merge Table XII/XIII nếu cần. |
| VIII–XI Reproducibility/Threats/Discussion/Limitations | 1.20 pages | Gộp thành 2 section ngắn. Move checklist/claim map to artifact. |
| Conclusion | 0.20 page | 1 paragraph. |
| References | 1.30–1.40 pages | Cắt còn khoảng 24–26 refs. |
| **Total** | **≤10 pages** | Không vượt. |

Ưu tiên chừa margin 0.1–0.2 page. Không cố nhồi đúng sát 10.00 trang vì compile variation có thể làm tràn sang trang 11.

---

## 3. Các phần phải move/delete để tiết kiệm trang

### 3.1. Move ra artifact/repo, không để trong main PDF

Chuyển các nội dung sau sang `ARTIFACTS.md`, `REPRODUCIBILITY.md`, hoặc supplementary artifact:

1. **Table XIV — Claim-to-evidence discipline.**
   - Lý do: tốt cho artifact nhưng không cần chiếm main PDF.
   - Trong paper chỉ giữ 1 câu:  
     “The artifact package includes a claim-to-evidence registry mapping each quantitative claim to its generating script, configuration, and locked result artifact.”

2. **Table XV — Reproducibility checklist.**
   - Lý do: checklist dài, chiếm nhiều không gian.
   - Trong paper chỉ giữ 1 đoạn 4–5 dòng tóm tắt.

3. **Full regime sensitivity details.**
   - Giữ 1 câu về UNKNOWN rate và sensitivity.
   - Move detailed sensitivity table to artifact.

4. **Long discussion of model-selection ledger.**
   - Giữ 1 paragraph ngắn trong Threats.
   - Move ledger details to `model_selection_audit.md`.

5. **Long responsible-use repetition.**
   - Giữ boundary trong Limitations.
   - Không lặp lại 4–5 lần “not live trading / not profitability”.

### 3.2. Merge tables

Hiện paper có quá nhiều bảng. Đề xuất:

| Current table | Action |
|---|---|
| Table I Chronological split audit | Keep. |
| Table II Default benchmark configuration | Keep, but compress to 6 rows if needed. |
| Table III Regime construction inputs | Merge into Table IV or delete. |
| Table IV Microstructure regime taxonomy | Compress to 5–6 regime groups, move full taxonomy to artifact. |
| Table V Forecasting metrics | Keep. |
| Table VI RSEP Algorithm | Merge with Table VII into one compact algorithm box. |
| Table VII RSEP term mapping | Merge with Table VI or move detailed mapping to artifact. |
| Table VIII Main execution with CI | Keep. This is central. |
| Table IX RSEP ablation | Optional. Keep only if space; otherwise move to artifact and mention in prose. |
| Table X Stress endpoints | Keep or merge with Table XI. |
| Table XI RobustnessAUC | Merge with Table X or move to artifact. |
| Table XII Cross-asset results | Merge with Table XIII. |
| Table XIII Cross-asset bootstrap | Merge with Table XII. |
| Table XIV Claim map | Move to artifact. |
| Table XV Checklist | Move to artifact. |

### 3.3. Figures

Current paper has at least 3 figures: fee stress, latency stress, worst-regime exposure.

For 10-page version:

- Keep **only Fig. 1 Fee stress** if it conveys the strongest degradation.
- Move latency stress and worst-regime exposure figures to artifact.
- If even Fig. 1 causes overflow, remove all figures and rely on compact stress table.

---

## 4. Section-by-section edit plan

## 4.1. Abstract

### Current issue

Abstract is acceptable but can be shortened. It already states:

- LOB directional metrics can overstate deployable signal.
- Benchmark is L2 crypto, regime-aware, forecast-to-execution.
- RSEP is diagnostic, not universal policy.
- Net PnL remains negative.
- Main contribution is methodological.

### Required edit

Shorten by 10–15%. Remove duplicate adjectives.

### Suggested replacement

```latex
\begin{abstract}
Limit order book (LOB) forecasting is often evaluated with directional metrics, but such metrics can overstate actionable signal when spread crossing, fees, latency, visible-depth limits, and regime shifts erode short-horizon edge. We present CryptoRegimeShift-LOB, a snapshot-level L2 crypto benchmark for studying forecast-to-execution degradation. The benchmark covers full-year BTC-USDT and ETH-USDT L2 snapshots and links causal feature construction, cost-aware ternary labels, diagnostic microstructure regimes, L2 snapshot replay, stress testing, bootstrap uncertainty, and BTC$\leftrightarrow$ETH transfer. We also evaluate Robust Selective Execution Policy (RSEP) as an interpretable selective-execution diagnostic. Results show that forecasting signal can be visible while net PnL remains negative after execution frictions; RSEP mitigates losses in some settings but does not establish profitability. The central contribution is an applied evaluation protocol showing why credible LOB benchmarks should be cost-aware, regime-aware, stress-tested, and explicit about L2 observational limits.
\end{abstract}
```

---

## 4.2. Introduction

### Current issue

Introduction is stronger than previous version but still a little long. Need keep applied contribution but reduce repetition.

### Target

Keep exactly 5 short paragraphs:

1. Problem: prediction metrics insufficient.
2. Microstructure/execution gap.
3. Why current LOB benchmarks insufficient.
4. Contributions.
5. Negative evidence as benchmark value.

### Delete or compress

- Remove the long cross-asset paragraph at end of Introduction.
- Move BTC↔ETH motivation to Cross-Asset section.
- Remove repeated “not universal / not live trading” sentence from Introduction; keep one scope sentence.

### Required contribution paragraph

Keep a compact version like:

```latex
This paper makes four applied benchmark contributions. First, it provides a full-year BTC-USDT and ETH-USDT L2 snapshot benchmark with chronological splits, causal features, and locked dataset statistics. Second, it defines cost-aware ternary labels and diagnostic microstructure regimes for by-regime forecasting and execution analysis. Third, it provides a reproducible forecast-to-execution path in which fixed predictions are passed through L2 snapshot replay, validation-tuned execution gates, stress grids, and day-level bootstrap. Fourth, it evaluates RSEP and BTC$\leftrightarrow$ETH transfer as diagnostic probes for when forecast signal survives, degrades, or fails under execution assumptions.
```

---

## 4.3. Related Work

### Current issue

Related Work has 3 subsections and is too long for a 10-page Applied Track paper.

### Required edit

Convert to 3 compact paragraphs without subsubsection over-expansion:

1. LOB forecasting and benchmarks.
2. Market microstructure and execution frictions.
3. Regime/stress/distribution shift and financial evaluation.

### Target length

Around 0.5 page.

### Suggested compressed version

```latex
\section{Related Work}
LOB forecasting is typically framed as short-horizon mid-price prediction. FI-2010 standardized supervised LOB evaluation, DeepLOB introduced CNN--LSTM modeling of book structure, and later studies extended the space to market-by-order data, transformer-style models, and benchmark comparisons. These works motivate our baseline families, but our contribution is not a new predictor; it is an execution-aware benchmark path that tests whether forecast signals remain meaningful after costs, regimes, and replay assumptions.

Market microstructure research shows that realized trading outcomes depend on trading rules, liquidity, adverse selection, order flow, and speed. For LOB forecasting, directional correctness is therefore insufficient: a signal must survive spread crossing, explicit fees, visible-depth constraints, and timing risk. Because our data are snapshot-level L2 observations, we evaluate a visible-depth market-order replay approximation and do not claim L3 reconstruction, queue priority, passive fills, or live deployment.

Our regime and stress design follows robustness and time-series evaluation principles: aggregate test metrics can hide distribution-shift failures, chronological validation is required to avoid leakage, and financial ML evaluation must account for transaction costs and data-snooping risk. CryptoRegimeShift-LOB combines these ideas into a domain-specific path: causal L2 features, cost-aware labels, diagnostic regimes, L2 replay, stress grids, bootstrap uncertainty, and BTC$\leftrightarrow$ETH transfer.
```

---

## 4.4. Data, labels, and split

### Current issue

This section is one of the strongest after revision, but contains too much audit prose and a dangerous split statement.

### Must keep

- Dataset scope: BTC-USDT/ETH-USDT, Binance, 2024, 20 bid/ask levels.
- Row counts.
- Table I split audit.
- Exact label formula.
- Table II default benchmark config.
- Causal feature statement.
- Training/validation/test roles.

### Must fix: split purge ambiguity

Current wording says locked Stage 3 artifacts had 0-row purge and 50-event overlap audited, then says future split generator drops last h rows. This is dangerous.

### Preferred fix

Recompute all reported results with purged split and state:

```latex
All reported results use row-contiguous chronological splits with an h-row embargo before each later split boundary. The last h rows before the train--validation boundary and the last h rows before the validation--test boundary are excluded from training and validation artifacts, respectively. This prevents label-horizon overlap across split boundaries. Training fits feature scalers, model parameters, and regime quantiles; validation tunes model-selection thresholds, execution thresholds, and RSEP parameters; and test is used only for final reporting.
```

### If results are not recomputed

Do **not** submit. Add this as blocker in internal notes:

```text
BLOCKER: Reported Stage 3 results were generated under a 0-row purge split with audited 50-event horizon overlap. Recompute all forecasting, execution, stress, bootstrap, and cross-asset artifacts using h-row purged splits before submission.
```

### Must fix: fee threshold explanation

Current formula:

```latex
\tau_t = (1+\kappa)\rho_t + f/10000
```

Execution charges entry and exit fees. Reviewer may ask why label uses only one fee.

Two options:

#### Option A — Keep formula, explain it

Add:

```latex
The label threshold is a one-step local significance proxy rather than the full round-trip execution cost. Round-trip fees, latency, visible-depth sweep, and partial fills are applied only in the execution replay layer. This separation prevents the supervised label from embedding simulator-specific assumptions while still requiring UP/DOWN moves to exceed a local spread-and-fee proxy.
```

#### Option B — Change formula to round-trip fee

```latex
\tau_t = (1+\kappa)\rho_t + 2f/10000
```

Only choose Option B if all labels, model metrics, execution results, and tables are recomputed. Otherwise use Option A.

---

## 4.5. Notation conflict fix

### Current issue

The paper uses `\rho_t` for both:

1. Relative spread in label threshold.
2. Regime assignment variable: `\rho_t = g(z_t), \rho_t \in R`.

This is unacceptable.

### Required fix

Use:

- `\rho_t` only for relative spread.
- Use `r_t` or `\psi_t` for regime label.

Replace:

```latex
\rho_t = g(z_t), \rho_t \in R
```

with:

```latex
r_t = g(z_t), \quad r_t \in \mathcal{R}
```

Then update all references:

- `regime \rho_t` → `regime r_t`
- `\rho_t \in R` → `r_t \in \mathcal{R}`
- Do not use `R` alone if it can be confused with return or real numbers.

---

## 4.6. Regime taxonomy section

### Current issue

Tables III and IV consume too much space. The full 11-regime taxonomy is detailed but not necessary in main PDF.

### Required edit

- Delete Table III.
- Replace Table IV with a compressed taxonomy table of 5 rows.
- Move full 11-regime taxonomy to artifact.

### Suggested compact table

```latex
\begin{table}[t]
\caption{Compressed regime groups used for diagnostic reporting. Full priority rules and thresholds are included in the artifact package.}
\centering
\small
\begin{tabular}{p{0.28\linewidth}p{0.62\linewidth}}
\toprule
Group & Diagnostic role \\
\midrule
Liquidity stress & Drought or mild depth/spread deterioration. \\
Volatile states & High volatility with liquid or illiquid visible depth. \\
Momentum/adverse states & Directional pressure and adverse-selection risk. \\
Choppy/recovery states & Reversal-prone or post-shock transition states. \\
Calm/transition/unknown & Low-stress, balanced, or ambiguous snapshots. \\
\bottomrule
\end{tabular}
\end{table}
```

### Keep one sensitivity sentence only

```latex
The regime audit reports UNKNOWN explicitly: BTC-USDT has 13.19\% overall UNKNOWN share and ETH-USDT has 12.68\%; alternative quantile settings change UNKNOWN rates but keep roughly 86\% agreement with the baseline taxonomy.
```

Move exact relaxed/strict sensitivity numbers to artifact.

---

## 4.7. Forecasting baselines

### Current issue

Current wording mentions DeepLOB-style and Transformer-style baselines but says they are pilot/smoke unless full-row artifacts exist. Reviewer may see this as weak or misleading.

### Required decision

Choose one path.

### Path A — Full baseline path, preferred

Run full-row DeepLOB-style and lightweight Transformer results. Then add them to forecasting table and, if possible, execution table.

Required artifacts:

- Forecasting metrics for DeepLOB.
- Forecasting metrics for Transformer.
- Prediction artifacts.
- Execution replay outputs or clear explanation why execution replay not reported.

### Path B — Honest artifact-only path

If full training is not feasible, do not claim them as evaluated baselines. Rewrite:

```latex
The full-row reported baselines are SGD, XGBoost, and TCN. The artifact suite additionally includes implementation-validated DeepLOB-style CNN--LSTM and lightweight Transformer modules with forward-shape and smoke-training tests, but these are not used for the main empirical claims because full-row prediction artifacts were not generated under the locked Stage 3 configuration.
```

Also remove any wording that implies DeepLOB/Transformer contributed to main findings.

### Target wording

Use Path B unless full results are available.

---

## 4.8. Forecast-to-execution / Replay / RSEP

### Current issue

Replay and RSEP are now reviewable, but too verbose. Need compress while keeping exactness.

### Keep

- Market buy sweeps asks, sell sweeps bids.
- Latency index.
- VWAP formula.
- Partial-fill rule summary.
- Fee on matched filled notional.
- Zero-fill/skip invalid book statement.
- RSEP expected edge and threshold formula.
- Strict abstain equality.
- θ validation-tuned, λ fixed.

### Move to artifact

- Full edge-case list.
- Detailed synthetic test descriptions.
- Full term mapping table if too long.

### Merge Algorithm 1 and Table VII

Instead of Table VI + Table VII, use one compact algorithm box:

```latex
\begin{algorithm}[t]
\caption{RSEP gate}
\small
\begin{algorithmic}[1]
\STATE Compute $\hat e_t=\sum_y p_t(y)\mu_y$ using train-split class-return means.
\STATE Compute $\hat c_t=\rho_t+f/10000$.
\STATE Set $E^{req}_t=\hat c_t+\lambda_{lat}r^{lat}_t+\lambda_{liq}r^{liq}_t+\lambda_{adv}r^{adv}_t+\lambda_{reg}r^{reg}_t+\theta$.
\STATE Return BUY if $\hat e_t>E^{req}_t$, SELL if $\hat e_t<-E^{req}_t$, otherwise abstain.
\end{algorithmic}
\end{algorithm}
```

Then in prose:

```latex
The risk terms are absolute latency sensitivity, positive liquidity-drought score, positive adverse-selection score, and a categorical regime penalty. The $\lambda$ values are fixed benchmark constants; $\theta$ is selected on validation rows. The artifact package maps each term to code variables and unit tests.
```

This saves more space than keeping the detailed term mapping table.

---

## 4.9. Main execution table

### Current status

Table VIII is strong and should remain.

### Required edit

Keep Table VIII but reduce width/columns if needed.

Possible compact version:

| Model | Policy | Trades | Net PnL [95% CI] | Net/trade [95% CI] |
|---|---:|---:|---:|---:|

Drop `Days` column if all rows have 65 days; state in caption:

```latex
All rows use 65 held-out test days.
```

This saves horizontal and vertical space.

### Keep interpretation

Keep these sentences:

```latex
All policies remain net negative after costs. Positive RSEP-minus-cost-aware differences therefore indicate relative loss mitigation only, not profitability. The stride-1 TCN result is negative evidence: stronger macro-F1 does not imply better selective execution.
```

---

## 4.10. RSEP ablation

### Current issue

Table IX costs space and is less central than Table VIII.

### Required edit

Move Table IX to artifact unless page budget allows.

Replace with one sentence:

```latex
Ablation artifacts show the same pattern: removing latency, liquidity, adverse-selection, or regime components makes the selected ablation setting more negative, but all variants remain net negative; hence the evidence supports risk filtering, not profitability.
```

---

## 4.11. Stress section

### Current issue

Stress section has multiple figures/tables and detailed prose. Need compress.

### Keep

- Exact stress grid values.
- No retraining/no retuning rule.
- Fee stress is dominant.
- One compact table of endpoints/AUC.

### Required edit

Merge Table X and Table XI:

```latex
\begin{table}[t]
\caption{Stress-grid summary. Entries are net PnL endpoints and RobustnessAUC; all remain negative.}
\centering
\small
\begin{tabular}{lrrrr}
\toprule
Model & Fee10 & Lat10 & Spread2 & Depth0.5 \\
\midrule
SGD & -65082 & -6097 & -4510 & -4484 \\
XGB & -69609 & -5761 & -4419 & -4345 \\
TCN-1 & -10587 & -955 & -820 & -818 \\
\bottomrule
\end{tabular}
\end{table}
```

If AUC must remain, put it in the artifact, not main paper. Or add AUC in parentheses only if space.

### Figures

Keep only one figure if there is room. Preferred:

- Keep Fee stress curve.
- Move Latency stress and Worst-regime exposure figures to artifact.

If still over 10 pages, remove all stress figures.

---

## 4.12. Cross-asset section

### Current issue

Good content, but can be compressed.

### Required edit

Merge Table XII and Table XIII:

```latex
\begin{table}[t]
\caption{BTC$\leftrightarrow$ETH asset-held-out evaluation. Bootstrap difference is RSEP-full minus cost-aware; positive values mean relative loss mitigation only.}
\centering
\small
\begin{tabular}{lrrrrr}
\toprule
Direction & F1 & MCC & RSEP net & Cost net & Diff CI \\
\midrule
BTC$\to$ETH & .4325 & .1486 & -74466 & -287991 & [3314,4048] \\
ETH$\to$BTC & .4839 & .2424 & -1145 & -3697 & [34,45] \\
\bottomrule
\end{tabular}
\end{table}
```

Then prose:

```latex
The directions are not averaged because the audit shows large distribution shifts in price scale, relative spread, depth, label mix, regime mix, and calibration. BTC$\to$ETH faces much higher target relative spread, whereas ETH$\to$BTC evaluates on a more FLAT-heavy BTC test split. The claim is limited to BTC-USDT and ETH-USDT.
```

This is enough. Move detailed ratios to artifact if page tight.

---

## 4.13. Reproducibility, threats, discussion, limitations

### Current issue

These sections are too long. They can be consolidated.

### Required structure

Replace current Sections VIII–XII with:

- `VIII. Reproducibility and Validity`
- `IX. Discussion and Responsible Use`
- `X. Conclusion`

This saves headings and repetition.

### VIII. Reproducibility and Validity target

0.6–0.7 page.

Must include:

- Restricted raw data statement.
- Public artifacts.
- Synthetic sample/smoke pipeline.
- Claim-evidence registry.
- Leakage controls.
- Main threats.

Suggested text:

```latex
\section{Reproducibility and Validity}
The artifact package separates restricted commercial data from public reproducibility assets. Public assets include schema documentation, benchmark configurations, checksum manifests, split audits, paper-ready tables, a claim-to-evidence registry, and a synthetic 20-level L2 sample. A one-command smoke pipeline runs data audit, feature construction, cost-aware labels, regime assignment, chronological splitting, forecasting, L2 replay, RSEP, stress evaluation, and report generation on the synthetic sample. The synthetic data are not used for scientific claims; they verify executable code paths.

The main internal-validity risk is temporal leakage. We use chronological splits, training-only scalers and regime quantiles, validation-only threshold/RSEP selection, and test-only reporting. Reported submission results should use an $h$-row embargo before validation and test boundaries. The main construct-validity limit is that net PnL is a diagnostic replay quantity, not live trading profit: L2 snapshots do not observe hidden liquidity, cancellations, queue position, passive fills, venue routing, or full market impact. External validity is limited to Binance BTC-USDT and ETH-USDT in 2024; other assets, venues, or L3 feeds require new experiments.
```

### IX. Discussion and Responsible Use target

0.5 page.

Must include:

- Practical benchmark takeaways.
- Negative PnL as informative.
- No deployment/profit claim.
- Future extensions.

Suggested text:

```latex
\section{Discussion and Responsible Use}
The empirical pattern is consistent: forecasting signal exists but is fragile after execution assumptions. The benchmark's practical value is an audit trail from prediction to degradation. Users can locate whether a model fails before costs, after spread crossing, under latency, in particular regimes, or under BTC$\leftrightarrow$ETH transfer.

Model ranking is evaluation-dependent: XGBoost leads accuracy, TCN stride-1 leads macro-F1 among full-row baselines, and tabular models remain competitive under MCC and execution diagnostics. Stress testing shows that fee assumptions dominate the reported grid, while latency, spread, and depth remain necessary axes for diagnosing execution fragility. RSEP shows that selective gates can reduce exposure in some settings, but the TCN result prevents a universal-win claim.

CryptoRegimeShift-LOB is intended for research evaluation, robustness analysis, and risk-aware model assessment. It is not investment advice, a trading recommendation, or evidence that an automated strategy is ready for deployment. Future extensions can add L3 data, passive-fill simulation, additional venues, or more assets by reusing the same evidence map and upgrading claims only when the new observational layer supports them.
```

### Conclusion target

1 paragraph, 5–6 lines.

---

## 4.14. References

### Current issue

References occupy too much space. Need cut to essential citations.

### Target

Keep 24–26 references. Remove duplicates and optional citations.

### Must keep

1. Market microstructure survey / O’Hara / Gould.
2. HFT latency / Budish / Aquilina.
3. FI-2010.
4. DeepLOB.
5. Sirignano or market-by-order paper.
6. Recent LOB benchmark/microstructural guide.
7. XGBoost.
8. TCN.
9. Dataset shift / WILDS or Quinonero-Candela.
10. Time-series CV.
11. Bootstrap.
12. Stationary bootstrap if day-level/time dependence used.
13. White Reality Check or Backtest Overfitting.
14. Crypto market microstructure/regulatory reference.
15. Crypto Lake data docs if using their data.

### Remove or consolidate

- Duplicate Aquilina BIS working paper if journal version already cited.
- Too many general dataset shift references; keep 1–2.
- Too many financial overfitting references; keep 2.
- Remove references not cited in the shortened text.
- If `LiT` not actually evaluated, cite only if mentioned in compressed related work.
- If DeepLOB/Transformer smoke baselines are not main results, do not over-cite model family.

---

## 5. Critical blockers to resolve before final PDF

## 5.1. Blocker A — 13 pages

**Fix:** reduce to ≤10 pages.

Checklist:

```text
[ ] Remove Table XIV from main PDF.
[ ] Remove Table XV from main PDF.
[ ] Merge Table XII and XIII.
[ ] Merge or remove Table X and XI.
[ ] Remove Table IX or move to artifact.
[ ] Delete Table III.
[ ] Compress Table IV.
[ ] Keep at most one figure.
[ ] Compress Related Work.
[ ] Merge Sections VIII–XII into 2 short sections + conclusion.
[ ] Cut references to around 24–26.
[ ] Compile and verify page count ≤10.
```

## 5.2. Blocker B — Author anonymity

**Fix:** replace `Anonymous Authors` with actual authors for Applied Track single-blind.

Checklist:

```text
[ ] Author names inserted.
[ ] Affiliations inserted.
[ ] Emails inserted if required.
[ ] Acknowledgements either included or omitted according to policy.
[ ] Artifact links do not violate review policy.
```

## 5.3. Blocker C — Split purge

**Fix:** recompute or explicitly block submission.

Preferred:

```text
[ ] h-row embargo implemented.
[ ] Forecasting metrics recomputed.
[ ] Execution results recomputed.
[ ] Stress-grid results recomputed.
[ ] Bootstrap CIs recomputed.
[ ] Cross-asset results recomputed.
[ ] Paper table values updated.
```

If not recomputed:

```text
[ ] Mark paper as NOT submission-ready.
```

## 5.4. Blocker D — Notation conflict

**Fix:** replace regime `\rho_t` with `r_t`.

Checklist:

```text
[ ] Relative spread remains `\rho_t`.
[ ] Regime label becomes `r_t`.
[ ] Regime set becomes `\mathcal{R}`.
[ ] No duplicate use remains.
```

## 5.5. Blocker E — DeepLOB/Transformer scope

**Fix:** either full evaluate or downgrade wording.

Checklist:

```text
[ ] If full artifacts exist: add results.
[ ] If no full artifacts: state clearly they are smoke-tested artifact modules only.
[ ] Do not list them as main evaluated baselines.
```

---

## 6. Minimal 10-page paper outline

Use this final structure:

```latex
\title{CryptoRegimeShift-LOB: A Regime-Aware L2 Crypto Benchmark for Forecast-to-Execution Degradation}

\begin{abstract}
...
\end{abstract}

\section{Introduction}
% 5 short paragraphs, 1 page max.

\section{Related Work}
% 3 compact paragraphs, no long subsections.

\section{Data and Benchmark Construction}
% Dataset, audit, split table, label formula, config table.

\section{Regimes and Forecasting Baselines}
% Compact regime taxonomy, forecasting table.

\section{Forecast-to-Execution Evaluation}
% Replay specification, RSEP algorithm, main execution table.

\section{Stress and Cross-Asset Analysis}
% Stress grid, compact stress table, cross-asset table.

\section{Reproducibility and Validity}
% Artifact pack, leakage controls, construct/external validity.

\section{Discussion and Responsible Use}
% Practical takeaways and no-deployment boundary.

\section{Conclusion}
% One paragraph.

\bibliographystyle{IEEEtran}
\bibliography{refs}
```

Do not keep separate sections for:

- Evidence Mapping and Reproducibility
- Threats to Validity
- Discussion
- Limitations and Responsible Use
- Reproducibility Checklist

Those are too expensive for a 10-page submission. Their content must be compressed into the two sections above.

---

## 7. Detailed cut plan by estimated page saving

| Edit | Estimated saving |
|---|---:|
| Move Table XIV and Table XV to artifact | 0.7–0.9 page |
| Compress Related Work | 0.3–0.4 page |
| Delete Table III and compress Table IV | 0.4–0.5 page |
| Merge RSEP Algorithm and term mapping | 0.3–0.4 page |
| Move RSEP ablation table to artifact | 0.2 page |
| Keep one stress figure only or none | 0.3–0.6 page |
| Merge stress tables | 0.2 page |
| Merge cross-asset tables | 0.15–0.25 page |
| Merge Sections VIII–XII | 0.8–1.2 page |
| Cut references by 6–8 entries | 0.25–0.4 page |
| **Total expected saving** | **3.6–4.8 pages** |

This is enough to bring 13 pages down to 9.6–10.0 pages.

---

## 8. Final reviewer-risk checklist

Before submission, inspect the PDF as a hostile ICDM Applied Track reviewer:

### Compliance

```text
[ ] PDF is ≤10 pages including references.
[ ] IEEE two-column format.
[ ] Single-blind author block is correct.
[ ] No appendix pushes paper beyond 10 pages.
```

### Claims

```text
[ ] No profitability claim.
[ ] No live-trading readiness claim.
[ ] No exact queue-priority claim.
[ ] No hidden-liquidity modeling claim.
[ ] No universal RSEP winner claim.
[ ] No cross-asset generalization beyond BTC↔ETH.
```

### Technical audit

```text
[ ] τt formula exact.
[ ] Label threshold constants exact.
[ ] h-row purge/embargo clean.
[ ] Validation split explicit.
[ ] RSEP terms defined.
[ ] Replay simulator defined.
[ ] Bootstrap CI reported for main table.
[ ] Stress grid exact and no retuning under stress.
```

### Presentation

```text
[ ] Negative PnL framed as degradation evidence.
[ ] Deep baselines not overstated.
[ ] Tables are readable in two columns.
[ ] No table spills or unreadably tiny font.
[ ] References are relevant and cited.
```

---

## 9. Priority order for implementation

Run edits in this order:

1. **Fix split purge and recompute results** if not already recomputed.
2. **Fix notation conflict**: `\rho_t` vs `r_t`.
3. **Fix author block** for single-blind Applied Track.
4. **Cut to 10 pages** using the table/section moves above.
5. **Clarify label fee proxy**.
6. **Clarify DeepLOB/Transformer scope**.
7. **Compile and check page count**.
8. **Run claim-evidence check** after all values are updated.
9. **Final PDF read-through** for overclaims.

Do not spend time polishing prose before fixing page count and split purge. Page count and split purge are acceptance-critical.

---

## 10. Suggested Codex instruction for applying this file

Use the following instruction when asking Codex to implement `fix_v1.md`:

```text
Apply fix_v1.md to the LaTeX paper. The target is an ICDM 2026 Applied Track submission of at most 10 pages including references. Do not invent or change numerical results unless the corresponding artifact is regenerated. If h-row purged split results are not available, stop and mark the paper as NOT submission-ready. Preserve the core claims: cost-aware L2 benchmark, forecast-to-execution degradation, RSEP as diagnostic only, net-negative execution, stress sensitivity, and BTC↔ETH-only transfer. Move detailed claim maps, reproducibility checklist, regime sensitivity, model-selection ledger, and ablation details to artifact text instead of main PDF.
```
