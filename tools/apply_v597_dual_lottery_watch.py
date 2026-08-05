from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected one regex match, found {count}")
    return updated


# ---------------------------------------------------------------------------
# App: preload and cache both lotteries. Switching only swaps the cached state;
# both datasets are refreshed together in the background.
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt"
text = read(path)
text = replace_once(
    text,
    "import java.util.UUID\nimport java.util.concurrent.Executors\n",
    "import java.util.UUID\nimport java.util.concurrent.ConcurrentHashMap\n"
    "import java.util.concurrent.Executors\n",
    "AppController concurrent map import",
)
text = replace_once(
    text,
    "    private val executor = Executors.newSingleThreadExecutor()\n",
    "    private val executor = Executors.newFixedThreadPool(\n"
    "        LotteryType.entries.size.coerceAtLeast(2),\n"
    "    )\n",
    "AppController dual loader executor",
)
text = replace_once(
    text,
    "    private val generation = AtomicInteger(0)\n"
    "    private val aiGeneration = AtomicInteger(0)\n"
    "    private val verifiedHistoryReady = mutableSetOf<LotteryType>()\n"
    "    private val reportCache = mutableMapOf<LotteryType, CachedForecast>()\n",
    "    private val refreshGenerations = LotteryType.entries.associateWith { AtomicInteger(0) }\n"
    "    private val aiGeneration = AtomicInteger(0)\n"
    "    private val verifiedHistoryReady = ConcurrentHashMap.newKeySet<LotteryType>()\n"
    "    private val reportCache = ConcurrentHashMap<LotteryType, CachedForecast>()\n"
    "    private val stateCache = ConcurrentHashMap<LotteryType, AppUiState>()\n"
    "    private val loadingLotteries = ConcurrentHashMap.newKeySet<LotteryType>()\n",
    "AppController cache fields",
)
text = replace_once(
    text,
    "    init {\n        refresh()\n",
    "    init {\n        refreshAll(force = true)\n",
    "AppController initial dual refresh",
)
new_switch_and_refresh = r'''    fun selectLottery(lottery: LotteryType) {
        if (lottery == state.lottery) return
        val previous = state
        stateCache[previous.lottery] = previous
        preferences.edit { putString("lottery", lottery.apiKey) }

        val cached = stateCache[lottery]
        state = (cached ?: AppUiState(
            lottery = lottery,
            aiConcurrency = previous.aiConcurrency,
        )).copy(
            lottery = lottery,
            aiStatuses = previous.aiStatuses,
            aiError = previous.aiError,
            aiConcurrency = previous.aiConcurrency,
        )
        refreshLottery(lottery, force = false)
    }

    fun refresh() {
        refreshAll(force = true)
    }

    private fun refreshAll(force: Boolean) {
        val selected = state.lottery
        val order = buildList {
            add(selected)
            addAll(LotteryType.entries.filterNot { it == selected })
        }
        order.forEach { lottery -> refreshLottery(lottery, force) }
    }

    private fun refreshLottery(lottery: LotteryType, force: Boolean) {
        val cached = stateCache[lottery]
        if (!force && cached != null && !isCacheStale(cached)) return
        if (!loadingLotteries.add(lottery)) return

        val generation = refreshGenerations.getValue(lottery)
        val token = generation.incrementAndGet()
        if (state.lottery == lottery) {
            state = state.copy(
                isLoading = state.snapshot == null,
                isRefreshing = state.snapshot != null,
                error = null,
            )
            stateCache[lottery] = state
        }

        executor.execute {
            val result = runCatching { load(lottery) }
            mainHandler.post {
                loadingLotteries.remove(lottery)
                if (generation.get() != token) return@post

                result.fold(
                    onSuccess = { loaded ->
                        val previous = if (state.lottery == lottery) {
                            state
                        } else {
                            stateCache[lottery]
                        }
                        val preservedAi = if (
                            previous?.report?.targetPeriod == loaded.report?.targetPeriod
                        ) {
                            previous.aiForecasts
                        } else {
                            emptyList()
                        }
                        val merged = loaded.copy(
                            aiForecasts = (preservedAi + loaded.aiForecasts)
                                .distinctBy { it.profileId },
                            aiStatuses = previous?.aiStatuses.orEmpty(),
                            aiError = previous?.aiError,
                            aiConcurrency = state.aiConcurrency,
                        )
                        stateCache[lottery] = merged
                        if (state.lottery == lottery) {
                            val globalStatuses = state.aiStatuses
                            val globalError = state.aiError
                            val concurrency = state.aiConcurrency
                            state = merged.copy(
                                aiStatuses = globalStatuses,
                                aiError = globalError,
                                aiConcurrency = concurrency,
                            )
                            stateCache[lottery] = state
                        }
                    },
                    onFailure = { failure ->
                        val previous = stateCache[lottery]
                            ?: AppUiState(
                                lottery = lottery,
                                aiConcurrency = state.aiConcurrency,
                            )
                        val failed = previous.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = failure.message ?: "数据加载失败",
                        )
                        stateCache[lottery] = failed
                        if (state.lottery == lottery) {
                            state = state.copy(
                                isLoading = false,
                                isRefreshing = false,
                                error = failure.message ?: "数据加载失败",
                            )
                            stateCache[lottery] = state
                        }
                    },
                )
            }
        }
    }

    private fun isCacheStale(cached: AppUiState): Boolean {
        val syncedAt = cached.snapshot?.sourceHealth?.syncedAtEpochMs ?: return true
        return System.currentTimeMillis() - syncedAt > 45_000L
    }
'''
text = regex_once(
    text,
    r"    fun selectLottery\(lottery: LotteryType\) \{.*?\n    \}\n\n"
    r"    fun refresh\(\) \{.*?\n    \}\n\n"
    r"    fun saveAiConfig",
    new_switch_and_refresh + "\n    fun saveAiConfig",
    "AppController switch and refresh implementation",
)
text = replace_once(
    text,
    "    fun close() {\n        generation.incrementAndGet()\n",
    "    fun close() {\n"
    "        refreshGenerations.values.forEach { it.incrementAndGet() }\n",
    "AppController close generations",
)
write(path, text)


