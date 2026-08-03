package com.tianji.probabilitylab.nativev4.ai

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.core.content.edit
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.model.LotteryType
import org.json.JSONArray
import org.json.JSONObject
import java.io.EOFException
import java.io.IOException
import java.net.HttpURLConnection
import java.net.SocketException
import java.net.SocketTimeoutException
import java.net.URL
import java.security.KeyStore
import java.util.concurrent.ConcurrentHashMap
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

enum class AiProvider(
    val label: String,
    val defaultEndpoint: String,
    val defaultModel: String,
    val fallbackModels: List<String>,
) {
    DEEPSEEK(
        label = "DeepSeek",
        defaultEndpoint = "https://api.deepseek.com/chat/completions",
        defaultModel = "deepseek-v4-flash",
        fallbackModels = listOf("deepseek-v4-flash", "deepseek-v4-pro"),
    ),
    OPENAI(
        label = "OpenAI",
        defaultEndpoint = "https://api.openai.com/v1/responses",
        defaultModel = "",
        fallbackModels = emptyList(),
    ),
    COMPATIBLE(
        label = "兼容服务 / 自定义",
        defaultEndpoint = "",
        defaultModel = "",
        fallbackModels = emptyList(),
    ),
}

enum class AiAnalysisMode(val label: String, val detail: String, val historyLimit: Int) {
    FAST("60期窗口", "最近 60 期接口历史；速度较快", 60),
    DEEP("120期窗口", "最近 120 期接口历史；数据更多但不等于深度思考", 120),
}

data class AiConfig(
    val id: String = "",
    val name: String = "",
    val provider: AiProvider = AiProvider.DEEPSEEK,
    val endpoint: String = "",
    val model: String = "",
    val apiKey: String = "",
    val analysisMode: AiAnalysisMode = AiAnalysisMode.FAST,
    val reasoningMode: AiReasoningMode = AiReasoningMode.LOW,
    val reasoningProtocol: AiReasoningProtocol = AiReasoningProtocol.AUTO,
    val inputPricePerMillion: Double? = null,
    val outputPricePerMillion: Double? = null,
    val capability: AiCapabilitySnapshot? = null,
) {
    val canQueryModels: Boolean
        get() = endpoint.startsWith("https://") && apiKey.isNotBlank()

    val isComplete: Boolean
        get() = canQueryModels && model.isNotBlank()

    val displayName: String
        get() = name.ifBlank { "${provider.label} · ${model.ifBlank { "待选模型" }}" }
}

enum class AiConnectionState { UNTESTED, TESTING, CONNECTED, ANALYZING, CANCELLED, FAILED }

data class AiRunStatus(
    val profileId: String,
    val state: AiConnectionState = AiConnectionState.UNTESTED,
    val message: String = "尚未测试",
    val latencyMs: Long? = null,
    val checkedAtEpochMs: Long? = null,
    val timeline: List<AiConversationEvent> = emptyList(),
)

data class AiCapabilitySnapshot(
    val structuredOutput: Boolean,
    val reasoningControl: Boolean,
    val reasoningVerified: Boolean,
    val usageReturned: Boolean,
    val protocol: AiReasoningProtocol,
    val latencyMs: Long,
    val checkedAtEpochMs: Long,
    val message: String,
)

data class AiConnectionProbe(
    val latencyMs: Long,
    val responseId: String,
    val capability: AiCapabilitySnapshot,
)

data class AiModelCatalog(
    val models: List<String>,
    val latencyMs: Long,
)

data class AiForecast(
    val profileId: String,
    val profileName: String,
    val targetPeriod: String,
    val position: Int,
    val top6: List<Int>,
    val top7: List<Int>,
    val probabilities: List<Double>,
    val analysis: String,
    val riskNote: String,
    val selfRating: Double,
    val model: String,
    val analysisMode: AiAnalysisMode,
    val reasoningMode: AiReasoningMode,
    val reasoningProtocol: AiReasoningProtocol,
    val reasoningState: AiReasoningState,
    val reasoningTokens: Int?,
    val inputTokens: Int?,
    val outputTokens: Int?,
    val estimatedCost: Double?,
    val executionNote: String,
    val createdAtEpochMs: Long,
    val latencyMs: Long,
    val responseId: String,
)

data class AiForecastRecord(
    val id: Long,
    val lottery: LotteryType,
    val profileId: String,
    val profileName: String,
    val targetPeriod: String,
    val trainedThroughPeriod: String,
    val position: Int,
    val top6: List<Int>,
    val top7: List<Int>,
    val probabilities: List<Double>,
    val analysis: String,
    val riskNote: String,
    val selfRating: Double,
    val model: String,
    val analysisMode: AiAnalysisMode,
    val reasoningMode: AiReasoningMode,
    val reasoningProtocol: AiReasoningProtocol,
    val reasoningState: AiReasoningState,
    val reasoningTokens: Int?,
    val inputTokens: Int?,
    val outputTokens: Int?,
    val estimatedCost: Double?,
    val executionNote: String,
    val createdAtEpochMs: Long,
    val latencyMs: Long,
    val responseId: String,
    val forecastHash: String,
    val previousHash: String,
    val actualNumber: Int?,
    val top6Hit: Boolean?,
    val top7Hit: Boolean?,
    val brierScore: Double?,
    val logLoss: Double?,
    val actualRank: Int?,
)

data class AiLiveAudit(
    val settled: Int = 0,
    val targetPeriods: Int = 0,
    val top6Hits: Int = 0,
    val top7Hits: Int = 0,
) {
    val top6Rate: Double get() = if (settled == 0) 0.0 else top6Hits.toDouble() / settled
    val top7Rate: Double get() = if (settled == 0) 0.0 else top7Hits.toDouble() / settled
}

data class AiProfileAudit(
    val profileId: String,
    val profileName: String,
    val model: String,
    val analysisMode: AiAnalysisMode,
    val reasoningMode: AiReasoningMode,
    val reasoningProtocol: AiReasoningProtocol,
    val settled: Int,
    val top6Hits: Int,
    val top7Hits: Int,
    val meanBrierScore: Double?,
    val meanLogLoss: Double?,
    val meanActualRank: Double?,
    val meanLatencyMs: Double? = null,
    val meanInputTokens: Double? = null,
    val meanOutputTokens: Double? = null,
    val meanEstimatedCost: Double? = null,
    val recent20Top6Rate: Double? = null,
    val recent50Top6Rate: Double? = null,
    val recent100Top6Rate: Double? = null,
) {
    val top6Rate: Double get() = if (settled == 0) 0.0 else top6Hits.toDouble() / settled
    val top7Rate: Double get() = if (settled == 0) 0.0 else top7Hits.toDouble() / settled
    val top6Lift: Double get() = top6Rate - 0.60
    val forwardWeight: Double
        get() {
            if (settled < 100) return 1.0
            val lower = wilsonLower(top6Hits, settled)
            if (lower <= 0.60) return 0.25
            val lossQuality = (1.0 - ((meanLogLoss ?: 2.302585) / 2.302585)).coerceIn(0.0, 1.0)
            return (1.0 + (lower - 0.60) * 12.0 + lossQuality).coerceIn(0.25, 3.0)
        }

    private fun wilsonLower(hits: Int, total: Int): Double {
        if (total <= 0) return 0.0
        val z = 1.959963984540054
        val p = hits.toDouble() / total
        val denominator = 1.0 + z * z / total
        val center = p + z * z / (2.0 * total)
        val margin = z * kotlin.math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
        return ((center - margin) / denominator).coerceIn(0.0, 1.0)
    }
}

