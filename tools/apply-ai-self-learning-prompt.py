from __future__ import annotations

from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing anchor: {label}")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# 1. Build a compact, auditable self-learning evidence package and pass it to
#    the remote AI BEFORE inference. It contains no native-model final answer.
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/ContinualRemoteAiAnalyzer.kt"
text = read(path)
text = replace_once(
    text,
    "import com.tianji.probabilitylab.nativev4.model.ForecastReport\n",
    "import com.tianji.probabilitylab.nativev4.model.ForecastReport\nimport org.json.JSONArray\nimport org.json.JSONObject\n",
    "ContinualRemoteAiAnalyzer imports",
)
text = replace_once(
    text,
    """        val plan = AiContinualForecastEngine.buildPlan(snapshot.history, profiles)\n        val remote = delegate.analyze(config, snapshot, report, onProgress)\n        onProgress(\n            \"AI旁路评审已返回，正在按固定六码真实前向成绩确定最终名次\",\n            System.currentTimeMillis() - started,\n        )\n""",
    """        val plan = AiContinualForecastEngine.buildPlan(snapshot.history, profiles)\n        val selfLearningEvidence = AiContinualForecastEngine.promptEvidence(plan)\n        onProgress(\n            \"AI自学习证据已注入：仅使用该AI自己的十名次结算证据，不包含本机预测答案\",\n            System.currentTimeMillis() - started,\n        )\n        val remote = delegate.analyze(\n            config = config,\n            snapshot = snapshot,\n            report = report,\n            onProgress = onProgress,\n            selfLearningEvidence = selfLearningEvidence,\n        )\n        onProgress(\n            \"AI自学习评审已返回，正在按固定六码真实前向成绩做二次校准\",\n            System.currentTimeMillis() - started,\n        )\n""",
    "pass self-learning evidence to remote",
)
insert_anchor = """    fun calibrate(\n        forecast: AiForecast,\n        plan: AiContinualForecastPlan,\n    ): AiForecast {\n"""
if insert_anchor not in text:
    raise SystemExit("missing calibrate anchor")
prompt_method = """    /**\n     * Evidence sent to the remote AI. It is deliberately restricted to the same AI profile's\n     * settled outcomes plus leakage-free walk-forward statistics. Native-model selections,\n     * candidates and probability matrices are never included.\n     */\n    fun promptEvidence(plan: AiContinualForecastPlan): JSONObject = JSONObject()\n        .put(\"schema\", \"tianji-ai-self-learning-v1\")\n        .put(\"target_pool\", TARGET_LABEL)\n        .put(\"target_numbers_internal\", JSONArray(TARGET_NUMBERS))\n        .put(\"random_baseline\", RANDOM_TARGET_RATE)\n        .put(\"history_size\", plan.historySize)\n        .put(\"gate_passed_positions\", plan.passedCount)\n        .put(\n            \"positions\",\n            JSONArray(plan.positions.map { evidence ->\n                JSONObject()\n                    .put(\"position\", evidence.position + 1)\n                    .put(\"validation_samples\", evidence.validationSamples)\n                    .put(\"target_hits\", evidence.targetHits)\n                    .put(\"shrinkage_target_hit_rate\", evidence.targetHitRate)\n                    .put(\"excess_over_random\", evidence.excessOverRandom)\n                    .put(\"average_binary_log_loss\", evidence.averageBinaryLogLoss)\n                    .put(\"max_miss_streak\", evidence.maxMissStreak)\n                    .put(\"current_miss_streak\", evidence.currentMissStreak)\n                    .put(\"current_target_probability\", evidence.targetProbability)\n                    .put(\"validation_score\", evidence.validationScore)\n                    .put(\"gate_passed\", evidence.gatePassed)\n                    .put(\"own_settled_samples\", evidence.learningProfile.settled)\n                    .put(\"own_settled_hit_rate\", evidence.learningProfile.top6Rate)\n                    .put(\n                        \"own_recent20_hit_rate\",\n                        evidence.learningProfile.recent20Top6Rate ?: JSONObject.NULL,\n                    )\n                    .put(\"own_profile_miss_streak\", evidence.learningProfile.missStreak)\n                    .put(\n                        \"own_long_term_factor_weights\",\n                        JSONArray(evidence.learningProfile.weights),\n                    )\n                    .put(\"own_last_learned_period\", evidence.learningProfile.lastLearnedPeriod)\n            }),\n        )\n        .put(\n            \"policy\",\n            \"这是该AI自身真实结算与开奖前滚动验证形成的弱先验，不是本机模型答案。\" +\n                \"当前最新原始开奖历史优先级最高；短期高于60%不得当作稳定规律，\" +\n                \"连续未中、对数损失变差或样本不足时必须主动降权。\",\n        )\n\n"""
text = text.replace(insert_anchor, prompt_method + insert_anchor, 1)
text = replace_once(
    text,
    """                forecast.executionNote +\n                    \" · 固定六码$TARGET_LABEL · 十名次二分类前向学习 · 最终第${selected.position + 1}名\"\n""",
    """                forecast.executionNote +\n                    \" · AI自学习证据已注入 · 与本机答案隔离 · 固定六码$TARGET_LABEL · \" +\n                    \"十名次二分类前向学习 · 最终第${selected.position + 1}名\"\n""",
    "final execution note",
)
write(path, text)


