from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
import tempfile
import time

from .config import settings


@dataclass(frozen=True)
class RuntimeAiConfig:
    enabled: bool
    endpoint: str
    model: str
    api_key: str
    timeout_seconds: int
    updated_at_epoch_ms: int | None = None

    @property
    def complete(self) -> bool:
        return bool(self.enabled and self.endpoint.startswith("https://") and self.model and self.api_key)

    def public_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "configured": self.complete,
            "endpoint": self.endpoint,
            "model": self.model,
            "has_api_key": bool(self.api_key),
            "api_key_hint": mask_secret(self.api_key),
            "timeout_seconds": self.timeout_seconds,
            "updated_at_epoch_ms": self.updated_at_epoch_ms,
        }


def _config_path() -> str:
    return os.path.join(settings.data_dir, "runtime-ai.json")


def _key_path() -> str:
    return os.path.join(settings.data_dir, "runtime-ai.key")


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return ""


def _atomic_write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".tianji-", dir=os.path.dirname(path) or ".")
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


def mask_secret(value: str) -> str:
    text = value.strip()
    if not text:
        return "未配置"
    if len(text) <= 10:
        return "•" * len(text)
    return f"{text[:4]}••••••{text[-4:]}"


def environment_ai_config() -> RuntimeAiConfig:
    return RuntimeAiConfig(
        enabled=settings.ai_enabled,
        endpoint=settings.ai_endpoint,
        model=settings.ai_model,
        api_key=settings.ai_api_key,
        timeout_seconds=settings.ai_timeout_seconds,
        updated_at_epoch_ms=None,
    )


def load_ai_config() -> RuntimeAiConfig:
    raw = _read_text(_config_path()).strip()
    if not raw:
        return environment_ai_config()
    try:
        value = json.loads(raw)
        endpoint = str(value.get("endpoint") or "").strip()
        model = str(value.get("model") or "").strip()
        timeout = int(value.get("timeout_seconds") or settings.ai_timeout_seconds)
        updated_at = int(value.get("updated_at_epoch_ms") or 0) or None
        api_key = _read_text(_key_path()).strip() or settings.ai_api_key
        return RuntimeAiConfig(
            enabled=bool(value.get("enabled", True)),
            endpoint=endpoint,
            model=model,
            api_key=api_key,
            timeout_seconds=max(20, min(300, timeout)),
            updated_at_epoch_ms=updated_at,
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return environment_ai_config()


def save_ai_config(
    *,
    enabled: bool,
    endpoint: str,
    model: str,
    api_key: str | None,
    timeout_seconds: int,
) -> RuntimeAiConfig:
    normalized_endpoint = endpoint.strip().rstrip("/")
    normalized_model = model.strip()
    if normalized_endpoint and not normalized_endpoint.startswith("https://"):
        raise ValueError("AI 接口必须使用 HTTPS")
    if enabled and (not normalized_endpoint or not normalized_model):
        raise ValueError("启用云端 AI 时必须填写接口地址和模型名")

    current = load_ai_config()
    final_key = current.api_key if api_key is None else api_key.strip()
    now = int(time.time() * 1000)
    result = RuntimeAiConfig(
        enabled=enabled,
        endpoint=normalized_endpoint,
        model=normalized_model,
        api_key=final_key,
        timeout_seconds=max(20, min(300, int(timeout_seconds))),
        updated_at_epoch_ms=now,
    )
    payload = asdict(result)
    payload.pop("api_key", None)
    _atomic_write(_config_path(), json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    if api_key is not None:
        _atomic_write(_key_path(), final_key)
    return result


def clear_runtime_ai_config() -> None:
    for path in (_config_path(), _key_path()):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
