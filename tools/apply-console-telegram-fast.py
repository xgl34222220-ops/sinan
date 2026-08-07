from __future__ import annotations

from pathlib import Path
import re


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


# 1) Remove the huge miss-watch dashboard and internal maintenance timeline from the UI.
path = "server/app/console_v594.js"
text = read(path)
marker = "workspace.id='v597MissWatchWorkspace';"
require(marker in text, "miss-watch workspace marker not found")
marker_at = text.index(marker)
start = text.rfind("\n(()=>{", 0, marker_at)
end_marker = "\n})();"
end = text.find(end_marker, marker_at)
require(start >= 0 and end >= 0, "miss-watch IIFE boundary not found")
text = text[:start] + text[end + len(end_marker):]
require("v597MissWatchWorkspace" not in text, "miss-watch workspace still present")
require("双彩种三期不中预警" not in text, "miss-watch title still present")

ops_pattern = re.compile(
    r"\n    const ops=document\.createElement\('section'\);ops\.className='section';ops\.id='opsWorkspace';.*?q\('#v3RefreshOps'\)\?\.addEventListener\('click',loadOperations\);",
    re.S,
)
text, count = ops_pattern.subn(
    "\n    // Internal deployment/database timeline stays available through the API, but is intentionally hidden from the daily console.",
    text,
    count=1,
)
require(count == 1, "ops workspace creation block not found")
old_load = "loadRecords();loadInsights();loadDraws();loadOperations();setInterval(()=>{loadDraws();loadOperations()},30000);"
new_load = "loadRecords();loadInsights();loadDraws();setInterval(loadDraws,30000);"
require(old_load in text, "overview polling call not found")
text = text.replace(old_load, new_load, 1)
old_overview = "  if(overview){\n    const draw=document.createElement('section');"
new_overview = "  if(overview){\n    q('#diagnostics')?.closest('.card')?.remove();\n    const draw=document.createElement('section');"
require(old_overview in text, "overview block not found")
text = text.replace(old_overview, new_overview, 1)
write(path, text)


# 2) Replace developer-facing stage rows with four readable health cards.
path = "server/app/console_v3.py"
text = read(path)
text = text.replace("grid-template-columns:repeat(5,minmax(0,1fr))", "grid-template-columns:repeat(4,minmax(0,1fr))", 1)
style_anchor = ".v510-platform-card strong{display:block;margin-top:6px;font-size:15px;overflow-wrap:anywhere}"
require(style_anchor in text, "platform card style anchor not found")
text = text.replace(
    style_anchor,
    style_anchor + ".v510-platform-card small{display:block;margin-top:4px;color:var(--muted);font-size:9px;line-height:1.45}",
    1,
)

