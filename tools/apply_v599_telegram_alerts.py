from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"marker not found in {path}: {old[:120]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "server/app/config.py",
    '''    fcm_project_id: str
    fcm_service_account_b64: str
    push_threshold: int
''',
    '''    fcm_project_id: str
    fcm_service_account_b64: str
    telegram_bot_token: str
    telegram_chat_ids: tuple[str, ...]
    push_threshold: int
''',
)
replace_once(
    "server/app/config.py",
    '''    @property
    def fcm_enabled(self) -> bool:
        return bool(self.fcm_project_id and self.fcm_service_account_b64)

    @property
    def data_dir(self) -> str:
''',
    '''    @property
    def fcm_enabled(self) -> bool:
        return bool(self.fcm_project_id and self.fcm_service_account_b64)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_ids)

    @property
    def data_dir(self) -> str:
''',
)
replace_once(
    "server/app/config.py",
    '''def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
''',
    '''def _list_env(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "").replace(";", ",").replace("\\n", ",")
    values: list[str] = []
    seen: set[str] = set()
    for item in raw.split(","):
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)
    return tuple(values)


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
''',
)
replace_once(
    "server/app/config.py",
    '''        fcm_project_id=os.getenv("TIANJI_FCM_PROJECT_ID", "").strip(),
        fcm_service_account_b64=os.getenv("TIANJI_FCM_SERVICE_ACCOUNT_B64", "").strip(),
        push_threshold=_int_env("TIANJI_PUSH_THRESHOLD", 3, 3, 10),
''',
    '''        fcm_project_id=os.getenv("TIANJI_FCM_PROJECT_ID", "").strip(),
        fcm_service_account_b64=os.getenv("TIANJI_FCM_SERVICE_ACCOUNT_B64", "").strip(),
        telegram_bot_token=os.getenv("TIANJI_TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_ids=_list_env("TIANJI_TELEGRAM_CHAT_IDS"),
        push_threshold=_int_env("TIANJI_PUSH_THRESHOLD", 3, 3, 10),
''',
)

replace_once(
    ".env.example",
    '''TIANJI_FCM_PROJECT_ID=
TIANJI_FCM_SERVICE_ACCOUNT_B64=
''',
    '''TIANJI_FCM_PROJECT_ID=
TIANJI_FCM_SERVICE_ACCOUNT_B64=

# Telegram is the preferred self-hosted alert channel. Create a bot with @BotFather,
# start the bot once, then add one or more private/group/channel chat IDs separated by commas.
TIANJI_TELEGRAM_BOT_TOKEN=
TIANJI_TELEGRAM_CHAT_IDS=
''',
)

replace_once(
    "server/app/push_alerts.py",
    '''from .models import LOTTERIES
''',
    '''from .models import LOTTERIES
from . import telegram_alerts
''',
)
replace_once(
    "server/app/push_alerts.py",
    '''    return {
        "created_alert_ids": inserted,
        "delivery": delivery,
        "push_configured": settings.fcm_enabled,
    }
''',
    '''    return {
        "created_alert_ids": inserted,
        "delivery": delivery,
        "push_configured": settings.fcm_enabled or settings.telegram_enabled,
        "channels": {
            "fcm": settings.fcm_enabled,
            "telegram": settings.telegram_enabled,
        },
    }
''',
)

push_file = Path("server/app/push_alerts.py")
push_text = push_file.read_text(encoding="utf-8")
marker = "def deliver_pending_alerts() -> dict[str, int]:\n"
if marker not in push_text:
    raise SystemExit("deliver_pending_alerts marker not found")
