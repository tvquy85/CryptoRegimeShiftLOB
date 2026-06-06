import subprocess
import sys
from pathlib import Path


def test_extractor_requires_license_confirmation():
    root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(root / "scripts" / "00_extract_minimal_raw_sample.py"),
        "--input-glob",
        "does_not_exist/*.parquet",
        "--source-type",
        "license_permitted_excerpt",
    ]
    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    assert result.returncode != 0
    assert "license-confirmed" in result.stderr or "license-confirmed" in result.stdout

