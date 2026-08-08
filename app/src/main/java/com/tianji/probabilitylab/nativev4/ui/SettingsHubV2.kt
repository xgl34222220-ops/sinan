package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.ColorLens
import androidx.compose.material.icons.rounded.ContentCopy
import androidx.compose.material.icons.rounded.Edit
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.Info
import androidx.compose.material.icons.rounded.NotificationsActive
import androidx.compose.material.icons.rounded.Psychology
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.Storage
import androidx.compose.material.icons.rounded.Verified
import androidx.compose.material.icons.rounded.Visibility
import androidx.compose.material.icons.rounded.VisibilityOff
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tianji.probabilitylab.nativev4.AppUiState
import com.tianji.probabilitylab.nativev4.BuildConfig
import com.tianji.probabilitylab.nativev4.ai.AiAnalysisMode
import com.tianji.probabilitylab.nativev4.ai.AiConfig
import com.tianji.probabilitylab.nativev4.ai.AiConnectionState
import com.tianji.probabilitylab.nativev4.ai.AiProvider
import com.tianji.probabilitylab.nativev4.ai.AiReasoningMode
import com.tianji.probabilitylab.nativev4.model.Draw
import com.tianji.probabilitylab.nativev4.ui.theme.AppearanceMode
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors
import com.tianji.probabilitylab.nativev4.ui.theme.PaletteMode

private enum class SettingsPageV2 { ROOT, AI, DATA, APPEARANCE, HISTORY, ABOUT }

private enum class AiApiRouteV2(val label: String) {
    AUTO("自动"),
    CHAT_COMPLETIONS("Chat"),
    RESPONSES("Responses"),
}

private fun AiProvider.editorLabelV2(): String = when (this) {
    AiProvider.COMPATIBLE -> "自定义"
    else -> label
}

private fun endpointBaseForEditorV2(value: String): String = value.trim().trimEnd('/')
    .removeSuffix("/chat/completions")
    .removeSuffix("/responses")
    .removeSuffix("/completions")

private fun inferApiRouteV2(endpoint: String, provider: AiProvider): AiApiRouteV2 = when {
    endpoint.trimEnd('/').endsWith("/responses") -> AiApiRouteV2.RESPONSES
    endpoint.trimEnd('/').endsWith("/chat/completions") ||
        endpoint.trimEnd('/').endsWith("/completions") -> AiApiRouteV2.CHAT_COMPLETIONS
    provider == AiProvider.OPENAI -> AiApiRouteV2.RESPONSES
    else -> AiApiRouteV2.AUTO
}

private fun normalizeAiEndpointV2(
    rawValue: String,
    provider: AiProvider,
    route: AiApiRouteV2,
): String {
    val value = rawValue.trim().trimEnd('/')
    if (!value.startsWith("https://")) return value
    if (
        value.endsWith("/responses") ||
        value.endsWith("/chat/completions") ||
        value.endsWith("/completions")
    ) return value
    val resolvedRoute = when (route) {
        AiApiRouteV2.AUTO -> if (provider == AiProvider.OPENAI) {
            AiApiRouteV2.RESPONSES
        } else {
            AiApiRouteV2.CHAT_COMPLETIONS
        }
        else -> route
    }
    return value + when (resolvedRoute) {
        AiApiRouteV2.RESPONSES -> "/responses"
        AiApiRouteV2.CHAT_COMPLETIONS, AiApiRouteV2.AUTO -> "/chat/completions"
    }
}