function_pattern = re.compile(
    r"  async function loadPlatform\(\)\{.*?\n  \}\n  loadPlatform\(\);",
    re.S,
)
replacement = r'''  async function loadPlatform(){
    const overview=document.getElementById('panel-overview');
    if(!overview)return;
    try{
      const response=await fetch('/health/detail',{cache:'no-store'});
      if(!response.ok)return;
      const data=await response.json();
      lastPlatformSuccess=Date.now();
      let section=document.getElementById('v510Platform');
      if(!section){section=document.createElement('section');section.id='v510Platform';section.className='section v510-platform';overview.appendChild(section)}
      const aiHealth=data.ai_health||{};
      const delivery=data.delivery_health||{};
      const fcm=(delivery.channels||{}).fcm||{};
      const telegram=(delivery.channels||{}).telegram||{};
      const workerState=String(data.worker?.status||'waiting').toLowerCase();
      const workerOk=['ok','running','healthy'].includes(workerState);
      const healthy=data.status==='ok'&&data.database?.ok!==false&&workerOk;
      section.innerHTML=`
        <div class="v3-head"><div><h3>服务状态</h3><p>只显示日常需要看的运行、AI 和推送状态；内部任务名、数据库细节与毫秒耗时已隐藏。</p></div><span class="badge ${healthy?'good':'warn'}">${healthy?'运行正常':'需要检查'}</span></div>
        <div class="v510-platform-grid">
          <article class="v510-platform-card"><span>云端服务</span><strong class="${workerOk?'good':'warn'}">${workerOk?'运行正常':'等待恢复'}</strong><small>Worker 心跳 ${age(data.worker?.updated_at_epoch_ms)}</small></article>
          <article class="v510-platform-card"><span>AI 任务</span><strong class="${Number(aiHealth.failed||0)?'warn':'good'}">${Number(aiHealth.running||0)} 运行 · ${Number(aiHealth.failed||0)} 失败</strong><small>${Number(aiHealth.failed||0)?'有失败任务需要留意':'当前调度正常'}</small></article>
          <article class="v510-platform-card"><span>App 预警</span><strong class="${Number(fcm.failed||0)?'warn':'good'}">${Number(fcm.sent||0)} 成功 · ${Number(fcm.failed||0)} 失败</strong><small>最近 24 小时 FCM 预警</small></article>
          <article class="v510-platform-card"><span>Telegram</span><strong class="${Number(telegram.failed||0)?'warn':'good'}">${Number(telegram.sent||0)} 成功 · ${Number(telegram.failed||0)} 失败</strong><small>最近 24 小时 · 预警优先发送</small></article>
        </div>`;
    }catch(_error){
      let section=document.getElementById('v510Platform');
      if(!section){
        const overview=document.getElementById('panel-overview');
        if(!overview)return;
        section=document.createElement('section');section.id='v510Platform';section.className='section v510-platform';overview.appendChild(section);
      }
      section.innerHTML=`<div class="v510-deploy attention"><div class="v510-deploy-main"><div class="v510-deploy-title"><i class="v510-deploy-dot"></i>服务状态刷新失败</div><div class="v510-deploy-message">暂时读取不到最新状态，请检查网络后刷新；后台预警与预测任务不会因为这个页面失败而停止。</div></div><div class="v510-deploy-meta"><span>最后成功刷新</span><strong>${lastPlatformSuccess?new Date(lastPlatformSuccess).toLocaleTimeString('zh-CN',{hour12:false}):'尚未成功'}</strong></div></div>`;
    }
  }
  loadPlatform();'''
text, count = function_pattern.subn(replacement, text, count=1)
require(count == 1, "loadPlatform function not found")
require("平台健康、部署与任务阶段" not in text, "old platform heading still present")
write(path, text)


# 3) Prioritize real miss alerts immediately after settlement, before routine Telegram events.
path = "server/app/service.py"
text = read(path)
old = '''    try:\n        with _record_stage(stages, "deliver_telegram"):\n            telegram_result = telegram_events.process(lottery_key)\n            database.delete_state(f"telegram_event_error:{lottery_key}")\n    except Exception as exc:\n        telegram_result = {\n            "created": 0,\n            "delivery": {"sent": 0, "failed": 0, "skipped": 0},\n            "error": str(exc)[:500],\n        }\n        _state(\n            f"telegram_event_error:{lottery_key}",\n            {"message": str(exc)[:500], "at": int(time.time() * 1000)},\n        )\n\n    try:\n        with _record_stage(stages, "deliver_push"):\n            push_result = push_alerts.process_prediction_alerts(lottery_key)\n            database.delete_state(f"push_error:{lottery_key}")\n    except Exception as exc:\n        push_result = {\n            "created_alert_ids": [],\n            "delivery": {"sent": 0, "failed": 0, "skipped": 0},\n            "error": str(exc)[:500],\n        }\n        _state(\n            f"push_error:{lottery_key}",\n            {"message": str(exc)[:500], "at": int(time.time() * 1000)},\n        )\n'''
new = '''    # Warning delivery is latency-sensitive: settle -> alert first -> routine Telegram queue.\n    # This keeps two/three-miss alerts from waiting behind ordinary prediction messages.\n    try:\n        with _record_stage(stages, "deliver_push"):\n            push_result = push_alerts.process_prediction_alerts(lottery_key)\n            database.delete_state(f"push_error:{lottery_key}")\n    except Exception as exc:\n        push_result = {\n            "created_alert_ids": [],\n            "delivery": {"sent": 0, "failed": 0, "skipped": 0},\n            "error": str(exc)[:500],\n        }\n        _state(\n            f"push_error:{lottery_key}",\n            {"message": str(exc)[:500], "at": int(time.time() * 1000)},\n        )\n\n    try:\n        with _record_stage(stages, "deliver_telegram"):\n            telegram_result = telegram_events.process(lottery_key)\n            database.delete_state(f"telegram_event_error:{lottery_key}")\n    except Exception as exc:\n        telegram_result = {\n            "created": 0,\n            "delivery": {"sent": 0, "failed": 0, "skipped": 0},\n            "error": str(exc)[:500],\n        }\n        _state(\n            f"telegram_event_error:{lottery_key}",\n            {"message": str(exc)[:500], "at": int(time.time() * 1000)},\n        )\n'''
require(old in text, "service delivery order block not found")
text = text.replace(old, new, 1)
write(path, text)


