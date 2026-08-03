from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

FREE_CHAT = r'''package com.tianji.probabilitylab.nativev4.ai

import java.util.UUID
import kotlin.math.ceil

enum class AiChatRole {
    SYSTEM,
    USER,
    ASSISTANT,
}

enum class AiChatPersona(
    val id: String,
    val displayName: String,
    val description: String,
    val instruction: String,
    val quickPrompts: List<String>,
) {
    COMPREHENSIVE(
        id = "comprehensive",
        displayName = "综合研判",
        description = "综合频次、遗漏、转移、趋势和本机模型",
        instruction = "综合使用20/60/120期频次、当前遗漏、后继转移、短长窗口变化和本机模型参考。先给结论，再列最关键证据和不确定性，避免只凭单一指标下结论。",
        quickPrompts = listOf(
            "综合分析第一名，给出下一期相对候选和主要依据",
            "上一期候选没有命中，复盘后调整这期的分析策略",
            "结合历史统计和本机模型，解释当前六码的优缺点",
        ),
    ),
    HISTORY(
        id = "history",
        displayName = "历史分析",
        description = "专注真实接口历史、频次、遗漏和样本窗口",
        instruction = "以历史统计审计员的方式回答。优先核对期数、窗口、次数、占比、遗漏和样本量；明确区分20期、60期和120期，发现样本不足或差异很小时必须指出。",
        quickPrompts = listOf(
            "分析第一名最近60期，哪些号码相对活跃？",
            "第一名1到10号最近20、60、120期分别出现多少次？",
            "查看第三名各号码当前遗漏多少期，并指出极端值",
        ),
    ),
    TREND(
        id = "trend",
        displayName = "走势研判",
        description = "比较短中长窗口的升温、降温与稳定性",
        instruction = "以走势研判员的方式回答。重点比较20期对60期、60期对120期的相对变化，识别升温、降温、震荡和稳定，但不得把短期波动描述成必然趋势。候选应同时考虑趋势强度和样本稳定性。",
        quickPrompts = listOf(
            "研判第一名最近20期相对60期的升温和降温号码",
            "比较十个名次的短期走势，哪个名次变化最明显？",
            "找出第一名短中长窗口方向一致的号码",
        ),
    ),
    OMISSION(
        id = "omission",
        displayName = "遗漏追踪",
        description = "追踪当前遗漏、回补节奏和过热风险",
        instruction = "以遗漏追踪员的方式回答。重点分析当前遗漏、历史出现节奏和近期密度，同时明确说明遗漏久不代表下一期必出，连续出现也不代表必然降温，避免赌徒谬误。",
        quickPrompts = listOf(
            "查看第一名当前遗漏最高和最低的号码",
            "第一名哪些号码近期密集出现，哪些号码长时间未出现？",
            "结合遗漏和频次给出第一名相对候选，但说明风险",
        ),
    ),
    TRANSITION(
        id = "transition",
        displayName = "转移分析",
        description = "分析当前号码之后历史上更常出现的后继号",
        instruction = "以后继转移分析员的方式回答。围绕当前号码，统计历史上下一期各号码的出现次数和样本总量；样本少时降低结论强度，并与总体频次对照，避免把偶然转移当规律。",
        quickPrompts = listOf(
            "第一名当前号码之后，历史上更常接哪些号？",
            "比较第一名后继转移和总体频次，哪些号码被明显高估或低估？",
            "分析第五名当前号码的历史后继分布和样本量",
        ),
    ),
    RISK_AUDIT(
        id = "risk_audit",
        displayName = "风险审计",
        description = "反向检查候选、样本偏差和过拟合风险",
        instruction = "以严格的风险审计员方式回答。主动寻找候选中的样本偏差、短窗过拟合、指标冲突、边界过小和本机模型不稳定之处；可以否定不可靠结论，并给出更保守的候选或建议继续观察。",
        quickPrompts = listOf(
            "审计当前第一名六码，哪些号码证据最弱？",
            "检查当前候选是否过度依赖最近20期",
            "从反方角度解释为什么这组候选可能失败",
        ),
    );

    companion object {
        fun fromId(id: String?): AiChatPersona =
            entries.firstOrNull { it.id == id } ?: COMPREHENSIVE
    }
}

data class AiChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val role: AiChatRole,
    val content: String,
    val targetPeriod: String? = null,
    val createdAtEpochMs: Long = System.currentTimeMillis(),
    val latencyMs: Long? = null,
)

data class AiChatPrediction(
    val position: Int,
    val top6: List<Int>,
    val top7: List<Int>,
    val probabilities: List<Double>,
)

data class AiChatCandidateRecord(
    val id: String = UUID.randomUUID().toString(),
    val messageId: String,
    val targetPeriod: String,
    val prediction: AiChatPrediction,
    val actualNumber: Int? = null,
    val resolvedPeriod: String? = null,
    val createdAtEpochMs: Long = System.currentTimeMillis(),
)

data class AiChatArchive(
    val id: String,
    val lotteryKey: String,
    val profileId: String,
    val profileName: String,
    val model: String,
    val title: String = "新对话",
    val targetPeriod: String,
    val personaId: String = AiChatPersona.COMPREHENSIVE.id,
    val memorySummary: String = "",
    val continuationOf: String? = null,
    val messages: List<AiChatMessage> = emptyList(),
    val candidates: List<AiChatCandidateRecord> = emptyList(),
    val createdAtEpochMs: Long = System.currentTimeMillis(),
    val updatedAtEpochMs: Long = System.currentTimeMillis(),
)

data class AiChatArchiveSummary(
    val id: String,
    val lotteryKey: String,
    val profileId: String,
    val targetPeriod: String,
    val profileName: String,
    val model: String,
    val title: String,
    val preview: String,
    val personaId: String,
    val messageCount: Int,
    val hasPrediction: Boolean,
    val updatedAtEpochMs: Long,
)

data class AiChatSession(
    val archiveId: String = "",
    val lotteryKey: String = "",
    val profileId: String,
    val profileName: String = "",
    val model: String = "",
    val title: String = "新对话",
    val personaId: String = AiChatPersona.COMPREHENSIVE.id,
    val memorySummary: String = "",
    val continuationOf: String? = null,
    val messages: List<AiChatMessage> = emptyList(),
    val candidates: List<AiChatCandidateRecord> = emptyList(),
    val isRunning: Boolean = false,
    val progress: String = "",
    val error: String? = null,
    val prediction: AiChatPrediction? = null,
    val targetPeriod: String? = null,
    val streamingMessageId: String? = null,
    val isReadOnlyArchive: Boolean = false,
    val contextUsagePercent: Int = 0,
    val rolloverNotice: String? = null,
    val createdAtEpochMs: Long = System.currentTimeMillis(),
    val updatedAtEpochMs: Long = System.currentTimeMillis(),
)

data class AiChatReply(
    val content: String,
    val prediction: AiChatPrediction?,
    val latencyMs: Long,
    val responseId: String,
    val reasoningTokens: Int?,
    val reasoningVerified: Boolean,
)

data class AiChatContextPlan(
    val messages: List<AiChatMessage>,
    val estimatedTokens: Int,
    val safeBudgetTokens: Int,
    val shouldRollover: Boolean,
) {
    val usagePercent: Int = ((estimatedTokens * 100.0) / safeBudgetTokens)
        .toInt().coerceIn(0, 100)
}

object AiChatConversationId {
    fun newId(lotteryKey: String, profileId: String, model: String): String =
        listOf(lotteryKey.trim(), profileId.trim(), model.trim(), UUID.randomUUID().toString())
            .joinToString("\u001F")
}

/** Kept only for decoding v1 period archives. New conversations use random stable IDs. */
object AiChatArchiveId {
    fun of(lotteryKey: String, targetPeriod: String, profileId: String, model: String): String =
        listOf(lotteryKey, targetPeriod, profileId, model).joinToString("\u001F") { it.trim() }
}

object AiChatProtocol {
    private const val SAFE_CONTEXT_TOKENS = 18_000
    private const val ROLLOVER_MESSAGES = 72
    private const val MEMORY_LIMIT = 5_500
    private val predictionTerms = listOf(
        "预测", "预判", "候选", "六码", "七码", "号码", "出号", "推荐", "名次",
        "position", "scores", "forecast", "pick",
    )
    private val strategyTerms = listOf(
        "没中", "未中", "命中", "调整", "策略", "降低", "提高", "保留", "排除",
        "权重", "复盘", "偏重", "不要", "继续", "改成",
    )

    fun wantsPrediction(text: String): Boolean {
        val normalized = text.trim().lowercase()
        return predictionTerms.any(normalized::contains)
    }

    fun estimateTokens(text: String): Int {
        if (text.isBlank()) return 0
        val cjk = text.count { it.code in 0x2E80..0x9FFF }
        val other = text.length - cjk
        return ceil(cjk * 0.95 + other * 0.28).toInt().coerceAtLeast(1)
    }

    fun planContext(
        messages: List<AiChatMessage>,
        memorySummary: String,
        safeBudgetTokens: Int = SAFE_CONTEXT_TOKENS,
    ): AiChatContextPlan {
        val clean = messages.filter { it.content.isNotBlank() }
        val total = estimateTokens(memorySummary) + clean.sumOf { estimateTokens(it.content) }
        val available = (safeBudgetTokens - estimateTokens(memorySummary) - 1_800).coerceAtLeast(2_000)
        var used = 0
        val kept = ArrayDeque<AiChatMessage>()
        clean.asReversed().forEach { message ->
            val cost = estimateTokens(message.content) + 8
            if (kept.isNotEmpty() && used + cost > available) return@forEach
            kept.addFirst(message)
            used += cost
        }
        return AiChatContextPlan(
            messages = kept.toList(),
            estimatedTokens = total,
            safeBudgetTokens = safeBudgetTokens,
            shouldRollover = total >= (safeBudgetTokens * 0.86).toInt() || clean.size >= ROLLOVER_MESSAGES,
        )
    }

    fun buildConversationTitle(firstQuestion: String): String = firstQuestion
        .replace(Regex("\\s+"), " ")
        .trim()
        .take(22)
        .ifBlank { "新对话" }

    fun buildMemorySummary(
        previousSummary: String,
        messages: List<AiChatMessage>,
        candidates: List<AiChatCandidateRecord>,
    ): String {
        val feedback = messages
            .filter { it.role == AiChatRole.USER && strategyTerms.any(it.content::contains) }
            .takeLast(14)
            .joinToString("\n") { "- ${it.content.replace(Regex("\\s+"), " ").take(240)}" }
        val recent = messages
            .filter { it.role != AiChatRole.SYSTEM }
            .takeLast(12)
            .joinToString("\n") { message ->
                val role = if (message.role == AiChatRole.USER) "用户" else "助手"
                "$role：${message.content.replace(Regex("\\s+"), " ").take(260)}"
            }
        val candidateDigest = candidates.takeLast(8).joinToString("\n") { record ->
            buildString {
                append("- 目标期${record.targetPeriod} 第${record.prediction.position + 1}名 ")
                append("六码${record.prediction.top6.joinToString("/")}")
                record.actualNumber?.let { actual ->
                    append("，实际$actual，")
                    append(if (actual in record.prediction.top6) "六码命中" else "六码未中")
                }
            }
        }
        return buildString {
            appendLine("长期对话记忆（仅用于延续用户明确表达的分析偏好，不代表模型已训练）：")
            if (previousSummary.isNotBlank()) {
                appendLine(previousSummary.take(1_600))
            }
            if (feedback.isNotBlank()) {
                appendLine("用户的策略反馈：")
                appendLine(feedback)
            }
            if (candidateDigest.isNotBlank()) {
                appendLine("近期候选与开奖核验：")
                appendLine(candidateDigest)
            }
            if (recent.isNotBlank()) {
                appendLine("最近对话摘要：")
                append(recent)
            }
        }.take(MEMORY_LIMIT)
    }

    fun parsePrediction(text: String): AiChatPrediction? {
        val canonical = AiForecastPayloadExtractor.salvageCoreJson(text) ?: return null
        val position = Regex("\\\"position\\\":(10|[1-9])")
            .find(canonical)?.groupValues?.getOrNull(1)?.toIntOrNull() ?: return null
        val scoreText = Regex("\\\"scores\\\":\\[([^]]+)]")
            .find(canonical)?.groupValues?.getOrNull(1) ?: return null
        val scores = scoreText.split(',').mapNotNull { it.trim().toDoubleOrNull() }
        if (scores.size != 10 || scores.any { !it.isFinite() || it < 0.0 }) return null
        val sum = scores.sum()
        if (!sum.isFinite() || sum <= 0.0) return null
        val probabilities = scores.map { it / sum }
        val ranking = probabilities.indices
            .sortedWith(compareByDescending<Int> { probabilities[it] }.thenBy { it })
            .map { it + 1 }
        return AiChatPrediction(
            position = position - 1,
            top6 = ranking.take(6),
            top7 = ranking.take(7),
            probabilities = probabilities,
        )
    }

    fun visibleText(text: String, hasPrediction: Boolean): String {
        var value = text.trim()
        value = value.replace(Regex("(?s)<tianji_forecast>.*?</tianji_forecast>"), "").trim()
        if (hasPrediction) {
            AiForecastPayloadExtractor.balancedJsonObjects(value)
                .firstOrNull { AiForecastPayloadExtractor.salvageCoreJson(it) != null }
                ?.let { value = value.replace(it, "").trim() }
        }
        value = value
            .replace(Regex("(?s)```json\\s*```"), "")
            .replace(Regex("\\n{3,}"), "\n\n")
            .trim()
        return value.ifBlank {
            if (hasPrediction) "已根据你的要求生成结构化候选结果。" else "模型已完成本次分析。"
        }
    }

    fun visibleStreamingText(text: String): String {
        val markerIndex = text.indexOf("<tianji_forecast>", ignoreCase = true)
        val visible = if (markerIndex >= 0) text.substring(0, markerIndex) else text
        return visible
            .replace(Regex("(?s)```json.*$"), "")
            .replace(Regex("\\n{3,}"), "\n\n")
            .trimStart()
    }

    fun trimHistory(messages: List<AiChatMessage>, maxMessages: Int = 36): List<AiChatMessage> =
        messages.filter { it.content.isNotBlank() }.takeLast(maxMessages.coerceAtLeast(1))
}
'''

