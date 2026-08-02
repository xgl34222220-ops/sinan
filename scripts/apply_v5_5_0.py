from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    file = Path(path)
    value = file.read_text(encoding="utf-8")
    if old not in value:
        raise RuntimeError(f"missing patch target: {label} in {path}")
    file.write_text(value.replace(old, new, 1), encoding="utf-8")


def write(path: str, content: str) -> None:
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")


# Version metadata.
replace_once(
    "app/build.gradle.kts",
    '        versionCode = 24\n        versionName = "5.4.7"',
    '        versionCode = 25\n        versionName = "5.5.0"',
    "app version",
)
replace_once("README.md", "- 版本：5.4.7", "- 版本：5.5.0", "README version")
replace_once(
    "README.md",
    "## v5.4.5 重点优化",
    """## v5.5.0 稳定重构版

- 真正取消运行中与排队中的 AI 任务，刷新、切换彩种和手动取消不会继续产生无效调用。
- AI 返回后再次核验最新开奖、目标期和服务器时间，跨期开奖的结果不再写入前向档案。
- 强制同步后再次检查目标期冻结记录，避免目标期变化造成重复计费。
- 增加同期开奖冲突检测、历史内容指纹缓存和按彩种区分的数据充分度。
- 拆出任务注册、目标期守卫、开奖合并策略和历史指纹等独立领域组件，并补充单元测试。
- 修正观察模式误显示为认证、概率条比例、系统字体缩放和开奖后轮询体验。
- 清理版本专用发布工作流，统一为通用 CI 与标签发布流程。

## v5.4.5 重点优化""",
    "README v5.5 section",
)

# Per-lottery history targets.
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/model/Models.kt",
    """    val lotCode: Int,
    val drawIntervalMinutes: Int,
) {
    XYFT(\"xyft\", \"幸运飞艇\", \"约 5 分钟一期\", 10057, 5),
    AZXY10(\"azxy10\", \"澳洲幸运10\", \"约 5 分钟一期\", 10012, 5),
}""",
    """    val lotCode: Int,
    val drawIntervalMinutes: Int,
    val historyTarget: Int,
) {
    XYFT(\"xyft\", \"幸运飞艇\", \"约 5 分钟一期\", 10057, 5, 2_000),
    AZXY10(\"azxy10\", \"澳洲幸运10\", \"约 5 分钟一期\", 10012, 5, 3_000),
}""",
    "lottery history targets",
)

# Deterministic cache input and per-lottery adequacy.
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/NativeEnsemblePredictor.kt",
    '    const val ALGORITHM_VERSION = "native-ensemble-4.1"',
    '    const val ALGORITHM_VERSION = "native-ensemble-5.0"',
    "algorithm version",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/NativeEnsemblePredictor.kt",
    "fun predict(historyInput: List<Draw>, payoutMultiplier: Double = 9.8): ForecastReport {",
    """fun predict(
        historyInput: List<Draw>,
        payoutMultiplier: Double = 9.8,
        historyTarget: Int = 3_000,
    ): ForecastReport {""",
    "predict signature",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/NativeEnsemblePredictor.kt",
    "dataAdequacy = ((history.size / 3_000.0) * 100).roundToInt().coerceIn(10, 100),",
    """dataAdequacy = (
                (history.size / historyTarget.coerceAtLeast(MIN_HISTORY).toDouble()) * 100
            ).roundToInt().coerceIn(10, 100),""",
    "data adequacy",
)

