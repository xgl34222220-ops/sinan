#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
controller = root / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt"
notes = root / "RELEASE_NOTES_v5.10.5.md"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, got {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

replace_once(
    controller,
    '                AiChatIntent.LOTTERY_ANALYSIS -> "正在读取开奖历史…"\n',
    '                AiChatIntent.LOTTERY_ANALYSIS -> "正在读取${snapshot.lottery.displayName}开奖 API…"\n',
)
replace_once(
    controller,
    '        val content = AiVerifiedAnswerComposer.compose(reconciled, verifiedFacts, intent)\n',
    '        val content = AiVerifiedAnswerComposer.compose(\n'
    '            modelText = reconciled,\n'
    '            facts = verifiedFacts,\n'
    '            intent = intent,\n'
    '            question = question,\n'
    '        )\n',
)
replace_once(
    controller,
    '                        "以下是当前彩种开奖接口历史、必要元数据与客户端逐期核验事实。独立模式不包含本机候选、模型选中名次、概率矩阵或因子权重；verified_position_facts只来自当前彩种原始历史，必须原样遵守。参考/反向模式才会额外附带native_model_reference：\\n${context}",\n',
    '                        "以下是当前彩种上游开奖 API 返回的历史与必要元数据。独立模式不包含本机候选、模型选中名次、概率矩阵或因子权重；verified_position_facts由程序直接从本次 API 历史逐期计算，必须原样遵守。参考/反向模式才会额外附带native_model_reference：\\n${context}",\n',
)
replace_once(
    controller,
    '                        "当前本轮唯一分析名次为第${positionScope + 1}名。客户端已排除其他名次的旧分析上下文；保持自然对话，但不得沿用、复制或混合此前其他名次的数据与结论。verified_position_facts是本轮唯一数值事实源。",\n',
    '                        "用户当前这句话指定分析第${positionScope + 1}名，它的优先级高于之前所有名次。保持正常自然对话；之前其他名次只是聊天历史，不得沿用其数据或结论。当前上游开奖 API 数据和verified_position_facts是本轮唯一事实源。",\n',
)
replace_once(
    controller,
    '                    "所有模式中的期号、最近序列、20/60/120期次数和遗漏只能引用verified_position_facts。禁止自行重算、补全、修改或生成另一套统计；正文只做定性解释，避免重复整张数字表。不得虚构期号、次数或数据来源。" +\n',
    '                    "所有模式中的期号、最近序列、20/60/120期次数和遗漏只能引用当前上游开奖 API 对应的verified_position_facts。用户问什么就回答什么，不要擅自补充固定模板、其他名次、候选号码或另一套统计。不得虚构期号、次数或数据来源。" +\n',
)

text = notes.read_text(encoding="utf-8")
text = text.replace("App 从当前开奖快照逐期计算并固定展示", "程序从当前彩种上游开奖 API 响应逐期计算并按需展示")
text = text.replace("AI 只负责解释、比较和候选排序，无权改写期号、序列、次数或遗漏；模型生成的冲突统计行会被客户端移除。", "AI 可自然解释、比较和预测，但期号、序列、次数与遗漏只能来自当前彩种上游开奖 API；用户问什么就回答什么，不强塞固定报告模板。")
notes.write_text(text, encoding="utf-8")
print("patched current-question semantics")