# 4) Within warning delivery, send Telegram before FCM so token refresh/device fan-out cannot delay Telegram.
path = "server/app/push_alerts.py"
text = read(path)
text = text.replace("retry_before = now - 300_000", "retry_before = now - 60_000", 1)
pattern = re.compile(
    r"\n    if settings\.fcm_enabled:\n(?P<fcm>.*?)\n    if settings\.telegram_enabled:\n(?P<telegram>.*?)\n    sent = fcm_sent \+ telegram_sent",
    re.S,
)
match = pattern.search(text)
require(match is not None, "push delivery channel blocks not found")
fcm = match.group("fcm")
telegram = match.group("telegram")
swapped = (
    "\n    # Telegram warnings are sent first; FCM fan-out follows without blocking them.\n"
    "    if settings.telegram_enabled:\n" + telegram +
    "\n    if settings.fcm_enabled:\n" + fcm +
    "\n    sent = fcm_sent + telegram_sent"
)
text = text[:match.start()] + swapped + text[match.end():]
write(path, text)


# 5) Routine Telegram queue: newest/important first, suppress stale predictions, retry sooner.
path = "server/app/telegram_events.py"
text = read(path)
anchor = "_STRONG_ALERT_AFTER_MISSES = 3\n"
require(anchor in text, "telegram constant anchor not found")
text = text.replace(
    anchor,
    anchor + "_MAX_PENDING_PER_TARGET = 24\n_MAX_PREDICTION_EVENT_AGE_MS = 8 * 60_000\n_RETRY_COOLDOWN_MS = 60_000\n",
    1,
)
text = text.replace("retry_before = now - 300_000", "retry_before = now - _RETRY_COOLDOWN_MS", 1)
old_query = """                ORDER BY event.created_at ASC\n                LIMIT 500\n"""
new_query = """                ORDER BY CASE event.event_type WHEN 'win' THEN 0 ELSE 1 END,\n                         event.created_at DESC\n                LIMIT ?\n"""
require(old_query in text, "telegram pending query order not found")
text = text.replace(old_query, new_query, 1)
old_params = """                (target_key,),\n            ).fetchall()\n\n        for event in events:\n"""
new_params = """                (target_key, _MAX_PENDING_PER_TARGET),\n            ).fetchall()\n\n        for event in events:\n"""
require(old_params in text, "telegram pending query params not found")
text = text.replace(old_params, new_params, 1)
old_loop = '''            event_key = str(event["event_key"])\n            event_type = str(event["event_type"])\n            now = _now_ms()\n            if (\n                event_type == "prediction"\n                and not _prediction_event_is_eligible(event_key)\n            ):\n'''
new_loop = '''            event_key = str(event["event_key"])\n            event_type = str(event["event_type"])\n            now = _now_ms()\n            if (\n                event_type == "prediction"\n                and now - int(event["created_at"] or now) > _MAX_PREDICTION_EVENT_AGE_MS\n            ):\n                _suppress_delivery(\n                    event_key,\n                    target_key,\n                    attempted_at=now,\n                    message="预测消息已超过8分钟，避免迟到推送",\n                )\n                skipped += 1\n                continue\n            if (\n                event_type == "prediction"\n                and not _prediction_event_is_eligible(event_key)\n            ):\n'''
require(old_loop in text, "telegram delivery loop anchor not found")
text = text.replace(old_loop, new_loop, 1)
write(path, text)