# Independent domain helpers.
write(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiTaskRegistry.kt",
    """package com.tianji.probabilitylab.nativev4.ai

import java.util.concurrent.Callable
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.FutureTask
import java.util.concurrent.ThreadPoolExecutor

/** Tracks queued and running AI work so cancellation also removes tasks that have not started yet. */
class AiTaskRegistry(private val executor: ThreadPoolExecutor) {
    private val tasks = ConcurrentHashMap<String, MutableSet<FutureTask<Unit>>>()

    fun submit(profileId: String, block: () -> Unit) {
        lateinit var task: FutureTask<Unit>
        task = FutureTask(
            Callable {
                try {
                    if (Thread.currentThread().isInterrupted) throw InterruptedException("AI 任务已取消")
                    block()
                    Unit
                } finally {
                    tasks[profileId]?.let { set ->
                        set.remove(task)
                        if (set.isEmpty()) tasks.remove(profileId, set)
                    }
                }
            },
        )
        tasks.computeIfAbsent(profileId) { ConcurrentHashMap.newKeySet() }.add(task)
        executor.execute(task)
    }

    fun cancel(profileId: String? = null) {
        val selected = if (profileId == null) tasks.values.flatMap { it.toList() }
        else tasks.remove(profileId)?.toList().orEmpty()
        selected.forEach { it.cancel(true) }
        if (profileId == null) tasks.clear()
        executor.purge()
    }

    fun close() {
        cancel()
        executor.shutdownNow()
    }
}
""",
)
write(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/data/DrawMergePolicy.kt",
    """package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.model.Draw

/** Rejects conflicting upstream records instead of silently overwriting the same period. */
object DrawMergePolicy {
    fun merge(draws: List<Draw>): List<Draw> {
        val grouped = draws.groupBy(Draw::period)
        val conflict = grouped.entries.firstOrNull { (_, records) ->
            records.map(Draw::numbers).distinct().size > 1
        }
        require(conflict == null) {
            val period = conflict?.key.orEmpty()
            "上游同一期 $period 返回了不同开奖号码，已停止预测并等待重新核验"
        }
        return grouped.values
            .map(List<Draw>::last)
            .sortedWith(compareBy<Draw>({ it.period.length }, Draw::period))
    }
}
""",
)
write(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/data/TargetPeriodGuard.kt",
    """package com.tianji.probabilitylab.nativev4.data

data class TargetPeriodCheck(val open: Boolean, val message: String)

/** Uses a freshly fetched latest payload to prevent post-draw results entering the forward archive. */
object TargetPeriodGuard {
    fun evaluate(
        expectedTargetPeriod: String,
        latestPeriod: String,
        nextPeriod: String,
        serverTimeEpochMs: Long?,
        nextDrawAtEpochMs: Long?,
        safetyWindowMs: Long = 5_000L,
    ): TargetPeriodCheck {
        if (latestPeriod == expectedTargetPeriod) {
            return TargetPeriodCheck(false, "目标期已经开奖，结果仅可查看，未写入前向档案")
        }
        if (nextPeriod != expectedTargetPeriod) {
            return TargetPeriodCheck(
                false,
                "目标期已变化：当前接口下一期为 $nextPeriod，原目标期 $expectedTargetPeriod 未写入档案",
            )
        }
        if (
            serverTimeEpochMs != null && nextDrawAtEpochMs != null &&
            serverTimeEpochMs >= nextDrawAtEpochMs - safetyWindowMs
        ) {
            return TargetPeriodCheck(false, "距离开奖不足 ${safetyWindowMs / 1_000} 秒，结果未写入前向档案")
        }
        return TargetPeriodCheck(true, "目标期仍开放")
    }
}
""",
)
write(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/domain/HistoryFingerprint.kt",
    """package com.tianji.probabilitylab.nativev4.domain

import com.tianji.probabilitylab.nativev4.model.Draw
import java.security.MessageDigest

object HistoryFingerprint {
    fun of(draws: List<Draw>): String {
        val canonical = draws.joinToString("\n") { draw ->
            listOf(
                draw.lottery.apiKey,
                draw.period,
                draw.numbers.joinToString(","),
                draw.drawTime,
                draw.source,
            ).joinToString("|")
        }
        return MessageDigest.getInstance("SHA-256")
            .digest(canonical.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
    }
}
""",
)

