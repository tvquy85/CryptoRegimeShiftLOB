# Final ICDM Applied Track Style Polish Summary

This version applies the reviewer-facing fixes requested after the latest review pass.

## Main changes

1. Shortened and sharpened the title toward an applied-auditing benchmark framing.
2. Removed all occurrences of the typo `supplementary supplementary artifact release`.
3. Strengthened the reproducibility boundary: public artifacts support method-surface audit and pipeline verification, while full numerical reproduction requires licensed access to Crypto Lake raw snapshots.
4. Clarified that the DeepLOB controlled subsample is not used for execution-policy comparison; it is only architectural interface coverage.
5. Clarified that RSEP is intentionally named for reproducibility and should not be read as a proposed trading algorithm.
6. Rewrote the RSEP decision table to remove duplicate steps, reduce crowding, and frame it as a diagnostic gate.
7. Added an explanatory sentence for why fee stress dominates short-horizon LOB replay.
8. Removed the `\balance` call that caused a non-fatal balance warning.
9. Added the arXiv URL note for the TCN reference.
10. Patched Figure 2 and Figure 3 legends to replace internal artifact names such as `sgd_stage3` with reviewer-facing labels: SGD, TCN, TCN stride-1, XGBoost.

## Compile status

- PDF compilation: successful.
- Page count: 10.
- Bib items: 31.
- Unique cited keys in `main.tex`: 31.
- Undefined citations/references: none detected in final compile log.
- Remaining warnings: only underfull box warnings from dense IEEE two-column layout; no fatal layout or citation issue detected.
