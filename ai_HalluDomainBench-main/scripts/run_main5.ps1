param(
    [ValidateSet("new_dataset", "sample_all_quantity_variants")]
    [string]$Dataset = "sample_all_quantity_variants",

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
    "new_dataset|baseline_http" { $Config = "configs/experiments/new_dataset.main5.v1.json" }
    "sample_all_quantity_variants|baseline_http" { $Config = "configs/experiments/sample_all_quantity_variants.main5.v1.json" }
    default {
        throw "No config is defined for Dataset=$Dataset and EvidenceStage=$EvidenceStage"
    }
}

& (Join-Path $ScriptRoot "run_experiment.ps1") -Config $Config -Command $Command -MaxPrompts $MaxPrompts -Resume:$Resume -Python $Python
exit $LASTEXITCODE
