package com.tianji.probabilitylab.nativev4

import android.content.Context
import android.os.Handler
import android.os.Looper
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.edit
import com.tianji.probabilitylab.nativev4.ai.AiAnalysisMode
import com.tianji.probabilitylab.nativev4.ai.AiConfig
import com.tianji.probabilitylab.nativev4.ai.AiConnectionState
import com.tianji.probabilitylab.nativev4.ai.AiErrorMessages
import com.tianji.probabilitylab.nativev4.ai.AiConversationStage
import com.tianji.probabilitylab.nativev4.ai.AiConversationTimeline
import com.tianji.probabilitylab.nativev4.ai.AiConsensusAudit
import com.tianji.probabilitylab.nativev4.ai.AiConsensusEngine
import com.tianji.probabilitylab.nativev4.ai.AiConsensusRecord
import com.tianji.probabilitylab.nativev4.ai.AiForecast
import com.tianji.probabilitylab.nativev4.ai.AiForecastRecord
import com.tianji.probabilitylab.nativev4.ai.AiLiveAudit
import com.tianji.probabilitylab.nativev4.ai.AiProfileAudit
import com.tianji.probabilitylab.nativev4.ai.AiReasoningEngine
import com.tianji.probabilitylab.nativev4.ai.AiReasoningMode
import com.tianji.probabilitylab.nativev4.ai.AiReasoningState
import com.tianji.probabilitylab.nativev4.ai.AiRunStatus
import com.tianji.probabilitylab.nativev4.ai.AiTaskRegistry
import com.tianji.probabilitylab.nativev4.ai.NativeEnsemblePredictor
import com.tianji.probabilitylab.nativev4.ai.RemoteAiAnalyzer
import com.tianji.probabilitylab.nativev4.ai.SecureAiConfigStore
import com.tianji.probabilitylab.nativev4.data.AppDatabase
import com.tianji.probabilitylab.nativev4.data.ArchiveIntegrity
import com.tianji.probabilitylab.nativev4.data.HistoryIntegrity
import com.tianji.probabilitylab.nativev4.data.LotteryApi
import com.tianji.probabilitylab.nativev4.data.hasAiForecast
import com.tianji.probabilitylab.nativev4.domain.HistoryFingerprint
import com.tianji.probabilitylab.nativev4.model.ApiTimeParser
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.EvidenceMode
import com.tianji.probabilitylab.nativev4.model.ForecastDeadlineResolver
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.model.LiveAudit
import com.tianji.probabilitylab.nativev4.model.LockedForecast
import com.tianji.probabilitylab.nativev4.model.LotteryType
import com.tianji.probabilitylab.nativev4.model.SourceHealth
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

data class AppUiState(
    val lottery: LotteryType = LotteryType.AZXY10,
    val snapshot: DrawSnapshot? = null,
    val report: ForecastReport? = null,
    val records: List<LockedForecast> = emptyList(),
    val liveAudit: LiveAudit = LiveAudit(0, 0, 0),
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    val aiForecasts: List<AiForecast> = emptyList(),
    val aiRecords: List<AiForecastRecord> = emptyList(),
    val aiLiveAudit: AiLiveAudit = AiLiveAudit(),
    val aiProfileAudits: List<AiProfileAudit> = emptyList(),
    val aiConsensusRecords: List<AiConsensusRecord> = emptyList(),
    val aiConsensusAudit: AiConsensusAudit = AiConsensusAudit(),
    val archiveIntegrity: ArchiveIntegrity = ArchiveIntegrity(),
    val aiStatuses: Map<String, AiRunStatus> = emptyMap(),
    val aiError: String? = null,
    val aiConcurrency: Int = 3,
) {
    val isAiAnalyzing: Boolean
        get() = aiStatuses.values.any {
            it.state == AiConnectionState.ANALYZING || it.state == AiConnectionState.TESTING
        }
}