# ---------------------------------------------------------------------------
# Server: compute per-lottery, per-source/model consecutive miss health.
# Three settled misses trigger an alert and retain the exact three periods.
# ---------------------------------------------------------------------------
path = "server/app/admin_insights.py"
text = read(path)
text = replace_once(
    text,
    '        "source_name": "云端 AI" if source == "ai" else "本机云端",\n',
    '        "source_name": "天机云端 AI" if source == "ai" else "天机云端本地",\n',
    "server source naming",
)
watch_code = r'''

def _prediction_miss_watch_from_records(
    records_desc: list[dict[str, Any]],
    threshold: int = 3,
) -> dict[str, Any]:
    safe_threshold = max(1, int(threshold))
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    seen_periods: dict[tuple[str, str, str], set[str]] = defaultdict(set)

    for record in records_desc:
        lottery = str(record.get("lottery") or "")
        source = str(record.get("source") or "")
        model = str(record.get("model") or "")
        target_period = str(record.get("target_period") or "")
        if not lottery or not source or not model or not target_period:
            continue
        key = (lottery, source, model)
        if target_period in seen_periods[key]:
            continue
        seen_periods[key].add(target_period)
        grouped[key].append(record)

    predictions_by_lottery: dict[str, list[dict[str, Any]]] = defaultdict(list)
    warning_count = 0
    for (lottery, source, model), records in grouped.items():
        settled = [record for record in records if record.get("top6_hit") is not None]
        current_miss_streak = 0
        for record in settled:
            if record.get("top6_hit") is False:
                current_miss_streak += 1
            else:
                break
        warning = current_miss_streak >= safe_threshold
        if warning:
            warning_count += 1
        recent = settled[:safe_threshold]
        source_name = "天机云端 AI" if source == "ai" else "天机云端本地"
        predictions_by_lottery[lottery].append(
            {
                "source": source,
                "source_name": source_name,
                "model": model,
                "warning": warning,
                "threshold": safe_threshold,
                "current_miss_streak": current_miss_streak,
                "total_records": len(records),
                "settled_records": len(settled),
                "pending_records": len(records) - len(settled),
                "recent_three": [
                    {
                        "target_period": str(record.get("target_period") or ""),
                        "hit": bool(record.get("top6_hit")),
                        "actual_number": record.get("actual_number"),
                        "position": int(record.get("position") or 0),
                        "top6": list(record.get("top6") or []),
                        "settled_at_epoch_ms": record.get("settled_at_epoch_ms"),
                    }
                    for record in recent
                ],
            }
        )

    lotteries = []
    for key, spec in LOTTERIES.items():
        predictions = predictions_by_lottery.get(key, [])
        predictions.sort(
            key=lambda item: (
                not item["warning"],
                -int(item["current_miss_streak"]),
                str(item["source_name"]),
                str(item["model"]),
            )
        )
        lotteries.append(
            {
                "key": key,
                "name": spec.name,
                "warning_count": sum(1 for item in predictions if item["warning"]),
                "predictions": predictions,
            }
        )

    return {
        "threshold": safe_threshold,
        "warning_count": warning_count,
        "lotteries": lotteries,
        "generated_at_epoch_ms": int(
            datetime.now(tz=timezone.utc).timestamp() * 1000
        ),
    }


def prediction_miss_watch(threshold: int = 3) -> dict[str, Any]:
    with database.connection() as db:
        rows = db.execute(
            "SELECT * FROM forecasts ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return _prediction_miss_watch_from_records(
        [_record_dict(row) for row in rows],
        threshold=threshold,
    )
'''
text = replace_once(
    text,
    "\ndef _read_json_file(path: str) -> dict[str, Any] | None:\n",
    watch_code + "\n\ndef _read_json_file(path: str) -> dict[str, Any] | None:\n",
    "server prediction miss watch functions",
)
text = replace_once(
    text,
    '        "integrity": _data_integrity(),\n        "timeline": _timeline(),\n',
    '        "integrity": _data_integrity(),\n'
    '        "miss_watch": prediction_miss_watch(threshold=3),\n'
    '        "timeline": _timeline(),\n',
    "server operations miss watch payload",
)
write(path, text)


