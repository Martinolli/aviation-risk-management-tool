from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PILOT_CHECKLIST = REPO_ROOT / "docs" / "pilot-deployment-checklist.md"
PILOT_CHECKLIST_CSV = (
    REPO_ROOT / "docs" / "templates" / "pilot-deployment-checklist.csv"
)
PILOT_GO_NO_GO_CSV = (
    REPO_ROOT / "docs" / "templates" / "pilot-go-no-go-decision.csv"
)
PILOT_ROLLBACK_LOG_CSV = (
    REPO_ROOT / "docs" / "templates" / "pilot-rollback-log.csv"
)


def test_pilot_deployment_checklist_doc_exists() -> None:
    assert PILOT_CHECKLIST.is_file()


def test_pilot_checklist_mentions_pilot_deployment() -> None:
    assert "Pilot Deployment" in PILOT_CHECKLIST.read_text()


def test_pilot_checklist_mentions_go_no_go() -> None:
    assert "Go / No-Go" in PILOT_CHECKLIST.read_text()


def test_pilot_checklist_mentions_rollback_plan() -> None:
    assert "Rollback Plan" in PILOT_CHECKLIST.read_text()


def test_pilot_checklist_mentions_post_deployment_monitoring() -> None:
    assert "Post-Deployment Monitoring" in PILOT_CHECKLIST.read_text()


def test_pilot_checklist_mentions_authority_level() -> None:
    assert "Authority Level" in PILOT_CHECKLIST.read_text()


def test_pilot_checklist_mentions_sms_governance() -> None:
    assert "SMS governance" in PILOT_CHECKLIST.read_text()


def test_pilot_checklist_includes_env_001() -> None:
    assert "ENV-001" in PILOT_CHECKLIST.read_text()


def test_pilot_checklist_includes_ci_001() -> None:
    assert "CI-001" in PILOT_CHECKLIST.read_text()


def test_pilot_checklist_includes_uat_001() -> None:
    assert "UAT-001" in PILOT_CHECKLIST.read_text()


def test_pilot_checklist_includes_log_001() -> None:
    assert "LOG-001" in PILOT_CHECKLIST.read_text()


def test_pilot_checklist_includes_pilot_sign_off() -> None:
    assert "pilot sign-off" in PILOT_CHECKLIST.read_text().lower()


def test_pilot_deployment_checklist_csv_exists() -> None:
    assert PILOT_CHECKLIST_CSV.is_file()


def test_pilot_go_no_go_decision_csv_exists() -> None:
    assert PILOT_GO_NO_GO_CSV.is_file()


def test_pilot_rollback_log_csv_exists() -> None:
    assert PILOT_ROLLBACK_LOG_CSV.is_file()


def test_readme_links_to_pilot_deployment_checklist() -> None:
    text = (REPO_ROOT / "README.md").read_text()

    assert "pilot-deployment-checklist.md" in text


def test_deployment_readiness_guide_links_to_pilot_deployment_checklist() -> None:
    text = (REPO_ROOT / "docs" / "deployment-readiness.md").read_text()

    assert "pilot-deployment-checklist.md" in text


def test_uat_pack_references_pilot_deployment_checklist() -> None:
    text = (REPO_ROOT / "docs" / "user-acceptance-test-pack.md").read_text()

    assert "pilot-deployment-checklist.md" in text
