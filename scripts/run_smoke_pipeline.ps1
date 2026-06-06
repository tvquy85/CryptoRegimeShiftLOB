$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$env:PYTHONIOENCODING = "utf-8"

$Config = "configs/repro_smoke.yaml"
$Stage = "stage_0_sanity_check"
$Symbol = "SYNTH-USDT"
$ModelLabel = "sgd_synthetic_smoke"

function Invoke-Step {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Command)
    & $Command[0] $Command[1..($Command.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $($Command -join ' ')"
    }
}

Invoke-Step python scripts/create_synthetic_l2_sample.py
Invoke-Step python scripts/00_audit_data.py --config $Config --run-id repro_smoke_audit_v001 --stage $Stage --symbol $Symbol
Invoke-Step python scripts/01_build_features.py --config $Config --run-id repro_smoke_features_v001 --stage $Stage --symbol $Symbol
Invoke-Step python scripts/02_label_regimes.py --config $Config --run-id repro_smoke_regimes_v001 --stage $Stage --symbol $Symbol
Invoke-Step python scripts/03_make_splits.py --config $Config --run-id repro_smoke_splits_v001 --stage $Stage --symbol $Symbol
Invoke-Step python scripts/04_train_forecasters.py --config $Config --run-id repro_smoke_train_sgd_v001 --stage $Stage --symbol $Symbol --model sgd
Invoke-Step python scripts/05_backtest_forecasts.py --config $Config --run-id repro_smoke_backtest_v001 --stage $Stage --symbol $Symbol
Invoke-Step python scripts/06_run_rsep.py --config $Config --run-id repro_smoke_rsep_v001 --stage $Stage --symbol $Symbol
Invoke-Step python scripts/09_tune_execution_policies.py --config $Config --run-id repro_smoke_tune_v001 --stage $Stage --symbol $Symbol --model-label $ModelLabel
Invoke-Step python scripts/07_run_stress_grid.py --config $Config --run-id repro_smoke_stress_v001 --stage $Stage --symbol $Symbol --model-label $ModelLabel --use-tuned-policy
Invoke-Step python scripts/08_generate_report_pack.py --config $Config --run-id repro_smoke_report_v001 --stage $Stage --symbol $Symbol --model-label $ModelLabel
Invoke-Step python scripts/verify_artifacts.py --require-smoke-outputs
