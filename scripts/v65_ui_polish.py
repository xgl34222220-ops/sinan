from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace(path: str, old: str, new: str, *, count: int | None = None) -> None:
    text = read(path)
    found = text.count(old)
    if found == 0:
        raise RuntimeError(f"{path}: replacement target not found: {old[:100]!r}")
    if count is not None and found != count:
        raise RuntimeError(f"{path}: expected {count} matches, found {found}: {old[:100]!r}")
    write(path, text.replace(old, new))


def regex(path: str, pattern: str, repl: str, *, count: int = 1, flags: int = 0) -> None:
    text = read(path)
    updated, n = re.subn(pattern, repl, text, count=count, flags=flags)
    if n != count:
        raise RuntimeError(f"{path}: expected {count} regex replacements, got {n}: {pattern[:100]!r}")
    write(path, updated)


# ---------------------------------------------------------------------------
# Shared Android visual language: less tinted surfaces, tighter controls.
# ---------------------------------------------------------------------------
THEME = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/theme/TianjiTheme.kt"
replace(THEME, "val tintAmount = if (isDark) 0.038f else 0.022f", "val tintAmount = if (isDark) 0.034f else 0.012f", count=1)
replace(THEME, "if (isDark) 0.04f else 0.025f", "if (isDark) 0.035f else 0.014f", count=1)
replace(THEME, "if (isDark) 0.075f else 0.10f", "if (isDark) 0.070f else 0.075f", count=1)
replace(THEME, "if (isDark) 0.17f else 0.12f", "if (isDark) 0.16f else 0.10f", count=1)

HEADER = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AppHeader.kt"
replace(HEADER, ".height(58.dp)", ".height(54.dp)", count=1)
replace(HEADER, ".padding(horizontal = 10.dp)", ".padding(horizontal = 8.dp)", count=1)
replace(HEADER, ".size(36.dp)\n                    .clip(RoundedCornerShape(12.dp))\n                    .border(1.dp, colors.accent.copy(alpha = 0.24f), RoundedCornerShape(12.dp))", ".size(34.dp)\n                    .clip(RoundedCornerShape(11.dp))\n                    .border(1.dp, colors.accent.copy(alpha = 0.20f), RoundedCornerShape(11.dp))", count=1)
replace(HEADER, ".size(46.dp)\n            .padding(3.dp)\n            .clip(RoundedCornerShape(14.dp))", ".size(42.dp)\n            .padding(2.dp)\n            .clip(RoundedCornerShape(13.dp))", count=1)
replace(HEADER, ".border(1.dp, colors.line, RoundedCornerShape(14.dp))", ".border(1.dp, colors.line, RoundedCornerShape(13.dp))", count=1)

BOTTOM = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/MainBottomBar.kt"
replace(BOTTOM, ".heightIn(min = 66.dp)", ".heightIn(min = 62.dp)", count=1)
replace(BOTTOM, "elevation = if (colors.isOled) 0.dp else 12.dp", "elevation = if (colors.isOled) 0.dp else 9.dp", count=1)
replace(BOTTOM, "shape = RoundedCornerShape(25.dp)", "shape = RoundedCornerShape(23.dp)", count=1)
replace(BOTTOM, ".clip(RoundedCornerShape(25.dp))", ".clip(RoundedCornerShape(23.dp))", count=1)
replace(BOTTOM, ".border(1.dp, colors.lineStrong, RoundedCornerShape(25.dp))", ".border(1.dp, colors.lineStrong, RoundedCornerShape(23.dp))", count=1)
replace(BOTTOM, "targetValue = colors.accent.copy(alpha = 0.15f)", "targetValue = colors.accent.copy(alpha = 0.12f)", count=1)
replace(BOTTOM, ".height(56.dp)\n                .padding(horizontal = 2.dp)\n                .clip(RoundedCornerShape(18.dp))", ".height(50.dp)\n                .padding(horizontal = 3.dp)\n                .clip(RoundedCornerShape(17.dp))", count=1)
replace(BOTTOM, "shape = RoundedCornerShape(18.dp),", "shape = RoundedCornerShape(17.dp),", count=1)
replace(BOTTOM, ".heightIn(min = 56.dp)", ".heightIn(min = 52.dp)")
replace(BOTTOM, "Box(modifier = Modifier.size(43.dp)", "Box(modifier = Modifier.size(40.dp)", count=1)
replace(BOTTOM, "modifier = Modifier.size(43.dp)", "modifier = Modifier.size(40.dp)", count=1)
replace(BOTTOM, ".size(38.dp)\n                    .shadow(", ".size(36.dp)\n                    .shadow(", count=1)
replace(BOTTOM, "modifier = Modifier.size(19.dp)", "modifier = Modifier.size(18.dp)", count=1)