# ---------------------------------------------------------------------------
# 2. Remote AI accepts self-learning evidence as an optional fifth argument and
#    places it in the formal prompt while preserving strict native isolation.
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
text = read(path)
old_signature = """    fun analyze(\n        config: AiConfig,\n        snapshot: DrawSnapshot,\n        report: ForecastReport,\n        onProgress: (String, Long) -> Unit = { _, _ -> },\n    ): AiForecast {\n"""
new_signature = """    fun analyze(\n        config: AiConfig,\n        snapshot: DrawSnapshot,\n        report: ForecastReport,\n        onProgress: (String, Long) -> Unit = { _, _ -> },\n        selfLearningEvidence: JSONObject? = null,\n    ): AiForecast {\n"""
text = replace_once(text, old_signature, new_signature, "RemoteAiAnalyzer.analyze signature")
text = replace_once(
    text,
    """        // Strict independence protocol: the remote model receives only raw verified draws.\n        // AI-specific outcomes remain archived for diagnostics, but local engineered factors and\n        // native-model selections are deliberately excluded from the prediction prompt.\n        val userPrompt = analysisPayload(snapshot, report, historyLimit).toString()\n""",
    """        // Strict independence protocol: the remote model receives verified raw draws plus,\n        // when available, this same AI profile's settled learning evidence. Native-model selections,\n        // candidates, probability matrices and engineered native statistics remain excluded.\n        val userPrompt = analysisPayload(\n            snapshot = snapshot,\n            report = report,\n            historyLimit = historyLimit,\n            selfLearningEvidence = selfLearningEvidence,\n        ).toString()\n""",
    "formal prompt construction",
)
text = text.replace(
    "同一份原始历史任务",
    "同一份历史与AI自学习证据任务",
)
text = text.replace(
    "同一份原始历史关闭额外思考并收口一次",
    "同一份历史与AI自学习证据关闭额外思考并收口一次",
)
text = replace_once(
    text,
    """                    append(\" · 严格独立原始历史输入\")\n""",
    """                    if (selfLearningEvidence != null) {\n                        append(\" · 原始历史+AI自学习证据 · 严格隔离本机答案\")\n                    } else {\n                        append(\" · 严格独立原始历史输入\")\n                    }\n""",
    "execution input label",
)
old_payload_signature = """    private fun analysisPayload(\n        snapshot: DrawSnapshot,\n        report: ForecastReport,\n        historyLimit: Int,\n    ): JSONObject {\n"""
new_payload_signature = """    private fun analysisPayload(\n        snapshot: DrawSnapshot,\n        report: ForecastReport,\n        historyLimit: Int,\n        selfLearningEvidence: JSONObject? = null,\n    ): JSONObject {\n"""
text = replace_once(text, old_payload_signature, new_payload_signature, "analysisPayload signature")
text = replace_once(
    text,
    """            put(\"independence_protocol\", \"raw-history-v1\")\n            put(\n                \"input_isolation\",\n                \"客户端未提供本机模型选择的名次、六码、七码、概率矩阵、因子权重或预计算统计。不得猜测本机答案，也不得为了刻意不同而反向选择。\",\n            )\n""",
    """            put(\n                \"independence_protocol\",\n                if (selfLearningEvidence == null) \"raw-history-v1\"\n                else \"raw-history+ai-self-learning-v2\",\n            )\n            put(\n                \"input_isolation\",\n                if (selfLearningEvidence == null) {\n                    \"客户端未提供本机模型选择的名次、六码、七码、概率矩阵、因子权重或预计算统计。不得猜测本机答案，也不得为了刻意不同而反向选择。\"\n                } else {\n                    \"客户端绝不提供本机模型最终名次、六码、七码、概率矩阵或本机候选。附带的ai_self_learning_evidence只来自该AI配置自身已结算预测和开奖前滚动验证，可作为弱先验；不得猜测本机答案。\"\n                },\n            )\n            if (selfLearningEvidence != null) {\n                put(\"ai_self_learning_evidence\", selfLearningEvidence)\n                put(\n                    \"self_learning_policy\",\n                    \"必须读取该AI自己的结算样本、近期命中率、连续未中、二元对数损失和十名次滚动验证。当前原始开奖历史优先于旧学习档案；样本不足、连续未中扩大或损失变差时降低旧经验权重，不得机械复制上期名次。\",\n                )\n            }\n""",
    "independence and self-learning payload",
)
text = replace_once(
    text,
    """                        \"derive your own useful features directly from raw draws\",\n                        \"compare all ten positions for next-draw membership in fixed set 2/3/5/7/8/10 before selecting one\",\n                        \"use at least three independently justified signals; do not inherit client weights\",\n                        \"treat small samples and tiny differences as weak evidence\",\n                        \"produce your own ten-position score vector for the fixed target; never generate or replace the target numbers\",\n""",
    """                        \"derive current signals directly from raw draws; current history outranks stale learned priors\",\n                        \"compare all ten positions for next-draw membership in fixed set 2/3/5/7/8/10 before selecting one\",\n                        \"if ai_self_learning_evidence exists, use only this AI's settled evidence as a weak prior and explicitly penalize poor log-loss or expanding miss streaks\",\n                        \"use at least three independently justified signals; never infer or copy the native model answer\",\n                        \"treat small samples, tiny differences and short-term rates above the 60% random baseline as weak evidence\",\n                        \"produce your own ten-position score vector for the fixed target; never generate or replace the target numbers\",\n""",
    "analysis requirements",
)
old_system = """        const val SYSTEM_PROMPT = \"\"\"你是与客户端本机模型严格隔离的固定目标位置预测模型。固定目标永远是235780，其中0在1至10赛制中表示10，即内部集合2/3/5/7/8/10；绝对禁止生成、替换或优化这组六码。你只会收到按时间排序的真实开奖原始记录、目标期和必要元数据。唯一任务是比较第1至第10位置，判断下一期各位置的号码落入固定集合2/3/5/7/8/10的相对可能性，position返回最有证据的位置，scores按位置1至10给出10项非负原始评分。每个位置在随机排列下的固定六码命中基准是60%，短期高于60%不代表稳定优势；必须重视时序、状态转移、近期与长期一致性并对小样本降权。不得猜测、迎合或复制本机答案。正式预测有严格时间预算：禁止输出隐藏思维链、解释、Markdown或逐期复述；只输出position与scores的紧凑JSON。不得承诺准确率、盈利或必中。\"\"\"\n"""
new_system = """        const val SYSTEM_PROMPT = \"\"\"你是与客户端本机模型严格隔离的固定目标位置预测模型。固定目标永远是235780，其中0在1至10赛制中表示10，即内部集合2/3/5/7/8/10；绝对禁止生成、替换或优化这组六码。你会收到按时间排序的真实开奖原始记录、目标期、必要元数据，以及可选的ai_self_learning_evidence。该学习证据只允许来自当前AI配置自身已经开奖结算的历史表现和开奖前滚动验证，绝不包含客户端本机模型最终名次、六码、七码或概率答案。唯一任务是比较第1至第10位置，判断下一期各位置的号码落入固定集合2/3/5/7/8/10的相对可能性，position返回最有证据的位置，scores按位置1至10给出10项非负原始评分。当前最新原始历史优先级最高，自学习证据只是可质疑的弱先验；连续未中扩大、二元对数损失恶化、样本不足或学习档案陈旧时必须主动降权。每个位置在随机排列下的固定六码命中基准是60%，短期高于60%不代表稳定优势。不得猜测、迎合或复制本机答案，也不得为了刻意与本机不同而反向选择。正式预测有严格时间预算：禁止输出隐藏思维链、解释、Markdown或逐期复述；只输出position与scores的紧凑JSON。不得承诺准确率、盈利或必中。\"\"\"\n"""
text = replace_once(text, old_system, new_system, "SYSTEM_PROMPT")
write(path, text)


