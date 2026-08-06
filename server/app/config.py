from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_path: str
    api_token: str
    admin_password: str
    poll_seconds: int
    history_days: int
    public_base_url: str
    ai_endpoint: str
    ai_model: str
    ai_api_key: str
    ai_timeout_seconds: int
    fcm_project_id: str
    fcm_service_account_b64: str
    telegram_bot_token: str
    telegram_chat_ids: tuple[str, ...]
    push_threshold: int
    push_delivery_workers: int
    push_retry_seconds: int
    push_delivery_retention_days: int
    push_device_stale_days: int
    docs_enabled: bool
    login_max_failures: int
    login_window_seconds: int
    login_lock_seconds: int
    worker_cycle_timeout_seconds: int
    worker_backoff_max_seconds: int
    backup_interval_seconds: int
    backup_retention_daily: int
    backup_retention_monthly: int

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_endpoint and self.ai_model and self.ai_api_key)

    @property
    def fcm_enabled(self) -> bool:
        return bool(self.fcm_project_id and self.fcm_service_account_b64)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_ids)

    @property
    def data_dir(self) -> str:
        return os.path.dirname(self.database_path) or "."


def _list_env(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "").replace(";", ",").replace("\n", ",")
    values: list[str] = []
    seen: set[str] = set()
    for item in raw.split(","):
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)
    return tuple(values)


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "enabled"}


def load_settings() -> Settings:
    return Settings(
        database_path=os.getenv("TIANJI_DATABASE", "./data/tianji.db").strip(),
        api_token=os.getenv("TIANJI_API_TOKEN", "").strip(),
        admin_password=os.getenv("TIANJI_ADMIN_PASSWORD", "").strip(),
        poll_seconds=_int_env("TIANJI_POLL_SECONDS", 30, 15, 3600),
        history_days=_int_env("TIANJI_HISTORY_DAYS", 14, 2, 40),
        public_base_url=os.getenv("TIANJI_PUBLIC_BASE_URL", "").strip().rstrip("/"),
        ai_endpoint=os.getenv("TIANJI_AI_ENDPOINT", "").strip(),
        ai_model=os.getenv("TIANJI_AI_MODEL", "").strip(),
        ai_api_key=os.getenv("TIANJI_AI_API_KEY", "").strip(),
        ai_timeout_seconds=_int_env("TIANJI_AI_TIMEOUT_SECONDS", 120, 20, 300),
        fcm_project_id=os.getenv("TIANJI_FCM_PROJECT_ID", "").strip(),
        fcm_service_account_b64=os.getenv("TIANJI_FCM_SERVICE_ACCOUNT_B64", "").strip(),
        telegram_bot_token=os.getenv("TIANJI_TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_ids=_list_env("TIANJI_TELEGRAM_CHAT_IDS"),
        push_threshold=_int_env("TIANJI_PUSH_THRESHOLD", 3, 3, 10),
        push_delivery_workers=_int_env("TIANJI_PUSH_DELIVERY_WORKERS", 6, 1, 32),
        push_retry_seconds=_int_env("TIANJI_PUSH_RETRY_SECONDS", 300, 60, 3600),
        push_delivery_retention_days=_int_env(
            "TIANJI_PUSH_DELIVERY_RETENTION_DAYS", 45, 7, 365
        ),
        push_device_stale_days=_int_env("TIANJI_PUSH_DEVICE_STALE_DAYS", 90, 7, 730),
        docs_enabled=_bool_env("TIANJI_DOCS_ENABLED", False),
        login_max_failures=_int_env("TIANJI_LOGIN_MAX_FAILURES", 5, 3, 20),
        login_window_seconds=_int_env("TIANJI_LOGIN_WINDOW_SECONDS", 600, 60, 86_400),
        login_lock_seconds=_int_env("TIANJI_LOGIN_LOCK_SECONDS", 900, 60, 86_400),
        worker_cycle_timeout_seconds=_int_env(
            "TIANJI_WORKER_CYCLE_TIMEOUT_SECONDS", 240, 60, 1800
        ),
        worker_backoff_max_seconds=_int_env(
            "TIANJI_WORKER_BACKOFF_MAX_SECONDS", 600, 60, 3600
        ),
        backup_interval_seconds=_int_env(
            "TIANJI_BACKUP_INTERVAL_SECONDS", 86_400, 3600, 604_800
        ),
        backup_retention_daily=_int_env("TIANJI_BACKUP_RETENTION_DAILY", 7, 2, 90),
        backup_retention_monthly=_int_env("TIANJI_BACKUP_RETENTION_MONTHLY", 6, 1, 36),
    )


settings = load_settings()