data class AiConsensusRecord(
    val id: Long,
    val lottery: LotteryType,
    val targetPeriod: String,
    val trainedThroughPeriod: String,
    val position: Int,
    val top6: List<Int>,
    val top7: List<Int>,
    val probabilities: List<Double>,
    val confidenceMargin: Double,
    val supportingProfiles: Int,
    val totalProfiles: Int,
    val createdAtEpochMs: Long,
    val consensusHash: String,
    val previousHash: String,
    val actualNumber: Int?,
    val top6Hit: Boolean?,
    val top7Hit: Boolean?,
    val brierScore: Double?,
    val logLoss: Double?,
    val actualRank: Int?,
)

data class AiConsensusAudit(
    val settled: Int = 0,
    val top6Hits: Int = 0,
    val top7Hits: Int = 0,
) {
    val top6Rate: Double get() = if (settled == 0) 0.0 else top6Hits.toDouble() / settled
    val top7Rate: Double get() = if (settled == 0) 0.0 else top7Hits.toDouble() / settled
}

class SecureAiConfigStore(context: Context) {
    private val preferences = context.getSharedPreferences("tianji-ai-config", Context.MODE_PRIVATE)

    fun loadAll(): List<AiConfig> {
        val encoded = preferences.getString("profiles", "").orEmpty()
        if (encoded.isNotBlank()) {
            return runCatching {
                val array = JSONArray(encoded)
                buildList {
                    for (index in 0 until array.length()) {
                        val item = array.optJSONObject(index) ?: continue
                        val historyMode = runCatching {
                            AiAnalysisMode.valueOf(item.optString("analysis_mode"))
                        }.getOrDefault(AiAnalysisMode.FAST)
                        add(
                            AiConfig(
                                id = item.optString("id").ifBlank { UUID.randomUUID().toString() },
                                name = item.optString("name"),
                                provider = runCatching {
                                    AiProvider.valueOf(item.optString("provider"))
                                }.getOrDefault(AiProvider.COMPATIBLE),
                                endpoint = item.optString("endpoint"),
                                model = item.optString("model"),
                                apiKey = decrypt(item.optString("api_key")),
                                analysisMode = historyMode,
                                reasoningMode = runCatching {
                                    AiReasoningMode.valueOf(item.optString("reasoning_mode"))
                                }.getOrDefault(
                                    if (historyMode == AiAnalysisMode.DEEP) AiReasoningMode.HIGH else AiReasoningMode.LOW,
                                ),
                                reasoningProtocol = runCatching {
                                    AiReasoningProtocol.valueOf(item.optString("reasoning_protocol"))
                                }.getOrDefault(AiReasoningProtocol.AUTO),
                                inputPricePerMillion = item.optNullableDouble("input_price_per_million"),
                                outputPricePerMillion = item.optNullableDouble("output_price_per_million"),
                                capability = item.optJSONObject("capability")?.toCapabilitySnapshot(),
                            ),
                        )
                    }
                }
            }.getOrDefault(emptyList())
        }
        val legacy = AiConfig(
            id = UUID.randomUUID().toString(),
            provider = runCatching {
                AiProvider.valueOf(preferences.getString("provider", AiProvider.DEEPSEEK.name).orEmpty())
            }.getOrDefault(AiProvider.DEEPSEEK),
            endpoint = preferences.getString("endpoint", "") ?: "",
            model = preferences.getString("model", "") ?: "",
            apiKey = decrypt(preferences.getString("api_key", "") ?: ""),
        )
        return if (legacy.endpoint.isNotBlank() || legacy.model.isNotBlank() || legacy.apiKey.isNotBlank()) {
            listOf(legacy).also(::saveAll)
        } else emptyList()
    }

    fun saveAll(configs: List<AiConfig>) {
        val profiles = JSONArray(
            configs.map { config ->
                JSONObject()
                    .put("id", config.id)
                    .put("name", config.name.trim())
                    .put("provider", config.provider.name)
                    .put("endpoint", config.endpoint.trim())
                    .put("model", config.model.trim())
                    .put("api_key", encrypt(config.apiKey.trim()))
                    .put("analysis_mode", config.analysisMode.name)
                    .put("reasoning_mode", config.reasoningMode.name)
                    .put("reasoning_protocol", config.reasoningProtocol.name)
                    .put("input_price_per_million", config.inputPricePerMillion ?: JSONObject.NULL)
                    .put("output_price_per_million", config.outputPricePerMillion ?: JSONObject.NULL)
                    .put(
                        "capability",
                        config.capability?.let { capability ->
                            JSONObject()
                                .put("structured_output", capability.structuredOutput)
                                .put("reasoning_control", capability.reasoningControl)
                                .put("reasoning_verified", capability.reasoningVerified)
                                .put("usage_returned", capability.usageReturned)
                                .put("protocol", capability.protocol.name)
                                .put("latency_ms", capability.latencyMs)
                                .put("checked_at", capability.checkedAtEpochMs)
                                .put("message", capability.message)
                        } ?: JSONObject.NULL,
                    )
            },
        )
        preferences.edit {
            putString("profiles", profiles.toString())
            remove("provider")
            remove("endpoint")
            remove("model")
            remove("api_key")
        }
    }

    private fun encrypt(value: String): String {
        if (value.isBlank()) return ""
        return runCatching {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.ENCRYPT_MODE, secretKey())
            val encrypted = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
            Base64.encodeToString(cipher.iv + encrypted, Base64.NO_WRAP)
        }.getOrDefault("")
    }

    private fun decrypt(value: String): String {
        if (value.isBlank()) return ""
        return runCatching {
            val payload = Base64.decode(value, Base64.NO_WRAP)
            require(payload.size > IV_SIZE)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(
                Cipher.DECRYPT_MODE,
                secretKey(),
                GCMParameterSpec(128, payload.copyOfRange(0, IV_SIZE)),
            )
            String(cipher.doFinal(payload.copyOfRange(IV_SIZE, payload.size)), Charsets.UTF_8)
        }.getOrDefault("")
    }

    private fun secretKey(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }

    private fun JSONObject.optNullableDouble(key: String): Double? =
        if (has(key) && !isNull(key)) optDouble(key).takeIf(Double::isFinite) else null

    private fun JSONObject.toCapabilitySnapshot(): AiCapabilitySnapshot = AiCapabilitySnapshot(
        structuredOutput = optBoolean("structured_output"),
        reasoningControl = optBoolean("reasoning_control"),
        reasoningVerified = optBoolean("reasoning_verified"),
        usageReturned = optBoolean("usage_returned"),
        protocol = runCatching { AiReasoningProtocol.valueOf(optString("protocol")) }
            .getOrDefault(AiReasoningProtocol.AUTO),
        latencyMs = optLong("latency_ms"),
        checkedAtEpochMs = optLong("checked_at"),
        message = optString("message"),
    )

    private companion object {
        const val KEY_ALIAS = "tianji_ai_api_key_v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_SIZE = 12
    }
}