# ---------------------------------------------------------------------------
# 3. Make the change obvious in the AI screen, rather than only in internals.
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt"
text = read(path)
text = replace_once(
    text,
    """                detail = \"每次分析先强制同步开奖接口历史；首次有效结果开奖前冻结，目标期开奖后自动验证。\",\n""",
    """                detail = \"每次先同步真实开奖；AI会读取自己的已结算学习证据再预测，与本机最终答案严格隔离。\",\n""",
    "AI panel detail",
)
card_anchor = """        Spacer(Modifier.height(8.dp))\n        ReasoningBadge(result.reasoningState, result.reasoningTokens)\n"""
card_replacement = """        Spacer(Modifier.height(8.dp))\n        Text(\n            if (result.executionNote.contains(\"AI自学习证据已注入\")) {\n                \"AI 自学习已注入 · 与本机答案隔离\"\n            } else {\n                \"AI 独立历史分析 · 未注入自学习证据\"\n            },\n            color = if (result.executionNote.contains(\"AI自学习证据已注入\")) colors.green else colors.amber,\n            fontSize = 7.2.sp,\n            fontWeight = FontWeight.Bold,\n            modifier = Modifier\n                .clip(CircleShape)\n                .background(\n                    (if (result.executionNote.contains(\"AI自学习证据已注入\")) colors.green else colors.amber)\n                        .copy(alpha = 0.08f),\n                )\n                .padding(horizontal = 9.dp, vertical = 6.dp),\n        )\n        Spacer(Modifier.height(8.dp))\n        ReasoningBadge(result.reasoningState, result.reasoningTokens)\n"""
text = replace_once(text, card_anchor, card_replacement, "AI forecast learning badge")
write(path, text)


