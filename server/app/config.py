from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_path: str
    api_token: str
    poll_seconds: int
    history_days: int
    public_base_url: str
    ai_endpoint: str
    ai_model: str
    ai_api_key: str
    ai_timeout_seconds: int

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_endpoint and self.ai_model and self.ai_api_key)


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def load_settings() -> Settings:
    return Settings(
        database_path=os.getenv("TIANJI_DATABASE", "/app/data/tianji.db").strip(),
        api_token=os.getenv("TIANJI_API_TOKEN", "").strip(),
        poll_seconds=_int_env("TIANJI_POLL_SECONDS", 30, 15, 3600),
        history_days=_int_env("TIANJI_HISTORY_DAYS", 14, 2, 40),
        public_base_url=os.getenv("TIANJI_PUBLIC_BASE_URL", "").strip().rstrip("/"),
        ai_endpoint=os.getenv("TIANJI_AI_ENDPOINT", "").strip(),
        ai_model=os.getenv("TIANJI_AI_MODEL", "").strip(),
        ai_api_key=os.getenv("TIANJI_AI_API_KEY", "").strip(),
        ai_timeout_seconds=_int_env("TIANJI_AI_TIMEOUT_SECONDS", 120, 20, 300),
    )


settings = load_settings()
