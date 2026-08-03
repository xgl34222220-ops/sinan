package com.tianji.probabilitylab.nativev4.ai

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
