param(
    [ValidateSet("core", "full")]
    [string]$Dataset = "full",

    [ValidateSet("inspect-dataset", "inspect-truth", "collect", "verify", "score", "report", "run")]
    [string]$Command = "run",

    [int]$MaxPrompts = 0,
    [switch]$Resume,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Config = "configs/experiments/main5.$Dataset.v1.json"

& (Join-Path $ScriptRoot "run_experiment.ps1") -Config $Config -Command $Command -MaxPrompts $MaxPrompts -Resume:$Resume -Python $Python
exit $LASTEXITCODE
