from pathlib import Path

PATH = Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AiChatDialog.kt")
text = PATH.read_text(encoding="utf-8")


def replace_between(source: str, start: str, end: str, replacement: str) -> str:
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[:start_index] + replacement.rstrip() + "\n\n" + source[end_index:]


old_list = """                            verticalArrangement = Arrangement.spacedBy(13.dp),
"""
new_list = """                            verticalArrangement = Arrangement.spacedBy(
                                13.dp,
                                Alignment.Bottom,
                            ),
"""
if old_list not in text:
    raise SystemExit("message list arrangement marker not found")
text = text.replace(old_list, new_list, 1)

chat_top_bar = r'''@Composable
private fun ChatTopBar(
    session: AiChatSession,
    selectedModel: String,
    onNew: () -> Unit,
    onHistory: () -> Unit,
    onClose: () -> Unit,
    onMore: () -> Unit,
    moreExpanded: Boolean,
    dismissMore: () -> Unit,
    onRefresh: () -> Unit,
    onClear: () -> Unit,
    onDelete: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(70.dp)
            .background(
                Brush.verticalGradient(
                    listOf(
                        colors.header,
                        colors.page.copy(alpha = 0.96f),
                    ),
                ),
            )
            .border(width = 0.5.dp, color = colors.line)
            .padding(horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(
            onClick = onClose,
            modifier = Modifier.size(42.dp),
        ) {
            Icon(
                imageVector = Icons.AutoMirrored.Rounded.ArrowBack,
                contentDescription = "返回",
                tint = colors.textSoft,
                modifier = Modifier.size(23.dp),
            )
        }

        Box(
            modifier = Modifier
                .size(42.dp)
                .shadow(
                    elevation = if (colors.isOled) 0.dp else 5.dp,
                    shape = RoundedCornerShape(15.dp),
                    ambientColor = colors.accent.copy(alpha = 0.20f),
                    spotColor = colors.accent.copy(alpha = 0.20f),
                )
                .clip(RoundedCornerShape(15.dp))
                .background(
                    Brush.linearGradient(
                        listOf(
                            colors.accent.copy(alpha = 0.24f),
                            colors.violet.copy(alpha = 0.16f),
                        ),
                    ),
                )
                .border(
                    width = 1.dp,
                    color = colors.accent.copy(alpha = 0.28f),
                    shape = RoundedCornerShape(15.dp),
                ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Rounded.AutoAwesome,
                contentDescription = null,
                tint = colors.accent,
                modifier = Modifier.size(20.dp),
            )
        }

        Spacer(Modifier.width(10.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = session.title.ifBlank { "新对话" },
                color = colors.text,
                fontSize = 16.sp,
                lineHeight = 21.sp,
                fontWeight = FontWeight.ExtraBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Surface(
                shape = CircleShape,
                color = colors.accent.copy(alpha = 0.09f),
            ) {
                Text(
                    text = selectedModel.ifBlank { "请选择模型" },
                    color = colors.accent,
                    fontSize = 9.5.sp,
                    lineHeight = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(horizontal = 7.dp, vertical = 2.dp),
                )
            }
        }

        ChatTopActionButton(
            icon = Icons.Rounded.History,
            description = "对话历史",
            enabled = !session.isRunning,
            onClick = onHistory,
        )
        Spacer(Modifier.width(5.dp))
        ChatTopActionButton(
            icon = Icons.Rounded.Add,
            description = "新建对话",
            enabled = !session.isRunning,
            onClick = onNew,
        )
        Spacer(Modifier.width(5.dp))
        Box {
            ChatTopActionButton(
                icon = Icons.Rounded.MoreVert,
                description = "更多",
                enabled = !session.isRunning,
                onClick = onMore,
            )
            DropdownMenu(
                expanded = moreExpanded,
                onDismissRequest = dismissMore,
            ) {
                DropdownMenuItem(
                    text = { Text("刷新开奖历史") },
                    leadingIcon = {
                        Icon(Icons.Rounded.Refresh, contentDescription = null)
                    },
                    onClick = {
                        dismissMore()
                        onRefresh()
                    },
                )
                DropdownMenuItem(
                    text = { Text("清空当前对话") },
                    leadingIcon = {
                        Icon(Icons.Rounded.DeleteSweep, contentDescription = null)
                    },
                    onClick = {
                        dismissMore()
                        onClear()
                    },
                )
                DropdownMenuItem(
                    text = { Text("删除当前会话") },
                    leadingIcon = {
                        Icon(Icons.Rounded.Close, contentDescription = null)
                    },
                    onClick = {
                        dismissMore()
                        onDelete()
                    },
                )
            }
        }
    }
}

@Composable
private fun ChatTopActionButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    description: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = Modifier
            .size(38.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 2.dp,
                shape = RoundedCornerShape(13.dp),
                ambientColor = Color.Black.copy(alpha = 0.12f),
                spotColor = Color.Black.copy(alpha = 0.12f),
            )
            .clickable(enabled = enabled, onClick = onClick),
        shape = RoundedCornerShape(13.dp),
        color = colors.glass,
        border = BorderStroke(1.dp, colors.lineStrong),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Icon(
                imageVector = icon,
                contentDescription = description,
                tint = if (enabled) colors.textSoft else colors.textDim.copy(alpha = 0.35f),
                modifier = Modifier.size(19.dp),
            )
        }
    }
}'''
text = replace_between(
    text,
    "@Composable\nprivate fun ChatTopBar(",
    "@Composable\nprivate fun SessionControlCard(",
    chat_top_bar,
)

