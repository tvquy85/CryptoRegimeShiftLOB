# fix_v2.md — Final ICDM 2026 Applied Track Revision Plan for Codex

## 0. Purpose

This file describes the **final surgical revision** required before submitting the current 10-page ICDM Applied Track paper.

The current paper is scientifically competitive but still has several submission-readiness and reviewer-risk issues:

1. The author block still contains placeholder text: `Author Name(s) / Affiliation(s) / Email(s)`.
2. The artifact/reproducibility claims need to be made operational and checkable.
3. The RSEP ablation paragraph still reports a standalone number without the corresponding ablation table in the main paper.
4. The RSEP expected-edge estimate is intentionally simple but should be framed more clearly as a diagnostic heuristic, not a calibrated trading edge.
5. The final PDF must remain **exactly within 10 pages including references** after all edits.
6. The final paper must have no unresolved citations, no placeholder text, no undefined references, no accidental overclaims, and no submission-format errors.

## Explicit non-goal

Do **not** implement the previous optional suggestion to remove or move Fig. 2 / Fig. 3. The user explicitly asked to ignore that suggestion.

Therefore:

```text
DO NOT remove Fig. 2.
DO NOT remove Fig. 3.
DO NOT move Fig. 2 or Fig. 3 to artifact only.
Keep the current figures unless the user gives a separate explicit instruction later.
```

---

## 1. Global rules for Codex

Apply these rules throughout the revision.

```text
1. Do not invent numerical results.
2. Do not change table values unless the corresponding artifact is regenerated.
3. Do not introduce profitability, live-trading, exact queue-priority, hidden-liquidity, passive-fill, or universal cross-asset claims.
4. Preserve the 10-page limit including references.
5. Preserve the main scientific contribution:
   - L2 crypto benchmark
   - cost-aware labels
   - purged chronological split
   - regime diagnostics
   - L2 snapshot replay
   - RSEP as diagnostic only
   - net-negative execution evidence
   - stress testing
   - bootstrap uncertainty
   - BTC↔ETH-only transfer
6. Keep Fig. 2 and Fig. 3 in the main paper.
7. If required data or author information is missing, mark the paper as NOT SUBMISSION-READY instead of fabricating.
```

---

## 2. Task A — Replace author placeholder

### Problem

The current first page still contains placeholder author metadata:

```latex
Author Name(s)
Affiliation(s)
Email(s)
```

This is not submission-ready for ICDM Applied Track single-blind submission.

### Required action

Search in `main.tex` or the active LaTeX source for the author block.

Likely current pattern:

```latex
\author{
\IEEEauthorblockN{Author Name(s)}
\IEEEauthorblockA{Affiliation(s)\\
Email(s)}
}
```

### Replacement rule

If actual author information is available in one of the following files:

- `AUTHORS.md`
- `author_info.tex`
- `metadata.yaml`
- `paper_metadata.yaml`
- explicit variables provided by the user

then replace the placeholder block with actual author names, affiliations, and emails.

If no actual author information is available, do **not** invent names. Insert a compile-visible TODO marker only in a separate internal file, and mark the main paper as:

```text
BLOCKED: actual single-blind author block not provided.
```

### Preferred LaTeX pattern

Use this format if there are multiple authors from one institution:

```latex
\author{
\IEEEauthorblockN{First Author, Second Author, Third Author}
\IEEEauthorblockA{
Department / Faculty / Lab\\
Institution Name\\
City, Country\\
email1@domain.edu, email2@domain.edu, email3@domain.edu
}
}
```

Use this format if there are multiple affiliations:

```latex
\author{
\IEEEauthorblockN{First Author\IEEEauthorrefmark{1}, Second Author\IEEEauthorrefmark{2}, Third Author\IEEEauthorrefmark{1}}
\IEEEauthorblockA{\IEEEauthorrefmark{1}Institution 1, City, Country\\
Emails: email1@domain.edu, email3@domain.edu}
\IEEEauthorblockA{\IEEEauthorrefmark{2}Institution 2, City, Country\\
Email: email2@domain.edu}
}
```

### Acceptance criteria

```text
[ ] No `Author Name(s)` remains.
[ ] No `Affiliation(s)` remains.
[ ] No `Email(s)` placeholder remains.
[ ] Author block matches single-blind Applied Track expectations.
[ ] Final PDF still has at most 10 pages.
```

---

## 3. Task B — Strengthen artifact/reproducibility statement

### Problem

The paper states that the artifact package contains:

- schema documentation
- benchmark configs
- checksum manifests
- split audits
- paper-ready tables
- synthetic 20-level L2 sample
- claim-to-evidence registry
- smoke pipeline

