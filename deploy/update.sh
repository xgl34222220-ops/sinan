#!/usr/bin/env bash
set -Eeuo pipefail

INSTALL_DIR="/opt/tianji"
REPO_URL="https://github.com/xgl34222220-ops/tianji.git"
DOMAIN="tianji-xgl.duckdns.org"
LOCK_FILE="/run/lock/tianji-update.lock"

log() { printf '\033[1;34m[天机]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[错误]\033[0m %s\n' "$*" >&2; exit 1; }

[[ ${EUID:-$(id -u)} -eq 0 ]] || fail "请使用 root 用户运行"
command -v git >/dev/null 2>&1 || fail "服务器没有安装 git"
command -v docker >/dev/null 2>&1 || fail "服务器没有安装 Docker"
command -v flock >/dev/null 2>&1 || fail "服务器没有安装 flock"

mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
flock -w 300 9 || fail "另一个更新任务仍在运行，请稍后重试"

if [[ -d "$INSTALL_DIR/.git" ]]; then
  log "更新天机代码"
  git -C "$INSTALL_DIR" fetch origin main
  git -C "$INSTALL_DIR" reset --hard origin/main
else
  log "获取天机代码"
  git clone --depth 1 --branch main "$REPO_URL" "$INSTALL_DIR"
fi

ENV_FILE="$INSTALL_DIR/.env"
[[ -f "$ENV_FILE" ]] || fail "未找到 $ENV_FILE，请先执行完整安装脚本"
DOMAIN="$(sed -n 's/^TIANJI_DOMAIN=//p' "$ENV_FILE" | tail -n1)"
DOMAIN="${DOMAIN:-tianji-xgl.duckdns.org}"

existing_password="$(sed -n 's/^TIANJI_ADMIN_PASSWORD=//p' "$ENV_FILE" | tail -n1)"
if [[ -z "$existing_password" ]]; then
  admin_password=""
  if [[ -r /dev/tty ]]; then
    read -r -s -p "请设置网页管理密码（至少8位，仅字母数字和 ._@!+=-；直接回车自动生成）: " admin_password </dev/tty || true
    printf '\n' >/dev/tty
  fi
  if [[ -z "$admin_password" ]]; then
    admin_password="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 20)"
    generated=1
  else
    generated=0
  fi
  [[ ${#admin_password} -ge 8 ]] || fail "管理密码至少需要 8 位"
  [[ "$admin_password" =~ ^[A-Za-z0-9._@!+=-]+$ ]] || fail "管理密码包含不支持的字符"
  printf '\nTIANJI_ADMIN_PASSWORD=%s\n' "$admin_password" >>"$ENV_FILE"
  chmod 600 "$ENV_FILE"
else
  generated=0
  admin_password=""
  log "已保留现有网页管理密码"
fi

log "更新前备份数据库"
chmod +x "$INSTALL_DIR/deploy/"*.sh
"$INSTALL_DIR/deploy/backup.sh" || log "当前没有可备份数据库，继续升级"

log "重建并启动服务"
cd "$INSTALL_DIR"
docker compose up -d --build --remove-orphans

log "等待控制台启动"
healthy=0
for _ in $(seq 1 45); do
  if curl -fsS --max-time 8 "https://$DOMAIN/health" >/tmp/tianji-health.json 2>/dev/null; then
    healthy=1
    break
  fi
  sleep 4
done

if [[ "$healthy" == 1 ]]; then
  log "升级成功"
  cat /tmp/tianji-health.json
  printf '\n\n公开页面：\033[1;32mhttps://%s\033[0m\n' "$DOMAIN"
  printf '管理面板：\033[1;32mhttps://%s/admin\033[0m\n' "$DOMAIN"
  if [[ "$generated" == 1 ]]; then
    printf '\n自动生成的管理密码：\033[1;33m%s\033[0m\n' "$admin_password"
    printf '请立即保存，登录后可在“安全”页面修改。\n'
  fi
  "$INSTALL_DIR/deploy/install-auto-update.sh"
else
  log "容器已启动，但健康检查尚未通过"
  docker compose ps
  docker compose logs --tail=100 api caddy || true
  exit 1
fi
