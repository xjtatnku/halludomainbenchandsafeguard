param(
    [Parameter(Mandatory = $true)]
    [string]$Config,

    [ValidateSet("inspect-dataset", "inspect-truth", "collect", "verify", "score", "report", "run")]
    [string]$Command = "run",

    [int]$MaxPrompts = 0,
    [switch]$Resume,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $RepoRoot
try {
    $Args = @("-m", "halludomainbench", "--config", $Config, $Command)

    if (($Command -eq "collect" -or $Command -eq "run") -and $MaxPrompts -gt 0) {
        $Args += @("--max-prompts", "$MaxPrompts")
    }
    if (($Command -eq "collect" -or $Command -eq "run") -and $Resume) {
        $Args += "--resume"
    }

    & $Python @Args
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
