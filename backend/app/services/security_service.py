from passlib.context import CryptContext

MINIMUM_PASSWORD_LENGTH = 8
MAXIMUM_BCRYPT_PASSWORD_BYTES = 72
_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityBusinessRuleError(ValueError):
    pass


def hash_password(plain_password: str) -> str:
    if not plain_password or not plain_password.strip():
        raise SecurityBusinessRuleError("Password must not be blank")
    if len(plain_password) < MINIMUM_PASSWORD_LENGTH:
        raise SecurityBusinessRuleError(
            f"Password must be at least {MINIMUM_PASSWORD_LENGTH} characters"
        )
    if len(plain_password.encode("utf-8")) > MAXIMUM_BCRYPT_PASSWORD_BYTES:
        raise SecurityBusinessRuleError(
            "Password must not exceed 72 bytes when encoded as UTF-8"
        )
    return _password_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str | None) -> bool:
    if not plain_password or not plain_password.strip() or not password_hash or not password_hash.strip():
        return False
    if len(plain_password.encode("utf-8")) > MAXIMUM_BCRYPT_PASSWORD_BYTES:
        return False
    try:
        return _password_context.verify(plain_password, password_hash)
    except (ValueError, TypeError):
        return False
