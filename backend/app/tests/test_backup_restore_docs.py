from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_backup_and_restore_doc_exists() -> None:
    assert (REPO_ROOT / "docs" / "backup-and-restore.md").is_file()


def test_backup_and_restore_doc_mentions_postgresql_database() -> None:
    text = (REPO_ROOT / "docs" / "backup-and-restore.md").read_text()

    assert "PostgreSQL database" in text
    assert "Database Backup" in text


def test_backup_and_restore_doc_mentions_evidence_uploads() -> None:
    text = (REPO_ROOT / "docs" / "backup-and-restore.md").read_text()

    assert "evidence uploads" in text
    assert "Evidence Backup" in text


def test_backup_and_restore_doc_mentions_generated_reports() -> None:
    text = (REPO_ROOT / "docs" / "backup-and-restore.md").read_text()

    assert "generated reports" in text
    assert "Generated Reports Backup" in text


def test_backup_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "backup-local.ps1").is_file()


def test_restore_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "restore-local.ps1").is_file()


def test_verify_backup_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "verify-backup-local.ps1").is_file()


def test_gitignore_ignores_backup_outputs_but_allows_gitkeep() -> None:
    text = (REPO_ROOT / ".gitignore").read_text()

    for expected in [
        "backups/*",
        "!backups/.gitkeep",
        "*.dump",
        "*.backup",
        "*.bak",
        "*.sql.gz",
        "*.tar.gz",
        "*.zip",
    ]:
        assert expected in text