class RemoteAiAnalyzer {
    private val activeConnections = ConcurrentHashMap.newKeySet<HttpURLConnection>()
    private val profileConnections = ConcurrentHashMap<String, MutableSet<HttpURLConnection>>()

    fun cancelActiveRequests(profileId: String? = null) {
        val targets = if (profileId == null) activeConnections.toList()
        else profileConnections[profileId]?.toList().orEmpty()
        targets.forEach(HttpURLConnection::disconnect)
        activeConnections.removeAll(targets.toSet())
        if (profileId == null) profileConnections.clear() else profileConnections.remove(profileId)
    }

    fun listModels(config: AiConfig): AiModelCatalog {
        require(config.endpoint.startsWith("https://") && config.apiKey.isNotBlank()) {
            "请先填写 HTTPS 接口和 API Key"
        }
        val endpoint = URL(modelsEndpoint(config.endpoint))
        val started = System.currentTimeMillis()
        val connection = endpoint.openConnection() as HttpURLConnection
        activeConnections += connection
        profileConnections.computeIfAbsent(config.id) { ConcurrentHashMap.newKeySet() } += connection
        val response = try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 12_000
            connection.readTimeout = 20_000
            connection.useCaches = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Authorization", "Bearer ${config.apiKey.trim()}")
            val code = connection.responseCode
            val body = (if (code in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (code !in 200..299) error("模型列表 HTTP $code：${body.take(160)}")
            JSONObject(body)
        } catch (_: SocketTimeoutException) {
            error("读取模型列表超过 20 秒，请检查网络或接口地址")
        } finally {
            activeConnections -= connection
            profileConnections[config.id]?.remove(connection)
            connection.disconnect()
        }
        val data = response.optJSONArray("data") ?: error("接口没有返回模型列表")
        val models = buildList {
            for (index in 0 until data.length()) {
                val id = data.optJSONObject(index)?.optString("id").orEmpty().trim()
                if (id.isNotBlank() && isLikelyTextModel(id)) add(id)
            }
        }.distinct().sorted()
        require(models.isNotEmpty()) { "没有找到可用于文本分析的模型" }
        return AiModelCatalog(models, System.currentTimeMillis() - started)
    }

    fun testConnection(config: AiConfig): AiConnectionProbe {
        require(config.isComplete) { "AI 配置不完整" }
        val baseDecision = AiReasoningEngine.resolve(config, config.reasoningMode)
        val baseResponse = post(
            config = config,
            temperature = 0.0,
            systemPrompt = "你正在执行结构化输出与真实思考能力测试。完成思考后只输出请求的JSON。",
            userPrompt = "能力测试：先完成思考，再返回position=7与号码1至10的非负scores；每项至少保留6位小数。",
            reasoningDecision = baseDecision,
            readTimeoutMs = if (baseDecision.expectsReasoning) 90_000 else 30_000,
            jsonOutput = true,
            explainOutput = false,
        )
        baseResponse.json.requireCompletedResponse()
        val baseContent = baseResponse.json.extractContent()
        val baseJson = JSONObject(stripCodeFence(baseContent))
        require(baseJson.optInt("position") in 1..10) { "接口响应了，但结构化名次无效" }
        AiProbabilityVector.requireForecastable(baseJson.doubleList("scores"))

        val highDecision = AiReasoningEngine.resolve(config, AiReasoningMode.HIGH)
        val reasoningResponse = if (highDecision.supported && !baseDecision.expectsReasoning) runCatching {
            post(
                config = config,
                temperature = 0.0,
                systemPrompt = "你正在执行推理与结构化输出能力测试。只输出请求的JSON。",
                userPrompt = "能力测试：请原样返回position=7，并为号码1至10各输出一个非负scores原始评分；每项至少保留6位小数，不要四舍五入成并列。",
                reasoningDecision = highDecision,
                readTimeoutMs = if (highDecision.protocol == AiReasoningProtocol.DEEPSEEK) 180_000 else 90_000,
                jsonOutput = true,
                explainOutput = false,
            ).also { response ->
                response.json.requireCompletedResponse()
                val json = JSONObject(stripCodeFence(response.json.extractContent()))
                AiProbabilityVector.requireForecastable(json.doubleList("scores"))
            }
        }.getOrNull() else null
        val evidenceResponse = reasoningResponse ?: baseResponse
        val usage = evidenceResponse.json.extractUsage()
        val reasoningVerified = evidenceResponse.json.extractReasoningContent().isNotBlank() ||
            (usage.reasoningTokens ?: 0) > 0
        val capability = AiCapabilitySnapshot(
            structuredOutput = true,
            reasoningControl = baseDecision.sendControl || reasoningResponse != null,
            reasoningVerified = reasoningVerified,
            usageReturned = usage.inputTokens != null || usage.outputTokens != null,
            protocol = highDecision.protocol,
            latencyMs = baseResponse.latencyMs + (reasoningResponse?.latencyMs ?: 0L),
            checkedAtEpochMs = System.currentTimeMillis(),
            message = buildString {
                append("结构化输出通过")
                when {
                    !highDecision.supported -> append(" · 未检测到可控推理")
                    reasoningVerified -> append(" · 真实思考已验证")
                    reasoningResponse == null && !baseDecision.sendControl -> append(" · 使用模型默认思考")
                    reasoningResponse == null -> append(" · 当前思考请求可用")
                    else -> append(" · 推理请求通过但无用量证明")
                }
            },
        )
        return AiConnectionProbe(
            latencyMs = capability.latencyMs,
            responseId = evidenceResponse.json.optString("id"),
            capability = capability,
        )
    }

    fun analyze(
        config: AiConfig,
        snapshot: DrawSnapshot,
        report: ForecastReport,
        onProgress: (String, Long) -> Unit = { _, _ -> },
    ): AiForecast {
        require(config.isComplete) { "请先在数据页填写 HTTPS 接口、模型名和 API Key" }
        val historyLimit = config.analysisMode.historyLimit
        val userPrompt = analysisPayload(snapshot, report, historyLimit).toString()
        val started = System.currentTimeMillis()
        val primaryDecision = AiReasoningEngine.resolveForecast(config)

        fun execute(
            reasoningDecision: AiReasoningDecision,
            readTimeoutMs: Int,
            executionNote: String,
            fallback: Boolean = false,
            prompt: String = userPrompt,
        ): AiForecast {
            var response = post(
                config = config,
                temperature = if (reasoningDecision.expectsReasoning) 0.1 else 0.2,
                systemPrompt = SYSTEM_PROMPT,
                userPrompt = prompt,
                reasoningDecision = reasoningDecision,
                readTimeoutMs = readTimeoutMs,
                jsonOutput = true,
                explainOutput = false,
                streamResponse = true,
                onProgress = onProgress,
            )
            var payload = response.json.extractCompleteForecastPayload()
            var continuedConversation = false
            if (
                payload == null &&
                (response.json.extractContent().isNotBlank() ||
                    response.json.extractReasoningContent().isNotBlank())
            ) {
                continuedConversation = true
                onProgress(
                    "首次推理已完成，正在沿用同一对话补全最终 JSON",
                    System.currentTimeMillis() - started,
                )
                response = runCatching {
                    post(
                        config = config,
                        temperature = if (reasoningDecision.expectsReasoning) 0.1 else 0.2,
                        systemPrompt = SYSTEM_PROMPT,
                        userPrompt = prompt,
                        reasoningDecision = reasoningDecision,
                        readTimeoutMs = 8_000,
                        jsonOutput = true,
                        explainOutput = false,
                        streamResponse = true,
                        onProgress = onProgress,
                        previousAssistantContent = response.json.extractContent(),
                        previousReasoningContent = response.json.extractReasoningContent(),
                        followUpPrompt = FINALIZE_JSON_PROMPT,
                    )
                }.getOrElse { cause ->
                    throw AiConversationFinalizationException(
                        "首次推理已完成，但继续对话补全结果失败：${cause.message.orEmpty().take(100)}",
                        cause,
                    )
                }
                payload = response.json.extractCompleteForecastPayload()
                if (payload == null) {
                    throw AiConversationFinalizationException(
                        "首次推理与继续对话均未返回完整的 position 和 10 项 scores",
                    )
                }
            }
            response.json.requireCompletedResponse()
            val usage = response.json.extractUsage()
            val hasReasoningContent = response.json.extractReasoningContent().isNotBlank()
            val content = payload ?: response.json.extractContent()
            require(content.isNotBlank()) {
                if (response.json.extractReasoningContent().isNotBlank()) {
                    "模型只返回了思考过程，没有生成最终 JSON"
                } else {
                    "模型返回了空内容"
                }
            }
            onProgress(
                "预测核心已完整，正在本机校验概率矩阵并生成六码/七码",
                System.currentTimeMillis() - started,
            )
            return parseForecastContent(
                content = content,
                profileId = config.id,
                profileName = config.displayName,
                targetPeriod = report.targetPeriod,
                modelLabel = "${config.provider.label} · ${config.model.trim()}",
                analysisMode = config.analysisMode,
                reasoningMode = config.reasoningMode,
                reasoningProtocol = reasoningDecision.protocol,
                reasoningState = AiReasoningEngine.stateFor(
                    reasoningDecision, usage, hasReasoningContent, fallback,
                ),
                tokenUsage = usage,
                estimatedCost = estimateCost(config, usage),
                executionNote = buildString {
                    append(executionNote)
                    if (continuedConversation) append(" · 同一对话补全结果")
                    response.json.streamPhaseSummary().takeIf(String::isNotBlank)?.let {
                        append(" · $it")
                    }
                    append(" · ${response.tokenBudgetLabel}")
                },
                history = snapshot.history,
                latencyMs = System.currentTimeMillis() - started,
                responseId = response.json.optString("id"),
            )
        }

        val primary = runCatching {
            execute(
                reasoningDecision = primaryDecision,
                readTimeoutMs = if (config.analysisMode == AiAnalysisMode.DEEP) 40_000 else 30_000,
                executionNote = "${config.analysisMode.label} · ${primaryDecision.displayLabel} · 核心矩阵优先",
            )
        }
        primary.getOrNull()?.let { return it }
        val firstFailure = primary.exceptionOrNull() ?: error("AI 分析失败")
        val reasoningControlFailure = isReasoningControlFailure(firstFailure, primaryDecision)
        if (!reasoningControlFailure) {
            // Partial output is already continued inside execute(). Transport timeouts, broken
            // streams and invalid model output must remain visible instead of silently starting a
            // second full 60/120-period analysis.
            throw firstFailure
        }
        onProgress(
            "接口拒绝显式思考参数；确认尚未进入模型推理，正在仅一次切换为模型默认思考协议",
            System.currentTimeMillis() - started,
        )
        val defaultThinkingDecision = primaryDecision.copy(
            sendControl = false,
            enableThinking = true,
            effort = null,
            displayLabel = "${primaryDecision.protocol.label} · 模型默认思考",
        )
        return runCatching {
            execute(
                reasoningDecision = defaultThinkingDecision,
                readTimeoutMs = 30_000,
                executionNote = "${config.analysisMode.label} · 限时参数兼容回退",
                fallback = true,
                prompt = userPrompt,
            )
        }.getOrElse { retryFailure ->
            error(
                "接口拒绝显式思考参数，切换模型默认思考后仍失败：" +
                    retryFailure.message.orEmpty().take(140),
            )
        }
    }

    private fun post(
        config: AiConfig,
        temperature: Double,
        systemPrompt: String,
        userPrompt: String,
        reasoningDecision: AiReasoningDecision,
        readTimeoutMs: Int,
        jsonOutput: Boolean,
        explainOutput: Boolean,
        streamResponse: Boolean = false,
        onProgress: (String, Long) -> Unit = { _, _ -> },
        previousAssistantContent: String = "",
        previousReasoningContent: String = "",
        followUpPrompt: String = "",
    ): RemoteResponse {
        val endpoint = URL(config.endpoint.trim())
        require(endpoint.protocol == "https") { "AI 接口必须使用 HTTPS" }
        val responsesApi = endpoint.path.trimEnd('/').endsWith("/responses")
        var useStreaming = streamResponse && !responsesApi
        val tokenBudget = AiTokenPolicy.resolve(config, responsesApi)

        fun conversationMessages(includeReasoning: Boolean): JSONArray = JSONArray().apply {
            put(JSONObject().put("role", "system").put("content", systemPrompt))
            put(JSONObject().put("role", "user").put("content", userPrompt))
            if (followUpPrompt.isNotBlank()) {
                val assistant = JSONObject()
                    .put("role", "assistant")
                    .put("content", previousAssistantContent)
                if (
                    includeReasoning &&
                    reasoningDecision.protocol == AiReasoningProtocol.DEEPSEEK &&
                    previousReasoningContent.isNotBlank()
                ) {
                    assistant.put("reasoning_content", previousReasoningContent)
                }
                put(assistant)
                put(JSONObject().put("role", "user").put("content", followUpPrompt))
            }
        }

        val request = JSONObject().apply {
            put("model", config.model.trim())
            put("stream", useStreaming)
            if (useStreaming && config.provider != AiProvider.COMPATIBLE) {
                put("stream_options", JSONObject().put("include_usage", true))
            }
            tokenBudget.parameter?.let { parameter -> put(parameter, tokenBudget.value) }
            if (
                !reasoningDecision.expectsReasoning &&
                reasoningDecision.protocol != AiReasoningProtocol.OPENAI
            ) put("temperature", temperature)
            if (responsesApi) {
                put("store", false)
                put(
                    "input",
                    conversationMessages(includeReasoning = false),
                )
                if (jsonOutput) {
                    put(
                        "text",
                        JSONObject().put(
                            "format",
                            forecastJsonSchema(responsesApi = true, explainOutput = explainOutput),
                        ),
                    )
                }
            } else {
                if (jsonOutput && config.provider == AiProvider.OPENAI) {
                    put(
                        "response_format",
                        forecastJsonSchema(responsesApi = false, explainOutput = explainOutput),
                    )
                } else if (jsonOutput && config.provider != AiProvider.COMPATIBLE) {
                    put("response_format", JSONObject().put("type", "json_object"))
                }
                put(
                    "messages",
                    conversationMessages(includeReasoning = true),
                )
            }
            applyReasoning(reasoningDecision, responsesApi)
        }
        val started = System.currentTimeMillis()
        for (attempt in 0..1) {
            onProgress(
                if (attempt == 0) "正在建立 HTTPS 连接" else "正在进行网络层重连 1/1",
                System.currentTimeMillis() - started,
            )
            val connection = endpoint.openConnection() as HttpURLConnection
            activeConnections += connection
            profileConnections.computeIfAbsent(config.id) { ConcurrentHashMap.newKeySet() } += connection
            var retryDelayMs: Long? = null
            try {
                connection.requestMethod = "POST"
                connection.connectTimeout = 12_000
                connection.readTimeout = readTimeoutMs
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.setRequestProperty("Accept", if (useStreaming) "text/event-stream" else "application/json")
                connection.setRequestProperty("Authorization", "Bearer ${config.apiKey.trim()}")
                connection.outputStream.use { it.write(request.toString().toByteArray(Charsets.UTF_8)) }
                onProgress("请求已发送，等待服务器接受", System.currentTimeMillis() - started)
                val code = connection.responseCode
                if (code in 200..299) {
                    onProgress("已连接模型，等待推理输出", System.currentTimeMillis() - started)
                    val json = connection.inputStream
                        ?.bufferedReader(Charsets.UTF_8)
                        ?.use { reader ->
                            if (useStreaming) {
                                readChatStream(
                                    reader = reader,
                                    startedAtMs = started,
                                    hardDeadlineMs = readTimeoutMs.toLong(),
                                    onProgress = onProgress,
                                )
                            } else {
                                JSONObject(reader.readText())
                            }
                        } ?: error("AI 接口返回空响应")
                    onProgress("模型响应已结束，正在本机校验 JSON", System.currentTimeMillis() - started)
                    return RemoteResponse(
                        json = json,
                        latencyMs = System.currentTimeMillis() - started,
                        tokenBudgetLabel = tokenBudget.label,
                    )
                }
                val body = connection.errorStream
                    ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                if (
                    attempt == 0 && useStreaming && code in listOf(400, 404, 405, 422) &&
                    (body.contains("stream", ignoreCase = true) ||
                        body.contains("stream_options", ignoreCase = true))
                ) {
                    useStreaming = false
                    request.put("stream", false)
                    request.remove("stream_options")
                    retryDelayMs = 0L
                    onProgress("接口不支持流式返回，已切换普通对话响应", System.currentTimeMillis() - started)
                } else if (attempt == 0 && code == 429) {
                    val retrySeconds = connection.getHeaderField("Retry-After")?.trim()?.toLongOrNull()
                        ?.coerceIn(1L, 10L) ?: 2L
                    retryDelayMs = retrySeconds * 1_000L
                    onProgress(
                        "供应商限流，${retrySeconds}秒后进行一次网络层重连",
                        System.currentTimeMillis() - started,
                    )
                } else if (attempt == 0 && code in 500..599) {
                    retryDelayMs = 500L
                    onProgress(
                        "供应商 HTTP $code，正在进行一次网络层重连",
                        System.currentTimeMillis() - started,
                    )
                } else {
                    error("AI 接口 HTTP $code：${body.take(160)}")
                }
            } catch (_: SocketTimeoutException) {
                onProgress(
                    "等待模型输出超时，本次请求已停止，不会自动重新预测",
                    System.currentTimeMillis() - started,
                )
                error("模型响应超过 ${readTimeoutMs / 1_000} 秒；本次已停止，未自动重新预测")
            } catch (cause: EOFException) {
                val message = transportFailureMessage(cause)
                onProgress("$message，本次未自动重新预测", System.currentTimeMillis() - started)
                error("$message；本次未自动重新预测")
            } catch (cause: SocketException) {
                val message = transportFailureMessage(cause)
                onProgress("$message，本次未自动重新预测", System.currentTimeMillis() - started)
                error("$message；本次未自动重新预测")
            } catch (cause: IOException) {
                val message = transportFailureMessage(cause)
                onProgress("$message，本次未自动重新预测", System.currentTimeMillis() - started)
                error("$message；本次未自动重新预测")
            } finally {
                activeConnections -= connection
                profileConnections[config.id]?.remove(connection)
                connection.disconnect()
            }
            retryDelayMs?.let(Thread::sleep)
        }
        error("AI 接口重试后仍未返回")
    }


    private fun readChatStream(
        reader: java.io.BufferedReader,
        startedAtMs: Long,
        hardDeadlineMs: Long,
        onProgress: (String, Long) -> Unit,
    ): JSONObject {
        val content = StringBuilder()
        val reasoning = StringBuilder()
        val plainBody = StringBuilder()
        var responseId = ""
        var finishReason = ""
        var usage: JSONObject? = null
        var lastProgressAt = 0L
        var firstReasoningMs = -1L
        var firstContentMs = -1L
        var hardDeadlineReached = false

        fun report(message: String) {
            val now = System.currentTimeMillis()
            if (now - lastProgressAt >= 1_000L) {
                lastProgressAt = now
                onProgress(message, now - startedAtMs)
            }
        }

        var streamFailure: IOException? = null
        try {
            reader.forEachLine { rawLine ->
                if (System.currentTimeMillis() - startedAtMs >= hardDeadlineMs) {
                    throw ForecastHardDeadlineException()
                }
                val line = rawLine.trim()
                if (line.isBlank()) return@forEachLine
                if (!line.startsWith("data:")) {
                    if (line.startsWith("{")) plainBody.append(line)
                    return@forEachLine
                }
                val payload = line.removePrefix("data:").trim()
                if (payload == "[DONE]" || payload.isBlank()) return@forEachLine
                val chunk = runCatching { JSONObject(payload) }.getOrNull() ?: return@forEachLine
                responseId = chunk.optString("id").ifBlank { responseId }
                chunk.optJSONObject("usage")?.let { usage = it }
                val choice = chunk.optJSONArray("choices")?.optJSONObject(0) ?: return@forEachLine
                finishReason = choice.optString("finish_reason").ifBlank { finishReason }
                val delta = choice.optJSONObject("delta") ?: return@forEachLine
                val reasoningPart = delta.optString("reasoning_content")
                val contentPart = delta.optString("content")
                if (reasoningPart.isNotEmpty()) {
                    if (firstReasoningMs < 0L) firstReasoningMs = System.currentTimeMillis() - startedAtMs
                    reasoning.append(reasoningPart)
                    report("模型正在推理 · 已收到 ${reasoning.length} 个推理字符")
                }
                if (contentPart.isNotEmpty()) {
                    if (firstContentMs < 0L) firstContentMs = System.currentTimeMillis() - startedAtMs
                    content.append(contentPart)
                    if (AiForecastPayloadExtractor.containsForecastCore(content.toString())) {
                        report("已收到完整预测核心，立即停止等待并转入本机校验")
                        throw ForecastCoreReadyException()
                    } else {
                        report("模型正在生成结构化预测 · 已收到 ${content.length} 个结果字符")
                    }
                }
            }
        } catch (_: ForecastCoreReadyException) {
            finishReason = "tianji_core_ready"
        } catch (_: ForecastHardDeadlineException) {
            hardDeadlineReached = true
            finishReason = "tianji_hard_deadline"
            onProgress(
                "正式预测达到总时长上限，正在抢救已接收内容",
                System.currentTimeMillis() - startedAtMs,
            )
        } catch (cause: IOException) {
            streamFailure = cause
        }

        if (content.isEmpty() && reasoning.isEmpty() && plainBody.isNotEmpty()) {
            val plainJson = runCatching { JSONObject(plainBody.toString()) }.getOrElse { parseFailure ->
                streamFailure?.let { throw it }
                throw parseFailure
            }
            streamFailure?.let { failure ->
                plainJson.put("_tianji_stream_interrupted", true)
                plainJson.put("_tianji_stream_error", transportFailureMessage(failure))
                onProgress(
                    "网络连接中断，但已恢复服务器返回内容，正在本机校验",
                    System.currentTimeMillis() - startedAtMs,
                )
            }
            return plainJson
        }

        val message = JSONObject().put("content", content.toString())
        if (reasoning.isNotEmpty()) message.put("reasoning_content", reasoning.toString())
        val result = JSONObject()
            .put("id", responseId)
            .put(
                "choices",
                JSONArray().put(
                    JSONObject()
                        .put("index", 0)
                        .put(
                            "finish_reason",
                            finishReason.ifBlank {
                                if (streamFailure == null) "stop" else "network_interrupted"
                            },
                        )
                        .put("message", message),
                ),
            )
            .apply {
                usage?.let { put("usage", it) }
                put("_tianji_first_reasoning_ms", firstReasoningMs)
                put("_tianji_first_content_ms", firstContentMs)
                put("_tianji_stream_finished_ms", System.currentTimeMillis() - startedAtMs)
                put("_tianji_hard_deadline", hardDeadlineReached)
            }

        if (hardDeadlineReached && content.isEmpty() && reasoning.isEmpty()) {
            error("正式预测达到总时长上限，模型尚未生成可补全内容")
        }

        streamFailure?.let { failure ->
            if (content.isEmpty() && reasoning.isEmpty()) throw failure
            result.put("_tianji_stream_interrupted", true)
            result.put("_tianji_stream_error", transportFailureMessage(failure))
            onProgress(
                if (result.hasCompleteForecastContent()) {
                    "网络连接中断，但已恢复完整预测核心，正在本机校验"
                } else {
                    "网络连接中断，已保留已接收内容，正在沿用同一对话补全结果"
                },
                System.currentTimeMillis() - startedAtMs,
            )
        }
        return result
    }

    private fun transportFailureMessage(cause: Throwable): String {
        val message = cause.message.orEmpty().lowercase()
        return when {
            cause is SocketTimeoutException -> "等待模型输出超时"
            cause is EOFException -> "模型连接提前结束"
            cause is SocketException && listOf(
                "software caused connection abort",
                "connection reset",
                "broken pipe",
                "socket closed",
            ).any(message::contains) -> "网络连接被系统、代理或服务器中断"
            cause is SocketException -> "网络连接异常中断"
            cause is IOException -> "网络连接在模型输出过程中中断"
            else -> "AI 网络请求失败"
        }
    }

    private fun JSONObject.streamPhaseSummary(): String {
        val firstReasoning = optLong("_tianji_first_reasoning_ms", -1L)
        val firstContent = optLong("_tianji_first_content_ms", -1L)
        val finished = optLong("_tianji_stream_finished_ms", -1L)
        if (finished < 0L) return ""
        fun seconds(value: Long): String = String.format(java.util.Locale.US, "%.1fs", value / 1000.0)
        val timing = when {
            firstReasoning >= 0L && firstContent >= firstReasoning ->
                "首个推理 ${seconds(firstReasoning)} · 推理阶段 ${seconds(firstContent - firstReasoning)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            firstContent >= 0L ->
                "首个结果 ${seconds(firstContent)} · 结果阶段 ${seconds((finished - firstContent).coerceAtLeast(0L))}"
            else -> "响应总耗时 ${seconds(finished)}"
        }
        return if (optBoolean("_tianji_stream_interrupted")) "$timing · 断流后已恢复" else timing
    }

    private fun JSONObject.extractContent(): String = optJSONArray("choices")
            ?.optJSONObject(0)
            ?.optJSONObject("message")
            ?.optString("content")
            ?.takeIf(String::isNotBlank)
            ?: optString("output_text").takeIf(String::isNotBlank)
            ?: run {
                val output = optJSONArray("output") ?: return@run null
                buildList {
                    for (index in 0 until output.length()) {
                        val content = output.optJSONObject(index)?.optJSONArray("content") ?: continue
                        for (contentIndex in 0 until content.length()) {
                            content.optJSONObject(contentIndex)?.optString("text")
                                ?.takeIf(String::isNotBlank)?.let(::add)
                        }
                    }
                }.joinToString("\n").takeIf(String::isNotBlank)
            }
            ?: ""

    private fun JSONObject.extractReasoningContent(): String = optJSONArray("choices")
        ?.optJSONObject(0)
        ?.optJSONObject("message")
        ?.optString("reasoning_content")
        .orEmpty()

    private fun JSONObject.extractUsage(): AiTokenUsage {
        val usage = optJSONObject("usage") ?: return AiTokenUsage()
        val reasoning = usage.optJSONObject("completion_tokens_details")?.optInt("reasoning_tokens", -1)
            ?.takeIf { it >= 0 }
            ?: usage.optJSONObject("output_tokens_details")?.optInt("reasoning_tokens", -1)
                ?.takeIf { it >= 0 }
        return AiTokenUsage(
            inputTokens = usage.firstPositiveInt("prompt_tokens", "input_tokens"),
            outputTokens = usage.firstPositiveInt("completion_tokens", "output_tokens"),
            reasoningTokens = reasoning,
        )
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

    private fun forecastJsonSchema(responsesApi: Boolean, explainOutput: Boolean): JSONObject {
        val scoreArray = JSONObject()
            .put("type", "array")
            .put("items", JSONObject().put("type", "number").put("minimum", 0))
            .put("minItems", 10)
            .put("maxItems", 10)
        val properties = JSONObject()
            .put(
                "position",
                JSONObject().put("type", "integer").put("minimum", 1).put("maximum", 10),
            )
            .put("scores", scoreArray)
        val required = mutableListOf("position", "scores")
        if (explainOutput) {
            val factorWeights = JSONObject()
                .put("type", "array")
                .put("items", JSONObject().put("type", "number").put("minimum", 0).put("maximum", 1))
                .put("minItems", 5)
                .put("maxItems", 5)
            properties
                .put("factor_weights", factorWeights)
                .put(
                    "calculation_summary",
                    JSONObject().put("type", "string").put("maxLength", 220),
                )
                .put(
                    "position_reason",
                    JSONObject().put("type", "string").put("maxLength", 180),
                )
                .put(
                    "candidate_reason",
                    JSONObject().put("type", "string").put("maxLength", 220),
                )
                .put(
                    "uncertainty",
                    JSONObject().put("type", "string").put("maxLength", 160),
                )
            required += listOf(
                "factor_weights",
                "calculation_summary",
                "position_reason",
                "candidate_reason",
                "uncertainty",
            )
        }
        val schema = JSONObject()
            .put("type", "object")
            .put("properties", properties)
            .put("required", JSONArray(required))
            .put("additionalProperties", false)
        return if (responsesApi) {
            JSONObject()
                .put("type", "json_schema")
                .put("name", "tianji_forecast")
                .put("strict", true)
                .put("schema", schema)
        } else {
            JSONObject()
                .put("type", "json_schema")
                .put(
                    "json_schema",
                    JSONObject()
                        .put("name", "tianji_forecast")
                        .put("strict", true)
                        .put("schema", schema),
                )
        }
    }

    private fun JSONObject.extractCompleteForecastPayload(): String? {
        val sources = listOf(extractContent(), extractReasoningContent())
        for (source in sources) {
            for (candidate in AiForecastPayloadExtractor.balancedJsonObjects(source)) {
                val valid = runCatching { JSONObject(candidate).hasForecastCore() }.getOrDefault(false)
                if (valid) return candidate
            }
        }
        for (source in sources) {
            AiForecastPayloadExtractor.salvageCoreJson(source)?.let { return it }
        }
        return null
    }

    private fun JSONObject.hasForecastCore(): Boolean {
        val position = optInt("position", 0)
        val scores = optJSONArray("scores") ?: return false
        return position in 1..10 && scores.length() == 10 && (0 until scores.length()).all { index ->
            val score = scores.optDouble(index, Double.NaN)
            score.isFinite() && score >= 0.0
        }
    }

    private fun JSONObject.hasCompleteForecastContent(): Boolean =
        extractCompleteForecastPayload() != null

    private fun JSONObject.requireCompletedResponse() {
        val completeForecastContent = hasCompleteForecastContent()
        val status = optString("status")
        if (status == "incomplete" && !completeForecastContent) {
            val reason = optJSONObject("incomplete_details")?.optString("reason").orEmpty()
            error("模型输出不完整：${reason.ifBlank { "达到输出上限" }}")
        }
        val choice = optJSONArray("choices")?.optJSONObject(0)
        when (choice?.optString("finish_reason")) {
            "length" -> if (!completeForecastContent) error("模型达到输出上限，没有生成完整 JSON")
            "content_filter" -> error("模型输出被内容过滤器中断")
        }
        val refusal = choice?.optJSONObject("message")?.optString("refusal").orEmpty()
        require(refusal.isBlank()) { "模型拒绝了本次分析：${refusal.take(100)}" }
        val output = optJSONArray("output")
        if (output != null) {
            for (index in 0 until output.length()) {
                val contents = output.optJSONObject(index)?.optJSONArray("content") ?: continue
                for (contentIndex in 0 until contents.length()) {
                    val item = contents.optJSONObject(contentIndex) ?: continue
                    if (item.optString("type") == "refusal") {
                        error("模型拒绝了本次分析：${item.optString("refusal").take(100)}")
                    }
                }
            }
        }
    }

    private fun JSONObject.firstPositiveInt(vararg keys: String): Int? {
        for (key in keys) {
            val value = optInt(key, -1)
            if (value >= 0) return value
        }
        return null
    }

    internal fun parseForecastContent(
        content: String,
        profileId: String,
        profileName: String,
        targetPeriod: String,
        modelLabel: String,
        analysisMode: AiAnalysisMode,
        reasoningMode: AiReasoningMode,
        reasoningProtocol: AiReasoningProtocol,
        reasoningState: AiReasoningState,
        tokenUsage: AiTokenUsage,
        estimatedCost: Double?,
        executionNote: String,
        history: List<com.tianji.probabilitylab.nativev4.model.Draw>,
        latencyMs: Long,
        responseId: String,
    ): AiForecast {
        val json = JSONObject(stripCodeFence(content))
        val position = json.optInt("position", 0)
        require(position in 1..10) { "AI 返回的名次无效" }
        val probabilities = AiProbabilityVector.requireForecastable(json.doubleList("scores"))
        val ranking = AiProbabilityVector.ranking(probabilities)
        val top6 = ranking.take(6)
        val top7 = ranking.take(7)
        val boundaryMargin = probabilities[ranking[5] - 1] - probabilities[ranking[6] - 1]
        val lowBoundarySeparation = boundaryMargin < 0.002
        AiOutputValidator.requireValidCandidateSets(top6, top7)
        val entropy = -probabilities.sumOf { probability ->
            if (probability <= 0.0) 0.0 else probability * kotlin.math.ln(probability)
        }
        val matrixConcentration = (1.0 - entropy / kotlin.math.ln(10.0)).coerceIn(0.0, 1.0)
        val calculation = AiExplanationPolicy.concise(json.optString("calculation_summary"), 220)
        val positionEvidence = AiExplanationPolicy.concise(json.optString("position_reason"), 180)
        val candidateEvidence = AiExplanationPolicy.concise(json.optString("candidate_reason"), 220)
        val uncertainty = AiExplanationPolicy.concise(json.optString("uncertainty"), 160)
        val factorAudit = AiExplanationPolicy.auditWeights(json.doubleList("factor_weights"))
        val explanationAccepted = factorAudit.validMultiFactor && AiExplanationPolicy.isChineseExplanation(
            calculation,
            positionEvidence,
            candidateEvidence,
            uncertainty,
        )
        return AiForecast(
            profileId = profileId,
            profileName = profileName,
            targetPeriod = targetPeriod,
            position = position - 1,
            top6 = top6,
            top7 = top7,
            probabilities = probabilities,
            analysis = buildString {
                if (explanationAccepted) {
                    append("多因素权重：${factorAudit.weightSummary}")
                    append("\n计算摘要：$calculation")
                    append("\n名次依据：$positionEvidence")
                    append("\n候选依据：$candidateEvidence")
                } else {
                    append("正式预测采用限时核心矩阵；为确保开奖前完成，模型长思考与长篇说明不会阻塞结果冻结。")
                    append("\n本机复核：")
                    append(AiFactEngine.verifiedSummary(history, position - 1, top6))
                }
            }.take(1_200),
            riskNote = buildString {
                if (explanationAccepted) append("AI 不确定性：$uncertainty ")
                else append("AI 说明未通过中文多因素审计；预测矩阵仍保留并进入真实前向验证。 ")
                append("统计由本机对刚同步的开奖接口历史逐期复核；随机开奖无法保证准确率或盈利。")
                if (lowBoundarySeparation) append(" 本次第6与第7候选差距较小，候选边界稳定性偏低。")
            }.take(700),
            selfRating = matrixConcentration,
            model = modelLabel,
            analysisMode = analysisMode,
            reasoningMode = reasoningMode,
            reasoningProtocol = reasoningProtocol,
            reasoningState = reasoningState,
            reasoningTokens = tokenUsage.reasoningTokens,
            inputTokens = tokenUsage.inputTokens,
            outputTokens = tokenUsage.outputTokens,
            estimatedCost = estimatedCost,
            executionNote = executionNote,
            createdAtEpochMs = System.currentTimeMillis(),
            latencyMs = latencyMs,
            responseId = responseId,
        )
    }

    private fun analysisPayload(
        snapshot: DrawSnapshot,
        report: ForecastReport,
        historyLimit: Int,
    ): JSONObject =
        JSONObject().apply {
            put("task", "独立分析下一期候选；不得承诺必中或虚构优势")
            put(
                "independence_rule",
                "本地盲测的名次、六码、七码和概率矩阵已故意隐藏。请只根据原始历史独立分析，不要猜测或复述本地候选。",
            )
            put("lottery", snapshot.lottery.displayName)
            put("target_period", report.targetPeriod)
            put("trained_through", report.trainedThroughPeriod)
            put("local_mode", report.mode.name)
            put("analysis_window", historyLimit)
            put("verified_fact_history_size", snapshot.history.size)
            put("data_source", "fresh lottery API history fetched immediately before this analysis")
            put("history_order", "oldest_to_newest; the final item is the latest verified draw")
            put("reasoning_efficiency_rule", AiPromptCompactor.REASONING_RULE)
            put("compact_draw_format", AiPromptCompactor.FORMAT)
            put("latest_period", snapshot.latest.period)
            put("latest_numbers", JSONArray(snapshot.latest.numbers))
            put(
                "position_selection_rule",
                "必须先横向比较position 1至10的全部已核验统计，再选择证据最充分的一个名次。不得默认、照抄或偏向position=1；名次选择必须由本次数据决定。",
            )
            put(
                "multi_factor_rule",
                "禁止使用单一指标或简单的遗漏+转移未加权求和。factor_weights固定顺序为[近20期频次,近60期频次,当前遗漏,后继转移,趋势稳定性]，归一化后至少3项权重>=0.08，任何一项不得超过0.65。scores必须与这些权重和已核验统计方向一致。",
            )
            put(
                "output_rule",
                "正式预测只输出position和scores核心矩阵。不要输出思维过程、Markdown、逐期复述或额外字段；客户端会立即冻结并生成可核验说明。",
            )
            put(
                "verified_position_statistics",
                AiPromptCompactor.verifiedPositionStatistics(snapshot.history),
            )
            put(
                "verified_draws_oldest_to_newest",
                AiPromptCompactor.compactDraws(snapshot.history, minOf(historyLimit, 24)),
            )
            put(
                "required_json_schema",
                JSONObject()
                    .put("position", "1至10的整数")
                    .put("scores", "按号码1至10排列的10项非负原始评分，不得全部相同"),
            )
        }

    private fun isRetriableModelOutput(error: Throwable): Boolean {
        if (error is AiConversationFinalizationException) return false
        val message = error.message.orEmpty()
        return error is org.json.JSONException || listOf(
            "没有生成最终 JSON",
            "返回了空内容",
            "响应超过",
            "输出不完整",
            "达到输出上限",
            "AI 返回的名次无效",
            "AI 返回的六码无效",
            "AI 返回的七码无效",
            "AI 返回的10号码评分无效",
            "AI 返回的10号码评分全部为零",
            "AI 概率矩阵完全相同",
            "AI 第6与第7候选评分同分",
        ).any(message::contains)
    }

    private fun isReasoningControlFailure(
        error: Throwable,
        decision: AiReasoningDecision,
    ): Boolean {
        if (!decision.sendControl) return false
        val message = error.message.orEmpty().lowercase()
        return listOf(
            "http 400",
            "http 422",
            "unsupported",
            "unknown parameter",
            "invalid parameter",
            "reasoning_effort",
            "enable_thinking",
            "thinking",
        ).any(message::contains)
    }

    internal fun modelsEndpoint(chatEndpoint: String): String {
        val endpoint = URL(chatEndpoint.trim())
        val path = endpoint.path.trimEnd('/')
        val modelsPath = when {
            path.endsWith("/chat/completions") -> path.removeSuffix("/chat/completions") + "/models"
            path.endsWith("/completions") -> path.removeSuffix("/completions") + "/models"
            else -> path.substringBeforeLast('/', "") + "/models"
        }
        return URL(endpoint.protocol, endpoint.host, endpoint.port, modelsPath).toString()
    }

    private fun isLikelyTextModel(id: String): Boolean {
        val value = id.lowercase()
        val excluded = listOf(
            "embed", "whisper", "tts", "dall-e", "image", "moderation",
            "realtime", "audio", "transcrib", "sora", "video",
        )
        return excluded.none(value::contains)
    }

    private fun JSONObject.intList(key: String): List<Int> {
        val array = optJSONArray(key) ?: return emptyList()
        return buildList {
            for (index in 0 until array.length()) array.optInt(index).takeIf { it in 1..10 }?.let(::add)
        }
    }

    private fun JSONObject.doubleList(key: String): List<Double> {
        val array = optJSONArray(key) ?: return emptyList()
        return buildList {
            for (index in 0 until array.length()) {
                val value = array.optDouble(index, Double.NaN)
                if (value.isFinite()) add(value)
            }
        }
    }

    private fun estimateCost(config: AiConfig, usage: AiTokenUsage): Double? {
        val inputPrice = config.inputPricePerMillion ?: return null
        val outputPrice = config.outputPricePerMillion ?: return null
        val input = usage.inputTokens ?: return null
        val output = usage.outputTokens ?: return null
        return (input * inputPrice + output * outputPrice) / 1_000_000.0
    }

    private fun stripCodeFence(value: String): String {
        val trimmed = value.trim()
        return if (trimmed.startsWith("```")) {
            trimmed.removePrefix("```json").removePrefix("```").removeSuffix("```").trim()
        } else trimmed
    }

    private data class RemoteResponse(
        val json: JSONObject,
        val latencyMs: Long,
        val tokenBudgetLabel: String,
    )

    private class ForecastCoreReadyException : RuntimeException()
    private class ForecastHardDeadlineException : RuntimeException()

    private class AiConversationFinalizationException(
        message: String,
        cause: Throwable? = null,
    ) : IllegalStateException(message, cause)

    private companion object {
        const val FINALIZE_JSON_PROMPT =
            "不要重新分析或复述过程。立即只输出紧凑JSON：{\"position\":1至10整数,\"scores\":[号码1至10对应的10项非负评分]}。"
        const val SYSTEM_PROMPT = """你是独立概率排序模型。客户端已经根据真实开奖历史计算并核验了position 1至10的频次、遗漏、后继转移和趋势统计，本地候选被刻意隐藏。请比较十个名次后选择证据最充分的一名，并按号码1至10顺序给出10项非负评分。正式预测有严格时间预算：禁止输出隐藏思维链、解释、Markdown或逐期复述；只输出position与scores的紧凑JSON。不得承诺准确率、盈利或必中。"""
    }
}
