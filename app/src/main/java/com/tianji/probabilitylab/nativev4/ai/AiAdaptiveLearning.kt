package com.tianji.probabilitylab.nativev4.ai

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.tianji.probabilitylab.nativev4.model.Draw
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.sqrt

/** Controls whether an AI receives the native model's already-selected answer. */
enum class AiJudgementMode(val label: String, val detail: String) {
    INDEPENDENT(
        "独立学习",
        "默认模式：不发送本机候选，AI只读取真实历史、独立统计和持续学习档案",
    ),
    NATIVE_REFERENCE(
        "参考本机",
        "把本机候选作为一份可质疑的参考，必须独立计算后才能采纳",
    ),
    CONTRARIAN(
        "反向审计",
        "读取本机候选，但优先寻找反例、过拟合和可替换号码",
    );

    companion object {
        fun fromId(value: String?): AiJudgementMode =
            entries.firstOrNull { it.name == value } ?: INDEPENDENT
    }
}

/** Keeps incompatible model/mode/persona histories from contaminating each other. */
object AiLearningStrategy {
    fun official(config: AiConfig): String = listOf(
        "official-v2",
        config.model.trim(),
        config.analysisMode.name,
        config.reasoningMode.name,
        config.reasoningProtocol.name,
    ).joinToString("|")

    fun official(record: AiForecastRecord): String = listOf(
        "official-v2",
        record.model.trim(),
        record.analysisMode.name,
        record.reasoningMode.name,
        record.reasoningProtocol.name,
    ).joinToString("|")

    fun chat(model: String, personaId: String, judgementMode: AiJudgementMode): String = listOf(
        "chat-v2",
        model.trim(),
        personaId.trim(),
        judgementMode.name,
    ).joinToString("|")
}

data class AiLearningProfile(
    val settled: Int = 0,
    val top6Hits: Int = 0,
    val missStreak: Int = 0,
    val recentTop6: List<Int> = emptyList(),
    val weights: List<Double> = DEFAULT_WEIGHTS,
    val lastChange: String = "尚无真实前向结算，当前使用均衡学习权重",
    val lastLearnedPeriod: String = "",
    val updatedAtEpochMs: Long = 0L,
) {
    val top6Rate: Double get() = if (settled == 0) 0.0 else top6Hits.toDouble() / settled
    val recent20Top6Rate: Double?
        get() = recentTop6.takeLast(20).takeIf { it.isNotEmpty() }?.average()

    fun toJson(): JSONObject = JSONObject()
        .put("settled", settled)
        .put("top6_hits", top6Hits)
        .put("top6_rate", top6Rate)
        .put("recent_20_top6_rate", recent20Top6Rate ?: JSONObject.NULL)
        .put("miss_streak", missStreak)
        .put("factor_names", JSONArray(AiAdaptiveSignalEngine.FACTOR_NAMES))
        .put("long_term_factor_weights", JSONArray(weights))
        .put("last_strategy_change", lastChange)
        .put("last_learned_period", lastLearnedPeriod)
        .put("updated_at", updatedAtEpochMs)

    companion object {
        val DEFAULT_WEIGHTS: List<Double> = List(6) { 1.0 / 6.0 }
    }
}

data class AiAdaptiveSnapshot(
    val position: Int,
    val profile: AiLearningProfile,
    val factorProbabilities: List<List<Double>>,
    val adaptiveScores: List<Double>,
    val effectiveWeights: List<Double>,
    val longTermBlend: Double,
    val periodsSinceLearning: Int,
    val regimeLabel: String,
) {
    fun toJson(): JSONObject = JSONObject()
        .put("position", position + 1)
        .put("learning_profile", profile.toJson())
        .put(
            "factor_probabilities_by_number_1_to_10",
            JSONObject().apply {
                AiAdaptiveSignalEngine.FACTOR_NAMES.forEachIndexed { index, name ->
                    put(name, JSONArray(factorProbabilities[index]))
                }
            },
        )
        .put("effective_factor_weights", JSONArray(effectiveWeights))
        .put("long_term_prior_blend", longTermBlend)
        .put("periods_since_last_learning", periodsSinceLearning)
        .put("current_regime", regimeLabel)
        .put("adaptive_scores_by_number_1_to_10", JSONArray(adaptiveScores))
        .put(
            "usage_rule",
            "当前开奖历史必须优先于旧学习权重。长期权重只是可质疑先验，最高只参与45%；" +
                "距离上次学习期数越多、连续未中越多，其影响自动衰减。其余权重按本期短中窗变化、" +
                "转移样本和稳定程度重新计算，禁止机械复用几天前的策略或候选。",
        )
}