ARCHIVE_STORE = r'''package com.tianji.probabilitylab.nativev4.ai

import android.content.Context
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** App-private multi-conversation store, deliberately separate from official forecast records. */
class AiChatArchiveStore(context: Context) {
    private val file = AtomicFile(File(context.filesDir, FILE_NAME))

    @Synchronized
    fun loadAll(): List<AiChatArchive> = runCatching {
        if (!file.baseFile.exists()) return emptyList()
        val text = file.openRead().bufferedReader(Charsets.UTF_8).use { it.readText() }
        AiChatArchiveCodec.decode(text)
    }.getOrDefault(emptyList())

    @Synchronized
    fun upsert(archive: AiChatArchive): List<AiChatArchive> {
        val normalized = archive.copy(
            messages = archive.messages.filter { it.content.isNotBlank() }.takeLast(MAX_MESSAGES),
            candidates = archive.candidates.takeLast(MAX_CANDIDATES),
            memorySummary = archive.memorySummary.take(MAX_MEMORY_CHARS),
            updatedAtEpochMs = System.currentTimeMillis(),
        )
        val all = (loadAll().filterNot { it.id == normalized.id } + normalized)
            .sortedByDescending(AiChatArchive::updatedAtEpochMs)
            .take(MAX_CONVERSATIONS)
        writeAll(all)
        return all
    }

    @Synchronized
    fun delete(id: String): List<AiChatArchive> {
        val all = loadAll().filterNot { it.id == id }
        writeAll(all)
        return all
    }

    private fun writeAll(archives: List<AiChatArchive>) {
        val output = file.startWrite()
        try {
            output.write(AiChatArchiveCodec.encode(archives).toByteArray(Charsets.UTF_8))
            output.flush()
            file.finishWrite(output)
        } catch (cause: Throwable) {
            file.failWrite(output)
            throw cause
        }
    }

    private companion object {
        const val FILE_NAME = "ai_chat_archive_v1.json"
        const val MAX_CONVERSATIONS = 240
        const val MAX_MESSAGES = 240
        const val MAX_CANDIDATES = 80
        const val MAX_MEMORY_CHARS = 6_000
    }
}

object AiChatArchiveCodec {
    fun encode(archives: List<AiChatArchive>): String = JSONObject()
        .put("schema", 2)
        .put("archives", JSONArray(archives.map(::toJson)))
        .toString()

    fun decode(text: String): List<AiChatArchive> {
        if (text.isBlank()) return emptyList()
        val root = JSONObject(text)
        val schema = root.optInt("schema", 1)
        val array = root.optJSONArray("archives") ?: return emptyList()
        return buildList {
            for (index in 0 until array.length()) {
                array.optJSONObject(index)?.toArchiveOrNull(schema)?.let(::add)
            }
        }.distinctBy(AiChatArchive::id)
            .sortedByDescending(AiChatArchive::updatedAtEpochMs)
    }

    fun summary(archive: AiChatArchive): AiChatArchiveSummary = AiChatArchiveSummary(
        id = archive.id,
        lotteryKey = archive.lotteryKey,
        profileId = archive.profileId,
        targetPeriod = archive.targetPeriod,
        profileName = archive.profileName,
        model = archive.model,
        title = archive.title,
        preview = archive.messages.lastOrNull { it.content.isNotBlank() }
            ?.content?.replace(Regex("\\s+"), " ")?.take(72).orEmpty(),
        personaId = archive.personaId,
        messageCount = archive.messages.count { it.role != AiChatRole.SYSTEM },
        hasPrediction = archive.candidates.isNotEmpty(),
        updatedAtEpochMs = archive.updatedAtEpochMs,
    )

    private fun toJson(archive: AiChatArchive): JSONObject = JSONObject()
        .put("id", archive.id)
        .put("lottery_key", archive.lotteryKey)
        .put("profile_id", archive.profileId)
        .put("profile_name", archive.profileName)
        .put("model", archive.model)
        .put("title", archive.title)
        .put("target_period", archive.targetPeriod)
        .put("persona_id", archive.personaId)
        .put("memory_summary", archive.memorySummary)
        .put("continuation_of", archive.continuationOf ?: JSONObject.NULL)
        .put("created_at", archive.createdAtEpochMs)
        .put("updated_at", archive.updatedAtEpochMs)
        .put("messages", JSONArray(archive.messages.map(::messageToJson)))
        .put("candidates", JSONArray(archive.candidates.map(::candidateToJson)))

    private fun messageToJson(message: AiChatMessage): JSONObject = JSONObject()
        .put("id", message.id)
        .put("role", message.role.name)
        .put("content", message.content)
        .put("target_period", message.targetPeriod ?: JSONObject.NULL)
        .put("created_at", message.createdAtEpochMs)
        .put("latency_ms", message.latencyMs ?: JSONObject.NULL)

    private fun candidateToJson(record: AiChatCandidateRecord): JSONObject = JSONObject()
        .put("id", record.id)
        .put("message_id", record.messageId)
        .put("target_period", record.targetPeriod)
        .put("actual_number", record.actualNumber ?: JSONObject.NULL)
        .put("resolved_period", record.resolvedPeriod ?: JSONObject.NULL)
        .put("created_at", record.createdAtEpochMs)
        .put("prediction", predictionToJson(record.prediction))

    private fun predictionToJson(prediction: AiChatPrediction): JSONObject = JSONObject()
        .put("position", prediction.position)
        .put("top6", JSONArray(prediction.top6))
        .put("top7", JSONArray(prediction.top7))
        .put("probabilities", JSONArray(prediction.probabilities))

    private fun JSONObject.toArchiveOrNull(schema: Int): AiChatArchive? = runCatching {
        val lotteryKey = getString("lottery_key")
        val profileId = getString("profile_id")
        val model = getString("model")
        val targetPeriod = optString("target_period")
        require(lotteryKey.isNotBlank() && profileId.isNotBlank() && model.isNotBlank())
        val messages = optJSONArray("messages").toMessages()
        val legacyPrediction = optJSONObject("prediction")?.toPredictionOrNull()
        val candidates = if (schema >= 2) {
            optJSONArray("candidates").toCandidates()
        } else {
            legacyPrediction?.let { prediction ->
                listOf(
                    AiChatCandidateRecord(
                        messageId = messages.lastOrNull { it.role == AiChatRole.ASSISTANT }?.id.orEmpty(),
                        targetPeriod = targetPeriod,
                        prediction = prediction,
                        createdAtEpochMs = optLong("updated_at", System.currentTimeMillis()),
                    ),
                )
            }.orEmpty()
        }
        val rawId = optString("id")
        AiChatArchive(
            id = rawId.ifBlank { AiChatConversationId.newId(lotteryKey, profileId, model) },
            lotteryKey = lotteryKey,
            profileId = profileId,
            profileName = optString("profile_name"),
            model = model,
            title = optString("title").ifBlank {
                messages.firstOrNull { it.role == AiChatRole.USER }
                    ?.content?.let(AiChatProtocol::buildConversationTitle)
                    ?: targetPeriod.takeIf(String::isNotBlank)?.let { "目标期 $it 分析" }
                    ?: "历史对话"
            },
            targetPeriod = targetPeriod,
            personaId = AiChatPersona.fromId(optString("persona_id")).id,
            memorySummary = optString("memory_summary").takeUnless { it == "null" }.orEmpty(),
            continuationOf = optString("continuation_of").takeUnless { it.isBlank() || it == "null" },
            messages = messages,
            candidates = candidates,
            createdAtEpochMs = optLong("created_at", System.currentTimeMillis()),
            updatedAtEpochMs = optLong("updated_at", System.currentTimeMillis()),
        )
    }.getOrNull()

    private fun JSONArray?.toMessages(): List<AiChatMessage> {
        if (this == null) return emptyList()
        return buildList {
            for (index in 0 until length()) {
                val item = optJSONObject(index) ?: continue
                val content = item.optString("content")
                if (content.isBlank()) continue
                add(
                    AiChatMessage(
                        id = item.optString("id").ifBlank { java.util.UUID.randomUUID().toString() },
                        role = runCatching { AiChatRole.valueOf(item.optString("role")) }
                            .getOrDefault(AiChatRole.ASSISTANT),
                        content = content,
                        targetPeriod = item.optString("target_period")
                            .takeUnless { it.isBlank() || it == "null" },
                        createdAtEpochMs = item.optLong("created_at", System.currentTimeMillis()),
                        latencyMs = item.optLong("latency_ms", -1L).takeIf { it >= 0L },
                    ),
                )
            }
        }
    }

    private fun JSONArray?.toCandidates(): List<AiChatCandidateRecord> {
        if (this == null) return emptyList()
        return buildList {
            for (index in 0 until length()) {
                val item = optJSONObject(index) ?: continue
                val prediction = item.optJSONObject("prediction")?.toPredictionOrNull() ?: continue
                add(
                    AiChatCandidateRecord(
                        id = item.optString("id").ifBlank { java.util.UUID.randomUUID().toString() },
                        messageId = item.optString("message_id"),
                        targetPeriod = item.optString("target_period"),
                        prediction = prediction,
                        actualNumber = item.optInt("actual_number", -1).takeIf { it in 1..10 },
                        resolvedPeriod = item.optString("resolved_period")
                            .takeUnless { it.isBlank() || it == "null" },
                        createdAtEpochMs = item.optLong("created_at", System.currentTimeMillis()),
                    ),
                )
            }
        }
    }

    private fun JSONObject.toPredictionOrNull(): AiChatPrediction? = runCatching {
        val probabilities = getJSONArray("probabilities").toDoubleList()
        require(probabilities.size == 10)
        AiChatPrediction(
            position = getInt("position").coerceIn(0, 9),
            top6 = getJSONArray("top6").toIntList().take(6),
            top7 = getJSONArray("top7").toIntList().take(7),
            probabilities = probabilities,
        )
    }.getOrNull()

    private fun JSONArray.toIntList(): List<Int> =
        (0 until length()).mapNotNull { index -> optInt(index, -1).takeIf { it > 0 } }

    private fun JSONArray.toDoubleList(): List<Double> =
        (0 until length()).mapNotNull { index -> optDouble(index, Double.NaN).takeIf(Double::isFinite) }
}
'''