# ---------------------------------------------------------------------------
# Console: add a combined two-lottery health board. It reads the operations API
# independently so the existing maintenance/timeline rendering stays isolated.
# ---------------------------------------------------------------------------
path = "server/app/console_v594.js"
text = read(path)
console_watch_js = r'''

(()=>{
  const overview=document.querySelector('#panel-overview');
  if(!overview)return;
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const workspace=document.createElement('section');
  workspace.className='section v597-watch-section';
  workspace.id='v597MissWatchWorkspace';
  workspace.innerHTML=`<div class="v3-head"><div><h3>双彩种三期不中预警</h3><p>幸运飞艇与澳洲幸运10放在同一处；每个预测来源和模型独立计算，连续三期六码未中立即报警。</p></div><span class="badge" id="v597WatchBadge">正在检查</span></div><div class="v597-watch-grid" id="v597WatchGrid"><div class="v3-empty"><strong>正在读取预测健康</strong>请稍候</div></div>`;
  const draw=document.querySelector('#drawWorkspace');
  if(draw)draw.insertAdjacentElement('afterend',workspace);else overview.prepend(workspace);

  const periodRow=item=>{
    const periods=item.recent_three||[];
    if(!periods.length)return '<div class="v597-period-empty">暂无已结算记录</div>';
    return `<div class="v597-periods">${periods.map(record=>`<span class="v597-period ${record.hit?'hit':'miss'}"><b>${esc(record.target_period)}</b><small>${record.hit?'命中':'未中'} · 第 ${Number(record.position)+1} 名</small></span>`).join('')}</div>`;
  };
  const predictionCard=item=>`<article class="v597-prediction ${item.warning?'warning':'safe'}"><div class="v597-prediction-head"><div><span class="v597-source ${item.source==='ai'?'ai':'native'}">${esc(item.source_name)}</span><strong>${esc(item.model)}</strong></div><span class="v597-streak">${item.current_miss_streak} 期未中</span></div><div class="v597-status ${item.warning?'bad':'good'}">${item.warning?'已达到三期预警':'当前未触发预警'}</div>${periodRow(item)}<div class="v597-meta">已结算 ${item.settled_records} · 待开奖 ${item.pending_records}</div></article>`;
  const lotteryCard=lottery=>`<section class="v597-lottery ${lottery.warning_count?'warning':''}"><div class="v597-lottery-head"><div><h4>${esc(lottery.name)}</h4><p>每种预测单独追踪连续未中</p></div><span class="badge ${lottery.warning_count?'bad':'good'}">${lottery.warning_count?lottery.warning_count+' 项预警':'全部正常'}</span></div><div class="v597-prediction-list">${lottery.predictions?.length?lottery.predictions.map(predictionCard).join(''):'<div class="v3-empty"><strong>暂无预测记录</strong>等待云端产生并完成结算</div>'}</div></section>`;

  async function loadMissWatch(){
    const grid=document.querySelector('#v597WatchGrid'),badge=document.querySelector('#v597WatchBadge');
    if(!grid||!badge)return;
    try{
      const response=await fetch('/admin/api/operations',{cache:'no-store',headers:{'X-Tianji-Admin':'1'}});
      if(response.status===401){location.href='/admin';return}
      const data=await response.json();
      if(!response.ok)throw Error(data.detail||('HTTP '+response.status));
      const watch=data.miss_watch||{warning_count:0,lotteries:[]};
      badge.className='badge '+(watch.warning_count?'bad':'good');
      badge.textContent=watch.warning_count?`${watch.warning_count} 项预警`:'暂无三期预警';
      grid.innerHTML=watch.lotteries?.length?watch.lotteries.map(lotteryCard).join(''):'<div class="v3-empty"><strong>暂无预警数据</strong>等待正式预测完成结算</div>';
    }catch(error){
      badge.className='badge warn';badge.textContent='读取失败';
      grid.innerHTML=`<div class="v3-empty"><strong>预警读取失败</strong>${esc(error.message)}</div>`;
    }
  }
  loadMissWatch();
  setInterval(loadMissWatch,30000);
})();
'''
if "v597MissWatchWorkspace" in text:
    raise RuntimeError("console v5.9.7 watch already present")
