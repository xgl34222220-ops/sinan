package com.tianji.probabilitylab.nativev4.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.ChatBubble
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.DeleteSweep
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Send
import androidx.compose.material.icons.rounded.StopCircle
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.tianji.probabilitylab.nativev4.ai.AiChatController
import com.tianji.probabilitylab.nativev4.ai.AiChatMessage
import com.tianji.probabilitylab.nativev4.ai.AiChatPrediction
import com.tianji.probabilitylab.nativev4.ai.AiChatRole
import com.tianji.probabilitylab.nativev4.ai.AiConfig
import com.tianji.probabilitylab.nativev4.model.DrawSnapshot
import com.tianji.probabilitylab.nativev4.model.ForecastReport
import com.tianji.probabilitylab.nativev4.ui.theme.LocalTianjiColors

@Composable
fun AiChatFloatingButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = LocalTianjiColors.current
    FloatingActionButton(
        onClick = onClick,
        modifier = modifier.size(52.dp),
        shape = CircleShape,
        containerColor = colors.accent,
        contentColor = Color.White,
    ) {
        Icon(Icons.Rounded.ChatBubble, contentDescription = "打开分析对话")
    }
}

@Composable
fun AiChatDialog(
    controller: AiChatController,
    configs: List<AiConfig>,
    snapshot: DrawSnapshot?,
    report: ForecastReport?,
    onRefresh: () -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    val completeConfigs = remember(configs) { configs.filter(AiConfig::isComplete) }
    val configIds = completeConfigs.joinToString("|") { it.id }
    val preferredConfig = completeConfigs.firstOrNull { it.id == controller.session.profileId }
        ?: completeConfigs.firstOrNull()
    val session = controller.session
    var input by rememberSaveable { mutableStateOf("") }
    val listState = rememberLazyListState()

    LaunchedEffect(configIds, report?.targetPeriod) {
        controller.selectProfile(preferredConfig?.id.orEmpty(), report?.targetPeriod)
    }
    LaunchedEffect(session.messages.size, session.isRunning, session.prediction) {
        val extra = if (session.prediction != null) 1 else 0
        val lastIndex = session.messages.size + extra - 1
        if (lastIndex >= 0) listState.animateScrollToItem(lastIndex)
    }

    fun submit(text: String) {
        val config = completeConfigs.firstOrNull { it.id == controller.session.profileId }
            ?: preferredConfig
        val currentSnapshot = snapshot
        val currentReport = report
        if (config == null || currentSnapshot == null || currentReport == null) return
        val question = text.trim()
        if (question.isBlank()) return
        input = ""
        controller.send(config, currentSnapshot, currentReport, question)
    }

    Dialog(
        onDismissRequest = {
            controller.cancel()
            onDismiss()
        },
        properties = DialogProperties(
            usePlatformDefaultWidth = false,
            decorFitsSystemWindows = false,
        ),
    ) {
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .background(colors.page)
                .windowInsetsPadding(WindowInsets.systemBars),
            color = colors.page,
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .imePadding()
                    .padding(horizontal = 12.dp),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 10.dp, bottom = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(
                        modifier = Modifier
                            .size(38.dp)
                            .clip(RoundedCornerShape(13.dp))
                            .background(colors.accent.copy(alpha = 0.14f)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(
                            Icons.Rounded.AutoAwesome,
                            contentDescription = null,
                            tint = colors.accent,
                            modifier = Modifier.size(20.dp),
                        )
                    }
                    Spacer(Modifier.width(10.dp))
                    Column(Modifier.weight(1f)) {
                        Text(
                            "天机分析对话",
                            color = colors.text,
                            fontSize = 17.sp,
                            fontWeight = FontWeight.ExtraBold,
                        )
                        Text(
                            "读取当前接口历史 · 不写入正式成绩",
                            color = colors.textDim,
                            fontSize = 8.sp,
                        )
                    }
                    IconButton(onClick = onRefresh, enabled = !session.isRunning) {
                        Icon(Icons.Rounded.Refresh, "刷新开奖历史", tint = colors.textSoft)
                    }
                    IconButton(
                        onClick = controller::clear,
                        enabled = session.messages.isNotEmpty() && !session.isRunning,
                    ) {
                        Icon(Icons.Rounded.DeleteSweep, "清空对话", tint = colors.textSoft)
                    }
                    IconButton(
                        onClick = {
                            controller.cancel()
                            onDismiss()
                        },
                    ) {
                        Icon(Icons.Rounded.Close, "关闭", tint = colors.textSoft)
                    }
                }

                if (completeConfigs.isNotEmpty()) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState())
                            .padding(bottom = 8.dp),
                        horizontalArrangement = Arrangement.spacedBy(7.dp),
                    ) {
                        completeConfigs.forEach { config ->
                            FilterChip(
                                selected = controller.session.profileId == config.id,
                                onClick = {
                                    if (!session.isRunning) {
                                        controller.selectProfile(config.id, report?.targetPeriod)
                                    }
                                },
                                label = {
                                    Text(
                                        config.displayName,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                        fontSize = 8.sp,
                                    )
                                },
                            )
                        }
                    }
                }

                SourceNotice(
                    snapshot = snapshot,
                    report = report,
                    hasConfig = preferredConfig != null,
                )
                Spacer(Modifier.height(8.dp))

                LazyColumn(
                    state = listState,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(
                        top = 6.dp,
                        bottom = 12.dp,
                    ),
                    verticalArrangement = Arrangement.spacedBy(9.dp),
                ) {
                    if (session.messages.isEmpty()) {
                        item(key = "welcome") {
                            WelcomePanel(
                                enabled = preferredConfig != null && snapshot != null && report != null,
                                onPrompt = ::submit,
                            )
                        }
                    }
                    items(session.messages, key = AiChatMessage::id) { message ->
                        ChatMessageBubble(message)
                    }
                    session.prediction?.let { prediction ->
                        item(key = "prediction-${session.messages.size}") {
                            ChatPredictionCard(
                                prediction = prediction,
                                targetPeriod = session.targetPeriod,
                            )
                        }
                    }
                    if (session.isRunning) {
                        item(key = "running") {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(15.dp))
                                    .background(colors.accent.copy(alpha = 0.07f))
                                    .border(
                                        1.dp,
                                        colors.accent.copy(alpha = 0.18f),
                                        RoundedCornerShape(15.dp),
                                    )
                                    .padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(16.dp),
                                    color = colors.accent,
                                    strokeWidth = 2.dp,
                                )
                                Spacer(Modifier.width(9.dp))
                                Text(
                                    session.progress.ifBlank { "正在分析…" },
                                    color = colors.textSoft,
                                    fontSize = 8.5.sp,
                                    modifier = Modifier.weight(1f),
                                )
                                IconButton(onClick = controller::cancel, modifier = Modifier.size(32.dp)) {
                                    Icon(
                                        Icons.Rounded.StopCircle,
                                        contentDescription = "取消",
                                        tint = colors.amber,
                                    )
                                }
                            }
                        }
                    }
                    session.error?.let { error ->
                        item(key = "error") {
                            Text(
                                error,
                                color = colors.red,
                                fontSize = 8.5.sp,
                                lineHeight = 13.sp,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(13.dp))
                                    .background(colors.red.copy(alpha = 0.07f))
                                    .border(
                                        1.dp,
                                        colors.red.copy(alpha = 0.18f),
                                        RoundedCornerShape(13.dp),
                                    )
                                    .padding(11.dp),
                            )
                        }
                    }
                }

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 10.dp),
                    verticalAlignment = Alignment.Bottom,
                ) {
                    OutlinedTextField(
                        value = input,
                        onValueChange = { input = it },
                        enabled = preferredConfig != null && snapshot != null && report != null &&
                            !session.isRunning,
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(18.dp),
                        placeholder = {
                            Text(
                                "例如：分析第一名最近60期，哪些号相对活跃？",
                                fontSize = 8.5.sp,
                            )
                        },
                        minLines = 1,
                        maxLines = 4,
                    )
                    Spacer(Modifier.width(8.dp))
                    Button(
                        onClick = { submit(input) },
                        enabled = input.isNotBlank() && preferredConfig != null &&
                            snapshot != null && report != null && !session.isRunning,
                        modifier = Modifier.size(52.dp),
                        shape = CircleShape,
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = colors.accent),
                    ) {
                        Icon(Icons.Rounded.Send, contentDescription = "发送", tint = Color.White)
                    }
                }
            }
        }
    }
}

