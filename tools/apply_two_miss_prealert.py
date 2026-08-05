from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing expected block in {path}: {old[:120]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "server/app/admin_insights.py",
    "        recent = settled[:safe_threshold]\n",
    "        # 两期预警也需要保留三期上下文，便于第三期加强提醒展示完整期号。\n"
    "        recent = settled[:max(3, safe_threshold)]\n",
)

replace_once(
    "server/app/push_alerts.py",
    'CHANNEL_ID = "tianji_prediction_alerts"\n',
    'CHANNEL_ID = "tianji_prediction_alerts"\n'
    'PREALERT_THRESHOLD = 2\n'
    'STRONG_ALERT_THRESHOLD = 3\n',
)

replace_once(
    "server/app/push_alerts.py",
    '    threshold = int(watch.get("threshold") or settings.push_threshold)\n'
    '    now = _now_ms()\n',
    '    prealert_threshold = PREALERT_THRESHOLD\n'
    '    strong_threshold = max(STRONG_ALERT_THRESHOLD, int(settings.push_threshold))\n'
    '    now = _now_ms()\n',
)

replace_once(
    "server/app/push_alerts.py",
    '            if not lottery_key or not source or not model or streak < threshold or not latest_period:\n'
    '                continue\n'
    '            event_key = _event_key(lottery_key, source, model, streak, latest_period)\n'
    '            recent_periods = [\n'
    '                str(item.get("target_period") or "")\n'
    '                for item in recent[:threshold]\n'
    '                if str(item.get("target_period") or "")\n'
    '            ]\n'
    '            title = "三期不中预警" if streak == threshold else f"连续 {streak} 期不中升级预警"\n'
    '            body = f"{lottery_name} · {source_name} · {model} 已连续 {streak} 期 Top 6 未命中"\n'
    '            data = {\n',
    '            if (\n'
    '                not lottery_key\n'
    '                or not source\n'
    '                or not model\n'
    '                or streak < prealert_threshold\n'
    '                or not latest_period\n'
    '            ):\n'
    '                continue\n'
    '            event_key = _event_key(lottery_key, source, model, streak, latest_period)\n'
    '            recent_periods = [\n'
    '                str(item.get("target_period") or "")\n'
    '                for item in recent[:strong_threshold]\n'
    '                if str(item.get("target_period") or "")\n'
    '            ]\n'
    '            if streak == prealert_threshold:\n'
    '                title = "两期不中预警"\n'
    '                alert_level = "prealert"\n'
    '            elif streak == strong_threshold:\n'
    '                title = "三期不中加强提醒"\n'
    '                alert_level = "strong"\n'
    '            else:\n'
    '                title = f"连续 {streak} 期不中升级预警"\n'
    '                alert_level = "escalation"\n'
    '            body = f"{lottery_name} · {source_name} · {model} 已连续 {streak} 期 Top 6 未命中"\n'
    '            data = {\n',
)

replace_once(
    "server/app/push_alerts.py",
    '                "threshold": str(threshold),\n'
    '                "latest_target_period": latest_period,\n',
    '                "threshold": str(strong_threshold),\n'
    '                "prealert_threshold": str(prealert_threshold),\n'
    '                "alert_level": alert_level,\n'
    '                "latest_target_period": latest_period,\n',
)

replace_once(
    "server/app/push_alerts.py",
    '                        streak,\n'
    '                        threshold,\n'
    '                        latest_period,\n',
    '                        streak,\n'
    '                        strong_threshold,\n'
    '                        latest_period,\n',
)

replace_once(
    "server/app/push_alerts.py",
    '    watch = prediction_miss_watch(threshold=settings.push_threshold)\n',
    '    watch = prediction_miss_watch(threshold=PREALERT_THRESHOLD)\n',
)

replace_once(
    "server/app/telegram_alerts.py",
    '    if streak == threshold:\n'
    '        heading = "🚨🚨 <b>连续三期不中 · 加强提醒</b>"\n'
    '        notice = "已达到加强提醒条件，请重点关注下一期预测；后续每期预测仍会正常推送。"\n'
    '    else:\n'
    '        heading = f"🔴🔴 <b>连续 {streak} 期不中 · 升级提醒</b>"\n'
    '        notice = "连续未中仍在扩大，当前处于升级提醒状态；后续每期预测仍会正常推送。"\n',
    '    if streak == 2:\n'
    '        heading = "⚠️ <b>连续两期不中 · 提前预警</b>"\n'
    '        notice = "已连续两期 Top 6 未中，请留意下一期；每期云端 AI 预测仍会正常推送。"\n'
    '    elif streak == threshold:\n'
    '        heading = "🚨🚨 <b>连续三期不中 · 加强提醒</b>"\n'
    '        notice = "已达到加强提醒条件，请重点关注下一期预测；后续每期预测仍会正常推送。"\n'
    '    else:\n'
    '        heading = f"🔴🔴 <b>连续 {streak} 期不中 · 升级提醒</b>"\n'
    '        notice = "连续未中仍在扩大，当前处于升级提醒状态；后续每期预测仍会正常推送。"\n',
)

