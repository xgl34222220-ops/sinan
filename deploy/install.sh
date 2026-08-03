#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/xgl34222220-ops/tianji.git"
INSTALL_DIR="/opt/tianji"
DEFAULT_DOMAIN="tianji-xgl.duckdns.org"

log() { printf '\033[1;34m[天机]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[错误]\033[0m %s\n' "$*" >&2; exit 1; }

[[ ${EUID:-$(id -u)} -eq 0 ]] || fail "请使用 root 用户运行安装命令"

read_tty() {
  local prompt="$1" default_value="${2:-}" value=""
  if [[ -r /dev/tty ]]; then
    if [[ -n "$default_value" ]]; then
      read -r -p "$prompt [$default_value]: " value </dev/tty || true
      printf '%s' "${value:-$default_value}"
    else
      read -r -p "$prompt: " value </dev/tty || true
      printf '%s' "$value"
    fi
  else
    printf '%s' "$default_value"
  fi
}

read_secret_tty() {
  local prompt="$1" value=""
  if [[ -r /dev/tty ]]; then
    read -r -s -p "$prompt（输入时不显示，直接回车保留原值或暂不配置）: " value </dev/tty || true
    printf '\n' >/dev/tty
  fi
  printf '%s' "$value"
}

env_value() {
  local key="$1" fallback="${2:-}"
  if [[ -f "$INSTALL_DIR/.env" ]]; then
    local value
    value="$(grep -m1 -E "^${key}=" "$INSTALL_DIR/.env" 2>/dev/null | cut -d= -f2- || true)"
    printf '%s' "${value:-$fallback}"
  else
    printf '%s' "$fallback"
  fi
}

log "安装基础工具"
apt-get update
apt-get install -y ca-certificates curl gnupg git openssl

install_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "Docker 与 Compose 已安装"
    systemctl enable --now docker
    return
  fi

  log "安装 Docker Engine 与 Compose"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  cat >/etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: ${VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
}

install_docker

log "获取天机项目"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  git -C "$INSTALL_DIR" fetch origin main
  git -C "$INSTALL_DIR" reset --hard origin/main
else
  rm -rf "$INSTALL_DIR"
  git clone --depth 1 --branch main "$REPO_URL" "$INSTALL_DIR"
fi
mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/backups"
# The API/worker images run as uid/gid 10001 so the bind-mounted database stays writable.
chown -R 10001:10001 "$INSTALL_DIR/data"

OLD_DOMAIN="$(env_value TIANJI_DOMAIN "$DEFAULT_DOMAIN")"
OLD_ENDPOINT="$(env_value TIANJI_AI_ENDPOINT 'https://api.deepseek.com/chat/completions')"
OLD_MODEL="$(env_value TIANJI_AI_MODEL 'deepseek-chat')"
OLD_KEY="$(env_value TIANJI_AI_API_KEY '')"
OLD_TOKEN="$(env_value TIANJI_API_TOKEN '')"

DOMAIN="$(read_tty '请输入 DuckDNS 域名' "$OLD_DOMAIN")"
[[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]] || fail "域名格式不正确"

AI_ENDPOINT="$(read_tty 'AI 接口地址' "$OLD_ENDPOINT")"
AI_MODEL="$(read_tty 'AI 模型名' "$OLD_MODEL")"
NEW_AI_KEY="$(read_secret_tty '请输入 AI API Key')"
AI_KEY="${NEW_AI_KEY:-$OLD_KEY}"
API_TOKEN="${OLD_TOKEN:-$(openssl rand -hex 32)}"

umask 077
cat >"$INSTALL_DIR/.env" <<EOF
TIANJI_DOMAIN=$DOMAIN
TIANJI_PUBLIC_BASE_URL=https://$DOMAIN
TIANJI_DATABASE=/app/data/tianji.db
TIANJI_API_TOKEN=$API_TOKEN
TIANJI_POLL_SECONDS=30
TIANJI_HISTORY_DAYS=14
TIANJI_AI_ENDPOINT=$AI_ENDPOINT
TIANJI_AI_MODEL=$AI_MODEL
TIANJI_AI_API_KEY=$AI_KEY
TIANJI_AI_TIMEOUT_SECONDS=120
EOF
chmod 600 "$INSTALL_DIR/.env"

log "构建并启动天机云端服务"
cd "$INSTALL_DIR"
docker compose up -d --build --remove-orphans

log "安装每日数据库备份任务"
chmod +x "$INSTALL_DIR/deploy/backup.sh"
cat >/etc/cron.d/tianji-backup <<EOF
17 4 * * * root $INSTALL_DIR/deploy/backup.sh >/var/log/tianji-backup.log 2>&1
EOF
chmod 644 /etc/cron.d/tianji-backup

log "等待 HTTPS 与后台服务启动"
healthy=0
for _ in $(seq 1 45); do
  if curl -fsS --max-time 8 "https://$DOMAIN/health" >/tmp/tianji-health.json 2>/dev/null; then
    healthy=1
    break
  fi
  sleep 4
done

printf '\n'
if [[ "$healthy" == 1 ]]; then
  log "部署成功"
  cat /tmp/tianji-health.json
  printf '\n\n访问地址：\033[1;32mhttps://%s\033[0m\n' "$DOMAIN"
else
  log "容器已经启动，但 HTTPS 暂未就绪。请确认 DuckDNS 指向本机、80/443 端口已开放。"
  docker compose ps
  docker compose logs --tail=80 caddy || true
fi

printf '\n管理令牌已保存在 %s/.env，不会显示在聊天或网页中。\n' "$INSTALL_DIR"
printf '查看日志：cd %s && docker compose logs -f\n' "$INSTALL_DIR"