SEG = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/SegmentedControls.kt"
replace(SEG, ".height(60.dp)", ".height(56.dp)", count=1)
replace(SEG, "shape = RoundedCornerShape(21.dp)", "shape = RoundedCornerShape(19.dp)", count=1)
replace(SEG, ".clip(RoundedCornerShape(21.dp))", ".clip(RoundedCornerShape(19.dp))", count=1)
replace(SEG, ".border(1.dp, colors.lineStrong, RoundedCornerShape(21.dp))", ".border(1.dp, colors.lineStrong, RoundedCornerShape(19.dp))", count=1)
replace(SEG, ".padding(5.dp),", ".padding(4.dp),", count=2)
replace(SEG, "val shape = RoundedCornerShape(16.dp)", "val shape = RoundedCornerShape(15.dp)", count=1)
replace(SEG, ".height(58.dp)", ".height(50.dp)", count=1)
replace(SEG, "shape = RoundedCornerShape(20.dp)", "shape = RoundedCornerShape(18.dp)", count=1)
replace(SEG, ".clip(RoundedCornerShape(20.dp))", ".clip(RoundedCornerShape(18.dp))", count=1)
replace(SEG, ".border(1.dp, colors.lineStrong, RoundedCornerShape(20.dp))", ".border(1.dp, colors.lineStrong, RoundedCornerShape(18.dp))", count=1)
replace(SEG, "val shape = RoundedCornerShape(15.dp)", "val shape = RoundedCornerShape(14.dp)", count=1)
replace(SEG, ".width(if (active) 22.dp else 8.dp)", ".width(if (active) 18.dp else 7.dp)", count=1)

SETTINGS_ENTRY = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/SettingsEntry.kt"
replace(SETTINGS_ENTRY, ".heightIn(min = 70.dp)", ".heightIn(min = 66.dp)", count=1)
replace(SETTINGS_ENTRY, ".clip(RoundedCornerShape(18.dp))", ".clip(RoundedCornerShape(17.dp))", count=1)
replace(SETTINGS_ENTRY, ".background(colors.surface.copy(alpha = 0.72f))", ".background(colors.surface.copy(alpha = 0.90f))", count=1)
replace(SETTINGS_ENTRY, ".border(1.dp, colors.line, RoundedCornerShape(18.dp))", ".border(1.dp, colors.line, RoundedCornerShape(17.dp))", count=1)
replace(SETTINGS_ENTRY, ".padding(horizontal = 14.dp, vertical = 11.dp)", ".padding(horizontal = 14.dp, vertical = 10.dp)", count=1)
replace(SETTINGS_ENTRY, "fontSize = 12.sp,\n                lineHeight = 17.sp,", "fontSize = 11.sp,\n                lineHeight = 16.sp,", count=1)

COMMON = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedUiCommon.kt"
replace(COMMON, ".padding(horizontal = 11.dp, vertical = 11.dp)", ".padding(horizontal = 10.dp, vertical = 9.dp)", count=1)
replace(COMMON, "fontSize = 12.sp, lineHeight = 16.sp, maxLines = 1", "fontSize = 11.sp, lineHeight = 15.sp, maxLines = 1", count=1)
replace(COMMON, "fontSize = 16.sp,\n            lineHeight = 21.sp,", "fontSize = 15.sp,\n            lineHeight = 20.sp,", count=1)