class AppController(context: Context) {
    private val appContext = context.applicationContext
    private val database = AppDatabase(appContext)
    private val api = LotteryApi()
    private val executor = Executors.newSingleThreadExecutor()
    private val preferences = appContext.getSharedPreferences("tianji-native-v5", Context.MODE_PRIVATE)
    private val initialAiConcurrency = preferences.getInt("ai_concurrency", 3).coerceIn(1, 3)
    private val aiExecutor = ThreadPoolExecutor(
        initialAiConcurrency,
        initialAiConcurrency,
        60L,
        TimeUnit.SECONDS,
        LinkedBlockingQueue(),
    )
    private val aiTasks = AiTaskRegistry(aiExecutor)
    private val mainHandler = Handler(Looper.getMainLooper())
    private val generation = AtomicInteger(0)
    private val aiGeneration = AtomicInteger(0)
    private val verifiedHistoryReady = mutableSetOf<LotteryType>()
    private val reportCache = mutableMapOf<LotteryType, CachedForecast>()
    private val aiConfigStore = SecureAiConfigStore(appContext)
    private val remoteAiAnalyzer = RemoteAiAnalyzer()

    var state by mutableStateOf(
        AppUiState(lottery = savedLottery(), aiConcurrency = initialAiConcurrency),
    )
        private set

    var aiConfigs by mutableStateOf(aiConfigStore.loadAll())
        private set

    var aiAvailableModels by mutableStateOf<Map<String, List<String>>>(emptyMap())
        private set

    init {
        refresh()
        aiConfigs.filter { it.canQueryModels }.forEach { loadAiModels(it.id) }
    }

    fun selectLottery(lottery: LotteryType) {
        if (lottery == state.lottery) return
        preferences.edit { putString("lottery", lottery.apiKey) }
        state = AppUiState(lottery = lottery, aiConcurrency = state.aiConcurrency)
        refresh()
    }

