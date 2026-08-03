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

data class AiLearningProfile(
    val settled: Int = 0,
    val top6Hits: Int = 0,
    val missStreak: Int = 0,
    val weights: List<Double> = DEFAULT_WEIGHTS,
    val lastChange: String = "尚无真实前向结算，当前使用均衡学习权重",
    val updatedAtEpochMs: Long = 0L,
) {
    val top6Rate: Double get() = if (settled == 0) 0.0 else top6Hits.toDouble() / settled

    fun toJson(): JSONObject = JSONObject()
        .put("settled", settled)
        .put("top6_hits", top6Hits)
        .put("top6_rate", top6Rate)
        .put("miss_streak", missStreak)
        .put("factor_names", JSONArray(AiAdaptiveSignalEngine.FACTOR_NAMES))
        .put("factor_weights", JSONArray(weights))
        .put("last_strategy_change", lastChange)
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
        .put("adaptive_scores_by_number_1_to_10", JSONArray(adaptiveScores))
        .put(
            "usage_rule",
            "这些权重由真实前向开奖结果逐期更新。命中会保留有效因子，未中会降低失效因子并提高对实际号码解释更好的因子；它们是可质疑的长期先验，不是必须照抄的答案。",
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
        val history = historyInput.filter { it.numbers.size == 10 }.takeLast(240)
        require(history.isNotEmpty()) { "没有可用于持续学习的开奖历史" }
        val values = history.map { it.numbers[position] }

        fun counts(window: Int): DoubleArray {
            val result = DoubleArray(10)
            values.takeLast(window).forEach { number -> if (number in 1..10) result[number - 1]++ }
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
                recencyRaw[number - 1] += exp(-age / 18.0)
            }
        }
        val recency = normalize(recencyRaw.toList())

        val omissionRaw = (1..10).map { number ->
            val latest = values.indexOfLast { it == number }
            val gap = if (latest < 0) values.size else values.lastIndex - latest
            0.18 + (1.0 - exp(-gap / 9.0))
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
        val transition = normalize((0 until 10).map { successors[it] + globalPrior[it] * shrinkStrength })

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
        val weights = normalizeWeights(profile.weights)
        val combined = normalize((0 until 10).map { number ->
            factors.indices.sumOf { factor -> factors[factor][number] * weights[factor] }
        })
        return AiAdaptiveSnapshot(position, profile.copy(weights = weights), factors, combined)
    }

    internal fun updatedWeights(
        oldWeights: List<Double>,
        factorProbabilities: List<List<Double>>,
        actualNumber: Int,
        settledBefore: Int,
    ): List<Double> {
        require(actualNumber in 1..10)
        val current = normalizeWeights(oldWeights)
        val eta = max(0.20, 0.95 / sqrt((settledBefore + 1).toDouble()))
        val updated = current.mapIndexed { index, weight ->
            val actualProbability = factorProbabilities[index][actualNumber - 1]
            val centeredReward = (actualProbability - 0.10) * 8.0
            (weight * exp(eta * centeredReward)).coerceAtLeast(0.025)
        }
        return normalizeWeights(updated)
    }

    private fun normalize(values: List<Double>): List<Double> {
        val safe = values.map { if (it.isFinite() && it > 0.0) it else 1e-9 }
        val sum = safe.sum().takeIf { it.isFinite() && it > 0.0 } ?: 1.0
        return safe.map { it / sum }
    }

    private fun normalizeWeights(values: List<Double>): List<Double> =
        normalize(if (values.size == FACTOR_NAMES.size) values else AiLearningProfile.DEFAULT_WEIGHTS)
}

/**
 * App-managed persistent learning. External APIs do not silently train themselves from one user's
 * calls, so Tianji records every resolved forward prediction and sends the updated strategy state
 * into the next request. This makes learning explicit, inspectable and reversible.
 */
class AiAdaptiveLearningStore(context: Context) {
    private val helper = LearningDb(context.applicationContext)