session_control = r'''@Composable
private fun SessionControlCard(
    expanded: Boolean,
    onToggle: () -> Unit,
    configs: List<AiConfig>,
    selectedConfig: AiConfig?,
    models: List<String>,
    selectedModel: String,
    session: AiChatSession,
    snapshot: DrawSnapshot?,
    report: ForecastReport?,
    onConfig: (AiConfig) -> Unit,
    onModel: (String) -> Unit,
    onPersona: (String) -> Unit,
    onJudgementMode: (AiJudgementMode) -> Unit,
) {
    val colors = LocalTianjiColors.current
    val persona = AiChatPersona.fromId(session.personaId)
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 14.dp, vertical = 9.dp)
            .shadow(
                elevation = if (colors.isOled) 0.dp else 3.dp,
                shape = RoundedCornerShape(21.dp),
                ambientColor = Color.Black.copy(alpha = 0.10f),
                spotColor = Color.Black.copy(alpha = 0.10f),
            )
            .animateContentSize(),
        shape = RoundedCornerShape(21.dp),
        color = colors.glass,
        border = BorderStroke(1.dp, colors.lineStrong),
    ) {
        Column {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(onClick = onToggle)
                    .padding(horizontal = 13.dp, vertical = 11.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(38.dp)
                            .clip(RoundedCornerShape(13.dp))
                            .background(
                                Brush.linearGradient(
                                    listOf(
                                        colors.accent.copy(alpha = 0.20f),
                                        colors.violet.copy(alpha = 0.12f),
                                    ),
                                ),
                            )
                            .border(
                                1.dp,
                                colors.accent.copy(alpha = 0.20f),
                                RoundedCornerShape(13.dp),
                            ),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Tune,
                            contentDescription = null,
                            tint = colors.accent,
                            modifier = Modifier.size(19.dp),
                        )
                    }
                    Spacer(Modifier.width(10.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = selectedModel.ifBlank { "选择模型" },
                            color = colors.text,
                            fontSize = 12.5.sp,
                            lineHeight = 17.sp,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            text = "${session.judgementMode.label} · ${persona.displayName}",
                            color = colors.textDim,
                            fontSize = 9.5.sp,
                            lineHeight = 14.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    Icon(
                        imageVector = if (expanded) {
                            Icons.Rounded.KeyboardArrowUp
                        } else {
                            Icons.Rounded.KeyboardArrowDown
                        },
                        contentDescription = if (expanded) "收起" else "展开",
                        tint = colors.textDim,
                        modifier = Modifier.size(20.dp),
                    )
                }

                Spacer(Modifier.height(9.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Surface(
                        shape = CircleShape,
                        color = colors.surfaceSoft,
                        border = BorderStroke(1.dp, colors.line),
                    ) {
                        Text(
                            text = report?.targetPeriod?.let { "目标期  $it" } ?: "目标期待同步",
                            color = colors.textSoft,
                            fontSize = 9.5.sp,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                        )
                    }
                    Spacer(Modifier.width(7.dp))
                    Surface(
                        shape = CircleShape,
                        color = colors.accent.copy(alpha = 0.08f),
                    ) {
                        Text(
                            text = selectedConfig?.displayName ?: "未配置",
                            color = colors.accent,
                            fontSize = 9.5.sp,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier
                                .widthIn(max = 142.dp)
                                .padding(horizontal = 9.dp, vertical = 5.dp),
                        )
                    }
                    Spacer(Modifier.weight(1f))
                    Text(
                        text = "上下文",
                        color = colors.textDim,
                        fontSize = 9.sp,
                    )
                    Spacer(Modifier.width(5.dp))
                    ContextUsagePill(session.contextUsagePercent)
                }
            }

            AnimatedVisibility(visible = expanded) {
                Column {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(1.dp)
                            .background(colors.line),
                    )
                    Column(
                        modifier = Modifier.padding(
                            start = 13.dp,
                            end = 13.dp,
                            top = 6.dp,
                            bottom = 12.dp,
                        ),
                    ) {
                        SelectorRow(
                            label = "配置",
                            value = selectedConfig?.displayName ?: "未配置",
                            options = configs.map { it.id to it.displayName },
                            selectedKey = selectedConfig?.id.orEmpty(),
                            onSelect = { id ->
                                configs.firstOrNull { it.id == id }?.let(onConfig)
                            },
                        )
                        SelectorRow(
                            label = "模型",
                            value = selectedModel.ifBlank { "未选择" },
                            options = models.map { it to it },
                            selectedKey = selectedModel,
                            onSelect = onModel,
                        )
                        SelectorRow(
                            label = "人设",
                            value = persona.displayName,
                            options = AiChatPersona.entries.map { it.id to it.displayName },
                            selectedKey = session.personaId,
                            onSelect = onPersona,
                        )
                        SelectorRow(
                            label = "判断",
                            value = session.judgementMode.label,
                            options = AiJudgementMode.entries.map { it.name to it.label },
                            selectedKey = session.judgementMode.name,
                            onSelect = { value ->
                                onJudgementMode(AiJudgementMode.fromId(value))
                            },
                        )

                        val ready = snapshot != null && report != null && selectedConfig != null
                        val learning = session.learningProfile
                        Surface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 7.dp),
                            shape = RoundedCornerShape(15.dp),
                            color = colors.surfaceSoft,
                            border = BorderStroke(1.dp, colors.line),
                        ) {
                            Column(
                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                            ) {
                                Text(
                                    text = if (ready) {
                                        "${snapshot!!.history.takeLast(120).size} 期真实接口历史已准备"
                                    } else {
                                        "请先准备开奖历史和完整 AI 配置"
                                    },
                                    color = if (ready) colors.green else colors.amber,
                                    fontSize = 10.sp,
                                    lineHeight = 15.sp,
                                    fontWeight = FontWeight.SemiBold,
                                )
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    text = "持续学习 ${learning.settled} 期 · 六码 " +
                                        "${(learning.top6Rate * 100).toInt()}% · 连续未中 " +
                                        "${learning.missStreak} 期",
                                    color = if (learning.missStreak >= 3) {
                                        colors.amber
                                    } else {
                                        colors.textSoft
                                    },
                                    fontSize = 10.sp,
                                    lineHeight = 15.sp,
                                )
                                if (learning.lastChange.isNotBlank()) {
                                    Spacer(Modifier.height(3.dp))
                                    Text(
                                        text = learning.lastChange,
                                        color = colors.textDim,
                                        fontSize = 10.sp,
                                        lineHeight = 15.sp,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}'''