# ---------------------------------------------------------------------------
# Archive: clarify counters and reduce sticky-filter bulk.
# ---------------------------------------------------------------------------
ARCHIVE = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/V62ArchiveScreen.kt"
replace(ARCHIVE, ".heightIn(min = 56.dp)", ".heightIn(min = 50.dp)", count=1)
replace(ARCHIVE, "if (shown.size < filtered.size) \"已显示 ${shown.size} / ${filtered.size}\" else \"${filtered.size} 条\"", "if (shown.size < filtered.size) \"当前加载 ${shown.size} / ${filtered.size}\" else \"当前加载 ${filtered.size} 条\"", count=1)
replace(ARCHIVE, "Text(\"$settled / $total\", color = colors.text, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold)\n                Text(\"已结算 / 总档案\", color = colors.textDim, fontSize = 10.sp)", "Text(\"已结算 $settled / 总计 $total\", color = colors.text, fontSize = 13.sp, fontWeight = FontWeight.ExtraBold)\n                Text(\"档案结算进度\", color = colors.textDim, fontSize = 10.sp)", count=1)
replace(ARCHIVE, "SurfaceCard(radius = 19.dp)", "SurfaceCard(radius = 18.dp)", count=1)
replace(ARCHIVE, "Column(Modifier.padding(14.dp))", "Column(Modifier.padding(13.dp))", count=1)

# ---------------------------------------------------------------------------
# Home: single-model AI is concise; probability rows fit more on a phone.
# ---------------------------------------------------------------------------
FORECAST = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/V62ForecastScreen.kt"
replace(FORECAST, "SurfaceCard(radius = 24.dp)", "SurfaceCard(radius = 22.dp)", count=2)
replace(FORECAST, ".padding(17.dp)", ".padding(15.dp)", count=2)
replace(FORECAST, "SurfaceCard(radius = 20.dp)", "SurfaceCard(radius = 19.dp)", count=1)
replace(FORECAST, "Column(Modifier.padding(horizontal = 14.dp, vertical = 13.dp))", "Column(Modifier.padding(horizontal = 13.dp, vertical = 12.dp))", count=1)
# Single model: keep the judgement and profile, but do not dramatize a meaningless 1/1 vote.
old_main = '''                Row(\n                    modifier = Modifier\n                        .fillMaxWidth()\n                        .clip(RoundedCornerShape(14.dp))\n                        .background(colors.violet.copy(alpha = 0.075f))\n                        .padding(horizontal = 12.dp, vertical = 10.dp),\n                    verticalAlignment = Alignment.CenterVertically,\n                ) {\n                    Column(Modifier.weight(1f)) {\n                        Text("当前主判断", color = colors.textDim, fontSize = 11.sp)\n                        Text(\n                            "第${positionNameV2(lead.key)}名",\n                            color = colors.violet,\n                            fontSize = 21.sp,\n                            fontWeight = FontWeight.ExtraBold,\n                        )\n                    }\n                    Column(horizontalAlignment = Alignment.End) {\n                        Text(consensusLabel, color = colors.textDim, fontSize = 11.sp)\n                        Text(\n                            "${lead.value}/${forecasts.size} 票",\n                            color = colors.text,\n                            fontSize = 18.sp,\n                            fontWeight = FontWeight.ExtraBold,\n                        )\n                    }\n                }\n\n                Spacer(Modifier.height(9.dp))\n                supportRanking.take(3).forEachIndexed { index, entry ->'''
new_main = '''                Row(\n                    modifier = Modifier\n                        .fillMaxWidth()\n                        .clip(RoundedCornerShape(14.dp))\n                        .background(colors.violet.copy(alpha = 0.065f))\n                        .padding(horizontal = 12.dp, vertical = 9.dp),\n                    verticalAlignment = Alignment.CenterVertically,\n                ) {\n                    Column(Modifier.weight(1f)) {\n                        Text("当前主判断", color = colors.textDim, fontSize = 11.sp)\n                        Text(\n                            "第${positionNameV2(lead.key)}名",\n                            color = colors.violet,\n                            fontSize = 20.sp,\n                            fontWeight = FontWeight.ExtraBold,\n                        )\n                    }\n                    Column(horizontalAlignment = Alignment.End) {\n                        Text(consensusLabel, color = colors.textDim, fontSize = 11.sp)\n                        Text(\n                            if (forecasts.size == 1) {\n                                forecasts.first().profileName.ifBlank { forecasts.first().model }\n                            } else {\n                                "${lead.value}/${forecasts.size} 票"\n                            },\n                            color = colors.text,\n                            fontSize = if (forecasts.size == 1) 12.sp else 17.sp,\n                            fontWeight = FontWeight.ExtraBold,\n                            maxLines = 1,\n                            overflow = TextOverflow.Ellipsis,\n                        )\n                    }\n                }\n\n                if (forecasts.size > 1) {\n                    Spacer(Modifier.height(8.dp))\n                    supportRanking.take(3).forEachIndexed { index, entry ->'''
replace(FORECAST, old_main, new_main, count=1)
old_after_bars = '''                    }\n                }\n\n                Spacer(Modifier.height(7.dp))\n                forecasts.take(2).forEach { forecast ->'''
new_after_bars = '''                    }\n                }\n                }\n\n                Spacer(Modifier.height(if (forecasts.size > 1) 7.dp else 5.dp))\n                forecasts.take(if (forecasts.size == 1) 1 else 2).forEach { forecast ->'''
replace(FORECAST, old_after_bars, new_after_bars, count=1)
replace(FORECAST, "modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp)", "modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)", count=1)
replace(FORECAST, "Column(Modifier.padding(16.dp))", "Column(Modifier.padding(15.dp))", count=1)

