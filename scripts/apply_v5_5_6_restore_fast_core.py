#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected 1 match, got {count}: {old[:140]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


analysis = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
reasoning = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiReasoning.kt"

# AUTO must use the provider/model default. It must not silently become forced high reasoning.
replace_once(
    reasoning,
    '''            AiReasoningMode.AUTO -> when (protocol) {
                AiReasoningProtocol.DEEPSEEK -> AiReasoningDecision(
                    protocol, preference, true, true, true, "high",
                    "${protocol.label} · 自动思考",
                )
                else -> AiReasoningDecision(
                    protocol, preference, true, false, false, null,
                    "${protocol.label} · 模型默认",
                )
            }
''',
    '''            AiReasoningMode.AUTO -> AiReasoningDecision(
                protocol, preference, true, false, false, null,
                "${protocol.label} · 模型默认",
            )
''',
)

# Restore the documented meaning of the low/fast option.
replace_once(
    reasoning,
    '''            AiReasoningMode.LOW -> when (protocol) {
                AiReasoningProtocol.DEEPSEEK -> AiReasoningDecision(
                    protocol, preference, true, true, true, "high",
                    "${protocol.label} · 省时思考",
                )
                AiReasoningProtocol.ENABLE_THINKING -> AiReasoningDecision(
                    protocol, preference, true, true, false, null,
                    "${protocol.label} · 已关闭推理",
                )
''',
    '''            AiReasoningMode.LOW -> when (protocol) {
                AiReasoningProtocol.DEEPSEEK,
                AiReasoningProtocol.ENABLE_THINKING -> AiReasoningDecision(
                    protocol, preference, true, true, false, null,
                    "${protocol.label} · 已关闭可控推理",
                )
''',
)

# Capability testing must not secretly launch a second forced-high request for AUTO profiles.
replace_once(
    analysis,
    '''        val reasoningResponse = if (highDecision.supported && !baseDecision.expectsReasoning) runCatching {''',
    '''        val reasoningResponse = if (
            config.reasoningMode == AiReasoningMode.HIGH &&
            highDecision.supported &&
            !baseDecision.expectsReasoning
        ) runCatching {''',
)

# Both the first response and same-conversation completion only need the core prediction JSON.
old_explain = '''                jsonOutput = true,
                explainOutput = true,
                streamResponse = true,'''
text = analysis.read_text(encoding="utf-8")
if text.count(old_explain) != 2:
    raise RuntimeError(f"{analysis}: expected 2 explainOutput matches, got {text.count(old_explain)}")
analysis.write_text(
    text.replace(
        old_explain,
        '''                jsonOutput = true,
                explainOutput = false,
                streamResponse = true,''',
    ),
    encoding="utf-8",
)

# Remove the instructions that expanded a small ranking task into a long report.
replace_once(
    analysis,
    '''            put("reasoning_efficiency_rule", AiPromptCompactor.REASONING_RULE)
            put("compact_draw_format", AiPromptCompactor.FORMAT)
''',
    '''            put("compact_draw_format", AiPromptCompactor.FORMAT)
            put(
                "response_priority",
                "完成名次与10项评分后立即输出JSON。不要解释方法、不要逐期复述、不要输出思维过程。",
            )
''',
)

replace_once(
    analysis,
    '''            put(
                "multi_factor_rule",
                "禁止使用单一指标或简单的遗漏+转移未加权求和。factor_weights固定顺序为[近20期频次,近60期频次,当前遗漏,后继转移,趋势稳定性]，归一化后至少3项权重>=0.08，任何一项不得超过0.65。scores必须与这些权重和已核验统计方向一致。",
            )
            put(
                "output_rule",
                "所有说明字段必须使用简体中文并保持精简；JSON键按position、scores、factor_weights、calculation_summary、position_reason、candidate_reason、uncertainty顺序输出。完成真实推理后立即输出JSON，不要写英文、Markdown、长篇方法教学或逐期复述。",
            )
''',
    '''            put(
                "scoring_rule",
                "综合已核验频次、遗漏、后继转移和趋势信息完成排序；不要把任何单项指标机械当成必中依据。",
            )
''',
)

replace_once(
    analysis,
    '''                JSONObject()
                    .put("position", "1至10的整数")
                    .put("scores", "按号码1至10排列的10项非负原始评分，每项至少6位小数，不得四舍五入成并列")
                    .put("factor_weights", "固定5项权重：[近20期频次,近60期频次,当前遗漏,后继转移,趋势稳定性]")
                    .put("calculation_summary", "不超过100个汉字，说明多因素如何共同形成评分；禁止单一公式")
                    .put("position_reason", "不超过80个汉字，说明该名次相对其他九个名次的多因素优势")
                    .put("candidate_reason", "不超过100个汉字，说明六码排序的主要证据与冲突")
                    .put("uncertainty", "不超过70个汉字，说明样本、漂移和冲突风险"),
''',
    '''                JSONObject()
                    .put("position", "1至10的整数")
                    .put("scores", "按号码1至10排列的10项非负原始评分，每项至少6位小数，不得四舍五入成并列"),
''',
)

# Same-conversation completion is core-only and does not re-run the analysis.
replace_once(
    analysis,
    '''        const val FINALIZE_JSON_PROMPT =
            "你已经完成上一轮统计分析。不要重新计算、不要复述推理过程。立即用简体中文输出一个紧凑JSON对象，键顺序必须为position、scores、factor_weights、calculation_summary、position_reason、candidate_reason、uncertainty。factor_weights固定对应近20频次、近60频次、遗漏、后继转移、趋势稳定性，至少三项有效参与。"
        const val SYSTEM_PROMPT = """你是独立概率排序模型。输入含真实开奖和由客户端逐期计算并核验的统计表，本地盲测候选已被刻意隐藏。遗漏、近20/60期次数、后继转移和趋势稳定性必须以 verified_position_statistics 为事实来源，原始历史仅用于交叉核验。你必须先比较position 1至10，再选择证据最充分的名次；不得默认第1名或偏向固定名次。禁止只使用单一指标，禁止使用“遗漏+转移次数”的简单未加权求和；必须让近20频次、近60频次、遗漏、后继转移、趋势稳定性中至少三类因素共同参与，任何一类归一化权重不得超过0.65。随后按号码1至10顺序输出10个非负原始评分，每项至少保留6位小数，六码、七码和最终排序由客户端从scores确定。所有解释必须使用简体中文且精简，只说明可核验统计、因素权重、证据冲突和不确定性，不得输出隐藏思维链、英文、Markdown、长篇教学或逐期复述。JSON键顺序必须为position、scores、factor_weights、calculation_summary、position_reason、candidate_reason、uncertainty。只输出required_json_schema规定的JSON，不承诺准确率、盈利或必中。"""
''',
    '''        const val FINALIZE_JSON_PROMPT =
            "你已经完成分析。不要重新计算或解释，立即只输出包含position与10项scores的紧凑JSON。"
        const val SYSTEM_PROMPT = """你是独立概率排序模型。输入包含真实开奖和客户端逐期核验的统计，本地候选已隐藏。先比较position 1至10，选择证据较充分的一个名次；不得默认固定名次。随后按号码1至10顺序给出10个非负原始scores，每项至少保留6位小数，避免并列。六码、七码和说明均由客户端根据scores与真实历史生成。完成内部分析后立即只输出position与scores的JSON，不要解释、不要Markdown、不要逐期复述，也不要输出思维过程。"""
''',
)

print("v5.5.6 lightweight core prediction restored")
