from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def sub_once(text: str, pattern: str, replacement: str, label: str) -> str:
    result, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return result


# Large-font friendly shell dimensions.
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AppShellV2.kt"
text = read(path)
if "import androidx.compose.foundation.layout.heightIn\n" not in text:
    text = text.replace(
        "import androidx.compose.foundation.layout.height\n",
        "import androidx.compose.foundation.layout.height\n"
        "import androidx.compose.foundation.layout.heightIn\n",
        1,
    )
for old, new in (
    (".height(58.dp)", ".heightIn(min = 58.dp)"),
    (".height(64.dp)", ".heightIn(min = 64.dp)"),
    (".height(48.dp)", ".heightIn(min = 48.dp)"),
    (".height(47.dp)", ".heightIn(min = 47.dp)"),
):
    if old not in text:
        raise RuntimeError(f"Missing shell height marker: {old}")
    text = text.replace(old, new, 1)
write(path, text)


# Expandable AI task summary.
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedForecastStrategy.kt"
text = read(path)
text = sub_once(
    text,
    r"(val evaluation = remember\(state\.aiForecasts, state\.aiProfileAudits\) \{\s*"
    r"AiConsensusEngine\.evaluateForecasts\(state\.aiForecasts, state\.aiProfileAudits\)\s*\})",
    r"\1\n    var showAllStatuses by rememberSaveable { mutableStateOf(false) }",
    "AI status state",
)
ai_status_block = '''if (state.aiStatuses.isNotEmpty()) {
                val statuses = state.aiStatuses.values.toList()
                val running = statuses.count {
                    it.state == AiConnectionState.ANALYZING ||
                        it.state == AiConnectionState.TESTING
                }
                val failed = statuses.count { it.state == AiConnectionState.FAILED }
                val completed = statuses.count { it.state == AiConnectionState.CONNECTED }
                Spacer(Modifier.height(12.dp))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(13.dp))
                        .background(colors.surfaceStrong)
                        .border(1.dp, colors.line, RoundedCornerShape(13.dp))
                        .padding(horizontal = 10.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        "运行 $running · 完成 $completed · 失败 $failed",
                        color = if (failed > 0) colors.red else colors.textSoft,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.weight(1f),
                    )
                    if (statuses.size > 3) {
                        Text(
                            if (showAllStatuses) "收起" else "查看全部 ${statuses.size} 项",
                            color = colors.accent,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier
                                .clip(CircleShape)
                                .clickable { showAllStatuses = !showAllStatuses }
                                .padding(horizontal = 8.dp, vertical = 5.dp),
                        )
                    }
                }
                val visibleStatuses = if (showAllStatuses) statuses else statuses.take(3)
                visibleStatuses.forEach { status ->
                    val tint = when (status.state) {
                        AiConnectionState.CONNECTED -> colors.green
                        AiConnectionState.FAILED -> colors.red
                        AiConnectionState.ANALYZING, AiConnectionState.TESTING -> colors.accent
                        else -> colors.amber
                    }
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 5.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(Modifier.size(7.dp).clip(CircleShape).background(tint))
                        Spacer(Modifier.width(8.dp))
                        Text(
                            status.message,
                            color = colors.textSoft,
                            fontSize = 11.sp,
                            maxLines = if (showAllStatuses) 2 else 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f),
                        )
                        if (status.state == AiConnectionState.ANALYZING ||
                            status.state == AiConnectionState.TESTING
                        ) {
                            Text(
                                "取消",
                                color = colors.amber,
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier
                                    .clip(CircleShape)
                                    .clickable { onCancel(status.profileId) }
                                    .padding(horizontal = 8.dp, vertical = 5.dp),
                            )
                        }
                    }
                }
            }'''
text = sub_once(
    text,
    r"if \(state\.aiStatuses\.isNotEmpty\(\)\) \{.*?\n            \}\n\n"
    r"            evaluation\.consensus",
    ai_status_block + "\n\n            evaluation.consensus",
    "AI status content",
)
write(path, text)


# Archive source, target period and settlement filters.
path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedArchive.kt"
text = read(path)
if "import androidx.compose.material3.OutlinedTextField\n" not in text:
    text = text.replace(
        "import androidx.compose.material3.Icon\n",
        "import androidx.compose.material3.Icon\n"
        "import androidx.compose.material3.OutlinedTextField\n"
        "import androidx.compose.material3.OutlinedTextFieldDefaults\n",
        1,
    )