# ---------------------------------------------------------------------------
# Strategy: less stacked chrome and denser experiment panel.
# ---------------------------------------------------------------------------
STRATEGY = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedForecastStrategy.kt"
replace(STRATEGY, "contentPadding = PaddingValues(12.dp, 12.dp, 12.dp, 16.dp)", "contentPadding = PaddingValues(12.dp, 10.dp, 12.dp, 16.dp)", count=1)
replace(STRATEGY, "verticalArrangement = Arrangement.spacedBy(11.dp),\n    ) {\n        item { CompactLotterySwitcher", "verticalArrangement = Arrangement.spacedBy(9.dp),\n    ) {\n        item { CompactLotterySwitcher", count=1)
replace(STRATEGY, "SurfaceCard(radius = 21.dp)", "SurfaceCard(radius = 20.dp)", count=3)
replace(STRATEGY, "Column(Modifier.padding(15.dp))", "Column(Modifier.padding(14.dp))", count=3)
replace(STRATEGY, "CompactNumberRowV2(selected.top7, size = 33, spread = true)", "CompactNumberRowV2(selected.top7, size = 31, spread = true)", count=1)
replace(STRATEGY, "LotteryBall(it, size = 27.dp, muted = true)", "LotteryBall(it, size = 26.dp, muted = true)", count=1)