# Lottery API conflict handling and fresh target verification.
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/data/LotteryApi.kt",
    """        val merged = (fetched.draws + latestPayload.draw)
            .associateBy { it.period }
            .values
            .sortedWith(compareBy<Draw>({ it.period.length }, { it.period }))
            .takeLast(3000)""",
    """        val merged = DrawMergePolicy.merge(fetched.draws + latestPayload.draw)
            .takeLast(lottery.historyTarget)""",
    "snapshot merge",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/data/LotteryApi.kt",
    """            draws = draws
                .associateBy(Draw::period)
                .values
                .sortedWith(compareBy<Draw>({ it.period.length }, { it.period })),""",
    """            draws = DrawMergePolicy.merge(draws),""",
    "historical merge",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/data/LotteryApi.kt",
    """    /** Fetches exact historical dates used to settle forecasts created before the recent window. */
    fun fetchHistoricalDates(lottery: LotteryType, dates: Set<LocalDate>): HistoricalFetchResult =
        fetchDates(lottery, dates.sorted().take(MAX_BACKFILL_DATES), cancellationGeneration.get())

    private fun fetchDates(""",
    """    /** Fetches exact historical dates used to settle forecasts created before the recent window. */
    fun fetchHistoricalDates(lottery: LotteryType, dates: Set<LocalDate>): HistoricalFetchResult =
        fetchDates(lottery, dates.sorted().take(MAX_BACKFILL_DATES), cancellationGeneration.get())

    fun verifyTargetPeriodOpen(
        lottery: LotteryType,
        targetPeriod: String,
        safetyWindowMs: Long = 5_000L,
    ): TargetPeriodCheck {
        val token = cancellationGeneration.get()
        val latest = fetchLatestWithRetry(lottery, token) ?: error("最新开奖接口没有返回有效期号")
        ensureActive(token)
        return TargetPeriodGuard.evaluate(
            expectedTargetPeriod = targetPeriod,
            latestPeriod = latest.draw.period,
            nextPeriod = latest.nextPeriod,
            serverTimeEpochMs = latest.serverTimeEpochMs,
            nextDrawAtEpochMs = latest.nextDrawAtEpochMs,
            safetyWindowMs = safetyWindowMs,
        )
    }

    private fun fetchDates(""",
    "target verification API",
)

# Database duplicate guard.
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/data/AppDatabase.kt",
    """    fun hasDraw(lottery: LotteryType, period: String): Boolean = readableDatabase.rawQuery(
        \"SELECT 1 FROM draws WHERE lottery_type = ? AND period = ? LIMIT 1\",
        arrayOf(lottery.apiKey, period),
    ).use(Cursor::moveToFirst)

    fun settleAiForecasts(""",
    """    fun hasDraw(lottery: LotteryType, period: String): Boolean = readableDatabase.rawQuery(
        \"SELECT 1 FROM draws WHERE lottery_type = ? AND period = ? LIMIT 1\",
        arrayOf(lottery.apiKey, period),
    ).use(Cursor::moveToFirst)

    fun hasAiForecast(lottery: LotteryType, profileId: String, targetPeriod: String): Boolean =
        readableDatabase.rawQuery(
            \"\"\"SELECT 1 FROM ai_forecast_records
                WHERE lottery_type = ? AND profile_id = ? AND target_period = ? LIMIT 1\"\"\".trimIndent(),
            arrayOf(lottery.apiKey, profileId, targetPeriod),
        ).use(Cursor::moveToFirst)

    fun settleAiForecasts(""",
    "AI duplicate query",
)