@Composable
fun SettingsHubScreen(
    state: AppUiState,
    paletteMode: PaletteMode,
    appearanceMode: AppearanceMode,
    aiConfigs: List<AiConfig>,
    aiAvailableModels: Map<String, List<String>>,
    activeAiProfileId: String,
    onPaletteChanged: (PaletteMode) -> Unit,
    onAppearanceChanged: (AppearanceMode) -> Unit,
    onSaveAiConfig: (AiConfig) -> Unit,
    onDeleteAiConfig: (String) -> Unit,
    onTestAiConnection: (String) -> Unit,
    onLoadAiModels: (String) -> Unit,
    onSelectAiModel: (String, String) -> Unit,
    onSelectAiMode: (String, AiAnalysisMode) -> Unit,
    onSelectAiReasoningMode: (String, AiReasoningMode) -> Unit,
    onSelectActiveAi: (String) -> Unit,
    onAnalyzeAi: (String) -> Unit,
    onAiConcurrencyChanged: (Int) -> Unit,
    pushUnreadCount: Int,
    onOpenPushAlerts: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var page by rememberSaveable { mutableStateOf(SettingsPageV2.ROOT) }
    when (page) {
        SettingsPageV2.ROOT -> SettingsRootV2(
            state = state,
            aiConfigs = aiConfigs,
            activeAiProfileId = activeAiProfileId,
            appearanceMode = appearanceMode,
            pushUnreadCount = pushUnreadCount,
            onOpenPushAlerts = onOpenPushAlerts,
            onOpen = { page = it },
            modifier = modifier,
        )
        SettingsPageV2.AI -> AiSettingsPageV2(
            state = state,
            configs = aiConfigs,
            catalogs = aiAvailableModels,
            activeAiProfileId = activeAiProfileId,
            onBack = { page = SettingsPageV2.ROOT },
            onSave = onSaveAiConfig,
            onDelete = onDeleteAiConfig,
            onTest = onTestAiConnection,
            onLoadModels = onLoadAiModels,
            onSelectModel = onSelectAiModel,
            onSelectMode = onSelectAiMode,
            onSelectReasoning = onSelectAiReasoningMode,
            onSelectActive = onSelectActiveAi,
            onAnalyze = onAnalyzeAi,
            onConcurrency = onAiConcurrencyChanged,
            modifier = modifier,
        )
        SettingsPageV2.DATA -> DataSettingsPageV2(state, { page = SettingsPageV2.ROOT }, modifier)
        SettingsPageV2.APPEARANCE -> AppearanceSettingsPageV2(
            paletteMode,
            appearanceMode,
            onPaletteChanged,
            onAppearanceChanged,
            { page = SettingsPageV2.ROOT },
            modifier,
        )
        SettingsPageV2.HISTORY -> RecentHistoryPageV2(state, { page = SettingsPageV2.ROOT }, modifier)
        SettingsPageV2.ABOUT -> AboutPageV2({ page = SettingsPageV2.ROOT }, modifier)
    }
}

@Composable
private fun SettingsRootV2(
    state: AppUiState,
    aiConfigs: List<AiConfig>,
    activeAiProfileId: String,
    appearanceMode: AppearanceMode,
    pushUnreadCount: Int,
    onOpenPushAlerts: () -> Unit,
    onOpen: (SettingsPageV2) -> Unit,
    modifier: Modifier,
) {
    val colors = LocalTianjiColors.current
    val activeAi = aiConfigs.firstOrNull { it.id == activeAiProfileId && it.isComplete }
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item("settings-section-core") {
            Text("核心能力", color = colors.textDim, fontSize = 11.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(start = 4.dp, end = 4.dp, top = 2.dp))
        }
        item {
            SettingsEntry(
                Icons.Rounded.Psychology,
                "AI 模型与接口",
                "可保存多个 Key，正式预测只调用当前 AI",
                { onOpen(SettingsPageV2.AI) },
                activeAi?.let { "当前 ${it.provider.label}" } ?: "${aiConfigs.count(AiConfig::isComplete)} 个可用",
            )
        }
        item {
            SettingsEntry(
                Icons.Rounded.Storage,
                "数据与同步",
                "接口状态、历史窗口、档案完整性和后台同步",
                { onOpen(SettingsPageV2.DATA) },
                "${state.snapshot?.history?.size ?: 0} 期",
            )
        }
        item {
            SettingsEntry(
                Icons.Rounded.NotificationsActive,
                "预警与推送",
                "三期不中即时提醒、接收范围和历史预警",
                onOpenPushAlerts,
                if (pushUnreadCount > 0) "$pushUnreadCount 条未读" else "已开启",
            )
        }
        item("settings-section-personal") {
            Text("个性化", color = colors.textDim, fontSize = 11.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(start = 4.dp, end = 4.dp, top = 4.dp))
        }
        item {
            SettingsEntry(
                Icons.Rounded.ColorLens,
                "外观与主题",
                "跟随系统、浅色、深色、OLED 和强调色",
                { onOpen(SettingsPageV2.APPEARANCE) },
                appearanceMode.label,
            )
        }
        item("settings-section-more") {
            Text("更多", color = colors.textDim, fontSize = 11.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(start = 4.dp, end = 4.dp, top = 4.dp))
        }
        item {
            SettingsEntry(
                Icons.Rounded.History,
                "最近开奖",
                "查看本机已核验的连续开奖记录",
                { onOpen(SettingsPageV2.HISTORY) },
            )
        }
        item {
            SettingsEntry(
                Icons.Rounded.Info,
                "关于天机",
                "版本、实验边界和开源信息",
                { onOpen(SettingsPageV2.ABOUT) },
                BuildConfig.VERSION_NAME,
            )
        }
    }
}

