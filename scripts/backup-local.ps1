param(
    [string]$BackupRoot = "backups",
    [string]$ContainerName = "aviation-risk-postgres",
    [string]$DatabaseName = "aviation_risk_management",
    [string]$DatabaseUser = "postgres",
    [string]$EvidenceDir = "backend/evidence_uploads",
    [string]$GeneratedReportsDir = "backend/generated_reports"
)

$ErrorActionPreference = "Stop"

function Assert-DockerAvailable {
    docker version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is not running or is not available on PATH."
    }

    docker inspect $ContainerName *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker container '$ContainerName' is not available."
    }
}

function Get-FileCount {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return 0
    }
    return @(Get-ChildItem -LiteralPath $Path -Recurse -File -Force).Count
}

try {
    Assert-DockerAvailable

    $timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
    $backupRootPath = New-Item -ItemType Directory -Force -Path $BackupRoot
    $backupPath = Join-Path $backupRootPath.FullName "backup_$timestamp"
    New-Item -ItemType Directory -Force -Path $backupPath | Out-Null

    $containerDumpPath = "/tmp/$DatabaseName.dump"
    $databaseDumpPath = Join-Path $backupPath "database.dump"

    docker exec $ContainerName pg_dump -U $DatabaseUser -d $DatabaseName -Fc -f $containerDumpPath
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump failed for database '$DatabaseName'."
    }

    docker cp "${ContainerName}:$containerDumpPath" $databaseDumpPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to copy database dump from container '$ContainerName'."
    }

    docker exec $ContainerName rm -f $containerDumpPath *> $null

    $evidenceIncluded = Test-Path -LiteralPath $EvidenceDir
    $reportsIncluded = Test-Path -LiteralPath $GeneratedReportsDir
    $evidenceCount = 0
    $reportCount = 0

    if ($evidenceIncluded) {
        $evidenceDestination = Join-Path $backupPath "evidence_uploads"
        Copy-Item -LiteralPath $EvidenceDir -Destination $evidenceDestination -Recurse -Force
        $evidenceCount = Get-FileCount -Path $evidenceDestination
    }

    if ($reportsIncluded) {
        $reportsDestination = Join-Path $backupPath "generated_reports"
        Copy-Item -LiteralPath $GeneratedReportsDir -Destination $reportsDestination -Recurse -Force
        $reportCount = Get-FileCount -Path $reportsDestination
    }

    $manifest = [ordered]@{
        backup_created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        app_name = "aviation-risk-management-tool"
        backup_type = "local-development-mvp"
        database_container = $ContainerName
        database_name = $DatabaseName
        database_user = $DatabaseUser
        database_dump_file = "database.dump"
        evidence_dir_included = $evidenceIncluded
        generated_reports_dir_included = $reportsIncluded
        evidence_file_count = $evidenceCount
        generated_report_file_count = $reportCount
        restore_script = "scripts/restore-local.ps1"
        notes = "Backup and Restore MVP package. Store backup securely and do not commit it."
    }
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $backupPath "backup_manifest.json") -Encoding UTF8

    Write-Host "Backup completed"
    Write-Host "Backup folder path: $backupPath"
    Write-Host "Reminder: store backup securely and do not commit it."
} catch {
    Write-Error $_
    exit 1
}