# Controller task lifecycle, duplicate checks, fresh freeze gate and content fingerprint cache.
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    "import com.tianji.probabilitylab.nativev4.ai.AiRunStatus\n",
    "import com.tianji.probabilitylab.nativev4.ai.AiRunStatus\nimport com.tianji.probabilitylab.nativev4.ai.AiTaskRegistry\n",
    "AiTaskRegistry import",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    "import com.tianji.probabilitylab.nativev4.data.LotteryApi\n",
    "import com.tianji.probabilitylab.nativev4.data.LotteryApi\nimport com.tianji.probabilitylab.nativev4.domain.HistoryFingerprint\n",
    "HistoryFingerprint import",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """    private val aiExecutor = ThreadPoolExecutor(
        initialAiConcurrency, initialAiConcurrency, 60L, TimeUnit.SECONDS, LinkedBlockingQueue(),
    )
    private val mainHandler""",
    """    private val aiExecutor = ThreadPoolExecutor(
        initialAiConcurrency, initialAiConcurrency, 60L, TimeUnit.SECONDS, LinkedBlockingQueue(),
    )
    private val aiTasks = AiTaskRegistry(aiExecutor)
    private val mainHandler""",
    "AI task registry",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    "private val reportCache = mutableMapOf<LotteryType, ForecastReport>()",
    "private val reportCache = mutableMapOf<LotteryType, CachedForecast>()",
    "cache type",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """    fun refresh() {
        api.cancelActiveRequests()
        remoteAiAnalyzer.cancelActiveRequests()
        aiGeneration.incrementAndGet()""",
    """    fun refresh() {
        aiTasks.cancel()
        api.cancelActiveRequests()
        remoteAiAnalyzer.cancelActiveRequests()
        aiGeneration.incrementAndGet()""",
    "refresh cancellation",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """    fun deleteAiConfig(profileId: String) {
        aiConfigs = aiConfigs.filterNot { it.id == profileId }""",
    """    fun deleteAiConfig(profileId: String) {
        aiTasks.cancel(profileId)
        remoteAiAnalyzer.cancelActiveRequests(profileId)
        aiConfigs = aiConfigs.filterNot { it.id == profileId }""",
    "delete config cancellation",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """        aiExecutor.execute {
            val result = runCatching { remoteAiAnalyzer.listModels(config) }""",
    """        aiTasks.submit(profileId) {
            val result = runCatching { remoteAiAnalyzer.listModels(config) }""",
    "model list task",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """    fun cancelAi(profileId: String) {
        remoteAiAnalyzer.cancelActiveRequests(profileId)""",
    """    fun cancelAi(profileId: String) {
        aiTasks.cancel(profileId)
        remoteAiAnalyzer.cancelActiveRequests(profileId)""",
    "manual cancellation",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """        aiExecutor.execute {
            val result = runCatching { remoteAiAnalyzer.testConnection(config) }""",
    """        aiTasks.submit(profileId) {
            val result = runCatching { remoteAiAnalyzer.testConnection(config) }""",
    "connection test task",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """                        val runningStatuses = configs.associate { config ->
                            val reasoning = AiReasoningEngine.resolve(config).displayLabel
                            val message = \"接口历史已同步，正在${config.analysisMode.label} · $reasoning…\"
                            config.id to AiRunStatus(config.id, AiConnectionState.ANALYZING, message)
                        }
                        state = preparation.loadedState.copy(
                            aiError = null,
                            aiStatuses = state.aiStatuses + runningStatuses,
                            aiForecasts = state.aiForecasts,
                        )
                        launchAiRequests(configs, preparation.apiSnapshot, report, token)""",
    """                        val eligibleConfigs = configs.filterNot { config ->
                            database.hasAiForecast(lottery, config.id, report.targetPeriod)
                        }
                        val skippedConfigs = configs - eligibleConfigs.toSet()
                        val skippedStatuses = skippedConfigs.associate { config ->
                            config.id to AiRunStatus(
                                config.id,
                                AiConnectionState.CONNECTED,
                                \"同步后发现本目标期已有冻结结果，未调用计费接口\",
                            )
                        }
                        val runningStatuses = eligibleConfigs.associate { config ->
                            val reasoning = AiReasoningEngine.resolve(config).displayLabel
                            val message = \"接口历史已同步，正在${config.analysisMode.label} · $reasoning…\"
                            config.id to AiRunStatus(config.id, AiConnectionState.ANALYZING, message)
                        }
                        state = preparation.loadedState.copy(
                            aiError = null,
                            aiStatuses = state.aiStatuses + skippedStatuses + runningStatuses,
                            aiForecasts = state.aiForecasts,
                        )
                        if (eligibleConfigs.isNotEmpty()) {
                            launchAiRequests(eligibleConfigs, preparation.apiSnapshot, report, token)
                        }""",
    "post-sync duplicate guard",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """        configs.forEach { config ->
            aiExecutor.execute {
                val result = runCatching {
                    require(state.aiStatuses[config.id]?.state != AiConnectionState.CANCELLED) {
                        \"请求已在发送前取消\"
                    }
                    val forecast = remoteAiAnalyzer.analyze(config, snapshot, report)
                    require(aiGeneration.get() == token) { \"数据已经刷新，本次 AI 结果已作废\" }
                    require(!database.hasDraw(snapshot.lottery, report.targetPeriod)) {
                        \"目标期已经开奖，AI 结果未写入前向档案\"
                    }
                    require(isBeforeForecastDeadline(snapshot)) {
                        \"AI 在目标期开奖时间后返回，结果未写入前向档案\"
                    }
                    val locked = database.lockAiForecast(snapshot.lottery, report, forecast)""",
    """        configs.forEach { config ->
            aiTasks.submit(config.id) {
                val result = runCatching {
                    require(aiGeneration.get() == token && !Thread.currentThread().isInterrupted) {
                        \"请求已在发送前取消\"
                    }
                    require(state.aiStatuses[config.id]?.state != AiConnectionState.CANCELLED) {
                        \"请求已在发送前取消\"
                    }
                    require(!database.hasAiForecast(snapshot.lottery, config.id, report.targetPeriod)) {
                        \"本目标期已有冻结结果，未重复调用计费接口\"
                    }
                    val forecast = remoteAiAnalyzer.analyze(config, snapshot, report)
                    require(aiGeneration.get() == token && !Thread.currentThread().isInterrupted) {
                        \"数据已经刷新，本次 AI 结果已作废\"
                    }
                    val targetCheck = api.verifyTargetPeriodOpen(snapshot.lottery, report.targetPeriod)
                    require(targetCheck.open) { targetCheck.message }
                    require(!database.hasDraw(snapshot.lottery, report.targetPeriod)) {
                        \"目标期已经开奖，AI 结果未写入前向档案\"
                    }
                    require(isBeforeForecastDeadline(snapshot)) {
                        \"AI 在目标期开奖时间后返回，结果未写入前向档案\"
                    }
                    val locked = database.lockAiForecast(snapshot.lottery, report, forecast)""",
    "fresh AI freeze guard",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """                        if (
                            consensus != null &&
                            !database.hasDraw(snapshot.lottery, report.targetPeriod) &&
                            isBeforeForecastDeadline(snapshot)
                        ) {
                            database.lockAiConsensus(snapshot.lottery, report, consensus)
                        }""",
    """                        val targetCheck = api.verifyTargetPeriodOpen(
                            snapshot.lottery,
                            report.targetPeriod,
                        )
                        if (
                            consensus != null &&
                            targetCheck.open &&
                            !database.hasDraw(snapshot.lottery, report.targetPeriod) &&
                            isBeforeForecastDeadline(snapshot)
                        ) {
                            database.lockAiConsensus(snapshot.lottery, report, consensus)
                        }""",
    "fresh consensus guard",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """        remoteAiAnalyzer.cancelActiveRequests()
        executor.shutdownNow()
        aiExecutor.shutdownNow()
        database.close()""",
    """        remoteAiAnalyzer.cancelActiveRequests()
        executor.shutdownNow()
        aiTasks.close()
        database.close()""",
    "controller close",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """        val computed = reportCache[lottery]
            ?.takeIf {
                it.trainedThroughPeriod == modelHistory.last().period &&
                    it.historySize == modelHistory.size
            }
            ?.copy(targetPeriod = snapshot.nextPeriod)
            ?: NativeEnsemblePredictor.predict(modelHistory)
                .copy(targetPeriod = snapshot.nextPeriod)
                .also { reportCache[lottery] = it }""",
    """        val historyFingerprint = HistoryFingerprint.of(modelHistory)
        val computed = reportCache[lottery]
            ?.takeIf { cached -> cached.historyFingerprint == historyFingerprint }
            ?.report
            ?.copy(targetPeriod = snapshot.nextPeriod)
            ?: NativeEnsemblePredictor.predict(
                historyInput = modelHistory,
                historyTarget = lottery.historyTarget,
            )
                .copy(targetPeriod = snapshot.nextPeriod)
                .also { reportCache[lottery] = CachedForecast(historyFingerprint, it) }""",
    "fingerprinted report cache",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """    private fun desiredHistoryTarget(lottery: LotteryType): Int = when (lottery) {
        LotteryType.AZXY10 -> 3_000
        LotteryType.XYFT -> 2_000
    }""",
    """    private fun desiredHistoryTarget(lottery: LotteryType): Int = lottery.historyTarget""",
    "history target helper",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt",
    """    private data class AnalysisPreparation(""",
    """    private data class CachedForecast(
        val historyFingerprint: String,
        val report: ForecastReport,
    )

    private data class AnalysisPreparation(""",
    "cached forecast data class",
)

