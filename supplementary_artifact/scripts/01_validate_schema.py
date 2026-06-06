from artifact_lib import ArtifactError, cli_config, load_config, load_l2_input, validate_full_or_fail, validate_l2_schema

if __name__ == "__main__":
    parser = cli_config()
    args = parser.parse_args()
    cfg = load_config(args.config)
    try:
        if args.mode == "full":
            validate_full_or_fail(cfg)
            print("[OK] licensed full-data schema validation passed")
        else:
            df = load_l2_input(cfg, args.mode)
            report = validate_l2_schema(df, cfg, args.mode)
            print(f"[OK] schema validation passed mode={args.mode} rows={report['rows']}")
    except FileNotFoundError as exc:
        if args.mode == "raw-sample":
            raise SystemExit("[ERROR] Raw-format sample not packaged. Use `make synthetic` or place provider sample here.")
        raise SystemExit(str(exc))
    except ArtifactError as exc:
        raise SystemExit(f"[ERROR] {exc}")