source_enum = '''private enum class ArchiveSourceFilter(val label: String) {
    ALL("全部来源"),
    CONSENSUS("AI 共识"),
    AI("独立 AI"),
    NATIVE("本地模型"),
}

'''
text = sub_once(
    text,
    r"(@Composable\nfun RefinedArchiveScreen)",
    source_enum + r"\1",
    "Archive source enum",
)
text = sub_once(
    text,
    r"(var settlementFilterName by rememberSaveable\(state\.lottery\.apiKey\) \{\s*"
    r"mutableStateOf\(ArchiveSettlementFilter\.ALL\.name\)\s*\})",
    r'''\1
    var sourceFilterName by rememberSaveable(state.lottery.apiKey) {
        mutableStateOf(ArchiveSourceFilter.ALL.name)
    }
    var periodQuery by rememberSaveable(state.lottery.apiKey) { mutableStateOf("") }''',
    "Archive filter states",
)
text = sub_once(
    text,
    r"(val settlementFilter = ArchiveSettlementFilter\.entries\.firstOrNull \{\s*"
    r"it\.name == settlementFilterName\s*\} \?: ArchiveSettlementFilter\.ALL)",
    r'''\1
    val sourceFilter = ArchiveSourceFilter.entries.firstOrNull {
        it.name == sourceFilterName
    } ?: ArchiveSourceFilter.ALL
    val periodNeedle = periodQuery.trim()''',
    "Archive selected filters",
)
filtered_records = '''val consensusRecords = state.aiConsensusRecords.filter {
        (sourceFilter == ArchiveSourceFilter.ALL ||
            sourceFilter == ArchiveSourceFilter.CONSENSUS) &&
            archiveMatchesFilter(settlementFilter, it.top6Hit, it.top7Hit) &&
            (periodNeedle.isEmpty() ||
                it.targetPeriod.contains(periodNeedle, ignoreCase = true))
    }
    val aiRecords = state.aiRecords.filter {
        (sourceFilter == ArchiveSourceFilter.ALL ||
            sourceFilter == ArchiveSourceFilter.AI) &&
            archiveMatchesFilter(settlementFilter, it.top6Hit, it.top7Hit) &&
            (periodNeedle.isEmpty() ||
                it.targetPeriod.contains(periodNeedle, ignoreCase = true))
    }
    val nativeRecords = state.records.filter {
        (sourceFilter == ArchiveSourceFilter.ALL ||
            sourceFilter == ArchiveSourceFilter.NATIVE) &&
            archiveMatchesFilter(settlementFilter, it.top6Hit, it.top7Hit) &&
            (periodNeedle.isEmpty() ||
                it.targetPeriod.contains(periodNeedle, ignoreCase = true))
    }'''
text = sub_once(
    text,
    r"val consensusRecords = state\.aiConsensusRecords\.filter \{.*?"
    r"val nativeRecords = state\.records\.filter \{.*?\n    \}",
    filtered_records,
    "Archive filtered records",
)
archive_controls = '''item("archive-filters") {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = periodQuery,
                    onValueChange = { periodQuery = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    placeholder = { Text("搜索目标期，例如 20260805123") },
                    shape = RoundedCornerShape(14.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.accent,
                        unfocusedBorderColor = colors.lineStrong,
                        focusedTextColor = colors.text,
                        unfocusedTextColor = colors.text,
                        focusedContainerColor = colors.surfaceStrong,
                        unfocusedContainerColor = colors.surfaceStrong,
                    ),
                )
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    ArchiveSourceFilter.entries.forEach { option ->
                        ArchiveFilterChipV594(
                            label = option.label,
                            active = option == sourceFilter,
                            onClick = { sourceFilterName = option.name },
                        )
                    }
                }
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    ArchiveSettlementFilter.entries.forEach { option ->
                        ArchiveFilterChipV594(
                            label = option.label,
                            active = option == settlementFilter,
                            onClick = { settlementFilterName = option.name },
                        )
                    }
                }
            }
        }'''
text = sub_once(
    text,
    r"item\(\"archive-filters\"\) \{.*?\n        \}\n\n        if \(consensusRecords",
    archive_controls + "\n\n        if (consensusRecords",
    "Archive filter controls",
)
chip_helper = '''@Composable
private fun ArchiveFilterChipV594(
    label: String,
    active: Boolean,
    onClick: () -> Unit,
) {
    val colors = LocalTianjiColors.current
    Text(
        label,
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
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp),
    )
}

'''
text = sub_once(
    text,
    r"(private fun archiveMatchesFilter\()",
    chip_helper + r"\1",
    "Archive filter chip helper",
)
write(path, text)


# Prevent accidental logout taps on the mobile console.
path = "server/app/console_v594.js"
text = read(path)
marker = "  label('logoutBtn','退出登录');label('runBtn','立即同步开奖与任务');"
if marker not in text:
    raise RuntimeError("Console logout marker missing")
text = text.replace(
    marker,
    marker
    + "\n  const logoutButton=document.getElementById('logoutBtn');"
    + "\n  logoutButton?.addEventListener('click',event=>{"
    + "if(!confirm('确认退出天机控制台？')){"
    + "event.preventDefault();event.stopImmediatePropagation()}},true);",
    1,
)
write(path, text)

print("Applied remaining Tianji v5.9.4 UI polish.")
