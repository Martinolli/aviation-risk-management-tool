from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_DOC = REPO_ROOT / "docs" / "data-retention-and-archive-policy.md"


def test_data_retention_policy_doc_exists() -> None:
    assert POLICY_DOC.is_file()


def test_data_retention_policy_doc_mentions_no_hard_delete() -> None:
    assert "No hard delete" in POLICY_DOC.read_text()


def test_data_retention_policy_doc_mentions_audit_integrity() -> None:
    assert "Audit integrity" in POLICY_DOC.read_text()


def test_data_retention_policy_doc_mentions_evidence_traceability() -> None:
    assert "Evidence traceability" in POLICY_DOC.read_text()


def test_data_retention_policy_doc_mentions_legal_investigation_hold() -> None:
    assert "Legal / Investigation Hold" in POLICY_DOC.read_text()


def test_readme_links_to_data_retention_policy() -> None:
    text = (REPO_ROOT / "README.md").read_text()

    assert "data-retention-and-archive-policy.md" in text


def test_backup_and_restore_guide_links_to_data_retention_policy() -> None:
    text = (REPO_ROOT / "docs" / "backup-and-restore.md").read_text()

    assert "data-retention-and-archive-policy.md" in text


def test_deployment_readiness_guide_links_to_data_retention_policy() -> None:
    text = (REPO_ROOT / "docs" / "deployment-readiness.md").read_text()

    assert "data-retention-and-archive-policy.md" in text
