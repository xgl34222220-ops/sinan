#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
analysis = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
gradle = ROOT / "app/build.gradle.kts"
readme = ROOT / "README.md"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected 1 match, got {count}: {old[:140]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1. Add phase timing to streamed responses so slow runs can be diagnosed.
replace_once(
    analysis,
    '''        var usage: JSONObject? = null
        var lastProgressAt = 0L
''',
    '''        var usage: JSONObject? = null
        var lastProgressAt = 0L
        var firstReasoningMs = -1L
        var firstContentMs = -1L
''',
)
replace_once(
    analysis,
    '''            if (reasoningPart.isNotEmpty()) {
                reasoning.append(reasoningPart)
                report("模型正在推理 · 已收到 ${reasoning.length} 个推理字符")
            }
            if (contentPart.isNotEmpty()) {
                content.append(contentPart)
''',
    '''            if (reasoningPart.isNotEmpty()) {
                if (firstReasoningMs < 0L) firstReasoningMs = System.currentTimeMillis() - startedAtMs
                reasoning.append(reasoningPart)
                report("模型正在推理 · 已收到 ${reasoning.length} 个推理字符")
            }
            if (contentPart.isNotEmpty()) {
                if (firstContentMs < 0L) firstContentMs = System.currentTimeMillis() - startedAtMs
                content.append(contentPart)
''',
)
replace_once(
    analysis,
    '''            .apply { usage?.let { put("usage", it) } }
    }

    private fun JSONObject.extractContent(): String = optJSONArray("choices")
''',
    '''            .apply {
                usage?.let { put("usage", it) }
                put("_tianji_first_reasoning_ms", firstReasoningMs)
                put("_tianji_first_content_ms", firstContentMs)
                put("_tianji_stream_finished_ms", System.currentTimeMillis() - startedAtMs)
            }
    }

    private fun JSONObject.streamPhaseSummary(): String {
        val firstReasoning = optLong("_tianji_first_reasoning_ms", -1L)
        val firstContent = optLong("_tianji_first_content_ms", -1L)
        val finished = optLong("_tianji_stream_finished_ms", -1L)
        if (finished < 0L) return ""
        fun seconds(value: Long): String = String.format(java.util.Locale.US, "%.1fs", value / 1000.0)
        return when {
            firstReasoning >= 0L && firstContent >= firstReasoning ->
                "首个推理 ${seconds(firstReasoning)} · 推理阶段 ${seconds(firstContent - firstReasoning)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            firstContent >= 0L ->
                "首个结果 ${seconds(firstContent)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            else -> "响应总耗时 ${seconds(finished)}"
        }
    }

    private fun JSONObject.extractContent(): String = optJSONArray("choices")
''',
)

# 2. Record the phase summary in the saved execution note.
replace_once(
    analysis,
    '''                    if (continuedConversation) append(" · 同一对话补全结果")
                    append(" · ${response.tokenBudgetLabel}")
''',
    '''                    if (continuedConversation) append(" · 同一对话补全结果")
                    response.json.streamPhaseSummary().takeIf(String::isNotBlank)?.let {
                        append(" · $it")
                    }
                    append(" · ${response.tokenBudgetLabel}")
''',
)

# 3. Add a compact factor-weight contract to structured output.
replace_once(
    analysis,
    '''        val properties = JSONObject()
            .put(
                "position",
                JSONObject().put("type", "integer").put("minimum", 1).put("maximum", 10),
            )
            .put("scores", scoreArray)
        val required = mutableListOf("position", "scores")
        if (explainOutput) {
            properties
''',
    '''        val properties = JSONObject()
            .put(
                "position",
                JSONObject().put("type", "integer").put("minimum", 1).put("maximum", 10),
            )
            .put("scores", scoreArray)
        val required = mutableListOf("position", "scores")
        if (explainOutput) {
            val factorWeights = JSONObject()
                .put("type", "array")
                .put("items", JSONObject().put("type", "number").put("minimum", 0).put("maximum", 1))
                .put("minItems", 5)
                .put("maxItems", 5)
            properties
                .put("factor_weights", factorWeights)
''',
)
replace_once(
    analysis,
    '''                    "calculation_summary",
                    JSONObject().put("type", "string").put("maxLength", 800),
''',
    '''                    "calculation_summary",
                    JSONObject().put("type", "string").put("maxLength", 220),
''',
)
replace_once(
    analysis,
    '''                    "position_reason",
                    JSONObject().put("type", "string").put("maxLength", 500),
''',
    '''                    "position_reason",
                    JSONObject().put("type", "string").put("maxLength", 180),
''',
)
replace_once(
    analysis,
    '''                    "candidate_reason",
                    JSONObject().put("type", "string").put("maxLength", 800),
''',
    '''                    "candidate_reason",
                    JSONObject().put("type", "string").put("maxLength", 220),
''',
)
replace_once(
    analysis,
    '''                    "uncertainty",
                    JSONObject().put("type", "string").put("maxLength", 500),
''',
    '''                    "uncertainty",
                    JSONObject().put("type", "string").put("maxLength", 160),
''',
)
replace_once(
    analysis,
    '''            required += listOf(
                "calculation_summary",
''',
    '''            required += listOf(
                "factor_weights",
                "calculation_summary",
''',
)

# 4. Audit explanation language and multi-factor quality without discarding a valid prediction.
replace_once(
    analysis,
    '''        val matrixConcentration = (1.0 - entropy / kotlin.math.ln(10.0)).coerceIn(0.0, 1.0)
        return AiForecast(
''',
    '''        val matrixConcentration = (1.0 - entropy / kotlin.math.ln(10.0)).coerceIn(0.0, 1.0)
        val calculation = AiExplanationPolicy.concise(json.optString("calculation_summary"), 220)
        val positionEvidence = AiExplanationPolicy.concise(json.optString("position_reason"), 180)
        val candidateEvidence = AiExplanationPolicy.concise(json.optString("candidate_reason"), 220)
        val uncertainty = AiExplanationPolicy.concise(json.optString("uncertainty"), 160)
        val factorAudit = AiExplanationPolicy.auditWeights(json.doubleList("factor_weights"))
        val explanationAccepted = factorAudit.validMultiFactor && AiExplanationPolicy.isChineseExplanation(
            calculation,
            positionEvidence,
            candidateEvidence,
            uncertainty,
        )
        return AiForecast(
''',
)
old_analysis = '''            analysis = buildString {
                val calculation = json.optString("calculation_summary").trim()
                val positionEvidence = json.optString("position_reason").trim()
                val candidateEvidence = json.optString("candidate_reason").trim()
                append("计算摘要：")
                append(
                    calculation.ifBlank {
                        AiFactEngine.verifiedSummary(history, position - 1, top6)
                    },
                )
                if (positionEvidence.isNotBlank()) append("\\n名次依据：$positionEvidence")
                if (candidateEvidence.isNotBlank()) append("\\n候选依据：$candidateEvidence")
            }.take(1_800),
            riskNote = buildString {
                val uncertainty = json.optString("uncertainty").trim()
                if (uncertainty.isNotBlank()) append("AI 不确定性：$uncertainty ")
                append("统计由本机对刚同步的开奖接口历史逐期复核；随机开奖无法保证准确率或盈利。")
                if (lowBoundarySeparation) append(" 本次第6与第7候选差距较小，候选边界稳定性偏低。")
            }.take(900),
'''
new_analysis = '''            analysis = buildString {
                if (explanationAccepted) {
                    append("多因素权重：${factorAudit.weightSummary}")
                    append("\\n计算摘要：$calculation")
                    append("\\n名次依据：$positionEvidence")
                    append("\\n候选依据：$candidateEvidence")
                } else {
                    append("说明审计：AI 已返回有效预测矩阵，但说明未满足“简体中文且至少三类因素共同参与”的协议，已隐藏不可核验说明。")
                    append("\\n本机复核：")
                    append(AiFactEngine.verifiedSummary(history, position - 1, top6))
                }
            }.take(1_200),
            riskNote = buildString {
                if (explanationAccepted) append("AI 不确定性：$uncertainty ")
                else append("AI 说明未通过中文多因素审计；预测矩阵仍保留并进入真实前向验证。 ")
                append("统计由本机对刚同步的开奖接口历史逐期复核；随机开奖无法保证准确率或盈利。")
                if (lowBoundarySeparation) append(" 本次第6与第7候选差距较小，候选边界稳定性偏低。")
            }.take(700),
'''
replace_once(analysis, old_analysis, new_analysis)

# 5. Tighten the prompt: Chinese, compact output, no one/two-factor shortcut.
replace_once(
    analysis,
    '''            put(
                "position_selection_rule",
                "必须先横向比较position 1至10的全部已核验统计，再选择证据最充分的一个名次。不得默认、照抄或偏向position=1；名次选择必须由本次数据决定。",
            )
''',
    '''            put(
                "position_selection_rule",
                "必须先横向比较position 1至10的全部已核验统计，再选择证据最充分的一个名次。不得默认、照抄或偏向position=1；名次选择必须由本次数据决定。",
            )
            put(
                "multi_factor_rule",
                "禁止使用单一指标或简单的遗漏+转移未加权求和。factor_weights固定顺序为[近20期频次,近60期频次,当前遗漏,后继转移,趋势稳定性]，归一化后至少3项权重>=0.08，任何一项不得超过0.65。scores必须与这些权重和已核验统计方向一致。",
            )
            put(
                "output_rule",
                "所有说明字段必须使用简体中文并保持精简；JSON键按position、scores、factor_weights、calculation_summary、position_reason、candidate_reason、uncertainty顺序输出。完成真实推理后立即输出JSON，不要写英文、Markdown、长篇方法教学或逐期复述。",
            )
''',
)
replace_once(
    analysis,
    '''                    .put("position", "integer 1..10")
                    .put("scores", "array of exactly 10 non-negative raw scores for numbers 1..10; keep at least 6 decimal places; do not round values into ties")
                    .put("calculation_summary", "concise auditable description of statistical method; do not expose hidden chain of thought")
                    .put("position_reason", "cite the verified facts that made this position stronger than the other nine")
                    .put("candidate_reason", "cite verified frequency, omission, transition or drift evidence behind the score ordering")
                    .put("uncertainty", "state weak evidence, conflicts and instability without claiming certainty"),
''',
    '''                    .put("position", "1至10的整数")
                    .put("scores", "按号码1至10排列的10项非负原始评分，每项至少6位小数，不得四舍五入成并列")
                    .put("factor_weights", "固定5项权重：[近20期频次,近60期频次,当前遗漏,后继转移,趋势稳定性]")
                    .put("calculation_summary", "不超过100个汉字，说明多因素如何共同形成评分；禁止单一公式")
                    .put("position_reason", "不超过80个汉字，说明该名次相对其他九个名次的多因素优势")
                    .put("candidate_reason", "不超过100个汉字，说明六码排序的主要证据与冲突")
                    .put("uncertainty", "不超过70个汉字，说明样本、漂移和冲突风险"),
''',
)

replace_once(
    analysis,
    '''        const val FINALIZE_JSON_PROMPT =
            "你已经完成上一轮统计分析。不要重新计算、不要复述推理过程。只根据上一轮结论立即输出一个JSON对象，必须包含position、10项scores、calculation_summary、position_reason、candidate_reason和uncertainty。"
        const val SYSTEM_PROMPT = """你是独立概率排序模型。输入含真实开奖和由客户端逐期计算并核验的统计表，本地盲测候选已被刻意隐藏。遗漏、近20/60期次数、后继转移和大小连开必须以 verified_position_statistics 为事实来源，原始历史仅用于交叉核验。你必须先比较position 1至10，再选择证据最充分的名次；不得默认第1名或偏向固定名次。随后按号码1至10顺序输出10个非负原始评分，每项至少保留6位小数，六码、七码和最终排序由客户端从scores确定。除position与scores外，还必须返回calculation_summary、position_reason、candidate_reason和uncertainty，让用户看见可核验的计算依据；这些字段只写简洁结论和使用了哪些已核验统计，不得输出隐藏思维链、逐字内心推理或Markdown。只输出required_json_schema规定的JSON，不承诺准确率、盈利或必中。"""
''',
    '''        const val FINALIZE_JSON_PROMPT =
            "你已经完成上一轮统计分析。不要重新计算、不要复述推理过程。立即用简体中文输出一个紧凑JSON对象，键顺序必须为position、scores、factor_weights、calculation_summary、position_reason、candidate_reason、uncertainty。factor_weights固定对应近20频次、近60频次、遗漏、后继转移、趋势稳定性，至少三项有效参与。"
        const val SYSTEM_PROMPT = """你是独立概率排序模型。输入含真实开奖和由客户端逐期计算并核验的统计表，本地盲测候选已被刻意隐藏。遗漏、近20/60期次数、后继转移和趋势稳定性必须以 verified_position_statistics 为事实来源，原始历史仅用于交叉核验。你必须先比较position 1至10，再选择证据最充分的名次；不得默认第1名或偏向固定名次。禁止只使用单一指标，禁止使用“遗漏+转移次数”的简单未加权求和；必须让近20频次、近60频次、遗漏、后继转移、趋势稳定性中至少三类因素共同参与，任何一类归一化权重不得超过0.65。随后按号码1至10顺序输出10个非负原始评分，每项至少保留6位小数，六码、七码和最终排序由客户端从scores确定。所有解释必须使用简体中文且精简，只说明可核验统计、因素权重、证据冲突和不确定性，不得输出隐藏思维链、英文、Markdown、长篇教学或逐期复述。JSON键顺序必须为position、scores、factor_weights、calculation_summary、position_reason、candidate_reason、uncertainty。只输出required_json_schema规定的JSON，不承诺准确率、盈利或必中。"""
''',
)

# 6. Version and release notes.
replace_once(gradle, 'versionCode = 29\n        versionName = "5.5.4"', 'versionCode = 30\n        versionName = "5.5.5"')
replace_once(readme, '- 版本：5.5.4', '- 版本：5.5.5')
replace_once(
    readme,
    '## v5.5.3 模型上限与透明计算',
    '''## v5.5.5 中文多因素审计与结果提速

- AI 说明固定使用简体中文，英文或缺失说明不会再直接展示。
- 新增五因素权重协议：近20期频次、近60期频次、遗漏、后继转移、趋势稳定性；至少三类因素共同参与。
- 禁止“遗漏+转移次数”这类单一或双因素未加权捷径；说明未通过审计时保留预测矩阵，但改用本机核验摘要。
- 结构化说明字段大幅缩短，并要求核心预测字段优先输出，减少推理完成后等待长篇说明的时间。
- 记录首个推理、推理阶段和结果阶段耗时，便于区分模型排队、真实推理和结果生成的慢点。
- 不降低模型 Token 上限、不关闭 thinking、不缩短60/120期历史。

## v5.5.3 模型上限与透明计算''',
)

print("v5.5.5 auditable-output patch applied")