This is good, but reviewer trust depends on whether these files really exist and are referenced clearly. The statement should be operational, not just aspirational.

### Required investigation

Check whether the repository/package contains:

```text
ARTIFACTS.md
REPRODUCIBILITY.md
DATA_CARD.md
SCHEMA.md
checksums.json
split_audit.csv or equivalent
claim_evidence_registry.csv or equivalent
sample_data/l2_synthetic_sample.* or equivalent
scripts/run_smoke_pipeline.sh or equivalent
scripts/verify_artifacts.py or equivalent
```

### If these files exist

Add or revise the artifact paragraph to name the artifact package more concretely.

Suggested replacement paragraph for Section VIII:

```latex
The artifact package separates restricted commercial snapshots from public reproducibility assets. Public assets include schema documentation, benchmark configuration files, checksum manifests, split audits, paper-ready result tables, a claim-to-evidence registry, and a synthetic 20-level L2 sample. The package also includes a smoke pipeline that exercises audit, feature construction, cost-aware labeling, regime assignment, chronological splitting, forecasting, L2 replay, RSEP, stress evaluation, and report generation on the synthetic sample. The synthetic sample is not used for scientific claims; it verifies executable code paths when raw commercial data cannot be redistributed.
```

### If these files do not exist

Do not claim they exist. Use a weaker but honest statement:

```latex
Because raw commercial snapshots cannot be redistributed, the submission package provides schema documentation, benchmark configurations, split definitions, paper-ready result tables, and checksum-style summaries. A synthetic L2 sample and smoke pipeline are planned for the public release and are not used for any scientific claim in this paper.
```

Also create an internal blocker note:

```text
BLOCKER: artifact package does not yet contain all public reproducibility files claimed in the paper.
```

### Acceptance criteria

```text
[ ] Paper does not claim non-existent artifacts.
[ ] Artifact statement is concrete and auditable.
[ ] Restricted raw data limitation remains explicit.
[ ] No unsupported reproducibility overclaim is introduced.
```

---

## 4. Task C — Add artifact URL / DOI / repository statement

### Problem

The paper currently says artifacts exist, but the final submission should include a clear artifact access statement. For a single-blind Applied Track paper, this may be a public repository, institutional repository, Zenodo DOI, or an artifact package link, depending on submission policy.

### Required action

Search for existing repository or artifact identifiers:

```text
GitHub URL
Zenodo DOI
OSF URL
Figshare URL
institutional repository URL
artifact package filename
anonymous artifact link, if required by system
```

### Insert one of the following statements

#### If public artifact URL exists

Add near the end of Section VIII:

```latex
The artifact package is available at: \url{<ARTIFACT_URL>}.
```

#### If DOI exists

```latex
The artifact package is archived at DOI: \url{<DOI_URL>}.
```

#### If artifact URL should not appear in review PDF

```latex
The artifact package will be provided through the ICDM submission system and includes source code, configurations, split manifests, checksums, synthetic data, and paper-ready result artifacts.
```

#### If no artifact is ready

```latex
The artifact package is under preparation and will include source code, configurations, split manifests, checksums, synthetic data, and paper-ready result artifacts. This paper does not rely on the synthetic data for scientific claims.
```

Also mark:

```text
BLOCKER: no final artifact URL/DOI/package path provided.
```

### Acceptance criteria

```text
[ ] Artifact availability statement is present.
[ ] Statement follows the applicable review/submission policy.
[ ] No private or non-public URL is exposed accidentally.
[ ] No anonymous-review conflict is introduced if the system requires anonymous artifacts.
```

---

## 5. Task D — Remove unsupported standalone RSEP ablation number from main text

### Problem

The main paper includes a specific ablation result:

```text
The full gate has net PnL −122,646.73 in the ablation setting...
```

But the corresponding ablation table is no longer in the 10-page main paper. A reviewer may ask:

- Which model?
- Which asset?
- Which split?
- Which ablation configuration?
- Why is the scale so different from Table VI?

This number creates unnecessary risk.

### Required action

Find the paragraph in Section V.C or near the execution results that starts with:

```text
The RSEP ablation evidence reinforces the cautious interpretation.
```

Replace the detailed numeric ablation paragraph with a concise artifact-based statement.

### Suggested replacement

```latex
Ablation artifacts reinforce the cautious interpretation: removing latency, liquidity, adverse-selection, or regime components generally worsens net PnL in the selected ablation setting, but all variants remain net negative. Thus, the evidence supports risk-filtering analysis, not profitability. The full ablation table is included in the artifact package rather than the 10-page main paper.
```

