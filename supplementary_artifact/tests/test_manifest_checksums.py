from pathlib import Path

from artifact_lib import make_manifest, sha256_file


def test_manifest_excludes_external_raw_data(tmp_path):
    manifest = make_manifest("synthetic")
    assert manifest["raw_commercial_data_included"] is False
    assert all("data/external/cryptolake" not in entry["path"] for entry in manifest["entries"])


def test_sha256_file_is_deterministic(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("abc", encoding="utf-8")
    assert sha256_file(p) == sha256_file(p)

