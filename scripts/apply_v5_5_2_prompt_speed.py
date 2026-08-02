#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected 1 match, got {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


analysis = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
gradle = ROOT / "app/build.gradle.kts"
readme = ROOT / "README.md"

replace_once(
    analysis,
    "val reasoningResponse = if (highDecision.supported) runCatching {",
    "val reasoningResponse = if (highDecision.supported && !baseDecision.expectsReasoning) runCatching {",
)

replace_once(
    analysis,
    '''        val userPrompt = analysisPayload(snapshot, report, historyLimit).toString()
        val started = System.currentTimeMillis()
        val primaryDecision = AiReasoningEngine.resolve(config)
''',
    '''        val userPrompt = analysisPayload(snapshot, report, historyLimit).toString()
        val retryPrompt = JSONObject(userPrompt).apply {
            put(
                "retry_rule",
                "上一轮没有生成完整JSON。本轮继续真实思考，但禁止重新逐期复述；直接利用已核验统计完成比较并尽快输出position与10项scores。",
            )
        }.toString()
        val started = System.currentTimeMillis()
        val primaryDecision = AiReasoningEngine.resolve(config)
''',
)

replace_once(
    analysis,
    '''            executionNote: String,
            fallback: Boolean = false,
        ): AiForecast {''',
    '''            executionNote: String,
            fallback: Boolean = false,
            prompt: String = userPrompt,
        ): AiForecast {''',
)

replace_once(
    analysis,
    '''                userPrompt = userPrompt,
                reasoningDecision = reasoningDecision,''',
    '''                userPrompt = prompt,
                reasoningDecision = reasoningDecision,''',
)

replace_once(
    analysis,
    '''                fallback = reasoningFallback,
            )''',
    '''                fallback = reasoningFallback,
                prompt = retryPrompt,
            )''',
)

replace_once(
    analysis,
    '''            put("data_source", "fresh lottery API history fetched immediately before this analysis")
            put("history_order", "oldest_to_newest; the final item is the latest verified draw")
            put("latest_period", snapshot.latest.period)''',
    '''            put("data_source", "fresh lottery API history fetched immediately before this analysis")
            put("history_order", "oldest_to_newest; the final item is the latest verified draw")
            put("reasoning_efficiency_rule", AiPromptCompactor.REASONING_RULE)
            put("compact_draw_format", AiPromptCompactor.FORMAT)
            put("latest_period", snapshot.latest.period)''',
)

old_stats = '''            put(
                "verified_position_statistics",
                JSONArray(
                    AiFactEngine.calculate(snapshot.history).map { facts ->
                        JSONObject()
                            .put("position", facts.position + 1)
                            .put("latest_number", facts.latestNumber)
                            .put("recent20_counts_for_numbers_1_to_10", JSONArray(facts.recent20Counts))
                            .put("current_omissions_for_numbers_1_to_10", JSONArray(facts.omissions))
                            .put("latest_size_side", facts.sizeSide)
                            .put("latest_size_streak", facts.sizeStreak)
                    },
                ),
            )
'''
new_stats = '''            put(
                "verified_position_statistics",
                AiPromptCompactor.verifiedPositionStatistics(snapshot.history),
            )
'''
replace_once(analysis, old_stats, new_stats)

old_local_models = '''            put(
                "local_model_quality_only_no_predictions",
                JSONArray(
                    report.models.map {
                        JSONObject()
                            .put("name", it.name)
                            .put("formal_weight", it.weight)
                            .put("shadow_weight", it.shadowWeight)
                            .put("forward_hit_rate", it.hitRate)
                            .put("log_loss", it.logLoss)
                    },
                ),
            )
'''
replace_once(analysis, old_local_models, "")

old_draws = '''            put(
                "verified_draws_oldest_to_newest",
                JSONArray(
                    snapshot.history.takeLast(historyLimit).map { draw ->
                        JSONObject().put("period", draw.period).put("numbers", JSONArray(draw.numbers))
                    },
                ),
            )
'''
new_draws = '''            put(
                "verified_draws_oldest_to_newest",
                AiPromptCompactor.compactDraws(snapshot.history, historyLimit),
            )
'''
replace_once(analysis, old_draws, new_draws)

replace_once(gradle, 'versionCode = 26\n        versionName = "5.5.1"', 'versionCode = 27\n        versionName = "5.5.2"')
replace_once(readme, '- 版本：5.5.1', '- 版本：5.5.2')
replace_once(
    readme,
    '## v5.5.0 稳定重构版',
    '''## v5.5.2 思考效率优化

- 保留 DeepSeek 真实 thinking、原有高输出上限和深入推理，不使用非思考结果冒充推理结果。
- 60/120 期历史数量不缩水，开奖记录改为紧凑编码，减少重复 JSON 字段。
- 本机预先核验近20/60期频次、遗漏和当前号码后继转移，避免 AI 在思考中重复逐期计数。
- 删除不会提供给 AI 候选结果、但会增加理解负担的本地模型权重摘要。
- 提示模型禁止逐期复述，完成十名次比较后立即输出结构化概率矩阵。
- 重试继续使用真实思考和充足输出空间，只使用更明确的紧凑提示。

## v5.5.0 稳定重构版''',
)

print("v5.5.2 prompt-speed patch applied")
