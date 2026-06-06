from artifact_lib import cli_config, load_config, train_baseline

if __name__ == "__main__":
    parser = cli_config()
    args = parser.parse_args()
    cfg = load_config(args.config)
    df = train_baseline(cfg, args.mode)
    print(f"[OK] SGD-small baseline predictions generated rows={len(df)}")

