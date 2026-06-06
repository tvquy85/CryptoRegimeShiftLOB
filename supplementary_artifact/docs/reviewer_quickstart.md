# Reviewer Quickstart

Run the public smoke pipeline:

```bash
cd supplementary_artifact
pip install -r requirements.txt
make synthetic
make verify
```

Validate optional raw-format sample:

```bash
make validate-raw-sample
```

If the raw-format sample is absent, this is acceptable for the public package. It means only the synthetic layer can be executed without user-supplied or provider-public data.

