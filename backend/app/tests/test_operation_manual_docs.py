from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OPERATION_MANUAL = REPO_ROOT / "docs" / "operation-manual.md"
PROCEDURE_INDEX = REPO_ROOT / "docs" / "templates" / "operation-procedure-index.csv"


def test_operation_manual_doc_exists() -> None:
    assert OPERATION_MANUAL.is_file()


def test_operation_manual_mentions_operation_manual() -> None:
    assert "Operation Manual" in OPERATION_MANUAL.read_text()


def test_operation_manual_mentions_user_guide() -> None:
    assert "User Guide" in OPERATION_MANUAL.read_text()


def test_operation_manual_mentions_normal_operation() -> None:
    assert "Normal Operation" in OPERATION_MANUAL.read_text()


def test_operation_manual_mentions_authority_level() -> None:
    assert "Authority Level" in OPERATION_MANUAL.read_text()


def test_operation_manual_mentions_board_of_origin() -> None:
    assert "Board of Origin" in OPERATION_MANUAL.read_text()


def test_operation_manual_mentions_sms_governance() -> None:
    assert "SMS governance" in OPERATION_MANUAL.read_text()


def test_operation_manual_mentions_audit_integrity() -> None:
    assert "Audit integrity" in OPERATION_MANUAL.read_text()


def test_operation_manual_mentions_evidence_traceability() -> None:
    assert "Evidence traceability" in OPERATION_MANUAL.read_text()


def test_operation_manual_mentions_no_hard_delete() -> None:
    assert "No Hard Delete" in OPERATION_MANUAL.read_text()


def test_operation_manual_includes_procedure_01() -> None:
    assert "Procedure 01" in OPERATION_MANUAL.read_text()


def test_operation_manual_includes_procedure_30() -> None:
    assert "Procedure 30" in OPERATION_MANUAL.read_text()


def test_operation_manual_includes_troubleshooting() -> None:
    assert "Troubleshooting" in OPERATION_MANUAL.read_text()


def test_operation_manual_includes_limitations() -> None:
    assert "Limitations" in OPERATION_MANUAL.read_text()


def test_operation_manual_includes_glossary() -> None:
    assert "Glossary" in OPERATION_MANUAL.read_text()


def test_operation_procedure_index_csv_exists() -> None:
    assert PROCEDURE_INDEX.is_file()


def test_readme_links_to_operation_manual() -> None:
    text = (REPO_ROOT / "README.md").read_text()

    assert "operation-manual.md" in text


def test_pilot_deployment_checklist_references_operation_manual() -> None:
    text = (REPO_ROOT / "docs" / "pilot-deployment-checklist.md").read_text()

    assert "operation-manual.md" in text


def test_uat_pack_references_operation_manual() -> None:
    text = (REPO_ROOT / "docs" / "user-acceptance-test-pack.md").read_text()

    assert "operation-manual.md" in text