prefix = push_text.split(marker, 1)[0]
replacement = '''def _delivery_allowed(
    deliveries: dict[tuple[int, str], dict[str, Any]],
    *,
    alert_id: int,
    target_key: str,
    retry_before: int,
) -> bool:
    previous = deliveries.get((alert_id, target_key))
    if previous and previous["status"] == "sent":
        return False
    if previous and int(previous["attempted_at"]) > retry_before:
        return False
    return True


def _store_delivery(
    *,
    alert_id: int,
    target_key: str,
    ok: bool,
    code: int | None,
    message: str,
    attempted_at: int,
) -> None:
    with database.connection() as db:
        db.execute(
            """
            INSERT INTO push_deliveries(
                alert_id,installation_id,status,response_code,message,attempted_at
            ) VALUES(?,?,?,?,?,?)
            ON CONFLICT(alert_id,installation_id) DO UPDATE SET
                status=excluded.status,
                response_code=excluded.response_code,
                message=excluded.message,
                attempted_at=excluded.attempted_at
            """,
            (
                alert_id,
                target_key,
                "sent" if ok else "failed",
                code,
                message,
                attempted_at,
            ),
        )


def deliver_pending_alerts() -> dict[str, int]:
    initialize()
    if not settings.fcm_enabled and not settings.telegram_enabled:
        return {
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "fcm_sent": 0,
            "fcm_failed": 0,
            "telegram_sent": 0,
            "telegram_failed": 0,
        }

    now = _now_ms()
    retry_before = now - 300_000
    with database.connection() as db:
        alerts = db.execute(
            "SELECT * FROM push_alerts ORDER BY id DESC LIMIT 100"
        ).fetchall()
        devices = (
            db.execute(
                "SELECT * FROM push_devices WHERE fcm_token<>'' ORDER BY updated_at DESC"
            ).fetchall()
            if settings.fcm_enabled
            else []
        )
        deliveries = {
            (int(row["alert_id"]), str(row["installation_id"])): dict(row)
            for row in db.execute("SELECT * FROM push_deliveries").fetchall()
        }

    fcm_sent = fcm_failed = telegram_sent = telegram_failed = skipped = 0

    if settings.fcm_enabled:
        for alert in alerts:
            alert_id = int(alert["id"])
            for device in devices:
                if not _device_accepts(device, alert):
                    skipped += 1
                    continue
                target_key = str(device["installation_id"])
                if not _delivery_allowed(
                    deliveries,
                    alert_id=alert_id,
                    target_key=target_key,
                    retry_before=retry_before,
                ):
                    continue
                ok, code, message = _send_fcm(str(device["fcm_token"]), alert)
                _store_delivery(
                    alert_id=alert_id,
                    target_key=target_key,
                    ok=ok,
                    code=code,
                    message=message,
                    attempted_at=now,
                )
                if not ok and code in {400, 404} and (
                    "UNREGISTERED" in message
                    or "registration-token-not-registered" in message
                ):
                    with database.connection() as db:
                        db.execute(
                            "UPDATE push_devices SET fcm_token='',updated_at=? WHERE installation_id=?",
                            (now, target_key),
                        )
                if ok:
                    fcm_sent += 1
                else:
                    fcm_failed += 1

    if settings.telegram_enabled:
        for alert in alerts:
            alert_id = int(alert["id"])
            for chat_id in settings.telegram_chat_ids:
                target_key = telegram_alerts.delivery_key(chat_id)
                if not _delivery_allowed(
                    deliveries,
                    alert_id=alert_id,
                    target_key=target_key,
                    retry_before=retry_before,
                ):
                    continue
                ok, code, message = telegram_alerts.send_alert(
                    bot_token=settings.telegram_bot_token,
                    chat_id=chat_id,
                    alert=alert,
                )
                _store_delivery(
                    alert_id=alert_id,
                    target_key=target_key,
                    ok=ok,
                    code=code,
                    message=message,
                    attempted_at=now,
                )
                if ok:
                    telegram_sent += 1
                else:
                    telegram_failed += 1

    sent = fcm_sent + telegram_sent
    failed = fcm_failed + telegram_failed
    return {
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "fcm_sent": fcm_sent,
        "fcm_failed": fcm_failed,
        "telegram_sent": telegram_sent,
        "telegram_failed": telegram_failed,
    }
'''
push_file.write_text(prefix + replacement, encoding="utf-8")

print("v5.9.9 Telegram alert integration applied")