### Remove

Remove these exact numerical claims from the main paper unless the ablation table is restored:

```text
−122,646.73
−131,038.20
−192,136.81
−217,306.21
−190,460.37
−64,999.54
−75,479.42
−70,887.92
−69,532.74
```

Important: worst-regime values may still appear in Fig. 3 caption or text if Fig. 3 is retained and the values are visually/table-supported. But the unsupported ablation paragraph should not contain the standalone large-scale net PnL number.

### Acceptance criteria

```text
[ ] No standalone ablation PnL number appears without a nearby table/figure.
[ ] RSEP ablation is described qualitatively in main text.
[ ] Full ablation is delegated to artifacts.
[ ] The core negative-evidence message is preserved.
```

---

## 6. Task E — Clarify RSEP expected-edge heuristic and calibration limits

### Problem

RSEP computes expected edge using forecast probabilities and train-split class-return means:

```latex
\hat e_t = \sum_y p_t(y)\mu_y
```

This is interpretable but simple. Reviewers may question calibration and whether this is a deployable expected-return estimate.

### Required action

Add one short clarification after the RSEP equation or immediately before/after Algorithm 1.

### Suggested insertion

```latex
This edge estimate is intentionally simple and diagnostic: it converts a probabilistic ternary forecast into a comparable replay gate using train-split class-return means. It is not claimed to be a calibrated live expected-return model. Calibration and cross-asset distribution shifts are therefore interpreted as part of the degradation analysis rather than as evidence of deployable trading edge.
```

### Optional artifact statement

If calibration artifacts exist, add:

```latex
Calibration diagnostics, including cross-asset ECE summaries, are included in the artifact package.
```

Only add this if those diagnostics exist.

### Acceptance criteria

```text
[ ] RSEP expected edge is framed as diagnostic, not live expected return.
[ ] No trading-edge overclaim is introduced.
[ ] The relation between calibration and degradation analysis is clear.
```

---

## 7. Task F — Final overclaim audit

### Problem

The paper is about financial ML and LOB execution diagnostics. It must avoid language that suggests profitability, deployment readiness, exact market reconstruction, or universal transfer.

### Required action

Search the paper for the following terms and inspect every occurrence:

```text
profitable
profitability
trading strategy
live trading
live-ready
deployment
deployable profit
exact replay
exact queue
queue priority
hidden liquidity
passive fill
market impact
universal
generalize
generalization
SOTA
state-of-the-art
winner
best model
```

### Required edits

Use conservative language:

| Risky wording | Replace with |
|---|---|
| profitable strategy | diagnostic policy / selective-execution diagnostic |
| live-ready | not used |
| exact replay | L2 snapshot replay approximation |
| queue-aware | outside scope |
| hidden-liquidity model | outside scope |
| universal winner | evaluated setting / selected setting / diagnostic result |
| cross-market generalization | BTC↔ETH asset-held-out diagnostic |
| best model | best under this metric / metric-dependent ranking |
| SOTA | controlled baseline / diagnostic baseline |

### Acceptance criteria

```text
[ ] No profitability claim.
[ ] No live-trading readiness claim.
[ ] No exact queue-priority claim.
[ ] No hidden-liquidity or passive-fill claim.
[ ] No universal RSEP winner claim.
[ ] No cross-asset generalization beyond BTC↔ETH.
[ ] No SOTA model-development claim.
```

---

## 8. Task G — Final PDF quality and placeholder scan

### Problem

The final paper must be clean enough for submission: no placeholders, no broken citations, no undefined refs, no accidental compile warnings that affect layout.

### Required action

Run final scans on the LaTeX source and compiled PDF.

### Search for placeholders

```text
Author Name
Affiliation
Email
TODO
TBD
FIXME
PLACEHOLDER
anonymous
Anonymous
?? 
[?]
undefined
missing
to be added
will be added
under preparation
```

Do not remove legitimate words if they are part of a necessary artifact statement, but flag them.

### Compile check

Compile with the correct sequence, for example:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

or the equivalent build system.

### Required checks

```text
[ ] PDF page count is <= 10.
[ ] All citations are resolved.
[ ] All references are resolved.
[ ] No `[?]` citation markers.
[ ] No `??` reference markers.
[ ] No author placeholder.
[ ] No overfull boxes that visibly break tables/figures.
[ ] Tables are readable in two-column format.
[ ] Figures render correctly.
[ ] References fit within page 10.
```

### Acceptance criteria