# UI accuracy and accessibility.
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt",
    "val fixedDensity = remember(density.density) { Density(density.density, 1.06f) }",
    "val fixedDensity = remember(density.density, density.fontScale) { Density(density.density, density.fontScale) }",
    "system font scale",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt",
    "val delays = listOf(1_500L, 2_500L, 4_000L, 6_000L, 10_000L, 15_000L)",
    "val delays = listOf(2_000L, 3_000L, 5_000L, 8_000L, 13_000L, 20_000L, 30_000L, 45_000L, 60_000L)",
    "post draw polling",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt",
    "delay(250)\n        }",
    "delay(1_000L)\n        }",
    "countdown cadence",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt",
    'if (report.displayUsesShadow) "影子集成六码" else "认证集成六码"',
    """when {
                        report.mode == EvidenceMode.CERTIFIED -> \"认证集成六码\"
                        report.displayUsesShadow -> \"影子实验六码\"
                        else -> \"观察实验六码\"
                    }""",
    "forecast tier label",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt",
    """private fun AiProbabilityComparison(results: List<com.tianji.probabilitylab.nativev4.ai.AiForecast>) {
    val colors = LocalTianjiColors.current
    Column(""",
    """private fun AiProbabilityComparison(results: List<com.tianji.probabilitylab.nativev4.ai.AiForecast>) {
    val colors = LocalTianjiColors.current
    val horizontalScroll = rememberScrollState()
    Column(""",
    "shared probability scroll",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt",
    "Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {\n            Spacer(Modifier.width(38.dp))",
    "Row(Modifier.fillMaxWidth().horizontalScroll(horizontalScroll)) {\n            Spacer(Modifier.width(38.dp))",
    "probability header scroll",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt",
    "Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(vertical = 3.dp)",
    "Modifier.fillMaxWidth().horizontalScroll(horizontalScroll).padding(vertical = 3.dp)",
    "probability row scroll",
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt",
    "progress = { (probability * 5.0).toFloat().coerceIn(0f, 1f) },",
    "progress = { probability.toFloat().coerceIn(0f, 1f) },",
    "probability progress scale",
)

