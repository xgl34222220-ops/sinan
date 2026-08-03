from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    result, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, found {count}")
    return result


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
path = "app/build.gradle.kts"
text = read(path)
text = replace_once(text, 'versionCode = 33\n        versionName = "5.5.8"', 'versionCode = 34\n        versionName = "5.5.9"', "version")
write(path, text)

# ---------------------------------------------------------------------------
# Manifest + process lifetime foreground service
# ---------------------------------------------------------------------------
path = "app/src/main/AndroidManifest.xml"
text = read(path)
text = replace_once(
    text,
    '    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />',
    '    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />\n'
    '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />\n'
    '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />\n'
    '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />',
    "manifest permissions",
)
text = replace_once(
    text,
    '    <application\n        android:allowBackup="false"',
    '    <application\n        android:name=".TianjiApplication"\n        android:allowBackup="false"',
    "application name",
)
text = replace_once(
    text,
    '        <activity\n            android:name=".MainActivity"',
    '        <service\n            android:name=".service.AiForegroundService"\n            android:exported="false"\n            android:foregroundServiceType="dataSync" />\n\n'
    '        <activity\n            android:name=".MainActivity"',
    "service declaration",
)
write(path, text)

write(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/TianjiApplication.kt",
    '''package com.tianji.probabilitylab.nativev4

import android.app.Application

class TianjiApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        TianjiRuntime.from(this)
    }
}
''',
)

write(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/TianjiRuntime.kt",
    '''package com.tianji.probabilitylab.nativev4

import android.content.Context
import com.tianji.probabilitylab.nativev4.ai.AiChatController

/**
 * Process-scoped runtime. Activity/Compose recreation no longer closes active AI sockets.
 * The foreground service keeps this process at foreground priority while a task is running.
 */
class TianjiRuntime private constructor(context: Context) {
    val chatController = AiChatController(context.applicationContext)
    val appController = AppController(context.applicationContext)

    companion object {
        @Volatile
        private var instance: TianjiRuntime? = null

        fun from(context: Context): TianjiRuntime = instance ?: synchronized(this) {
            instance ?: TianjiRuntime(context.applicationContext).also { instance = it }
        }
    }
}
''',
)

write(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/service/AiForegroundService.kt",
    '''package com.tianji.probabilitylab.nativev4.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.tianji.probabilitylab.nativev4.MainActivity

class AiForegroundService : Service() {
    override fun onCreate() {
        super.onCreate()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    "天机 AI 后台任务",
                    NotificationManager.IMPORTANCE_LOW,
                ).apply {
                    description = "保持正式预测和分析对话在切出页面后继续运行"
                    setShowBadge(false)
                },
            )
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val title = intent?.getStringExtra(EXTRA_TITLE).orEmpty().ifBlank { "天机 AI 正在运行" }
        val detail = intent?.getStringExtra(EXTRA_DETAIL).orEmpty().ifBlank { "返回应用可查看实时进度" }
        val openIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle(title)
            .setContentText(detail)
            .setContentIntent(openIntent)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(NotificationCompat.CATEGORY_PROGRESS)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
        startForeground(NOTIFICATION_ID, notification)
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val CHANNEL_ID = "tianji_ai_tasks"
        private const val NOTIFICATION_ID = 5909
        private const val EXTRA_TITLE = "title"
        private const val EXTRA_DETAIL = "detail"

        fun show(context: Context, title: String, detail: String) {
            val intent = Intent(context, AiForegroundService::class.java)
                .putExtra(EXTRA_TITLE, title)
                .putExtra(EXTRA_DETAIL, detail)
            runCatching { ContextCompat.startForegroundService(context.applicationContext, intent) }
        }

        fun hide(context: Context) {
            runCatching { context.applicationContext.stopService(Intent(context, AiForegroundService::class.java)) }
        }
    }
}
''',
)