/** Pure deterministic signal engine. It never reads the native model's selected candidate. */
object AiAdaptiveSignalEngine {
    val FACTOR_NAMES = listOf(
        "贝叶斯长窗频率",
        "指数衰减近期热度",
        "遗漏回补风险",
        "收缩后继转移",
        "短中窗状态变化",
        "跨窗口稳定性",
    )

    fun extractRequestedPosition(text: String): Int? {
        val token = Regex("""第\s*([一二三四五六七八九十0-9]{1,2})\s*名""")
            .find(text)?.groupValues?.getOrNull(1) ?: return null
        val value = token.toIntOrNull() ?: when (token) {
            "一" -> 1; "二" -> 2; "三" -> 3; "四" -> 4; "五" -> 5
            "六" -> 6; "七" -> 7; "八" -> 8; "九" -> 9; "十" -> 10
            else -> return null
        }
        return (value - 1).takeIf { it in 0..9 }
    }

    fun compute(
        historyInput: List<Draw>,
        position: Int,
        profile: AiLearningProfile = AiLearningProfile(),
    ): AiAdaptiveSnapshot {
        require(position in 0..9)
        val history = historyInput
            .filter { it.numbers.size == 10 }
            .distinctBy { it.period }
            .takeLast(240)
        require(history.isNotEmpty()) { "没有可用于持续学习的开奖历史" }
        val values = history.map { it.numbers[position] }

        fun counts(window: Int): DoubleArray {
            val result = DoubleArray(10)
            values.takeLast(window).forEach { number ->
                if (number in 1..10) result[number - 1]++
            }
            return result
        }

        val count20 = counts(20)
        val count60 = counts(60)
        val count120 = counts(120)
        val size20 = values.takeLast(20).size.coerceAtLeast(1).toDouble()
        val size60 = values.takeLast(60).size.coerceAtLeast(1).toDouble()
        val size120 = values.takeLast(120).size.coerceAtLeast(1).toDouble()

        val bayes = normalize((0 until 10).map { (count120[it] + 1.0) / (size120 + 10.0) })

        val recencyRaw = DoubleArray(10)
        values.forEachIndexed { index, number ->
            if (number in 1..10) {
                val age = values.lastIndex - index
                recencyRaw[number - 1] += exp(-age / 15.0)
            }
        }
        val recency = normalize(recencyRaw.toList())

        // Omission is intentionally non-monotonic: a longer gap is not proof a number is "due".
        val omissionRaw = (1..10).map { number ->
            val latest = values.indexOfLast { it == number }
            val gap = if (latest < 0) values.size else values.lastIndex - latest
            0.45 + exp(-abs(gap - 9.0) / 7.0)
        }
        val omission = normalize(omissionRaw)

        val globalPrior = normalize((0 until 10).map { count120[it] + 1.0 })
        val current = values.last()
        val successors = DoubleArray(10)
        var transitionSamples = 0
        for (index in 1 until values.size) {
            if (values[index - 1] == current && values[index] in 1..10) {
                successors[values[index] - 1]++
                transitionSamples++
            }
        }
        val shrinkStrength = max(5.0, 18.0 - transitionSamples)
        val transition = normalize(
            (0 until 10).map { successors[it] + globalPrior[it] * shrinkStrength },
        )

        val trend = normalize((0 until 10).map { index ->
            val short = count20[index] / size20
            val medium = count60[index] / size60
            exp((short - medium) * 7.0)
        })

        val stability = normalize((0 until 10).map { index ->
            val short = count20[index] / size20
            val medium = count60[index] / size60
            val long = count120[index] / size120
            1.0 / (0.04 + abs(short - medium) + 0.6 * abs(medium - long))
        })

        val factors = listOf(bayes, recency, omission, transition, trend, stability)
        val shortMediumDrift = (0 until 10).map { index ->
            abs(count20[index] / size20 - count60[index] / size60)
        }.average()
        val mediumLongDrift = (0 until 10).map { index ->
            abs(count60[index] / size60 - count120[index] / size120)
        }.average()
        val driftStrength = (shortMediumDrift * 12.0).coerceIn(0.0, 1.0)
        val stabilityStrength = (1.0 - (shortMediumDrift + mediumLongDrift) * 8.0)
            .coerceIn(0.0, 1.0)
        val transitionConfidence = (transitionSamples / 14.0).coerceIn(0.0, 1.0)

        val currentRegimeWeights = normalizeWeights(
            listOf(
                1.0 + stabilityStrength * 0.8,
                1.0 + driftStrength * 2.0,
                0.62,
                0.75 + transitionConfidence * 1.35,
                0.9 + driftStrength * 2.5,
                0.9 + stabilityStrength * 1.5,
            ),
        )
        val periodsSinceLearning = periodsSinceLearning(history, profile.lastLearnedPeriod)
        val sampleConfidence = (profile.settled / 60.0).coerceIn(0.0, 1.0)
        val stalenessDecay = if (profile.lastLearnedPeriod.isBlank()) {
            0.0
        } else {
            exp(-periodsSinceLearning / 10.0)
        }
        val missDecay = exp(-profile.missStreak / 4.0)
        val longTermBlend = (0.45 * sampleConfidence * stalenessDecay * missDecay)
            .coerceIn(0.0, 0.45)
        val longTermWeights = normalizeWeights(profile.weights)
        val effectiveWeights = normalizeWeights(
            currentRegimeWeights.indices.map { index ->
                currentRegimeWeights[index] * (1.0 - longTermBlend) +
                    longTermWeights[index] * longTermBlend
            },
        )
        val combined = normalize((0 until 10).map { number ->
            factors.indices.sumOf { factor ->
                factors[factor][number] * effectiveWeights[factor]
            }
        })
        val regimeLabel = when {
            driftStrength >= 0.65 -> "短期结构快速变化：近期热度与短中窗变化优先"
            driftStrength >= 0.30 -> "短期结构正在变化：新旧窗口动态混合"
            else -> "结构相对稳定：稳定性与长窗频率可适度参考"
        }
        return AiAdaptiveSnapshot(
            position = position,
            profile = profile.copy(weights = longTermWeights),
            factorProbabilities = factors,
            adaptiveScores = combined,
            effectiveWeights = effectiveWeights,
            longTermBlend = longTermBlend,
            periodsSinceLearning = periodsSinceLearning,
            regimeLabel = regimeLabel,
        )
    }

