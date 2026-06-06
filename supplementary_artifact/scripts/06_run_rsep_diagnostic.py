from artifact_lib import cli_config, load_config, run_rsep

if __name__ == "__main__":
    parser = cli_config()
    args = parser.parse_args()
    cfg = load_config(args.config)
    summary = run_rsep(cfg, args.mode)
    print(f"[OK] RSEP diagnostic completed n_trades={int(summary.iloc[0]['n_trades'])}")

