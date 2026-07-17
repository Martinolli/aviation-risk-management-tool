from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_DOC = REPO_ROOT / "docs" / "electronic-approval-concept.md"


def test_electronic_approval_concept_doc_exists() -> None:
    assert POLICY_DOC.is_file()


def test_electronic_approval_doc_mentions_required_concepts() -> None:
    text = POLICY_DOC.read_text()

    assert "Electronic Approval" in text
    assert "Signature Concept" in text
    assert "Controlled Approval Record" in text
    assert "Authority Level" in text
    assert "Acknowledgement" in text
    assert "Audit integrity" in text
    assert "SMS governance" in text
    assert "Not a cryptographic digital signature" in text


def test_related_docs_link_or_reference_electronic_approval() -> None:
    assert "electronic-approval-concept.md" in (REPO_ROOT / "README.md").read_text()
    assert "Electronic Approval" in (
        REPO_ROOT / "docs" / "permission-matrix.md"
    ).read_text()
    assert "Electronic Approval Records" in (
        REPO_ROOT / "docs" / "data-retention-and-archive-policy.md"
    ).read_text()
    assert "electronic-approval-concept.md" in (
        REPO_ROOT / "docs" / "deployment-readiness.md"
    ).read_text()
