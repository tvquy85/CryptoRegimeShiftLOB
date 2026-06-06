from artifact_lib import build_features, cli_config, load_config

if __name__ == "__main__":
    parser = cli_config()
    args = parser.parse_args()
    cfg = load_config(args.config)
    df = build_features(cfg, args.mode)
    print(f"[OK] time-causal features built rows={len(df)}")