@Composable
private fun SettingsPageHeaderV2(title: String, detail: String, onBack: () -> Unit) {
    val colors = LocalTianjiColors.current
    Row(verticalAlignment = Alignment.CenterVertically) {
        IconButton(
            onClick = onBack,
            modifier = Modifier
                .size(40.dp)
                .clip(RoundedCornerShape(13.dp))
                .background(colors.surfaceStrong),
        ) {
            Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "返回", tint = colors.textSoft)
        }
        Spacer(Modifier.width(10.dp))
        Column {
            Text(title, color = colors.text, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
            Text(detail, color = colors.textDim, fontSize = 11.sp)
        }
    }
}

@Composable
private fun AiSettingsPageV2(
    state: AppUiState,
    configs: List<AiConfig>,
    catalogs: Map<String, List<String>>,
    activeAiProfileId: String,
    onBack: () -> Unit,
    onSave: (AiConfig) -> Unit,
    onDelete: (String) -> Unit,
    onTest: (String) -> Unit,
    onLoadModels: (String) -> Unit,
    onSelectModel: (String, String) -> Unit,
    onSelectMode: (String, AiAnalysisMode) -> Unit,
    onSelectReasoning: (String, AiReasoningMode) -> Unit,
    onSelectActive: (String) -> Unit,
    onAnalyze: (String) -> Unit,
    onConcurrency: (Int) -> Unit,
    modifier: Modifier,
) {
    val colors = LocalTianjiColors.current
    var editor by remember { mutableStateOf<AiConfig?>(null) }
    var createNew by remember { mutableStateOf(false) }
    var pendingDelete by remember { mutableStateOf<AiConfig?>(null) }
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item { SettingsPageHeaderV2("AI 服务", "多个 Key 可保存，正式预测只调用当前 AI", onBack) }
        item {
            SurfaceCard(radius = 20.dp) {
                Column(Modifier.padding(14.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text("并发任务", color = colors.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                            Text(
                                "单个 AI 的任务并行能力；正式预测仍只调用当前 AI",
                                color = colors.textDim,
                                fontSize = 11.sp,
                            )
                        }
                        (1..3).forEach { value ->
                            Text(
                                value.toString(),
                                color = if (state.aiConcurrency == value) Color.White else colors.textSoft,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier
                                    .padding(start = 5.dp)
                                    .clip(CircleShape)
                                    .background(if (state.aiConcurrency == value) colors.accent else colors.surfaceStrong)
                                    .clickable { onConcurrency(value) }
                                    .padding(horizontal = 10.dp, vertical = 7.dp),
                            )
                        }
                    }
                }
            }
        }
        item {
            Button(
                onClick = { createNew = true },
                modifier = Modifier.fillMaxWidth().height(44.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = colors.accent),
            ) {
                Icon(Icons.Rounded.Add, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(7.dp))
                Text("添加 AI 接口", fontSize = 12.sp, fontWeight = FontWeight.Bold)
            }
        }

        configs.forEach { config ->
            item("config-${config.id}") {
                AiConfigCardV2(
                    config = config,
                    status = state.aiStatuses[config.id],
                    isActive = config.id == activeAiProfileId,
                    models = (listOf(config.model) + catalogs[config.id].orEmpty() + config.provider.fallbackModels)
                        .map(String::trim)
                        .filter(String::isNotBlank)
                        .distinct(),
                    onEdit = { editor = config },
                    onDelete = { pendingDelete = config },
                    onTest = { onTest(config.id) },
                    onLoad = { onLoadModels(config.id) },
                    onSetActive = { onSelectActive(config.id) },
                    onAnalyze = { onAnalyze(config.id) },
                    onModel = { onSelectModel(config.id, it) },
                    onMode = { onSelectMode(config.id, it) },
                    onReasoning = { onSelectReasoning(config.id, it) },
                )
            }
        }

        if (configs.isEmpty()) {
            item { EmptyState("还没有 AI 配置", "添加兼容 HTTPS 接口、模型与 API Key", false) }
        }
    }

    if (createNew || editor != null) {
        AiConfigEditorDialogV2(
            initial = editor ?: AiConfig(
                provider = AiProvider.DEEPSEEK,
                endpoint = AiProvider.DEEPSEEK.defaultEndpoint,
                model = AiProvider.DEEPSEEK.defaultModel,
            ),
            onDismiss = {
                createNew = false
                editor = null
            },
            onSave = {
                onSave(it)
                createNew = false
                editor = null
            },
        )
    }

    pendingDelete?.let { config ->
        AlertDialog(
            onDismissRequest = { pendingDelete = null },
            containerColor = colors.surface,
            shape = RoundedCornerShape(24.dp),
            title = { Text("删除 AI 配置？", color = colors.text, fontWeight = FontWeight.ExtraBold) },
            text = {
                Text(
                    "将删除“${config.displayName}”的接口、模型与密钥配置。此操作不会影响已经冻结的预测档案。",
                    color = colors.textSoft,
                    lineHeight = 20.sp,
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        onDelete(config.id)
                        pendingDelete = null
                    },
                ) { Text("确认删除", color = colors.red, fontWeight = FontWeight.Bold) }
            },
            dismissButton = {
                TextButton(onClick = { pendingDelete = null }) {
                    Text("取消", color = colors.textDim)
                }
            },
        )
    }
}

