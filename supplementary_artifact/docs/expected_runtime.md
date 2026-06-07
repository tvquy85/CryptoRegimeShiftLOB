# Expected Runtime

Synthetic mode is designed to run on CPU in a few minutes or less. It generates
a small deterministic two-asset L2 sample, trains a lightweight SGD classifier,
runs visible-depth replay, stress tests, bootstrap diagnostics, and creates a
manifest. This mode is intended to verify the artifact surface and code paths,
not to reproduce the scientific paper numbers.

Full licensed-data mode is not bounded by this artifact package because runtime
depends on local storage, CPU, RAM, GPU availability, and the size/layout of the
licensed Crypto Lake snapshots. The reported full-year experiments used
workstation-class compute and GPU acceleration where appropriate, but the public
artifact does not claim a fixed wall-clock runtime for full reproduction.

Recommended reviewer checks:

- Run `make synthetic` and `make verify` for the public executable path.
- Run `python scripts/10_make_artifact_manifest.py --mode synthetic` to record
  hashes and environment metadata.
- Run `make validate-full-data` only if licensed raw snapshots are locally
  available; otherwise the command should fail with a license/data-location
  message rather than fabricating paper-number outputs.
