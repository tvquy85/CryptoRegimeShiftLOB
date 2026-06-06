from artifact_lib import cli_config, load_config, run_bootstrap_and_transfer

if __name__ == "__main__":
    parser = cli_config()
    args = parser.parse_args()
    cfg = load_config(args.config)
    boot, transfer = run_bootstrap_and_transfer(cfg, args.mode)
    print(f"[OK] bootstrap diagnostics completed rows={len(boot)}")
    print(f"[OK] transfer diagnostics completed rows={len(transfer)}")