    @Synchronized
    fun profile(lotteryKey: String, profileId: String, model: String, position: Int): AiLearningProfile {
        val key = key(lotteryKey, profileId, model, position)
        return helper.readableDatabase.rawQuery(
            "SELECT settled, top6_hits, miss_streak, weights_json, last_change, updated_at " +
                "FROM ai_learning_profiles WHERE profile_key = ?",
            arrayOf(key),
        ).use { cursor ->
            if (!cursor.moveToFirst()) return@use AiLearningProfile()
            val weights = runCatching {
                val array = JSONArray(cursor.getString(3))
                (0 until array.length()).map { array.optDouble(it) }
            }.getOrDefault(AiLearningProfile.DEFAULT_WEIGHTS)
            AiLearningProfile(
                settled = cursor.getInt(0),
                top6Hits = cursor.getInt(1),
                missStreak = cursor.getInt(2),
                weights = weights,
                lastChange = cursor.getString(4),
                updatedAtEpochMs = cursor.getLong(5),
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
        .put("engine", "online_expert_weighting_v1")
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
            "先独立比较十个名次；持续学习权重只作为长期先验。连续未中时必须重新检查失效因子，不得机械复制上一期候选。",
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
        "chat:$outcomeId",
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
        records.forEach { record ->
            val actual = record.actualNumber ?: return@forEach
            learn(
                outcomeId = "official:${record.id}",
                lotteryKey = lotteryKey,
                profileId = record.profileId,
                model = record.model,
                position = record.position,
                top6 = record.top6,
                targetPeriod = record.targetPeriod,
                actualNumber = actual,
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
        val targetIndex = draws.indexOfFirst { it.period == targetPeriod }
        if (targetIndex <= 0) return profile(lotteryKey, profileId, model, position)
        val trainingHistory = draws.take(targetIndex)
        val before = profile(lotteryKey, profileId, model, position)
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
            val deltas = nextWeights.indices.map { index -> index to (nextWeights[index] - before.weights[index]) }
            val raised = deltas.maxByOrNull { it.second }?.first ?: 0
            val lowered = deltas.minByOrNull { it.second }?.first ?: 0
            val note = buildString {
                append(if (hit) "上期六码命中；" else "上期六码未中；")
                append("根据实际号码 $actualNumber 的可解释度，")
                append("提高“${AiAdaptiveSignalEngine.FACTOR_NAMES[raised]}”，")
                append("降低“${AiAdaptiveSignalEngine.FACTOR_NAMES[lowered]}”")
                if (!hit) append("，下一期禁止机械沿用原候选")
            }
            val next = AiLearningProfile(
                settled = before.settled + 1,
                top6Hits = before.top6Hits + if (hit) 1 else 0,
                missStreak = if (hit) 0 else before.missStreak + 1,
                weights = nextWeights,
                lastChange = note,
                updatedAtEpochMs = System.currentTimeMillis(),
            )
            val values = ContentValues().apply {
                put("profile_key", key(lotteryKey, profileId, model, position))
                put("settled", next.settled)
                put("top6_hits", next.top6Hits)
                put("miss_streak", next.missStreak)
                put("weights_json", JSONArray(next.weights).toString())
                put("last_change", next.lastChange)
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

    private fun key(lotteryKey: String, profileId: String, model: String, position: Int): String =
        listOf(lotteryKey.trim(), profileId.trim(), model.trim(), position.toString()).joinToString("\u001F")

    private class LearningDb(context: Context) :
        SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {
        override fun onCreate(db: SQLiteDatabase) {
            db.execSQL(
                "CREATE TABLE ai_learning_profiles (" +
                    "profile_key TEXT PRIMARY KEY, settled INTEGER NOT NULL, top6_hits INTEGER NOT NULL, " +
                    "miss_streak INTEGER NOT NULL, weights_json TEXT NOT NULL, last_change TEXT NOT NULL, " +
                    "updated_at INTEGER NOT NULL)",
            )
            db.execSQL(
                "CREATE TABLE ai_learning_outcomes (" +
                    "outcome_id TEXT PRIMARY KEY, profile_key TEXT NOT NULL, target_period TEXT NOT NULL, " +
                    "actual_number INTEGER NOT NULL, top6_hit INTEGER NOT NULL, created_at INTEGER NOT NULL)",
            )
            db.execSQL("CREATE INDEX ai_learning_outcomes_profile ON ai_learning_outcomes(profile_key)")
        }

        override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
    }

    private companion object {
        const val DATABASE_NAME = "ai_adaptive_learning_v1.db"
        const val DATABASE_VERSION = 1
    }
}