# ---------------------------------------------------------------------------
# Notifications: status lives in one place, type chips stay visible, sheet is grouped.
# ---------------------------------------------------------------------------
PUSH = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/V62PushAlertCenter.kt"
replace(PUSH, ".heightIn(min = 58.dp)", ".heightIn(min = 54.dp)", count=1)
replace(PUSH, "v62ConnectionTitle(status),\n                    color = if (status.instantReady) colors.green else if (status.registered) colors.accent else colors.amber,\n                    fontSize = 11.sp,\n                    fontWeight = FontWeight.SemiBold,", "\"${alerts.size} 条历史通知 · ${alerts.count { !it.isRead }} 条未读\",\n                    color = colors.textDim,\n                    fontSize = 11.sp,\n                    fontWeight = FontWeight.Medium,", count=1)
# Keep event type filtering immediately available. Lottery/source filtering remains behind the filter button.
old_filters = '''                    if (showFilters) {\n                        V62AlertChipRow(V62AlertFilter.entries, filter, V62AlertFilter::label) { filterName = it.name }\n                        V62AlertChipRow(V62AlertLottery.entries, lottery, V62AlertLottery::label) { lotteryName = it.name }\n                        if (activeFilterCount > 0) {'''
new_filters = '''                    V62AlertChipRow(V62AlertFilter.entries, filter, V62AlertFilter::label) { filterName = it.name }\n                    if (showFilters) {\n                        V62AlertChipRow(V62AlertLottery.entries, lottery, V62AlertLottery::label) { lotteryName = it.name }\n                        if (activeFilterCount > 0) {'''
replace(PUSH, old_filters, new_filters, count=1)
# Compact settings and visually group rows without introducing new state/data semantics.
replace(PUSH, "modifier = Modifier.fillMaxWidth().padding(start = 18.dp, end = 18.dp, bottom = 24.dp)", "modifier = Modifier.fillMaxWidth().padding(start = 18.dp, end = 18.dp, bottom = 18.dp)", count=1)
replace(PUSH, "Spacer(Modifier.height(10.dp))\n        V62PreferenceRow(\"启用天机推送\"", "Spacer(Modifier.height(8.dp))\n        Text(\"总开关\", color = colors.textDim, fontSize = 11.sp, fontWeight = FontWeight.Bold)\n        V62PreferenceRow(\"启用天机推送\"", count=1)
replace(PUSH, "V62PreferenceRow(\"启用天机推送\", preferences.enabled) { onPreferencesChange(preferences.copy(enabled = it)) }\n        V62PreferenceRow(\"幸运飞艇\"", "V62PreferenceRow(\"启用天机推送\", preferences.enabled) { onPreferencesChange(preferences.copy(enabled = it)) }\n        Text(\"彩种\", color = colors.textDim, fontSize = 11.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 4.dp))\n        V62PreferenceRow(\"幸运飞艇\"", count=1)
replace(PUSH, "V62PreferenceRow(\"澳洲幸运10\", preferences.azxy10Enabled) { onPreferencesChange(preferences.copy(azxy10Enabled = it)) }\n        V62PreferenceRow(\"云端 AI\"", "V62PreferenceRow(\"澳洲幸运10\", preferences.azxy10Enabled) { onPreferencesChange(preferences.copy(azxy10Enabled = it)) }\n        Text(\"内容类型\", color = colors.textDim, fontSize = 11.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 4.dp))\n        V62PreferenceRow(\"云端 AI\"", count=1)
replace(PUSH, "V62PreferenceRow(\"云端本地\", preferences.nativeEnabled) { onPreferencesChange(preferences.copy(nativeEnabled = it)) }\n        V62PreferenceRow(\"升级预警\"", "V62PreferenceRow(\"云端本地\", preferences.nativeEnabled) { onPreferencesChange(preferences.copy(nativeEnabled = it)) }\n        Text(\"高级\", color = colors.textDim, fontSize = 11.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 4.dp))\n        V62PreferenceRow(\"升级预警\"", count=1)
replace(PUSH, ".fillMaxWidth().heightIn(min = 50.dp)", ".fillMaxWidth().heightIn(min = 46.dp)", count=1)
replace(PUSH, "modifier = Modifier.fillMaxWidth().height(48.dp)", "modifier = Modifier.fillMaxWidth().height(44.dp)", count=1)
replace(PUSH, ".heightIn(min = 42.dp)", ".heightIn(min = 40.dp)")

