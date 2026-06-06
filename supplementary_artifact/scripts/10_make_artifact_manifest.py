from artifact_lib import make_manifest

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="synthetic")
    args = parser.parse_args()
    manifest = make_manifest(args.mode)
    print(f"[OK] claim-evidence manifest generated entries={len(manifest['entries'])}")