@Composable
private fun AiConfigCardV2(
    config: AiConfig,
    status: com.tianji.probabilitylab.nativev4.ai.AiRunStatus?,
    isActive: Boolean,
    models: List<String>,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
    onTest: () -> Unit,
    onLoad: () -> Unit,
    onSetActive: () -> Unit,
    onAnalyze: () -> Unit,
    onModel: (String) -> Unit,
    onMode: (AiAnalysisMode) -> Unit,
    onReasoning: (AiReasoningMode) -> Unit,
) {
    val colors = LocalTianjiColors.current
    var expanded by rememberSaveable(config.id) { mutableStateOf(false) }
    val tint = when (status?.state) {
        AiConnectionState.CONNECTED -> colors.green
        AiConnectionState.FAILED -> colors.red
        AiConnectionState.ANALYZING, AiConnectionState.TESTING -> colors.accent
        else -> colors.amber
    }
    SurfaceCard(radius = 20.dp) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    Modifier.size(41.dp).clip(RoundedCornerShape(14.dp)).background(colors.accentSoft),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        config.provider.label.take(2).uppercase(),
                        color = colors.accent,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(config.displayName, color = colors.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    Text(
                        config.model.ifBlank { "尚未选择模型" },
                        color = colors.textDim,
                        fontSize = 11.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Box(Modifier.size(7.dp).clip(CircleShape).background(tint))
                Spacer(Modifier.width(6.dp))
                Text(
                    aiStateLabelV594(status?.state),
                    color = tint,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                )
                IconButton(onClick = onEdit, modifier = Modifier.size(35.dp)) {
                    Icon(Icons.Rounded.Edit, contentDescription = "编辑", tint = colors.textDim, modifier = Modifier.size(18.dp))
                }
            }

            if (isActive) {
                Text(
                    "● 当前 AI · 主页正式预测只调用此配置",
                    color = colors.accent,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 7.dp),
                )
            }

            Text(
                status?.message ?: "配置已保存，尚未测试",
                color = tint,
                fontSize = 11.sp,
                lineHeight = 16.sp,
                modifier = Modifier.padding(top = if (isActive) 4.dp else 8.dp),
            )

            val capability = config.capability
            if (capability != null) {
                Spacer(Modifier.height(8.dp))
                Row(
                    Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    CapabilityBadgeV2("结构化", capability.structuredOutput)
                    CapabilityBadgeV2("推理控制", capability.reasoningControl)
                    CapabilityBadgeV2("推理已验证", capability.reasoningVerified)
                    CapabilityBadgeV2("Token 用量", capability.usageReturned)
                }
                Text(
                    "${capability.protocol.label} · ${status?.latencyMs ?: capability.latencyMs} ms",
                    color = colors.textDim,
                    fontSize = 10.sp,
                    modifier = Modifier.padding(top = 6.dp),
                )
            } else if (status?.latencyMs != null) {
                Text(
                    "接口延迟 ${status.latencyMs} ms",
                    color = colors.textDim,
                    fontSize = 10.sp,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }

            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                MiniButtonV2(
                    if (status?.state == AiConnectionState.ANALYZING) "正在分析" else "立即分析",
                    onAnalyze,
                    Modifier.weight(1.2f),
                    primary = true,
                )
                MiniButtonV2(
                    if (isActive) "当前 AI" else "设为当前",
                    if (isActive) ({}) else onSetActive,
                    Modifier.weight(0.9f),
                )
                MiniButtonV2(
                    if (expanded) "收起" else "更多",
                    { expanded = !expanded },
                    Modifier.weight(0.8f),
                )
            }

            if (expanded) {
                if (models.isNotEmpty()) {
                    Spacer(Modifier.height(10.dp))
                    Row(
                        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        models.forEach { model ->
                            val active = model == config.model
                            Text(
                                model,
                                color = if (active) colors.accent else colors.textSoft,
                                fontSize = 11.sp,
                                fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
                                modifier = Modifier
                                    .clip(CircleShape)
                                    .background(if (active) colors.accentSoft else colors.surfaceStrong)
                                    .border(
                                        1.dp,
                                        if (active) colors.accent.copy(alpha = 0.25f) else colors.line,
                                        CircleShape,
                                    )
                                    .clickable { onModel(model) }
                                    .padding(horizontal = 9.dp, vertical = 7.dp),
                            )
                        }
                    }
                }

                Spacer(Modifier.height(9.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    AiAnalysisMode.entries.forEach { mode ->
                        SmallChoiceV2(mode.label, config.analysisMode == mode, Modifier.weight(1f)) { onMode(mode) }
                    }
                }
                Spacer(Modifier.height(6.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    AiReasoningMode.entries.forEach { mode ->
                        SmallChoiceV2(mode.label, config.reasoningMode == mode, Modifier.weight(1f)) {
                            onReasoning(mode)
                        }
                    }
                }

                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    MiniButtonV2("读取模型", onLoad, Modifier.weight(1f))
                    MiniButtonV2("测试连接", onTest, Modifier.weight(1f))
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    "删除配置",
                    color = colors.red,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier
                        .align(Alignment.End)
                        .clip(CircleShape)
                        .clickable(onClick = onDelete)
                        .padding(horizontal = 8.dp, vertical = 5.dp),
                )
            }
        }
    }
}

