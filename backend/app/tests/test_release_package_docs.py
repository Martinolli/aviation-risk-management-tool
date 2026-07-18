from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RELEASE_NOTES = REPO_ROOT / "docs" / "release-notes-v1.0.md"
RELEASE_CHECKLIST = REPO_ROOT / "docs" / "release-package-checklist.md"
RELEASE_CHECKLIST_CSV = (
    REPO_ROOT / "docs" / "templates" / "release-package-checklist.csv"
)


def test_release_notes_doc_exists() -> None:
    assert RELEASE_NOTES.is_file()


def test_release_notes_mention_release_notes() -> None:
    assert "Release Notes" in RELEASE_NOTES.read_text()


def test_release_notes_mention_version_1_0() -> None:
    assert "Version 1.0" in RELEASE_NOTES.read_text()


def test_release_notes_mention_pilot_release_candidate() -> None:
    assert "Pilot Release Candidate" in RELEASE_NOTES.read_text()


def test_release_notes_mention_validation_evidence() -> None:
    assert "Validation Evidence" in RELEASE_NOTES.read_text()


def test_release_notes_mention_known_limitations() -> None:
    assert "Known Limitations" in RELEASE_NOTES.read_text()


def test_release_notes_mention_llm_advisory_not_included() -> None:
    assert "LLM advisory interface not included" in RELEASE_NOTES.read_text()


def test_release_notes_mention_pilot_tag() -> None:
    assert "v1.0.0-pilot" in RELEASE_NOTES.read_text()


def test_release_notes_mention_go_no_go() -> None:
    assert "Go / No-Go" in RELEASE_NOTES.read_text()


def test_release_package_checklist_doc_exists() -> None:
    assert RELEASE_CHECKLIST.is_file()


def test_release_package_checklist_mentions_operation_manual() -> None:
    assert "Operation Manual" in RELEASE_CHECKLIST.read_text()


def test_release_package_checklist_mentions_uat_pack() -> None:
    assert "UAT Pack" in RELEASE_CHECKLIST.read_text()


def test_release_package_checklist_mentions_pilot_deployment_checklist() -> None:
    assert "Pilot Deployment Checklist" in RELEASE_CHECKLIST.read_text()


def test_release_package_checklist_csv_exists() -> None:
    assert RELEASE_CHECKLIST_CSV.is_file()


def test_readme_links_to_release_notes() -> None:
    text = (REPO_ROOT / "README.md").read_text()

    assert "release-notes-v1.0.md" in text


def test_readme_links_to_release_package_checklist() -> None:
    text = (REPO_ROOT / "README.md").read_text()

    assert "release-package-checklist.md" in text


def test_operation_manual_links_to_release_notes() -> None:
    text = (REPO_ROOT / "docs" / "operation-manual.md").read_text()

    assert "release-notes-v1.0.md" in text


def test_pilot_deployment_checklist_references_release_notes_v1_0() -> None:
    text = (REPO_ROOT / "docs" / "pilot-deployment-checklist.md").read_text()

    assert "Release Notes v1.0" in text
