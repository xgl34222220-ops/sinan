#!/usr/bin/env bash
set -Eeuo pipefail

INSTALL_DIR="/opt/tianji"
LOCK_FILE="/run/lock/tianji-update.lock"
STATUS_FILE="$INSTALL_DIR/data/auto-update-status.json"
BLOCKED_FILE="$INSTALL_DIR/data/auto-update-blocked-commit"
ENV_FILE="$INSTALL_DIR/.env"

log() { printf '[天机自动更新] %s\n' "$*"; }

write_status() {
  local status="$1" message="$2" from_commit="${3:-}" to_commit="${4:-}"
  local temp_file="${STATUS_FILE}.tmp"
  mkdir -p "$(dirname "$STATUS_FILE")"
  printf '{"status":"%s","message":"%s","from_commit":"%s","to_commit":"%s","updated_at_epoch_ms":%s}\n' \
    "$status" "$message" "$from_commit" "$to_commit" "$(date +%s%3N)" >"$temp_file"
  chmod 644 "$temp_file"
  mv -f "$temp_file" "$STATUS_FILE"
}

[[ ${EUID:-$(id -u)} -eq 0 ]] || exit 0
[[ -d "$INSTALL_DIR/.git" && -f "$ENV_FILE" ]] || exit 0
command -v git >/dev/null 2>&1 || exit 0
command -v docker >/dev/null 2>&1 || exit 0
command -v flock >/dev/null 2>&1 || exit 0

mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
flock -n 9 || exit 0

cd "$INSTALL_DIR"
old_commit="$(git rev-parse HEAD)"
if ! git fetch --quiet origin main; then
  write_status "check_failed" "无法连接 GitHub，保留当前版本" "$old_commit" ""
  exit 0
fi
new_commit="$(git rev-parse origin/main)"

if [[ "$old_commit" == "$new_commit" ]]; then
  write_status "up_to_date" "当前已经是最新版本" "$old_commit" "$new_commit"
  exit 0
fi

blocked_commit="$(cat "$BLOCKED_FILE" 2>/dev/null || true)"
if [[ -n "$blocked_commit" && "$blocked_commit" == "$new_commit" ]]; then
  write_status "blocked" "该版本曾部署失败，等待后续新版本后再重试" "$old_commit" "$new_commit"
  exit 0
fi

changed_files="$(git diff --name-only "$old_commit..$new_commit")"
runtime_changed=0
if grep -Eq '^(server/|docker-compose\.yml$|Caddyfile$|\.env\.example$)' <<<"$changed_files"; then
  runtime_changed=1
fi

log "发现新版本 ${old_commit:0:8} -> ${new_commit:0:8}"
write_status "updating" "正在拉取并验证新版本" "$old_commit" "$new_commit"

backup_file=""
if [[ "$runtime_changed" == 1 && -x "$INSTALL_DIR/deploy/backup.sh" ]]; then
  if ! "$INSTALL_DIR/deploy/backup.sh"; then
    write_status "backup_failed" "数据库备份失败，本次更新已取消" "$old_commit" "$new_commit"
    log "数据库备份失败，保留当前版本"
    exit 0
  fi
  backup_file="$(find "$INSTALL_DIR/backups" -maxdepth 1 -type f -name 'tianji-*.db.gz' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2- || true)"
fi

git reset --hard "$new_commit" >/dev/null
chmod +x "$INSTALL_DIR/deploy/"*.sh

if [[ -x "$INSTALL_DIR/deploy/install-auto-update.sh" ]]; then
  "$INSTALL_DIR/deploy/install-auto-update.sh" --refresh >/dev/null
fi

if [[ "$runtime_changed" == 0 ]]; then
  rm -f "$BLOCKED_FILE"
  write_status "source_synced" "仅 App 或文档发生变化，云端无需重启" "$old_commit" "$new_commit"
  log "仅同步仓库文件，云端服务无需重建"
  exit 0
fi

if docker compose up -d --build --remove-orphans; then
  domain="$(sed -n 's/^TIANJI_DOMAIN=//p' "$ENV_FILE" | tail -n1)"
  domain="${domain:-tianji-xgl.duckdns.org}"
  healthy=0
  for _ in $(seq 1 45); do
    if docker compose exec -T api python -c \
      "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" \
      >/dev/null 2>&1 \
      && curl -fsS --max-time 8 "https://$domain/health" >/dev/null 2>&1; then
      healthy=1
      break
    fi
    sleep 4
  done
else
  healthy=0
fi

if [[ "$healthy" == 1 ]]; then
  rm -f "$BLOCKED_FILE"
  write_status "updated" "新版本已自动部署并通过健康检查" "$old_commit" "$new_commit"
  log "自动更新成功"
  exit 0
fi

log "新版本健康检查失败，开始自动回滚"
write_status "rolling_back" "新版本健康检查失败，正在恢复旧版本" "$old_commit" "$new_commit"
printf '%s\n' "$new_commit" >"$BLOCKED_FILE"

git reset --hard "$old_commit" >/dev/null

if [[ -n "$backup_file" && -f "$backup_file" ]]; then
  docker compose stop api worker >/dev/null 2>&1 || true
  gzip -dc "$backup_file" >"$INSTALL_DIR/data/tianji.db.rollback"
  mv -f "$INSTALL_DIR/data/tianji.db.rollback" "$INSTALL_DIR/data/tianji.db"
  rm -f "$INSTALL_DIR/data/tianji.db-wal" "$INSTALL_DIR/data/tianji.db-shm"
  chown 10001:10001 "$INSTALL_DIR/data/tianji.db"
fi

docker compose up -d --build --remove-orphans >/dev/null 2>&1 || true
rollback_ok=0
for _ in $(seq 1 30); do
  if docker compose exec -T api python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" \
    >/dev/null 2>&1; then
    rollback_ok=1
    break
  fi
  sleep 4
done

if [[ "$rollback_ok" == 1 ]]; then
  write_status "rolled_back" "新版本部署失败，已恢复到旧版本" "$old_commit" "$new_commit"
  log "已回滚到 ${old_commit:0:8}"
else
  write_status "rollback_failed" "新版本失败且旧版本未恢复，请检查服务日志" "$old_commit" "$new_commit"
  log "自动回滚后健康检查仍失败"
fi
exit 0