CONTROLLER_HEAD = r'''class AiChatController(context: Context) {
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())
    private val generation = AtomicInteger(0)
    private val client = RemoteAiChatClient()
    private val archiveStore = AiChatArchiveStore(context.applicationContext)
    private var archiveData = archiveStore.loadAll()

    var session by mutableStateOf(AiChatSession(profileId = ""))
        private set

    var archives by mutableStateOf(archiveData.map(AiChatArchiveCodec::summary))
        private set

    fun selectContext(
        profileId: String,
        profileName: String,
        model: String,
        lotteryKey: String,
        targetPeriod: String?,
        latestPeriod: String? = null,
        latestNumbers: List<Int> = emptyList(),
    ) {
        val normalizedModel = model.trim()
        val normalizedProfile = profileId.trim()
        val normalizedLottery = lotteryKey.trim()
        val normalizedTarget = targetPeriod.orEmpty().trim()
        if (normalizedProfile.isBlank() || normalizedModel.isBlank() || normalizedLottery.isBlank()) {
            if (session.isRunning) cancel()
            persistCurrent()
            session = AiChatSession(
                profileId = normalizedProfile,
                profileName = profileName.trim(),
                model = normalizedModel,
                lotteryKey = normalizedLottery,
                targetPeriod = normalizedTarget.ifBlank { null },
                personaId = session.personaId,
            )
            return
        }
        val sameContext = session.lotteryKey == normalizedLottery &&
            session.profileId == normalizedProfile && session.model == normalizedModel &&
            session.archiveId.isNotBlank()
        if (!sameContext) {
            if (session.isRunning) cancel()
            persistCurrent()
            val saved = archiveData
                .filter {
                    it.lotteryKey == normalizedLottery && it.profileId == normalizedProfile &&
                        it.model == normalizedModel
                }
                .maxByOrNull(AiChatArchive::updatedAtEpochMs)
            session = saved?.toSession() ?: freshSession(
                profileId = normalizedProfile,
                profileName = profileName.trim(),
                model = normalizedModel,
                lotteryKey = normalizedLottery,
                targetPeriod = normalizedTarget,
            )
        }
        syncTargetTransition(normalizedTarget, latestPeriod, latestNumbers)
    }

    fun newConversation(
        profileId: String,
        profileName: String,
        model: String,
        lotteryKey: String,
        targetPeriod: String?,
        inheritStrategy: Boolean,
    ) {
        if (session.isRunning) cancel()
        val memory = if (inheritStrategy) {
            AiChatProtocol.buildMemorySummary(session.memorySummary, session.messages, session.candidates)
        } else {
            ""
        }
        val previousId = session.archiveId.takeIf { inheritStrategy && it.isNotBlank() }
        persistCurrent()
        session = freshSession(
            profileId = profileId.trim(),
            profileName = profileName.trim(),
            model = model.trim(),
            lotteryKey = lotteryKey.trim(),
            targetPeriod = targetPeriod.orEmpty().trim(),
            memorySummary = memory,
            continuationOf = previousId,
        ).copy(
            messages = if (inheritStrategy && memory.isNotBlank()) {
                listOf(
                    AiChatMessage(
                        role = AiChatRole.SYSTEM,
                        content = "已从上一段对话继承关键策略、复盘反馈和候选核验；完整旧消息仍保存在历史会话中。",
                        targetPeriod = targetPeriod,
                    ),
                )
            } else {
                emptyList()
            },
            rolloverNotice = if (inheritStrategy) "已继承上一段对话的策略摘要" else null,
        )
        persistCurrent()
    }

    fun openArchive(archiveId: String) {
        if (session.isRunning) return
        val saved = archiveData.firstOrNull { it.id == archiveId } ?: return
        persistCurrent()
        session = saved.toSession()
    }

    fun selectPersona(personaId: String) {
        if (session.isRunning) return
        val persona = AiChatPersona.fromId(personaId)
        if (session.personaId != persona.id) {
            session = session.copy(
                personaId = persona.id,
                error = null,
                updatedAtEpochMs = System.currentTimeMillis(),
            )
            persistCurrent()
        }
    }

    fun send(
        config: AiConfig,
        snapshot: DrawSnapshot,
        report: ForecastReport,
        question: String,
    ) {
        val text = question.trim()
        if (text.isBlank() || session.isRunning) return
        val activeModel = session.model.ifBlank { config.model }.trim()
        selectContext(
            profileId = config.id,
            profileName = config.displayName,
            model = activeModel,
            lotteryKey = snapshot.lottery.apiKey,
            targetPeriod = report.targetPeriod,
            latestPeriod = snapshot.latest.period,
            latestNumbers = snapshot.latest.numbers,
        )
        ensureContextCapacity()
        val activeConfig = config.copy(model = activeModel)
        val plan = AiChatProtocol.planContext(session.messages, session.memorySummary)
        val previousMessages = plan.messages
        val userMessage = AiChatMessage(
            role = AiChatRole.USER,
            content = text,
            targetPeriod = report.targetPeriod,
        )
        val assistantMessage = AiChatMessage(
            role = AiChatRole.ASSISTANT,
            content = "",
            targetPeriod = report.targetPeriod,
        )
        val persona = AiChatPersona.fromId(session.personaId)
        val token = generation.incrementAndGet()
        val nextTitle = if (session.messages.none { it.role == AiChatRole.USER }) {
            AiChatProtocol.buildConversationTitle(text)
        } else {
            session.title
        }
        session = session.copy(
            title = nextTitle,
            messages = session.messages + userMessage + assistantMessage,
            isRunning = true,
            progress = "正在整理当前接口历史…",
            error = null,
            prediction = null,
            streamingMessageId = assistantMessage.id,
            contextUsagePercent = plan.usagePercent,
            rolloverNotice = null,
            updatedAtEpochMs = System.currentTimeMillis(),
        )
        persistCurrent()
        executor.execute {
            val result = runCatching {
                client.chat(
                    config = activeConfig,
                    snapshot = snapshot,
                    report = report,
                    previousMessages = previousMessages,
                    memorySummary = session.memorySummary,
                    question = text,
                    persona = persona,
                    onProgress = { progress ->
                        mainHandler.post {
                            if (generation.get() == token && session.isRunning) {
                                session = session.copy(progress = progress)
                            }
                        }
                    },
                    onStreamText = { content ->
                        mainHandler.post {
                            if (generation.get() == token && session.isRunning) {
                                replaceMessage(assistantMessage.id) { current -> current.copy(content = content) }
                            }
                        }
                    },
                )
            }
            mainHandler.post {
                if (generation.get() != token) return@post
                result.fold(
                    onSuccess = { reply ->
                        replaceMessage(assistantMessage.id) { current ->
                            current.copy(content = reply.content, latencyMs = reply.latencyMs)
                        }
                        val nextCandidates = reply.prediction?.let { prediction ->
                            session.candidates + AiChatCandidateRecord(
                                messageId = assistantMessage.id,
                                targetPeriod = report.targetPeriod,
                                prediction = prediction,
                            )
                        } ?: session.candidates
                        session = session.copy(
                            isRunning = false,
                            progress = if (reply.reasoningVerified) {
                                reply.reasoningTokens?.let { "回答完成 · 推理 $it tokens" }
                                    ?: "回答完成 · 已验证模型思考"
                            } else {
                                "回答完成"
                            },
                            error = null,
                            prediction = reply.prediction,
                            candidates = nextCandidates,
                            streamingMessageId = null,
                            contextUsagePercent = AiChatProtocol
                                .planContext(session.messages, session.memorySummary).usagePercent,
                            updatedAtEpochMs = System.currentTimeMillis(),
                        )
                        persistCurrent()
                    },
                    onFailure = { cause ->
                        val partial = session.messages
                            .firstOrNull { it.id == assistantMessage.id }?.content.orEmpty()
                        session = session.copy(
                            messages = if (partial.isBlank()) {
                                session.messages.filterNot { it.id == assistantMessage.id }
                            } else {
                                session.messages
                            },
                            isRunning = false,
                            progress = "",
                            error = cause.message ?: "对话分析失败",
                            streamingMessageId = null,
                            updatedAtEpochMs = System.currentTimeMillis(),
                        )
                        persistCurrent()
                    },
                )
            }
        }
    }

    fun cancel() {
        generation.incrementAndGet()
        client.cancel()
        if (session.isRunning) {
            val streamingId = session.streamingMessageId
            val partial = session.messages.firstOrNull { it.id == streamingId }?.content.orEmpty()
            session = session.copy(
                messages = if (streamingId != null && partial.isBlank()) {
                    session.messages.filterNot { it.id == streamingId }
                } else {
                    session.messages
                },
                isRunning = false,
                progress = if (partial.isBlank()) "已取消本次对话" else "已停止继续生成",
                error = null,
                streamingMessageId = null,
                updatedAtEpochMs = System.currentTimeMillis(),
            )
            persistCurrent()
        }
    }

    fun clear() {
        cancel()
        session = session.copy(
            messages = emptyList(),
            candidates = emptyList(),
            prediction = null,
            memorySummary = "",
            title = "新对话",
            contextUsagePercent = 0,
            error = null,
            progress = "",
            updatedAtEpochMs = System.currentTimeMillis(),
        )
        persistCurrent(force = true)
    }

    fun deleteCurrent() {
        cancel()
        val deleted = session.archiveId
        if (deleted.isNotBlank()) archiveData = archiveStore.delete(deleted)
        refreshArchiveSummaries()
        val replacement = archiveData
            .filter {
                it.lotteryKey == session.lotteryKey && it.profileId == session.profileId &&
                    it.model == session.model
            }
            .maxByOrNull(AiChatArchive::updatedAtEpochMs)
        session = replacement?.toSession() ?: freshSession(
            profileId = session.profileId,
            profileName = session.profileName,
            model = session.model,
            lotteryKey = session.lotteryKey,
            targetPeriod = session.targetPeriod.orEmpty(),
        )
    }

    fun close() {
        cancel()
        persistCurrent()
        executor.shutdownNow()
    }

    private fun ensureContextCapacity() {
        val plan = AiChatProtocol.planContext(session.messages, session.memorySummary)
        if (!plan.shouldRollover || session.messages.isEmpty()) {
            session = session.copy(contextUsagePercent = plan.usagePercent)
            return
        }
        val old = session
        val summary = AiChatProtocol.buildMemorySummary(
            old.memorySummary,
            old.messages,
            old.candidates,
        )
        persistCurrent()
        session = freshSession(
            profileId = old.profileId,
            profileName = old.profileName,
            model = old.model,
            lotteryKey = old.lotteryKey,
            targetPeriod = old.targetPeriod.orEmpty(),
            memorySummary = summary,
            continuationOf = old.archiveId,
        ).copy(
            title = "${old.title.take(17)} · 续",
            personaId = old.personaId,
            messages = listOf(
                AiChatMessage(
                    role = AiChatRole.SYSTEM,
                    content = "当前对话接近客户端安全上下文阈值，已保存旧会话并用策略摘要续接。",
                    targetPeriod = old.targetPeriod,
                ),
            ),
            rolloverNotice = "上下文已自动总结并续接为新对话",
        )
        persistCurrent()
    }

    private fun syncTargetTransition(
        newTarget: String,
        latestPeriod: String?,
        latestNumbers: List<Int>,
    ) {
        if (newTarget.isBlank()) return
        val oldTarget = session.targetPeriod.orEmpty()
        if (oldTarget.isBlank()) {
            session = session.copy(targetPeriod = newTarget)
            return
        }
        if (oldTarget == newTarget) return
        val resolvedPeriod = latestPeriod.orEmpty()
        var resolvedCandidate: AiChatCandidateRecord? = null
        val nextCandidates = session.candidates.map { record ->
            if (
                record.actualNumber == null && record.targetPeriod == resolvedPeriod &&
                record.prediction.position in latestNumbers.indices
            ) {
                val resolved = record.copy(
                    actualNumber = latestNumbers[record.prediction.position],
                    resolvedPeriod = resolvedPeriod,
                )
                resolvedCandidate = resolved
                resolved
            } else {
                record
            }
        }
        val event = buildString {
            append("期开奖衔接：")
            if (resolvedCandidate != null) {
                val candidate = requireNotNull(resolvedCandidate)
                val actual = requireNotNull(candidate.actualNumber)
                append("${candidate.targetPeriod}期第${candidate.prediction.position + 1}名实际开出$actual，")
                append(if (actual in candidate.prediction.top6) "上期六码命中" else "上期六码未中")
                append("；")
            } else if (resolvedPeriod.isNotBlank()) {
                append("接口已更新到${resolvedPeriod}期；")
            }
            append("当前进入目标期$newTarget。可以继续在本对话中复盘并要求调整分析策略。")
        }
        session = session.copy(
            targetPeriod = newTarget,
            candidates = nextCandidates,
            messages = session.messages + AiChatMessage(
                role = AiChatRole.SYSTEM,
                content = event,
                targetPeriod = newTarget,
            ),
            updatedAtEpochMs = System.currentTimeMillis(),
        )
        persistCurrent()
    }

    private fun freshSession(
        profileId: String,
        profileName: String,
        model: String,
        lotteryKey: String,
        targetPeriod: String,
        memorySummary: String = "",
        continuationOf: String? = null,
    ): AiChatSession = AiChatSession(
        archiveId = AiChatConversationId.newId(lotteryKey, profileId, model),
        lotteryKey = lotteryKey,
        profileId = profileId,
        profileName = profileName,
        model = model,
        targetPeriod = targetPeriod.ifBlank { null },
        memorySummary = memorySummary,
        continuationOf = continuationOf,
    )

    private fun persistCurrent(force: Boolean = false) {
        if (
            session.archiveId.isBlank() || session.lotteryKey.isBlank() ||
            session.profileId.isBlank() || session.model.isBlank()
        ) return
        val persistedMessages = session.messages.filter { it.content.isNotBlank() }
        if (!force && persistedMessages.isEmpty() && session.candidates.isEmpty()) return
        val archive = AiChatArchive(
            id = session.archiveId,
            lotteryKey = session.lotteryKey,
            profileId = session.profileId,
            profileName = session.profileName,
            model = session.model,
            title = session.title,
            targetPeriod = session.targetPeriod.orEmpty(),
            personaId = session.personaId,
            memorySummary = session.memorySummary,
            continuationOf = session.continuationOf,
            messages = persistedMessages,
            candidates = session.candidates,
            createdAtEpochMs = session.createdAtEpochMs,
            updatedAtEpochMs = System.currentTimeMillis(),
        )
        archiveData = archiveStore.upsert(archive)
        refreshArchiveSummaries()
    }

    private fun refreshArchiveSummaries() {
        archives = archiveData.map(AiChatArchiveCodec::summary)
    }

    private fun AiChatArchive.toSession(): AiChatSession = AiChatSession(
        archiveId = id,
        lotteryKey = lotteryKey,
        profileId = profileId,
        profileName = profileName,
        model = model,
        title = title,
        personaId = personaId,
        memorySummary = memorySummary,
        continuationOf = continuationOf,
        messages = messages,
        candidates = candidates,
        prediction = candidates.lastOrNull()?.prediction,
        targetPeriod = targetPeriod.ifBlank { null },
        contextUsagePercent = AiChatProtocol.planContext(messages, memorySummary).usagePercent,
        createdAtEpochMs = createdAtEpochMs,
        updatedAtEpochMs = updatedAtEpochMs,
    )

    private fun replaceMessage(id: String, transform: (AiChatMessage) -> AiChatMessage) {
        session = session.copy(
            messages = session.messages.map { message -> if (message.id == id) transform(message) else message },
            updatedAtEpochMs = System.currentTimeMillis(),
        )
    }
}
'''