# ---------------------------------------------------------------------------
# Compose runtime wiring
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt"
text = read(path)
text = text.replace("import androidx.compose.runtime.DisposableEffect\n", "")
text = replace_once(text, "import androidx.compose.runtime.Composable\n", "import androidx.compose.runtime.Composable\nimport androidx.compose.runtime.LaunchedEffect\n", "LaunchedEffect import")
text = text.replace("import com.tianji.probabilitylab.nativev4.AppController\n", "")
text = text.replace("import com.tianji.probabilitylab.nativev4.ai.AiChatController\n", "")
text = replace_once(
    text,
    "import com.tianji.probabilitylab.nativev4.ui.theme.AppearanceStore\n",
    "import com.tianji.probabilitylab.nativev4.TianjiRuntime\n"
    "import com.tianji.probabilitylab.nativev4.service.AiForegroundService\n"
    "import com.tianji.probabilitylab.nativev4.ui.theme.AppearanceStore\n",
    "runtime imports",
)
text = replace_once(
    text,
    "    val controller = remember { AppController(context) }\n    val chatController = remember { AiChatController(context.applicationContext) }",
    "    val runtime = remember(context.applicationContext) { TianjiRuntime.from(context.applicationContext) }\n"
    "    val controller = runtime.appController\n"
    "    val chatController = runtime.chatController",
    "runtime controllers",
)
text = regex_once(
    text,
    r"\n    DisposableEffect\(controller, chatController\) \{.*?\n    \}\n    BackHandler",
    "\n    BackHandler",
    "remove lifecycle close",
)
text = replace_once(
    text,
    "    val state = controller.state\n    var destination",
    "    val state = controller.state\n"
    "    val refreshSafely: () -> Unit = {\n"
    "        if (!state.isAiAnalyzing) controller.refresh()\n"
    "    }\n"
    "    val chatRunning = chatController.session.isRunning\n"
    "    LaunchedEffect(state.isAiAnalyzing, chatRunning, chatController.session.progress) {\n"
    "        if (state.isAiAnalyzing || chatRunning) {\n"
    "            val title = when {\n"
    "                state.isAiAnalyzing && chatRunning -> \"天机 AI 任务正在运行\"\n"
    "                state.isAiAnalyzing -> \"天机正式预测正在运行\"\n"
    "                else -> \"天机分析对话正在运行\"\n"
    "            }\n"
    "            val detail = if (chatRunning) {\n"
    "                chatController.session.progress.ifBlank { \"切出页面后仍会继续生成\" }\n"
    "            } else {\n"
    "                state.aiStatuses.values.firstOrNull { it.state.name == \"ANALYZING\" }\n"
    "                    ?.message.orEmpty().ifBlank { \"切出页面后仍会继续预测\" }\n"
    "            }\n"
    "            AiForegroundService.show(context, title, detail)\n"
    "        } else {\n"
    "            AiForegroundService.hide(context)\n"
    "        }\n"
    "    }\n"
    "    LaunchedEffect(state.snapshot?.latest?.period, state.snapshot?.history?.size) {\n"
    "        state.snapshot?.let(chatController::settleCandidates)\n"
    "    }\n"
    "    var destination",
    "runtime effects",
)
text = text.replace("AppHeader(state.isRefreshing, controller::refresh)", "AppHeader(state.isRefreshing, refreshSafely)")
text = text.replace("onRefresh = controller::refresh,", "onRefresh = refreshSafely,")
write(path, text)

# ---------------------------------------------------------------------------
# Do not let draw polling cancel an in-flight formal forecast
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt"
text = read(path)
text = replace_once(
    text,
    "                        error = state.error,\n                        onRefresh = onRefresh,",
    "                        error = state.error,\n                        aiRunning = state.isAiAnalyzing,\n                        onRefresh = onRefresh,",
    "live draw call",
)
text = replace_once(
    text,
    "    error: String?,\n    onRefresh: () -> Unit,",
    "    error: String?,\n    aiRunning: Boolean,\n    onRefresh: () -> Unit,",
    "live draw signature",
)
text = replace_once(
    text,
    "                    isRefreshing = isRefreshing,\n                    onRefresh = onRefresh,",
    "                    isRefreshing = isRefreshing,\n                    aiRunning = aiRunning,\n                    onRefresh = onRefresh,",
    "countdown call",
)
text = replace_once(
    text,
    "    isRefreshing: Boolean,\n    onRefresh: () -> Unit,\n    modifier: Modifier = Modifier,",
    "    isRefreshing: Boolean,\n    aiRunning: Boolean,\n    onRefresh: () -> Unit,\n    modifier: Modifier = Modifier,",
    "countdown signature",
)
text = replace_once(
    text,
    "        isRefreshing,\n    ) {",
    "        isRefreshing,\n        aiRunning,\n    ) {",
    "countdown effect key",
)
text = replace_once(
    text,
    "            if (remaining <= 0) {\n                val delays = listOf(",
    "            if (remaining <= 0) {\n"
    "                if (aiRunning) {\n"
    "                    delay(1_000L)\n"
    "                    continue\n"
    "                }\n"
    "                val delays = listOf(",
    "defer draw refresh",
)
text = replace_once(
    text,
    '"${config.analysisMode.label} · ${AiReasoningEngine.resolve(config).displayLabel}",',
    '"${config.analysisMode.label} · ${AiReasoningEngine.resolveForecast(config).displayLabel}",',
    "formal status label",
)
text = replace_once(
    text,
    'AiReasoningState.DISABLED -> "可控推理已关闭" to colors.textDim',
    'AiReasoningState.DISABLED -> "正式预测限时模式 · 长思考已关闭" to colors.textDim',
    "reasoning badge",
)
text = replace_once(
    text,
    '"${audit.settled}期 · 六码 ${(audit.top6Rate * 100).format1()}%",',
    '"${audit.settled}期 · 六码 ${(audit.top6Rate * 100).format1()}% · 较随机 ${if (audit.top6Lift >= 0) "+" else ""}${(audit.top6Lift * 100).format1()}%",',
    "audit headline",
)
text = replace_once(
    text,
    '''                if (audit.settled < 100) {
                    "前向 ${audit.settled}/100 · 基础权重"
                } else {
                    "LogLoss ${audit.meanLogLoss?.format2() ?: "--"} · 权重 ${audit.forwardWeight.format2()}"
                },''',
    '''                buildString {
                    append("近20/50/100：")
                    append(audit.recent20Top6Rate?.let { "${(it * 100).format1()}%" } ?: "--")
                    append(" / ")
                    append(audit.recent50Top6Rate?.let { "${(it * 100).format1()}%" } ?: "--")
                    append(" / ")
                    append(audit.recent100Top6Rate?.let { "${(it * 100).format1()}%" } ?: "--")
                    append(" · ")
                    append(if (audit.settled < 30) "样本不足" else "LogLoss ${audit.meanLogLoss?.format2() ?: "--"}")
                    audit.meanLatencyMs?.let { append(" · ${it.toLong()}ms") }
                    audit.meanEstimatedCost?.let { append(" · 均价 $${"%.5f".format(Locale.US, it)}") }
                },''',
    "audit rolling text",
)
write(path, text)

