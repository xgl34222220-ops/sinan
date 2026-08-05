#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt"
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one match, got {count}: {old[:100]!r}")
    text = text.replace(old, new, 1)


replace_once(
    '''        val wantsPrediction = intent.wantsPrediction
        AiChatProtocol.wantsPrediction(if (wantsPrediction) question else "")
''',
    '''        val wantsPrediction = intent.wantsPrediction
        val expectedTargetPeriod = if (intent.usesLotteryContext) report.targetPeriod.trim() else ""
        AiChatProtocol.wantsPrediction(if (wantsPrediction) question else "")
''',
)

replace_once(
    '''            judgementMode = judgementMode,
            intent = intent,
        )
''',
    '''            judgementMode = judgementMode,
            intent = intent,
            expectedTargetPeriod = expectedTargetPeriod,
        )
''',
)

replace_once(
    '''                                "上一请求没有产生最终正文。请立即基于同一份原始历史完成回答，不要输出思考过程，并按原要求在正文后追加完整 tianji_forecast。"
''',
    '''                                "上一请求没有产生最终正文。当前唯一目标期为${expectedTargetPeriod}期。请立即基于同一份原始历史完成回答，不要输出思考过程，并按原要求在正文后追加完整 tianji_forecast；不得沿用旧期号。"
''',
)

replace_once(
    '''        val prediction = if (wantsPrediction) AiChatProtocol.parsePrediction(rawContent) else null
        val content = AiChatProtocol.visibleText(rawContent, prediction != null)
        publisher.finish(content)
''',
    '''        val prediction = if (wantsPrediction) AiChatProtocol.parsePrediction(rawContent) else null
        val content = AiTargetPeriodGuard.reconcilePredictionText(
            text = AiChatProtocol.visibleText(rawContent, prediction != null),
            expectedTargetPeriod = expectedTargetPeriod,
            isPrediction = prediction != null,
        )
        publisher.finish(content)
''',
)

replace_once(
    '''        judgementMode: AiJudgementMode,
        intent: AiChatIntent,
    ): JSONArray = JSONArray().apply {
''',
    '''        judgementMode: AiJudgementMode,
        intent: AiChatIntent,
        expectedTargetPeriod: String,
    ): JSONArray = JSONArray().apply {
''',
)

replace_once(
    '''            put(JSONObject().put("role", role).put("content", message.content))
        }
        put(JSONObject().put("role", "user").put("content", question))
''',
    '''            put(
                JSONObject()
                    .put("role", role)
                    .put(
                        "content",
                        AiTargetPeriodGuard.contextualizePreviousMessage(
                            message = message,
                            expectedTargetPeriod = expectedTargetPeriod,
                        ),
                    ),
            )
        }
        if (intent.usesLotteryContext && expectedTargetPeriod.isNotBlank()) {
            put(
                JSONObject()
                    .put("role", "system")
                    .put(
                        "content",
                        AiTargetPeriodGuard.currentRequestInstruction(expectedTargetPeriod),
                    ),
            )
        }
        val currentQuestion = if (intent.usesLotteryContext && expectedTargetPeriod.isNotBlank()) {
            "【当前唯一目标期：${expectedTargetPeriod}期】\\n$question"
        } else {
            question
        }
        put(JSONObject().put("role", "user").put("content", currentQuestion))
''',
)

path.write_text(text, encoding="utf-8")
print("patched", path)