UI = r'''package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.Send
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.ChatBubble
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.DeleteSweep
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.MoreVert
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.StopCircle
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.tianji.probabilitylab.nativev4.ai.AiChatArchiveSummary
import com.tianji.probabilitylab.nativev4.ai.AiChatCandidateRecord
import com.tianji.probabilitylab.nativev4.ai.AiChatController
import com.tianji.probabilitylab.nativev4.ai.AiChatMessage
import com.tianji.probabilitylab.nativev4.ai.AiChatPersona
import com.tianji.probabilitylab.nativev4.ai.AiChatRole
import com.tianji.probabilitylab.nativev4.ai.AiChatSession
import com.tianji.probabilitylab.nativev4.ai.AiConfig
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun AiChatFloatingButton(onClick: () -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalTianjiColors.current
    FloatingActionButton(
        onClick = onClick,
        modifier = modifier.size(54.dp),
        shape = RoundedCornerShape(19.dp),
        containerColor = colors.accent,
        contentColor = Color.White,
    ) {
        Icon(Icons.Rounded.ChatBubble, contentDescription = "打开分析对话")
    }
}

@Composable
fun AiChatDialog(
    controller: AiChatController,
    configs: List<AiConfig>,
    modelCatalogs: Map<String, List<String>>,
    snapshot: DrawSnapshot?,
    report: ForecastReport?,
    onRefresh: () -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    val completeConfigs = remember(configs) { configs.filter(AiConfig::isComplete) }
    val session = controller.session
    val selectedConfig = completeConfigs.firstOrNull { it.id == session.profileId }
        ?: completeConfigs.firstOrNull()
    fun modelOptions(config: AiConfig?): List<String> = buildList {
        if (config != null) {
            config.model.trim().takeIf(String::isNotBlank)?.let(::add)
            addAll(modelCatalogs[config.id].orEmpty())
            addAll(config.provider.fallbackModels)
        }
        if (session.profileId == config?.id) session.model.takeIf(String::isNotBlank)?.let(::add)
    }.map(String::trim).filter(String::isNotBlank).distinct()

    val models = modelOptions(selectedConfig)
    val selectedModel = session.model.takeIf { it in models }
        ?: selectedConfig?.model?.takeIf(String::isNotBlank)
        ?: models.firstOrNull().orEmpty()
    val lotteryKey = snapshot?.lottery?.apiKey.orEmpty()
    val targetPeriod = report?.targetPeriod
    var input by rememberSaveable { mutableStateOf("") }
    var showHistory by rememberSaveable { mutableStateOf(false) }
    var showNewConversation by rememberSaveable { mutableStateOf(false) }
    var moreExpanded by rememberSaveable { mutableStateOf(false) }
    val listState = rememberLazyListState()

    fun openContext(config: AiConfig?, model: String) {
        controller.selectContext(
            profileId = config?.id.orEmpty(),
            profileName = config?.displayName.orEmpty(),
            model = model,
            lotteryKey = lotteryKey,
            targetPeriod = targetPeriod,
            latestPeriod = snapshot?.latest?.period,
            latestNumbers = snapshot?.latest?.numbers.orEmpty(),
        )
    }

    val signature = completeConfigs.joinToString("|") { "${it.id}:${it.model}" } +
        modelCatalogs.entries.sortedBy { it.key }.joinToString("|") { it.value.joinToString(",") }
    LaunchedEffect(signature, lotteryKey, targetPeriod, snapshot?.latest?.period) {
        openContext(selectedConfig, selectedModel)
    }
    LaunchedEffect(
        session.messages.size,
        session.messages.lastOrNull()?.content?.length,
        session.isRunning,
        session.candidates.size,
    ) {
        val last = session.messages.lastIndex
        if (last >= 0) listState.animateScrollToItem(last)
    }

    fun submit(value: String) {
        val config = completeConfigs.firstOrNull { it.id == controller.session.profileId }
            ?: selectedConfig
        val activeSnapshot = snapshot
        val activeReport = report
        val question = value.trim()
        if (config == null || activeSnapshot == null || activeReport == null || question.isBlank()) return
        input = ""
        controller.send(
            config = config.copy(model = controller.session.model.ifBlank { selectedModel }),
            snapshot = activeSnapshot,
            report = activeReport,
            question = question,
        )
    }

    Dialog(
        onDismissRequest = { controller.cancel(); onDismiss() },
        properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false),
    ) {
        Surface(
            modifier = Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.systemBars),
            color = colors.page,
        ) {
            Column(
                modifier = Modifier.fillMaxSize().imePadding().padding(horizontal = 14.dp),
            ) {
                ChatTopBar(
                    session = session,
                    onNew = { showNewConversation = true },
                    onHistory = { showHistory = true },
                    onClose = { controller.cancel(); onDismiss() },
                    onMore = { moreExpanded = true },
                    moreExpanded = moreExpanded,
                    dismissMore = { moreExpanded = false },
                    onRefresh = onRefresh,
                    onClear = controller::clear,
                    onDelete = controller::deleteCurrent,
                )

                CompactControlCard(
                    configs = completeConfigs,
                    selectedConfig = selectedConfig,
                    models = models,
                    selectedModel = selectedModel,
                    session = session,
                    snapshot = snapshot,
                    report = report,
                    onConfig = { config ->
                        val next = modelOptions(config).firstOrNull { it == config.model }
                            ?: modelOptions(config).firstOrNull().orEmpty()
                        openContext(config, next)
                    },
                    onModel = { openContext(selectedConfig, it) },
                    onPersona = controller::selectPersona,
                )
                Spacer(Modifier.height(10.dp))

                val candidatesByMessage = session.candidates.groupBy(AiChatCandidateRecord::messageId)
                LazyColumn(
                    state = listState,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    contentPadding = PaddingValues(top = 4.dp, bottom = 14.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    if (session.messages.isEmpty()) {
                        item("welcome") {
                            WelcomePanel(
                                persona = AiChatPersona.fromId(session.personaId),
                                enabled = selectedConfig != null && snapshot != null && report != null,
                                onPrompt = ::submit,
                            )
                        }
                    }
                    items(session.messages, key = AiChatMessage::id) { message ->
                        ChatMessageBubble(
                            message = message,
                            isStreaming = message.id == session.streamingMessageId && session.isRunning,
                        )
                        candidatesByMessage[message.id].orEmpty().forEach { record ->
                            Spacer(Modifier.height(8.dp))
                            ChatPredictionCard(record)
                        }
                    }
                    val detached = session.candidates.filter { it.messageId.isBlank() }
                    items(detached, key = AiChatCandidateRecord::id) { record -> ChatPredictionCard(record) }
                    if (session.isRunning) {
                        item("running") {
                            StreamingStatus(session.progress, controller::cancel)
                        }
                    }
                    session.rolloverNotice?.let { notice ->
                        item("rollover") { SystemEventChip(notice) }
                    }
                    session.error?.let { error ->
                        item("error") {
                            Surface(
                                shape = RoundedCornerShape(18.dp),
                                color = colors.red.copy(alpha = 0.08f),
                                border = androidx.compose.foundation.BorderStroke(1.dp, colors.red.copy(alpha = 0.2f)),
                            ) {
                                Text(error, color = colors.red, fontSize = 13.sp, modifier = Modifier.padding(14.dp))
                            }
                        }
                    }
                }

                ChatComposer(
                    input = input,
                    onInput = { input = it },
                    enabled = selectedConfig != null && snapshot != null && report != null && !session.isRunning,
                    isRunning = session.isRunning,
                    placeholder = AiChatPersona.fromId(session.personaId).quickPrompts.firstOrNull()
                        ?: "继续追问，或告诉它上一期哪里需要调整",
                    onSend = { submit(input) },
                    onStop = controller::cancel,
                )
            }
        }
    }

    if (showHistory) {
        ConversationHistoryDialog(
            items = controller.archives.filter { lotteryKey.isBlank() || it.lotteryKey == lotteryKey },
            currentId = session.archiveId,
            onOpen = { controller.openArchive(it); showHistory = false },
            onDismiss = { showHistory = false },
        )
    }
    if (showNewConversation) {
        NewConversationDialog(
            hasHistory = session.messages.isNotEmpty(),
            onBlank = {
                controller.newConversation(
                    selectedConfig?.id.orEmpty(), selectedConfig?.displayName.orEmpty(), selectedModel,
                    lotteryKey, targetPeriod, inheritStrategy = false,
                )
                showNewConversation = false
            },
            onContinue = {
                controller.newConversation(
                    selectedConfig?.id.orEmpty(), selectedConfig?.displayName.orEmpty(), selectedModel,
                    lotteryKey, targetPeriod, inheritStrategy = true,
                )
                showNewConversation = false
            },
            onDismiss = { showNewConversation = false },
        )
    }
}

@Composable
private fun ChatTopBar(
    session: AiChatSession,
    onNew: () -> Unit,
    onHistory: () -> Unit,
    onClose: () -> Unit,
    onMore: () -> Unit,
    moreExpanded: Boolean,
    dismissMore: () -> Unit,
    onRefresh: () -> Unit,
    onClear: () -> Unit,
    onDelete: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier.fillMaxWidth().height(68.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier.size(42.dp).clip(RoundedCornerShape(15.dp))
                .background(colors.accent.copy(alpha = 0.14f)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Rounded.AutoAwesome, null, tint = colors.accent)
        }
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text("天机", color = colors.text, fontSize = 21.sp, fontWeight = FontWeight.ExtraBold)
            Text(
                session.title.ifBlank { "新对话" },
                color = colors.textDim,
                fontSize = 11.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        ContextUsagePill(session.contextUsagePercent)
        IconButton(onClick = onNew, enabled = !session.isRunning) {
            Icon(Icons.Rounded.Add, "新建对话", tint = colors.textSoft)
        }
        IconButton(onClick = onHistory, enabled = !session.isRunning) {
            Icon(Icons.Rounded.History, "对话历史", tint = colors.textSoft)
        }
        Box {
            IconButton(onClick = onMore, enabled = !session.isRunning) {
                Icon(Icons.Rounded.MoreVert, "更多", tint = colors.textSoft)
            }
            DropdownMenu(expanded = moreExpanded, onDismissRequest = dismissMore) {
                DropdownMenuItem(
                    text = { Text("刷新开奖历史") },
                    leadingIcon = { Icon(Icons.Rounded.Refresh, null) },
                    onClick = { dismissMore(); onRefresh() },
                )
                DropdownMenuItem(
                    text = { Text("清空当前对话") },
                    leadingIcon = { Icon(Icons.Rounded.DeleteSweep, null) },
                    onClick = { dismissMore(); onClear() },
                )
                DropdownMenuItem(
                    text = { Text("删除当前会话") },
                    leadingIcon = { Icon(Icons.Rounded.DeleteSweep, null) },
                    onClick = { dismissMore(); onDelete() },
                )
            }
        }
        IconButton(onClick = onClose) { Icon(Icons.Rounded.Close, "关闭", tint = colors.textSoft) }
    }
}

@Composable
private fun ContextUsagePill(percent: Int) {
    val colors = LocalTianjiColors.current
    val tint = when {
        percent >= 80 -> colors.amber
        percent >= 55 -> colors.accent
        else -> colors.green
    }
    Surface(shape = CircleShape, color = tint.copy(alpha = 0.1f)) {
        Text(
            "上下文 ${percent.coerceIn(0, 100)}%",
            color = tint,
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp),
        )
    }
}

@Composable
private fun CompactControlCard(
    configs: List<AiConfig>,
    selectedConfig: AiConfig?,
    models: List<String>,
    selectedModel: String,
    session: AiChatSession,
    snapshot: DrawSnapshot?,
    report: ForecastReport?,
    onConfig: (AiConfig) -> Unit,
    onModel: (String) -> Unit,
    onPersona: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    Surface(
        shape = RoundedCornerShape(22.dp),
        color = Color.White.copy(alpha = 0.035f),
        border = androidx.compose.foundation.BorderStroke(1.dp, colors.line),
    ) {
        Column(Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                SelectorPill(
                    label = "配置",
                    value = selectedConfig?.displayName ?: "未配置",
                    options = configs.map { it.id to it.displayName },
                    selectedKey = selectedConfig?.id.orEmpty(),
                    onSelect = { id -> configs.firstOrNull { it.id == id }?.let(onConfig) },
                )
                SelectorPill(
                    label = "模型",
                    value = selectedModel.ifBlank { "未选择" },
                    options = models.map { it to it },
                    selectedKey = selectedModel,
                    onSelect = onModel,
                )
                SelectorPill(
                    label = "人设",
                    value = AiChatPersona.fromId(session.personaId).displayName,
                    options = AiChatPersona.entries.map { it.id to it.displayName },
                    selectedKey = session.personaId,
                    onSelect = onPersona,
                )
            }
            Spacer(Modifier.height(9.dp))
            val ready = snapshot != null && report != null && selectedConfig != null
            val statusColor = if (ready) colors.green else colors.amber
            Text(
                if (ready) {
                    "${snapshot!!.history.takeLast(120).size}期真实接口历史 · 当前目标期 ${report!!.targetPeriod} · 对话可跨期开奖继续"
                } else {
                    "请先准备开奖历史和完整 AI 配置"
                },
                color = statusColor,
                fontSize = 10.5.sp,
                lineHeight = 15.sp,
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp))
                    .background(statusColor.copy(alpha = 0.07f))
                    .padding(horizontal = 10.dp, vertical = 8.dp),
            )
            Text(
                "你说“上一期没中、降低热号权重”等反馈会保留在当前对话；只调整对话分析策略，不修改正式预测模型参数。",
                color = colors.textDim,
                fontSize = 9.5.sp,
                lineHeight = 14.sp,
                modifier = Modifier.padding(top = 7.dp, start = 2.dp, end = 2.dp),
            )
        }
    }
}

@Composable
private fun SelectorPill(
    label: String,
    value: String,
    options: List<Pair<String, String>>,
    selectedKey: String,
    onSelect: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    var expanded by remember { mutableStateOf(false) }
    Box {
        Surface(
            modifier = Modifier.clickable(enabled = options.isNotEmpty()) { expanded = true },
            shape = RoundedCornerShape(14.dp),
            color = colors.accent.copy(alpha = 0.08f),
            border = androidx.compose.foundation.BorderStroke(1.dp, colors.accent.copy(alpha = 0.17f)),
        ) {
            Column(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
                Text(label, color = colors.textDim, fontSize = 8.5.sp)
                Text(value, color = colors.text, fontSize = 11.5.sp, fontWeight = FontWeight.Bold)
            }
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { (key, text) ->
                DropdownMenuItem(
                    text = {
                        Text(text, fontWeight = if (key == selectedKey) FontWeight.Bold else FontWeight.Normal)
                    },
                    onClick = { expanded = false; onSelect(key) },
                )
            }
        }
    }
}

@Composable
private fun WelcomePanel(persona: AiChatPersona, enabled: Boolean, onPrompt: (String) -> Unit) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = Modifier.fillMaxWidth().padding(top = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier.size(64.dp).clip(RoundedCornerShape(22.dp))
                .background(colors.accent.copy(alpha = 0.13f)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Rounded.AutoAwesome, null, tint = colors.accent, modifier = Modifier.size(30.dp))
        }
        Spacer(Modifier.height(14.dp))
        Text("开始一段持续分析", color = colors.text, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
        Text(
            "可以跨期开奖继续复盘，也可以随时新建空白对话。",
            color = colors.textDim,
            fontSize = 12.sp,
            modifier = Modifier.padding(top = 5.dp, bottom = 18.dp),
        )
        persona.quickPrompts.forEach { prompt ->
            Surface(
                modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp)
                    .clickable(enabled = enabled) { onPrompt(prompt) },
                shape = RoundedCornerShape(18.dp),
                color = Color.White.copy(alpha = 0.035f),
                border = androidx.compose.foundation.BorderStroke(1.dp, colors.line),
            ) {
                Text(
                    prompt,
                    color = if (enabled) colors.textSoft else colors.textDim,
                    fontSize = 13.sp,
                    lineHeight = 18.sp,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
                )
            }
        }
    }
}

@Composable
private fun ChatMessageBubble(message: AiChatMessage, isStreaming: Boolean) {
    val colors = LocalTianjiColors.current
    if (message.role == AiChatRole.SYSTEM) {
        SystemEventChip(message.content)
        return
    }
    val user = message.role == AiChatRole.USER
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = if (user) Alignment.CenterEnd else Alignment.CenterStart,
    ) {
        Column(
            modifier = Modifier.widthIn(max = if (user) 330.dp else 390.dp)
                .animateContentSize()
                .clip(
                    RoundedCornerShape(
                        topStart = 21.dp,
                        topEnd = 21.dp,
                        bottomStart = if (user) 21.dp else 7.dp,
                        bottomEnd = if (user) 7.dp else 21.dp,
                    ),
                )
                .background(if (user) colors.accent.copy(alpha = 0.2f) else Color.White.copy(alpha = 0.045f))
                .border(
                    1.dp,
                    if (user) colors.accent.copy(alpha = 0.26f) else colors.line,
                    RoundedCornerShape(21.dp),
                )
                .padding(horizontal = 15.dp, vertical = 13.dp),
        ) {
            if (!user) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Rounded.AutoAwesome, null, tint = colors.accent, modifier = Modifier.size(15.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("天机分析", color = colors.accent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
                Spacer(Modifier.height(8.dp))
            }
            val visible = when {
                message.content.isNotBlank() && isStreaming -> message.content + " ▍"
                message.content.isNotBlank() -> message.content
                isStreaming -> "正在思考，等待第一段正文…"
                else -> ""
            }
            Text(
                visible,
                color = if (message.content.isBlank()) colors.textDim else colors.textSoft,
                fontSize = 14.sp,
                lineHeight = 21.sp,
            )
            message.latencyMs?.let {
                Text(
                    "${it / 1_000.0}s",
                    color = colors.textDim,
                    fontSize = 9.sp,
                    modifier = Modifier.align(Alignment.End).padding(top = 7.dp),
                )
            }
        }
    }
}

@Composable
private fun SystemEventChip(text: String) {
    val colors = LocalTianjiColors.current
    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        Text(
            text,
            color = colors.textDim,
            fontSize = 10.5.sp,
            lineHeight = 15.sp,
            modifier = Modifier.widthIn(max = 360.dp).clip(RoundedCornerShape(14.dp))
                .background(colors.accent.copy(alpha = 0.055f))
                .padding(horizontal = 12.dp, vertical = 8.dp),
        )
    }
}

@Composable
private fun StreamingStatus(progress: String, onCancel: () -> Unit) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp))
            .background(colors.accent.copy(alpha = 0.06f))
            .border(1.dp, colors.accent.copy(alpha = 0.14f), RoundedCornerShape(18.dp))
            .padding(horizontal = 13.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        CircularProgressIndicator(modifier = Modifier.size(16.dp), color = colors.accent, strokeWidth = 2.dp)
        Spacer(Modifier.width(9.dp))
        Text(progress.ifBlank { "正在继续生成…" }, color = colors.textDim, fontSize = 11.sp, modifier = Modifier.weight(1f))
        IconButton(onClick = onCancel, modifier = Modifier.size(34.dp)) {
            Icon(Icons.Rounded.StopCircle, "停止", tint = colors.amber)
        }
    }
}

@Composable
private fun ChatPredictionCard(record: AiChatCandidateRecord) {
    val colors = LocalTianjiColors.current
    val hit = record.actualNumber?.let { it in record.prediction.top6 }
    Surface(
        shape = RoundedCornerShape(22.dp),
        color = colors.accent.copy(alpha = 0.075f),
        border = androidx.compose.foundation.BorderStroke(1.dp, colors.accent.copy(alpha = 0.22f)),
    ) {
        Column(Modifier.padding(15.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "对话候选 · 第${record.prediction.position + 1}名",
                    color = colors.accent,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.ExtraBold,
                    modifier = Modifier.weight(1f),
                )
                hit?.let {
                    Text(
                        if (it) "已命中" else "未命中",
                        color = if (it) colors.green else colors.amber,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            Text(
                "目标期 ${record.targetPeriod} · 仅属于本次对话策略，不计入正式成绩",
                color = colors.textDim,
                fontSize = 10.sp,
                modifier = Modifier.padding(top = 3.dp, bottom = 12.dp),
            )
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                record.prediction.top6.forEach { number -> NumberBall(number) }
            }
            record.actualNumber?.let { actual ->
                Text(
                    "实际号码：$actual",
                    color = colors.textSoft,
                    fontSize = 11.sp,
                    modifier = Modifier.padding(top = 11.dp),
                )
            }
        }
    }
}

@Composable
private fun NumberBall(number: Int) {
    val colors = LocalTianjiColors.current
    Box(
        modifier = Modifier.size(38.dp).clip(CircleShape)
            .background(colors.accent.copy(alpha = 0.18f))
            .border(1.dp, colors.accent.copy(alpha = 0.34f), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Text(number.toString(), color = colors.text, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold)
    }
}

@Composable
private fun ChatComposer(
    input: String,
    onInput: (String) -> Unit,
    enabled: Boolean,
    isRunning: Boolean,
    placeholder: String,
    onSend: () -> Unit,
    onStop: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = Modifier.fillMaxWidth().padding(bottom = 10.dp),
        shape = RoundedCornerShape(25.dp),
        color = Color.White.copy(alpha = 0.05f),
        border = androidx.compose.foundation.BorderStroke(1.dp, colors.line),
    ) {
        Row(
            modifier = Modifier.padding(6.dp),
            verticalAlignment = Alignment.Bottom,
        ) {
            OutlinedTextField(
                value = input,
                onValueChange = onInput,
                enabled = enabled,
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(20.dp),
                placeholder = { Text(placeholder, fontSize = 12.sp, maxLines = 2) },
                minLines = 1,
                maxLines = 5,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { if (enabled && input.isNotBlank()) onSend() }),
            )
            Spacer(Modifier.width(7.dp))
            Button(
                onClick = if (isRunning) onStop else onSend,
                enabled = isRunning || (enabled && input.isNotBlank()),
                modifier = Modifier.size(49.dp),
                shape = CircleShape,
                contentPadding = PaddingValues(0.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isRunning) colors.amber else colors.accent,
                ),
            ) {
                Icon(
                    if (isRunning) Icons.Rounded.StopCircle else Icons.AutoMirrored.Rounded.Send,
                    if (isRunning) "停止" else "发送",
                    tint = Color.White,
                )
            }
        }
    }
}

@Composable
private fun ConversationHistoryDialog(
    items: List<AiChatArchiveSummary>,
    currentId: String,
    onOpen: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Dialog(onDismissRequest = onDismiss) {
        Surface(
            modifier = Modifier.fillMaxWidth().heightIn(max = 660.dp),
            shape = RoundedCornerShape(28.dp),
            color = colors.page,
            border = androidx.compose.foundation.BorderStroke(1.dp, colors.line),
        ) {
            Column(Modifier.padding(18.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("对话历史", color = colors.text, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                        Text("每条会话都可以重新打开并继续聊天", color = colors.textDim, fontSize = 11.sp)
                    }
                    IconButton(onClick = onDismiss) { Icon(Icons.Rounded.Close, "关闭", tint = colors.textSoft) }
                }
                Spacer(Modifier.height(10.dp))
                LazyColumn(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    items(items.sortedByDescending(AiChatArchiveSummary::updatedAtEpochMs), key = AiChatArchiveSummary::id) { item ->
                        Surface(
                            modifier = Modifier.fillMaxWidth().clickable { onOpen(item.id) },
                            shape = RoundedCornerShape(18.dp),
                            color = if (item.id == currentId) colors.accent.copy(alpha = 0.1f)
                                else Color.White.copy(alpha = 0.035f),
                            border = androidx.compose.foundation.BorderStroke(
                                1.dp,
                                if (item.id == currentId) colors.accent.copy(alpha = 0.25f) else colors.line,
                            ),
                        ) {
                            Column(Modifier.padding(14.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        item.title,
                                        color = colors.text,
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.Bold,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                        modifier = Modifier.weight(1f),
                                    )
                                    Text(formatTime(item.updatedAtEpochMs), color = colors.textDim, fontSize = 9.sp)
                                }
                                Text(
                                    "${item.model} · ${item.messageCount}条消息 · 目标期${item.targetPeriod.ifBlank { "待同步" }}",
                                    color = colors.accent,
                                    fontSize = 10.sp,
                                    modifier = Modifier.padding(top = 4.dp),
                                )
                                if (item.preview.isNotBlank()) {
                                    Text(
                                        item.preview,
                                        color = colors.textDim,
                                        fontSize = 11.sp,
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis,
                                        modifier = Modifier.padding(top = 5.dp),
                                    )
                                }
                            }
                        }
                    }
                    if (items.isEmpty()) {
                        item { Text("暂无对话", color = colors.textDim, modifier = Modifier.padding(24.dp)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun NewConversationDialog(
    hasHistory: Boolean,
    onBlank: () -> Unit,
    onContinue: () -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(28.dp),
            color = colors.page,
            border = androidx.compose.foundation.BorderStroke(1.dp, colors.line),
        ) {
            Column(Modifier.padding(20.dp)) {
                Text("新建对话", color = colors.text, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                Text(
                    "空白开始，或只继承上一段的策略摘要与复盘结论。",
                    color = colors.textDim,
                    fontSize = 11.sp,
                    modifier = Modifier.padding(top = 5.dp, bottom = 14.dp),
                )
                ChoiceCard("空白新对话", "不带入任何旧上下文", onBlank)
                Spacer(Modifier.height(9.dp))
                ChoiceCard(
                    "继承策略继续",
                    "保留明确的调整要求、近期候选与命中复盘，不复制整段原文",
                    onContinue,
                    enabled = hasHistory,
                )
            }
        }
    }
}

@Composable
private fun ChoiceCard(title: String, subtitle: String, onClick: () -> Unit, enabled: Boolean = true) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(enabled = enabled, onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        color = colors.accent.copy(alpha = if (enabled) 0.08f else 0.03f),
        border = androidx.compose.foundation.BorderStroke(1.dp, colors.accent.copy(alpha = 0.16f)),
    ) {
        Column(Modifier.padding(15.dp)) {
            Text(title, color = if (enabled) colors.text else colors.textDim, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            Text(subtitle, color = colors.textDim, fontSize = 10.5.sp, lineHeight = 15.sp, modifier = Modifier.padding(top = 4.dp))
        }
    }
}

private fun formatTime(epochMs: Long): String =
    SimpleDateFormat("MM-dd HH:mm", Locale.getDefault()).format(Date(epochMs))
'''