# Tests.
write(
    "app/src/test/java/com/tianji/probabilitylab/nativev4/data/DrawMergePolicyTest.kt",
    """package com.tianji.probabilitylab.nativev4.data

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Test

class DrawMergePolicyTest {
    @Test(expected = IllegalArgumentException::class)
    fun conflictingSamePeriodIsRejected() {
        DrawMergePolicy.merge(
            listOf(
                Draw(LotteryType.AZXY10, "100", (1..10).toList()),
                Draw(LotteryType.AZXY10, "100", (2..10).toList() + 1),
            ),
        )
    }

    @Test
    fun identicalDuplicateIsDeduplicated() {
        val draw = Draw(LotteryType.AZXY10, "100", (1..10).toList())
        assertEquals(1, DrawMergePolicy.merge(listOf(draw, draw.copy(source = "latest"))).size)
    }
}
""",
)
write(
    "app/src/test/java/com/tianji/probabilitylab/nativev4/data/TargetPeriodGuardTest.kt",
    """package com.tianji.probabilitylab.nativev4.data

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TargetPeriodGuardTest {
    @Test
    fun targetRemainsOpenBeforeSafetyWindow() {
        assertTrue(
            TargetPeriodGuard.evaluate("101", "100", "101", 10_000L, 20_000L).open,
        )
    }

    @Test
    fun alreadyDrawnTargetIsRejected() {
        assertFalse(
            TargetPeriodGuard.evaluate("101", "101", "102", 20_000L, 30_000L).open,
        )
    }

    @Test
    fun safetyWindowRejectsLateResult() {
        assertFalse(
            TargetPeriodGuard.evaluate("101", "100", "101", 16_000L, 20_000L, 5_000L).open,
        )
    }
}
""",
)
write(
    "app/src/test/java/com/tianji/probabilitylab/nativev4/domain/HistoryFingerprintTest.kt",
    """package com.tianji.probabilitylab.nativev4.domain

import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class HistoryFingerprintTest {
    private val draw = Draw(LotteryType.AZXY10, "100", (1..10).toList(), "2026-08-03 00:00:00")

    @Test
    fun sameHistoryHasStableFingerprint() {
        assertEquals(HistoryFingerprint.of(listOf(draw)), HistoryFingerprint.of(listOf(draw)))
    }

    @Test
    fun correctedMiddleContentInvalidatesCache() {
        assertNotEquals(
            HistoryFingerprint.of(listOf(draw)),
            HistoryFingerprint.of(listOf(draw.copy(numbers = (2..10).toList() + 1))),
        )
    }
}
""",
)