@Composable
private fun SourceNotice(
    snapshot: DrawSnapshot?,
    report: ForecastReport?,
    hasConfig: Boolean,
) {
    val colors = LocalTianjiColors.current
    val tint = when {
        !hasConfig -> colors.amber
        snapshot == null || report == null -> colors.red
        snapshot.sourceHealth.isFresh -> colors.green
        else -> colors.amber
    }
    val text = when {
        !hasConfig -> "请先在数据页保存一个完整的 AI 配置"
        snapshot == null || report == null -> "开奖历史尚未准备完成，请先刷新"
        else -> "已载入 ${snapshot.history.takeLast(120).size} 期接口历史 · 目标期 ${report.targetPeriod}"
    }
    Text(
        text,
        color = tint,
        fontSize = 8.sp,
        fontWeight = FontWeight.Bold,
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(tint.copy(alpha = 0.07f))
            .border(1.dp, tint.copy(alpha = 0.18f), RoundedCornerShape(12.dp))
            .padding(horizontal = 11.dp, vertical = 9.dp),
    )
}

@Composable
private fun WelcomePanel(
    enabled: Boolean,
    onPrompt: (String) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val prompts = listOf(
        "分析第一名最近60期，哪些号码相对活跃？",
        "第一名当前号码之后，历史上更常接哪些号？",
        "比较十个名次最近20期和60期的稳定性",
        "解释当前本机六码的边界和不确定性",
    )
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Color.White.copy(alpha = 0.035f))
            .border(1.dp, colors.line, RoundedCornerShape(20.dp))
            .padding(15.dp),
    ) {
        Text(
            "可以直接问开奖记录",
            color = colors.text,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(5.dp))
        Text(
            "支持连续追问某个名次、统计窗口、遗漏、后继转移和下期相对候选。回答基于当前接口历史，不会冒充真实中奖概率。",
            color = colors.textDim,
            fontSize = 8.sp,
            lineHeight = 13.sp,
        )
        Spacer(Modifier.height(12.dp))
        prompts.forEach { prompt ->
            OutlinedButton(
                onClick = { onPrompt(prompt) },
                enabled = enabled,
                modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp),
                shape = RoundedCornerShape(13.dp),
            ) {
                Text(
                    prompt,
                    color = if (enabled) colors.textSoft else colors.textDim,
                    fontSize = 8.sp,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun ChatMessageBubble(message: AiChatMessage) {
    val colors = LocalTianjiColors.current
    val user = message.role == AiChatRole.USER
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = if (user) Alignment.CenterEnd else Alignment.CenterStart,
    ) {
        Column(
            modifier = Modifier
                .widthIn(max = 340.dp)
                .clip(
                    RoundedCornerShape(
                        topStart = 18.dp,
                        topEnd = 18.dp,
                        bottomStart = if (user) 18.dp else 5.dp,
                        bottomEnd = if (user) 5.dp else 18.dp,
                    ),
                )
                .background(
                    if (user) colors.accent.copy(alpha = 0.22f)
                    else Color.White.copy(alpha = 0.045f),
                )
                .border(
                    1.dp,
                    if (user) colors.accent.copy(alpha = 0.25f) else colors.line,
                    RoundedCornerShape(18.dp),
                )
                .padding(horizontal = 13.dp, vertical = 11.dp),
        ) {
            if (!user) {
                Text(
                    "天机分析助手",
                    color = colors.accent,
                    fontSize = 7.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(5.dp))
            }
            Text(
                message.content,
                color = colors.textSoft,
                fontSize = 9.sp,
                lineHeight = 15.sp,
            )
            message.latencyMs?.let { latency ->
                Spacer(Modifier.height(5.dp))
                Text(
                    "${latency / 1_000.0}s",
                    color = colors.textDim,
                    fontSize = 6.5.sp,
                    modifier = Modifier.align(Alignment.End),
                )
            }
        }
    }
}

@Composable
private fun ChatPredictionCard(
    prediction: AiChatPrediction,
    targetPeriod: String?,
) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(colors.accent.copy(alpha = 0.075f))
            .border(1.dp, colors.accent.copy(alpha = 0.22f), RoundedCornerShape(20.dp))
            .padding(15.dp),
    ) {
        Text(
            "对话候选 · 第${prediction.position + 1}名",
            color = colors.accent,
            fontSize = 11.sp,
            fontWeight = FontWeight.ExtraBold,
        )
        Text(
            "目标期 ${targetPeriod ?: "待同步"} · 仅供本次对话比较，不计入真实成绩",
            color = colors.textDim,
            fontSize = 7.sp,
        )
        Spacer(Modifier.height(12.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            prediction.top6.forEach { number -> ChatNumberBall(number) }
        }
        Spacer(Modifier.height(10.dp))
        val ranked = prediction.probabilities.indices
            .sortedByDescending { prediction.probabilities[it] }
            .take(3)
        Text(
            ranked.joinToString(" · ") { index ->
                "${index + 1}号 ${(prediction.probabilities[index] * 100).format1()}%"
            },
            color = colors.textSoft,
            fontSize = 7.5.sp,
        )
    }
}

@Composable
private fun ChatNumberBall(number: Int) {
    val colors = LocalTianjiColors.current
    Box(
        modifier = Modifier
            .size(34.dp)
            .clip(CircleShape)
            .background(colors.accent.copy(alpha = 0.18f))
            .border(1.dp, colors.accent.copy(alpha = 0.35f), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            number.toString(),
            color = colors.text,
            fontSize = 11.sp,
            fontWeight = FontWeight.ExtraBold,
        )
    }
}

private fun Double.format1(): String = String.format(java.util.Locale.US, "%.1f", this)
