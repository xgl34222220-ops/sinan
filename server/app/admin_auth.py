from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import tempfile
import time

from .config import settings


SESSION_COOKIE = "tianji_admin_session"
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
PBKDF2_ITERATIONS = 310_000


def _password_path() -> str:
    return os.path.join(settings.data_dir, "admin-password.hash")


def _read_password_hash() -> str:
    try:
        with open(_password_path(), "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return ""


def _atomic_write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".tianji-admin-", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("管理密码至少需要 8 个字符")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password_hash(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def admin_password_configured() -> bool:
    return bool(_read_password_hash() or settings.admin_password)


def verify_admin_password(password: str) -> bool:
    encoded = _read_password_hash()
    if encoded:
        return verify_password_hash(password, encoded)
    return bool(settings.admin_password) and hmac.compare_digest(password, settings.admin_password)


def change_admin_password(new_password: str) -> None:
    _atomic_write(_password_path(), hash_password(new_password))


def _session_secret() -> bytes:
    source = settings.api_token or settings.admin_password
    if not source:
        source = "tianji-unconfigured-session-secret"
    return hashlib.sha256(("tianji-admin-session:" + source).encode("utf-8")).digest()


def create_session() -> str:
    issued_at = int(time.time())
    nonce = secrets.token_bytes(16)
    payload = struct.pack(">Q", issued_at) + nonce
    signature = hmac.new(_session_secret(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + signature).decode("ascii").rstrip("=")


def verify_session(token: str | None) -> bool:
    if not token:
        return False
    try:
        padded = token + "=" * (-len(token) % 4)
        value = base64.urlsafe_b64decode(padded.encode("ascii"))
        if len(value) != 8 + 16 + 32:
            return False
        payload, supplied = value[:-32], value[-32:]
        expected = hmac.new(_session_secret(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(supplied, expected):
            return False
        issued_at = struct.unpack(">Q", payload[:8])[0]
        now = int(time.time())
        return issued_at <= now + 60 and now - issued_at <= SESSION_TTL_SECONDS
    except (ValueError, TypeError, struct.error):
        return False
