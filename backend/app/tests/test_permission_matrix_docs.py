from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_DOC = REPO_ROOT / "docs" / "permission-matrix.md"


def test_permission_matrix_doc_exists() -> None:
    assert POLICY_DOC.is_file()


def test_permission_matrix_doc_mentions_required_access_control_terms() -> None:
    text = POLICY_DOC.read_text()

    assert "Permission Matrix" in text
    assert "Access Control" in text
    assert "Authority Level" in text
    assert "Board of Origin" in text
    assert "Fixed Governance Committee" in text
    assert "SMS governance" in text
    assert "audit integrity" in text.lower()


def test_permission_matrix_doc_mentions_export_authorization_boundary() -> None:
    text = POLICY_DOC.read_text()

    assert "Exports must never include records the requesting user cannot read" in text


def test_readme_links_to_permission_matrix() -> None:
    text = (REPO_ROOT / "README.md").read_text()

    assert "docs/permission-matrix.md" in text


def test_data_retention_policy_links_to_permission_matrix() -> None:
    text = (REPO_ROOT / "docs" / "data-retention-and-archive-policy.md").read_text()

    assert "permission-matrix.md" in text


def test_deployment_readiness_guide_links_to_permission_matrix() -> None:
    text = (REPO_ROOT / "docs" / "deployment-readiness.md").read_text()

    assert "permission-matrix.md" in text