# ---------------------------------------------------------------------------
# Refresh no longer cancels paid AI work; each request uses its frozen snapshot
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt"
text = read(path)
text = text.replace("        aiGeneration.incrementAndGet()\n        preferences.edit", "        preferences.edit", 1)
text = regex_once(
    text,
    r"    fun refresh\(\) \{\n.*?\n        executor\.execute \{",
    '''    fun refresh() {
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
        executor.execute {''',
    "refresh preservation",
)
text = replace_once(
    text,
    "        val requested = aiConfigs.filter { it.isComplete && (profileId == null || it.id == profileId) }",
    "        val runningIds = state.aiStatuses.filterValues {\n"
    "            it.state == AiConnectionState.ANALYZING || it.state == AiConnectionState.TESTING\n"
    "        }.keys\n"
    "        if (profileId != null && profileId in runningIds) {\n"
    "            state = state.copy(aiError = \"该 AI 仍在后台运行，请等待完成或先手动取消\")\n"
    "            return\n"
    "        }\n"
    "        val requested = aiConfigs.filter {\n"
    "            it.isComplete && (profileId == null || it.id == profileId) && it.id !in runningIds\n"
    "        }",
    "avoid duplicate running request",
)
text = text.replace("if (aiGeneration.get() != token || state.lottery != lottery) return@post", "if (state.lottery != lottery) return@post")
text = text.replace(
    "require(aiGeneration.get() == token && !Thread.currentThread().isInterrupted) {",
    "require(!Thread.currentThread().isInterrupted) {",
)
text = text.replace(
    "                                aiGeneration.get() == token &&\n                                state.report?.targetPeriod",
    "                                state.report?.targetPeriod",
)
text = text.replace(
    "                    require(aiGeneration.get() == token && !Thread.currentThread().isInterrupted) {",
    "                    require(!Thread.currentThread().isInterrupted) {",
)
text = text.replace(
    "                    if (aiGeneration.get() != token || state.report?.targetPeriod != report.targetPeriod) {",
    "                    if (state.report?.targetPeriod != report.targetPeriod) {",
)
text = text.replace("AiReasoningEngine.resolve(config).displayLabel", "AiReasoningEngine.resolveForecast(config).displayLabel")
write(path, text)

# ---------------------------------------------------------------------------
# Formal forecast policy: bounded, core-first, no multi-minute hidden reasoning
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiReasoning.kt"
text = read(path)
text = replace_once(
    text,
    'HIGH("深入", "请求供应商高强度推理，可能更慢且更贵"),',
    'HIGH("深入", "分析对话可使用高推理；正式预测仍采用限时核心矩阵"),',
    "reasoning detail",
)
text = regex_once(
    text,
    r"    fun resolveForecast\(config: AiConfig\): AiReasoningDecision \{.*?\n    \}\n\n    fun fallback",
    '''    fun resolveForecast(config: AiConfig): AiReasoningDecision {
        val resolved = resolve(config)
        return when (resolved.protocol) {
            AiReasoningProtocol.DEEPSEEK -> resolved.copy(
                sendControl = true,
                enableThinking = false,
                effort = null,
                displayLabel = "${resolved.protocol.label} · 正式预测限时",
            )
            AiReasoningProtocol.ENABLE_THINKING, AiReasoningProtocol.OPENROUTER -> resolved.copy(
                sendControl = true,
                enableThinking = false,
                effort = null,
                displayLabel = "${resolved.protocol.label} · 正式预测限时",
            )
            AiReasoningProtocol.OPENAI -> resolved.copy(
                sendControl = false,
                enableThinking = false,
                effort = null,
                displayLabel = "${resolved.protocol.label} · 正式预测限时结构化",
            )
            AiReasoningProtocol.AUTO, AiReasoningProtocol.NONE -> resolved.copy(
                sendControl = false,
                enableThinking = false,
                effort = null,
                displayLabel = "正式预测限时结构化",
            )
        }
    }

    fun fallback''',
    "resolveForecast",
)
write(path, text)

