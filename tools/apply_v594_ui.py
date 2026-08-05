from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {text.count(old)}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, found {count}")
    return updated


# ---------------------------------------------------------------------------
# App shell: improve readable sizing and turn the center AI entry into a true
# primary action with a running-state progress ring.
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AppShellV2.kt"
text = read(path)
text = text.replace(".height(54.dp)", ".height(58.dp)", 1)
text = text.replace("fontSize = 10.sp,\n                lineHeight = 13.sp,", "fontSize = 11.sp,\n                lineHeight = 15.sp,", 1)
text = replace_once(
    text,
    "    onChat: () -> Unit,\n    modifier: Modifier = Modifier,\n)",
    "    onChat: () -> Unit,\n    isAiRunning: Boolean = false,\n    modifier: Modifier = Modifier,\n)",
    "MainBottomBar parameters",
)
text = text.replace(".height(60.dp)", ".height(64.dp)", 1)
text = replace_once(
    text,
    "ChatNavItem(onClick = onChat, modifier = Modifier.weight(1f))",
    "ChatNavItem(\n                    onClick = onChat,\n                    isRunning = isAiRunning,\n                    modifier = Modifier.weight(1f),\n                )",
    "ChatNavItem call",
)
text = text.replace("fontSize = 9.sp,\n            fontWeight = if (active)", "fontSize = 10.sp,\n            fontWeight = if (active)", 1)
chat_function = r'''@Composable
private fun ChatNavItem(
    onClick: () -> Unit,
    isRunning: Boolean,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    val interaction = remember { MutableInteractionSource() }
    Column(
        modifier = modifier
            .fillMaxHeight()
            .clip(RoundedCornerShape(16.dp))
            .clickable(
                interactionSource = interaction,
                indication = null,
                onClick = onClick,
            ),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(
            modifier = Modifier.size(42.dp),
            contentAlignment = Alignment.Center,
        ) {
            if (isRunning) {
                CircularProgressIndicator(
                    modifier = Modifier.size(42.dp),
                    color = colors.accent,
                    strokeWidth = 2.dp,
                )
            }
            Box(
                modifier = Modifier
                    .size(35.dp)
                    .shadow(
                        elevation = if (colors.isOled) 0.dp else 5.dp,
                        shape = CircleShape,
                        ambientColor = colors.accent.copy(alpha = 0.22f),
                        spotColor = colors.accent.copy(alpha = 0.22f),
                    )
                    .clip(CircleShape)
                    .background(
                        Brush.linearGradient(
                            listOf(colors.accent, colors.violet),
                        ),
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Rounded.AutoAwesome,
                    contentDescription = if (isRunning) "查看正在运行的 AI 任务" else "打开 AI 对话",
                    tint = Color.White,
                    modifier = Modifier.size(18.dp),
                )
            }
        }
        Text(
            if (isRunning) "运行中" else "AI",
            color = colors.accent,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}
'''
text = regex_once(
    text,
    r"@Composable\nprivate fun ChatNavItem\(.*?\n}\n\n@Composable\nfun CompactLotterySwitcher",
    chat_function + "\n@Composable\nfun CompactLotterySwitcher",
    "ChatNavItem implementation",
)
text = text.replace(".height(44.dp)", ".height(48.dp)", 1)
text = text.replace(".height(43.dp)", ".height(47.dp)", 1)
write(path, text)


# ---------------------------------------------------------------------------
# App root: feed AI running state into the central action.
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt"
text = read(path)
text = replace_once(
    text,
    "                                onChat = { showChat = true },\n                                modifier = Modifier",
    "                                onChat = { showChat = true },\n                                isAiRunning = state.isAiAnalyzing || chatRunning,\n                                modifier = Modifier",
    "MainBottomBar AI state",
)
write(path, text)


