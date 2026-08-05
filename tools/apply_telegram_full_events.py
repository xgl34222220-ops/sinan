from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"marker not found in {path}: {old[:160]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "server/app/telegram_alerts.py",
    "\ndef send_alert(\n",
    '''\ndef send_html_message(
    *,
    bot_token: str,
    chat_id: str,
    text: str,
    timeout_seconds: int = 12,
    disable_notification: bool = False,
) -> tuple[bool, int | None, str]:
    token = bot_token.strip()
    target = chat_id.strip()
    if not token or not target:
        return False, None, "Telegram 配置不完整"

    url = f"{_TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": target,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "disable_notification": disable_notification,
    }
    try:
        response = requests.post(url, json=payload, timeout=timeout_seconds)
        message = response.text[:800]
        return response.ok, int(response.status_code), message
    except requests.RequestException as exc:
        return False, None, str(exc)[:800]


def send_alert(
''',
)

replace_once(
    "server/app/service.py",
    "from . import ai, push_alerts\n",
    "from . import ai, push_alerts, telegram_events\n",
)
replace_once(
    "server/app/service.py",
    '''    if spec is None:
        raise KeyError(f"未知彩种：{lottery_key}")

    existing_count = len(database.list_draws(lottery_key, 180))
''',
    '''    if spec is None:
        raise KeyError(f"未知彩种：{lottery_key}")

    telegram_events.initialize()
    existing_count = len(database.list_draws(lottery_key, 180))
''',
)
replace_once(
    "server/app/service.py",
    '''        final_status = "completed" if inserted is not None else "duplicate"
''',
    '''        if inserted is not None:
            try:
                telegram_events.process(spec.key)
                database.delete_state(f"telegram_event_error:{spec.key}")
            except Exception as notify_exc:
                _state(
                    f"telegram_event_error:{spec.key}",
                    {"message": str(notify_exc)[:500], "at": int(time.time() * 1000)},
                )
        final_status = "completed" if inserted is not None else "duplicate"
''',
)
replace_once(
    "server/app/service.py",
    '''    settled = database.settle_forecasts(lottery_key)
    try:
        push_result = push_alerts.process_prediction_alerts(lottery_key)
''',
    '''    settled = database.settle_forecasts(lottery_key)
    try:
        telegram_result = telegram_events.process(lottery_key)
        database.delete_state(f"telegram_event_error:{lottery_key}")
    except Exception as exc:
        telegram_result = {
            "created": 0,
            "delivery": {"sent": 0, "failed": 0, "skipped": 0},
            "error": str(exc)[:500],
        }
        _state(
            f"telegram_event_error:{lottery_key}",
            {"message": str(exc)[:500], "at": int(time.time() * 1000)},
        )
    try:
        push_result = push_alerts.process_prediction_alerts(lottery_key)
''',
)
replace_once(
    "server/app/service.py",
    '''        "push": push_result,
        "generated": generated,
''',
    '''        "push": push_result,
        "telegram": telegram_result,
        "generated": generated,
''',
)
replace_once(
    "server/app/service.py",
    '''                if inserted is not None:
                    generated.append("native")
''',
    '''                if inserted is not None:
                    generated.append("native")
                    try:
                        telegram_result = telegram_events.process(lottery_key)
                        database.delete_state(f"telegram_event_error:{lottery_key}")
                    except Exception as notify_exc:
                        errors["telegram"] = str(notify_exc)[:500]
                        _state(
                            f"telegram_event_error:{lottery_key}",
                            {
                                "message": errors["telegram"],
                                "at": int(time.time() * 1000),
                            },
                        )
''',
)
replace_once(
    "server/app/service.py",
    '''            "generated": generated,
            "scheduled": scheduled,
            "errors": errors,
''',
    '''            "telegram": telegram_result,
            "generated": generated,
            "scheduled": scheduled,
            "errors": errors,
''',
)

print("Telegram prediction and win event integration applied")
