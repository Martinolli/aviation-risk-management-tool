import pytest

from app.services.security_service import (
    SecurityBusinessRuleError,
    hash_password,
    verify_password,
)


@pytest.mark.parametrize("password", ["", "   ", "short"])
def test_hash_password_rejects_blank_and_too_short_passwords(password: str) -> None:
    with pytest.raises(SecurityBusinessRuleError):
        hash_password(password)


def test_hash_and_verify_password() -> None:
    password = "StrongPassword123!"

    password_hash = hash_password(password)

    assert password_hash
    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("WrongPassword123!", password_hash)


def test_hash_password_rejects_password_longer_than_72_utf8_bytes() -> None:
    with pytest.raises(
        SecurityBusinessRuleError,
        match="must not exceed 72 bytes when encoded as UTF-8",
    ):
        hash_password("a" * 73)


def test_verify_password_rejects_password_longer_than_72_utf8_bytes() -> None:
    password_hash = hash_password("StrongPassword123!")

    assert not verify_password("a" * 73, password_hash)


@pytest.mark.parametrize("plain_password,password_hash", [
    ("", "hash"),
    ("   ", "hash"),
    ("StrongPassword123!", None),
    ("StrongPassword123!", ""),
    ("StrongPassword123!", "   "),
])
def test_verify_password_rejects_blank_input_or_missing_hash(
    plain_password: str,
    password_hash: str | None,
) -> None:
    assert not verify_password(plain_password, password_hash)