# ---------------------------------------------------------------------------
# Lottery balls: fixed number palette + restrained dimensional gradient,
# highlight and inner ring. This keeps number identity stable across App/Web.
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Components.kt"
text = read(path)
lottery_ball = r'''@Composable
fun LotteryBall(
    number: Int,
    modifier: Modifier = Modifier,
    size: Dp = 42.dp,
    muted: Boolean = false,
) {
    val pair = ballColors(number)
    val alpha = if (muted) 0.42f else 1f
    Box(
        modifier = modifier
            .size(size)
            .shadow(
                elevation = if (muted) 1.dp else 5.dp,
                shape = CircleShape,
                ambientColor = pair.second.copy(alpha = 0.24f),
                spotColor = pair.second.copy(alpha = 0.24f),
            )
            .clip(CircleShape)
            .background(
                Brush.linearGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.18f * alpha),
                        pair.first.copy(alpha = alpha),
                        pair.second.copy(alpha = alpha),
                    ),
                ),
            )
            .border(1.dp, Color.White.copy(alpha = 0.26f * alpha), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.radialGradient(
                        colors = listOf(
                            Color.White.copy(alpha = 0.34f * alpha),
                            Color.Transparent,
                        ),
                        radius = size.value * 0.72f,
                    ),
                ),
        )
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(3.dp)
                .border(1.dp, Color.White.copy(alpha = 0.13f * alpha), CircleShape),
        )
        Text(
            text = number.toString(),
            color = Color.White.copy(alpha = alpha),
            fontSize = when {
                size >= 42.dp -> 16.sp
                size >= 36.dp -> 14.sp
                else -> 11.sp
            },
            fontWeight = FontWeight.ExtraBold,
        )
    }
}
'''
text = regex_once(
    text,
    r"@Composable\nfun LotteryBall\(.*?\n}\n\n@Composable\nfun EvidencePill",
    lottery_ball + "\n@Composable\nfun EvidencePill",
    "LotteryBall implementation",
)
write(path, text)


