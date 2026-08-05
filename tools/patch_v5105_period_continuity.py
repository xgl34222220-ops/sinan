#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
controller = root / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt"
notes = root / "RELEASE_NOTES_v5.10.5.md"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, got {count}: {old[:160]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

replace_once(
    controller,
    '''        val rankScopedMessages = if (intent.usesLotteryContext) {
            AiPositionScope.filterPrevious(plan.messages, activePosition)
        } else {
            plan.messages
        }
        val previousMessages = if (intent == AiChatIntent.FREE_CHAT) {
            rankScopedMessages.filter { it.role != AiChatRole.SYSTEM }.takeLast(16)
        } else {
            rankScopedMessages
        }
''',
    '''        val continuity = if (intent.usesLotteryContext) {
            AiConversationContinuity.resolve(
                question = text,
                activePosition = activePosition,
                currentTargetPeriod = report.targetPeriod,
                latestApiPeriod = snapshot.latest.period,
                messages = plan.messages,
                candidates = session.candidates,
            )
        } else {
            null
        }
        val previousMessages = if (intent == AiChatIntent.FREE_CHAT) {
            plan.messages.filter { it.role != AiChatRole.SYSTEM }.takeLast(16)
        } else {
            continuity?.previousMessages.orEmpty()
        }
''',
)
replace_once(
    controller,
    '''                    memorySummary = if (intent.usesLotteryContext && activePosition != null) {
                        ""
                    } else {
                        session.memorySummary
                    },
''',
    '''                    memorySummary = if (intent.usesLotteryContext) {
                        continuity?.relevantFeedback.orEmpty()
                    } else {
                        session.memorySummary
                    },
''',
)
replace_once(
    controller,
    '''                        "以下是客户端保存的长期策略记忆。它包含用户明确反馈、前期候选和真实开奖核验；必须与adaptive_learning一起用于下一期纠偏，但不得伪称供应商模型已在后台训练：\\n$memorySummary",
''',
    '''                        "以下内容仅是与用户当前问题直接相关、且已按期号核验的结算记录。只有这里明确给出的记录才能称为上次或前一期；没有这段内容时不得主动翻旧账。adaptive_learning只是同名次长期汇总，不代表最近一期结果：\\n$memorySummary",
''',
)
replace_once(
    controller,
    '''                    "adaptive_learning由客户端根据此前真实前向开奖结果逐期更新，包含学习期数、命中率、连续未中、六类因子权重和最近策略变化。" +
                    "上一期未中或连续未中时，必须重新检查因子是否失效，并明确说明本期改变了什么；禁止机械复制旧候选。" +
''',
    '''                    "adaptive_learning由客户端根据同彩种、同名次的真实前向开奖结果累计更新，只能作为长期汇总信号。除非上下文明确提供与当前问题直接相关的已结算记录，否则不得把历史未中说成上一期，也不得主动复盘几天前的预测。若提供了紧邻当前目标期的未中记录，必须比较当时候选与实际号码，说明哪些信号没有区分力以及本期如何调整；禁止机械复制旧候选。" +
''',
)

text = notes.read_text(encoding="utf-8")
insert = "- 对话连续性改为按期号判断：只有紧邻当前目标期的已结算预测，或用户明确要求复盘的历史记录，才会进入本轮上下文；隔几天重新问同一名次会直接按当前 API 数据重新分析。\n"
marker = "- 旧名次消息仍保留在聊天页面和历史记录中，但不会再次发送给模型参与新名次分析。\n"
if insert not in text:
    if marker not in text:
        raise SystemExit("release notes marker missing")
    text = text.replace(marker, marker + insert, 1)
notes.write_text(text, encoding="utf-8")
print("patched period-aware continuity")
