param(
    [ValidateSet("dns_enriched", "rdap_curated")]
    [string]$EvidenceStage = "dns_enriched",

    [ValidateSet("inspect-dataset", "inspect-truth", "collect", "verify", "score", "report", "run")]
    [string]$Command = "run",

    [int]$MaxPrompts = 0,
    [switch]$Resume,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

switch ($EvidenceStage) {
    "dns_enriched" { $Config = "configs/experiments/legacy330.highrisk_targeted.main5.v1.json" }
    "rdap_curated" { $Config = "configs/experiments/legacy330.highrisk_targeted.main5.rdap_curated.v1.json" }
    default { throw "Unsupported EvidenceStage=$EvidenceStage" }
}

& (Join-Path $ScriptRoot "run_experiment.ps1") -Config $Config -Command $Command -MaxPrompts $MaxPrompts -Resume:$Resume -Python $Python
exit $LASTEXITCODE