private fun aiStateLabelV594(state: AiConnectionState?): String = when (state) {
    AiConnectionState.CONNECTED -> "连接正常"
    AiConnectionState.FAILED -> "连接失败"
    AiConnectionState.ANALYZING -> "分析中"
    AiConnectionState.TESTING -> "测试中"
    else -> "未测试"
}

@Composable
private fun AiConfigEditorDialogV2(
    initial: AiConfig,
    onDismiss: () -> Unit,
    onSave: (AiConfig) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val clipboard = LocalClipboardManager.current
    var provider by remember(initial.id) { mutableStateOf(initial.provider) }
    var name by remember(initial.id) { mutableStateOf(initial.name) }
    var endpoint by remember(initial.id) { mutableStateOf(endpointBaseForEditorV2(initial.endpoint)) }
    var model by remember(initial.id) { mutableStateOf(initial.model) }
    var apiKey by remember(initial.id) { mutableStateOf(initial.apiKey) }
    var apiKeyVisible by remember(initial.id) { mutableStateOf(false) }
    var customEndpoint by remember(initial.id) {
        mutableStateOf(
            initial.provider == AiProvider.COMPATIBLE ||
                initial.endpoint.trimEnd('/') != initial.provider.defaultEndpoint.trimEnd('/'),
        )
    }
    var apiRoute by remember(initial.id) {
        mutableStateOf(inferApiRouteV2(initial.endpoint, initial.provider))
    }
    var mode by remember(initial.id) { mutableStateOf(initial.analysisMode) }
    var reasoning by remember(initial.id) { mutableStateOf(initial.reasoningMode) }
    val fieldColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = colors.accent,
        unfocusedBorderColor = colors.lineStrong,
        focusedTextColor = colors.text,
        unfocusedTextColor = colors.text,
        focusedLabelColor = colors.accent,
        unfocusedLabelColor = colors.textDim,
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = colors.surface,
        shape = RoundedCornerShape(24.dp),
        title = {
            Text(
                if (initial.id.isBlank()) "添加 AI 接口" else "编辑 AI 接口",
                color = colors.text,
                fontWeight = FontWeight.ExtraBold,
            )
        },
        text = {
            Column(
                Modifier
                    .fillMaxWidth()
                    .fillMaxHeight(0.70f)
                    .verticalScroll(rememberScrollState()),
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    AiProvider.entries.forEach { item ->
                        SmallChoiceV2(item.editorLabelV2(), provider == item, Modifier.weight(1f)) {
                            provider = item
                            customEndpoint = item == AiProvider.COMPATIBLE
                            endpoint = endpointBaseForEditorV2(item.defaultEndpoint)
                            apiRoute = inferApiRouteV2(item.defaultEndpoint, item)
                            if (model.isBlank() && item.defaultModel.isNotBlank()) model = item.defaultModel
                        }
                    }
                }
                Spacer(Modifier.height(9.dp))
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("名称") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = fieldColors,
                    shape = RoundedCornerShape(14.dp),
                )
                Spacer(Modifier.height(8.dp))
                Text("接口来源", color = colors.textDim, fontSize = 11.sp)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    SmallChoiceV2(
                        "官方接口",
                        !customEndpoint && provider != AiProvider.COMPATIBLE,
                        Modifier.weight(1f),
                    ) {
                        if (provider != AiProvider.COMPATIBLE) {
                            customEndpoint = false
                            endpoint = endpointBaseForEditorV2(provider.defaultEndpoint)
                            apiRoute = inferApiRouteV2(provider.defaultEndpoint, provider)
                        }
                    }
                    SmallChoiceV2(
                        "自定义 / 中转",
                        customEndpoint || provider == AiProvider.COMPATIBLE,
                        Modifier.weight(1f),
                    ) {
                        customEndpoint = true
                    }
                }
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = endpoint,
                    onValueChange = { endpoint = it },
                    label = { Text("API Base URL / 接口地址") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    readOnly = !customEndpoint && provider != AiProvider.COMPATIBLE,
                    supportingText = {
                        Text(
                            if (customEndpoint || provider == AiProvider.COMPATIBLE) {
                                "中转站可直接填 https://example.com/v1，保存时自动补齐请求路径"
                            } else {
                                "官方地址由天机维护；切换到“自定义 / 中转”后可修改"
                            },
                            fontSize = 10.sp,
                        )
                    },
                    colors = fieldColors,
                    shape = RoundedCornerShape(14.dp),
                )
                Spacer(Modifier.height(8.dp))
                Text("API 协议", color = colors.textDim, fontSize = 11.sp)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    AiApiRouteV2.entries.forEach { item ->
                        SmallChoiceV2(item.label, apiRoute == item, Modifier.weight(1f)) {
                            apiRoute = item
                        }
                    }
                }
                Text(
                    when (apiRoute) {
                        AiApiRouteV2.AUTO -> "自动：OpenAI 默认 Responses，其余兼容接口默认 Chat Completions"
                        AiApiRouteV2.CHAT_COMPLETIONS -> "适用于大多数 OpenAI 兼容中转站"
                        AiApiRouteV2.RESPONSES -> "适用于支持 OpenAI Responses API 的官方或中转接口"
                    },
                    color = colors.textDim,
                    fontSize = 10.sp,
                    lineHeight = 15.sp,
                    modifier = Modifier.padding(top = 4.dp),
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = model,
                    onValueChange = { model = it },
                    label = { Text("模型名") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = fieldColors,
                    shape = RoundedCornerShape(14.dp),
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = apiKey,
                    onValueChange = { apiKey = it },
                    label = { Text("API Key（加密保存）") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    visualTransformation = if (apiKeyVisible) {
                        VisualTransformation.None
                    } else {
                        PasswordVisualTransformation()
                    },
                    trailingIcon = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            IconButton(
                                onClick = {
                                    if (apiKey.isNotBlank()) clipboard.setText(AnnotatedString(apiKey))
                                },
                                enabled = apiKey.isNotBlank(),
                            ) {
                                Icon(Icons.Rounded.ContentCopy, contentDescription = "复制 Key")
                            }
                            IconButton(onClick = { apiKeyVisible = !apiKeyVisible }) {
                                Icon(
                                    if (apiKeyVisible) Icons.Rounded.VisibilityOff else Icons.Rounded.Visibility,
                                    contentDescription = if (apiKeyVisible) "隐藏 Key" else "显示 Key",
                                )
                            }
                        }
                    },
                    colors = fieldColors,
                    shape = RoundedCornerShape(14.dp),
                )
                Spacer(Modifier.height(9.dp))
                Text("历史窗口", color = colors.textDim, fontSize = 11.sp)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    AiAnalysisMode.entries.forEach { item ->
                        SmallChoiceV2(item.label, mode == item, Modifier.weight(1f)) { mode = item }
                    }
                }
                Spacer(Modifier.height(8.dp))
                Text("推理强度", color = colors.textDim, fontSize = 11.sp)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    AiReasoningMode.entries.forEach { item ->
                        SmallChoiceV2(item.label, reasoning == item, Modifier.weight(1f)) { reasoning = item }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    val normalizedEndpoint = normalizeAiEndpointV2(endpoint, provider, apiRoute)
                    val connectionChanged =
                        provider != initial.provider ||
                            normalizedEndpoint != initial.endpoint.trim() ||
                            model.trim() != initial.model.trim() ||
                            apiKey.trim() != initial.apiKey.trim()
                    onSave(
                        initial.copy(
                            name = name.trim(),
                            provider = provider,
                            endpoint = normalizedEndpoint,
                            model = model.trim(),
                            apiKey = apiKey.trim(),
                            analysisMode = mode,
                            reasoningMode = reasoning,
                            capability = if (connectionChanged) null else initial.capability,
                        ),
                    )
                },
                enabled = endpoint.startsWith("https://") && apiKey.isNotBlank(),
            ) {
                Text("保存", color = colors.accent, fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("取消", color = colors.textDim) }
        },
    )
}