text = replace_between(
    text,
    "@Composable\nprivate fun SessionControlCard(",
    "@Composable\nprivate fun ContextUsagePill(",
    session_control,
)

system_event = r'''@Composable
private fun SystemEventChip(text: String) {
    val colors = LocalTianjiColors.current
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .widthIn(max = 390.dp),
        shape = RoundedCornerShape(17.dp),
        color = colors.surfaceSoft,
        border = BorderStroke(1.dp, colors.lineStrong),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Box(
                modifier = Modifier
                    .size(30.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(colors.accent.copy(alpha = 0.10f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Rounded.Refresh,
                    contentDescription = null,
                    tint = colors.accent,
                    modifier = Modifier.size(16.dp),
                )
            }
            Spacer(Modifier.width(9.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "期次更新",
                    color = colors.textSoft,
                    fontSize = 10.sp,
                    lineHeight = 14.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    text = text,
                    color = colors.textDim,
                    fontSize = 10.5.sp,
                    lineHeight = 16.sp,
                )
            }
        }
    }
}'''
text = replace_between(
    text,
    "@Composable\nprivate fun SystemEventChip(",
    "@Composable\nprivate fun StreamingStatus(",
    system_event,
)

composer = r'''@Composable
private fun ChatComposer(
    input: String,
    onInput: (String) -> Unit,
    ready: Boolean,
    isRunning: Boolean,
    placeholder: String,
    suggestions: List<String>,
    onSuggestion: (String) -> Unit,
    onSend: () -> Unit,
    onStop: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Brush.verticalGradient(
                    listOf(
                        colors.header.copy(alpha = 0.96f),
                        colors.page.copy(alpha = 0.99f),
                    ),
                ),
            )
            .border(width = 0.5.dp, color = colors.line)
            .padding(top = 8.dp, bottom = 8.dp),
    ) {
        if (input.isBlank() && !isRunning && ready && suggestions.isNotEmpty()) {
            LazyRow(
                contentPadding = PaddingValues(horizontal = 14.dp),
                horizontalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                items(suggestions) { suggestion ->
                    Surface(
                        modifier = Modifier.clickable { onSuggestion(suggestion) },
                        shape = CircleShape,
                        color = colors.accent.copy(alpha = 0.07f),
                        border = BorderStroke(1.dp, colors.accent.copy(alpha = 0.15f)),
                    ) {
                        Text(
                            text = suggestion,
                            color = colors.textSoft,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Medium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier
                                .widthIn(max = 220.dp)
                                .padding(horizontal = 11.dp, vertical = 7.dp),
                        )
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
        }

        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp)
                .shadow(
                    elevation = if (colors.isOled) 0.dp else 7.dp,
                    shape = RoundedCornerShape(24.dp),
                    ambientColor = Color.Black.copy(alpha = 0.16f),
                    spotColor = Color.Black.copy(alpha = 0.16f),
                ),
            shape = RoundedCornerShape(24.dp),
            color = colors.glass,
            border = BorderStroke(1.dp, colors.lineStrong),
        ) {
            Row(
                modifier = Modifier.padding(
                    start = 15.dp,
                    top = 8.dp,
                    end = 7.dp,
                    bottom = 8.dp,
                ),
                verticalAlignment = Alignment.Bottom,
            ) {
                BasicTextField(
                    value = input,
                    onValueChange = onInput,
                    enabled = ready,
                    modifier = Modifier
                        .weight(1f)
                        .heightIn(min = 42.dp, max = 132.dp)
                        .padding(vertical = 9.dp),
                    textStyle = TextStyle(
                        color = colors.text,
                        fontSize = 13.sp,
                        lineHeight = 20.sp,
                    ),
                    cursorBrush = SolidColor(colors.accent),
                    minLines = 1,
                    maxLines = 6,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                    keyboardActions = KeyboardActions(
                        onSend = {
                            if (ready && !isRunning && input.isNotBlank()) onSend()
                        },
                    ),
                    decorationBox = { inner ->
                        Box(contentAlignment = Alignment.CenterStart) {
                            if (input.isBlank()) {
                                Text(
                                    text = when {
                                        !ready -> "请先同步数据并配置 AI"
                                        isRunning -> "可先输入下一条问题，生成结束后发送"
                                        else -> placeholder
                                    },
                                    color = colors.textDim,
                                    fontSize = 11.sp,
                                    lineHeight = 16.sp,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                            inner()
                        }
                    },
                )
                Spacer(Modifier.width(8.dp))
                val sendEnabled = isRunning || (ready && input.isNotBlank())
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .shadow(
                            elevation = if (sendEnabled && !colors.isOled) 5.dp else 0.dp,
                            shape = CircleShape,
                            ambientColor = colors.accent.copy(alpha = 0.24f),
                            spotColor = colors.accent.copy(alpha = 0.24f),
                        )
                        .clip(CircleShape)
                        .background(
                            when {
                                isRunning -> Brush.linearGradient(
                                    listOf(colors.amber, colors.red.copy(alpha = 0.85f)),
                                )
                                ready && input.isNotBlank() -> Brush.linearGradient(
                                    listOf(colors.accent, colors.violet),
                                )
                                else -> Brush.linearGradient(
                                    listOf(colors.surfaceSoft, colors.surfaceSoft),
                                )
                            },
                        )
                        .border(
                            1.dp,
                            if (sendEnabled) Color.White.copy(alpha = 0.16f) else colors.line,
                            CircleShape,
                        )
                        .clickable(
                            enabled = sendEnabled,
                            onClick = if (isRunning) onStop else onSend,
                        ),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        imageVector = if (isRunning) {
                            Icons.Rounded.StopCircle
                        } else {
                            Icons.AutoMirrored.Rounded.Send
                        },
                        contentDescription = if (isRunning) "停止" else "发送",
                        tint = if (sendEnabled) Color.White else colors.textDim,
                        modifier = Modifier.size(21.dp),
                    )
                }
            }
        }
    }
}'''
text = replace_between(
    text,
    "@Composable\nprivate fun ChatComposer(",
    "@Composable\nprivate fun ConversationHistoryDialog(",
    composer,
)

PATH.write_text(text, encoding="utf-8")
print(f"updated {PATH} ({len(text)} bytes)")
