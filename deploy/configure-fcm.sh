#!/usr/bin/env bash
set -Eeuo pipefail

INSTALL_DIR="${TIANJI_INSTALL_DIR:-/opt/tianji}"
SERVICE_ACCOUNT_FILE="${1:-}"
ENV_FILE="$INSTALL_DIR/.env"
DOMAIN="tianji-xgl.duckdns.org"

log() { printf '\033[1;34m[天机 FCM]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[错误]\033[0m %s\n' "$*" >&2; exit 1; }

[[ ${EUID:-$(id -u)} -eq 0 ]] || fail "请使用 root 用户运行"
[[ -n "$SERVICE_ACCOUNT_FILE" ]] || fail "用法：$0 /安全路径/firebase-service-account.json"
[[ -f "$SERVICE_ACCOUNT_FILE" ]] || fail "找不到服务账号文件：$SERVICE_ACCOUNT_FILE"
[[ -d "$INSTALL_DIR" ]] || fail "未找到天机安装目录：$INSTALL_DIR"
[[ -f "$ENV_FILE" ]] || fail "未找到环境文件：$ENV_FILE"
command -v python3 >/dev/null 2>&1 || fail "服务器需要 python3"
command -v docker >/dev/null 2>&1 || fail "服务器需要 Docker"

project_id="$(python3 - "$SERVICE_ACCOUNT_FILE" "$ENV_FILE" <<'PY'
from __future__ import annotations

import base64
import json
import pathlib
import sys

service_path = pathlib.Path(sys.argv[1])
env_path = pathlib.Path(sys.argv[2])
raw = service_path.read_bytes()
try:
    payload = json.loads(raw)
except json.JSONDecodeError as exc:
    raise SystemExit(f"服务账号 JSON 格式无效：{exc}")

required = ("project_id", "client_email", "private_key", "token_uri")
missing = [key for key in required if not str(payload.get(key) or "").strip()]
if payload.get("type") != "service_account":
    missing.append("type=service_account")
if missing:
    raise SystemExit("服务账号缺少字段：" + ", ".join(missing))

project_id = str(payload["project_id"]).strip()
encoded = base64.b64encode(raw).decode("ascii")
updates = {
    "TIANJI_FCM_PROJECT_ID": project_id,
    "TIANJI_FCM_SERVICE_ACCOUNT_B64": encoded,
}
lines = env_path.read_text(encoding="utf-8").splitlines()
seen: set[str] = set()
output: list[str] = []
for line in lines:
    if "=" in line and not line.lstrip().startswith("#"):
        key = line.split("=", 1)[0].strip()
        if key in updates:
            if key not in seen:
                output.append(f"{key}={updates[key]}")
                seen.add(key)
            continue
    output.append(line)
for key, value in updates.items():
    if key not in seen:
        output.append(f"{key}={value}")
env_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
print(project_id)
PY
)"

[[ -n "$project_id" ]] || fail "无法读取 Firebase Project ID"
chmod 600 "$ENV_FILE"
DOMAIN="$(sed -n 's/^TIANJI_DOMAIN=//p' "$ENV_FILE" | tail -n1)"
DOMAIN="${DOMAIN:-tianji-xgl.duckdns.org}"

log "已安全写入服务端环境变量，正在重建 API 与 Worker"
cd "$INSTALL_DIR"
docker compose up -d --build --force-recreate api worker

log "验证服务账号并获取短期 OAuth 令牌"
docker compose exec -T api python - <<'PY'
from app import push_alerts
from app.config import settings

assert settings.fcm_enabled, "FCM 环境变量未生效"
credentials = push_alerts._credentials()
assert credentials is not None and credentials.token, "服务账号无法获取 OAuth 令牌"
print(f"FCM 服务端已就绪：{settings.fcm_project_id}")
PY

log "等待服务恢复"
for _ in $(seq 1 30); do
    if curl -fsS --max-time 8 "https://$DOMAIN/health" >/tmp/tianji-fcm-health.json 2>/dev/null; then
        cat /tmp/tianji-fcm-health.json
        printf '\n'
        log "FCM 服务端配置完成（Project ID：$project_id）"
        printf '请删除服务器上的服务账号原始 JSON，仅保留 /opt/tianji/.env。\n'
        exit 0
    fi
    sleep 3
done

docker compose ps
fail "服务重启后健康检查未通过"