@Composable
private fun CapabilityBadgeV2(text: String, supported: Boolean) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .clip(CircleShape)
            .background(if (supported) colors.accentSoft else colors.surfaceStrong)
            .border(
                1.dp,
                if (supported) colors.accent.copy(alpha = 0.22f) else colors.line,
                CircleShape,
            )
            .padding(horizontal = 8.dp, vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Box(
            Modifier.size(6.dp).clip(CircleShape).background(if (supported) colors.green else colors.textDim),
        )
        Text(
            text,
            color = if (supported) colors.textSoft else colors.textDim,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun DataSettingsPageV2(state: AppUiState, onBack: () -> Unit, modifier: Modifier) {
    val colors = LocalTianjiColors.current
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item { SettingsPageHeaderV2("数据与同步", "真实历史、档案与后台状态", onBack) }
        item {
            SurfaceCard(radius = 20.dp) {
                Column(Modifier.padding(14.dp)) {
                    EvidenceRowV2("原生 SQLite 持久化", true)
                    EvidenceRowV2("断网只读真实历史，不生成假开奖", true)
                    EvidenceRowV2("本地与 AI 档案按目标期精确结算", true)
                    EvidenceRowV2(
                        state.snapshot?.sourceHealth?.message ?: state.error ?: "等待首次同步",
                        state.snapshot?.sourceHealth?.isFresh == true,
                    )
                    HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp), color = colors.line)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        CompactMetricV2(
                            "接口历史",
                            (state.snapshot?.history?.size ?: 0).toString(),
                            Modifier.weight(1f),
                        )
                        CompactMetricV2(
                            "预测档案",
                            (state.records.size + state.aiRecords.size + state.aiConsensusRecords.size).toString(),
                            Modifier.weight(1f),
                        )
                        CompactMetricV2(
                            "完整性",
                            if (state.archiveIntegrity.isValid) "正常" else "异常",
                            Modifier.weight(1f),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AppearanceSettingsPageV2(
    palette: PaletteMode,
    appearance: AppearanceMode,
    onPalette: (PaletteMode) -> Unit,
    onAppearance: (AppearanceMode) -> Unit,
    onBack: () -> Unit,
    modifier: Modifier,
) {
    val colors = LocalTianjiColors.current
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item { SettingsPageHeaderV2("外观与主题", "显示模式与强调色分开设置", onBack) }
        item {
            SurfaceCard(radius = 20.dp) {
                Column(Modifier.padding(14.dp)) {
                    Text("显示模式", color = colors.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    Text("浅色、深色和 OLED 不再与强调色绑定", color = colors.textDim, fontSize = 11.sp)
                    Spacer(Modifier.height(10.dp))
                    AppearanceMode.entries.chunked(2).forEach { row ->
                        Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                            row.forEach { item ->
                                AppearanceChoiceV2(item.label, appearance == item, Modifier.weight(1f)) {
                                    onAppearance(item)
                                }
                            }
                            if (row.size == 1) Spacer(Modifier.weight(1f))
                        }
                        Spacer(Modifier.height(7.dp))
                    }
                }
            }
        }
        item {
            SurfaceCard(radius = 20.dp) {
                Column(Modifier.padding(14.dp)) {
                    Text("强调色", color = colors.text, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    Text(
                        if (colors.monetSupported) "系统 Monet 已连接" else "当前系统不支持 Monet，使用后备色",
                        color = colors.textDim,
                        fontSize = 11.sp,
                    )
                    Spacer(Modifier.height(10.dp))
                    PaletteMode.entries.filter { it != PaletteMode.OLED }.chunked(2).forEach { row ->
                        Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                            row.forEach { item ->
                                AccentChoiceV2(item, palette == item, Modifier.weight(1f)) { onPalette(item) }
                            }
                            if (row.size == 1) Spacer(Modifier.weight(1f))
                        }
                        Spacer(Modifier.height(7.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun RecentHistoryPageV2(state: AppUiState, onBack: () -> Unit, modifier: Modifier) {
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item { SettingsPageHeaderV2("最近开奖", "本机已核验的连续历史", onBack) }
        state.snapshot?.history?.takeLast(30)?.asReversed()?.forEach { draw ->
            item(draw.period) { HistoryCardV2(draw) }
        }
        if (state.snapshot?.history.isNullOrEmpty()) {
            item { EmptyState("暂无历史", state.error ?: "等待接口同步", state.isLoading) }
        }
    }
}

@Composable
private fun AboutPageV2(onBack: () -> Unit, modifier: Modifier) {
    val colors = LocalTianjiColors.current
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item { SettingsPageHeaderV2("关于天机", "概率实验与真实前向验证工具", onBack) }
        item {
            SurfaceCard(radius = 20.dp) {
                Column(Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        Modifier.size(58.dp).clip(RoundedCornerShape(19.dp)).background(colors.accentSoft),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(Icons.Rounded.AutoAwesome, null, tint = colors.accent, modifier = Modifier.size(30.dp))
                    }
                    Spacer(Modifier.height(10.dp))
                    Text(
                        "天机 ${BuildConfig.VERSION_NAME}",
                        color = colors.text,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.ExtraBold,
                    )
                    Text(
                        "本应用只用于统计实验、模型比较和前向验证，不承诺盈利或必中。",
                        color = colors.textDim,
                        fontSize = 11.sp,
                        lineHeight = 17.sp,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun HistoryCardV2(draw: Draw) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(colors.surface)
            .border(1.dp, colors.line, RoundedCornerShape(16.dp))
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.width(76.dp)) {
            Text(
                draw.period.takeLast(8),
                color = colors.textSoft,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
            )
            Text(draw.drawTime.takeLast(8), color = colors.textDim, fontSize = 9.sp)
        }
        Row(Modifier.weight(1f), horizontalArrangement = Arrangement.SpaceBetween) {
            draw.numbers.forEach { LotteryBall(it, size = 21.dp) }
        }
    }
}

@Composable
private fun SmallChoiceV2(
    text: String,
    active: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Box(
        modifier = modifier
            .height(36.dp)
            .clip(RoundedCornerShape(11.dp))
            .background(if (active) colors.accentSoft else colors.surfaceStrong)
            .border(
                1.dp,
                if (active) colors.accent.copy(alpha = 0.25f) else colors.line,
                RoundedCornerShape(11.dp),
            )
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text,
            color = if (active) colors.accent else colors.textSoft,
            fontSize = 11.sp,
            fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun MiniButtonV2(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    primary: Boolean = false,
) {
    val colors = LocalTianjiColors.current
    Box(
        modifier = modifier
            .height(37.dp)
            .clip(RoundedCornerShape(11.dp))
            .background(if (primary) colors.accent else colors.surfaceStrong)
            .border(1.dp, if (primary) Color.Transparent else colors.line, RoundedCornerShape(11.dp))
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text,
            color = if (primary) Color.White else colors.textSoft,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun AppearanceChoiceV2(
    text: String,
    active: Boolean,
    modifier: Modifier,
    onClick: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = modifier
            .height(46.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(if (active) colors.accentSoft else colors.surfaceStrong)
            .border(
                1.dp,
                if (active) colors.accent.copy(alpha = 0.28f) else colors.line,
                RoundedCornerShape(14.dp),
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 11.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            if (active) Icons.Rounded.Verified else Icons.Rounded.Settings,
            null,
            tint = if (active) colors.accent else colors.textDim,
            modifier = Modifier.size(18.dp),
        )
        Spacer(Modifier.width(8.dp))
        Text(text, color = colors.textSoft, fontSize = 11.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun AccentChoiceV2(
    item: PaletteMode,
    active: Boolean,
    modifier: Modifier,
    onClick: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = modifier
            .height(46.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(if (active) colors.accentSoft else colors.surfaceStrong)
            .border(
                1.dp,
                if (active) colors.accent.copy(alpha = 0.28f) else colors.line,
                RoundedCornerShape(14.dp),
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 11.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier
                .size(18.dp)
                .clip(CircleShape)
                .background(item.preview)
                .border(1.dp, Color.White.copy(alpha = 0.25f), CircleShape),
        )
        Spacer(Modifier.width(8.dp))
        Text(item.label, color = colors.textSoft, fontSize = 11.sp, fontWeight = FontWeight.Bold)
    }
}
