from artifact_lib import cli_config, load_config, run_stress

if __name__ == "__main__":
    parser = cli_config()
    args = parser.parse_args()
    cfg = load_config(args.config)
    out = run_stress(cfg, args.mode)
    print(f"[OK] stress tests completed rows={len(out)}")