```text
[ ] The final PDF is submission-ready except for any explicitly marked BLOCKER.
[ ] If any blocker remains, output a blocker report instead of claiming success.
```

---

## 9. Task H — Ensure final paper stays within 10 pages after author/artifact edits

### Problem

Adding real authors, artifact URL, and clarifying sentences may push the PDF beyond 10 pages.

### Required action

After applying Tasks A–G, compile and check page count.

### If PDF becomes 11 pages

Do **not** remove Fig. 2 or Fig. 3 because the user explicitly said to ignore that suggestion.

Instead cut text in this order:

1. Shorten Related Work by 3–5 sentences.
2. Shorten the long cross-asset asymmetry paragraph by moving exact ratios to artifacts.
3. Shorten Threats to Validity by removing the model-selection ledger details.
4. Shorten Discussion by removing one paragraph of repeated practical takeaway.
5. Shorten Limitations by merging paragraphs 2 and 3.
6. Reduce reference list only if a reference is no longer cited.

### Safe compression candidates

#### Cross-asset paragraph shorter replacement

Replace the long ratio paragraph with:

```latex
The two directions are reported separately because the asset audit shows substantial distribution shift in price scale, relative spread, depth, label mix, regime distribution, and calibration. BTC$\to$ETH faces a target split with much higher relative spread, whereas ETH$\to$BTC evaluates on a more FLAT-heavy BTC target split. Full distribution-shift ratios are included in the artifact package.
```

#### Model-selection ledger shorter replacement

Replace the detailed ledger paragraph with:

```latex
A model-selection ledger records feature versions, label versions, prediction artifacts, threshold grids, validation objectives, selected thresholds, and held-out results. Selection is validation-only; stress-grid results keep predictions and thresholds fixed. The paper does not claim to eliminate data-snooping risk, but reports conservative controls rather than unsupported overfitting p-values.
```

#### Limitations shorter replacement

```latex
The benchmark is bounded by snapshot-level L2 data. It cannot observe order arrivals, cancellations, queue priority, hidden liquidity, passive-fill dynamics, venue routing, or matching-engine details. It is intended for research evaluation and robustness analysis, not investment advice or deployment evidence.
```

### Acceptance criteria

```text
[ ] Final PDF remains <= 10 pages.
[ ] Fig. 2 and Fig. 3 remain in the paper.
[ ] Scientific core claims are preserved.
```

---

## 10. Task I — Final reviewer-readiness report

After all edits, generate a short report called:

```text
final_submission_readiness_report.md
```

The report must include:

```text
1. Final PDF page count.
2. Whether author block is real or still blocked.
3. Whether citations/references are resolved.
4. Whether artifact package files exist.
5. Whether ablation standalone number was removed.
6. Whether RSEP heuristic clarification was added.
7. Whether no-overclaim scan passed.
8. Whether final PDF is submission-ready.
9. Any remaining blocker.
```

Use this format:

```markdown
# Final Submission Readiness Report

## Page Count
- Final PDF pages: X
- Status: PASS/FAIL

## Author Block
- Status: PASS/FAIL/BLOCKED
- Notes:

## References
- Citations resolved: YES/NO
- Undefined refs: YES/NO

## Artifact Package
- Required files found:
  - ARTIFACTS.md: YES/NO
  - REPRODUCIBILITY.md: YES/NO
  - checksums.json: YES/NO
  - split audit: YES/NO
  - claim-evidence registry: YES/NO
  - synthetic sample: YES/NO
  - smoke pipeline: YES/NO

## Main Text Fixes
- Standalone RSEP ablation number removed: YES/NO
- RSEP heuristic clarified: YES/NO
- Overclaim scan passed: YES/NO
- Fig. 2 retained: YES/NO
- Fig. 3 retained: YES/NO

## Final Verdict
- SUBMISSION-READY / NOT SUBMISSION-READY
- Remaining blockers:
```

---

## 11. One-shot Codex instruction

Use the following prompt when giving this file to Codex:

```text
Apply fix_v2.md to the current ICDM 2026 Applied Track paper. Keep Fig. 2 and Fig. 3 in the main paper. Do not invent numerical results or author information. Replace author placeholders only if actual author metadata is available; otherwise mark the paper as BLOCKED. Remove unsupported standalone RSEP ablation numbers from the main text, clarify that RSEP expected edge is a diagnostic heuristic, strengthen the artifact availability statement only to the extent supported by actual files, run a full overclaim and placeholder scan, compile with bibliography, and ensure the final PDF remains at most 10 pages including references. Produce final_submission_readiness_report.md.
```