# ---------------------------------------------------------------------------
# Archive: add settlement filters and an explicit expandable verification area
# with one-tap hash copy.
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedArchive.kt"
text = read(path)
text = replace_once(
    text,
    "import androidx.compose.foundation.layout.fillMaxWidth\n",
    "import androidx.compose.foundation.horizontalScroll\nimport androidx.compose.foundation.layout.fillMaxWidth\n",
    "archive horizontal scroll import",
)
text = replace_once(
    text,
    "import androidx.compose.foundation.lazy.LazyColumn\n",
    "import androidx.compose.foundation.lazy.LazyColumn\nimport androidx.compose.foundation.rememberScrollState\n",
    "archive scroll state import",
)
text = replace_once(
    text,
    "import androidx.compose.material.icons.rounded.AutoAwesome\n",
    "import androidx.compose.material.icons.rounded.AutoAwesome\nimport androidx.compose.material.icons.rounded.ContentCopy\n",
    "archive copy icon import",
)
text = replace_once(
    text,
    "import androidx.compose.material.icons.rounded.KeyboardArrowDown\n",
    "import androidx.compose.material.icons.rounded.KeyboardArrowDown\nimport androidx.compose.material.icons.rounded.KeyboardArrowUp\n",
    "archive arrow icon import",
)
text = replace_once(
    text,
    "import androidx.compose.ui.Alignment\n",
    "import androidx.compose.ui.Alignment\nimport androidx.compose.ui.platform.LocalClipboardManager\n",
    "archive clipboard import",
)
text = replace_once(
    text,
    "import androidx.compose.ui.text.font.FontWeight\n",
    "import androidx.compose.ui.text.AnnotatedString\nimport androidx.compose.ui.text.font.FontWeight\n",
    "archive annotated string import",
)
text = replace_once(
    text,
    "private enum class ArchiveDisplayLimit(val label: String, val count: Int?) {\n    RECENT_8(\"最近 8 条\", 8),\n    RECENT_20(\"最近 20 条\", 20),\n    ALL(\"显示全部\", null),\n}\n",
    "private enum class ArchiveDisplayLimit(val label: String, val count: Int?) {\n    RECENT_8(\"最近 8 条\", 8),\n    RECENT_20(\"最近 20 条\", 20),\n    ALL(\"显示全部\", null),\n}\n\nprivate enum class ArchiveSettlementFilter(val label: String) {\n    ALL(\"全部\"),\n    PENDING(\"待开奖\"),\n    HIT(\"已命中\"),\n    MISSED(\"未命中\"),\n}\n",
    "archive filter enum",
)
text = replace_once(
    text,
    "    var limitMenuExpanded by rememberSaveable { mutableStateOf(false) }\n",
    "    var limitMenuExpanded by rememberSaveable { mutableStateOf(false) }\n    var settlementFilterName by rememberSaveable(state.lottery.apiKey) {\n        mutableStateOf(ArchiveSettlementFilter.ALL.name)\n    }\n",
    "archive filter state",
)
text = replace_once(
    text,
    "    val maxItems = selectedLimit.count ?: Int.MAX_VALUE\n",
    "    val maxItems = selectedLimit.count ?: Int.MAX_VALUE\n    val settlementFilter = ArchiveSettlementFilter.entries.firstOrNull {\n        it.name == settlementFilterName\n    } ?: ArchiveSettlementFilter.ALL\n",
    "archive selected filter",
)
text = replace_once(
    text,
    "    val aiRate = if (aiSettled > 0) {\n        \"${(state.aiLiveAudit.top6Rate * 100).format1V2()}%\"\n    } else {\n        \"暂无\"\n    }\n",
    "    val aiRate = if (aiSettled > 0) {\n        \"${(state.aiLiveAudit.top6Rate * 100).format1V2()}%\"\n    } else {\n        \"暂无\"\n    }\n    val consensusRecords = state.aiConsensusRecords.filter {\n        archiveMatchesFilter(settlementFilter, it.top6Hit, it.top7Hit)\n    }\n    val aiRecords = state.aiRecords.filter {\n        archiveMatchesFilter(settlementFilter, it.top6Hit, it.top7Hit)\n    }\n    val nativeRecords = state.records.filter {\n        archiveMatchesFilter(settlementFilter, it.top6Hit, it.top7Hit)\n    }\n",
    "archive filtered records",
)
filter_item = '''        item("archive-filters") {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                ArchiveSettlementFilter.entries.forEach { option ->
                    val active = option == settlementFilter
                    Text(
                        option.label,
                        color = if (active) colors.accent else colors.textSoft,
                        fontSize = 11.sp,
                        fontWeight = if (active) FontWeight.Bold else FontWeight.Medium,
                        modifier = Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(if (active) colors.accentSoft else colors.surfaceStrong)
                            .border(
                                1.dp,
                                if (active) colors.accent.copy(alpha = 0.24f) else colors.line,
                                RoundedCornerShape(12.dp),
                            )
                            .clickable { settlementFilterName = option.name }
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                    )
                }
            }
        }

'''
text = replace_once(
    text,
    "        if (state.aiConsensusRecords.isNotEmpty()) {\n",
    filter_item + "        if (consensusRecords.isNotEmpty()) {\n",
    "archive filter row",
)
text = text.replace("count = state.aiConsensusRecords.size", "count = consensusRecords.size")
text = text.replace("state.aiConsensusRecords.take(maxItems).forEach", "consensusRecords.take(maxItems).forEach")
text = text.replace("if (state.aiRecords.isNotEmpty())", "if (aiRecords.isNotEmpty())")
text = text.replace("count = state.aiRecords.size", "count = aiRecords.size")
text = text.replace("state.aiRecords.take(maxItems).forEach", "aiRecords.take(maxItems).forEach")
text = text.replace("if (state.records.isNotEmpty())", "if (nativeRecords.isNotEmpty())")
text = text.replace("count = state.records.size", "count = nativeRecords.size")
text = text.replace("state.records.take(maxItems).forEach", "nativeRecords.take(maxItems).forEach")
text = replace_once(
    text,
    "        if (state.records.isEmpty() && state.aiRecords.isEmpty() && state.aiConsensusRecords.isEmpty()) {\n            item { EmptyState(\"暂无冻结档案\", \"完成一次预测后会在开奖前自动锁定\", false) }\n        }\n",
    "        if (nativeRecords.isEmpty() && aiRecords.isEmpty() && consensusRecords.isEmpty()) {\n            item {\n                EmptyState(\n                    if (settlementFilter == ArchiveSettlementFilter.ALL) \"暂无冻结档案\" else \"当前筛选暂无档案\",\n                    if (settlementFilter == ArchiveSettlementFilter.ALL) {\n                        \"完成一次预测后会在开奖前自动锁定\"\n                    } else {\n                        \"切换筛选条件可查看其他结算状态\"\n                    },\n                    false,\n                )\n            }\n        }\n",
    "archive empty state",
)
text = replace_once(
    text,
    "@Composable\nprivate fun ArchiveLabelV2(",
    "private fun archiveMatchesFilter(\n    filter: ArchiveSettlementFilter,\n    top6Hit: Boolean?,\n    top7Hit: Boolean?,\n): Boolean = when (filter) {\n    ArchiveSettlementFilter.ALL -> true\n    ArchiveSettlementFilter.PENDING -> top6Hit == null && top7Hit == null\n    ArchiveSettlementFilter.HIT -> top6Hit == true || top7Hit == true\n    ArchiveSettlementFilter.MISSED -> top6Hit == false && top7Hit == false\n}\n\n@Composable\nprivate fun ArchiveLabelV2(",
    "archive filter helper",
)
text = replace_once(
    text,
    "    var hashExpanded by rememberSaveable(hash) { mutableStateOf(false) }\n    val colors = LocalTianjiColors.current\n",
    "    var hashExpanded by rememberSaveable(hash) { mutableStateOf(false) }\n    val colors = LocalTianjiColors.current\n    val clipboard = LocalClipboardManager.current\n",
    "archive clipboard state",
)
old_footer = '''            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                Text(
                    if (hashExpanded) "哈希 $hash" else "点击卡片查看完整哈希",
                    color = if (hashExpanded) colors.textSoft else colors.textDim,
                    fontSize = 10.sp,
                    lineHeight = 14.sp,
                    maxLines = if (hashExpanded) 3 else 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.size(8.dp))
                Text(time, color = colors.textDim, fontSize = 10.sp)
            }
'''
new_footer = '''            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(
                    if (hashExpanded) "验证信息已展开" else "查看验证信息",
                    color = if (hashExpanded) colors.textSoft else colors.textDim,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    modifier = Modifier.weight(1f),
                )
                Text(time, color = colors.textDim, fontSize = 10.sp)
                Spacer(Modifier.size(5.dp))
                Icon(
                    if (hashExpanded) Icons.Rounded.KeyboardArrowUp else Icons.Rounded.KeyboardArrowDown,
                    contentDescription = if (hashExpanded) "收起验证信息" else "展开验证信息",
                    tint = colors.textDim,
                    modifier = Modifier.size(18.dp),
                )
            }
            if (hashExpanded) {
                Spacer(Modifier.height(9.dp))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(colors.surfaceStrong)
                        .border(1.dp, colors.line, RoundedCornerShape(12.dp))
                        .padding(horizontal = 10.dp, vertical = 9.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        "哈希 $hash",
                        color = colors.textSoft,
                        fontSize = 10.sp,
                        lineHeight = 15.sp,
                        modifier = Modifier.weight(1f),
                    )
                    Icon(
                        Icons.Rounded.ContentCopy,
                        contentDescription = "复制完整哈希",
                        tint = colors.accent,
                        modifier = Modifier
                            .size(30.dp)
                            .clip(CircleShape)
                            .clickable { clipboard.setText(AnnotatedString(hash)) }
                            .padding(6.dp),
                    )
                }
            }
'''
text = replace_once(text, old_footer, new_footer, "archive verification footer")
write(path, text)


