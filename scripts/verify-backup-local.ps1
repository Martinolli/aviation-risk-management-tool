param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath
)

$ErrorActionPreference = "Stop"

function Get-FileCount {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return 0
    }
    return @(Get-ChildItem -LiteralPath $Path -Recurse -File -Force).Count
}

try {
    if (-not (Test-Path -LiteralPath $BackupPath -PathType Container)) {
        throw "BackupPath '$BackupPath' does not exist."
    }

    $databaseDumpPath = Join-Path $BackupPath "database.dump"
    $manifestPath = Join-Path $BackupPath "backup_manifest.json"
    if (-not (Test-Path -LiteralPath $databaseDumpPath -PathType Leaf)) {
        throw "database.dump is missing."
    }
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "backup_manifest.json is missing."
    }

    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $evidencePath = Join-Path $BackupPath "evidence_uploads"
    $reportsPath = Join-Path $BackupPath "generated_reports"
    $evidencePresent = Test-Path -LiteralPath $evidencePath -PathType Container
    $reportsPresent = Test-Path -LiteralPath $reportsPath -PathType Container

    if ([bool]$manifest.evidence_dir_included -ne $evidencePresent) {
        throw "Evidence Backup folder presence does not match manifest."
    }
    if ([bool]$manifest.generated_reports_dir_included -ne $reportsPresent) {
        throw "Generated Reports Backup folder presence does not match manifest."
    }

    $evidenceCount = Get-FileCount -Path $evidencePath
    $reportCount = Get-FileCount -Path $reportsPath

    Write-Host "Backup verification completed"
    Write-Host "Backup type: $($manifest.backup_type)"
    Write-Host "Database Backup: $databaseDumpPath"
    Write-Host "Evidence Backup included: $evidencePresent ($evidenceCount files)"
    Write-Host "Generated Reports Backup included: $reportsPresent ($reportCount files)"
} catch {
    Write-Error $_
    exit 1
}
