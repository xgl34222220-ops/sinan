from __future__ import annotations

from pathlib import Path


path = Path("server/app/telegram_events.py")
text = path.read_text(encoding="utf-8")
old = '''def deliver_pending_events() -> dict[str, int]:
    initialize()
    if not settings.telegram_enabled:
        return {"sent": 0, "failed": 0, "skipped": 0}
    with database.connection() as db:
        events = db.execute(
            "SELECT * FROM telegram_events ORDER BY created_at ASC LIMIT 500"
        ).fetchall()

    sent = failed = skipped = 0
    for event in events:
        event_key = str(event["event_key"])
        for chat_id in settings.telegram_chat_ids:
            target_key = telegram_alerts.delivery_key(chat_id)
            now = _now_ms()
            if not _claim_delivery(event_key, target_key, now):
                skipped += 1
                continue
            ok, code, message = telegram_alerts.send_html_message(
                bot_token=settings.telegram_bot_token,
                chat_id=chat_id,
                text=str(event["message_html"]),
            )
            _finish_delivery(
                event_key,
                target_key,
                ok=ok,
                code=code,
                message=message,
                attempted_at=now,
            )
            if ok:
                sent += 1
            else:
                failed += 1
    return {"sent": sent, "failed": failed, "skipped": skipped}
'''
new = '''def deliver_pending_events() -> dict[str, int]:
    initialize()
    if not settings.telegram_enabled:
        return {"sent": 0, "failed": 0, "skipped": 0}

    sent = failed = skipped = 0
    for chat_id in settings.telegram_chat_ids:
        target_key = telegram_alerts.delivery_key(chat_id)
        with database.connection() as db:
            events = db.execute(
                """
                SELECT event.*
                FROM telegram_events AS event
                LEFT JOIN telegram_event_deliveries AS delivery
                  ON delivery.event_key=event.event_key
                 AND delivery.target_key=?
                WHERE delivery.status IS NULL OR delivery.status<>'sent'
                ORDER BY event.created_at ASC
                LIMIT 500
                """,
                (target_key,),
            ).fetchall()

        for event in events:
            event_key = str(event["event_key"])
            now = _now_ms()
            if not _claim_delivery(event_key, target_key, now):
                skipped += 1
                continue
            ok, code, message = telegram_alerts.send_html_message(
                bot_token=settings.telegram_bot_token,
                chat_id=chat_id,
                text=str(event["message_html"]),
            )
            _finish_delivery(
                event_key,
                target_key,
                ok=ok,
                code=code,
                message=message,
                attempted_at=now,
            )
            if ok:
                sent += 1
            else:
                failed += 1
    return {"sent": sent, "failed": failed, "skipped": skipped}
'''
if new in text:
    raise SystemExit(0)
if old not in text:
    raise SystemExit("Telegram delivery queue marker not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Telegram event queue fixed")