# ---------------------------------------------------------------------------
# Settings: Chinese status labels, collapsed advanced controls, prominent
# primary analysis action, and delete confirmation.
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/SettingsHubV2.kt"
text = read(path)
text = replace_once(
    text,
    "    var editor by remember { mutableStateOf<AiConfig?>(null) }\n    var createNew by remember { mutableStateOf(false) }\n",
    "    var editor by remember { mutableStateOf<AiConfig?>(null) }\n    var createNew by remember { mutableStateOf(false) }\n    var pendingDelete by remember { mutableStateOf<AiConfig?>(null) }\n",
    "AI delete state",
)
text = replace_once(
    text,
    "                    onDelete = { onDelete(config.id) },",
    "                    onDelete = { pendingDelete = config },",
    "AI delete action",
)
confirm_dialog = '''
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
'''
text = replace_once(
    text,
    "    }\n}\n\n@Composable\nprivate fun AiConfigCardV2(",
    "    }\n" + confirm_dialog + "}\n\n@Composable\nprivate fun AiConfigCardV2(",
    "AI delete confirmation dialog",
)
new_ai_card = r'''@Composable
private fun AiConfigCardV2(
    config: AiConfig,
    status: com.tianji.probabilitylab.nativev4.ai.AiRunStatus?,
    models: List<String>,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
    onTest: () -> Unit,
    onLoad: () -> Unit,
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
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                )
                IconButton(onClick = onEdit, modifier = Modifier.size(35.dp)) {
                    Icon(Icons.Rounded.Edit, contentDescription = "编辑", tint = colors.textDim, modifier = Modifier.size(18.dp))
                }
            }

            Text(
                status?.message ?: "配置已保存，尚未测试",
                color = tint,
                fontSize = 11.sp,
                lineHeight = 16.sp,
                modifier = Modifier.padding(top = 8.dp),
            )

            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                MiniButtonV2(
                    if (status?.state == AiConnectionState.ANALYZING) "正在分析" else "立即分析",
                    onAnalyze,
                    Modifier.weight(1.25f),
                    primary = true,
                )
                MiniButtonV2(
                    if (expanded) "收起设置" else "更多设置",
                    { expanded = !expanded },
                    Modifier.weight(1f),
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
                                fontSize = 10.sp,
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
                    fontSize = 10.sp,
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
'''
text = regex_once(
    text,
    r"@Composable\nprivate fun AiConfigCardV2\(.*?\n}\n\n@Composable\nprivate fun AiConfigEditorDialogV2",
    new_ai_card + "\n@Composable\nprivate fun AiConfigEditorDialogV2",
    "AI config card implementation",
)
write(path, text)