replace_once(
    "server/app/telegram_alerts.py",
    '            "命中后连续未中计数清零；下一次重新连续三期不中时再次加强提醒。",\n',
    '            "命中后连续未中计数清零；下一次两期不中先预警，三期不中再加强提醒。",\n',
)

replace_once(
    "server/tests/test_push_alerts.py",
    '    def test_warning_is_idempotent_and_escalation_is_separate(self) -> None:\n'
    '        first = materialize_warning_alerts(self.watch())\n'
    '        duplicate = materialize_warning_alerts(self.watch())\n'
    '        escalation = materialize_warning_alerts(self.watch(streak=4, latest="104"))\n'
    '        self.assertEqual(1, len(first))\n'
    '        self.assertEqual([], duplicate)\n'
    '        self.assertEqual(1, len(escalation))\n'
    '        with database.connection() as db:\n'
    '            count = int(db.execute("SELECT COUNT(*) FROM push_alerts").fetchone()[0])\n'
    '        self.assertEqual(2, count)\n',
    '    def test_two_miss_prealert_strong_alert_and_escalation_are_separate(self) -> None:\n'
    '        prealert = materialize_warning_alerts(self.watch(streak=2, latest="102"))\n'
    '        duplicate = materialize_warning_alerts(self.watch(streak=2, latest="102"))\n'
    '        strong = materialize_warning_alerts(self.watch(streak=3, latest="103"))\n'
    '        escalation = materialize_warning_alerts(self.watch(streak=4, latest="104"))\n'
    '        self.assertEqual(1, len(prealert))\n'
    '        self.assertEqual([], duplicate)\n'
    '        self.assertEqual(1, len(strong))\n'
    '        self.assertEqual(1, len(escalation))\n'
    '        with database.connection() as db:\n'
    '            rows = db.execute(\n'
    '                "SELECT streak,threshold,title FROM push_alerts ORDER BY streak"\n'
    '            ).fetchall()\n'
    '        self.assertEqual(\n'
    '            [\n'
    '                (2, 3, "两期不中预警"),\n'
    '                (3, 3, "三期不中加强提醒"),\n'
    '                (4, 3, "连续 4 期不中升级预警"),\n'
    '            ],\n'
    '            [\n'
    '                (int(row["streak"]), int(row["threshold"]), str(row["title"]))\n'
    '                for row in rows\n'
    '            ],\n'
    '        )\n',
)

replace_once(
    "server/tests/test_telegram_alerts.py",
    '    def test_message_escapes_html_and_contains_periods(self) -> None:\n'
    '        alert_id = push_alerts.materialize_warning_alerts(self.watch())[0]\n'
    '        with database.connection() as db:\n'
    '            alert = db.execute(\n'
    '                "SELECT * FROM push_alerts WHERE id=?",\n'
    '                (alert_id,),\n'
    '            ).fetchone()\n'
    '        message = telegram_alerts.format_alert_message(alert)\n'
    '        self.assertIn("deepseek&lt;pro&gt;", message)\n'
    '        self.assertIn("103、102、101", message)\n'
    '        self.assertIn("连续未中：</b>3 期", message)\n',
    '    def alert_message(self, streak: int, latest: str) -> str:\n'
    '        alert_id = push_alerts.materialize_warning_alerts(\n'
    '            self.watch(streak=streak, latest=latest)\n'
    '        )[0]\n'
    '        with database.connection() as db:\n'
    '            alert = db.execute(\n'
    '                "SELECT * FROM push_alerts WHERE id=?",\n'
    '                (alert_id,),\n'
    '            ).fetchone()\n'
    '        return telegram_alerts.format_alert_message(alert)\n'
    '\n'
    '    def test_two_three_and_four_miss_alert_levels(self) -> None:\n'
    '        two = self.alert_message(2, "102")\n'
    '        three = self.alert_message(3, "103")\n'
    '        four = self.alert_message(4, "104")\n'
    '        self.assertIn("连续两期不中 · 提前预警", two)\n'
    '        self.assertIn("连续三期不中 · 加强提醒", three)\n'
    '        self.assertIn("连续 4 期不中 · 升级提醒", four)\n'
    '        self.assertIn("deepseek&lt;pro&gt;", three)\n'
    '        self.assertIn("103、102、101", three)\n'
    '        self.assertIn("连续未中：</b><b>3 期", three)\n',
)

replace_once(
    "server/tests/test_telegram_alerts.py",
    '    def watch(source: str = "ai") -> dict:\n',
    '    def watch(\n'
    '        source: str = "ai",\n'
    '        *,\n'
    '        streak: int = 3,\n'
    '        latest: str = "103",\n'
    '    ) -> dict:\n',
)

replace_once(
    "server/tests/test_telegram_alerts.py",
    '                            "current_miss_streak": 3,\n'
    '                            "recent_three": [\n'
    '                                {"target_period": "103"},\n'
    '                                {"target_period": "102"},\n'
    '                                {"target_period": "101"},\n'
    '                            ],\n',
    '                            "current_miss_streak": streak,\n'
    '                            "recent_three": [\n'
    '                                {"target_period": latest},\n'
    '                                {"target_period": str(int(latest) - 1)},\n'
    '                                {"target_period": str(int(latest) - 2)},\n'
    '                            ],\n',
)

print("two-miss prealert patch applied")
