from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PILOT_EXECUTION_PACK = REPO_ROOT / "docs" / "pilot-execution-support-pack.md"
PILOT_FEEDBACK_FORM = REPO_ROOT / "docs" / "templates" / "pilot-feedback-form.csv"
PILOT_DEFECT_REGISTER = (
    REPO_ROOT / "docs" / "templates" / "pilot-defect-register.csv"
)
PILOT_DAILY_LOG = REPO_ROOT / "docs" / "templates" / "pilot-daily-log.csv"


def test_pilot_execution_pack_doc_exists() -> None:
    assert PILOT_EXECUTION_PACK.is_file()


def test_pilot_execution_pack_mentions_pilot_execution() -> None:
    assert "Pilot Execution" in PILOT_EXECUTION_PACK.read_text()


def test_pilot_execution_pack_mentions_pilot_user_briefing() -> None:
    assert "Pilot User Briefing" in PILOT_EXECUTION_PACK.read_text()


def test_pilot_execution_pack_mentions_pilot_feedback() -> None:
    assert "Pilot Feedback" in PILOT_EXECUTION_PACK.read_text()


def test_pilot_execution_pack_mentions_defect_register() -> None:
    assert "Defect Register" in PILOT_EXECUTION_PACK.read_text()


def test_pilot_execution_pack_mentions_observation_log() -> None:
    assert "Observation Log" in PILOT_EXECUTION_PACK.read_text()


def test_pilot_execution_pack_mentions_sms_governance() -> None:
    assert "SMS governance" in PILOT_EXECUTION_PACK.read_text()


def test_pilot_execution_pack_mentions_authority_level() -> None:
    assert "Authority Level" in PILOT_EXECUTION_PACK.read_text()


def test_pilot_feedback_form_csv_exists() -> None:
    assert PILOT_FEEDBACK_FORM.is_file()


def test_pilot_defect_register_csv_exists() -> None:
    assert PILOT_DEFECT_REGISTER.is_file()


def test_pilot_daily_log_csv_exists() -> None:
    assert PILOT_DAILY_LOG.is_file()


def test_readme_links_to_pilot_execution_support_pack() -> None:
    text = (REPO_ROOT / "README.md").read_text()

    assert "pilot-execution-support-pack.md" in text


def test_pilot_deployment_checklist_links_to_pilot_execution_support_pack() -> None:
    text = (REPO_ROOT / "docs" / "pilot-deployment-checklist.md").read_text()

    assert "pilot-execution-support-pack.md" in text


def test_operation_manual_references_pilot_execution_support() -> None:
    text = (REPO_ROOT / "docs" / "operation-manual.md").read_text()

    assert "Pilot Execution Support Pack" in text


def test_release_notes_reference_pilot_execution_support() -> None:
    text = (REPO_ROOT / "docs" / "release-notes-v1.0.md").read_text()

    assert "pilot execution support" in text.lower()
