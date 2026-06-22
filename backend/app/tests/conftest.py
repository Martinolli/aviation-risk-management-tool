import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def enable_x_user_id_auth_fallback_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retain temporary legacy-header coverage while production defaults to disabled."""
    monkeypatch.setattr(settings, "enable_x_user_id_auth_fallback", True)
