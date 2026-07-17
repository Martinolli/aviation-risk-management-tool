from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
LOGGING_DOC = REPO_ROOT / "docs" / "production-logging-and-monitoring.md"


def test_production_logging_doc_exists() -> None:
    assert LOGGING_DOC.is_file()


def test_production_logging_doc_mentions_required_terms() -> None:
    text = LOGGING_DOC.read_text()

    assert "Production Logging" in text
    assert "Error Monitoring" in text
    assert "Request ID" in text
    assert "Operational Diagnostics" in text
    assert "Safe Logging" in text
    assert "Audit Trail" in text
    assert "SMS governance" in text


def test_production_logging_doc_lists_sensitive_data_not_to_log() -> None:
    text = LOGGING_DOC.read_text()

    assert "JWT tokens" in text
    assert "Passwords" in text
    assert "Database URLs" in text
    assert "Request bodies" in text
    assert "Uploaded evidence contents" in text


def test_related_docs_link_to_production_logging_doc() -> None:
    for path in [
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "deployment-readiness.md",
        REPO_ROOT / "docs" / "backup-and-restore.md",
    ]:
        assert "production-logging-and-monitoring.md" in path.read_text()


def test_permission_matrix_mentions_operational_logs_access() -> None:
    text = (REPO_ROOT / "docs" / "permission-matrix.md").read_text()

    assert "Operational Logs Access Rule" in text
    assert "authorized IT/admin personnel" in text
