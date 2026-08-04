from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import shutil
import tempfile
import time
import uuid

from .config import settings


_PROFILE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_MAX_PROFILES = 12


@dataclass(frozen=True)
class AiProfile:
    profile_id: str
    name: str
    endpoint: str
    model: str
    api_key: str
    timeout_seconds: int
    updated_at_epoch_ms: int | None = None

    @property
    def ready(self) -> bool:
        return bool(self.endpoint.startswith("https://") and self.model and self.api_key)

    def public_dict(self, *, active: bool = False) -> dict[str, object]:
        return {
            "id": self.profile_id,
            "name": self.name,
            "endpoint": self.endpoint,
            "model": self.model,
            "has_api_key": bool(self.api_key),
            "api_key_hint": mask_secret(self.api_key),
            "timeout_seconds": self.timeout_seconds,
            "ready": self.ready,
            "active": active,
            "updated_at_epoch_ms": self.updated_at_epoch_ms,
        }


@dataclass(frozen=True)
class RuntimeAiRegistry:
    auto_predict: bool
    active_profile_id: str | None
    profiles: tuple[AiProfile, ...]
    updated_at_epoch_ms: int | None = None

    @property
    def active_profile(self) -> AiProfile | None:
        if self.active_profile_id:
            for profile in self.profiles:
                if profile.profile_id == self.active_profile_id:
                    return profile
        return self.profiles[0] if self.profiles else None

    def public_dict(self) -> dict[str, object]:
        active = self.active_profile
        active_id = active.profile_id if active else None
        return {
            "auto_predict": self.auto_predict,
            "active_profile_id": active_id,
            "profile_count": len(self.profiles),
            "profiles": [
                profile.public_dict(active=profile.profile_id == active_id)
                for profile in self.profiles
            ],
            "updated_at_epoch_ms": self.updated_at_epoch_ms,
        }


@dataclass(frozen=True)
class RuntimeAiConfig:
    enabled: bool
    endpoint: str
    model: str
    api_key: str
    timeout_seconds: int
    updated_at_epoch_ms: int | None = None
    profile_id: str | None = None
    profile_name: str = ""

    @property
    def ready(self) -> bool:
        return bool(self.endpoint.startswith("https://") and self.model and self.api_key)

    @property
    def complete(self) -> bool:
        return bool(self.enabled and self.ready)

    def public_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "auto_predict": self.enabled,
            "configured": self.ready,
            "active": self.complete,
            "endpoint": self.endpoint,
            "model": self.model,
            "profile_id": self.profile_id,
            "profile_name": self.profile_name,
            "has_api_key": bool(self.api_key),
            "api_key_hint": mask_secret(self.api_key),
            "timeout_seconds": self.timeout_seconds,
            "updated_at_epoch_ms": self.updated_at_epoch_ms,
        }


def _legacy_config_path() -> str:
    return os.path.join(settings.data_dir, "runtime-ai.json")


def _legacy_key_path() -> str:
    return os.path.join(settings.data_dir, "runtime-ai.key")


def _registry_path() -> str:
    return os.path.join(settings.data_dir, "runtime-ai-profiles.json")


def _keys_dir() -> str:
    return os.path.join(settings.data_dir, "runtime-ai-keys")


def _key_path(profile_id: str) -> str:
    if not _PROFILE_ID_RE.fullmatch(profile_id):
        raise ValueError("模型配置 ID 无效")
    return os.path.join(_keys_dir(), f"{profile_id}.key")


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


def _normalized_timeout(value: int) -> int:
    return max(20, min(300, int(value)))


def _validated_endpoint(value: str) -> str:
    endpoint = value.strip().rstrip("/")
    if endpoint and not endpoint.startswith("https://"):
        raise ValueError("AI 接口必须使用 HTTPS")
    return endpoint


def _profile_name(value: str, model: str) -> str:
    return (value.strip() or model.strip() or "未命名模型")[:80]


def _environment_registry() -> RuntimeAiRegistry:
    endpoint = settings.ai_endpoint.strip().rstrip("/")
    model = settings.ai_model.strip()
    key = settings.ai_api_key.strip()
    if not endpoint and not model and not key:
        return RuntimeAiRegistry(False, None, ())
    profile = AiProfile(
        profile_id="environment",
        name=_profile_name("环境配置", model),
        endpoint=endpoint,
        model=model,
        api_key=key,
        timeout_seconds=_normalized_timeout(settings.ai_timeout_seconds),
    )
    return RuntimeAiRegistry(settings.ai_enabled, profile.profile_id, (profile,))