# Generic CI and release workflow.
write(
    ".github/workflows/android-ci.yml",
    """name: Tianji Android CI

on:
  push:
    branches: [main, 'feature/**']
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - uses: android-actions/setup-android@v3
      - uses: gradle/actions/setup-gradle@v4
        with:
          gradle-version: '8.13'
      - name: Install Android SDK 36
        run: |
          yes | sdkmanager --licenses >/dev/null || true
          sdkmanager 'platforms;android-36' 'build-tools;36.0.0'
      - name: Test, lint and build
        run: gradle --no-daemon --stacktrace :app:testDebugUnitTest :app:testReleaseUnitTest :app:lintDebug :app:assembleDebug :app:assembleRelease
      - uses: actions/upload-artifact@v4
        with:
          name: Tianji-debug-APK
          path: app/build/outputs/apk/debug/app-debug.apk
          if-no-files-found: error
          retention-days: 14
""",
)
write(
    ".github/workflows/release.yml",
    """name: Tianji Release

on:
  push:
    tags: ['v*']
  workflow_dispatch:

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    environment: release
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - uses: android-actions/setup-android@v3
      - uses: gradle/actions/setup-gradle@v4
        with:
          gradle-version: '8.13'
      - name: Install Android SDK 36
        run: |
          yes | sdkmanager --licenses >/dev/null || true
          sdkmanager 'platforms;android-36' 'build-tools;36.0.0'
      - name: Restore signing key from secrets
        env:
          TIANJI_KEYSTORE_BASE64: ${{ secrets.TIANJI_KEYSTORE_BASE64 }}
        run: |
          set -euo pipefail
          test -n "$TIANJI_KEYSTORE_BASE64"
          mkdir -p .signing
          printf '%s' "$TIANJI_KEYSTORE_BASE64" | base64 --decode > .signing/tianji-release.jks
      - name: Verify tag, test and build
        env:
          TIANJI_KEYSTORE_FILE: ${{ github.workspace }}/.signing/tianji-release.jks
          TIANJI_KEYSTORE_PASSWORD: ${{ secrets.TIANJI_KEYSTORE_PASSWORD }}
          TIANJI_KEY_ALIAS: ${{ secrets.TIANJI_KEY_ALIAS }}
          TIANJI_KEY_PASSWORD: ${{ secrets.TIANJI_KEY_PASSWORD }}
        run: |
          set -euo pipefail
          VERSION=$(sed -n 's/.*versionName = "\([^"]*\)".*/\1/p' app/build.gradle.kts | head -n1)
          test "v$VERSION" = "${GITHUB_REF_NAME}"
          gradle --no-daemon --stacktrace :app:testReleaseUnitTest :app:lintRelease :app:assembleRelease
          mkdir -p dist
          cp app/build/outputs/apk/release/app-release.apk "dist/Tianji-${GITHUB_REF_NAME}-release.apk"
          "$ANDROID_SDK_ROOT/build-tools/36.0.0/apksigner" verify --verbose --print-certs "dist/Tianji-${GITHUB_REF_NAME}-release.apk" > dist/APK_VERIFY.txt
          sha256sum "dist/Tianji-${GITHUB_REF_NAME}-release.apk" > "dist/Tianji-${GITHUB_REF_NAME}-SHA256.txt"
      - name: Publish release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          NOTES="RELEASE_NOTES_${GITHUB_REF_NAME}.md"
          if [ ! -f "$NOTES" ]; then NOTES="README.md"; fi
          gh release create "$GITHUB_REF_NAME" --verify-tag --title "天机 $GITHUB_REF_NAME" --notes-file "$NOTES" dist/*
""",
)
write(
    "RELEASE_NOTES_v5.5.0.md",
    """# 天机 v5.5.0 稳定重构版

- 真正取消运行中和排队中的 AI 任务，避免刷新、切换彩种后继续产生无效调用。
- AI 返回后重新核验最新开奖、目标期与服务器截止时间，跨期开奖结果不进入前向档案。
- 强制同步后再次检查已有冻结记录，避免目标期变化造成重复计费。
- 新增同期冲突检测、历史内容指纹缓存和按彩种区分的数据充分度。
- 拆分任务注册、开奖合并、目标期守卫和历史指纹组件并补充单元测试。
- 修正观察模式文案、概率条比例、字体缩放与开奖后轮询。
- 统一 CI 和标签发布流程，签名材料只从 GitHub Environment Secrets 恢复。
""",
)

# Remove old one-off release and patch workflows.
for old in [
    ".github/workflows/apply-tianji-v5.4.6-hotfix.yml",
    ".github/workflows/build-release-tianji-v5.4.6.yml",
    ".github/workflows/publish-v5.4.5-and-clean-branches.yml",
    ".github/workflows/publish-v5.4.6-delete-v5.4.5.yml",
    ".github/workflows/tianji-v5.4.7-deepseek-output-fix.yml",
    "scripts/apply_v5_4_7_fix.py",
]:
    Path(old).unlink(missing_ok=True)

print("Applied Tianji v5.5.0 stability and architecture refactor")