# ---------------------------------------------------------------------------
# Typography: use readable defaults while still respecting the user's system
# font scale.
# ---------------------------------------------------------------------------
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/theme/TianjiTheme.kt"
text = read(path)
replacements = {
    "bodySmall = TextStyle(fontSize = 12.sp, lineHeight = 18.sp)": "bodySmall = TextStyle(fontSize = 13.sp, lineHeight = 19.sp)",
    "bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 21.sp)": "bodyMedium = TextStyle(fontSize = 15.sp, lineHeight = 22.sp)",
    "labelSmall = TextStyle(fontSize = 10.sp, lineHeight = 15.sp": "labelSmall = TextStyle(fontSize = 11.sp, lineHeight = 16.sp",
    "labelMedium = TextStyle(fontSize = 12.sp, lineHeight = 17.sp": "labelMedium = TextStyle(fontSize = 13.sp, lineHeight = 18.sp",
    "titleSmall = TextStyle(fontSize = 15.sp, lineHeight = 20.sp": "titleSmall = TextStyle(fontSize = 16.sp, lineHeight = 21.sp",
}
for old, new in replacements.items():
    text = replace_once(text, old, new, f"typography {old}")
write(path, text)


# ---------------------------------------------------------------------------
# Server console: consolidate the legacy style/script layers into one runtime
# asset and append V5.9.4 mobile, accessibility and number-gradient polish.
# ---------------------------------------------------------------------------
extra_css = r'''
/* Tianji Console V5.9.4 unified polish */
html.tianji-console-v5 body{font-size:14px}
html.tianji-console-v5 button:focus-visible,
html.tianji-console-v5 input:focus-visible,
html.tianji-console-v5 select:focus-visible,
html.tianji-console-v5 summary:focus-visible{
  outline:3px solid color-mix(in srgb,var(--primary) 28%,transparent);
  outline-offset:2px;
}
html.tianji-console-v5 .number,
html.tianji-console-v5 .v3-ball,
html.tianji-console-v5 .ball{
  --ball-a:#718096;--ball-b:#313744;--ball-text:#fff;
  color:var(--ball-text)!important;
  background:
    radial-gradient(circle at 30% 22%,rgba(255,255,255,.46),rgba(255,255,255,0) 34%),
    linear-gradient(145deg,var(--ball-a),var(--ball-b))!important;
  border:1px solid rgba(255,255,255,.24)!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.28),0 5px 13px color-mix(in srgb,var(--ball-b) 28%,transparent)!important;
}
html.tianji-console-v5 [data-number="1"]{--ball-a:#ffe36d;--ball-b:#e5a900;--ball-text:#3b2a00}
html.tianji-console-v5 [data-number="2"]{--ball-a:#61b1ff;--ball-b:#1768c7}
html.tianji-console-v5 [data-number="3"]{--ball-a:#9299a8;--ball-b:#454b59}
html.tianji-console-v5 [data-number="4"]{--ball-a:#ffb25e;--ball-b:#e66c0c}
html.tianji-console-v5 [data-number="5"]{--ball-a:#6fd8ff;--ball-b:#168dbb}
html.tianji-console-v5 [data-number="6"]{--ball-a:#9b86ff;--ball-b:#5436cf}
html.tianji-console-v5 [data-number="7"]{--ball-a:#e8ebf1;--ball-b:#a8afbc;--ball-text:#252a34}
html.tianji-console-v5 [data-number="8"]{--ball-a:#ff827c;--ball-b:#ca302d}
html.tianji-console-v5 [data-number="9"]{--ball-a:#d05a87;--ball-b:#7b173e}
html.tianji-console-v5 [data-number="10"]{--ball-a:#69d7a0;--ball-b:#16885a}
html.tianji-console-v5 .diag[data-severity="bad"]{border-color:color-mix(in srgb,var(--bad) 25%,var(--v5-line))}
html.tianji-console-v5 .diag[data-severity="warn"]{border-color:color-mix(in srgb,var(--warn) 22%,var(--v5-line))}
html.tianji-console-v5 .card:not(.quick-card),
html.tianji-console-v5 .overview-card,
html.tianji-console-v5 .v3-record{box-shadow:0 4px 14px rgba(40,45,72,.055)}

@media(max-width:740px){
  html.tianji-console-v5 .topbar{
    position:sticky!important;top:0!important;z-index:60!important;
    min-height:52px!important;margin:0 -2px 8px!important;padding:5px 4px!important;
    border:0!important;background:color-mix(in srgb,var(--v5-page) 90%,transparent)!important;
    backdrop-filter:blur(18px) saturate(125%)!important;
    -webkit-backdrop-filter:blur(18px) saturate(125%)!important;
  }
  html.tianji-console-v5 .topbar .brand{display:flex!important;gap:7px!important;margin-right:auto!important}
  html.tianji-console-v5 .topbar .brand .mark{width:34px!important;height:34px!important;flex-basis:34px!important;border-radius:12px!important}
  html.tianji-console-v5 .topbar .brand h1{font-size:14px!important}
  html.tianji-console-v5 .topbar .brand p{display:none!important}
  html.tianji-console-v5 .topbar .status{display:flex!important;min-height:34px!important;padding:0 9px!important;font-size:10px!important;box-shadow:none!important}
  html.tianji-console-v5 .topbar .icon-btn{width:36px!important;height:36px!important;min-height:36px!important}
  html.tianji-console-v5 .panel-head h2{font-size:23px}
  html.tianji-console-v5 .panel-head p{font-size:11px}
}
@media(max-width:430px){
  html.tianji-console-v5 .topbar .status{max-width:92px;overflow:hidden;white-space:nowrap}
  html.tianji-console-v5 .numbers{grid-template-columns:repeat(5,minmax(0,1fr))!important;gap:7px!important}
  html.tianji-console-v5 .number{width:min(42px,100%);justify-self:center;font-size:11px!important}
}
@media(prefers-reduced-motion:reduce){
  html.tianji-console-v5 *,html.tianji-console-v5 *:before,html.tianji-console-v5 *:after{
    scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;
  }
}
'''