path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiTokenPolicy.kt"
text = read(path)
text = replace_once(text, "const val LOW_MAX_OUTPUT_TOKENS: Int = 4 * 1024", "const val LOW_MAX_OUTPUT_TOKENS: Int = 1024", "low tokens")
text = replace_once(text, "const val AUTO_MAX_OUTPUT_TOKENS: Int = 8 * 1024", "const val AUTO_MAX_OUTPUT_TOKENS: Int = 1536", "auto tokens")
text = replace_once(text, "const val HIGH_MAX_OUTPUT_TOKENS: Int = 32 * 1024", "const val HIGH_MAX_OUTPUT_TOKENS: Int = 2048", "high tokens")
text = replace_once(
    text,
    '        val officialDeepSeekV4 = host.endsWith("deepseek.com") && model.startsWith("deepseek-v4")\n\n        if (!officialDeepSeekV4) {',
    '        val boundedDeepSeek = config.provider == AiProvider.DEEPSEEK ||\n            host.contains("deepseek") || model.startsWith("deepseek-")\n        val boundedOpenAiResponses = config.provider == AiProvider.OPENAI && responsesApi\n\n        if (!boundedDeepSeek && !boundedOpenAiResponses) {',
    "token provider detection",
)
text = replace_once(
    text,
    '            parameter = if (responsesApi) "max_output_tokens" else "max_tokens",',
    '            parameter = if (boundedOpenAiResponses) "max_output_tokens" else "max_tokens",',
    "token parameter",
)
text = replace_once(
    text,
    '            label = "正式预测输出上限 ${value / 1024}K（$modeLabel）",',
    '            label = "正式预测核心输出上限 $value tokens（$modeLabel）",',
    "token label",
)
write(path, text)