CODEC_TEST = r'''package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AiChatArchiveCodecTest {
    @Test
    fun roundTripKeepsConversationMemoryMessagesAndCandidateHistory() {
        val prediction = AiChatPrediction(
            position = 0,
            top6 = listOf(9, 1, 6, 3, 5, 10),
            top7 = listOf(9, 1, 6, 3, 5, 10, 2),
            probabilities = List(10) { index -> (index + 1).toDouble() },
        )
        val archive = AiChatArchive(
            id = "conversation-1",
            lotteryKey = "azxy10",
            profileId = "profile-1",
            profileName = "DeepSeek 主力",
            model = "deepseek-v4-pro",
            title = "第一名跨期调整",
            targetPeriod = "21347341",
            personaId = AiChatPersona.TREND.id,
            memorySummary = "上一期未中，用户要求降低短期热号权重",
            continuationOf = "conversation-0",
            messages = listOf(
                AiChatMessage(id = "u1", role = AiChatRole.USER, content = "上一期没中，调整策略", targetPeriod = "21347341"),
                AiChatMessage(id = "a1", role = AiChatRole.ASSISTANT, content = "本期降低短窗权重", targetPeriod = "21347341"),
            ),
            candidates = listOf(
                AiChatCandidateRecord(
                    id = "c1",
                    messageId = "a1",
                    targetPeriod = "21347341",
                    prediction = prediction,
                    actualNumber = 4,
                    resolvedPeriod = "21347341",
                ),
            ),
            createdAtEpochMs = 100L,
            updatedAtEpochMs = 200L,
        )

        val decoded = AiChatArchiveCodec.decode(AiChatArchiveCodec.encode(listOf(archive))).single()

        assertEquals(archive.id, decoded.id)
        assertEquals("第一名跨期调整", decoded.title)
        assertEquals("上一期未中，用户要求降低短期热号权重", decoded.memorySummary)
        assertEquals("conversation-0", decoded.continuationOf)
        assertEquals(listOf("上一期没中，调整策略", "本期降低短窗权重"), decoded.messages.map { it.content })
        assertEquals(listOf(9, 1, 6, 3, 5, 10), decoded.candidates.single().prediction.top6)
        assertEquals(4, decoded.candidates.single().actualNumber)
        assertTrue(AiChatArchiveCodec.summary(decoded).hasPrediction)
    }

    @Test
    fun newConversationIdsDoNotDependOnTargetPeriod() {
        val first = AiChatConversationId.newId("azxy10", "profile", "deepseek-v4-pro")
        val second = AiChatConversationId.newId("azxy10", "profile", "deepseek-v4-pro")
        assertNotEquals(first, second)
    }

    @Test
    fun legacySchemaOnePredictionMigratesIntoCandidateHistory() {
        val legacy = """{"schema":1,"archives":[{"id":"legacy","lottery_key":"azxy10","profile_id":"p","profile_name":"P","model":"m","target_period":"100","persona_id":"trend","created_at":1,"updated_at":2,"messages":[{"id":"a","role":"ASSISTANT","content":"结果","created_at":1,"latency_ms":null}],"prediction":{"position":0,"top6":[1,2,3,4,5,6],"top7":[1,2,3,4,5,6,7],"probabilities":[1,1,1,1,1,1,1,1,1,1]}}]}"""
        val decoded = AiChatArchiveCodec.decode(legacy).single()
        assertEquals(1, decoded.candidates.size)
        assertEquals("100", decoded.candidates.single().targetPeriod)
    }
}
'''

