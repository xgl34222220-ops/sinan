from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AI_ANALYSIS = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
AI_CHAT = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt"
BUILD = ROOT / "app/build.gradle.kts"
TEST = ROOT / "app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiIndependenceContractTest.kt"
NOTES = ROOT / "RELEASE_NOTES_v5.7.1.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, got {count}")
    return updated


def patch_formal_prediction() -> None:
    text = AI_ANALYSIS.read_text(encoding="utf-8")

    old_learning = '''        val learningContext = learningStore.snapshotAll(
            snapshot.history,
            snapshot.lottery.apiKey,
            config.id,
            AiLearningStrategy.official(config),
        )
        val userPrompt = analysisPayload(snapshot, report, historyLimit)
            .put("adaptive_learning", learningContext)
            .toString()
'''
    new_learning = '''        // Strict independence protocol: the remote model receives only raw verified draws.
        // AI-specific outcomes remain archived for diagnostics, but local engineered factors and
        // native-model selections are deliberately excluded from the prediction prompt.
        val userPrompt = analysisPayload(snapshot, report, historyLimit).toString()
'''
    text = replace_once(text, old_learning, new_learning, "formal prompt isolation")

    payload_function = '''    private fun analysisPayload(
        snapshot: DrawSnapshot,
        report: ForecastReport,
        historyLimit: Int,
    ): JSONObject {
        val rawHistory = snapshot.history
            .filter { it.numbers.size == 10 }
            .takeLast(historyLimit)
        require(rawHistory.isNotEmpty()) { "没有可用于独立 AI 分析的开奖历史" }
        return JSONObject().apply {
            put("task", "仅根据原始开奖历史，独立选择下一期一个名次并对号码1至10排序")
            put("independence_protocol", "raw-history-v1")
            put(
                "input_isolation",
                "客户端未提供本机模型选择的名次、六码、七码、概率矩阵、因子权重或预计算统计。不得猜测本机答案，也不得为了刻意不同而反向选择。",
            )
            put("lottery", snapshot.lottery.displayName)
            put("target_period", report.targetPeriod)
            put("trained_through", report.trainedThroughPeriod)
            put("analysis_window", rawHistory.size)
            put("data_source", "fresh lottery API history fetched immediately before this analysis")
            put("history_order", "oldest_to_newest; final item is the latest verified draw")
            put("latest_period", snapshot.latest.period)
            put(
                "raw_draws_oldest_to_newest",
                JSONArray(rawHistory.map { draw ->
                    JSONObject()
                        .put("period", draw.period)
                        .put("numbers", JSONArray(draw.numbers))
                }),
            )
            put(
                "analysis_requirements",
                JSONArray(
                    listOf(
                        "derive your own useful features directly from raw draws",
                        "compare all ten positions before selecting one unless evidence is genuinely weak",
                        "use at least three independently justified signals; do not inherit client weights",
                        "treat small samples and tiny differences as weak evidence",
                        "produce your own ten-number score vector; natural agreement with another model is allowed but copying is not",
                    ),
                ),
            )
            put(
                "output_rule",
                "只输出position和scores紧凑JSON；不要输出隐藏思维链、Markdown、逐期复述或额外字段。",
            )
            put(
                "required_json_schema",
                JSONObject()
                    .put("position", "1至10的整数")
                    .put("scores", "按号码1至10排列的10项非负原始评分，不得全部相同"),
            )
        }
    }

    private fun isRetriableModelOutput'''
    text = regex_once(
        text,
        r"    private fun analysisPayload\(.*?\n    private fun isRetriableModelOutput",
        payload_function,
        "replace formal analysis payload",
    )

    new_system_prompt = '''const val SYSTEM_PROMPT = """你是与客户端本机模型严格隔离的概率排序模型。你只会收到按时间排序的真实开奖原始记录、目标期和必要元数据；客户端不会提供本机选择的名次、候选、概率矩阵、预计算频次/遗漏/转移统计或本机因子权重。你必须从原始记录自行决定分析方法，先比较十个名次，再选择证据相对充分的一个名次，并按号码1至10给出10项非负评分。不得猜测、迎合或复制本机答案，也不得为了显得不同而故意反选；独立分析后自然重合是允许的。小样本和细微差异必须降权。正式预测有严格时间预算：禁止输出隐藏思维链、解释、Markdown或逐期复述；只输出position与scores的紧凑JSON。不得承诺准确率、盈利或必中。"""'''
    text = regex_once(
        text,
        r'const val SYSTEM_PROMPT = """.*?"""',
        new_system_prompt,
        "replace formal system prompt",
    )

    text = replace_once(
        text,
        'append(executionNote)\n',
        'append(executionNote)\n                    append(" · 严格独立原始历史输入")\n',
        "formal execution audit label",
    )
    text = text.replace(
        "正在使用同一模型关闭额外思考并重新提交精简统计任务",
        "正在使用同一模型关闭额外思考并重新提交同一份原始历史任务",
    )

    AI_ANALYSIS.write_text(text, encoding="utf-8")


