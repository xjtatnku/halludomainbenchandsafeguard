param(
    [ValidateSet("all", "kimi_mode", "deepseek_reasoning", "qwen_scale", "glm_generation")]
    [string]$Pair = "all",

    [ValidateSet("inspect-dataset", "inspect-truth", "collect", "verify", "score", "report", "run")]
    [string]$Command = "run",

    [int]$MaxPrompts = 0,
    [switch]$Resume,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$Pairs = if ($Pair -eq "all") {
    @("kimi_mode", "deepseek_reasoning", "qwen_scale", "glm_generation")
} else {
    @($Pair)
}

foreach ($Current in $Pairs) {
    $Config = "configs/experiments/ablation.$Current.core.v1.json"
    Write-Host "Running $Current with $Config"
    & (Join-Path $ScriptRoot "run_experiment.ps1") -Config $Config -Command $Command -MaxPrompts $MaxPrompts -Resume:$Resume -Python $Python
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
