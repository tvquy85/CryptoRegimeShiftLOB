from artifact_lib import ArtifactError, verify_tables

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="synthetic", choices=["synthetic", "full"])
    args = parser.parse_args()
    try:
        report = verify_tables(args.mode)
        print(f"[OK] paper table verifier completed on {args.mode} mode raw_sample_status={report['raw_sample_status']}")
    except ArtifactError as exc:
        raise SystemExit(f"[ERROR] {exc}")

