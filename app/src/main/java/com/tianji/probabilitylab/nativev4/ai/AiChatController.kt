package com.tianji.probabilitylab.nativev4.ai

import android.content.Context
import android.os.Handler
import android.os.Looper
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.EOFException
import java.io.IOException
import java.net.HttpURLConnection
import java.net.SocketException
import java.net.SocketTimeoutException
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger
import kotlin.math.abs
import kotlin.math.max

/**
 * Runs free-form questions independently from the official forward forecast archive.
 * Chat replies are never persisted as verified results and never replace first-frozen forecasts.
 */
class AiChatController(context: Context) {
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())
    private val generation = AtomicInteger(0)
    private val client = RemoteAiChatClient()
    private val archiveStore = AiChatArchiveStore(context.applicationContext)
    private val learningStore = AiAdaptiveLearningStore(context.applicationContext)
    private var archiveData = archiveStore.loadAll()

    var session by mutableStateOf(AiChatSession(profileId = ""))
        private set

    var archives by mutableStateOf(archiveData.map(AiChatArchiveCodec::summary))
        private set

    fun settleCandidates(snapshot: DrawSnapshot) {
        val drawsByPeriod = snapshot.history.associateBy(Draw::period)
        archiveData.filter { it.lotteryKey == snapshot.lottery.apiKey }.forEach { archive ->
            archive.candidates.forEach candidateLoop@ { record ->
                val position = record.prediction.position
                val actualNumber = record.actualNumber
                    ?: drawsByPeriod[record.targetPeriod]?.numbers?.getOrNull(position)
                    ?: return@candidateLoop
                learningStore.learnChatCandidate(
                    outcomeId = record.id,
                    lotteryKey = archive.lotteryKey,
                    profileId = archive.profileId,
                    model = AiLearningStrategy.chat(
                        archive.model,
                        archive.personaId,
                        archive.judgementMode,
                    ),
                    position = position,
                    top6 = record.prediction.top6,
                    targetPeriod = record.targetPeriod,
                    actualNumber = actualNumber,
                    draws = snapshot.history,
                )
            }
        }
        val updated = archiveStore.settleCandidates(snapshot.lottery.apiKey, snapshot.history)
        archiveData = updated
        val current = updated.firstOrNull { it.id == session.archiveId }
        if (current != null) {
            session = if (session.isRunning) {
                session.copy(candidates = current.candidates)
            } else {
                current.toSession()
            }
        }
        refreshArchiveSummaries()
    }

    fun selectContext(
        profileId: String,
        profileName: String,
        model: String,
        lotteryKey: String,
        targetPeriod: String?,
        latestPeriod: String? = null,
        latestNumbers: List<Int> = emptyList(),
        announceTargetTransition: Boolean = true,
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
                judgementMode = session.judgementMode,
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
        if (announceTargetTransition) {
            syncTargetTransition(normalizedTarget, latestPeriod, latestNumbers)
        } else if (normalizedTarget.isNotBlank() && session.targetPeriod != normalizedTarget) {
            session = session.copy(targetPeriod = normalizedTarget)
        }
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

    fun selectJudgementMode(mode: AiJudgementMode) {
        if (session.isRunning || session.judgementMode == mode) return
        session = session.copy(
            judgementMode = mode,
            error = null,
            updatedAtEpochMs = System.currentTimeMillis(),
        )
        persistCurrent()
    }

    fun send(
        config: AiConfig,
        snapshot: DrawSnapshot,
        report: ForecastReport,
        question: String,
    ) {
        val text = question.trim()
        if (text.isBlank() || session.isRunning) return
        val intent = AiChatIntentRouter.resolve(text)
        AiChatProtocol.wantsPrediction(if (intent.wantsPrediction) text else "")
        if (intent.wantsPrediction) {
            AiPredictionFreshnessGuard.error(snapshot, report)?.let { message ->
                session = session.copy(
                    error = message,
                    progress = "",
                    updatedAtEpochMs = System.currentTimeMillis(),
                )
                return
            }
        }
        val activeModel = session.model.ifBlank { config.model }.trim()
        if (intent.usesLotteryContext) settleCandidates(snapshot)
        selectContext(
            profileId = config.id,
            profileName = config.displayName,
            model = activeModel,
            lotteryKey = snapshot.lottery.apiKey,
            targetPeriod = report.targetPeriod,
            latestPeriod = snapshot.latest.period,
            latestNumbers = snapshot.latest.numbers,
            announceTargetTransition = intent.usesLotteryContext,
        )
        ensureContextCapacity()
        val activeConfig = config.copy(model = activeModel)
        val plan = AiChatProtocol.planContext(session.messages, session.memorySummary)
        val activePosition = if (intent.usesLotteryContext) {
            AiPositionScope.resolve(text, plan.messages)
        } else {
            null
        }
        val continuity = if (intent.usesLotteryContext) {
            AiConversationContinuity.resolve(
                question = text,
                activePosition = activePosition,
                currentTargetPeriod = report.targetPeriod,
                latestApiPeriod = snapshot.latest.period,
                messages = plan.messages,
                candidates = session.candidates,
            )
        } else {
            null
        }
        val previousMessages = if (intent == AiChatIntent.FREE_CHAT) {
            plan.messages.filter { it.role != AiChatRole.SYSTEM }.takeLast(16)
        } else {
            continuity?.previousMessages.orEmpty()
        }
        val userMessage = AiChatMessage(
            role = AiChatRole.USER,
            content = text,
            targetPeriod = report.targetPeriod,
            positionScope = activePosition,
        )
        val assistantMessage = AiChatMessage(
            role = AiChatRole.ASSISTANT,
            content = "",
            targetPeriod = report.targetPeriod,
            positionScope = activePosition,
        )
        val persona = AiChatPersona.fromId(session.personaId)
        val judgementMode = session.judgementMode
        val learningStrategy = AiLearningStrategy.chat(activeModel, persona.id, judgementMode)
        // The current turn's explicit rank is authoritative. A natural follow-up inherits the
        // most recent rank, while an all-rank request deliberately clears the scope.
        val learningPosition = activePosition ?: 0
        val learningProfile = if (intent.usesLotteryContext) {
            learningStore.profile(
                snapshot.lottery.apiKey,
                config.id,
                learningStrategy,
                learningPosition,
            )
        } else {
            session.learningProfile
        }
        val learningContext = if (intent.usesLotteryContext) {
            learningStore.snapshot(
                snapshot.history,
                snapshot.lottery.apiKey,
                config.id,
                learningStrategy,
                learningPosition,
            )
        } else {
            JSONObject()
        }
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
            progress = when (intent) {
                AiChatIntent.FREE_CHAT -> "正在回复…"
                AiChatIntent.LOTTERY_ANALYSIS -> "正在读取${snapshot.lottery.displayName}开奖 API…"
                AiChatIntent.LOTTERY_PREDICTION -> "正在分析本期候选…"
            },
            error = null,
            prediction = null,
            streamingMessageId = assistantMessage.id,
            contextUsagePercent = plan.usagePercent,
            rolloverNotice = null,
            learningProfile = learningProfile,
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
                    memorySummary = if (intent.usesLotteryContext) {
                        continuity?.relevantFeedback.orEmpty()
                    } else {
                        session.memorySummary
                    },
                    question = text,
                    persona = persona,
                    judgementMode = judgementMode,
                    learningContext = learningContext,
                    intent = intent,
                    positionScope = activePosition,
                    onProgress = { progress ->
                        mainHandler.post {
                            if (generation.get() == token && session.isRunning) {
                                session = session.copy(progress = progress)
                            }
                        }
                    },
                    onStreamText = { content ->
                        mainHandler.post {
                            if (
                                generation.get() == token && session.isRunning &&
                                (!intent.usesLotteryContext || activePosition == null)
                            ) {
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
                        val resolvedLearning = reply.prediction?.let { prediction ->
                            learningStore.profile(
                                snapshot.lottery.apiKey,
                                config.id,
                                learningStrategy,
                                prediction.position,
                            )
                        } ?: learningProfile
                        val completion = if (reply.reasoningVerified && intent != AiChatIntent.FREE_CHAT) {
                            reply.reasoningTokens?.let { "回答完成 · 推理 $it tokens" }
                                ?: "回答完成 · 已验证模型思考"
                        } else {
                            "回答完成"
                        }
                        session = session.copy(
                            isRunning = false,
                            progress = if (intent.usesLotteryContext) {
                                "$completion · 已学习 ${resolvedLearning.settled} 期"
                            } else {
                                completion
                            },
                            error = null,
                            prediction = reply.prediction,
                            candidates = nextCandidates,
                            streamingMessageId = null,
                            learningProfile = resolvedLearning,
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
                            error = AiErrorMessages.userFacing(
                                cause,
                                if (intent == AiChatIntent.FREE_CHAT) "对话失败" else "对话分析失败",
                            ),
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
            judgementMode = old.judgementMode,
            learningProfile = old.learningProfile,
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
                val candidateCount = candidate.prediction.top6.size.coerceAtLeast(1)
                append(
                    if (actual in candidate.prediction.top6) {
                        "上期${candidateCount}码命中"
                    } else {
                        "上期${candidateCount}码未中"
                    },
                )
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
            judgementMode = session.judgementMode,
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
        judgementMode = judgementMode,
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



internal object AiPredictionFreshnessGuard {
    fun error(snapshot: DrawSnapshot, report: ForecastReport): String? = when {
        !snapshot.sourceHealth.isFresh ->
            "开奖数据不是最新状态，预测类问题已拦截。请先刷新成功后再分析"
        report.targetPeriod.isBlank() || report.targetPeriod == "待同步" ->
            "目标期尚未同步，不能使用旧历史生成预测"
        snapshot.nextPeriod != report.targetPeriod ->
            "当前目标期已经变化，请刷新后重新提问"
        report.trainedThroughPeriod != snapshot.latest.period ->
            "分析历史没有训练到最新期开奖，请刷新后重新提问"
        else -> null
    }
}



internal data class AiPositionStatistics(
    val position: Int,
    val currentNumber: Int,
    val count20: List<Int>,
    val count60: List<Int>,
    val count120: List<Int>,
    val omission: List<Int>,
    val successorAfterCurrent: List<Int>,
    val trendDelta: List<Double>,
)

/** Builds deterministic, locally verified facts for the conversation model. */
object AiChatContextBuilder {
    fun build(
        snapshot: DrawSnapshot,
        report: ForecastReport,
        question: String,
        judgementMode: AiJudgementMode,
        learningContext: JSONObject,
        wantsPrediction: Boolean = AiChatProtocol.wantsPrediction(question),
        positionScope: Int? = null,
    ): JSONObject {
        val verifiedHistory = snapshot.history
            .filter { it.numbers.size == 10 }
            .takeLast(120)
        require(verifiedHistory.isNotEmpty()) { "没有可用于对话分析的接口历史" }
        val requestedPosition = positionScope ?: AiPositionScope.extract(question)
        val positions = requestedPosition?.let(::listOf) ?: (0 until 10).toList()
        val rawWindow = when {
            wantsPrediction -> 120
            requestedPosition != null -> 80
            else -> 60
        }
        val compactHistory = verifiedHistory.takeLast(rawWindow)
        val independent = judgementMode == AiJudgementMode.INDEPENDENT
        return JSONObject()
            .put("lottery", snapshot.lottery.displayName)
            .put("latest_period", snapshot.latest.period)
            .put("target_period", report.targetPeriod)
            .put("history_source", "current lottery API snapshot")
            .put("history_order", "oldest_to_newest")
            .put("verified_history_size", verifiedHistory.size)
            .put("raw_history_window", compactHistory.size)
            .put("position_scope", JSONArray(positions.map { it + 1 }))
            .put("latest_numbers", JSONArray(snapshot.latest.numbers))
            .put(
                "verified_position_facts",
                JSONArray(positions.map { position ->
                    AiVerifiedPositionEngine.calculate(snapshot, report, position).toJson()
                }),
            )
            .put(
                "compact_history",
                JSONArray(compactHistory.map { draw ->
                    JSONObject()
                        .put("period", draw.period)
                        .put("numbers", JSONArray(draw.numbers))
                }),
            )
            .put(
                "input_isolation",
                if (independent) {
                    "strict: no native selected position, candidates, matrix or factor weights; only deterministic facts recalculated from the current lottery snapshot"
                } else {
                    "native reference explicitly enabled by the user"
                },
            )
            .apply {
                if (independent) {
                    put("independence_protocol", "raw-history-plus-client-verified-facts-v2")
                    put(
                        "independent_analysis_rule",
                        "verified_position_facts是客户端从当前彩种原始历史逐期计算的权威事实。只能解释和比较，禁止重算、改写或另造期号、序列、次数与遗漏。用户明确指定名次时只处理该名次；只有用户要求全名次比较时才比较十名。",
                    )
                } else {
                    put(
                        "verified_position_statistics",
                        JSONArray(positions.map { position ->
                            toJson(computePositionStatistics(verifiedHistory, position))
                        }),
                    )
                    put("adaptive_learning", learningContext)
                    put(
                        "native_model_reference",
                        JSONObject()
                            .put("algorithm_version", report.algorithmVersion)
                            .put("trained_through_period", report.trainedThroughPeriod)
                            .put("selected_position", report.selectedPosition + 1)
                            .put("top6", JSONArray(report.selected.top6))
                            .put("evidence_mode", report.mode.name)
                            .put(
                                "rule",
                                if (judgementMode == AiJudgementMode.CONTRARIAN) {
                                    "contrarian audit only; actively search for weaknesses and alternatives"
                                } else {
                                    "reference only; independently calculate before accepting"
                                },
                            ),
                    )
                }
            }
    }

    private fun extractPosition(question: String): Int? = AiPositionScope.extract(question)

    internal fun computePositionStatistics(
        historyInput: List<Draw>,
        position: Int,
    ): AiPositionStatistics {
        require(position in 0..9)
        val history = historyInput.filter { it.numbers.size == 10 }.takeLast(120)
        require(history.isNotEmpty()) { "没有可用于对话分析的接口历史" }

        fun counts(window: Int): List<Int> {
            val result = IntArray(10)
            history.takeLast(window).forEach { draw ->
                draw.numbers[position].takeIf { it in 1..10 }?.let { result[it - 1]++ }
            }
            return result.toList()
        }

        val count20 = counts(20)
        val count60 = counts(60)
        val count120 = counts(120)
        val omission = (1..10).map { number ->
            var gap = history.size
            for (index in history.indices.reversed()) {
                if (history[index].numbers[position] == number) {
                    gap = history.lastIndex - index
                    break
                }
            }
            gap
        }
        val current = history.last().numbers[position]
        val successors = IntArray(10)
        for (index in max(1, history.size - 120) until history.size) {
            if (history[index - 1].numbers[position] == current) {
                val next = history[index].numbers[position]
                if (next in 1..10) successors[next - 1]++
            }
        }
        val size20 = history.takeLast(20).size.coerceAtLeast(1).toDouble()
        val size60 = history.takeLast(60).size.coerceAtLeast(1).toDouble()
        val trend = (0 until 10).map { number ->
            abs(count20[number] / size20 - count60[number] / size60)
        }
        return AiPositionStatistics(
            position = position,
            currentNumber = current,
            count20 = count20,
            count60 = count60,
            count120 = count120,
            omission = omission,
            successorAfterCurrent = successors.toList(),
            trendDelta = trend,
        )
    }

    private fun toJson(stats: AiPositionStatistics): JSONObject = JSONObject()
        .put("position", stats.position + 1)
        .put("current_number", stats.currentNumber)
        .put("count_20_by_number_1_to_10", JSONArray(stats.count20))
        .put("count_60_by_number_1_to_10", JSONArray(stats.count60))
        .put("count_120_by_number_1_to_10", JSONArray(stats.count120))
        .put("omission_by_number_1_to_10", JSONArray(stats.omission))
        .put("successor_after_current_by_number_1_to_10", JSONArray(stats.successorAfterCurrent))
        .put("trend_delta_20_vs_60_by_number_1_to_10", JSONArray(stats.trendDelta))
}

private class RemoteAiChatClient {
    @Volatile
    private var activeConnection: HttpURLConnection? = null

    fun cancel() {
        activeConnection?.disconnect()
        activeConnection = null
    }

    fun chat(
        config: AiConfig,
        snapshot: DrawSnapshot,
        report: ForecastReport,
        previousMessages: List<AiChatMessage>,
        memorySummary: String,
        question: String,
        persona: AiChatPersona,
        judgementMode: AiJudgementMode,
        learningContext: JSONObject,
        intent: AiChatIntent,
        positionScope: Int?,
        onProgress: (String) -> Unit,
        onStreamText: (String) -> Unit,
    ): AiChatReply {
        require(config.isComplete) { "AI 配置不完整" }
        val endpoint = URL(config.endpoint.trim())
        require(endpoint.protocol == "https") { "AI 接口必须使用 HTTPS" }
        val started = System.currentTimeMillis()
        val wantsPrediction = intent.wantsPrediction
        val expectedTargetPeriod = if (intent.usesLotteryContext) report.targetPeriod.trim() else ""
        AiChatProtocol.wantsPrediction(if (wantsPrediction) question else "")
        val context = if (intent.usesLotteryContext) {
            AiChatContextBuilder.build(
                snapshot = snapshot,
                report = report,
                question = question,
                judgementMode = judgementMode,
                learningContext = learningContext,
                wantsPrediction = wantsPrediction,
                positionScope = positionScope,
            )
        } else {
            null
        }
        val decision = decisionFor(config, intent)
        val responsesApi = endpoint.path.trimEnd('/').endsWith("/responses")
        val messages = conversationMessages(
            context = context,
            previousMessages = previousMessages,
            memorySummary = memorySummary,
            question = question,
            wantsPrediction = wantsPrediction,
            persona = persona,
            judgementMode = judgementMode,
            intent = intent,
            expectedTargetPeriod = expectedTargetPeriod,
            positionScope = positionScope,
        )
        val publisher = VisibleStreamPublisher(onStreamText)

        fun runRequest(activeDecision: AiReasoningDecision): JSONObject {
            val streamingRequest = requestBody(
                config = config,
                responsesApi = responsesApi,
                messages = messages,
                decision = activeDecision,
                stream = true,
                wantsPrediction = wantsPrediction,
                intent = intent,
            )
            return try {
                execute(
                    endpoint = endpoint,
                    config = config,
                    request = streamingRequest,
                    timeoutMs = timeoutFor(activeDecision, intent),
                    onProgress = onProgress,
                    publisher = publisher,
                    intent = intent,
                )
            } catch (_: AiChatStreamingRejectedException) {
                publisher.reset()
                onProgress("当前接口不支持流式返回，已切换兼容输出…")
                execute(
                    endpoint = endpoint,
                    config = config,
                    request = requestBody(
                        config = config,
                        responsesApi = responsesApi,
                        messages = messages,
                        decision = activeDecision,
                        stream = false,
                        wantsPrediction = wantsPrediction,
                        intent = intent,
                    ),
                    timeoutMs = timeoutFor(activeDecision, intent),
                    onProgress = onProgress,
                    publisher = publisher,
                    intent = intent,
                )
            }
        }

        onProgress(
            if (intent == AiChatIntent.FREE_CHAT) {
                "正在连接 ${config.displayName}…"
            } else {
                "正在连接 ${config.displayName} · ${persona.displayName}…"
            },
        )
        var response = try {
            runRequest(decision)
        } catch (cause: AiChatProtocolRejectedException) {
            if (!decision.sendControl) throw cause
            publisher.reset()
            onProgress("接口拒绝显式思考参数，正在使用模型默认协议重发一次…")
            runRequest(
                decision.copy(sendControl = false, enableThinking = false, effort = null),
            )
        }
        var rawContent = extractContent(response)
        if (rawContent.isBlank()) {
            val hadReasoning = extractReasoning(response).isNotBlank()
            publisher.reset()
            onProgress(
                if (hadReasoning) {
                    "模型只返回了思考流，正在用同一模型关闭额外思考并生成最终正文…"
                } else {
                    "流式接口没有返回正文，正在切换同一模型的普通兼容输出…"
                },
            )
            val finalizationDecision = when (decision.protocol) {
                AiReasoningProtocol.DEEPSEEK,
                AiReasoningProtocol.OPENROUTER,
                AiReasoningProtocol.ENABLE_THINKING,
                -> decision.copy(
                    sendControl = true,
                    enableThinking = false,
                    effort = null,
                    displayLabel = "${decision.protocol.label} · 对话正文收口",
                )
                AiReasoningProtocol.OPENAI,
                AiReasoningProtocol.AUTO,
                AiReasoningProtocol.NONE,
                -> decision.copy(
                    sendControl = false,
                    enableThinking = false,
                    effort = null,
                    displayLabel = "对话正文收口",
                )
            }
            val finalizationMessages = JSONArray(messages.toString()).apply {
                put(
                    JSONObject()
                        .put("role", "user")
                        .put(
                            "content",
                            if (wantsPrediction) {
                                "上一请求没有产生最终正文。当前唯一目标期为${expectedTargetPeriod}期。请立即基于同一份原始历史完成回答，不要输出思考过程，并按原要求在正文后追加完整 tianji_forecast；不得沿用旧期号。"
                            } else {
                                "上一请求没有产生最终正文。请立即基于同一上下文给出简体中文最终回答，不要输出思考过程。"
                            },
                        ),
                )
            }
            response = try {
                execute(
                    endpoint = endpoint,
                    config = config,
                    request = requestBody(
                        config = config,
                        responsesApi = responsesApi,
                        messages = finalizationMessages,
                        decision = finalizationDecision,
                        stream = false,
                        wantsPrediction = wantsPrediction,
                        intent = intent,
                    ),
                    timeoutMs = if (intent == AiChatIntent.FREE_CHAT) 20_000 else 45_000,
                    onProgress = onProgress,
                    publisher = publisher,
                    intent = intent,
                )
            } catch (cause: AiChatProtocolRejectedException) {
                execute(
                    endpoint = endpoint,
                    config = config,
                    request = requestBody(
                        config = config,
                        responsesApi = responsesApi,
                        messages = finalizationMessages,
                        decision = finalizationDecision.copy(sendControl = false),
                        stream = false,
                        wantsPrediction = wantsPrediction,
                        intent = intent,
                    ),
                    timeoutMs = if (intent == AiChatIntent.FREE_CHAT) 20_000 else 45_000,
                    onProgress = onProgress,
                    publisher = publisher,
                    intent = intent,
                )
            }
            rawContent = extractContent(response)
        }
        require(rawContent.isNotBlank()) {
            if (extractReasoning(response).isNotBlank()) {
                "模型只返回了思考过程；关闭思考收口后仍没有最终正文"
            } else {
                "模型接口已响应，但流式与普通输出均没有返回正文"
            }
        }
        val parsedPrediction = if (wantsPrediction) AiChatProtocol.parsePrediction(rawContent) else null
        val prediction = parsedPrediction?.let { value ->
            if (positionScope != null && value.position != positionScope) {
                value.copy(position = positionScope)
            } else {
                value
            }
        }
        val reconciled = AiTargetPeriodGuard.reconcilePredictionText(
            text = AiChatProtocol.visibleText(rawContent, prediction != null),
            expectedTargetPeriod = expectedTargetPeriod,
            isPrediction = wantsPrediction,
        )
        val verifiedFacts = if (intent.usesLotteryContext && positionScope != null) {
            AiVerifiedPositionEngine.calculate(snapshot, report, positionScope)
        } else {
            null
        }
        val content = AiVerifiedAnswerComposer.compose(
            modelText = reconciled,
            facts = verifiedFacts,
            intent = intent,
            question = question,
        )
        publisher.finish(content)
        val usage = extractUsage(response)
        val reasoningVerified = extractReasoning(response).isNotBlank() ||
            (usage.reasoningTokens ?: 0) > 0
        onProgress(
            when {
                response.optBoolean("_tianji_stream_interrupted") && wantsPrediction ->
                    "网络中断后已恢复现有回答，正在整理候选卡片…"
                response.optBoolean("_tianji_stream_interrupted") ->
                    "网络中断后已恢复现有回答…"
                wantsPrediction -> "回答完成，正在整理候选卡片…"
                else -> "回答完成…"
            },
        )
        return AiChatReply(
            content = content,
            prediction = prediction,
            latencyMs = System.currentTimeMillis() - started,
            responseId = response.optString("id"),
            reasoningTokens = usage.reasoningTokens,
            reasoningVerified = reasoningVerified,
        )
    }

    private fun conversationMessages(
        context: JSONObject?,
        previousMessages: List<AiChatMessage>,
        memorySummary: String,
        question: String,
        wantsPrediction: Boolean,
        persona: AiChatPersona,
        judgementMode: AiJudgementMode,
        intent: AiChatIntent,
        expectedTargetPeriod: String,
        positionScope: Int?,
    ): JSONArray = JSONArray().apply {
        put(
            JSONObject()
                .put("role", "system")
                .put("content", systemPrompt(intent, persona, judgementMode)),
        )
        if (context != null) {
            put(
                JSONObject()
                    .put("role", "user")
                    .put(
                        "content",
                        "以下是当前彩种上游开奖 API 返回的历史与必要元数据。独立模式不包含本机候选、模型选中名次、概率矩阵或因子权重；verified_position_facts由程序直接从本次 API 历史逐期计算，必须原样遵守。参考/反向模式才会额外附带native_model_reference：\n${context}",
                    ),
            )
        }
        if (intent.usesLotteryContext && memorySummary.isNotBlank()) {
            put(
                JSONObject()
                    .put("role", "system")
                    .put(
                        "content",
                        "以下内容仅是与用户当前问题直接相关、且已按期号核验的结算记录。只有这里明确给出的记录才能称为上次或前一期；没有这段内容时不得主动翻旧账。adaptive_learning只是同名次长期汇总，不代表最近一期结果：\n$memorySummary",
                    ),
            )
        }
        previousMessages
            .filter { it.content.isNotBlank() }
            .filter { intent.usesLotteryContext || it.role != AiChatRole.SYSTEM }
            .forEach { message ->
            val role = when (message.role) {
                AiChatRole.SYSTEM -> "system"
                AiChatRole.USER -> "user"
                AiChatRole.ASSISTANT -> "assistant"
            }
            put(
                JSONObject()
                    .put("role", role)
                    .put(
                        "content",
                        AiTargetPeriodGuard.contextualizePreviousMessage(
                            message = message,
                            expectedTargetPeriod = expectedTargetPeriod,
                        ),
                    ),
            )
        }
        if (intent.usesLotteryContext && expectedTargetPeriod.isNotBlank()) {
            put(
                JSONObject()
                    .put("role", "system")
                    .put(
                        "content",
                        AiTargetPeriodGuard.currentRequestInstruction(expectedTargetPeriod),
                    ),
            )
        }
        if (intent.usesLotteryContext && positionScope != null) {
            put(
                JSONObject()
                    .put("role", "system")
                    .put(
                        "content",
                        "用户当前这句话指定分析第${positionScope + 1}名，它的优先级高于之前所有名次。保持正常自然对话；之前其他名次只是聊天历史，不得沿用其数据或结论。当前上游开奖 API 数据和verified_position_facts是本轮唯一事实源。",
                    ),
            )
        }
        val currentQuestion = if (intent.usesLotteryContext && expectedTargetPeriod.isNotBlank()) {
            buildString {
                append("【当前唯一目标期：${expectedTargetPeriod}期】\n")
                if (positionScope != null) append("【当前唯一分析名次：第${positionScope + 1}名】\n")
                append(question)
            }
        } else {
            question
        }
        put(JSONObject().put("role", "user").put("content", currentQuestion))
    }

    private fun systemPrompt(
        intent: AiChatIntent,
        persona: AiChatPersona,
        judgementMode: AiJudgementMode,
    ): String {
        if (intent == AiChatIntent.FREE_CHAT) {
            return "你是天机 App 内置的通用 AI 助手。优先理解用户当前真正想表达的内容，像正常聊天助手一样自然回答。" +
                "普通问候用一两句话快速回应，也可以回答日常、软件使用和通用知识问题。" +
                "除非用户明确提出开奖、走势、历史分析或预测请求，否则禁止主动谈彩票、期号、候选号码、命中率或复盘，" +
                "更不能把“你好”等普通对话理解成预测命令。使用简体中文，直接回答，不输出隐藏思维链。"
        }
        return buildString {
            val judgementInstruction = when (judgementMode) {
                AiJudgementMode.INDEPENDENT ->
                    "当前为严格独立模式：客户端不提供本机候选、模型选择名次、概率矩阵或因子权重；但会提供由当前彩种原始历史逐期计算的verified_position_facts。用户明确指定名次时只分析该名次，用户要求全名次时才比较十名。不得改写核验事实，也不得为了显得不同而故意反选。"
                AiJudgementMode.NATIVE_REFERENCE ->
                    "当前为参考本机模式：native_model_reference只是一份可质疑参考，必须独立计算并在不同时坚持自己的结论。"
                AiJudgementMode.CONTRARIAN ->
                    "当前为反向审计模式：优先寻找native_model_reference中的薄弱号码、样本偏差和替代方案，不得简单赞同。"
            }
            append(
                "你是天机内置的开奖记录分析助手，当前分析人设为【${persona.displayName}】。" +
                    "人设要求：${persona.instruction}" + judgementInstruction +
                    "adaptive_learning由客户端根据同彩种、同名次的真实前向开奖结果累计更新，只能作为长期汇总信号。除非上下文明确提供与当前问题直接相关的已结算记录，否则不得把历史未中说成上一期，也不得主动复盘几天前的预测。若提供了紧邻当前目标期的未中记录，必须比较当时候选与实际号码，说明哪些信号没有区分力以及本期如何调整；禁止机械复制旧候选。" +
                    "使用简体中文直接、自然地回答，只处理用户当前提出的问题。" +
                    "所有模式中的期号、最近序列、20/60/120期次数和遗漏只能引用当前上游开奖 API 对应的verified_position_facts。用户问什么就回答什么，不要擅自补充固定模板、其他名次、候选号码或另一套统计。不得虚构期号、次数或数据来源。" +
                    "所有转移、遗漏和趋势结论必须同时说明样本强弱；1次与2次之类的小差异不得包装成强规律。" +
                    "用户说出现几率大时，应解释为历史样本中的相对频次或模型相对评分，不得称为真实中奖概率。" +
                    "不要输出隐藏思维链，不得承诺必中、盈利或准确率。证据接近时明确说差异小或没有强候选。" +
                    "回答先给结论，再给关键依据、策略变化和不确定性，不要堆砌无关术语。",
            )
            if (intent == AiChatIntent.LOTTERY_PREDICTION) {
                append(
                    "用户本次明确要求候选或预测。正文先给简洁依据与本期策略变化，随后追加且只追加一个" +
                        "<tianji_forecast>{\"position\":1至10整数,\"scores\":[按号码1至10排列的10项非负评分]," +
                        "\"strategy_weights\":[与六类因子顺序一致的6项非负权重],\"strategy_note\":\"不超过60字的本期策略变化\"}</tianji_forecast>。" +
                        "scores必须来自本次独立比较，避免无依据并列。",
                )
            } else {
                append("用户本次只要求解释或分析，不是候选预测请求。禁止主动输出候选号码、六码、七码或tianji_forecast。")
            }
        }
    }

    private fun decisionFor(config: AiConfig, intent: AiChatIntent): AiReasoningDecision {
        val resolved = AiReasoningEngine.resolve(config)
        if (intent != AiChatIntent.FREE_CHAT) return resolved
        return when (resolved.protocol) {
            AiReasoningProtocol.DEEPSEEK,
            AiReasoningProtocol.OPENROUTER,
            AiReasoningProtocol.ENABLE_THINKING,
            -> resolved.copy(
                preference = AiReasoningMode.LOW,
                sendControl = true,
                enableThinking = false,
                effort = null,
                displayLabel = "快速对话 · 已关闭长思考",
            )
            AiReasoningProtocol.OPENAI,
            AiReasoningProtocol.AUTO,
            AiReasoningProtocol.NONE,
            -> resolved.copy(
                preference = AiReasoningMode.LOW,
                sendControl = false,
                enableThinking = false,
                effort = null,
                displayLabel = "快速对话",
            )
        }
    }

    private fun requestBody(
        config: AiConfig,
        responsesApi: Boolean,
        messages: JSONArray,
        decision: AiReasoningDecision,
        stream: Boolean,
        wantsPrediction: Boolean,
        intent: AiChatIntent,
    ): JSONObject = JSONObject().apply {
        put("model", config.model.trim())
        put("stream", stream)
        val outputBudget = when {
            intent == AiChatIntent.FREE_CHAT -> 768
            decision.expectsReasoning && wantsPrediction -> 8_192
            decision.expectsReasoning -> 6_144
            wantsPrediction -> 4_096
            else -> 2_048
        }
        if (intent == AiChatIntent.FREE_CHAT || config.provider != AiProvider.COMPATIBLE) {
            put(if (responsesApi) "max_output_tokens" else "max_tokens", outputBudget)
        }
        if (responsesApi) {
            put("store", false)
            put("input", messages)
        } else {
            put("messages", messages)
        }
        if (!decision.expectsReasoning && decision.protocol != AiReasoningProtocol.OPENAI) {
            put("temperature", if (intent == AiChatIntent.FREE_CHAT) 0.65 else 0.2)
        }
        applyReasoning(decision, responsesApi)
    }

    private fun JSONObject.applyReasoning(
        decision: AiReasoningDecision,
        responsesApi: Boolean,
    ) {
        if (!decision.sendControl) return
        when (decision.protocol) {
            AiReasoningProtocol.DEEPSEEK -> {
                put(
                    "thinking",
                    JSONObject().put("type", if (decision.enableThinking) "enabled" else "disabled"),
                )
                if (decision.enableThinking) put("reasoning_effort", decision.effort ?: "high")
            }
            AiReasoningProtocol.OPENAI -> if (decision.enableThinking) {
                if (responsesApi) {
                    put("reasoning", JSONObject().put("effort", decision.effort ?: "high"))
                } else {
                    put("reasoning_effort", decision.effort ?: "high")
                }
            }
            AiReasoningProtocol.OPENROUTER -> put(
                "reasoning",
                if (decision.enableThinking) {
                    JSONObject().put("effort", decision.effort ?: "high").put("exclude", true)
                } else {
                    JSONObject().put("enabled", false)
                },
            )
            AiReasoningProtocol.ENABLE_THINKING -> put("enable_thinking", decision.enableThinking)
            AiReasoningProtocol.AUTO, AiReasoningProtocol.NONE -> Unit
        }
    }

    private fun execute(
        endpoint: URL,
        config: AiConfig,
        request: JSONObject,
        timeoutMs: Int,
        onProgress: (String) -> Unit,
        publisher: VisibleStreamPublisher,
        intent: AiChatIntent,
    ): JSONObject {
        var lastFailure: Throwable? = null
        repeat(if (intent == AiChatIntent.FREE_CHAT) 1 else 2) { attempt ->
            var deliveredVisibleText = false
            val connection = endpoint.openConnection() as HttpURLConnection
            activeConnection = connection
            try {
                connection.requestMethod = "POST"
                connection.connectTimeout = 12_000
                connection.readTimeout = timeoutMs
                connection.doOutput = true
                connection.useCaches = false
                connection.setRequestProperty("Content-Type", "application/json")
                connection.setRequestProperty("Accept", "text/event-stream, application/json")
                connection.setRequestProperty("Authorization", "Bearer ${config.apiKey.trim()}")
                connection.outputStream.use { output ->
                    output.write(request.toString().toByteArray(Charsets.UTF_8))
                }
                onProgress(
                    when {
                        intent == AiChatIntent.FREE_CHAT && request.optBoolean("stream", false) ->
                            "正在回复，内容会实时显示…"
                        intent == AiChatIntent.FREE_CHAT -> "正在回复…"
                        request.optBoolean("stream", false) ->
                            "模型正在分析，回答开始后会实时显示…"
                        else -> "模型正在分析，完成后将分段显示…"
                    },
                )
                val code = connection.responseCode
                if (code in 200..299) {
                    val reader = connection.inputStream.bufferedReader(Charsets.UTF_8)
                    return readSuccessResponse(
                        reader = reader,
                        contentType = connection.contentType.orEmpty(),
                        publisher = publisher,
                        isCancelled = { activeConnection !== connection },
                        onVisibleDelivered = { deliveredVisibleText = true },
                    )
                }
                val body = connection.errorStream
                    ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                if (
                    code in listOf(400, 404, 422) &&
                    listOf("reasoning", "thinking", "enable_thinking", "reasoning_effort")
                        .any { body.contains(it, ignoreCase = true) }
                ) {
                    throw AiChatProtocolRejectedException("AI 接口拒绝当前思考参数：${body.take(140)}")
                }
                if (
                    request.optBoolean("stream", false) &&
                    code in listOf(400, 404, 405, 415, 422) &&
                    body.contains("stream", ignoreCase = true)
                ) {
                    throw AiChatStreamingRejectedException()
                }
                if (intent != AiChatIntent.FREE_CHAT && attempt == 0 && (code == 429 || code in 500..599)) {
                    onProgress(if (code == 429) "供应商限流，正在重连一次…" else "供应商暂时异常，正在重连一次…")
                    Thread.sleep(if (code == 429) 1_500L else 500L)
                    return@repeat
                }
                error("AI 接口 HTTP $code：${body.take(180)}")
            } catch (cause: SocketTimeoutException) {
                lastFailure = cause
                if (intent != AiChatIntent.FREE_CHAT && attempt == 0 && !deliveredVisibleText) {
                    onProgress("模型响应超时，正在进行一次网络重连…")
                    return@repeat
                }
                throw IllegalStateException(
                    if (deliveredVisibleText) "流式回答中断，已保留已生成内容" else "模型响应超时",
                    cause,
                )
            } catch (cause: EOFException) {
                throw IllegalStateException(AiErrorMessages.userFacing(cause, "模型连接提前结束"), cause)
            } catch (cause: SocketException) {
                throw IllegalStateException(AiErrorMessages.userFacing(cause, "网络连接异常中断"), cause)
            } catch (cause: IOException) {
                throw IllegalStateException(AiErrorMessages.userFacing(cause, "网络连接中断"), cause)
            } finally {
                if (activeConnection === connection) activeConnection = null
                connection.disconnect()
            }
        }
        throw IllegalStateException("模型对话超过 ${timeoutMs / 1_000} 秒或重连后仍失败", lastFailure)
    }

    private fun readSuccessResponse(
        reader: BufferedReader,
        contentType: String,
        publisher: VisibleStreamPublisher,
        isCancelled: () -> Boolean,
        onVisibleDelivered: () -> Unit,
    ): JSONObject = reader.use {
        val prefix = mutableListOf<String>()
        var firstMeaningful: String? = null
        while (firstMeaningful == null) {
            val line = it.readLine() ?: break
            prefix += line
            if (line.isNotBlank()) firstMeaningful = line
        }
        val looksLikeSse = contentType.contains("text/event-stream", ignoreCase = true) ||
            firstMeaningful?.trimStart()?.let { line ->
                line.startsWith("data:") || line.startsWith("event:") || line.startsWith(":")
            } == true
        if (looksLikeSse) {
            readSse(it, prefix, publisher, isCancelled, onVisibleDelivered)
        } else {
            val body = buildString {
                prefix.forEachIndexed { index, line ->
                    if (index > 0) append('\n')
                    append(line)
                }
                val remainder = it.readText()
                if (remainder.isNotEmpty()) {
                    if (isNotEmpty()) append('\n')
                    append(remainder)
                }
            }
            val root = JSONObject(body)
            val content = extractContent(root)
            emitBufferedFallback(content, publisher, isCancelled, onVisibleDelivered)
            root
        }
    }

    private fun readSse(
        reader: BufferedReader,
        initialLines: List<String>,
        publisher: VisibleStreamPublisher,
        isCancelled: () -> Boolean,
        onVisibleDelivered: () -> Unit,
    ): JSONObject {
        val rawContent = StringBuilder()
        val reasoning = StringBuilder()
        var responseId = ""
        var usage: JSONObject? = null
        var eventName = ""
        val eventData = mutableListOf<String>()

        fun appendVisible(delta: String) {
            if (delta.isEmpty()) return
            rawContent.append(delta)
            if (publisher.append(delta)) onVisibleDelivered()
        }

        fun consumeEvent() {
            if (eventData.isEmpty()) {
                eventName = ""
                return
            }
            val data = eventData.joinToString("\n").trim()
            eventData.clear()
            if (data.isBlank() || data == "[DONE]") {
                eventName = ""
                return
            }
            val root = runCatching { JSONObject(data) }.getOrNull()
                ?: run {
                    eventName = ""
                    return
                }
            root.optJSONObject("error")?.let { error ->
                throw IllegalStateException(
                    error.optString("message").ifBlank { "模型流式接口返回错误" },
                )
            }
            responseId = root.optString("id").ifBlank { responseId }
            root.optJSONObject("usage")?.let { usage = it }

            val type = root.optString("type").ifBlank { eventName }
            when {
                type == "response.output_text.delta" -> appendVisible(root.optString("delta"))
                type == "response.output_text.done" && rawContent.isEmpty() -> {
                    appendVisible(root.optString("text"))
                }
                type.contains("reasoning", ignoreCase = true) && type.endsWith(".delta") -> {
                    reasoning.append(root.optString("delta"))
                }
                type == "response.completed" -> {
                    root.optJSONObject("response")?.let { completed ->
                        responseId = completed.optString("id").ifBlank { responseId }
                        completed.optJSONObject("usage")?.let { usage = it }
                        if (rawContent.isEmpty()) appendVisible(extractContent(completed))
                        reasoning.append(extractReasoning(completed))
                    }
                }
            }

            val choice = root.optJSONArray("choices")?.optJSONObject(0)
            val delta = choice?.optJSONObject("delta")
            extractTextNode(delta?.opt("content"))
                .takeIf(String::isNotEmpty)
                ?.let(::appendVisible)
            listOf("reasoning_content", "reasoning", "thinking").forEach { key ->
                extractTextNode(delta?.opt(key))
                    .takeIf(String::isNotEmpty)
                    ?.let(reasoning::append)
            }
            listOf("reasoning_content", "reasoning", "thinking").forEach { key ->
                extractTextNode(root.opt(key))
                    .takeIf(String::isNotEmpty)
                    ?.let(reasoning::append)
            }
            if (rawContent.isEmpty()) {
                val message = choice?.optJSONObject("message")
                extractTextNode(message?.opt("content"))
                    .takeIf(String::isNotEmpty)
                    ?.let(::appendVisible)
                extractTextNode(message?.opt("reasoning_content"))
                    .takeIf(String::isNotEmpty)
                    ?.let(reasoning::append)
            }
            eventName = ""
        }

        fun processLine(line: String) {
            if (isCancelled()) throw IllegalStateException("已取消本次对话")
            when {
                line.isBlank() -> consumeEvent()
                line.startsWith("event:") -> eventName = line.substringAfter(':').trim()
                line.startsWith("data:") -> eventData += line.substringAfter(':').trimStart()
                line.startsWith(":") -> Unit
            }
        }

        var streamFailure: IOException? = null
        try {
            initialLines.forEach(::processLine)
            while (true) {
                val line = reader.readLine() ?: break
                processLine(line)
            }
            consumeEvent()
        } catch (cause: IOException) {
            streamFailure = cause
        }
        publisher.flush()
        if (rawContent.isBlank() && reasoning.isBlank()) {
            streamFailure?.let { throw it }
        }
        return JSONObject()
            .put("id", responseId)
            .put("output_text", rawContent.toString())
            .put("_tianji_reasoning", reasoning.toString())
            .put("_tianji_stream_interrupted", streamFailure != null)
            .put("usage", usage ?: JSONObject())
    }

    private fun emitBufferedFallback(
        content: String,
        publisher: VisibleStreamPublisher,
        isCancelled: () -> Boolean,
        onVisibleDelivered: () -> Unit,
    ) {
        if (content.isBlank()) return
        content.chunked(8).forEach { chunk ->
            if (isCancelled() || Thread.currentThread().isInterrupted) {
                throw IllegalStateException("已取消本次对话")
            }
            if (publisher.append(chunk)) onVisibleDelivered()
            Thread.sleep(12L)
        }
        publisher.flush()
    }

    private fun timeoutFor(decision: AiReasoningDecision, intent: AiChatIntent): Int = when {
        intent == AiChatIntent.FREE_CHAT -> 30_000
        decision.preference == AiReasoningMode.HIGH -> 120_000
        decision.expectsReasoning -> 90_000
        else -> 60_000
    }

    private fun extractContent(root: JSONObject): String {
        root.optString("output_text").trim().takeIf(String::isNotBlank)?.let { return it }
        val chatContent = root.optJSONArray("choices")
            ?.optJSONObject(0)
            ?.optJSONObject("message")
            ?.opt("content")
        extractTextNode(chatContent).trim().takeIf(String::isNotBlank)?.let { return it }
        val output = root.optJSONArray("output") ?: return ""
        return (0 until output.length()).flatMap { index ->
            val content = output.optJSONObject(index)?.optJSONArray("content") ?: return@flatMap emptyList()
            (0 until content.length()).mapNotNull { contentIndex ->
                val item = content.optJSONObject(contentIndex) ?: return@mapNotNull null
                item.optString("text").ifBlank { item.optString("content") }
                    .takeIf(String::isNotBlank)
            }
        }.joinToString("\n")
    }

    private fun extractTextNode(value: Any?): String = when (value) {
        null, JSONObject.NULL -> ""
        is String -> value
        is JSONObject -> value.optString("text").ifBlank {
            value.optString("content").ifBlank { value.optString("value") }
        }
        is JSONArray -> (0 until value.length()).mapNotNull { index ->
            extractTextNode(value.opt(index)).takeIf(String::isNotBlank)
        }.joinToString("")
        else -> ""
    }

    private fun extractReasoning(root: JSONObject): String = root
        .optString("_tianji_reasoning")
        .ifBlank {
            root.optJSONArray("choices")
                ?.optJSONObject(0)
                ?.optJSONObject("message")
                ?.optString("reasoning_content")
                .orEmpty()
        }

    private fun extractUsage(root: JSONObject): AiTokenUsage {
        val usage = root.optJSONObject("usage") ?: return AiTokenUsage()
        val reasoning = usage.optJSONObject("completion_tokens_details")
            ?.optInt("reasoning_tokens", -1)?.takeIf { it >= 0 }
            ?: usage.optJSONObject("output_tokens_details")
                ?.optInt("reasoning_tokens", -1)?.takeIf { it >= 0 }
        fun firstPositive(vararg keys: String): Int? = keys.firstNotNullOfOrNull { key ->
            usage.optInt(key, -1).takeIf { it >= 0 }
        }
        return AiTokenUsage(
            inputTokens = firstPositive("prompt_tokens", "input_tokens"),
            outputTokens = firstPositive("completion_tokens", "output_tokens"),
            reasoningTokens = reasoning,
        )
    }

    private class VisibleStreamPublisher(
        private val onText: (String) -> Unit,
    ) {
        private val raw = StringBuilder()
        private var lastVisible = ""
        private var lastEmitAt = 0L

        fun append(delta: String): Boolean {
            if (delta.isEmpty()) return false
            raw.append(delta)
            val visible = AiChatProtocol.visibleStreamingText(raw.toString())
            if (visible == lastVisible) return false
            val now = System.currentTimeMillis()
            val urgent = delta.any { it == '\n' || it in "。！？；：" } ||
                visible.length - lastVisible.length >= 32
            if (urgent || now - lastEmitAt >= 120L) {
                lastVisible = visible
                lastEmitAt = now
                onText(visible)
                return visible.isNotBlank()
            }
            return false
        }

        fun flush() {
            val visible = AiChatProtocol.visibleStreamingText(raw.toString())
            if (visible != lastVisible) {
                lastVisible = visible
                lastEmitAt = System.currentTimeMillis()
                onText(visible)
            }
        }

        fun finish(finalText: String) {
            lastVisible = finalText
            onText(finalText)
        }

        fun reset() {
            raw.clear()
            lastVisible = ""
            lastEmitAt = 0L
            onText("")
        }
    }

    private class AiChatProtocolRejectedException(message: String) : IllegalStateException(message)
    private class AiChatStreamingRejectedException : IllegalStateException()
}