def patch_chat_analysis() -> None:
    text = AI_CHAT.read_text(encoding="utf-8")

    old_position = '''        val requestedPosition = AiAdaptiveSignalEngine.extractRequestedPosition(text)
            ?: report.selectedPosition
        val learningProfile = learningStore.profile(
            snapshot.lottery.apiKey,
            config.id,
            learningStrategy,
            requestedPosition,
        )
        val learningContext = learningStore.snapshot(
            snapshot.history,
            snapshot.lottery.apiKey,
            config.id,
            learningStrategy,
            requestedPosition,
        )
'''
    new_position = '''        val requestedPosition = AiAdaptiveSignalEngine.extractRequestedPosition(text)
        // Never default an independent chat request to the native model's selected position.
        // The provisional position only drives the local status card; strict independent prompts
        // omit this learning context and compare all ten positions from raw history.
        val learningPosition = requestedPosition ?: session.prediction?.position ?: 0
        val learningProfile = learningStore.profile(
            snapshot.lottery.apiKey,
            config.id,
            learningStrategy,
            learningPosition,
        )
        val learningContext = learningStore.snapshot(
            snapshot.history,
            snapshot.lottery.apiKey,
            config.id,
            learningStrategy,
            learningPosition,
        )
'''
    text = replace_once(text, old_position, new_position, "chat native-position leak")

    build_function = '''    fun build(
        snapshot: DrawSnapshot,
        report: ForecastReport,
        question: String,
        judgementMode: AiJudgementMode,
        learningContext: JSONObject,
    ): JSONObject {
        val verifiedHistory = snapshot.history
            .filter { it.numbers.size == 10 }
            .takeLast(120)
        require(verifiedHistory.isNotEmpty()) { "没有可用于对话分析的接口历史" }
        val wantsPrediction = AiChatProtocol.wantsPrediction(question)
        val requestedPosition = extractPosition(question)
        val positions = requestedPosition?.let(::listOf) ?: (0 until 10).toList()
        val rawWindow = when {
            wantsPrediction -> 120
            requestedPosition != null -> 80
            else -> 60
        }
        val compactHistory = verifiedHistory.takeLast(rawWindow)
        val independent = judgementMode == AiJudgementMode.INDEPENDENT
        return JSONObject()
            .put("lottery", snapshot.lottery.displayName)
            .put("latest_period", snapshot.latest.period)
            .put("target_period", report.targetPeriod)
            .put("history_source", "current lottery API snapshot")
            .put("history_order", "oldest_to_newest")
            .put("verified_history_size", verifiedHistory.size)
            .put("raw_history_window", compactHistory.size)
            .put("position_scope", JSONArray(positions.map { it + 1 }))
            .put("latest_numbers", JSONArray(snapshot.latest.numbers))
            .put(
                "compact_history",
                JSONArray(compactHistory.map { draw ->
                    JSONObject()
                        .put("period", draw.period)
                        .put("numbers", JSONArray(draw.numbers))
                }),
            )
            .put(
                "input_isolation",
                if (independent) {
                    "strict: no native selected position, candidates, matrix, factor weights or client precomputed statistics"
                } else {
                    "native reference explicitly enabled by the user"
                },
            )
            .apply {
                if (independent) {
                    put("independence_protocol", "raw-history-v1")
                    put(
                        "independent_analysis_rule",
                        "自行从原始历史提取特征并比较名次；不得猜测本机答案，也不得为了刻意不同而反向选择。",
                    )
                } else {
                    put(
                        "verified_position_statistics",
                        JSONArray(positions.map { position ->
                            toJson(computePositionStatistics(verifiedHistory, position))
                        }),
                    )
                    put("adaptive_learning", learningContext)
                    put(
                        "native_model_reference",
                        JSONObject()
                            .put("algorithm_version", report.algorithmVersion)
                            .put("trained_through_period", report.trainedThroughPeriod)
                            .put("selected_position", report.selectedPosition + 1)
                            .put("top6", JSONArray(report.selected.top6))
                            .put("evidence_mode", report.mode.name)
                            .put(
                                "rule",
                                if (judgementMode == AiJudgementMode.CONTRARIAN) {
                                    "contrarian audit only; actively search for weaknesses and alternatives"
                                } else {
                                    "reference only; independently calculate before accepting"
                                },
                            ),
                    )
                }
            }
    }

    private fun extractPosition'''
    text = regex_once(
        text,
        r"    fun build\(\n        snapshot: DrawSnapshot,.*?\n    private fun extractPosition",
        build_function,
        "replace chat context builder",
    )

    old_context_message = '''                    "以下是客户端刚刚根据当前开奖接口历史逐期计算的事实。所有回答只能以这些事实为依据：\\n${context}",
'''
    new_context_message = '''                    "以下是当前开奖接口原始历史与必要元数据。独立模式不会包含本机候选、名次、概率矩阵或本机预计算统计；参考/反向模式才会明确附带native_model_reference：\\n${context}",
'''
    text = replace_once(text, old_context_message, new_context_message, "chat context message")

    old_independent = '''            AiJudgementMode.INDEPENDENT ->
                "当前为独立学习模式：客户端没有向你提供本机最终候选。必须形成自己的判断，不得猜测或迎合本机答案。"
'''
    new_independent = '''            AiJudgementMode.INDEPENDENT ->
                "当前为严格独立模式：客户端只提供原始开奖历史，不提供本机选择的名次、候选、概率矩阵、因子权重或本机预计算统计。必须自行提取特征并比较十个名次；不得猜测本机答案，也不得为了显得不同而故意反选。"
'''
    text = replace_once(text, old_independent, new_independent, "chat independent system prompt")

    text = replace_once(
        text,
        '"只能引用客户端提供的当前开奖接口历史、核验统计和持续学习档案，不得虚构期号、次数或数据来源。" +\n',
        '"独立模式只能引用客户端提供的原始开奖历史；参考/反向模式可额外使用明确标注的核验统计与本机参考。不得虚构期号、次数或数据来源。" +\n',
        "chat evidence rule",
    )

    AI_CHAT.write_text(text, encoding="utf-8")