    internal fun updatedWeights(
        oldWeights: List<Double>,
        factorProbabilities: List<List<Double>>,
        actualNumber: Int,
        settledBefore: Int,
    ): List<Double> {
        require(actualNumber in 1..10)
        val uniform = 1.0 / FACTOR_NAMES.size
        val current = normalizeWeights(oldWeights)
        // Every result forgets a small part of old experience so the profile cannot become locked.
        val forgotten = current.map { weight -> weight * 0.94 + uniform * 0.06 }
        val eta = max(0.12, 0.82 / sqrt((settledBefore + 1).toDouble()))
        val updated = forgotten.mapIndexed { index, weight ->
            val actualProbability = factorProbabilities[index][actualNumber - 1]
            val centeredReward = (actualProbability - 0.10) * 8.0
            (weight * exp(eta * centeredReward)).coerceAtLeast(0.025)
        }
        return normalizeWeights(updated)
    }

    private fun periodsSinceLearning(history: List<Draw>, lastLearnedPeriod: String): Int {
        if (lastLearnedPeriod.isBlank()) return history.size
        val index = history.indexOfLast { it.period == lastLearnedPeriod }
        return if (index < 0) history.size else history.lastIndex - index
    }

    private fun normalize(values: List<Double>): List<Double> {
        val safe = values.map { if (it.isFinite() && it > 0.0) it else 1e-9 }
        val sum = safe.sum().takeIf { it.isFinite() && it > 0.0 } ?: 1.0
        return safe.map { it / sum }
    }

    private fun normalizeWeights(values: List<Double>): List<Double> =
        normalize(
            if (values.size == FACTOR_NAMES.size) {
                values
            } else {
                AiLearningProfile.DEFAULT_WEIGHTS
            },
        )
}

/**
 * App-managed persistent learning. External APIs do not silently train themselves from one user's
 * calls, so Tianji records every resolved forward prediction and sends the updated strategy state
 * into the next request. Current history always outranks stale stored weights.
 */
class AiAdaptiveLearningStore(context: Context) {
    private val helper = LearningDb(context.applicationContext)