# ---------------------------------------------------------------------------
# AI chat: give the conversation more room and move secondary tools to More.
# ---------------------------------------------------------------------------
CHAT = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AiChatDialog.kt"
replace(CHAT, ".height(70.dp)", ".height(60.dp)", count=1)
replace(CHAT, "fontSize = 9.5.sp,\n                    lineHeight = 13.sp,", "fontSize = 11.sp,\n                    lineHeight = 14.sp,", count=1)
# Remove history button from the crowded top row and expose it in More.
old_history_button = '''        ChatTopActionButton(\n            icon = Icons.Rounded.History,\n            description = "对话历史",\n            enabled = !session.isRunning,\n            onClick = onHistory,\n        )\n        Spacer(Modifier.width(5.dp))\n'''
replace(CHAT, old_history_button, "", count=1)
old_more_first = '''            DropdownMenu(\n                expanded = moreExpanded,\n                onDismissRequest = dismissMore,\n            ) {\n                DropdownMenuItem(\n                    text = { Text("刷新开奖历史") },'''
new_more_first = '''            DropdownMenu(\n                expanded = moreExpanded,\n                onDismissRequest = dismissMore,\n            ) {\n                DropdownMenuItem(\n                    text = { Text("对话历史") },\n                    leadingIcon = {\n                        Icon(Icons.Rounded.History, contentDescription = null)\n                    },\n                    onClick = {\n                        dismissMore()\n                        onHistory()\n                    },\n                )\n                DropdownMenuItem(\n                    text = { Text("刷新开奖历史") },'''
replace(CHAT, old_more_first, new_more_first, count=1)
replace(CHAT, ".padding(horizontal = 14.dp, vertical = 9.dp)", ".padding(horizontal = 14.dp, vertical = 5.dp)", count=1)
replace(CHAT, "shape = RoundedCornerShape(21.dp)", "shape = RoundedCornerShape(18.dp)", count=1)
replace(CHAT, "shape = RoundedCornerShape(21.dp),", "shape = RoundedCornerShape(18.dp),", count=1)
replace(CHAT, ".padding(horizontal = 13.dp, vertical = 11.dp)", ".padding(horizontal = 12.dp, vertical = 8.dp)", count=1)
replace(CHAT, ".size(38.dp)\n                            .clip(RoundedCornerShape(13.dp))", ".size(34.dp)\n                            .clip(RoundedCornerShape(12.dp))", count=1)
replace(CHAT, "fontSize = 12.5.sp,", "fontSize = 12.sp,", count=1)
replace(CHAT, "fontSize = 9.5.sp,\n                            lineHeight = 14.sp,", "fontSize = 11.sp,\n                            lineHeight = 15.sp,", count=1)
# Chips in the collapsed session control should be readable.
replace(CHAT, "fontSize = 9.5.sp,\n                            fontWeight = FontWeight.SemiBold,", "fontSize = 10.5.sp,\n                            fontWeight = FontWeight.SemiBold,", count=2)
replace(CHAT, "fontSize = 9.sp,\n                    )\n                    Spacer(Modifier.width(5.dp))", "fontSize = 10.5.sp,\n                    )\n                    Spacer(Modifier.width(5.dp))", count=1)
replace(CHAT, "fontSize = 9.sp,\n            fontWeight = FontWeight.Bold,", "fontSize = 10.5.sp,\n            fontWeight = FontWeight.Bold,", count=1)
# Welcome state becomes a lightweight launcher instead of a tutorial wall.
replace(CHAT, ".padding(top = 18.dp)", ".padding(top = 6.dp)", count=1)
replace(CHAT, ".size(54.dp)", ".size(46.dp)", count=1)
replace(CHAT, "shape = RoundedCornerShape(19.dp)", "shape = RoundedCornerShape(17.dp)", count=1)
replace(CHAT, ".clip(RoundedCornerShape(19.dp))", ".clip(RoundedCornerShape(17.dp))", count=1)
replace(CHAT, "shape = RoundedCornerShape(19.dp),", "shape = RoundedCornerShape(17.dp),", count=1)
replace(CHAT, "modifier = Modifier.size(25.dp)", "modifier = Modifier.size(22.dp)", count=1)
replace(CHAT, "fontSize = 19.sp,\n            lineHeight = 25.sp,", "fontSize = 17.sp,\n            lineHeight = 23.sp,", count=1)
replace(CHAT, "modifier = Modifier.padding(top = 5.dp, bottom = 17.dp)", "modifier = Modifier.padding(top = 4.dp, bottom = 10.dp)", count=1)
replace(CHAT, "persona.quickPrompts.take(3).forEach", "persona.quickPrompts.take(2).forEach", count=1)
replace(CHAT, ".padding(vertical = 4.dp)", ".padding(vertical = 3.dp)", count=1)
replace(CHAT, "modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp)", "modifier = Modifier.padding(horizontal = 13.dp, vertical = 10.dp)", count=1)
# Composer suggestions also stay short enough to scan and do not dominate the keyboard edge.
replace(CHAT, "suggestions = persona.quickPrompts.take(3),", "suggestions = persona.quickPrompts.take(2),", count=1)
# AI response metadata was below the visual readability floor.
replace(CHAT, "fontSize = 9.sp,\n                        lineHeight = 13.sp,", "fontSize = 10.5.sp,\n                        lineHeight = 14.sp,", count=1)
replace(CHAT, "fontSize = 9.sp,\n                            fontWeight = FontWeight.Bold,", "fontSize = 10.5.sp,\n                            fontWeight = FontWeight.Bold,", count=1)