text += console_watch_js
write(path, text)


path = "server/app/console_v594.css"
text = read(path)
console_watch_css = r'''

/* Tianji Console V5.9.7 dual-lottery miss watch */
.v597-watch-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}
.v597-lottery{padding:16px;border:1px solid var(--v5-line,var(--line));border-radius:22px;background:var(--v5-surface,var(--surface));box-shadow:0 5px 18px rgba(40,45,72,.055)}
.v597-lottery.warning{border-color:color-mix(in srgb,var(--bad) 26%,var(--v5-line,var(--line)))}
.v597-lottery-head,.v597-prediction-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.v597-lottery-head h4{margin:0;font-size:17px;letter-spacing:-.025em}
.v597-lottery-head p{margin:3px 0 0;color:var(--muted);font-size:10px}
.v597-prediction-list{display:grid;gap:8px;margin-top:12px}
.v597-prediction{padding:12px;border:1px solid var(--v5-line,var(--line));border-radius:16px;background:var(--soft)}
.v597-prediction.warning{background:linear-gradient(135deg,color-mix(in srgb,var(--bad-soft) 75%,var(--soft)),var(--soft));border-color:color-mix(in srgb,var(--bad) 25%,var(--line))}
.v597-prediction-head strong{display:block;margin-top:5px;font-size:11px;overflow-wrap:anywhere}
.v597-source{display:inline-flex;align-items:center;min-height:22px;padding:0 8px;border-radius:999px;font-size:8px;font-weight:820}
.v597-source.ai{color:var(--primary);background:var(--primary-soft)}
.v597-source.native{color:#168f99;background:color-mix(in srgb,#35c3d2 15%,transparent)}
.v597-streak{flex:0 0 auto;font-size:11px;font-weight:850;color:var(--warn)}
.v597-prediction.warning .v597-streak{color:var(--bad)}
.v597-status{font-size:9px;font-weight:760;margin-top:8px}
.v597-periods{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:8px}
.v597-period{min-width:0;padding:7px;border-radius:11px;border:1px solid var(--line);background:var(--surface)}
.v597-period b,.v597-period small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.v597-period b{font-size:9px}.v597-period small{font-size:7px;color:var(--muted);margin-top:2px}
.v597-period.hit{border-color:color-mix(in srgb,var(--good) 20%,var(--line))}.v597-period.miss{border-color:color-mix(in srgb,var(--bad) 18%,var(--line))}
.v597-period-empty,.v597-meta{font-size:8px;color:var(--muted);margin-top:8px}
@media(max-width:840px){.v597-watch-grid{grid-template-columns:1fr}}
@media(max-width:430px){.v597-lottery{padding:13px}.v597-periods{grid-template-columns:1fr}.v597-period b,.v597-period small{white-space:normal}}
'''
if "v597-watch-grid" in text:
    raise RuntimeError("console v5.9.7 watch CSS already present")