    @Synchronized
    fun profile(
        lotteryKey: String,
        profileId: String,
        model: String,
        position: Int,
    ): AiLearningProfile {
        val profileKey = key(lotteryKey, profileId, model, position)
        return helper.readableDatabase.rawQuery(
            "SELECT settled, top6_hits, miss_streak, recent_hits_json, weights_json, " +
                "last_change, last_period, updated_at " +
                "FROM ai_learning_profiles WHERE profile_key = ?",
            arrayOf(profileKey),
        ).use { cursor ->
            if (!cursor.moveToFirst()) return@use AiLearningProfile()
            val recentHits = runCatching {
                val array = JSONArray(cursor.getString(3))
                (0 until array.length()).map { array.optInt(it).coerceIn(0, 1) }
            }.getOrDefault(emptyList())
            val weights = runCatching {
                val array = JSONArray(cursor.getString(4))
                (0 until array.length()).map { array.optDouble(it) }
            }.getOrDefault(AiLearningProfile.DEFAULT_WEIGHTS)
            AiLearningProfile(
                settled = cursor.getInt(0),
                top6Hits = cursor.getInt(1),
                missStreak = cursor.getInt(2),
                recentTop6 = recentHits,
                weights = weights,
                lastChange = cursor.getString(5),
                lastLearnedPeriod = cursor.getString(6),
                updatedAtEpochMs = cursor.getLong(7),
            )
        }
    }

    @Synchronized
    fun snapshot(
        history: List<Draw>,
        lotteryKey: String,
        profileId: String,
        model: String,
        position: Int,
    ): JSONObject = AiAdaptiveSignalEngine.compute(
        history,
        position,
        profile(lotteryKey, profileId, model, position),
    ).toJson()

    @Synchronized
    fun snapshotAll(
        history: List<Draw>,
        lotteryKey: String,
        profileId: String,
        model: String,
    ): JSONObject = JSONObject()
        .put("engine", "regime_aware_online_weighting_v2")
        .put(
            "positions",
            JSONArray((0 until 10).map { position ->
                AiAdaptiveSignalEngine.compute(
                    history,
                    position,
                    profile(lotteryKey, profileId, model, position),
                ).toJson()
            }),
        )
        .put(
            "instruction",
            "先用当前接口历史独立判断十个名次，再把长期档案当作弱先验。" +
                "几天未运行或跨越多期时旧权重会自动衰减；连续未中时必须重新选择策略，" +
                "不得机械复制上一期候选。",
        )

    @Synchronized
    fun learnChatCandidate(
        outcomeId: String,
        lotteryKey: String,
        profileId: String,
        model: String,
        position: Int,
        top6: List<Int>,
        targetPeriod: String,
        actualNumber: Int,
        draws: List<Draw>,
    ): AiLearningProfile = learn(
        "chat-v2:$outcomeId",
        lotteryKey,
        profileId,
        model,
        position,
        top6,
        targetPeriod,
        actualNumber,
        draws,
    )

    @Synchronized
    fun learnOfficialRecords(
        lotteryKey: String,
        draws: List<Draw>,
        records: List<AiForecastRecord>,
    ) {
        val periodOrder = draws.mapIndexed { index, draw -> draw.period to index }.toMap()
        records.asSequence()
            .filter { it.actualNumber != null && periodOrder.containsKey(it.targetPeriod) }
            .sortedWith(
                compareBy<AiForecastRecord>(
                    { periodOrder[it.targetPeriod] ?: Int.MAX_VALUE },
                    { it.id },
                ),
            )
            .forEach { record ->
                learn(
                    outcomeId = "official-v2:${record.id}",
                    lotteryKey = lotteryKey,
                    profileId = record.profileId,
                    model = AiLearningStrategy.official(record),
                    position = record.position,
                    top6 = record.top6,
                    targetPeriod = record.targetPeriod,
                    actualNumber = requireNotNull(record.actualNumber),
                    draws = draws,
                )
            }
    }