def _legacy_registry() -> RuntimeAiRegistry:
    raw = _read_text(_legacy_config_path()).strip()
    if not raw:
        return _environment_registry()
    try:
        value = json.loads(raw)
        endpoint = str(value.get("endpoint") or "").strip().rstrip("/")
        model = str(value.get("model") or "").strip()
        timeout = _normalized_timeout(int(value.get("timeout_seconds") or settings.ai_timeout_seconds))
        updated_at = int(value.get("updated_at_epoch_ms") or 0) or None
        key = _read_text(_legacy_key_path()).strip() or settings.ai_api_key
        profile = AiProfile(
            profile_id="default",
            name=_profile_name("默认模型", model),
            endpoint=endpoint,
            model=model,
            api_key=key,
            timeout_seconds=timeout,
            updated_at_epoch_ms=updated_at,
        )
        return RuntimeAiRegistry(
            auto_predict=bool(value.get("enabled", True)),
            active_profile_id=profile.profile_id,
            profiles=(profile,),
            updated_at_epoch_ms=updated_at,
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return _environment_registry()


def load_ai_registry() -> RuntimeAiRegistry:
    raw = _read_text(_registry_path()).strip()
    if not raw:
        return _legacy_registry()
    try:
        value = json.loads(raw)
        raw_profiles = value.get("profiles")
        if not isinstance(raw_profiles, list):
            raise ValueError("模型配置格式异常")
        profiles: list[AiProfile] = []
        legacy_key = _read_text(_legacy_key_path()).strip()
        for item in raw_profiles[:_MAX_PROFILES]:
            if not isinstance(item, dict):
                continue
            profile_id = str(item.get("id") or "").strip()
            if not _PROFILE_ID_RE.fullmatch(profile_id):
                continue
            endpoint = str(item.get("endpoint") or "").strip().rstrip("/")
            model = str(item.get("model") or "").strip()
            key = _read_text(_key_path(profile_id)).strip()
            if not key and len(raw_profiles) == 1:
                key = legacy_key or settings.ai_api_key
            profiles.append(
                AiProfile(
                    profile_id=profile_id,
                    name=_profile_name(str(item.get("name") or ""), model),
                    endpoint=endpoint,
                    model=model,
                    api_key=key,
                    timeout_seconds=_normalized_timeout(
                        int(item.get("timeout_seconds") or settings.ai_timeout_seconds)
                    ),
                    updated_at_epoch_ms=int(item.get("updated_at_epoch_ms") or 0) or None,
                )
            )
        active_id = str(value.get("active_profile_id") or "").strip() or None
        if active_id not in {profile.profile_id for profile in profiles}:
            active_id = profiles[0].profile_id if profiles else None
        return RuntimeAiRegistry(
            auto_predict=bool(value.get("auto_predict", False)),
            active_profile_id=active_id,
            profiles=tuple(profiles),
            updated_at_epoch_ms=int(value.get("updated_at_epoch_ms") or 0) or None,
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return _legacy_registry()


def _persist_registry(registry: RuntimeAiRegistry) -> None:
    now = int(time.time() * 1000)
    payload = {
        "version": 2,
        "auto_predict": registry.auto_predict,
        "active_profile_id": registry.active_profile_id,
        "updated_at_epoch_ms": now,
        "profiles": [
            {
                "id": profile.profile_id,
                "name": profile.name,
                "endpoint": profile.endpoint,
                "model": profile.model,
                "timeout_seconds": profile.timeout_seconds,
                "updated_at_epoch_ms": profile.updated_at_epoch_ms,
            }
            for profile in registry.profiles
        ],
    }
    _atomic_write(_registry_path(), json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    for profile in registry.profiles:
        if profile.api_key:
            _atomic_write(_key_path(profile.profile_id), profile.api_key)


def load_ai_profile(profile_id: str | None) -> AiProfile | None:
    registry = load_ai_registry()
    if not profile_id:
        return registry.active_profile
    return next((item for item in registry.profiles if item.profile_id == profile_id), None)


def load_ai_config() -> RuntimeAiConfig:
    registry = load_ai_registry()
    profile = registry.active_profile
    if profile is None:
        return RuntimeAiConfig(
            enabled=registry.auto_predict,
            endpoint="",
            model="",
            api_key="",
            timeout_seconds=_normalized_timeout(settings.ai_timeout_seconds),
            updated_at_epoch_ms=registry.updated_at_epoch_ms,
        )
    return RuntimeAiConfig(
        enabled=registry.auto_predict,
        endpoint=profile.endpoint,
        model=profile.model,
        api_key=profile.api_key,
        timeout_seconds=profile.timeout_seconds,
        updated_at_epoch_ms=profile.updated_at_epoch_ms,
        profile_id=profile.profile_id,
        profile_name=profile.name,
    )


def save_ai_profile(
    *,
    profile_id: str | None,
    name: str,
    endpoint: str,
    model: str,
    api_key: str | None,
    timeout_seconds: int,
    activate: bool = False,
) -> AiProfile:
    registry = load_ai_registry()
    profiles = list(registry.profiles)
    existing = next((item for item in profiles if item.profile_id == profile_id), None)
    if profile_id and existing is None:
        raise ValueError("没有找到要修改的模型配置")
    if existing is None and len(profiles) >= _MAX_PROFILES:
        raise ValueError(f"最多保存 {_MAX_PROFILES} 个模型配置")

    normalized_endpoint = _validated_endpoint(endpoint)
    normalized_model = model.strip()
    if not normalized_endpoint or not normalized_model:
        raise ValueError("请填写接口地址和模型名")
    final_id = existing.profile_id if existing else uuid.uuid4().hex[:12]
    final_key = existing.api_key if existing and api_key is None else (api_key or "").strip()
    now = int(time.time() * 1000)
    result = AiProfile(
        profile_id=final_id,
        name=_profile_name(name, normalized_model),
        endpoint=normalized_endpoint,
        model=normalized_model,
        api_key=final_key,
        timeout_seconds=_normalized_timeout(timeout_seconds),
        updated_at_epoch_ms=now,
    )
    if existing:
        profiles = [result if item.profile_id == final_id else item for item in profiles]
    else:
        profiles.append(result)

    active_id = registry.active_profile_id
    if activate or not active_id:
        active_id = final_id
    updated = RuntimeAiRegistry(
        auto_predict=registry.auto_predict,
        active_profile_id=active_id,
        profiles=tuple(profiles),
        updated_at_epoch_ms=now,
    )
    _persist_registry(updated)
    return result


def activate_ai_profile(profile_id: str) -> RuntimeAiRegistry:
    registry = load_ai_registry()
    if profile_id not in {profile.profile_id for profile in registry.profiles}:
        raise ValueError("没有找到要启用的模型配置")
    updated = RuntimeAiRegistry(
        auto_predict=registry.auto_predict,
        active_profile_id=profile_id,
        profiles=registry.profiles,
        updated_at_epoch_ms=int(time.time() * 1000),
    )
    _persist_registry(updated)
    return load_ai_registry()


def delete_ai_profile(profile_id: str) -> RuntimeAiRegistry:
    registry = load_ai_registry()
    if profile_id not in {profile.profile_id for profile in registry.profiles}:
        raise ValueError("没有找到要删除的模型配置")
    profiles = tuple(profile for profile in registry.profiles if profile.profile_id != profile_id)
    active_id = registry.active_profile_id
    if active_id == profile_id:
        active_id = profiles[0].profile_id if profiles else None
    active = next((profile for profile in profiles if profile.profile_id == active_id), None)
    auto_predict = registry.auto_predict and bool(active and active.ready)
    updated = RuntimeAiRegistry(
        auto_predict=auto_predict,
        active_profile_id=active_id,
        profiles=profiles,
        updated_at_epoch_ms=int(time.time() * 1000),
    )
    _persist_registry(updated)
    try:
        os.remove(_key_path(profile_id))
    except FileNotFoundError:
        pass
    return load_ai_registry()


def set_ai_auto_predict(enabled: bool) -> RuntimeAiRegistry:
    registry = load_ai_registry()
    if enabled and not (registry.active_profile and registry.active_profile.ready):
        raise ValueError("开启自动预测前，请先选择并完整配置一个可用模型")
    updated = RuntimeAiRegistry(
        auto_predict=enabled,
        active_profile_id=registry.active_profile_id,
        profiles=registry.profiles,
        updated_at_epoch_ms=int(time.time() * 1000),
    )
    _persist_registry(updated)
    return load_ai_registry()


def save_ai_config(
    *,
    enabled: bool,
    endpoint: str,
    model: str,
    api_key: str | None,
    timeout_seconds: int,
) -> RuntimeAiConfig:
    registry = load_ai_registry()
    active = registry.active_profile
    saved = save_ai_profile(
        profile_id=active.profile_id if active else None,
        name=active.name if active else model,
        endpoint=endpoint,
        model=model,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        activate=True,
    )
    if enabled and not saved.ready:
        raise ValueError("启用云端 AI 时必须配置 API Key")
    set_ai_auto_predict(enabled)
    return load_ai_config()


def clear_runtime_ai_config() -> None:
    for path in (_legacy_config_path(), _legacy_key_path(), _registry_path()):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    shutil.rmtree(_keys_dir(), ignore_errors=True)