path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
text = read(path)
text = text.replace("                explainOutput = true,", "                explainOutput = false,")
text = replace_once(
    text,
    "                        readTimeoutMs = 120_000,\n                        jsonOutput = true,\n                        explainOutput = false,",
    "                        readTimeoutMs = 30_000,\n                        jsonOutput = true,\n                        explainOutput = false,",
    "finalize timeout",
)
text = regex_once(
    text,
    r"                readTimeoutMs = when \{.*?\n                \},\n                executionNote =",
    "                readTimeoutMs = if (config.analysisMode == AiAnalysisMode.DEEP) 60_000 else 45_000,\n"
    "                executionNote =",
    "formal timeout",
)
text = regex_once(
    text,
    r"                readTimeoutMs = if \(primaryDecision\.protocol == AiReasoningProtocol\.DEEPSEEK\) \{.*?\n                \},\n                executionNote = \"\$\{config\.analysisMode\.label\} · 显式参数被拒绝后使用模型默认思考\"",
    "                readTimeoutMs = 45_000,\n"
    "                executionNote = \"${config.analysisMode.label} · 限时参数兼容回退\"",
    "fallback timeout",
)
text = replace_once(
    text,
    '                executionNote = "${config.analysisMode.label} · ${primaryDecision.displayLabel}",',
    '                executionNote = "${config.analysisMode.label} · ${primaryDecision.displayLabel} · 核心矩阵优先",',
    "execution note",
)
text = replace_once(
    text,
    '                connection.setRequestProperty("Accept", "application/json")',
    '                connection.setRequestProperty("Accept", if (useStreaming) "text/event-stream" else "application/json")',
    "stream accept",
)
text = replace_once(
    text,
    '''                    if (AiForecastPayloadExtractor.containsForecastCore(content.toString())) {
                        report("已收到完整预测核心，正在校验说明与结束状态")
                    } else {''',
    '''                    if (AiForecastPayloadExtractor.containsForecastCore(content.toString())) {
                        report("已收到完整预测核心，立即停止等待并转入本机校验")
                        throw ForecastCoreReadyException()
                    } else {''',
    "core early stop",
)
text = replace_once(
    text,
    "        } catch (cause: IOException) {\n            streamFailure = cause\n        }",
    "        } catch (_: ForecastCoreReadyException) {\n"
    "            finishReason = \"tianji_core_ready\"\n"
    "        } catch (cause: IOException) {\n"
    "            streamFailure = cause\n"
    "        }",
    "core stop catch",
)
text = replace_once(
    text,
    "                AiPromptCompactor.compactDraws(snapshot.history, historyLimit),",
    "                AiPromptCompactor.compactDraws(snapshot.history, minOf(historyLimit, 24)),",
    "compact raw draws",
)
text = replace_once(
    text,
    '                "所有说明字段必须使用简体中文并保持精简；JSON键按position、scores、factor_weights、calculation_summary、position_reason、candidate_reason、uncertainty顺序输出。完成真实推理后立即输出JSON，不要写英文、Markdown、长篇方法教学或逐期复述。",',
    '                "正式预测只输出position和scores核心矩阵。不要输出思维过程、Markdown、逐期复述或额外字段；客户端会立即冻结并生成可核验说明。",',
    "output rule",
)
text = regex_once(
    text,
    r"            put\(\n                \"required_json_schema\",\n                JSONObject\(\).*?\n            \)\n        \}",
    '''            put(
                "required_json_schema",
                JSONObject()
                    .put("position", "1至10的整数")
                    .put("scores", "按号码1至10排列的10项非负原始评分，不得全部相同"),
            )
        }''',
    "core schema prompt",
)
text = replace_once(
    text,
    '                    append("说明审计：AI 已返回有效预测矩阵，但说明未满足“简体中文且至少三类因素共同参与”的协议，已隐藏不可核验说明。")',
    '                    append("正式预测采用限时核心矩阵；为确保开奖前完成，模型长思考与长篇说明不会阻塞结果冻结。")',
    "local explanation",
)
text = replace_once(
    text,
    '''        const val FINALIZE_JSON_PROMPT =
            "你已经完成上一轮统计分析。不要重新计算、不要复述推理过程。立即用简体中文输出一个紧凑JSON对象，键顺序必须为position、scores、factor_weights、calculation_summary、position_reason、candidate_reason、uncertainty。factor_weights固定对应近20频次、近60频次、遗漏、后继转移、趋势稳定性，至少三项有效参与。"
        const val SYSTEM_PROMPT = """你是独立概率排序模型。输入含真实开奖和由客户端逐期计算并核验的统计表，本地盲测候选已被刻意隐藏。遗漏、近20/60期次数、后继转移和趋势稳定性必须以 verified_position_statistics 为事实来源，原始历史仅用于交叉核验。你必须先比较position 1至10，再选择证据最充分的名次；不得默认第1名或偏向固定名次。禁止只使用单一指标，禁止使用“遗漏+转移次数”的简单未加权求和；必须让近20频次、近60频次、遗漏、后继转移、趋势稳定性中至少三类因素共同参与，任何一类归一化权重不得超过0.65。随后按号码1至10顺序输出10个非负原始评分，每项至少保留6位小数，六码、七码和最终排序由客户端从scores确定。所有解释必须使用简体中文且精简，只说明可核验统计、因素权重、证据冲突和不确定性，不得输出隐藏思维链、英文、Markdown、长篇教学或逐期复述。JSON键顺序必须为position、scores、factor_weights、calculation_summary、position_reason、candidate_reason、uncertainty。只输出required_json_schema规定的JSON，不承诺准确率、盈利或必中。"""''',
    '''        const val FINALIZE_JSON_PROMPT =
            "不要重新分析或复述过程。立即只输出紧凑JSON：{\\\"position\\\":1至10整数,\\\"scores\\\":[号码1至10对应的10项非负评分]}。"
        const val SYSTEM_PROMPT = """你是独立概率排序模型。客户端已经根据真实开奖历史计算并核验了position 1至10的频次、遗漏、后继转移和趋势统计，本地候选被刻意隐藏。请比较十个名次后选择证据最充分的一名，并按号码1至10顺序给出10项非负评分。正式预测有严格时间预算：禁止输出隐藏思维链、解释、Markdown或逐期复述；只输出position与scores的紧凑JSON。不得承诺准确率、盈利或必中。"""''',
    "compact prompts",
)
text = replace_once(
    text,
    "    private class AiConversationFinalizationException(\n",
    "    private class ForecastCoreReadyException : RuntimeException()\n\n"
    "    private class AiConversationFinalizationException(\n",
    "core exception",
)
write(path, text)

