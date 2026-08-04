#!/usr/bin/env bash
set -Eeuo pipefail

INSTALL_DIR="/opt/tianji"
SERVICE_FILE="/etc/systemd/system/tianji-auto-update.service"
TIMER_FILE="/etc/systemd/system/tianji-auto-update.timer"
REFRESH_ONLY=0
[[ "${1:-}" == "--refresh" ]] && REFRESH_ONLY=1

[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "请使用 root 用户运行" >&2; exit 1; }
[[ -x "$INSTALL_DIR/deploy/auto-update.sh" ]] || chmod +x "$INSTALL_DIR/deploy/auto-update.sh"

cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=Tianji cloud safe automatic updater
Wants=network-online.target
After=network-online.target docker.service
ConditionPathExists=$INSTALL_DIR/.git
ConditionPathExists=$INSTALL_DIR/.env

[Service]
Type=oneshot
ExecStart=$INSTALL_DIR/deploy/auto-update.sh
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=6
TimeoutStartSec=20min
EOF

cat >"$TIMER_FILE" <<'EOF'
[Unit]
Description=Check Tianji cloud updates every five minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
RandomizedDelaySec=45s
AccuracySec=30s
Persistent=true
Unit=tianji-auto-update.service

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now tianji-auto-update.timer >/dev/null

if [[ "$REFRESH_ONLY" == 0 ]]; then
  printf '\033[1;34m[天机]\033[0m 自动更新已启用：每 5 分钟检查一次，失败会自动回滚。\n'
  printf '查看状态：systemctl status tianji-auto-update.timer --no-pager\n'
  printf '查看日志：journalctl -u tianji-auto-update.service -n 100 --no-pager\n'
fi
