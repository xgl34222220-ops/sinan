#!/usr/bin/env bash
set -Eeuo pipefail

REPO="${TIANJI_GITHUB_REPOSITORY:-xgl34222220-ops/tianji}"
PACKAGE_NAME="com.tianji.probabilitylab.nativev5"
CONFIG_FILE="${1:-}"

log() { printf '\033[1;34m[天机 FCM]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[错误]\033[0m %s\n' "$*" >&2; exit 1; }

[[ -n "$CONFIG_FILE" ]] || fail "用法：$0 /路径/google-services.json"
[[ -f "$CONFIG_FILE" ]] || fail "找不到配置文件：$CONFIG_FILE"
command -v python3 >/dev/null 2>&1 || fail "需要 python3"
command -v gh >/dev/null 2>&1 || fail "需要 GitHub CLI（gh）"
gh auth status >/dev/null 2>&1 || fail "请先执行 gh auth login"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

python3 - "$CONFIG_FILE" "$PACKAGE_NAME" "$tmp_dir" <<'PY'
from __future__ import annotations

import base64
import json
import pathlib
import sys

config_path = pathlib.Path(sys.argv[1])
package_name = sys.argv[2]
out_dir = pathlib.Path(sys.argv[3])
raw = config_path.read_bytes()
try:
    payload = json.loads(raw)
except json.JSONDecodeError as exc:
    raise SystemExit(f"google-services.json 格式无效：{exc}")

project = payload.get("project_info") or {}
project_id = str(project.get("project_id") or "").strip()
sender_id = str(project.get("project_number") or "").strip()
selected = None
for client in payload.get("client") or []:
    android = ((client.get("client_info") or {}).get("android_client_info") or {})
    if str(android.get("package_name") or "").strip() == package_name:
        selected = client
        break
if selected is None:
    raise SystemExit(f"配置文件中找不到 Android 包名 {package_name}")

client_info = selected.get("client_info") or {}
app_id = str(client_info.get("mobilesdk_app_id") or "").strip()
api_keys = selected.get("api_key") or []
api_key = str((api_keys[0] if api_keys else {}).get("current_key") or "").strip()
values = {
    "TIANJI_FIREBASE_PROJECT_ID": project_id,
    "TIANJI_FIREBASE_APP_ID": app_id,
    "TIANJI_FIREBASE_API_KEY": api_key,
    "TIANJI_FIREBASE_SENDER_ID": sender_id,
    "TIANJI_FIREBASE_GOOGLE_SERVICES_JSON_B64": base64.b64encode(raw).decode("ascii"),
}
missing = [name for name, value in values.items() if not value]
if missing:
    raise SystemExit("Firebase 配置缺少字段：" + ", ".join(missing))
for name, value in values.items():
    (out_dir / name).write_text(value, encoding="utf-8")
(out_dir / "PROJECT_ID.txt").write_text(project_id, encoding="utf-8")
PY

log "正在写入 GitHub Actions Secrets（不会写入仓库）"
for secret_name in \
    TIANJI_FIREBASE_GOOGLE_SERVICES_JSON_B64 \
    TIANJI_FIREBASE_PROJECT_ID \
    TIANJI_FIREBASE_APP_ID \
    TIANJI_FIREBASE_API_KEY \
    TIANJI_FIREBASE_SENDER_ID; do
    gh secret set "$secret_name" --repo "$REPO" <"$tmp_dir/$secret_name"
done

log "客户端配置完成"
printf '仓库：%s\nFirebase Project ID：%s\nAndroid 包名：%s\n' \
    "$REPO" "$(cat "$tmp_dir/PROJECT_ID.txt")" "$PACKAGE_NAME"
printf '下一步：在服务器运行 deploy/configure-fcm.sh 配置服务账号。\n'