# ---------------------------------------------------------------------------
# 4. Update independence tests: AI's own evidence is allowed; native answers are not.
# ---------------------------------------------------------------------------
path = "app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiIndependenceContractTest.kt"
text = read(path)
text = replace_once(
    text,
    """    fun formalPredictionUsesRawHistoryWithoutNativeStatistics() {\n        val source = source(\"AiAnalysis.kt\")\n        val payload = source.substringAfter(\"private fun analysisPayload(\")\n            .substringBefore(\"private fun isRetriableModelOutput\")\n        assertTrue(payload.contains(\"raw_draws_oldest_to_newest\"))\n        assertTrue(payload.contains(\"raw-history-v1\"))\n        assertFalse(payload.contains(\"verified_position_statistics\"))\n        assertFalse(payload.contains(\"report.selectedPosition\"))\n        assertFalse(payload.contains(\"report.selected.top6\"))\n    }\n""",
    """    fun formalPredictionUsesRawHistoryAndOwnLearningWithoutNativeAnswers() {\n        val source = source(\"AiAnalysis.kt\")\n        val payload = source.substringAfter(\"private fun analysisPayload(\")\n            .substringBefore(\"private fun isRetriableModelOutput\")\n        assertTrue(payload.contains(\"raw_draws_oldest_to_newest\"))\n        assertTrue(payload.contains(\"raw-history+ai-self-learning-v2\"))\n        assertTrue(payload.contains(\"ai_self_learning_evidence\"))\n        assertTrue(payload.contains(\"self_learning_policy\"))\n        assertFalse(payload.contains(\"verified_position_statistics\"))\n        assertFalse(payload.contains(\"report.selectedPosition\"))\n        assertFalse(payload.contains(\"report.selected.top6\"))\n        assertFalse(payload.contains(\"native_model_reference\"))\n    }\n""",
    "formal independence test",
)
write(path, text)