# ---------------------------------------------------------------------------
# Chat: exact settlement, adaptive context, bounded output,断流恢复, UI throttling
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt"
text = read(path)
text = replace_once(
    text,
    "import java.io.BufferedReader\n",
    "import java.io.BufferedReader\nimport java.io.EOFException\nimport java.io.IOException\n",
    "chat io imports",
)
text = replace_once(
    text,
    "import java.net.HttpURLConnection\n",
    "import java.net.HttpURLConnection\nimport java.net.SocketException\n",
    "chat socket import",
)
text = replace_once(
    text,
    "    var archives by mutableStateOf(archiveData.map(AiChatArchiveCodec::summary))\n        private set\n\n    fun selectContext(",
    "    var archives by mutableStateOf(archiveData.map(AiChatArchiveCodec::summary))\n"
    "        private set\n\n"
    "    fun settleCandidates(snapshot: DrawSnapshot) {\n"
    "        val updated = archiveStore.settleCandidates(snapshot.lottery.apiKey, snapshot.history)\n"
    "        archiveData = updated\n"
    "        val current = updated.firstOrNull { it.id == session.archiveId }\n"
    "        if (current != null) {\n"
    "            session = if (session.isRunning) {\n"
    "                session.copy(candidates = current.candidates)\n"
    "            } else {\n"
    "                current.toSession()\n"
    "            }\n"
    "        }\n"
    "        refreshArchiveSummaries()\n"
    "    }\n\n"
    "    fun selectContext(",
    "settle method",
)
text = replace_once(
    text,
    "        val activeModel = session.model.ifBlank { config.model }.trim()\n        selectContext(",
    "        val activeModel = session.model.ifBlank { config.model }.trim()\n"
    "        settleCandidates(snapshot)\n"
    "        selectContext(",
    "settle before send",
)
text = replace_once(
    text,
    '                            error = cause.message ?: "对话分析失败",',
    '                            error = AiErrorMessages.userFacing(cause, "对话分析失败"),',
    "chat error translation",
)
text = replace_once(text, "val context = AiChatContextBuilder.build(snapshot, report)", "val context = AiChatContextBuilder.build(snapshot, report, question)", "adaptive context call")
text = regex_once(
    text,
    r"object AiChatContextBuilder \{\n    fun build\(snapshot: DrawSnapshot, report: ForecastReport\): JSONObject \{.*?\n    \}\n\n    internal fun computePositionStatistics",
    '''object AiChatContextBuilder {
    fun build(snapshot: DrawSnapshot, report: ForecastReport, question: String): JSONObject {
        val verifiedHistory = snapshot.history.takeLast(120)
        val wantsPrediction = AiChatProtocol.wantsPrediction(question)
        val requestedPosition = extractPosition(question)
        val positions = when {
            requestedPosition != null -> listOf(requestedPosition)
            wantsPrediction -> (0 until 10).toList()
            else -> listOf(report.selectedPosition)
        }
        val rawWindow = when {
            wantsPrediction && requestedPosition == null -> 48
            wantsPrediction -> 32
            requestedPosition != null -> 24
            else -> 12
        }
        val compactHistory = verifiedHistory.takeLast(rawWindow)
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
                "compact_history",
                JSONArray(compactHistory.map { draw ->
                    "${draw.period}:${draw.numbers.joinToString(",")}"
                }),
            )
            .put(
                "verified_position_statistics",
                JSONArray(positions.map { position ->
                    toJson(computePositionStatistics(verifiedHistory, position))
                }),
            )
            .put(
                "native_model_reference",
                JSONObject()
                    .put("algorithm_version", report.algorithmVersion)
                    .put("trained_through_period", report.trainedThroughPeriod)
                    .put("selected_position", report.selectedPosition + 1)
                    .put("top6", JSONArray(report.selected.top6))
                    .put("evidence_mode", report.mode.name)
                    .put("rule", "local reference only; do not copy without comparing verified facts"),
            )
    }

    private fun extractPosition(question: String): Int? {
        val token = Regex("第\\s*([一二三四五六七八九十0-9]{1,2})\\s*名")
            .find(question)?.groupValues?.getOrNull(1) ?: return null
        val value = token.toIntOrNull() ?: when (token) {
            "一" -> 1; "二" -> 2; "三" -> 3; "四" -> 4; "五" -> 5
            "六" -> 6; "七" -> 7; "八" -> 8; "九" -> 9; "十" -> 10
            else -> return null
        }
        return (value - 1).takeIf { it in 0..9 }
    }

    internal fun computePositionStatistics''',
    "adaptive context builder",
)
text = text.replace(
    "                stream = true,\n            )",
    "                stream = true,\n                wantsPrediction = wantsPrediction,\n            )",
    1,
)
text = text.replace(
    "                        stream = false,\n                    ),",
    "                        stream = false,\n                        wantsPrediction = wantsPrediction,\n                    ),",
    1,
)
text = replace_once(
    text,
    "        decision: AiReasoningDecision,\n        stream: Boolean,\n    ): JSONObject",
    "        decision: AiReasoningDecision,\n        stream: Boolean,\n        wantsPrediction: Boolean,\n    ): JSONObject",
    "chat request signature",
)
text = replace_once(
    text,
    "        put(\"stream\", stream)\n        if (responsesApi) {",
    "        put(\"stream\", stream)\n"
    "        if (config.provider != AiProvider.COMPATIBLE) {\n"
    "            put(if (responsesApi) \"max_output_tokens\" else \"max_tokens\", if (wantsPrediction) 4096 else 2048)\n"
    "        }\n"
    "        if (responsesApi) {",
    "chat output budget",
)
text = replace_once(
    text,
    "            } catch (cause: SocketTimeoutException) {\n                lastFailure = cause",
    "            } catch (cause: SocketTimeoutException) {\n                lastFailure = cause",
    "timeout anchor",
)
text = replace_once(
    text,
    '''                throw IllegalStateException(
                    if (deliveredVisibleText) "流式回答中断，已保留已生成内容" else "模型响应超时",
                    cause,
                )
            } finally {''',
    '''                throw IllegalStateException(
                    if (deliveredVisibleText) "流式回答中断，已保留已生成内容" else "模型响应超时",
                    cause,
                )
            } catch (cause: EOFException) {
                throw IllegalStateException(AiErrorMessages.userFacing(cause, "模型连接提前结束"), cause)
            } catch (cause: SocketException) {
                throw IllegalStateException(AiErrorMessages.userFacing(cause, "网络连接异常中断"), cause)
            } catch (cause: IOException) {
                throw IllegalStateException(AiErrorMessages.userFacing(cause, "网络连接中断"), cause)
            } finally {''',
    "chat io catches",
)
text = replace_once(
    text,
    '''        initialLines.forEach(::processLine)
        while (true) {
            val line = reader.readLine() ?: break
            processLine(line)
        }
        consumeEvent()
        publisher.flush()
        require(rawContent.isNotBlank()) { "模型没有返回可显示的流式回答" }
        return JSONObject()
            .put("id", responseId)
            .put("output_text", rawContent.toString())
            .put("_tianji_reasoning", reasoning.toString())
            .put("usage", usage ?: JSONObject())''',
    '''        var streamFailure: IOException? = null
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
        if (rawContent.isBlank()) {
            streamFailure?.let { throw it }
            error("模型没有返回可显示的流式回答")
        }
        return JSONObject()
            .put("id", responseId)
            .put("output_text", rawContent.toString())
            .put("_tianji_reasoning", reasoning.toString())
            .put("_tianji_stream_interrupted", streamFailure != null)
            .put("usage", usage ?: JSONObject())''',
    "chat stream salvage",
)
text = replace_once(
    text,
    "        onProgress(\"回答完成，正在整理候选卡片…\")",
    "        onProgress(if (response.optBoolean(\"_tianji_stream_interrupted\")) {\n"
    "            \"网络中断后已恢复现有回答，正在整理候选卡片…\"\n"
    "        } else {\n"
    "            \"回答完成，正在整理候选卡片…\"\n"
    "        })",
    "chat salvage progress",
)
text = replace_once(
    text,
    '''    private fun timeoutFor(decision: AiReasoningDecision): Int = when {
        decision.preference == AiReasoningMode.HIGH -> 180_000
        decision.expectsReasoning -> 120_000
        else -> 75_000
    }''',
    '''    private fun timeoutFor(decision: AiReasoningDecision): Int = when {
        decision.preference == AiReasoningMode.HIGH -> 120_000
        decision.expectsReasoning -> 90_000
        else -> 60_000
    }''',
    "chat timeout",
)
text = replace_once(
    text,
    '                visible.length - lastVisible.length >= 12\n            if (urgent || now - lastEmitAt >= 35L) {',
    '                visible.length - lastVisible.length >= 32\n            if (urgent || now - lastEmitAt >= 120L) {',
    "chat throttle",
)
write(path, text)

