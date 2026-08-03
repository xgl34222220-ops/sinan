package com.tianji.probabilitylab.nativev4.data

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import androidx.core.database.sqlite.transaction
import com.tianji.probabilitylab.nativev4.ai.AiAnalysisMode
import com.tianji.probabilitylab.nativev4.ai.AiConsensus
import com.tianji.probabilitylab.nativev4.ai.AiConsensusAudit
import com.tianji.probabilitylab.nativev4.ai.AiConsensusRecord
import com.tianji.probabilitylab.nativev4.ai.AiForecast
import com.tianji.probabilitylab.nativev4.ai.AiForecastRecord
import com.tianji.probabilitylab.nativev4.ai.AiLiveAudit
import com.tianji.probabilitylab.nativev4.ai.AiProbabilityVector
import com.tianji.probabilitylab.nativev4.ai.AiProfileAudit
import com.tianji.probabilitylab.nativev4.ai.AiReasoningMode
import com.tianji.probabilitylab.nativev4.ai.AiReasoningProtocol
import com.tianji.probabilitylab.nativev4.ai.AiReasoningState
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.model.LiveAudit
import com.tianji.probabilitylab.nativev4.model.LockedForecast
import com.tianji.probabilitylab.nativev4.model.LotteryType
import java.security.MessageDigest

private const val DATABASE_NAME = "tianji_native_v5.db"
private const val DATABASE_VERSION = 6
private const val LEGACY_ARCHIVE_VERSION = "legacy-v5"
private val LEGACY_DATABASE_NAMES = listOf("tianji_native_v4.db", "tianji_native.db")
private val DATABASE_SIDECARS = listOf("", "-wal", "-shm", "-journal")

private fun prepareDatabaseName(context: Context): String {
    val target = context.getDatabasePath(DATABASE_NAME)
    if (target.exists()) return DATABASE_NAME
    val source = LEGACY_DATABASE_NAMES
        .asSequence()
        .map(context::getDatabasePath)
        .firstOrNull { it.exists() }
        ?: return DATABASE_NAME

    target.parentFile?.mkdirs()
    DATABASE_SIDECARS.forEach { suffix ->
        val sourceFile = java.io.File(source.path + suffix)
        val targetFile = java.io.File(target.path + suffix)
        if (!sourceFile.exists() || targetFile.exists()) return@forEach
        if (!sourceFile.renameTo(targetFile)) {
            runCatching {
                sourceFile.copyTo(targetFile, overwrite = false)
                sourceFile.delete()
            }
        }
    }
    return DATABASE_NAME
}