    fun refresh() {
        // Refreshing draw data must not disconnect a paid AI request. Every AI task already owns
        // a frozen snapshot and is validated against its exact target period before archiving.
        api.cancelActiveRequests()
        val token = generation.incrementAndGet()
        val lottery = state.lottery
        state = state.copy(
            isLoading = state.snapshot == null,
            isRefreshing = state.snapshot != null,
            error = null,
        )
        executor.execute {
            val result = runCatching { load(lottery) }
            mainHandler.post {
                if (generation.get() != token || state.lottery != lottery) return@post
                state = result.fold(
                    onSuccess = { loaded ->
                        val preservedAi = if (state.report?.targetPeriod == loaded.report?.targetPeriod) {
                            state.aiForecasts
                        } else {
                            emptyList()
                        }
                        loaded.copy(
                            aiForecasts = (preservedAi + loaded.aiForecasts).distinctBy { it.profileId },
                            aiStatuses = state.aiStatuses,
                            aiError = state.aiError,
                        )
                    },
                    onFailure = {
                        state.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = it.message ?: "数据加载失败",
                        )
                    },
                )
            }
        }
    }

    fun saveAiConfig(config: AiConfig) {
        val normalized = config.copy(
            id = config.id.ifBlank { UUID.randomUUID().toString() },
            name = config.name.trim(),
            endpoint = config.endpoint.trim(),
            model = config.model.trim(),
            apiKey = config.apiKey.trim(),
        )
        aiConfigs = if (aiConfigs.any { it.id == normalized.id }) {
            aiConfigs.map { if (it.id == normalized.id) normalized else it }
        } else {
            aiConfigs + normalized
        }
        aiConfigStore.saveAll(aiConfigs)
        state = state.copy(
            aiError = null,
            aiStatuses = state.aiStatuses + (
                normalized.id to AiRunStatus(normalized.id, message = "配置已保存，尚未测试")
            ),
        )
        if (normalized.canQueryModels && normalized.id !in aiAvailableModels) {
            loadAiModels(normalized.id)
        }
    }

    fun deleteAiConfig(profileId: String) {
        aiTasks.cancel(profileId)
        remoteAiAnalyzer.cancelActiveRequests(profileId)
        aiConfigs = aiConfigs.filterNot { it.id == profileId }
        aiAvailableModels = aiAvailableModels - profileId
        aiConfigStore.saveAll(aiConfigs)
        state = state.copy(aiStatuses = state.aiStatuses - profileId)
    }

    fun loadAiModels(profileId: String) {
        val config = aiConfigs.firstOrNull { it.id == profileId } ?: return
        state = state.copy(
            aiStatuses = state.aiStatuses + (
                profileId to AiRunStatus(profileId, AiConnectionState.TESTING, "正在读取真实模型列表…")
            ),
        )
        aiTasks.submit(profileId) {
            val result = runCatching { remoteAiAnalyzer.listModels(config) }
            mainHandler.post {
                if (aiConfigs.none { it.id == profileId }) return@post
                if (state.aiStatuses[profileId]?.state != AiConnectionState.TESTING) return@post
                result.fold(
                    onSuccess = { catalog ->
                        aiAvailableModels = aiAvailableModels + (profileId to catalog.models)
                        state = state.copy(
                            aiStatuses = state.aiStatuses + (
                                profileId to AiRunStatus(
                                    profileId = profileId,
                                    state = AiConnectionState.CONNECTED,
                                    message = "已读取 ${catalog.models.size} 个可用模型",
                                    latencyMs = catalog.latencyMs,
                                    checkedAtEpochMs = System.currentTimeMillis(),
                                )
                            ),
                        )
                    },
                    onFailure = {
                        state = state.copy(
                            aiStatuses = state.aiStatuses + (
                                profileId to AiRunStatus(
                                    profileId = profileId,
                                    state = AiConnectionState.FAILED,
                                    message = AiErrorMessages.userFacing(it, "读取模型列表失败"),
                                    checkedAtEpochMs = System.currentTimeMillis(),
                                )
                            ),
                        )
                    },
                )
            }
        }
    }

    fun selectAiModel(profileId: String, model: String) {
        val config = aiConfigs.firstOrNull { it.id == profileId } ?: return
        saveAiConfig(config.copy(model = model))
    }

    fun selectAiAnalysisMode(profileId: String, mode: AiAnalysisMode) {
        val config = aiConfigs.firstOrNull { it.id == profileId } ?: return
        if (config.analysisMode == mode) return
        saveAiConfig(config.copy(analysisMode = mode))
    }

    fun selectAiReasoningMode(profileId: String, mode: AiReasoningMode) {
        val config = aiConfigs.firstOrNull { it.id == profileId } ?: return
        if (config.reasoningMode == mode) return
        saveAiConfig(config.copy(reasoningMode = mode))
    }

    fun setAiConcurrency(value: Int) {
        val normalized = value.coerceIn(1, 3)
        if (normalized == state.aiConcurrency) return
        if (normalized > aiExecutor.maximumPoolSize) {
            aiExecutor.maximumPoolSize = normalized
            aiExecutor.corePoolSize = normalized
        } else {
            aiExecutor.corePoolSize = normalized
            aiExecutor.maximumPoolSize = normalized
        }
        preferences.edit { putInt("ai_concurrency", normalized) }
        state = state.copy(aiConcurrency = normalized)
    }

    fun cancelAi(profileId: String) {
        aiTasks.cancel(profileId)
        remoteAiAnalyzer.cancelActiveRequests(profileId)
        val current = state.aiStatuses[profileId] ?: AiRunStatus(profileId)
        state = state.copy(
            aiStatuses = state.aiStatuses + (
                profileId to current.copy(
                    state = AiConnectionState.CANCELLED,
                    message = "已取消本次请求",
                    checkedAtEpochMs = System.currentTimeMillis(),
                    timeline = AiConversationTimeline.merge(
                        current.timeline,
                        AiConversationTimeline.event(
                            AiConversationStage.CANCELLED,
                            "用户取消了当前请求",
                        ),
                    ),
                )
            ),
        )
    }

    fun testAiConnection(profileId: String) {
        val config = aiConfigs.firstOrNull { it.id == profileId } ?: return
        if (!config.isComplete) {
            state = state.copy(
                aiStatuses = state.aiStatuses + (
                    profileId to AiRunStatus(profileId, AiConnectionState.FAILED, "配置不完整")
                ),
            )
            return
        }
        state = state.copy(
            aiStatuses = state.aiStatuses + (
                profileId to AiRunStatus(profileId, AiConnectionState.TESTING, "正在测试真实接口…")
            ),
        )
        aiTasks.submit(profileId) {
            val result = runCatching { remoteAiAnalyzer.testConnection(config) }
            mainHandler.post {
                if (aiConfigs.none { it.id == profileId }) return@post
                if (state.aiStatuses[profileId]?.state != AiConnectionState.TESTING) return@post
                val status = result.fold(
                    onSuccess = {
                        aiConfigs = aiConfigs.map { current ->
                            if (current.id == profileId) current.copy(capability = it.capability) else current
                        }
                        aiConfigStore.saveAll(aiConfigs)
                        AiRunStatus(
                            profileId = profileId,
                            state = AiConnectionState.CONNECTED,
                            message = it.capability.message,
                            latencyMs = it.latencyMs,
                            checkedAtEpochMs = System.currentTimeMillis(),
                        )
                    },
                    onFailure = {
                        AiRunStatus(
                            profileId = profileId,
                            state = AiConnectionState.FAILED,
                            message = AiErrorMessages.userFacing(it, "连接失败"),
                            checkedAtEpochMs = System.currentTimeMillis(),
                        )
                    },
                )
                state = state.copy(aiStatuses = state.aiStatuses + (profileId to status))
            }
        }
    }

    fun analyzeWithAi(profileId: String? = null) {
        val runningIds = state.aiStatuses.filterValues {
            it.state == AiConnectionState.ANALYZING || it.state == AiConnectionState.TESTING
        }.keys
        if (profileId != null && profileId in runningIds) {
            state = state.copy(aiError = "该 AI 仍在后台运行，请等待完成或先手动取消")
            return
        }
        val requested = aiConfigs.filter {
            it.isComplete && (profileId == null || it.id == profileId) && it.id !in runningIds
        }
        if (requested.isEmpty()) {
            state = state.copy(aiError = "请先在数据页保存至少一个完整的 AI 配置")
            return
        }
        val targetPeriod = state.report?.targetPeriod
        val configs = requested.filterNot { config ->
            targetPeriod != null && state.aiRecords.any {
                it.profileId == config.id && it.targetPeriod == targetPeriod
            }
        }
        val alreadyFrozen = requested - configs.toSet()
        if (alreadyFrozen.isNotEmpty()) {
            state = state.copy(
                aiStatuses = state.aiStatuses + alreadyFrozen.associate { config ->
                    config.id to AiRunStatus(
                        config.id,
                        AiConnectionState.CONNECTED,
                        "本目标期已有首次冻结结果，未重复调用计费接口",
                    )
                },
            )
        }
        if (configs.isEmpty()) return
        val lottery = state.lottery
        val token = aiGeneration.incrementAndGet()
        val syncingStatuses = configs.associate { config ->
            val message = "正在从开奖接口强制同步最新历史…"
            config.id to AiRunStatus(
                profileId = config.id,
                state = AiConnectionState.ANALYZING,
                message = message,
                timeline = listOf(
                    AiConversationTimeline.event(AiConversationStage.PREPARING, message),
                ),
            )
        }
        state = state.copy(
            aiError = null,
            aiStatuses = state.aiStatuses + syncingStatuses,
        )

        executor.execute {
            val prepared = runCatching {
                val freshSnapshot = api.fetchSnapshot(lottery, days = 2)
                val required = configs.maxOf { it.analysisMode.historyLimit }
                val integrity = HistoryIntegrity.inspect(
                    lottery = lottery,
                    historyInput = freshSnapshot.history,
                    latestPeriod = freshSnapshot.latest.period,
                    minimumHistory = required,
                )
                require(integrity.valid) { integrity.message }
                val loadedState = load(lottery, onlineOverride = freshSnapshot)
                val verifiedSnapshot = loadedState.snapshot
                    ?: error("接口历史同步后未生成有效快照")
                AnalysisPreparation(
                    apiSnapshot = verifiedSnapshot,
                    loadedState = loadedState,
                )
            }
            mainHandler.post {
                if (state.lottery != lottery) return@post
                prepared.fold(
                    onSuccess = { preparation ->
                        val report = preparation.loadedState.report
                        if (report == null) {
                            markAiPreparationFailed(configs, "本地模型未完成，未调用 AI")
                            return@fold
                        }
                        val eligibleConfigs = configs.filterNot { config ->
                            database.hasAiForecast(lottery, config.id, report.targetPeriod)
                        }
                        val skippedConfigs = configs - eligibleConfigs.toSet()
                        val skippedStatuses = skippedConfigs.associate { config ->
                            config.id to AiRunStatus(
                                config.id,
                                AiConnectionState.CONNECTED,
                                "同步后发现本目标期已有冻结结果，未调用计费接口",
                            )
                        }
                        val runningStatuses = eligibleConfigs.associate { config ->
                            val reasoning = AiReasoningEngine.resolveForecast(config).displayLabel
                            val message = "接口历史已同步，准备${config.analysisMode.label} · $reasoning"
                            val current = state.aiStatuses[config.id] ?: AiRunStatus(config.id)
                            config.id to current.copy(
                                state = AiConnectionState.ANALYZING,
                                message = message,
                                timeline = AiConversationTimeline.merge(
                                    current.timeline,
                                    AiConversationTimeline.event(AiConversationStage.REQUEST, message),
                                ),
                            )
                        }
                        state = preparation.loadedState.copy(
                            aiError = null,
                            aiStatuses = state.aiStatuses + skippedStatuses + runningStatuses,
                            aiForecasts = state.aiForecasts,
                        )
                        if (eligibleConfigs.isNotEmpty()) {
                            launchAiRequests(eligibleConfigs, preparation.apiSnapshot, report, token)
                        }
                    },
                    onFailure = {
                        markAiPreparationFailed(
                            configs,
                            "开奖接口同步失败，未调用 AI：${it.message ?: "未知错误"}",
                        )
                    },
                )
            }
        }
    }

    private fun launchAiRequests(
        configs: List<AiConfig>,
        snapshot: DrawSnapshot,
        report: ForecastReport,
        token: Int,
    ) {
        val remaining = AtomicInteger(configs.size)
        configs.forEach { config ->
            aiTasks.submit(config.id) {
                val result = runCatching {
                    require(!Thread.currentThread().isInterrupted) {
                        "请求已在发送前取消"
                    }
                    require(state.aiStatuses[config.id]?.state != AiConnectionState.CANCELLED) {
                        "请求已在发送前取消"
                    }
                    require(!database.hasAiForecast(snapshot.lottery, config.id, report.targetPeriod)) {
                        "本目标期已有冻结结果，未重复调用计费接口"
                    }
                    val forecast = remoteAiAnalyzer.analyze(config, snapshot, report) { message, elapsedMs ->
                        mainHandler.post {
                            if (
                                state.report?.targetPeriod == report.targetPeriod &&
                                state.aiStatuses[config.id]?.state == AiConnectionState.ANALYZING
                            ) {
                                val current = state.aiStatuses[config.id] ?: AiRunStatus(config.id)
                                val event = AiConversationTimeline.event(
                                    stage = AiConversationTimeline.classify(message),
                                    message = message,
                                    elapsedMs = elapsedMs,
                                )
                                state = state.copy(
                                    aiStatuses = state.aiStatuses + (
                                        config.id to current.copy(
                                            state = AiConnectionState.ANALYZING,
                                            message = "$message · ${elapsedMs / 1_000}s",
                                            checkedAtEpochMs = System.currentTimeMillis(),
                                            timeline = AiConversationTimeline.merge(current.timeline, event),
                                        )
                                    ),
                                )
                            }
                        }
                    }
                    require(!Thread.currentThread().isInterrupted) {
                        "数据已经刷新，本次 AI 结果已作废"
                    }
                    val targetCheck = api.verifyTargetPeriodOpen(snapshot.lottery, report.targetPeriod)
                    require(targetCheck.open) { targetCheck.message }
                    require(!database.hasDraw(snapshot.lottery, report.targetPeriod)) {
                        "目标期已经开奖，AI 结果未写入前向档案"
                    }
                    require(isBeforeForecastDeadline(snapshot)) {
                        "AI 在目标期开奖时间后返回，结果未写入前向档案"
                    }
                    val locked = database.lockAiForecast(snapshot.lottery, report, forecast)
                    AiAnalysisCompletion(
                        forecast = locked.record.toForecast(),
                        inserted = locked.inserted,
                        records = database.loadAiForecasts(snapshot.lottery),
                        audit = database.loadAiLiveAudit(snapshot.lottery),
                        profileAudits = database.loadAiProfileAudits(snapshot.lottery),
                    )
                }
                val batch = if (remaining.decrementAndGet() == 0) {
                    runCatching {
                        val current = database.loadAiForecasts(snapshot.lottery, 200)
                            .filter { it.targetPeriod == report.targetPeriod }
                        val consensus = AiConsensusEngine.fromRecords(
                            current,
                            database.loadAiProfileAudits(snapshot.lottery),
                        )
                        val targetCheck = api.verifyTargetPeriodOpen(
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
                        }
                        AiBatchCompletion(
                            consensusRecords = database.loadAiConsensusRecords(snapshot.lottery),
                            consensusAudit = database.loadAiConsensusAudit(snapshot.lottery),
                            archiveIntegrity = database.verifyArchiveIntegrity(snapshot.lottery),
                        )
                    }.getOrNull()
                } else {
                    null
                }
                mainHandler.post {
                    if (state.report?.targetPeriod != report.targetPeriod) {
                        return@post
                    }
                    result.fold(
                        onSuccess = { completed ->
                            if (state.aiStatuses[config.id]?.state == AiConnectionState.CANCELLED) {
                                return@fold
                            }
                            val forecast = completed.forecast
                            state = state.copy(
                                aiForecasts = (
                                    state.aiForecasts.filterNot { it.profileId == config.id } + forecast
                                    ).sortedBy { item ->
                                    aiConfigs.indexOfFirst { it.id == item.profileId }
                                },
                                aiRecords = completed.records,
                                aiLiveAudit = completed.audit,
                                aiProfileAudits = completed.profileAudits,
                                aiStatuses = state.aiStatuses + (
                                    config.id to run {
                                        val current = state.aiStatuses[config.id] ?: AiRunStatus(config.id)
                                        val successMessage = when {
                                            !completed.inserted -> "本期已有冻结预测，保留首次结果"
                                            forecast.reasoningState == AiReasoningState.FALLBACK ->
                                                "${forecast.executionNote} · 已冻结协议兼容结果"
                                            forecast.reasoningState == AiReasoningState.VERIFIED ->
                                                forecast.reasoningTokens?.let { "已冻结 · 推理 $it tokens" }
                                                    ?: "已冻结 · 推理状态已验证"
                                            forecast.responseId.isBlank() -> "已接入并冻结预测"
                                            else -> "已冻结 · 响应 ${forecast.responseId.takeLast(10)}"
                                        }
                                        current.copy(
                                            state = AiConnectionState.CONNECTED,
                                            message = successMessage,
                                            latencyMs = forecast.latencyMs,
                                            checkedAtEpochMs = forecast.createdAtEpochMs,
                                            timeline = AiConversationTimeline.merge(
                                                current.timeline,
                                                AiConversationTimeline.event(
                                                    AiConversationStage.SUCCESS,
                                                    successMessage,
                                                    forecast.latencyMs,
                                                ),
                                            ),
                                        )
                                    }
                                ),
                            )
                        },
                        onFailure = {
                            if (state.aiStatuses[config.id]?.state == AiConnectionState.CANCELLED) {
                                return@fold
                            }
                            state = state.copy(
                                aiStatuses = state.aiStatuses + (
                                    config.id to run {
                                        val current = state.aiStatuses[config.id] ?: AiRunStatus(config.id)
                                        val failureMessage = AiErrorMessages.userFacing(it, "AI 分析失败")
                                        current.copy(
                                            state = AiConnectionState.FAILED,
                                            message = failureMessage,
                                            checkedAtEpochMs = System.currentTimeMillis(),
                                            timeline = AiConversationTimeline.merge(
                                                current.timeline,
                                                AiConversationTimeline.event(
                                                    AiConversationStage.ERROR,
                                                    failureMessage,
                                                ),
                                            ),
                                        )
                                    }
                                ),
                            )
                        },
                    )
                    batch?.let { completed ->
                        state = state.copy(
                            aiConsensusRecords = completed.consensusRecords,
                            aiConsensusAudit = completed.consensusAudit,
                            archiveIntegrity = completed.archiveIntegrity,
                        )
                    }
                }
            }
        }
    }

    private fun markAiPreparationFailed(configs: List<AiConfig>, message: String) {
        val failed = configs.associate { config ->
            val current = state.aiStatuses[config.id] ?: AiRunStatus(config.id)
            config.id to current.copy(
                state = AiConnectionState.FAILED,
                message = message,
                checkedAtEpochMs = System.currentTimeMillis(),
                timeline = AiConversationTimeline.merge(
                    current.timeline,
                    AiConversationTimeline.event(AiConversationStage.ERROR, message),
                ),
            )
        }
        state = state.copy(aiError = message, aiStatuses = state.aiStatuses + failed)
    }

    fun close() {
        generation.incrementAndGet()
        aiGeneration.incrementAndGet()
        api.cancelActiveRequests()
        remoteAiAnalyzer.cancelActiveRequests()
        executor.shutdownNow()
        aiTasks.close()
        database.close()
    }

    private fun load(lottery: LotteryType, onlineOverride: DrawSnapshot? = null): AppUiState {
        var online: DrawSnapshot? = onlineOverride
        val shortRefresh = onlineOverride == null && lottery in verifiedHistoryReady
        val networkFailure = if (onlineOverride == null) {
            runCatching {
                api.fetchSnapshot(lottery, days = if (shortRefresh) 2 else 14).also {
                    online = it
                    database.saveDraws(it.history)
                    rememberSuccessfulSync(it)
                }
            }.exceptionOrNull()
        } else {
            database.saveDraws(onlineOverride.history)
            rememberSuccessfulSync(onlineOverride)
            null
        }

        var modelHistory = when {
            online == null -> database.loadDraws(lottery, lottery.historyTarget)
            onlineOverride == null && !shortRefresh -> online!!.history
            else -> database.loadDraws(lottery, lottery.historyTarget)
        }
        var integrity = HistoryIntegrity.inspect(
            lottery = lottery,
            historyInput = modelHistory,
            latestPeriod = online?.latest?.period ?: modelHistory.lastOrNull()?.period.orEmpty(),
            minimumHistory = 180,
        )
        if (
            (onlineOverride != null || shortRefresh) &&
            (!integrity.valid || modelHistory.size < desiredHistoryTarget(lottery))
        ) {
            val fullSnapshot = api.fetchSnapshot(lottery, days = 14)
            database.saveDraws(fullSnapshot.history)
            rememberSuccessfulSync(fullSnapshot)
            online = fullSnapshot
            modelHistory = fullSnapshot.history
            integrity = HistoryIntegrity.inspect(
                lottery = lottery,
                historyInput = modelHistory,
                latestPeriod = fullSnapshot.latest.period,
                minimumHistory = 180,
            )
        }
        if (!integrity.valid) {
            error(
                networkFailure?.let {
                    "网络同步失败且历史校验未通过：${it.message}；${integrity.message}"
                } ?: integrity.message,
            )
        }
        if (online != null && modelHistory.size >= desiredHistoryTarget(lottery)) {
            verifiedHistoryReady += lottery
        }

        val settlementHistory = modelHistory.toMutableList()
        var backfillMessage = ""
        if (online != null) {
            val availablePeriods = settlementHistory.asSequence().map { it.period }.toHashSet()
            val unresolved = database.loadPendingSettlements(lottery)
                .filterNot { it.targetPeriod in availablePeriods }
            if (unresolved.isNotEmpty()) {
                val zone = ZoneId.of("Asia/Shanghai")
                val dates = unresolved.flatMap { pending ->
                    val trainedDate = runCatching {
                        LocalDateTime.parse(
                            pending.trainedThroughDrawTime,
                            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"),
                        ).toLocalDate()
                    }.getOrElse {
                        Instant.ofEpochMilli(pending.createdAtEpochMs).atZone(zone).toLocalDate()
                    }
                    listOf(trainedDate, trainedDate.plusDays(1))
                }.toSet()
                val backfill = api.fetchHistoricalDates(lottery, dates)
                database.saveDraws(backfill.draws)
                settlementHistory += backfill.draws
                val returnedPeriods = backfill.draws.asSequence().map { it.period }.toHashSet()
                val resolvedCount = unresolved.count { it.targetPeriod in returnedPeriods }
                val remainingCount = unresolved.size - resolvedCount
                backfillMessage = if (remainingCount == 0 && backfill.failedDates.isEmpty()) {
                    "；已按目标期结算 $resolvedCount 个旧档案"
                } else {
                    "；旧档案回查 $resolvedCount/${unresolved.size}，其余稍后重试"
                }
            }
        }

        val latest = online?.latest ?: modelHistory.last()
        val snapshot = online?.copy(
            history = modelHistory,
            latest = latest,
            sourceHealth = online!!.sourceHealth.copy(message = integrity.message + backfillMessage),
        ) ?: DrawSnapshot(
            lottery = lottery,
            history = modelHistory,
            latest = latest,
            nextPeriod = "待同步",
            sourceHealth = SourceHealth(
                label = "本机数据库",
                isFresh = false,
                independentSources = 1,
                message = "网络不可用：只读真实历史，不生成假开奖",
                syncedAtEpochMs = preferences.getLong(
                    "last_sync_${lottery.apiKey}",
                    latest.drawTime.toEpochMillisOrNull() ?: System.currentTimeMillis(),
                ),
            ),
        )
        database.settleForecasts(lottery, settlementHistory)
        database.settleAiForecasts(lottery, settlementHistory)
        database.settleAiConsensus(lottery, settlementHistory)

        val historyFingerprint = HistoryFingerprint.of(modelHistory)
        val computed = reportCache[lottery]
            ?.takeIf { cached -> cached.historyFingerprint == historyFingerprint }
            ?.report
            ?.copy(targetPeriod = snapshot.nextPeriod)
            ?: NativeEnsemblePredictor.predict(
                historyInput = modelHistory,
                historyTarget = lottery.historyTarget,
            )
                .copy(targetPeriod = snapshot.nextPeriod)
                .also { reportCache[lottery] = CachedForecast(historyFingerprint, it) }
        val sourceBlocks = buildList {
            if (!snapshot.sourceHealth.isFresh) add("实时数据不可用，保持观察模式")
            if (snapshot.sourceHealth.independentSources < 2) add("独立数据源不足 2 个")
        }
        val report = computed.copy(
            mode = if (computed.mode == EvidenceMode.CERTIFIED && sourceBlocks.isEmpty()) {
                EvidenceMode.CERTIFIED
            } else {
                EvidenceMode.OBSERVE
            },
            blockedReasons = (computed.blockedReasons + sourceBlocks).distinct(),
        )
        if (
            snapshot.sourceHealth.isFresh &&
            report.targetPeriod != "待同步" &&
            !database.hasDraw(lottery, report.targetPeriod)
        ) {
            database.lockForecast(lottery, report)
        }
        val aiRecords = database.loadAiForecasts(lottery)
        return AppUiState(
            lottery = lottery,
            snapshot = snapshot,
            report = report,
            records = database.loadForecasts(lottery),
            liveAudit = database.loadLiveAudit(lottery),
            aiForecasts = aiRecords.filter { it.targetPeriod == report.targetPeriod }.map { it.toForecast() },
            aiRecords = aiRecords,
            aiLiveAudit = database.loadAiLiveAudit(lottery),
            aiProfileAudits = database.loadAiProfileAudits(lottery),
            aiConsensusRecords = database.loadAiConsensusRecords(lottery),
            aiConsensusAudit = database.loadAiConsensusAudit(lottery),
            archiveIntegrity = database.verifyArchiveIntegrity(lottery),
            aiConcurrency = preferences.getInt("ai_concurrency", 3).coerceIn(1, 3),
            isLoading = false,
            isRefreshing = false,
            error = networkFailure?.message,
        )
    }

    private fun savedLottery(): LotteryType {
        val key = preferences.getString("lottery", LotteryType.AZXY10.apiKey)
        return LotteryType.entries.firstOrNull { it.apiKey == key } ?: LotteryType.AZXY10
    }

    private fun desiredHistoryTarget(lottery: LotteryType): Int = lottery.historyTarget

    private fun isBeforeForecastDeadline(snapshot: DrawSnapshot): Boolean =
        ForecastDeadlineResolver.isBeforeDeadline(snapshot)

    private fun rememberSuccessfulSync(snapshot: DrawSnapshot) {
        preferences.edit {
            putLong("last_sync_${snapshot.lottery.apiKey}", snapshot.sourceHealth.syncedAtEpochMs)
        }
    }

    private fun String.toEpochMillisOrNull(): Long? = ApiTimeParser.parseEpochMillis(this)

    private fun AiForecastRecord.toForecast() = AiForecast(
        profileId = profileId,
        profileName = profileName,
        targetPeriod = targetPeriod,
        position = position,
        top6 = top6,
        top7 = top7,
        probabilities = probabilities,
        analysis = analysis,
        riskNote = riskNote,
        selfRating = selfRating,
        model = model,
        analysisMode = analysisMode,
        reasoningMode = reasoningMode,
        reasoningProtocol = reasoningProtocol,
        reasoningState = reasoningState,
        reasoningTokens = reasoningTokens,
        inputTokens = inputTokens,
        outputTokens = outputTokens,
        estimatedCost = estimatedCost,
        executionNote = executionNote,
        createdAtEpochMs = createdAtEpochMs,
        latencyMs = latencyMs,
        responseId = responseId,
    )

    private data class CachedForecast(
        val historyFingerprint: String,
        val report: ForecastReport,
    )

    private data class AnalysisPreparation(
        val apiSnapshot: DrawSnapshot,
        val loadedState: AppUiState,
    )

    private data class AiAnalysisCompletion(
        val forecast: AiForecast,
        val inserted: Boolean,
        val records: List<AiForecastRecord>,
        val audit: AiLiveAudit,
        val profileAudits: List<AiProfileAudit>,
    )

    private data class AiBatchCompletion(
        val consensusRecords: List<AiConsensusRecord>,
        val consensusAudit: AiConsensusAudit,
        val archiveIntegrity: ArchiveIntegrity,
    )
}