# 6) A network stall should not hold the worker for 12 seconds per Telegram target.
path = "server/app/telegram_alerts.py"
text = read(path)
count = text.count("timeout_seconds: int = 12")
require(count == 2, f"expected 2 Telegram timeout defaults, found {count}")
text = text.replace("timeout_seconds: int = 12", "timeout_seconds: int = 6")
write(path, text)


# 7) Regression test: stale routine prediction is suppressed instead of arriving late.
path = "server/tests/test_telegram_events.py"
text = read(path)
insert_before = "    def test_prediction_start_watermark_prevents_historical_backfill(self) -> None:\n"
require(insert_before in text, "telegram test insertion point not found")
test = '''    def test_stale_prediction_is_suppressed_instead_of_sent_late(self) -> None:\n        self.save_forecast(target="100")\n        telegram_events.materialize_events("xyft")\n        stale_at = int(time.time() * 1000) - 9 * 60_000\n        with database.connection() as db:\n            db.execute(\n                "UPDATE telegram_events SET created_at=? WHERE event_key LIKE 'prediction:%'",\n                (stale_at,),\n            )\n\n        with patch.object(\n            telegram_events,\n            "settings",\n            self.fake_settings(),\n        ), patch.object(\n            telegram_alerts,\n            "send_html_message",\n            return_value=(True, 200, json.dumps({"ok": True})),\n        ) as sender:\n            result = telegram_events.deliver_pending_events()\n\n        self.assertEqual(0, result["sent"])\n        self.assertEqual(1, result["skipped"])\n        self.assertEqual(0, sender.call_count)\n        with database.connection() as db:\n            delivery = db.execute(\n                "SELECT status,message FROM telegram_event_deliveries LIMIT 1"\n            ).fetchone()\n        self.assertIsNotNone(delivery)\n        self.assertEqual("suppressed", str(delivery["status"]))\n        self.assertIn("超过8分钟", str(delivery["message"]))\n\n'''
text = text.replace(insert_before, test + insert_before, 1)
write(path, text)


# 8) Lightweight source contract for the console cleanup and latency policy.
path = "server/tests/test_console_delivery_simplification.py"
Path(path).write_text(
    '''from pathlib import Path\n\n\ndef test_console_hides_internal_stage_and_miss_watch_workspaces():\n    root = Path(__file__).resolve().parents[1] / "app"\n    js = (root / "console_v594.js").read_text(encoding="utf-8")\n    py = (root / "console_v3.py").read_text(encoding="utf-8")\n    assert "v597MissWatchWorkspace" not in js\n    assert "双彩种三期不中预警" not in js\n    assert "loadRecords();loadInsights();loadDraws();setInterval(loadDraws,30000);" in js\n    assert "<h3>服务状态</h3>" in py\n    assert "stage.name" not in py\n    assert "内部任务名、数据库细节与毫秒耗时已隐藏" in py\n\n\ndef test_telegram_latency_policy_is_explicit():\n    root = Path(__file__).resolve().parents[1] / "app"\n    events = (root / "telegram_events.py").read_text(encoding="utf-8")\n    alerts = (root / "telegram_alerts.py").read_text(encoding="utf-8")\n    service = (root / "service.py").read_text(encoding="utf-8")\n    assert "_MAX_PREDICTION_EVENT_AGE_MS = 8 * 60_000" in events\n    assert "_RETRY_COOLDOWN_MS = 60_000" in events\n    assert "timeout_seconds: int = 6" in alerts\n    assert service.index('stages, "deliver_push"') < service.index('stages, "deliver_telegram"')\n''',
    encoding="utf-8",
)

print("console + Telegram fast path patch applied")