class AppDatabase(context: Context) :
    SQLiteOpenHelper(context, prepareDatabaseName(context), null, DATABASE_VERSION) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """CREATE TABLE draws (
                lottery_type TEXT NOT NULL, period TEXT NOT NULL, numbers TEXT NOT NULL,
                draw_time TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (lottery_type, period)
            )""".trimIndent(),
        )
        db.execSQL(
            """CREATE TABLE forecast_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_type TEXT NOT NULL, target_period TEXT NOT NULL,
                trained_through_period TEXT NOT NULL, position_index INTEGER NOT NULL,
                top6 TEXT NOT NULL, top7 TEXT NOT NULL, certified INTEGER NOT NULL DEFAULT 0,
                algorithm_version TEXT NOT NULL DEFAULT '', probabilities TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL, report_hash TEXT NOT NULL,
                previous_hash TEXT NOT NULL DEFAULT '', actual_number INTEGER,
                top6_hit INTEGER, top7_hit INTEGER, settled_at INTEGER,
                UNIQUE (lottery_type, target_period)
            )""".trimIndent(),
        )
        db.execSQL("CREATE INDEX draws_type_period ON draws(lottery_type, period)")
        db.execSQL("CREATE INDEX forecasts_type_target ON forecast_records(lottery_type, target_period)")
        createAiForecastTable(db)
        createAiConsensusTable(db)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) createAiForecastTable(db)
        if (oldVersion < 3) createAiConsensusTable(db)

        if (oldVersion in 2..3) {
            db.execSQL("ALTER TABLE ai_forecast_records ADD COLUMN reasoning_mode TEXT NOT NULL DEFAULT 'AUTO'")
            db.execSQL("ALTER TABLE ai_forecast_records ADD COLUMN reasoning_protocol TEXT NOT NULL DEFAULT 'AUTO'")
            db.execSQL("ALTER TABLE ai_forecast_records ADD COLUMN reasoning_state TEXT NOT NULL DEFAULT 'UNSUPPORTED'")
            db.execSQL("ALTER TABLE ai_forecast_records ADD COLUMN reasoning_tokens INTEGER")
            db.execSQL("ALTER TABLE ai_forecast_records ADD COLUMN input_tokens INTEGER")
            db.execSQL("ALTER TABLE ai_forecast_records ADD COLUMN output_tokens INTEGER")
            db.execSQL(
                "UPDATE ai_forecast_records SET reasoning_mode = " +
                    "CASE WHEN analysis_mode = 'DEEP' THEN 'HIGH' ELSE 'LOW' END",
            )
        }
        if (oldVersion in 2..4) {
            db.execSQL("ALTER TABLE ai_forecast_records ADD COLUMN probabilities TEXT NOT NULL DEFAULT ''")
            db.execSQL("ALTER TABLE ai_forecast_records ADD COLUMN estimated_cost REAL")
            db.execSQL("ALTER TABLE ai_forecast_records ADD COLUMN brier_score REAL")
            db.execSQL("ALTER TABLE ai_forecast_records ADD COLUMN log_loss REAL")
            db.execSQL("ALTER TABLE ai_forecast_records ADD COLUMN actual_rank INTEGER")
        }
        if (oldVersion in 3..4) {
            db.execSQL("ALTER TABLE ai_consensus_records ADD COLUMN probabilities TEXT NOT NULL DEFAULT ''")
            db.execSQL("ALTER TABLE ai_consensus_records ADD COLUMN confidence_margin REAL NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE ai_consensus_records ADD COLUMN brier_score REAL")
            db.execSQL("ALTER TABLE ai_consensus_records ADD COLUMN log_loss REAL")
            db.execSQL("ALTER TABLE ai_consensus_records ADD COLUMN actual_rank INTEGER")
        }
        if (oldVersion < 6) {
            db.execSQL(
                "ALTER TABLE forecast_records ADD COLUMN algorithm_version " +
                    "TEXT NOT NULL DEFAULT '$LEGACY_ARCHIVE_VERSION'",
            )
            db.execSQL("ALTER TABLE forecast_records ADD COLUMN probabilities TEXT NOT NULL DEFAULT ''")
            if (oldVersion in 2..5) {
                db.execSQL(
                    "ALTER TABLE ai_forecast_records ADD COLUMN algorithm_version " +
                        "TEXT NOT NULL DEFAULT '$LEGACY_ARCHIVE_VERSION'",
                )
            }
            if (oldVersion in 3..5) {
                db.execSQL(
                    "ALTER TABLE ai_consensus_records ADD COLUMN algorithm_version " +
                        "TEXT NOT NULL DEFAULT '$LEGACY_ARCHIVE_VERSION'",
                )
            }
        }
    }

    private fun createAiForecastTable(db: SQLiteDatabase) {
        db.execSQL(
            """CREATE TABLE IF NOT EXISTS ai_forecast_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_type TEXT NOT NULL, profile_id TEXT NOT NULL,
                profile_name TEXT NOT NULL, target_period TEXT NOT NULL,
                trained_through_period TEXT NOT NULL, position_index INTEGER NOT NULL,
                top6 TEXT NOT NULL, top7 TEXT NOT NULL, probabilities TEXT NOT NULL,
                analysis TEXT NOT NULL,
                risk_note TEXT NOT NULL, self_rating REAL NOT NULL,
                model TEXT NOT NULL, analysis_mode TEXT NOT NULL,
                reasoning_mode TEXT NOT NULL, reasoning_protocol TEXT NOT NULL,
                reasoning_state TEXT NOT NULL, reasoning_tokens INTEGER,
                input_tokens INTEGER, output_tokens INTEGER, estimated_cost REAL,
                execution_note TEXT NOT NULL, algorithm_version TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL, latency_ms INTEGER NOT NULL,
                response_id TEXT NOT NULL, forecast_hash TEXT NOT NULL,
                previous_hash TEXT NOT NULL DEFAULT '', actual_number INTEGER,
                top6_hit INTEGER, top7_hit INTEGER, brier_score REAL,
                log_loss REAL, actual_rank INTEGER, settled_at INTEGER,
                UNIQUE (lottery_type, profile_id, target_period)
            )""".trimIndent(),
        )
        db.execSQL(
            "CREATE INDEX IF NOT EXISTS ai_forecasts_type_target " +
                "ON ai_forecast_records(lottery_type, target_period)",
        )
    }

    private fun createAiConsensusTable(db: SQLiteDatabase) {
        db.execSQL(
            """CREATE TABLE IF NOT EXISTS ai_consensus_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_type TEXT NOT NULL, target_period TEXT NOT NULL,
                trained_through_period TEXT NOT NULL, position_index INTEGER NOT NULL,
                top6 TEXT NOT NULL, top7 TEXT NOT NULL, probabilities TEXT NOT NULL,
                confidence_margin REAL NOT NULL,
                supporting_profiles INTEGER NOT NULL, total_profiles INTEGER NOT NULL,
                algorithm_version TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL,
                consensus_hash TEXT NOT NULL, previous_hash TEXT NOT NULL DEFAULT '',
                actual_number INTEGER, top6_hit INTEGER, top7_hit INTEGER,
                brier_score REAL, log_loss REAL, actual_rank INTEGER, settled_at INTEGER,
                UNIQUE (lottery_type, target_period)
            )""".trimIndent(),
        )
        db.execSQL(
            "CREATE INDEX IF NOT EXISTS ai_consensus_type_target " +
                "ON ai_consensus_records(lottery_type, target_period)",
        )
    }

    fun saveDraws(draws: List<Draw>) {
        if (draws.isEmpty()) return
        writableDatabase.transaction {
            draws.forEach { draw ->
                val values = ContentValues().apply {
                    put("lottery_type", draw.lottery.apiKey)
                    put("period", draw.period)
                    put("numbers", draw.numbers.joinToString(","))
                    put("draw_time", draw.drawTime)
                    put("source", draw.source)
                }
                insertWithOnConflict("draws", null, values, SQLiteDatabase.CONFLICT_REPLACE)
            }
        }
    }

    fun loadDraws(lottery: LotteryType, limit: Int = 3000): List<Draw> {
        val safeLimit = limit.coerceIn(1, 6000)
        val rows = readableDatabase.rawQuery(
            """SELECT period, numbers, draw_time, source FROM draws
                WHERE lottery_type = ? ORDER BY LENGTH(period) DESC, period DESC LIMIT $safeLimit""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    val numbers = parseNumbers(cursor.getString(1))
                    if (numbers.size == 10 && numbers.toSet().size == 10) {
                        add(
                            Draw(
                                lottery = lottery,
                                period = cursor.getString(0),
                                numbers = numbers,
                                drawTime = cursor.getString(2),
                                source = cursor.getString(3),
                            ),
                        )
                    }
                }
            }
        }
        return rows.asReversed()
    }

    fun lockForecast(lottery: LotteryType, report: ForecastReport): Long {
        val selected = report.selected
        val probabilitiesText = selected.probabilities.joinToString(",") { it.toString() }
        val createdAt = System.currentTimeMillis()
        return writableDatabase.transaction {
            val previousHash = rawQuery(
                "SELECT report_hash FROM forecast_records " +
                    "WHERE lottery_type = ? ORDER BY id DESC LIMIT 1",
                arrayOf(lottery.apiKey),
            ).use { if (it.moveToFirst()) it.getString(0) else "" }
            val canonical = ArchiveCanonical.encode(
                ArchiveCanonical.NATIVE_VERSION,
                lottery.apiKey,
                report.algorithmVersion,
                report.targetPeriod,
                report.trainedThroughPeriod,
                report.selectedPosition,
                selected.top6.joinToString(","),
                selected.top7.joinToString(","),
                probabilitiesText,
                report.mode.name,
                createdAt,
                previousHash,
            )
            val values = ContentValues().apply {
                put("lottery_type", lottery.apiKey)
                put("target_period", report.targetPeriod)
                put("trained_through_period", report.trainedThroughPeriod)
                put("position_index", report.selectedPosition)
                put("top6", selected.top6.joinToString(","))
                put("top7", selected.top7.joinToString(","))
                put("certified", if (report.mode.name == "CERTIFIED") 1 else 0)
                put("algorithm_version", report.algorithmVersion)
                put("probabilities", probabilitiesText)
                put("created_at", createdAt)
                put("report_hash", sha256(canonical))
                put("previous_hash", previousHash)
            }
            insertWithOnConflict(
                "forecast_records",
                null,
                values,
                SQLiteDatabase.CONFLICT_IGNORE,
            )
        }
    }

    fun settleForecasts(lottery: LotteryType, draws: List<Draw>) {
        val pending = readableDatabase.rawQuery(
            """SELECT id, target_period, position_index, top6, top7 FROM forecast_records
                WHERE lottery_type = ? AND settled_at IS NULL""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        Pending(
                            cursor.getLong(0),
                            cursor.getString(1),
                            cursor.getInt(2),
                            parseNumbers(cursor.getString(3)),
                            parseNumbers(cursor.getString(4)),
                        ),
                    )
                }
            }
        }
        writableDatabase.transaction {
            pending.forEach { forecast ->
                val settlement = ExactTargetSettlement.evaluate(
                    draws = draws,
                    targetPeriod = forecast.targetPeriod,
                    position = forecast.position,
                    top6 = forecast.top6,
                    top7 = forecast.top7,
                ) ?: return@forEach
                val values = ContentValues().apply {
                    put("actual_number", settlement.actualNumber)
                    put("top6_hit", if (settlement.top6Hit) 1 else 0)
                    put("top7_hit", if (settlement.top7Hit) 1 else 0)
                    put("settled_at", System.currentTimeMillis())
                }
                update("forecast_records", values, "id = ?", arrayOf(forecast.id.toString()))
            }
        }
    }

    fun loadForecasts(lottery: LotteryType, limit: Int = 80): List<LockedForecast> {
        val safeLimit = limit.coerceIn(1, 200)
        return readableDatabase.rawQuery(
            """SELECT id, target_period, trained_through_period, position_index, top6, top7,
                certified, created_at, report_hash, previous_hash, actual_number, top6_hit, top7_hit
                FROM forecast_records WHERE lottery_type = ? ORDER BY id DESC LIMIT $safeLimit""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList { while (cursor.moveToNext()) add(cursor.toRecord(lottery)) }
        }
    }

    fun loadLiveAudit(lottery: LotteryType): LiveAudit = readableDatabase.rawQuery(
        """SELECT COUNT(*), COALESCE(SUM(top6_hit), 0), COALESCE(SUM(top7_hit), 0)
            FROM forecast_records WHERE lottery_type = ? AND settled_at IS NOT NULL""".trimIndent(),
        arrayOf(lottery.apiKey),
    ).use { cursor ->
        if (cursor.moveToFirst()) LiveAudit(cursor.getInt(0), cursor.getInt(1), cursor.getInt(2))
        else LiveAudit(0, 0, 0)
    }

    fun lockAiForecast(
        lottery: LotteryType,
        report: ForecastReport,
        forecast: AiForecast,
    ): AiForecastLockResult {
        val probabilitiesText = forecast.probabilities.joinToString(",") { it.toString() }
        val inserted = writableDatabase.transaction {
            val previousHash = rawQuery(
                """SELECT forecast_hash FROM ai_forecast_records
                    WHERE lottery_type = ? AND profile_id = ? ORDER BY id DESC LIMIT 1""".trimIndent(),
                arrayOf(lottery.apiKey, forecast.profileId),
            ).use { if (it.moveToFirst()) it.getString(0) else "" }
            val canonical = ArchiveCanonical.encode(
                ArchiveCanonical.AI_VERSION,
                lottery.apiKey,
                forecast.profileId,
                forecast.profileName,
                forecast.targetPeriod,
                report.trainedThroughPeriod,
                forecast.position,
                forecast.top6.joinToString(","),
                forecast.top7.joinToString(","),
                probabilitiesText,
                forecast.analysis,
                forecast.riskNote,
                forecast.selfRating,
                forecast.model,
                forecast.analysisMode.name,
                forecast.reasoningMode.name,
                forecast.reasoningProtocol.name,
                forecast.reasoningState.name,
                forecast.reasoningTokens,
                forecast.inputTokens,
                forecast.outputTokens,
                forecast.estimatedCost,
                forecast.executionNote,
                report.algorithmVersion,
                forecast.createdAtEpochMs,
                forecast.latencyMs,
                forecast.responseId,
                previousHash,
            )
            val forecastHash = sha256(canonical)
            val values = ContentValues().apply {
                put("lottery_type", lottery.apiKey)
                put("profile_id", forecast.profileId)
                put("profile_name", forecast.profileName)
                put("target_period", forecast.targetPeriod)
                put("trained_through_period", report.trainedThroughPeriod)
                put("position_index", forecast.position)
                put("top6", forecast.top6.joinToString(","))
                put("top7", forecast.top7.joinToString(","))
                put("probabilities", probabilitiesText)
                put("analysis", forecast.analysis)
                put("risk_note", forecast.riskNote)
                put("self_rating", forecast.selfRating)
                put("model", forecast.model)
                put("analysis_mode", forecast.analysisMode.name)
                put("reasoning_mode", forecast.reasoningMode.name)
                put("reasoning_protocol", forecast.reasoningProtocol.name)
                put("reasoning_state", forecast.reasoningState.name)
                forecast.reasoningTokens?.let { put("reasoning_tokens", it) }
                forecast.inputTokens?.let { put("input_tokens", it) }
                forecast.outputTokens?.let { put("output_tokens", it) }
                forecast.estimatedCost?.let { put("estimated_cost", it) }
                put("execution_note", forecast.executionNote)
                put("algorithm_version", report.algorithmVersion)
                put("created_at", forecast.createdAtEpochMs)
                put("latency_ms", forecast.latencyMs)
                put("response_id", forecast.responseId)
                put("forecast_hash", forecastHash)
                put("previous_hash", previousHash)
            }
            insertWithOnConflict(
                "ai_forecast_records",
                null,
                values,
                SQLiteDatabase.CONFLICT_IGNORE,
            ) != -1L
        }
        val record = loadAiForecast(lottery, forecast.profileId, forecast.targetPeriod)
            ?: error("AI 冻结档案写入失败")
        return AiForecastLockResult(record = record, inserted = inserted)
    }

    fun hasDraw(lottery: LotteryType, period: String): Boolean = readableDatabase.rawQuery(
        "SELECT 1 FROM draws WHERE lottery_type = ? AND period = ? LIMIT 1",
        arrayOf(lottery.apiKey, period),
    ).use(Cursor::moveToFirst)

    fun hasAiForecast(lottery: LotteryType, profileId: String, targetPeriod: String): Boolean =
        readableDatabase.rawQuery(
            """SELECT 1 FROM ai_forecast_records
                WHERE lottery_type = ? AND profile_id = ? AND target_period = ? LIMIT 1""".trimIndent(),
            arrayOf(lottery.apiKey, profileId, targetPeriod),
        ).use(Cursor::moveToFirst)

    fun settleAiForecasts(lottery: LotteryType, draws: List<Draw>) {
        val pending = readableDatabase.rawQuery(
            """SELECT id, target_period, position_index, top6, top7, probabilities FROM ai_forecast_records
                WHERE lottery_type = ? AND settled_at IS NULL""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        Pending(
                            cursor.getLong(0),
                            cursor.getString(1),
                            cursor.getInt(2),
                            parseNumbers(cursor.getString(3)),
                            parseNumbers(cursor.getString(4)),
                            parseProbabilities(cursor.getString(5)),
                        ),
                    )
                }
            }
        }
        writableDatabase.transaction {
            pending.forEach { forecast ->
                val settlement = ExactTargetSettlement.evaluate(
                    draws = draws,
                    targetPeriod = forecast.targetPeriod,
                    position = forecast.position,
                    top6 = forecast.top6,
                    top7 = forecast.top7,
                ) ?: return@forEach
                val values = ContentValues().apply {
                    put("actual_number", settlement.actualNumber)
                    put("top6_hit", if (settlement.top6Hit) 1 else 0)
                    put("top7_hit", if (settlement.top7Hit) 1 else 0)
                    metricsFor(forecast.probabilities, settlement.actualNumber)?.let { metrics ->
                        put("brier_score", metrics.brierScore)
                        put("log_loss", metrics.logLoss)
                        put("actual_rank", metrics.actualRank)
                    }
                    put("settled_at", System.currentTimeMillis())
                }
                update("ai_forecast_records", values, "id = ?", arrayOf(forecast.id.toString()))
            }
        }
    }

    fun loadAiForecasts(lottery: LotteryType, limit: Int = 80): List<AiForecastRecord> {
        val safeLimit = limit.coerceIn(1, 200)
        return readableDatabase.rawQuery(
            """SELECT id, profile_id, profile_name, target_period, trained_through_period,
                position_index, top6, top7, probabilities, analysis, risk_note, self_rating, model,
                analysis_mode, reasoning_mode, reasoning_protocol, reasoning_state,
                reasoning_tokens, input_tokens, output_tokens, estimated_cost,
                execution_note, created_at, latency_ms, response_id,
                forecast_hash, previous_hash, actual_number, top6_hit, top7_hit,
                brier_score, log_loss, actual_rank
                FROM ai_forecast_records WHERE lottery_type = ? ORDER BY id DESC LIMIT $safeLimit""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList { while (cursor.moveToNext()) add(cursor.toAiRecord(lottery)) }
        }
    }

    /**
     * Learning must not inherit the archive screen's display limit. Records are returned
     * from the oldest settled target to the newest for correct online updates.
     */
    fun loadSettledAiForecastsForLearning(lottery: LotteryType): List<AiForecastRecord> =
        readableDatabase.rawQuery(
            """SELECT id, profile_id, profile_name, target_period, trained_through_period,
                position_index, top6, top7, probabilities, analysis, risk_note, self_rating, model,
                analysis_mode, reasoning_mode, reasoning_protocol, reasoning_state,
                reasoning_tokens, input_tokens, output_tokens, estimated_cost,
                execution_note, created_at, latency_ms, response_id,
                forecast_hash, previous_hash, actual_number, top6_hit, top7_hit,
                brier_score, log_loss, actual_rank
                FROM ai_forecast_records
                WHERE lottery_type = ? AND settled_at IS NOT NULL
                ORDER BY id ASC""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList { while (cursor.moveToNext()) add(cursor.toAiRecord(lottery)) }
        }


    fun loadAiLiveAudit(lottery: LotteryType): AiLiveAudit = readableDatabase.rawQuery(
        """SELECT COUNT(*), COUNT(DISTINCT target_period),
            COALESCE(SUM(top6_hit), 0), COALESCE(SUM(top7_hit), 0)
            FROM ai_forecast_records WHERE lottery_type = ? AND settled_at IS NOT NULL""".trimIndent(),
        arrayOf(lottery.apiKey),
    ).use { cursor ->
        if (cursor.moveToFirst()) {
            AiLiveAudit(
                settled = cursor.getInt(0),
                targetPeriods = cursor.getInt(1),
                top6Hits = cursor.getInt(2),
                top7Hits = cursor.getInt(3),
            )
        } else {
            AiLiveAudit()
        }
    }

    fun loadAiProfileAudits(lottery: LotteryType): List<AiProfileAudit> {
        val base = readableDatabase.rawQuery(
            """SELECT f.profile_id,
                (SELECT f2.profile_name FROM ai_forecast_records f2
                    WHERE f2.lottery_type = f.lottery_type
                        AND f2.profile_id = f.profile_id AND f2.model = f.model
                        AND f2.analysis_mode = f.analysis_mode
                        AND f2.reasoning_mode = f.reasoning_mode
                        AND f2.reasoning_protocol = f.reasoning_protocol
                        AND f2.settled_at IS NOT NULL
                    ORDER BY f2.id DESC LIMIT 1),
                f.model, f.analysis_mode, f.reasoning_mode, f.reasoning_protocol, COUNT(*),
                COALESCE(SUM(f.top6_hit), 0), COALESCE(SUM(f.top7_hit), 0),
                AVG(f.brier_score), AVG(f.log_loss), AVG(f.actual_rank),
                AVG(f.latency_ms), AVG(f.input_tokens), AVG(f.output_tokens), AVG(f.estimated_cost)
                FROM ai_forecast_records f
                WHERE f.lottery_type = ? AND f.settled_at IS NOT NULL
                GROUP BY f.profile_id, f.model, f.analysis_mode, f.reasoning_mode, f.reasoning_protocol
                ORDER BY MAX(f.id) DESC""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        AiProfileAudit(
                            profileId = cursor.getString(0),
                            profileName = cursor.getString(1),
                            model = cursor.getString(2),
                            analysisMode = runCatching { AiAnalysisMode.valueOf(cursor.getString(3)) }
                                .getOrDefault(AiAnalysisMode.FAST),
                            reasoningMode = runCatching { AiReasoningMode.valueOf(cursor.getString(4)) }
                                .getOrDefault(AiReasoningMode.AUTO),
                            reasoningProtocol = runCatching {
                                AiReasoningProtocol.valueOf(cursor.getString(5))
                            }.getOrDefault(AiReasoningProtocol.AUTO),
                            settled = cursor.getInt(6),
                            top6Hits = cursor.getInt(7),
                            top7Hits = cursor.getInt(8),
                            meanBrierScore = if (cursor.isNull(9)) null else cursor.getDouble(9),
                            meanLogLoss = if (cursor.isNull(10)) null else cursor.getDouble(10),
                            meanActualRank = if (cursor.isNull(11)) null else cursor.getDouble(11),
                            meanLatencyMs = if (cursor.isNull(12)) null else cursor.getDouble(12),
                            meanInputTokens = if (cursor.isNull(13)) null else cursor.getDouble(13),
                            meanOutputTokens = if (cursor.isNull(14)) null else cursor.getDouble(14),
                            meanEstimatedCost = if (cursor.isNull(15)) null else cursor.getDouble(15),
                        ),
                    )
                }
            }
        }

        fun recentRate(audit: AiProfileAudit, limit: Int): Double? = readableDatabase.rawQuery(
            """SELECT AVG(top6_hit * 1.0) FROM (
                SELECT top6_hit FROM ai_forecast_records
                WHERE lottery_type = ? AND profile_id = ? AND model = ?
                    AND analysis_mode = ? AND reasoning_mode = ? AND reasoning_protocol = ?
                    AND settled_at IS NOT NULL
                ORDER BY id DESC LIMIT $limit
            )""".trimIndent(),
            arrayOf(
                lottery.apiKey,
                audit.profileId,
                audit.model,
                audit.analysisMode.name,
                audit.reasoningMode.name,
                audit.reasoningProtocol.name,
            ),
        ).use { cursor ->
            if (cursor.moveToFirst() && !cursor.isNull(0)) cursor.getDouble(0) else null
        }

        return base.map { audit ->
            audit.copy(
                recent20Top6Rate = recentRate(audit, 20),
                recent50Top6Rate = recentRate(audit, 50),
                recent100Top6Rate = recentRate(audit, 100),
            )
        }
    }

    fun lockAiConsensus(
        lottery: LotteryType,
        report: ForecastReport,
        consensus: AiConsensus,
    ): Boolean {
        val probabilitiesText = consensus.probabilities.joinToString(",") { it.toString() }
        val createdAt = System.currentTimeMillis()
        return writableDatabase.transaction {
            val previousHash = rawQuery(
                "SELECT consensus_hash FROM ai_consensus_records " +
                    "WHERE lottery_type = ? ORDER BY id DESC LIMIT 1",
                arrayOf(lottery.apiKey),
            ).use { if (it.moveToFirst()) it.getString(0) else "" }
            val canonical = ArchiveCanonical.encode(
                ArchiveCanonical.CONSENSUS_VERSION,
                lottery.apiKey,
                report.algorithmVersion,
                report.targetPeriod,
                report.trainedThroughPeriod,
                consensus.position,
                consensus.top6.joinToString(","),
                consensus.top7.joinToString(","),
                probabilitiesText,
                consensus.confidenceMargin,
                consensus.supportingProfiles,
                consensus.totalProfiles,
                createdAt,
                previousHash,
            )
            val values = ContentValues().apply {
                put("lottery_type", lottery.apiKey)
                put("target_period", report.targetPeriod)
                put("trained_through_period", report.trainedThroughPeriod)
                put("position_index", consensus.position)
                put("top6", consensus.top6.joinToString(","))
                put("top7", consensus.top7.joinToString(","))
                put("probabilities", probabilitiesText)
                put("confidence_margin", consensus.confidenceMargin)
                put("supporting_profiles", consensus.supportingProfiles)
                put("total_profiles", consensus.totalProfiles)
                put("algorithm_version", report.algorithmVersion)
                put("created_at", createdAt)
                put("consensus_hash", sha256(canonical))
                put("previous_hash", previousHash)
            }
            insertWithOnConflict(
                "ai_consensus_records",
                null,
                values,
                SQLiteDatabase.CONFLICT_IGNORE,
            ) != -1L
        }
    }

    fun settleAiConsensus(lottery: LotteryType, draws: List<Draw>) {
        val pending = readableDatabase.rawQuery(
            """SELECT id, target_period, position_index, top6, top7, probabilities FROM ai_consensus_records
                WHERE lottery_type = ? AND settled_at IS NULL""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        Pending(
                            cursor.getLong(0),
                            cursor.getString(1),
                            cursor.getInt(2),
                            parseNumbers(cursor.getString(3)),
                            parseNumbers(cursor.getString(4)),
                            parseProbabilities(cursor.getString(5)),
                        ),
                    )
                }
            }
        }
        writableDatabase.transaction {
            pending.forEach { forecast ->
                val settlement = ExactTargetSettlement.evaluate(
                    draws,
                    forecast.targetPeriod,
                    forecast.position,
                    forecast.top6,
                    forecast.top7,
                ) ?: return@forEach
                update(
                    "ai_consensus_records",
                    ContentValues().apply {
                        put("actual_number", settlement.actualNumber)
                        put("top6_hit", if (settlement.top6Hit) 1 else 0)
                        put("top7_hit", if (settlement.top7Hit) 1 else 0)
                        metricsFor(forecast.probabilities, settlement.actualNumber)?.let { metrics ->
                            put("brier_score", metrics.brierScore)
                            put("log_loss", metrics.logLoss)
                            put("actual_rank", metrics.actualRank)
                        }
                        put("settled_at", System.currentTimeMillis())
                    },
                    "id = ?",
                    arrayOf(forecast.id.toString()),
                )
            }
        }
    }

    fun loadAiConsensusRecords(lottery: LotteryType, limit: Int = 80): List<AiConsensusRecord> {
        val safeLimit = limit.coerceIn(1, 200)
        return readableDatabase.rawQuery(
            """SELECT id, target_period, trained_through_period, position_index, top6, top7,
                probabilities, confidence_margin, supporting_profiles, total_profiles,
                created_at, consensus_hash, previous_hash, actual_number, top6_hit, top7_hit,
                brier_score, log_loss, actual_rank FROM ai_consensus_records
                WHERE lottery_type = ? ORDER BY id DESC LIMIT $safeLimit""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        AiConsensusRecord(
                            id = cursor.getLong(0),
                            lottery = lottery,
                            targetPeriod = cursor.getString(1),
                            trainedThroughPeriod = cursor.getString(2),
                            position = cursor.getInt(3),
                            top6 = parseNumbers(cursor.getString(4)),
                            top7 = parseNumbers(cursor.getString(5)),
                            probabilities = parseProbabilities(cursor.getString(6))
                                .takeIf { it.size == 10 }
                                ?: AiProbabilityVector.legacy(
                                    parseNumbers(cursor.getString(4)),
                                    parseNumbers(cursor.getString(5)),
                                ),
                            confidenceMargin = cursor.getDouble(7),
                            supportingProfiles = cursor.getInt(8),
                            totalProfiles = cursor.getInt(9),
                            createdAtEpochMs = cursor.getLong(10),
                            consensusHash = cursor.getString(11),
                            previousHash = cursor.getString(12),
                            actualNumber = if (cursor.isNull(13)) null else cursor.getInt(13),
                            top6Hit = if (cursor.isNull(14)) null else cursor.getInt(14) == 1,
                            top7Hit = if (cursor.isNull(15)) null else cursor.getInt(15) == 1,
                            brierScore = if (cursor.isNull(16)) null else cursor.getDouble(16),
                            logLoss = if (cursor.isNull(17)) null else cursor.getDouble(17),
                            actualRank = if (cursor.isNull(18)) null else cursor.getInt(18),
                        ),
                    )
                }
            }
        }
    }

    fun loadAiConsensusAudit(lottery: LotteryType): AiConsensusAudit = readableDatabase.rawQuery(
        """SELECT COUNT(*), COALESCE(SUM(top6_hit), 0), COALESCE(SUM(top7_hit), 0)
            FROM ai_consensus_records WHERE lottery_type = ? AND settled_at IS NOT NULL""".trimIndent(),
        arrayOf(lottery.apiKey),
    ).use { cursor ->
        if (cursor.moveToFirst()) {
            AiConsensusAudit(cursor.getInt(0), cursor.getInt(1), cursor.getInt(2))
        } else {
            AiConsensusAudit()
        }
    }

    fun loadPendingSettlements(lottery: LotteryType): List<PendingSettlementTarget> {
        val native = readableDatabase.rawQuery(
            """SELECT f.target_period, f.created_at, COALESCE(d.draw_time, '')
                FROM forecast_records f LEFT JOIN draws d
                ON d.lottery_type = f.lottery_type AND d.period = f.trained_through_period
                WHERE f.lottery_type = ? AND f.settled_at IS NULL""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        PendingSettlementTarget(
                            cursor.getString(0),
                            cursor.getLong(1),
                            cursor.getString(2),
                        ),
                    )
                }
            }
        }
        val ai = readableDatabase.rawQuery(
            """SELECT f.target_period, f.created_at, COALESCE(d.draw_time, '')
                FROM ai_forecast_records f LEFT JOIN draws d
                ON d.lottery_type = f.lottery_type AND d.period = f.trained_through_period
                WHERE f.lottery_type = ? AND f.settled_at IS NULL""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        PendingSettlementTarget(
                            cursor.getString(0),
                            cursor.getLong(1),
                            cursor.getString(2),
                        ),
                    )
                }
            }
        }
        val consensus = readableDatabase.rawQuery(
            """SELECT f.target_period, f.created_at, COALESCE(d.draw_time, '')
                FROM ai_consensus_records f LEFT JOIN draws d
                ON d.lottery_type = f.lottery_type AND d.period = f.trained_through_period
                WHERE f.lottery_type = ? AND f.settled_at IS NULL""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        PendingSettlementTarget(
                            cursor.getString(0),
                            cursor.getLong(1),
                            cursor.getString(2),
                        ),
                    )
                }
            }
        }
        return (native + ai + consensus).distinctBy { it.targetPeriod }.take(200)
    }

    fun verifyArchiveIntegrity(lottery: LotteryType): ArchiveIntegrity {
        var nativePrevious = ""
        var nativeCount = 0
        var nativeValid = true
        readableDatabase.rawQuery(
            """SELECT target_period, trained_through_period, position_index, top6, top7,
                certified, algorithm_version, probabilities, created_at, report_hash, previous_hash
                FROM forecast_records WHERE lottery_type = ? ORDER BY id ASC""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            while (cursor.moveToNext()) {
                val previous = cursor.getString(10)
                val newCanonical = ArchiveCanonical.encode(
                    ArchiveCanonical.NATIVE_VERSION,
                    lottery.apiKey,
                    cursor.getString(6),
                    cursor.getString(0),
                    cursor.getString(1),
                    cursor.getInt(2),
                    cursor.getString(3),
                    cursor.getString(4),
                    cursor.getString(7),
                    if (cursor.getInt(5) == 1) "CERTIFIED" else "OBSERVE",
                    cursor.getLong(8),
                    previous,
                )
                val legacyCanonical = listOf(
                    lottery.apiKey,
                    cursor.getString(0),
                    cursor.getString(1),
                    cursor.getInt(2).toString(),
                    cursor.getString(3),
                    cursor.getString(4),
                    if (cursor.getInt(5) == 1) "CERTIFIED" else "OBSERVE",
                    cursor.getLong(8).toString(),
                    previous,
                ).joinToString("|")
                val stored = cursor.getString(9)
                val hashValid = sha256(newCanonical) == stored ||
                    (cursor.getString(6) == LEGACY_ARCHIVE_VERSION && sha256(legacyCanonical) == stored)
                nativeValid = nativeValid && previous == nativePrevious && hashValid
                nativePrevious = stored
                nativeCount++
            }
        }

        val aiPreviousByProfile = mutableMapOf<String, String>()
        var aiCount = 0
        var aiValid = true
        readableDatabase.rawQuery(
            """SELECT profile_id, profile_name, target_period, trained_through_period,
                position_index, top6, top7, probabilities, analysis, risk_note, self_rating,
                model, analysis_mode, reasoning_mode, reasoning_protocol, reasoning_state,
                reasoning_tokens, input_tokens, output_tokens, estimated_cost, execution_note,
                algorithm_version, created_at, latency_ms, response_id, forecast_hash, previous_hash
                FROM ai_forecast_records WHERE lottery_type = ? ORDER BY id ASC""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            while (cursor.moveToNext()) {
                val profile = cursor.getString(0)
                val previous = cursor.getString(26)
                val newCanonical = ArchiveCanonical.encode(
                    ArchiveCanonical.AI_VERSION,
                    lottery.apiKey,
                    profile,
                    cursor.getString(1),
                    cursor.getString(2),
                    cursor.getString(3),
                    cursor.getInt(4),
                    cursor.getString(5),
                    cursor.getString(6),
                    cursor.getString(7),
                    cursor.getString(8),
                    cursor.getString(9),
                    cursor.getDouble(10),
                    cursor.getString(11),
                    cursor.getString(12),
                    cursor.getString(13),
                    cursor.getString(14),
                    cursor.getString(15),
                    cursor.textOrEmpty(16),
                    cursor.textOrEmpty(17),
                    cursor.textOrEmpty(18),
                    cursor.textOrEmpty(19),
                    cursor.getString(20),
                    cursor.getString(21),
                    cursor.getLong(22),
                    cursor.getLong(23),
                    cursor.getString(24),
                    previous,
                )
                val legacyCanonical = listOf(
                    lottery.apiKey,
                    profile,
                    cursor.getString(2),
                    cursor.getString(3),
                    cursor.getInt(4).toString(),
                    cursor.getString(5),
                    cursor.getString(6),
                    cursor.getString(11),
                    cursor.getString(12),
                    cursor.getLong(22).toString(),
                    previous,
                ).joinToString("|")
                val stored = cursor.getString(25)
                val hashValid = sha256(newCanonical) == stored ||
                    (cursor.getString(21) == LEGACY_ARCHIVE_VERSION && sha256(legacyCanonical) == stored)
                aiValid = aiValid &&
                    previous == aiPreviousByProfile.getOrDefault(profile, "") &&
                    hashValid
                aiPreviousByProfile[profile] = stored
                aiCount++
            }
        }

        var consensusPrevious = ""
        var consensusCount = 0
        var consensusValid = true
        readableDatabase.rawQuery(
            """SELECT target_period, trained_through_period, position_index, top6, top7,
                probabilities, confidence_margin, supporting_profiles, total_profiles,
                algorithm_version, created_at, consensus_hash, previous_hash
                FROM ai_consensus_records WHERE lottery_type = ? ORDER BY id ASC""".trimIndent(),
            arrayOf(lottery.apiKey),
        ).use { cursor ->
            while (cursor.moveToNext()) {
                val previous = cursor.getString(12)
                val newCanonical = ArchiveCanonical.encode(
                    ArchiveCanonical.CONSENSUS_VERSION,
                    lottery.apiKey,
                    cursor.getString(9),
                    cursor.getString(0),
                    cursor.getString(1),
                    cursor.getInt(2),
                    cursor.getString(3),
                    cursor.getString(4),
                    cursor.getString(5),
                    cursor.getDouble(6),
                    cursor.getInt(7),
                    cursor.getInt(8),
                    cursor.getLong(10),
                    previous,
                )
                val legacyCanonical = listOf(
                    lottery.apiKey,
                    cursor.getString(0),
                    cursor.getString(1),
                    cursor.getInt(2).toString(),
                    cursor.getString(3),
                    cursor.getString(4),
                    cursor.getInt(7).toString(),
                    cursor.getInt(8).toString(),
                    cursor.getLong(10).toString(),
                    previous,
                ).joinToString("|")
                val stored = cursor.getString(11)
                val hashValid = sha256(newCanonical) == stored ||
                    (cursor.getString(9) == LEGACY_ARCHIVE_VERSION && sha256(legacyCanonical) == stored)
                consensusValid = consensusValid && previous == consensusPrevious && hashValid
                consensusPrevious = stored
                consensusCount++
            }
        }
        return ArchiveIntegrity(
            nativeValid,
            aiValid,
            consensusValid,
            nativeCount,
            aiCount,
            consensusCount,
        )
    }

    private fun loadAiForecast(
        lottery: LotteryType,
        profileId: String,
        targetPeriod: String,
    ): AiForecastRecord? = readableDatabase.rawQuery(
        """SELECT id, profile_id, profile_name, target_period, trained_through_period,
            position_index, top6, top7, probabilities, analysis, risk_note, self_rating, model,
            analysis_mode, reasoning_mode, reasoning_protocol, reasoning_state,
            reasoning_tokens, input_tokens, output_tokens, estimated_cost,
            execution_note, created_at, latency_ms, response_id,
            forecast_hash, previous_hash, actual_number, top6_hit, top7_hit,
            brier_score, log_loss, actual_rank
            FROM ai_forecast_records
            WHERE lottery_type = ? AND profile_id = ? AND target_period = ? LIMIT 1""".trimIndent(),
        arrayOf(lottery.apiKey, profileId, targetPeriod),
    ).use { cursor -> if (cursor.moveToFirst()) cursor.toAiRecord(lottery) else null }

    private fun Cursor.toRecord(lottery: LotteryType) = LockedForecast(
        id = getLong(0),
        lottery = lottery,
        targetPeriod = getString(1),
        trainedThroughPeriod = getString(2),
        position = getInt(3),
        top6 = parseNumbers(getString(4)),
        top7 = parseNumbers(getString(5)),
        certified = getInt(6) == 1,
        createdAtEpochMs = getLong(7),
        reportHash = getString(8),
        previousHash = getString(9),
        actualNumber = if (isNull(10)) null else getInt(10),
        top6Hit = if (isNull(11)) null else getInt(11) == 1,
        top7Hit = if (isNull(12)) null else getInt(12) == 1,
    )

    private fun Cursor.toAiRecord(lottery: LotteryType) = AiForecastRecord(
        id = getLong(0),
        lottery = lottery,
        profileId = getString(1),
        profileName = getString(2),
        targetPeriod = getString(3),
        trainedThroughPeriod = getString(4),
        position = getInt(5),
        top6 = parseNumbers(getString(6)),
        top7 = parseNumbers(getString(7)),
        probabilities = parseProbabilities(getString(8)).takeIf { it.size == 10 }
            ?: AiProbabilityVector.legacy(parseNumbers(getString(6)), parseNumbers(getString(7))),
        analysis = getString(9),
        riskNote = getString(10),
        selfRating = getDouble(11),
        model = getString(12),
        analysisMode = runCatching { AiAnalysisMode.valueOf(getString(13)) }
            .getOrDefault(AiAnalysisMode.FAST),
        reasoningMode = runCatching { AiReasoningMode.valueOf(getString(14)) }
            .getOrDefault(AiReasoningMode.AUTO),
        reasoningProtocol = runCatching { AiReasoningProtocol.valueOf(getString(15)) }
            .getOrDefault(AiReasoningProtocol.AUTO),
        reasoningState = runCatching { AiReasoningState.valueOf(getString(16)) }
            .getOrDefault(AiReasoningState.UNSUPPORTED),
        reasoningTokens = if (isNull(17)) null else getInt(17),
        inputTokens = if (isNull(18)) null else getInt(18),
        outputTokens = if (isNull(19)) null else getInt(19),
        estimatedCost = if (isNull(20)) null else getDouble(20),
        executionNote = getString(21),
        createdAtEpochMs = getLong(22),
        latencyMs = getLong(23),
        responseId = getString(24),
        forecastHash = getString(25),
        previousHash = getString(26),
        actualNumber = if (isNull(27)) null else getInt(27),
        top6Hit = if (isNull(28)) null else getInt(28) == 1,
        top7Hit = if (isNull(29)) null else getInt(29) == 1,
        brierScore = if (isNull(30)) null else getDouble(30),
        logLoss = if (isNull(31)) null else getDouble(31),
        actualRank = if (isNull(32)) null else getInt(32),
    )

    private fun Cursor.textOrEmpty(index: Int): String = if (isNull(index)) "" else getString(index)

    private fun parseNumbers(value: String): List<Int> = value.split(',')
        .mapNotNull { it.trim().toIntOrNull() }
        .filter { it in 1..10 }

    private fun parseProbabilities(value: String): List<Double> = value.split(',')
        .mapNotNull { it.trim().toDoubleOrNull() }
        .filter(Double::isFinite)

    private fun metricsFor(probabilities: List<Double>, actualNumber: Int) =
        runCatching { AiProbabilityVector.metrics(probabilities, actualNumber) }.getOrNull()

    private fun sha256(value: String): String = MessageDigest.getInstance("SHA-256")
        .digest(value.toByteArray(Charsets.UTF_8))
        .joinToString("") { "%02x".format(it) }

    private data class Pending(
        val id: Long,
        val targetPeriod: String,
        val position: Int,
        val top6: List<Int>,
        val top7: List<Int>,
        val probabilities: List<Double> = emptyList(),
    )
}

data class PendingSettlementTarget(
    val targetPeriod: String,
    val createdAtEpochMs: Long,
    val trainedThroughDrawTime: String,
)

data class AiForecastLockResult(
    val record: AiForecastRecord,
    val inserted: Boolean,
)

data class ArchiveIntegrity(
    val nativeValid: Boolean = true,
    val aiValid: Boolean = true,
    val consensusValid: Boolean = true,
    val nativeCount: Int = 0,
    val aiCount: Int = 0,
    val consensusCount: Int = 0,
) {
    val isValid: Boolean get() = nativeValid && aiValid && consensusValid
    val checkedCount: Int get() = nativeCount + aiCount + consensusCount
}