CONTEXT_TEST = r'''package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertTrue
import org.junit.Test

class AiChatContextWindowTest {
    @Test
    fun longConversationTriggersRolloverWithoutDroppingStoredMessages() {
        val messages = (0 until 80).map { index ->
            AiChatMessage(
                role = if (index % 2 == 0) AiChatRole.USER else AiChatRole.ASSISTANT,
                content = "第$index轮对话：" + "分析内容".repeat(120),
            )
        }
        val plan = AiChatProtocol.planContext(messages, "")
        assertTrue(plan.shouldRollover)
        assertTrue(plan.messages.isNotEmpty())
        assertTrue(plan.messages.size < messages.size)
    }

    @Test
    fun memorySummaryKeepsExplicitStrategyFeedbackAndOutcome() {
        val messages = listOf(
            AiChatMessage(role = AiChatRole.USER, content = "上一期没中，降低最近20期热号权重"),
            AiChatMessage(role = AiChatRole.ASSISTANT, content = "下一期将提高中长窗口稳定性权重"),
        )
        val candidate = AiChatCandidateRecord(
            messageId = "a",
            targetPeriod = "101",
            prediction = AiChatPrediction(0, listOf(1,2,3,4,5,6), listOf(1,2,3,4,5,6,7), List(10) { 0.1 }),
            actualNumber = 9,
            resolvedPeriod = "101",
        )
        val summary = AiChatProtocol.buildMemorySummary("", messages, listOf(candidate))
        assertTrue(summary.contains("降低最近20期热号权重"))
        assertTrue(summary.contains("六码未中"))
    }
}
'''


