from artifact_lib import cli_config, load_config, make_labels_regimes_splits

if __name__ == "__main__":
    parser = cli_config()
    args = parser.parse_args()
    cfg = load_config(args.config)
    df = make_labels_regimes_splits(cfg, args.mode)
    print(f"[OK] cost-aware labels, regimes, and purged splits created rows={len(df)}")

