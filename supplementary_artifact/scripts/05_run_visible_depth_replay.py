from artifact_lib import cli_config, load_config, run_replay

if __name__ == "__main__":
    parser = cli_config()
    args = parser.parse_args()
    cfg = load_config(args.config)
    trades, summary = run_replay(cfg, args.mode, policy="cost_aware")
    print(f"[OK] visible-depth replay completed trades={len(trades)} net_pnl={summary.iloc[0]['net_pnl']:.6f}")

