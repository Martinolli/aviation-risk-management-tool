param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [string]$ContainerName = "aviation-risk-postgres",
    [string]$DatabaseName = "aviation_risk_management",
    [string]$DatabaseUser = "postgres",
    [string]$EvidenceDir = "backend/evidence_uploads",
    [string]$GeneratedReportsDir = "backend/generated_reports",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

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

function Resolve-LocalRestorePath {
    param([string]$Path)
    $parent = Split-Path -Parent $Path
    if (-not $parent) {
        $parent = "."
    }
    $resolvedParent = (Resolve-Path -LiteralPath $parent).Path
    return [System.IO.Path]::GetFullPath((Join-Path $resolvedParent (Split-Path -Leaf $Path)))
}

function Assert-PathWithinRepo {
    param(
        [string]$Path,
        [string]$Label
    )
    $fullPath = Resolve-LocalRestorePath -Path $Path
    if (-not $fullPath.StartsWith($RepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label restore target '$fullPath' is outside the repository. This local MVP script only restores repository-local folders."
    }
    return $fullPath
}

try {
    if (-not (Test-Path -LiteralPath $BackupPath -PathType Container)) {
        throw "BackupPath '$BackupPath' does not exist."
    }

    $databaseDumpPath = Join-Path $BackupPath "database.dump"
    if (-not (Test-Path -LiteralPath $databaseDumpPath -PathType Leaf)) {
        throw "Required database dump not found: $databaseDumpPath"
    }

    Write-Warning "Restore will replace local database data and may overwrite evidence/generated report folders."
    Write-Warning "This script is for local development or pilot restore only. Do not target production by default."
    if (-not $Force) {
        $confirmation = Read-Host "Type RESTORE to continue"
        if ($confirmation -ne "RESTORE") {
            Write-Host "Restore cancelled."
            exit 0
        }
    }

    Assert-DockerAvailable

    $containerRestorePath = "/tmp/${DatabaseName}_restore.dump"
    docker cp $databaseDumpPath "${ContainerName}:$containerRestorePath"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to copy database dump into container '$ContainerName'."
    }

    docker exec $ContainerName psql -U $DatabaseUser -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DatabaseName' AND pid <> pg_backend_pid();" | Out-Null
    docker exec $ContainerName dropdb -U $DatabaseUser --if-exists $DatabaseName
    if ($LASTEXITCODE -ne 0) {
        throw "dropdb failed for '$DatabaseName'."
    }
    docker exec $ContainerName createdb -U $DatabaseUser $DatabaseName
    if ($LASTEXITCODE -ne 0) {
        throw "createdb failed for '$DatabaseName'."
    }
    docker exec $ContainerName pg_restore -U $DatabaseUser -d $DatabaseName --clean --if-exists $containerRestorePath
    if ($LASTEXITCODE -ne 0) {
        throw "pg_restore failed for '$DatabaseName'."
    }

    docker exec $ContainerName rm -f $containerRestorePath *> $null

    $evidenceSource = Join-Path $BackupPath "evidence_uploads"
    if (Test-Path -LiteralPath $evidenceSource -PathType Container) {
        $safeEvidenceDir = Assert-PathWithinRepo -Path $EvidenceDir -Label "Evidence Backup"
        if (Test-Path -LiteralPath $safeEvidenceDir) {
            Remove-Item -LiteralPath $safeEvidenceDir -Recurse -Force
        }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $safeEvidenceDir) | Out-Null
        Copy-Item -LiteralPath $evidenceSource -Destination $safeEvidenceDir -Recurse -Force
    }

    $reportsSource = Join-Path $BackupPath "generated_reports"
    if (Test-Path -LiteralPath $reportsSource -PathType Container) {
        $safeGeneratedReportsDir = Assert-PathWithinRepo -Path $GeneratedReportsDir -Label "Generated Reports Backup"
        if (Test-Path -LiteralPath $safeGeneratedReportsDir) {
            Remove-Item -LiteralPath $safeGeneratedReportsDir -Recurse -Force
        }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $safeGeneratedReportsDir) | Out-Null
        Copy-Item -LiteralPath $reportsSource -Destination $safeGeneratedReportsDir -Recurse -Force
    }

    Write-Host "Restore completed"
    Write-Host "Reminder: run backend tests or manually validate the app."
} catch {
    Write-Error $_
    exit 1
}
