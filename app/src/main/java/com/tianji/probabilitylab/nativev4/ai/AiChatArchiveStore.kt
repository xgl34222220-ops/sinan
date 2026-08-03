package com.tianji.probabilitylab.nativev4.ai

import android.content.Context
import android.content.ContentValues
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.tianji.probabilitylab.nativev4.model.Draw
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** App-private multi-conversation store, deliberately separate from official forecast records. */
class AiChatArchiveStore(context: Context) {
    private val appContext = context.applicationContext
    private val helper = ArchiveDb(appContext)
    private val legacyFile = File(appContext.filesDir, LEGACY_FILE_NAME)

    init {
        migrateLegacyJson()
    }

    @Synchronized
    fun loadAll(): List<AiChatArchive> = helper.readableDatabase.rawQuery(
        "SELECT payload FROM chat_archives ORDER BY updated_at DESC LIMIT $MAX_CONVERSATIONS",
        null,
    ).use { cursor ->
        buildList {
            while (cursor.moveToNext()) {
                AiChatArchiveCodec.decode(cursor.getString(0)).firstOrNull()?.let(::add)
            }
        }
    }

    @Synchronized
    fun upsert(archive: AiChatArchive): List<AiChatArchive> {
        val normalized = normalize(archive)
        put(normalized)
        trimOldRows()
        return loadAll()
    }

    @Synchronized
    fun delete(id: String): List<AiChatArchive> {
        helper.writableDatabase.delete("chat_archives", "id = ?", arrayOf(id))
        return loadAll()
    }

    @Synchronized
    fun settleCandidates(lotteryKey: String, draws: List<Draw>): List<AiChatArchive> {
        if (lotteryKey.isBlank() || draws.isEmpty()) return loadAll()
        val byPeriod = draws.asSequence()
            .filter { it.lottery.apiKey == lotteryKey && it.numbers.size == 10 }
            .associateBy(Draw::period)
        if (byPeriod.isEmpty()) return loadAll()
        loadAll().filter { it.lotteryKey == lotteryKey }.forEach { archive ->
            var changed = false
            val candidates = archive.candidates.map { record ->
                if (record.actualNumber != null) return@map record
                val draw = byPeriod[record.targetPeriod] ?: return@map record
                val position = record.prediction.position
                if (position !in draw.numbers.indices) return@map record
                changed = true
                record.copy(
                    actualNumber = draw.numbers[position],
                    resolvedPeriod = draw.period,
                )
            }
            if (changed) put(normalize(archive.copy(candidates = candidates)))
        }
        return loadAll()
    }

    private fun normalize(archive: AiChatArchive): AiChatArchive = archive.copy(
        messages = archive.messages.filter { it.content.isNotBlank() }.takeLast(MAX_MESSAGES),
        candidates = archive.candidates.takeLast(MAX_CANDIDATES),
        memorySummary = archive.memorySummary.take(MAX_MEMORY_CHARS),
        updatedAtEpochMs = System.currentTimeMillis(),
    )

    private fun put(archive: AiChatArchive) {
        val values = ContentValues().apply {
            put("id", archive.id)
            put("updated_at", archive.updatedAtEpochMs)
            put("payload", AiChatArchiveCodec.encode(listOf(archive)))
        }
        helper.writableDatabase.insertWithOnConflict(
            "chat_archives",
            null,
            values,
            SQLiteDatabase.CONFLICT_REPLACE,
        )
    }

    private fun trimOldRows() {
        helper.writableDatabase.execSQL(
            "DELETE FROM chat_archives WHERE id NOT IN " +
                "(SELECT id FROM chat_archives ORDER BY updated_at DESC LIMIT $MAX_CONVERSATIONS)",
        )
    }

    private fun migrateLegacyJson() {
        val count = helper.readableDatabase.rawQuery("SELECT COUNT(*) FROM chat_archives", null)
            .use { if (it.moveToFirst()) it.getInt(0) else 0 }
        if (count > 0 || !legacyFile.exists()) return
        val archives = runCatching {
            AiChatArchiveCodec.decode(legacyFile.readText(Charsets.UTF_8))
        }.getOrDefault(emptyList())
        helper.writableDatabase.beginTransaction()
        try {
            archives.forEach { put(normalize(it)) }
            helper.writableDatabase.setTransactionSuccessful()
        } finally {
            helper.writableDatabase.endTransaction()
        }
        if (archives.isNotEmpty()) {
            legacyFile.renameTo(File(legacyFile.parentFile, "$LEGACY_FILE_NAME.migrated"))
        }
    }

    private class ArchiveDb(context: Context) :
        SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {
        override fun onCreate(db: SQLiteDatabase) {
            db.execSQL(
                "CREATE TABLE chat_archives (" +
                    "id TEXT PRIMARY KEY, updated_at INTEGER NOT NULL, payload TEXT NOT NULL)",
            )
            db.execSQL("CREATE INDEX chat_archives_updated ON chat_archives(updated_at DESC)")
        }

        override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
    }

    private companion object {
        const val DATABASE_NAME = "ai_chat_archive_v2.db"
        const val DATABASE_VERSION = 1
        const val LEGACY_FILE_NAME = "ai_chat_archive_v1.json"
        const val MAX_CONVERSATIONS = 240
        const val MAX_MESSAGES = 240
        const val MAX_CANDIDATES = 80
        const val MAX_MEMORY_CHARS = 6_000
    }
}

object AiChatArchiveCodec {
    fun encode(archives: List<AiChatArchive>): String = JSONObject()
        .put("schema", 3)
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
        .put("judgement_mode", archive.judgementMode.name)
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
            judgementMode = AiJudgementMode.fromId(optString("judgement_mode")),
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