extra_js = r'''
(()=>{
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const enhanceBalls=(root=document)=>{
    qa('.number,.v3-ball,.ball',root).forEach(el=>{
      const n=Number(String(el.textContent||'').trim());
      if(Number.isInteger(n)&&n>=1&&n<=10)el.dataset.number=String(n);
    });
  };
  const rankDiagnostics=()=>{
    const list=document.getElementById('diagnostics');
    if(!list)return;
    const weight={bad:0,warn:1,good:2};
    const rows=[...list.children];
    rows.forEach(row=>{
      const badge=row.querySelector('.badge');
      const severity=badge?.classList.contains('bad')?'bad':badge?.classList.contains('warn')?'warn':'good';
      row.dataset.severity=severity;
    });
    rows.sort((a,b)=>(weight[a.dataset.severity]??3)-(weight[b.dataset.severity]??3)).forEach(row=>list.appendChild(row));
  };
  const restorePanel=()=>{
    const name=sessionStorage.getItem('tianji-console-panel');
    if(name)document.querySelector(`.nav-btn[data-panel="${name}"]`)?.click();
  };
  qa('.nav-btn[data-panel]').forEach(btn=>btn.addEventListener('click',()=>sessionStorage.setItem('tianji-console-panel',btn.dataset.panel||'overview')));
  const label=(id,value)=>{const el=document.getElementById(id);if(el&&!el.getAttribute('aria-label'))el.setAttribute('aria-label',value)};
  label('logoutBtn','退出登录');label('runBtn','立即同步开奖与任务');
  qa('.topbar .icon-btn').forEach((el,index)=>{if(!el.getAttribute('aria-label'))el.setAttribute('aria-label',index===0?'切换明暗主题':'退出登录')});
  const syncExpandableState=()=>{
    const account=document.querySelector('.v5-account-toggle');
    const filter=document.querySelector('.v5-filter-toggle');
    if(account&&!account.dataset.v594){
      account.dataset.v594='1';account.setAttribute('aria-expanded','false');
      account.addEventListener('click',()=>{
        const expanded=account.textContent?.includes('只看当前')||false;
        account.setAttribute('aria-expanded',String(expanded));
        sessionStorage.setItem('tianji-account-expanded',String(expanded));
      });
      if(sessionStorage.getItem('tianji-account-expanded')==='true')account.click();
    }
    if(filter&&!filter.dataset.v594){
      filter.dataset.v594='1';filter.setAttribute('aria-expanded','false');
      filter.addEventListener('click',()=>{
        const expanded=filter.textContent?.includes('收起')||false;
        filter.setAttribute('aria-expanded',String(expanded));
        sessionStorage.setItem('tianji-filter-expanded',String(expanded));
      });
      if(sessionStorage.getItem('tianji-filter-expanded')==='true')filter.click();
    }
  };
  enhanceBalls();rankDiagnostics();syncExpandableState();restorePanel();
  new MutationObserver(records=>{
    records.forEach(record=>record.addedNodes.forEach(node=>{if(node.nodeType===1)enhanceBalls(node)}));
    rankDiagnostics();syncExpandableState();
  }).observe(document.body,{childList:true,subtree:true});
})();
'''

css_parts = [
    read("server/app/console_v3.css"),
    read("server/app/console_v5.css"),
    read("server/app/console_v5_polish.css"),
    extra_css,
]
js_parts = [
    read("server/app/console_v3.js"),
    read("server/app/console_v5.js"),
    read("server/app/console_v5_polish.js"),
    extra_js,
]
write("server/app/console_v594.css", "\n\n".join(css_parts))
write("server/app/console_v594.js", "\n\n".join(js_parts))

path = "server/app/console_v3.py"
text = read(path)
text = regex_once(
    text,
    r"    # Keep the proven V5 visual baseline.*?    return style_text, script_text",
    "    # V5.9.4 ships a single consolidated runtime asset to prevent override drift.\n"
    "    style_text = (root / \"console_v594.css\").read_text(encoding=\"utf-8\")\n"
    "    script_text = (root / \"console_v594.js\").read_text(encoding=\"utf-8\")\n"
    "    return style_text, script_text",
    "console consolidated assets",
)
text = text.replace("Tianji Cloud Console V5 polish", "Tianji Cloud Console V5.9.4 unified")
write(path, text)

print("Applied Tianji v5.9.4 App and Console UI unification.")