# ---------------------------------------------------------------------------
# Chat archive: migrate monolithic JSON to row-based SQLite and settle all targets
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatArchiveStore.kt"
text = read(path)
text = regex_once(
    text,
    r"import android\.util\.AtomicFile\nimport org\.json",
    "import android.content.ContentValues\n"
    "import android.database.sqlite.SQLiteDatabase\n"
    "import android.database.sqlite.SQLiteOpenHelper\n"
    "import com.tianji.probabilitylab.nativev4.model.Draw\n"
    "import org.json",
    "archive imports",
)
text = regex_once(
    text,
    r"class AiChatArchiveStore\(context: Context\) \{.*?\n\}\n\nobject AiChatArchiveCodec",
    '''class AiChatArchiveStore(context: Context) {
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

object AiChatArchiveCodec''',
    "sqlite archive store",
)
write(path, text)

# ---------------------------------------------------------------------------
# AI audit: rolling windows, latency/cost and explicit random baseline
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiAnalysis.kt"
text = read(path)
text = replace_once(
    text,
    "    val meanActualRank: Double?,\n) {",
    "    val meanActualRank: Double?,\n"
    "    val meanLatencyMs: Double? = null,\n"
    "    val meanInputTokens: Double? = null,\n"
    "    val meanOutputTokens: Double? = null,\n"
    "    val meanEstimatedCost: Double? = null,\n"
    "    val recent20Top6Rate: Double? = null,\n"
    "    val recent50Top6Rate: Double? = null,\n"
    "    val recent100Top6Rate: Double? = null,\n"
    ") {",
    "audit fields",
)
text = replace_once(
    text,
    "    val top7Rate: Double get() = if (settled == 0) 0.0 else top7Hits.toDouble() / settled\n    val forwardWeight:",
    "    val top7Rate: Double get() = if (settled == 0) 0.0 else top7Hits.toDouble() / settled\n"
    "    val top6Lift: Double get() = top6Rate - 0.60\n"
    "    val forwardWeight:",
    "audit lift",
)
write(path, text)