# ---------------------------------------------------------------------------
# Server console: interaction blue + AI violet, less duplicate chrome on mobile.
# ---------------------------------------------------------------------------
WEB = "server/app/web_console.py"
replace(WEB, "--primary:#6757f4;--primary2:#9565ff;--primary-soft:#eeebff;", "--primary:#326fe8;--primary2:#7c68f2;--primary-soft:#eaf1ff;--ai:#7657f6;", count=1)
replace(WEB, "--primary:#998bff;--primary2:#c08cff;--primary-soft:#2d2952;", "--primary:#75a5ff;--primary2:#9a8cff;--primary-soft:#202f50;--ai:#9a8cff;", count=1)
replace(WEB, "color-mix(in srgb,var(--primary) 15%,transparent)", "color-mix(in srgb,var(--primary) 10%,transparent)", count=1)
replace(WEB, "color-mix(in srgb,var(--primary2) 11%,transparent)", "color-mix(in srgb,var(--primary2) 8%,transparent)", count=1)

CONSOLE = "server/app/console_v3.py"
# Insert a final v6.5 token layer right before media rules. This intentionally overrides older v5/v6 layers.
anchor = "@media(max-width:1040px){.v510-platform-grid"
insert = '''/* v6.5 UI Final Polish 2: shared density + semantic token layer */\n.tianji-console-v620{--v65-card-radius:18px;--v65-control-radius:14px;--v65-gap:9px}\n.tianji-console-v620 .card,.tianji-console-v620 .lottery-card{border-radius:var(--v65-card-radius)}\n.tianji-console-v620 .btn,.tianji-console-v620 .icon-btn,.tianji-console-v620 .status{border-radius:var(--v65-control-radius)}\n.tianji-console-v620 .v620-realtime-card{border-radius:var(--v65-card-radius)}\n.tianji-console-v620 .v630-health-pill{font-size:11px}\n'''
replace(CONSOLE, anchor, insert + anchor, count=1)
# Rewrite only the mobile sub-block values that are currently below 11px.
replace(CONSOLE, ".tianji-console-v620 .topbar .brand h1{font-size:15px}.tianji-console-v620 .topbar .brand p{display:none}", ".tianji-console-v620 .topbar .mark{display:none}.tianji-console-v620 .topbar .brand h1{display:none}.tianji-console-v620 .topbar .brand p{display:none}", count=1)
replace(CONSOLE, ".v630-health-pill{flex:1 1 calc(50% - 8px);justify-content:flex-start;min-height:32px;padding:0 9px;font-size:10px}", ".v630-health-pill{flex:1 1 calc(50% - 8px);justify-content:flex-start;min-height:34px;padding:0 9px;font-size:11px}", count=1)
replace(CONSOLE, ".v620-realtime-head>span{font-size:10px}", ".v620-realtime-head>span{font-size:11px}", count=1)
replace(CONSOLE, ".v620-card-state{min-height:21px;padding:0 7px;font-size:9px}", ".v620-card-state{min-height:23px;padding:0 8px;font-size:11px}", count=1)
replace(CONSOLE, ".v620-latency span{font-size:9.5px", ".v620-latency span{font-size:11px", count=1)
replace(CONSOLE, ".v620-latency em{font-size:9.5px", ".v620-latency em{font-size:11px", count=1)
replace(CONSOLE, ".v620-realtime-foot{margin-top:7px;font-size:9.5px", ".v620-realtime-foot{margin-top:7px;font-size:11px", count=1)
replace(CONSOLE, "font-size:9.5px!important", "font-size:11px!important", count=1)

# ---------------------------------------------------------------------------
# Contract tests guard the most regression-prone mobile decisions.
# ---------------------------------------------------------------------------
SERVER_TEST = "server/tests/test_v620_experience.py"
server_text = read(SERVER_TEST)
if "test_v650_mobile_polish_contract" not in server_text:
    server_text += '''\n\ndef test_v650_mobile_polish_contract() -> None:\n    from server.app.console_v3 import V510_STYLE\n\n    assert "v6.5 UI Final Polish 2" in V510_STYLE\n    assert ".topbar .brand h1{display:none}" in V510_STYLE\n    assert ".v620-card-state{min-height:23px;padding:0 8px;font-size:11px}" in V510_STYLE\n    assert ".v620-latency span{font-size:11px" in V510_STYLE\n    assert ".mobile-nav .nav-tail{display:none!important}" in V510_STYLE\n'''
    write(SERVER_TEST, server_text)

print("v6.5 UI polish applied")
