from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .config import settings


_PROCESS_STARTED_AT_EPOCH_MS = int(time.time() * 1000)
_STATUS_LABELS = {
    "unknown": "等待部署状态",
    "up_to_date": "当前已经是最新版本",
    "updated": "新版本已部署并通过健康检查",
    "source_synced": "仓库已同步，云端无需重建",
    "updating": "正在拉取并验证新版本",
    "check_failed": "无法检查远端版本",
    "backup_failed": "数据库备份失败，更新已取消",
    "blocked": "该版本曾部署失败，已暂停重试",
    "rolling_back": "健康检查失败，正在自动回滚",
    "rolled_back": "新版本失败，已恢复旧版本",
    "rollback_failed": "自动回滚失败，需要人工检查",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _short(value: object) -> str:
    text = str(value or "").strip()
    return text[:12] if text else ""


def deployment_status(service_version: str) -> dict[str, Any]:
    data_dir = Path(settings.data_dir)
    status_path = data_dir / "auto-update-status.json"
    blocked_path = data_dir / "auto-update-blocked-commit"
    raw = _read_json(status_path)

    status = str(raw.get("status") or "unknown")
    from_commit = _short(raw.get("from_commit"))
    target_commit = _short(raw.get("to_commit"))
    blocked_commit = ""
    try:
        blocked_commit = _short(blocked_path.read_text(encoding="utf-8"))
    except OSError:
        pass

    if status in {"updated", "source_synced", "up_to_date"}:
        current_commit = target_commit or from_commit
    elif status in {"rolled_back", "rolling_back", "rollback_failed", "blocked"}:
        current_commit = from_commit
    else:
        current_commit = from_commit or target_commit

    updated_at = raw.get("updated_at_epoch_ms")
    try:
        updated_at_epoch_ms = int(updated_at) if updated_at is not None else None
    except (TypeError, ValueError):
        updated_at_epoch_ms = None

    is_current = bool(current_commit and target_commit and current_commit == target_commit)
    requires_attention = status in {
        "check_failed",
        "backup_failed",
        "blocked",
        "rolling_back",
        "rolled_back",
        "rollback_failed",
    }

    return {
        "status": status,
        "label": _STATUS_LABELS.get(status, str(raw.get("message") or "等待部署状态")),
        "message": str(raw.get("message") or _STATUS_LABELS.get(status, "等待部署状态")),
        "service_version": service_version,
        "current_commit": current_commit or None,
        "target_commit": target_commit or None,
        "previous_commit": from_commit or None,
        "blocked_commit": blocked_commit or None,
        "is_current": is_current,
        "requires_attention": requires_attention,
        "updated_at_epoch_ms": updated_at_epoch_ms,
        "container_started_at_epoch_ms": _PROCESS_STARTED_AT_EPOCH_MS,
        "status_file_present": status_path.exists(),
        "environment": os.getenv("TIANJI_ENVIRONMENT", "production").strip() or "production",
    }
