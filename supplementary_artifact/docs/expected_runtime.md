# Expected Runtime

Synthetic mode is designed to run on CPU in a few minutes or less. It generates a small deterministic two-asset L2 sample, trains a lightweight SGD classifier, runs visible-depth replay, stress tests, bootstrap diagnostics, and creates a manifest.

Full licensed-data mode is not bounded by this artifact package because runtime depends on local storage, CPU, GPU, and the size/layout of the licensed Crypto Lake snapshots.

