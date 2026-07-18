from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
UAT_PACK = REPO_ROOT / "docs" / "user-acceptance-test-pack.md"
UAT_MATRIX = REPO_ROOT / "docs" / "templates" / "uat-test-matrix.csv"
UAT_DEFECT_LOG = REPO_ROOT / "docs" / "templates" / "uat-defect-log.csv"


def test_uat_pack_doc_exists() -> None:
    assert UAT_PACK.is_file()


def test_uat_pack_mentions_user_acceptance_test() -> None:
    assert "User Acceptance Test" in UAT_PACK.read_text()


def test_uat_pack_mentions_pilot_validation() -> None:
    assert "Pilot Validation" in UAT_PACK.read_text()


def test_uat_pack_includes_uat_001() -> None:
    assert "UAT-001" in UAT_PACK.read_text()


def test_uat_pack_includes_uat_046() -> None:
    assert "UAT-046" in UAT_PACK.read_text()


def test_uat_pack_includes_pass_fail() -> None:
    assert "Pass / Fail" in UAT_PACK.read_text()


def test_uat_pack_includes_defect_log() -> None:
    assert "Defect Log" in UAT_PACK.read_text()


def test_uat_pack_includes_sign_off() -> None:
    assert "Sign-Off" in UAT_PACK.read_text()


def test_uat_test_matrix_csv_exists() -> None:
    assert UAT_MATRIX.is_file()


def test_uat_defect_log_csv_exists() -> None:
    assert UAT_DEFECT_LOG.is_file()


def test_readme_links_to_uat_pack() -> None:
    text = (REPO_ROOT / "README.md").read_text()

    assert "user-acceptance-test-pack.md" in text


def test_deployment_readiness_guide_links_to_uat_pack() -> None:
    text = (REPO_ROOT / "docs" / "deployment-readiness.md").read_text()

    assert "user-acceptance-test-pack.md" in text