# ---------------------------------------------------------------------------
# 5. Add semantic tests for the evidence envelope and visible injection marker.
# ---------------------------------------------------------------------------
path = "app/src/test/java/com/tianji/probabilitylab/nativev4/ai/ContinualRemoteAiAnalyzerTest.kt"
text = read(path)
text = replace_once(
    text,
    "import org.junit.Assert.assertEquals\nimport org.junit.Assert.assertTrue\n",
    "import org.junit.Assert.assertEquals\nimport org.junit.Assert.assertFalse\nimport org.junit.Assert.assertTrue\n",
    "test imports",
)
insert_at = """    @Test\n    fun acceptedForecastUsesFixed235780PoolAndBinaryLearningSummary() {\n"""
if insert_at not in text:
    raise SystemExit("missing continual test insertion anchor")
new_test = """    @Test\n    fun promptEvidenceContainsOwnLearningButNeverNativeAnswer() {\n        val plan = manualPlan(\n            bestPosition = 4,\n            remotePosition = 0,\n            remoteScore = 0.30,\n        )\n        val json = AiContinualForecastEngine.promptEvidence(plan)\n\n        assertEquals(\"tianji-ai-self-learning-v1\", json.getString(\"schema\"))\n        assertEquals(\"235780\", json.getString(\"target_pool\"))\n        assertEquals(0.60, json.getDouble(\"random_baseline\"), 1e-9)\n        assertEquals(10, json.getJSONArray(\"positions\").length())\n        val first = json.getJSONArray(\"positions\").getJSONObject(0)\n        assertTrue(first.has(\"validation_samples\"))\n        assertTrue(first.has(\"average_binary_log_loss\"))\n        assertTrue(first.has(\"own_long_term_factor_weights\"))\n        val raw = json.toString()\n        assertFalse(raw.contains(\"native\", ignoreCase = true))\n        assertFalse(raw.contains(\"本机\"))\n    }\n\n"""
text = text.replace(insert_at, new_test + insert_at, 1)
text = replace_once(
    text,
    """        assertTrue(result.executionNote.contains(\"固定六码235780\"))\n""",
    """        assertTrue(result.executionNote.contains(\"AI自学习证据已注入\"))\n        assertTrue(result.executionNote.contains(\"与本机答案隔离\"))\n        assertTrue(result.executionNote.contains(\"固定六码235780\"))\n""",
    "execution marker test",
)
write(path, text)


# ---------------------------------------------------------------------------
# 6. Source-level contract: wrapper must inject evidence before delegate call.
# ---------------------------------------------------------------------------
path = "app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiSelfLearningPromptContractTest.kt"
Path(path).write_text(
    '''package com.tianji.probabilitylab.nativev4.ai\n\nimport java.io.File\nimport org.junit.Assert.assertFalse\nimport org.junit.Assert.assertTrue\nimport org.junit.Test\n\nclass AiSelfLearningPromptContractTest {\n    private fun source(name: String): String = File(\n        "src/main/java/com/tianji/probabilitylab/nativev4/ai/$name",\n    ).readText()\n\n    @Test\n    fun continualWrapperInjectsEvidenceBeforeRemoteInference() {\n        val source = source("ContinualRemoteAiAnalyzer.kt")\n        val analyze = source.substringAfter("fun analyze(")\n            .substringBefore("data class AiPositionForwardEvidence")\n        val build = analyze.indexOf("promptEvidence(plan)")\n        val remote = analyze.indexOf("delegate.analyze(")\n        assertTrue(build >= 0)\n        assertTrue(remote > build)\n        assertTrue(analyze.contains("selfLearningEvidence = selfLearningEvidence"))\n    }\n\n    @Test\n    fun remotePayloadAllowsOwnLearningButStillRejectsNativeAnswers() {\n        val source = source("AiAnalysis.kt")\n        assertTrue(source.contains("raw-history+ai-self-learning-v2"))\n        assertTrue(source.contains("ai_self_learning_evidence"))\n        assertTrue(source.contains("原始历史+AI自学习证据 · 严格隔离本机答案"))\n        val payload = source.substringAfter("private fun analysisPayload(")\n            .substringBefore("private fun isRetriableModelOutput")\n        assertFalse(payload.contains("report.selectedPosition"))\n        assertFalse(payload.contains("report.selected.top6"))\n        assertFalse(payload.contains("native_model_reference"))\n    }\n}\n''',
    encoding="utf-8",
)

print("AI self-learning prompt injection patch applied")