path = "app/src/main/java/com/tianji/probabilitylab/nativev4/data/AppDatabase.kt"
text = read(path)
text = regex_once(
    text,
    r"    fun loadAiProfileAudits\(lottery: LotteryType\): List<AiProfileAudit> = readableDatabase\.rawQuery\(.*?\n    \}\n\n    fun lockAiConsensus",
    '''    fun loadAiProfileAudits(lottery: LotteryType): List<AiProfileAudit> {
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

    fun lockAiConsensus''',
    "rolling audit query",
)
write(path, text)

# ---------------------------------------------------------------------------
# Tests + notes
# ---------------------------------------------------------------------------
write(
    "app/src/test/java/com/tianji/probabilitylab/nativev4/ai/AiFormalForecastPolicyTest.kt",
    '''package com.tianji.probabilitylab.nativev4.ai

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.assertEquals
import org.junit.Test

class AiFormalForecastPolicyTest {
    @Test
    fun highDeepSeekFormalForecastStillDisablesLongThinking() {
        val config = AiConfig(
            provider = AiProvider.DEEPSEEK,
            endpoint = "https://api.deepseek.com/chat/completions",
            model = "deepseek-v4-pro",
            apiKey = "test",
            reasoningMode = AiReasoningMode.HIGH,
        )
        val decision = AiReasoningEngine.resolveForecast(config)
        assertTrue(decision.sendControl)
        assertFalse(decision.enableThinking)
        assertTrue(decision.displayLabel.contains("限时"))
    }

    @Test
    fun formalCoreBudgetIsBounded() {
        val config = AiConfig(
            provider = AiProvider.DEEPSEEK,
            endpoint = "https://api.deepseek.com/chat/completions",
            model = "deepseek-v4-pro",
            apiKey = "test",
            reasoningMode = AiReasoningMode.HIGH,
        )
        val budget = AiTokenPolicy.resolve(config, responsesApi = false)
        assertEquals("max_tokens", budget.parameter)
        assertTrue((budget.value ?: Int.MAX_VALUE) <= 2048)
    }
}
''',
)

write(
    "RELEASE_NOTES_v5.5.9.md",
    '''# 天机 v5.5.9

## 正式预测及时性
- 正式预测改为限时核心矩阵，不再让“高推理”阻塞数分钟。
- 收到完整 position 与 10 项 scores 后立即结束等待并在本机冻结结果。
- 60 期模式最长等待 45 秒，120 期模式最长等待 60 秒。
- 原始开奖只保留最近 24 期交叉核验，完整 120 期统计继续由本机计算并发送。
- 开奖轮询和手动刷新不再取消已经发出的付费 AI 任务。

## 后台与对话
- 控制器提升为进程级运行时，Activity 重建不再关闭正在运行的连接。
- 正式预测或分析对话运行时启用前台服务通知，切出页面和锁屏后更不易被系统回收。
- AI 对话增加 Socket/EOF/IOException 中文错误与部分回答恢复。
- 对话上下文按问题名次和类型裁剪，降低输入 Token 与等待时间。
- 流式界面更新节流到约 120ms，减少长回答重组卡顿。

## 档案与验证
- 对话历史由整文件 JSON 改为 SQLite 单会话行更新，并自动迁移旧历史。
- 所有未结算对话候选按各自目标期从接口历史精确补验，不再只验证最新一期。
- AI 档案增加最近 20/50/100 次六码成绩、随机六码 60% 基线差、平均延迟与平均成本展示。
''',
)

# Self-delete temporary patch machinery from the generated source commit.
for temporary in [
    ROOT / "tools/apply_v559.py",
    ROOT / ".github/workflows/apply-v559.yml",
]:
    if temporary.exists():
        temporary.unlink()