def write(path: str, content: str):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

write("app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiFreeChat.kt", FREE_CHAT)
write("app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatArchiveStore.kt", ARCHIVE_STORE)
write("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AiChatDialog.kt", UI)
write("app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiChatArchiveCodecTest.kt", CODEC_TEST)
write("app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiChatContextWindowTest.kt", CONTEXT_TEST)

controller_path = ROOT / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt"
controller = controller_path.read_text(encoding="utf-8")
controller, count = re.subn(
    r"class AiChatController\(context: Context\) \{.*?\n\}\n\ninternal data class AiPositionStatistics",
    CONTROLLER_HEAD + "\n\ninternal data class AiPositionStatistics",
    controller,
    count=1,
    flags=re.S,
)
if count != 1:
    raise SystemExit("failed to replace AiChatController class")

controller = controller.replace(
    "previousMessages: List<AiChatMessage>,\n        question: String,",
    "previousMessages: List<AiChatMessage>,\n        memorySummary: String,\n        question: String,",
    1,
)
controller = controller.replace(
    "previousMessages = previousMessages,\n            question = question,",
    "previousMessages = previousMessages,\n            memorySummary = memorySummary,\n            question = question,",
    1,
)
controller = controller.replace(
    "previousMessages: List<AiChatMessage>,\n        question: String,\n        wantsPrediction: Boolean,",
    "previousMessages: List<AiChatMessage>,\n        memorySummary: String,\n        question: String,\n        wantsPrediction: Boolean,",
    1,
)
old_context_block = '''        put(\n            JSONObject()\n                .put("role", "user")\n                .put(\n                    "content",\n                    "以下是客户端刚刚根据当前开奖接口历史逐期计算的事实。所有回答只能以这些事实为依据：\\n${context}",\n                ),\n        )\n        AiChatProtocol.trimHistory(previousMessages).forEach { message ->\n            put(\n                JSONObject()\n                    .put("role", if (message.role == AiChatRole.USER) "user" else "assistant")\n                    .put("content", message.content),\n            )\n        }'''
new_context_block = '''        put(\n            JSONObject()\n                .put("role", "user")\n                .put(\n                    "content",\n                    "以下是客户端刚刚根据当前开奖接口历史逐期计算的事实。所有回答只能以这些事实为依据：\\n${context}",\n                ),\n        )\n        if (memorySummary.isNotBlank()) {\n            put(\n                JSONObject()\n                    .put("role", "system")\n                    .put(\n                        "content",\n                        "以下是客户端从上一段长期对话压缩的策略记忆。它只代表用户曾明确提出的偏好、复盘和候选核验，不是新的开奖事实，也不代表模型参数已训练：\\n$memorySummary",\n                    ),\n            )\n        }\n        previousMessages.filter { it.content.isNotBlank() }.forEach { message ->\n            val role = when (message.role) {\n                AiChatRole.SYSTEM -> "system"\n                AiChatRole.USER -> "user"\n                AiChatRole.ASSISTANT -> "assistant"\n            }\n            put(JSONObject().put("role", role).put("content", message.content))\n        }'''
if old_context_block not in controller:
    raise SystemExit("failed to locate conversation context block")
controller = controller.replace(old_context_block, new_context_block, 1)
controller = controller.replace(
    '"使用简体中文直接、自然地回答，支持连续追问。" +',
    '"使用简体中文直接、自然地回答，支持跨期开奖的连续追问和复盘。" +\n                "用户可以要求调整当前对话的分析侧重点；要明确这只影响后续对话研判，不会改写正式本机预测模型参数。" +',
    1,
)
controller_path.write_text(controller, encoding="utf-8")

print("chat v2 sources applied")
