package com.tianji.probabilitylab.nativev4.ai

import android.content.Context
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * App-private archive for chat conversations and chat-only candidate cards.
 * It is deliberately separate from the official forward-forecast database.
 */
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
            messages = archive.messages
                .filter { it.content.isNotBlank() }
                .takeLast(MAX_MESSAGES_PER_ARCHIVE),
            updatedAtEpochMs = System.currentTimeMillis(),
        )
        val all = (loadAll().filterNot { it.id == normalized.id } + normalized)
            .sortedByDescending(AiChatArchive::updatedAtEpochMs)
            .take(MAX_ARCHIVES)
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
        const val MAX_ARCHIVES = 1_000
        const val MAX_MESSAGES_PER_ARCHIVE = 60
    }
}

object AiChatArchiveCodec {
    fun encode(archives: List<AiChatArchive>): String = JSONObject()
        .put("schema", 1)
        .put("archives", JSONArray(archives.map(::toJson)))
        .toString()

    fun decode(text: String): List<AiChatArchive> {
        if (text.isBlank()) return emptyList()
        val array = JSONObject(text).optJSONArray("archives") ?: return emptyList()
        return buildList {
            for (index in 0 until array.length()) {
                array.optJSONObject(index)?.toArchiveOrNull()?.let(::add)
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
        personaId = archive.personaId,
        messageCount = archive.messages.size,
        hasPrediction = archive.prediction != null,
        updatedAtEpochMs = archive.updatedAtEpochMs,
    )

    private fun toJson(archive: AiChatArchive): JSONObject = JSONObject()
        .put("id", archive.id)
        .put("lottery_key", archive.lotteryKey)
        .put("profile_id", archive.profileId)
        .put("profile_name", archive.profileName)
        .put("model", archive.model)
        .put("target_period", archive.targetPeriod)
        .put("persona_id", archive.personaId)
        .put("created_at", archive.createdAtEpochMs)
        .put("updated_at", archive.updatedAtEpochMs)
        .put(
            "messages",
            JSONArray(archive.messages.map { message ->
                JSONObject()
                    .put("id", message.id)
                    .put("role", message.role.name)
                    .put("content", message.content)
                    .put("created_at", message.createdAtEpochMs)
                    .put("latency_ms", message.latencyMs ?: JSONObject.NULL)
            }),
        )
        .put(
            "prediction",
            archive.prediction?.let { prediction ->
                JSONObject()
                    .put("position", prediction.position)
                    .put("top6", JSONArray(prediction.top6))
                    .put("top7", JSONArray(prediction.top7))
                    .put("probabilities", JSONArray(prediction.probabilities))
            } ?: JSONObject.NULL,
        )

    private fun JSONObject.toArchiveOrNull(): AiChatArchive? = runCatching {
        val lotteryKey = getString("lottery_key")
        val profileId = getString("profile_id")
        val model = getString("model")
        val targetPeriod = getString("target_period")
        val id = optString("id").ifBlank {
            AiChatArchiveId.of(lotteryKey, targetPeriod, profileId, model)
        }
        require(lotteryKey.isNotBlank() && profileId.isNotBlank() && model.isNotBlank())
        require(targetPeriod.isNotBlank())
        AiChatArchive(
            id = id,
            lotteryKey = lotteryKey,
            profileId = profileId,
            profileName = optString("profile_name"),
            model = model,
            targetPeriod = targetPeriod,
            personaId = AiChatPersona.fromId(optString("persona_id")).id,
            messages = optJSONArray("messages").toMessages(),
            prediction = optJSONObject("prediction")?.toPredictionOrNull(),
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
                        createdAtEpochMs = item.optLong("created_at", System.currentTimeMillis()),
                        latencyMs = item.optLong("latency_ms", -1L).takeIf { it >= 0L },
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
        (0 until length()).mapNotNull { index ->
            optDouble(index, Double.NaN).takeIf(Double::isFinite)
        }
}
