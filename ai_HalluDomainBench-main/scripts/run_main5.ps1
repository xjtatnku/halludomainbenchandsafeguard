param(
    [ValidateSet("core", "full")]
    [string]$Dataset = "full",

    [ValidateSet("baseline_http", "dns_enriched")]
    [string]$EvidenceStage = "baseline_http",

    [ValidateSet("inspect-dataset", "inspect-truth", "collect", "verify", "score", "report", "run")]
    [string]$Command = "run",

    [int]$MaxPrompts = 0,
    [switch]$Resume,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

switch ("$Dataset|$EvidenceStage") {
    "core|baseline_http" { $Config = "configs/experiments/main5.core.v1.json" }
    "core|dns_enriched" { $Config = "configs/experiments/main5.core.dns_enriched.v1.json" }
    "full|baseline_http" { $Config = "configs/experiments/main5.full.v1.json" }
    default {
        throw "No config is defined for Dataset=$Dataset and EvidenceStage=$EvidenceStage"
    }
}

& (Join-Path $ScriptRoot "run_experiment.ps1") -Config $Config -Command $Command -MaxPrompts $MaxPrompts -Resume:$Resume -Python $Python
exit $LASTEXITCODE