def patch_version_and_docs() -> None:
    build = BUILD.read_text(encoding="utf-8")
    build = replace_once(build, 'versionCode = 37', 'versionCode = 38', "version code")
    build = replace_once(build, 'versionName = "5.7.0"', 'versionName = "5.7.1"', "version name")
    BUILD.write_text(build, encoding="utf-8")

    TEST.parent.mkdir(parents=True, exist_ok=True)
    TEST.write_text(
        '''package com.tianji.probabilitylab.nativev4.ai

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AiIndependenceContractTest {
    private fun source(name: String): String = File(
        "src/main/java/com/tianji/probabilitylab/nativev4/ai/$name",
    ).readText()

    @Test
    fun formalPredictionUsesRawHistoryWithoutNativeStatistics() {
        val source = source("AiAnalysis.kt")
        val payload = source.substringAfter("private fun analysisPayload(")
            .substringBefore("private fun isRetriableModelOutput")
        assertTrue(payload.contains("raw_draws_oldest_to_newest"))
        assertTrue(payload.contains("raw-history-v1"))
        assertFalse(payload.contains("verified_position_statistics"))
        assertFalse(payload.contains("report.selectedPosition"))
        assertFalse(payload.contains("report.selected.top6"))
    }

    @Test
    fun independentChatDoesNotDefaultToNativePositionOrInjectNativeFacts() {
        val source = source("AiChatController.kt")
        assertFalse(source.contains("?: report.selectedPosition"))
        val builder = source.substringAfter("object AiChatContextBuilder")
            .substringBefore("private class RemoteAiChatClient")
        assertTrue(builder.contains("judgementMode == AiJudgementMode.INDEPENDENT"))
        assertTrue(builder.contains("raw-history-v1"))
        assertTrue(builder.contains("if (independent)"))
        assertTrue(builder.contains("else {\n                    put(\n                        \"verified_position_statistics\""))
    }
}
''',
        encoding="utf-8",
    )

    NOTES.write_text(
        '''# 天机 v5.7.1 AI 真独立修正版

## 修复原因

此前虽然没有直接把本机六码写进 AI 提示词，但正式预测仍向 AI 提供了本机预计算的频次、遗漏、后继转移和趋势统计，并要求模型评分与这些统计方向一致；对话未指定名次时还会默认使用本机模型选中的名次作为学习入口。因此不同 AI 容易长期复刻本机模型结果。

## 本次修复

- 正式 AI 预测改为严格原始历史输入：只发送真实期开奖原始记录、目标期和必要元数据。
- 不再向正式 AI 注入本机名次、六码、七码、概率矩阵、本机因子权重或本机预计算统计。
- 独立对话不再默认使用本机模型选中的名次。
- 独立对话只读取原始历史；只有用户主动切换“参考本机”或“反向审计”时，才会明确附带本机参考与核验统计。
- 60期与120期模式现在分别发送真实60/120期原始记录，不再只发送24期原始数据。
- 增加自动化防回归测试，阻止以后再次把本机结果或统计偷偷注入独立 AI。

独立分析后偶尔与本机结果自然重合属于正常现象；本版本不通过强制反选制造“看起来不同”的假独立。

- versionName：5.7.1
- versionCode：38

> 随机开奖不可可靠预测。本项目用于统计实验、记录和真实前向验证，不承诺准确率、收益或必中。
''',
        encoding="utf-8",
    )


def verify_contract() -> None:
    formal = AI_ANALYSIS.read_text(encoding="utf-8")
    chat = AI_CHAT.read_text(encoding="utf-8")
    payload = formal.split("private fun analysisPayload(", 1)[1].split(
        "private fun isRetriableModelOutput", 1,
    )[0]
    if "verified_position_statistics" in payload or "report.selectedPosition" in payload:
        raise RuntimeError("formal prompt still leaks native engineered data")
    if "raw_draws_oldest_to_newest" not in payload:
        raise RuntimeError("formal prompt does not contain raw history")
    if "?: report.selectedPosition" in chat:
        raise RuntimeError("chat still defaults to native selected position")


if __name__ == "__main__":
    patch_formal_prediction()
    patch_chat_analysis()
    patch_version_and_docs()
    verify_contract()
    print("AI true-independence patch applied successfully")