    private fun learn(
        outcomeId: String,
        lotteryKey: String,
        profileId: String,
        model: String,
        position: Int,
        top6: List<Int>,
        targetPeriod: String,
        actualNumber: Int,
        draws: List<Draw>,
    ): AiLearningProfile {
        if (position !in 0..9 || actualNumber !in 1..10) {
            return profile(lotteryKey, profileId, model, position.coerceIn(0, 9))
        }
        val before = profile(lotteryKey, profileId, model, position)
        if (hasOutcome(outcomeId)) return before
        val targetIndex = draws.indexOfFirst { it.period == targetPeriod }
        if (targetIndex <= 0) return before
        val trainingHistory = draws.take(targetIndex)
        val snapshot = AiAdaptiveSignalEngine.compute(trainingHistory, position, before)
        val database = helper.writableDatabase
        database.beginTransaction()
        try {
            val outcomeValues = ContentValues().apply {
                put("outcome_id", outcomeId)
                put("profile_key", key(lotteryKey, profileId, model, position))
                put("target_period", targetPeriod)
                put("actual_number", actualNumber)
                put("top6_hit", if (actualNumber in top6) 1 else 0)
                put("created_at", System.currentTimeMillis())
            }
            val inserted = database.insertWithOnConflict(
                "ai_learning_outcomes",
                null,
                outcomeValues,
                SQLiteDatabase.CONFLICT_IGNORE,
            )
            if (inserted == -1L) {
                database.setTransactionSuccessful()
                return before
            }
            val nextWeights = AiAdaptiveSignalEngine.updatedWeights(
                before.weights,
                snapshot.factorProbabilities,
                actualNumber,
                before.settled,
            )
            val hit = actualNumber in top6
            val deltas = nextWeights.indices.map { index ->
                index to (nextWeights[index] - before.weights[index])
            }
            val raised = deltas.maxByOrNull { it.second }?.first ?: 0
            val lowered = deltas.minByOrNull { it.second }?.first ?: 0
            val note = buildString {
                append(if (hit) "本期六码命中；" else "本期六码未中；")
                append("长期先验提高“${AiAdaptiveSignalEngine.FACTOR_NAMES[raised]}”，")
                append("降低“${AiAdaptiveSignalEngine.FACTOR_NAMES[lowered]}”。")
                append("下一期仍须按最新历史重新判断")
                if (!hit) append("，禁止机械沿用原候选")
            }
            val nextRecent = (before.recentTop6 + if (hit) 1 else 0).takeLast(40)
            val next = AiLearningProfile(
                settled = before.settled + 1,
                top6Hits = before.top6Hits + if (hit) 1 else 0,
                missStreak = if (hit) 0 else before.missStreak + 1,
                recentTop6 = nextRecent,
                weights = nextWeights,
                lastChange = note,
                lastLearnedPeriod = targetPeriod,
                updatedAtEpochMs = System.currentTimeMillis(),
            )
            val values = ContentValues().apply {
                put("profile_key", key(lotteryKey, profileId, model, position))
                put("settled", next.settled)
                put("top6_hits", next.top6Hits)
                put("miss_streak", next.missStreak)
                put("recent_hits_json", JSONArray(next.recentTop6).toString())
                put("weights_json", JSONArray(next.weights).toString())
                put("last_change", next.lastChange)
                put("last_period", next.lastLearnedPeriod)
                put("updated_at", next.updatedAtEpochMs)
            }
            database.insertWithOnConflict(
                "ai_learning_profiles",
                null,
                values,
                SQLiteDatabase.CONFLICT_REPLACE,
            )
            database.setTransactionSuccessful()
            return next
        } finally {
            database.endTransaction()
        }
    }

    private fun hasOutcome(outcomeId: String): Boolean =
        helper.readableDatabase.rawQuery(
            "SELECT 1 FROM ai_learning_outcomes WHERE outcome_id = ? LIMIT 1",
            arrayOf(outcomeId),
        ).use { it.moveToFirst() }

    private fun key(
        lotteryKey: String,
        profileId: String,
        model: String,
        position: Int,
    ): String = listOf(
        lotteryKey.trim(),
        profileId.trim(),
        model.trim(),
        position.toString(),
    ).joinToString("\u001F")

    private class LearningDb(context: Context) :
        SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {
        override fun onCreate(db: SQLiteDatabase) {
            db.execSQL(
                "CREATE TABLE ai_learning_profiles (" +
                    "profile_key TEXT PRIMARY KEY, settled INTEGER NOT NULL, " +
                    "top6_hits INTEGER NOT NULL, miss_streak INTEGER NOT NULL, " +
                    "recent_hits_json TEXT NOT NULL, weights_json TEXT NOT NULL, " +
                    "last_change TEXT NOT NULL, last_period TEXT NOT NULL, " +
                    "updated_at INTEGER NOT NULL)",
            )
            db.execSQL(
                "CREATE TABLE ai_learning_outcomes (" +
                    "outcome_id TEXT PRIMARY KEY, profile_key TEXT NOT NULL, " +
                    "target_period TEXT NOT NULL, actual_number INTEGER NOT NULL, " +
                    "top6_hit INTEGER NOT NULL, created_at INTEGER NOT NULL)",
            )
            db.execSQL(
                "CREATE INDEX ai_learning_outcomes_profile " +
                    "ON ai_learning_outcomes(profile_key)",
            )
        }

        override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
            if (oldVersion < 2) {
                db.execSQL(
                    "ALTER TABLE ai_learning_profiles ADD COLUMN " +
                        "recent_hits_json TEXT NOT NULL DEFAULT '[]'",
                )
                db.execSQL(
                    "ALTER TABLE ai_learning_profiles ADD COLUMN " +
                        "last_period TEXT NOT NULL DEFAULT ''",
                )
            }
        }
    }

    private companion object {
        const val DATABASE_NAME = "ai_adaptive_learning_v1.db"
        const val DATABASE_VERSION = 2
    }
}
