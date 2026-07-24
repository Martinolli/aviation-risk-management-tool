from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
POST_PILOT_GUIDE = REPO_ROOT / "docs" / "post-pilot-feedback-and-defect-register.md"
POST_PILOT_FEEDBACK_REGISTER = (
    REPO_ROOT / "docs" / "templates" / "post-pilot-feedback-register.csv"
)
POST_PILOT_CLOSEOUT_REPORT = (
    REPO_ROOT / "docs" / "templates" / "post-pilot-closeout-report-template.md"
)
POST_PILOT_TASK_BACKLOG = (
    REPO_ROOT / "docs" / "templates" / "post-pilot-task-backlog.csv"
)


def test_post_pilot_feedback_guide_doc_exists() -> None:
    assert POST_PILOT_GUIDE.is_file()


def test_post_pilot_feedback_guide_mentions_post_pilot_feedback() -> None:
    assert "Post-Pilot Feedback" in POST_PILOT_GUIDE.read_text()


def test_post_pilot_feedback_guide_mentions_defect_register() -> None:
    assert "Defect Register" in POST_PILOT_GUIDE.read_text()


def test_post_pilot_feedback_guide_mentions_observation_log() -> None:
    assert "Observation Log" in POST_PILOT_GUIDE.read_text()


def test_post_pilot_feedback_guide_mentions_enhancement_request() -> None:
    assert "Enhancement Request" in POST_PILOT_GUIDE.read_text()


def test_post_pilot_feedback_guide_mentions_training_need() -> None:
    assert "Training Need" in POST_PILOT_GUIDE.read_text()


def test_post_pilot_feedback_guide_mentions_governance_question() -> None:
    assert "Governance Question" in POST_PILOT_GUIDE.read_text()


def test_post_pilot_feedback_guide_mentions_request_id() -> None:
    assert "Request ID" in POST_PILOT_GUIDE.read_text()


def test_post_pilot_feedback_guide_mentions_sms_governance() -> None:
    assert "SMS governance" in POST_PILOT_GUIDE.read_text()


def test_post_pilot_feedback_register_csv_exists() -> None:
    assert POST_PILOT_FEEDBACK_REGISTER.is_file()


def test_post_pilot_closeout_report_template_exists() -> None:
    assert POST_PILOT_CLOSEOUT_REPORT.is_file()


def test_post_pilot_task_backlog_csv_exists() -> None:
    assert POST_PILOT_TASK_BACKLOG.is_file()


def test_readme_links_to_post_pilot_feedback_guide() -> None:
    text = (REPO_ROOT / "README.md").read_text()

    assert "post-pilot-feedback-and-defect-register.md" in text


def test_pilot_execution_pack_links_to_post_pilot_feedback_guide() -> None:
    text = (REPO_ROOT / "docs" / "pilot-execution-support-pack.md").read_text()

    assert "post-pilot-feedback-and-defect-register.md" in text


def test_release_notes_mention_post_pilot_feedback() -> None:
    text = (REPO_ROOT / "docs" / "release-notes-v1.0.md").read_text()

    assert "post-pilot feedback" in text.lower()


def test_operation_manual_references_post_pilot_feedback_process() -> None:
    text = (REPO_ROOT / "docs" / "operation-manual.md").read_text()

    assert "post-pilot feedback process" in text.lower()