text += console_watch_css
write(path, text)


# ---------------------------------------------------------------------------
# Server regression tests for exact three-miss threshold and lottery/model
# isolation.
# ---------------------------------------------------------------------------
write(
    "server/tests/test_prediction_miss_watch.py",
    r'''from __future__ import annotations

import unittest

from app.admin_insights import _prediction_miss_watch_from_records


class PredictionMissWatchTests(unittest.TestCase):
    @staticmethod
    def record(
        lottery: str,
        source: str,
        model: str,
        period: str,
        hit: bool | None,
        created: int,
    ) -> dict:
        return {
            "lottery": lottery,
            "source": source,
            "model": model,
            "target_period": period,
            "top6_hit": hit,
            "actual_number": 8,
            "position": 0,
            "top6": [1, 2, 3, 4, 5, 6],
            "settled_at_epoch_ms": created if hit is not None else None,
            "created_at_epoch_ms": created,
        }

    def test_three_consecutive_misses_trigger_warning_with_exact_periods(self) -> None:
        records = [
            self.record("xyft", "ai", "deepseek-v4", "104", False, 104),
            self.record("xyft", "ai", "deepseek-v4", "103", False, 103),
            self.record("xyft", "ai", "deepseek-v4", "102", False, 102),
            self.record("xyft", "ai", "deepseek-v4", "101", True, 101),
        ]
        result = _prediction_miss_watch_from_records(records, threshold=3)
        xyft = next(item for item in result["lotteries"] if item["key"] == "xyft")
        prediction = xyft["predictions"][0]
        self.assertTrue(prediction["warning"])
        self.assertEqual(prediction["current_miss_streak"], 3)
        self.assertEqual(
            [item["target_period"] for item in prediction["recent_three"]],
            ["104", "103", "102"],
        )

    def test_hit_resets_streak_and_models_are_isolated(self) -> None:
        records = [
            self.record("azxy10", "native", "native-a", "204", False, 204),
            self.record("azxy10", "native", "native-a", "203", True, 203),
            self.record("azxy10", "ai", "ai-b", "204", False, 202),
            self.record("azxy10", "ai", "ai-b", "203", False, 201),
            self.record("azxy10", "ai", "ai-b", "202", False, 200),
        ]
        result = _prediction_miss_watch_from_records(records, threshold=3)
        azxy = next(item for item in result["lotteries"] if item["key"] == "azxy10")
        values = {item["model"]: item for item in azxy["predictions"]}
        self.assertFalse(values["native-a"]["warning"])
        self.assertEqual(values["native-a"]["current_miss_streak"], 1)
        self.assertTrue(values["ai-b"]["warning"])
        self.assertEqual(result["warning_count"], 1)

    def test_pending_record_does_not_count_as_miss(self) -> None:
        records = [
            self.record("xyft", "ai", "model", "304", None, 304),
            self.record("xyft", "ai", "model", "303", False, 303),
            self.record("xyft", "ai", "model", "302", False, 302),
        ]
        result = _prediction_miss_watch_from_records(records, threshold=3)
        xyft = next(item for item in result["lotteries"] if item["key"] == "xyft")
        prediction = xyft["predictions"][0]
        self.assertFalse(prediction["warning"])
        self.assertEqual(prediction["current_miss_streak"], 2)
        self.assertEqual(prediction["pending_records"], 1)


if __name__ == "__main__":
    unittest.main()
''',
)

print("Applied Tianji v5.9.7 dual-lottery cache and three-miss watch.")
