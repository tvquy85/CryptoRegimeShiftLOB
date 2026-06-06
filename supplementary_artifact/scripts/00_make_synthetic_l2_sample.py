from artifact_lib import load_config, make_synthetic_sample

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/synthetic.yaml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    df = make_synthetic_sample(cfg)
    print(f"[OK] synthetic L2 sample generated rows={len(df)}")

