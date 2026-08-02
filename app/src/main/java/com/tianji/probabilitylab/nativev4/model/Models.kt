package com.tianji.probabilitylab.nativev4.model

enum class LotteryType(
    val apiKey: String,
    val displayName: String,
    val subtitle: String,
    val lotCode: Int,
    val drawIntervalMinutes: Int,
    val historyTarget: Int,
) {
    XYFT("xyft", "幸运飞艇", "约 5 分钟一期", 10057, 5, 2_000),
    AZXY10("azxy10", "澳洲幸运10", "约 5 分钟一期", 10012, 5, 3_000),
}

data class Draw(
    val lottery: LotteryType,
    val period: String,
    val numbers: List<Int>,
    val drawTime: String = "",
    val source: String = "network",
)

data class SourceHealth(
    val label: String,
    val isFresh: Boolean,
    val independentSources: Int,
    val message: String,
    val syncedAtEpochMs: Long,
)

data class DrawSnapshot(
    val lottery: LotteryType,
    val history: List<Draw>,
    val latest: Draw,
    val nextPeriod: String,
    val sourceHealth: SourceHealth,
    val serverTimeEpochMs: Long? = null,
    val nextDrawAtEpochMs: Long? = null,
)

enum class EvidenceMode { CERTIFIED, OBSERVE }

data class ConfidenceInterval(val low: Double, val high: Double)

data class ModelPerformance(
    val key: String,
    val name: String,
    val shortName: String,
    val priorWeight: Double,
    val weight: Double,
    val shadowWeight: Double,
    val hitRate: Double,
    val logLoss: Double,
    val status: String,
)

data class PositionPrediction(
    val position: Int,
    val probabilities: List<Double>,
    val top6: List<Int>,
    val top7: List<Int>,
    val coverage6: Double,
    val coverage7: Double,
    val boundaryMargin: Double,
)

data class ForecastReport(
    val algorithmVersion: String,
    val trainedThroughPeriod: String,
    val targetPeriod: String,
    val historySize: Int,
    val validationDraws: Int,
    val mode: EvidenceMode,
    val displayUsesShadow: Boolean,
    val selectedPosition: Int,
    val positions: List<PositionPrediction>,
    val models: List<ModelPerformance>,
    val top6HitRate: Double,
    val top7HitRate: Double,
    val top6Interval: ConfidenceInterval,
    val top7Interval: ConfidenceInterval,
    val randomTop6Baseline: Double,
    val randomTop7Baseline: Double,
    val breakEvenTop7: Double,
    val averageLogLoss: Double,
    val randomLogLoss: Double,
    val dataAdequacy: Int,
    val blockedReasons: List<String>,
) {
    val selected: PositionPrediction get() = positions[selectedPosition]
}

data class LockedForecast(
    val id: Long,
    val lottery: LotteryType,
    val targetPeriod: String,
    val trainedThroughPeriod: String,
    val position: Int,
    val top6: List<Int>,
    val top7: List<Int>,
    val certified: Boolean,
    val createdAtEpochMs: Long,
    val reportHash: String,
    val previousHash: String,
    val actualNumber: Int?,
    val top6Hit: Boolean?,
    val top7Hit: Boolean?,
)

data class LiveAudit(
    val settled: Int,
    val top6Hits: Int,
    val top7Hits: Int,
) {
    val top6Rate: Double get() = if (settled == 0) 0.0 else top6Hits.toDouble() / settled
    val top7Rate: Double get() = if (settled == 0) 0.0 else top7Hits.toDouble() / settled
}
