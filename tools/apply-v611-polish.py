from __future__ import annotations

from pathlib import Path
import re
import textwrap


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(value, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    value = read(path)
    count = value.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}: {old[:100]!r}")
    write(path, value.replace(old, new, 1))


def regex_once(path: str, pattern: str, replacement: str) -> None:
    value = read(path)
    updated, count = re.subn(pattern, replacement, value, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{path}: regex expected one match, found {count}: {pattern[:120]!r}")
    write(path, updated)


# Repository and release hygiene.
readme = read("README.md")
old_version = "- 开发版：**6.1.0-beta01 稳定化与统一推送版**\n- 最近正式版：**6.0.0**"
new_version = (
    "- 当前正式版：**6.1.0**\n"
    "- 发布策略：默认仅发布正式稳定版；只有明确测试需求时才使用 Alpha、Beta 或 RC"
)
if old_version in readme:
    readme = readme.replace(old_version, new_version, 1)
elif new_version not in readme:
    raise SystemExit("README version block not found")
write("README.md", readme)

keep_notes = {
    "RELEASE_NOTES_v6.1.0.md",
    "RELEASE_NOTES_v6.0.0.md",
    "RELEASE_NOTES_v5.10.4.md",
}
for path in Path(".").glob("RELEASE_NOTES_v*.md"):
    if path.name not in keep_notes:
        path.unlink()
legacy_verified = Path(".release/v5.5.9-verified.txt")
if legacy_verified.exists():
    legacy_verified.unlink()
release_dir = Path(".release")
if release_dir.exists() and not any(release_dir.iterdir()):
    release_dir.rmdir()

write(
    "tools/check-version-consistency.py",
    textwrap.dedent(
        '''\
        from __future__ import annotations

        import re
        from pathlib import Path

        gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")
        readme = Path("README.md").read_text(encoding="utf-8")
        version = re.search(r'versionName\s*=\s*"([^"]+)"', gradle)
        if version is None:
            raise SystemExit("无法读取 Android versionName")
        current = version.group(1)
        if f"当前正式版：**{current}**" not in readme:
            raise SystemExit(f"README 当前正式版与 Android 不一致：{current}")
        note = Path(f"RELEASE_NOTES_v{current}.md")
        if not note.exists():
            raise SystemExit(f"缺少正式发行说明：{note}")
        print(f"version consistency ok: {current}")
        '''
    ),
)

write(
    "tools/check-ui-contract.py",
    textwrap.dedent(
        '''\
        from __future__ import annotations

        from pathlib import Path

        refined = [
            Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedForecastStrategy.kt"),
            Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedPushAlertCenter.kt"),
            Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/ExperienceOverlays.kt"),
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in refined)
        forbidden = {
            "1 路 AI 已完成": "不得向用户展示内部路数",
            "运行 $running · 完成 $completed": "连接状态不得冒充预测完成状态",
            "fontSize = 8.sp": "关键界面最小字号不得低于 11sp",
            "fontSize = 9.sp": "关键界面最小字号不得低于 11sp",
        }
        failures = [message for token, message in forbidden.items() if token in text]
        if failures:
            raise SystemExit("；".join(failures))
        app = Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt").read_text(encoding="utf-8")
        if "HomePredictionFocusStrip(" in app:
            raise SystemExit("首页不得重复展示第二张预测摘要卡")
        notification = Path("app/src/main/java/com/tianji/probabilitylab/nativev4/push/PushNotificationManager.kt").read_text(encoding="utf-8")
        if "EXTRA_OPEN_PREDICTION" not in notification:
            raise SystemExit("预测完成通知必须支持直达预测首页")
        print("ui contract ok")
        '''
    ),
)

ci_path = ".github/workflows/android-ci.yml"
ci = read(ci_path)
check_lines = (
    "          python tools/check-version-consistency.py\n"
    "          python tools/check-ui-contract.py\n"
)
if check_lines not in ci:
    marker = "          ruby -e \"require 'yaml'; YAML.load_file('.github/workflows/release.yml')\"\n"
    if marker not in ci:
        raise SystemExit("android-ci validation marker not found")
    ci = ci.replace(marker, marker + check_lines, 1)
write(ci_path, ci)

# Atomic delivery claim fixes duplicate Telegram/FCM sends under parallel cycles.
push_path = "server/app/push_alerts.py"
push = read(push_path)
push = push.replace("    delivery = deliver_pending_alerts()\n", "    delivery = deliver_pending_alerts(lottery_key)\n", 1)
push = push.replace(
    "def deliver_pending_alerts() -> dict[str, int]:\n",
    "def deliver_pending_alerts(lottery_filter: str | None = None) -> dict[str, int]:\n",
    1,
)
old_alert_query = '''        alerts = db.execute(
            "SELECT * FROM push_alerts ORDER BY id DESC LIMIT 100"
        ).fetchall()
'''
new_alert_query = '''        if lottery_filter:
            alerts = db.execute(
                "SELECT * FROM push_alerts WHERE lottery=? ORDER BY id DESC LIMIT 100",
                (lottery_filter,),
            ).fetchall()
        else:
            alerts = db.execute(
                "SELECT * FROM push_alerts ORDER BY id DESC LIMIT 100"
            ).fetchall()
'''
if old_alert_query not in push:
    raise SystemExit("push alert query block not found")
push = push.replace(old_alert_query, new_alert_query, 1)
old_deliveries = '''        deliveries = {
            (int(row["alert_id"]), str(row["installation_id"])): dict(row)
            for row in db.execute("SELECT * FROM push_deliveries").fetchall()
        }
'''
if old_deliveries not in push:
    raise SystemExit("stale delivery snapshot block not found")
push = push.replace(old_deliveries, "", 1)
atomic_claim = '''

def _claim_delivery(
    *,
    alert_id: int,
    target_key: str,
    attempted_at: int,
    retry_before: int,
) -> bool:
    """Atomically reserve one alert/target delivery across concurrent cycles."""
    with database.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute(
            """
            SELECT status,attempted_at
            FROM push_deliveries
            WHERE alert_id=? AND installation_id=?
            """,
            (alert_id, target_key),
        ).fetchone()
        if previous is not None:
            if str(previous["status"]) == "sent":
                return False
            if int(previous["attempted_at"]) > retry_before:
                return False
        db.execute(
            """
            INSERT INTO push_deliveries(
                alert_id,installation_id,status,response_code,message,attempted_at
            ) VALUES(?,?,'sending',NULL,'',?)
            ON CONFLICT(alert_id,installation_id) DO UPDATE SET
                status='sending',response_code=NULL,message='',attempted_at=excluded.attempted_at
            """,
            (alert_id, target_key, attempted_at),
        )
    return True
'''
if "def _claim_delivery(" not in push:
    marker = "\ndef _store_delivery(\n"
    if marker not in push:
        raise SystemExit("store delivery marker not found")
    push = push.replace(marker, atomic_claim + marker, 1)
old_allowed = '''                if not _delivery_allowed(
                    deliveries,
                    alert_id=alert_id,
                    target_key=target_key,
                    retry_before=retry_before,
                ):
                    continue
'''
new_claim = '''                if not _claim_delivery(
                    alert_id=alert_id,
                    target_key=target_key,
                    attempted_at=now,
                    retry_before=retry_before,
                ):
                    continue
'''
if push.count(old_allowed) != 2:
    raise SystemExit(f"expected two delivery guards, found {push.count(old_allowed)}")
push = push.replace(old_allowed, new_claim)
write(push_path, push)

# Concurrent delivery regression test.
test_path = "server/tests/test_push_alerts.py"
test = read(test_path)
if "ThreadPoolExecutor" not in test:
    test = test.replace(
        "import unittest\n",
        "import unittest\nfrom concurrent.futures import ThreadPoolExecutor\nimport time\n",
        1,
    )
if "    _claim_delivery,\n" not in test:
    test = test.replace("    DevicePreferences,\n", "    DevicePreferences,\n    _claim_delivery,\n", 1)
if "test_delivery_claim_is_atomic_across_parallel_cycles" not in test:
    method = '''

    def test_delivery_claim_is_atomic_across_parallel_cycles(self) -> None:
        alert_id = materialize_warning_alerts(self.watch(streak=2, latest="202"))[0]
        now = int(time.time() * 1000)

        def claim(_index: int) -> bool:
            return _claim_delivery(
                alert_id=alert_id,
                target_key="telegram:test-chat",
                attempted_at=now,
                retry_before=now - 300_000,
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(claim, range(8)))
        self.assertEqual(1, sum(bool(value) for value in results))
'''
    marker = "\n\nif __name__ == \"__main__\":\n"
    if marker not in test:
        raise SystemExit("push test footer not found")
    test = test.replace(marker, method + marker, 1)
write(test_path, test)

# Remove duplicate home strip from the app shell.
app_path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt"
app = read(app_path)
app, count = re.subn(
    r'''\n                    if \(destination == MainDestination\.HOME && state\.report != null\) \{\n                        HomePredictionFocusStrip\([\s\S]*?\n                        \)\n                    \}\n''',
    "\n",
    app,
    count=1,
)
if count != 1:
    raise SystemExit(f"home strip removal count={count}")
write(app_path, app)

# Adaptive home layout and plain-language copy.
ui_path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedForecastStrategy.kt"
ui = read(ui_path)
if "import androidx.compose.foundation.layout.BoxWithConstraints" not in ui:
    ui = ui.replace(
        "import androidx.compose.foundation.layout.Box\n",
        "import androidx.compose.foundation.layout.Box\nimport androidx.compose.foundation.layout.BoxWithConstraints\n",
        1,
    )
if "import androidx.compose.foundation.layout.fillMaxSize" not in ui:
    ui = ui.replace(
        "import androidx.compose.foundation.layout.fillMaxWidth\n",
        "import androidx.compose.foundation.layout.fillMaxSize\nimport androidx.compose.foundation.layout.fillMaxWidth\n",
        1,
    )
new_forecast_screen = '''@Composable
fun RefinedForecastScreen(
    state: AppUiState,
    aiConfigs: List<AiConfig>,
    onSelectLottery: (LotteryType) -> Unit,
    onRefresh: () -> Unit,
    onAnalyzeAllAi: () -> Unit,
    onCancelAi: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var section by rememberSaveable(state.lottery.apiKey) { mutableIntStateOf(0) }
    var selectedPosition by rememberSaveable(state.report?.targetPeriod) {
        mutableIntStateOf(state.report?.selectedPosition ?: 0)
    }
    val report = state.report
    val hasContent = state.snapshot != null && report != null

    BoxWithConstraints(modifier = modifier) {
        val wideLayout = maxWidth >= 600.dp && hasContent
        if (wideLayout) {
            Row(
                modifier = Modifier.fillMaxSize().padding(12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                LazyColumn(
                    modifier = Modifier.weight(1f),
                    contentPadding = PaddingValues(bottom = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(11.dp),
                ) {
                    item("lottery-switch") { CompactLotterySwitcher(state.lottery, onSelectLottery) }
                    item("forecast") {
                        RefinedForecastCard(requireNotNull(report), selectedPosition) { selectedPosition = it }
                    }
                    item("live-summary") { RefinedLiveCard(state, onRefresh) }
                }
                LazyColumn(
                    modifier = Modifier.weight(1f),
                    contentPadding = PaddingValues(bottom = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(11.dp),
                ) {
                    item("tabs") {
                        SegmentedTabs(
                            items = listOf("分析", "概率", "模型"),
                            selectedIndex = section,
                            onSelected = { section = it },
                        )
                    }
                    when (section) {
                        0 -> item("ai") {
                            RefinedAiPanel(state, aiConfigs, onAnalyzeAllAi, onCancelAi)
                        }
                        1 -> item("probability") {
                            RefinedProbabilityCard(requireNotNull(report), selectedPosition) { selectedPosition = it }
                        }
                        else -> item("models") { RefinedModelCardV2(requireNotNull(report).models) }
                    }
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 12.dp, end = 12.dp, top = 12.dp, bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(11.dp),
            ) {
                item("lottery-switch") { CompactLotterySwitcher(state.lottery, onSelectLottery) }
                if (!hasContent) {
                    item("empty") {
                        EmptyState(
                            title = if (state.isLoading) "正在同步开奖数据" else "暂时无法生成预测",
                            detail = state.error ?: "数据同步完成后会自动生成结果",
                            loading = state.isLoading,
                        )
                    }
                } else {
                    item("forecast") {
                        RefinedForecastCard(requireNotNull(report), selectedPosition) { selectedPosition = it }
                    }
                    item("live-summary") { RefinedLiveCard(state, onRefresh) }
                    item("tabs") {
                        SegmentedTabs(
                            items = listOf("分析", "概率", "模型"),
                            selectedIndex = section,
                            onSelected = { section = it },
                        )
                    }
                    when (section) {
                        0 -> item("ai") {
                            RefinedAiPanel(state, aiConfigs, onAnalyzeAllAi, onCancelAi)
                        }
                        1 -> item("probability") {
                            RefinedProbabilityCard(requireNotNull(report), selectedPosition) { selectedPosition = it }
                        }
                        else -> item("models") { RefinedModelCardV2(requireNotNull(report).models) }
                    }
                }
            }
        }
    }
}

@Composable
private fun RefinedLiveCard'''
ui, count = re.subn(
    r'''@Composable\nfun RefinedForecastScreen\([\s\S]*?\n\}\n\n@Composable\nprivate fun RefinedLiveCard''',
    new_forecast_screen,
    ui,
    count=1,
)
if count != 1:
    raise SystemExit(f"forecast screen replacement count={count}")
copy_replacements = {
    'if (report.mode == EvidenceMode.CERTIFIED) "前向证据通过" else "观察模式 · 暂未认证"': '"结果已生成 · 持续验证中"',
    'color = if (report.mode == EvidenceMode.CERTIFIED) colors.green else colors.amber,': 'color = colors.textDim,',
    'if (report.displayUsesShadow) "影子实验六码" else "本机集成六码"': '"预测六码"',
    'Text("AI 联合分析", color = colors.text, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold)': 'Text("AI 预测", color = colors.text, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold)',
    '"${complete.size} 个可用配置 · 独立分析后再形成共识"': '"${complete.size} 个 AI 模型可用 · 每个模型单独生成结果"',
    'evaluation.stable -> "已形成共识"': 'evaluation.stable -> "结果已生成"',
    'state.aiForecasts.isNotEmpty() -> "模型有分歧"': 'state.aiForecasts.isNotEmpty() -> "结果需要复核"',
    'else -> "等待分析"': 'else -> "尚未生成"',
    'val completed = statuses.count { it.state == AiConnectionState.CONNECTED }': 'val available = complete.size\n                val results = state.aiForecasts.size',
    '"运行 $running · 完成 $completed · 失败 $failed"': '"可用 $available · 正在 $running · 本期结果 $results · 失败 $failed"',
    '"AI 共识 · 第${positionNameV2(consensus.position)}名"': '"AI 综合结果 · 第${positionNameV2(consensus.position)}名"',
    'if (state.isAiAnalyzing) "多个 AI 正在独立分析" else "开始全部 AI 分析"': 'if (state.isAiAnalyzing) "正在生成本期预测" else "生成本期 AI 预测"',
    '"七码三段观察"': '"七码观察方案"',
    '"时间切分留出验证"': '"历史验证"',
    '"证据闸门"': '"验证条件"',
    '"全部证据闸门已通过"': '"全部验证条件已通过"',
    '"证据通过" else "观察模式"': '"验证通过" else "持续观察"',
}
for old, new in copy_replacements.items():
    if old not in ui:
        raise SystemExit(f"missing UI token: {old}")
    ui = ui.replace(old, new)
ui = ui.replace("fontSize = 8.sp", "fontSize = 11.sp")
ui = ui.replace("fontSize = 9.sp", "fontSize = 11.sp")
ui = ui.replace("fontSize = 10.sp", "fontSize = 11.sp")
write(ui_path, ui)

# Keep only the actual AI running dock in the overlay file.
overlay_path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/ExperienceOverlays.kt"
overlay = read(overlay_path)
overlay, count = re.subn(
    r'''@Composable\nfun HomePredictionFocusStrip\([\s\S]*?\n\}\n\n@Composable\nfun AiReviewProgressDock''',
    "@Composable\nfun AiReviewProgressDock",
    overlay,
    count=1,
)
if count != 1:
    raise SystemExit(f"overlay strip removal count={count}")
overlay = overlay.replace("fontSize = 10.sp", "fontSize = 11.sp")
write(overlay_path, overlay)

# Ripple and light haptic feedback on the bottom bar.
bottom_path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/MainBottomBar.kt"
bottom = read(bottom_path)
if "LocalHapticFeedback" not in bottom:
    bottom = bottom.replace(
        "import androidx.compose.ui.graphics.Brush\n",
        "import androidx.compose.ui.graphics.Brush\n"
        "import androidx.compose.ui.hapticfeedback.HapticFeedbackType\n"
        "import androidx.compose.ui.platform.LocalHapticFeedback\n",
        1,
    )
bottom = bottom.replace(
    "    val interaction = remember { MutableInteractionSource() }\n",
    "    val haptics = LocalHapticFeedback.current\n",
)
old_click = '''            .clickable(
                interactionSource = interaction,
                indication = null,
                onClick = onClick,
            )'''
new_click = '''            .clickable {
                haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
                onClick()
            }'''
if bottom.count(old_click) != 2:
    raise SystemExit(f"expected two bottom bar click handlers, found {bottom.count(old_click)}")
bottom = bottom.replace(old_click, new_click)
write(bottom_path, bottom)

# Prediction notifications open the home prediction directly.
notify_path = "app/src/main/java/com/tianji/probabilitylab/nativev4/push/PushNotificationManager.kt"
notify = read(notify_path)
old_navigation = '''object PushAlertNavigation {
    private val pending = MutableStateFlow<Long?>(null)
    val pendingAlertId = pending.asStateFlow()
    fun open(alertId: Long = 0L) { pending.value = alertId }
    fun consume() { pending.value = null }
}
'''
new_navigation = '''data class PushPredictionTarget(val lottery: String, val targetPeriod: String)

object PushAlertNavigation {
    private val pending = MutableStateFlow<Long?>(null)
    private val prediction = MutableStateFlow<PushPredictionTarget?>(null)
    val pendingAlertId = pending.asStateFlow()
    val pendingPrediction = prediction.asStateFlow()
    fun open(alertId: Long = 0L) { pending.value = alertId }
    fun consume() { pending.value = null }
    fun openPrediction(lottery: String, targetPeriod: String) {
        prediction.value = PushPredictionTarget(lottery, targetPeriod)
    }
    fun consumePrediction() { prediction.value = null }
}
'''
if old_navigation not in notify:
    raise SystemExit("push navigation block not found")
notify = notify.replace(old_navigation, new_navigation, 1)
notify = notify.replace(
    '''    const val EXTRA_OPEN_ALERT_CENTER = "open_alert_center"
    const val EXTRA_ALERT_ID = "alert_id"
''',
    '''    const val EXTRA_OPEN_ALERT_CENTER = "open_alert_center"
    const val EXTRA_OPEN_PREDICTION = "open_prediction"
    const val EXTRA_ALERT_ID = "alert_id"
    const val EXTRA_LOTTERY = "lottery"
    const val EXTRA_TARGET_PERIOD = "target_period"
''',
    1,
)
notify = notify.replace(
    "        val openIntent = openAlertIntent(context, alert.id, notificationId)\n",
    '''        val openIntent = if (alert.eventType == PushProtocol.EVENT_PREDICTION_READY) {
            openPredictionIntent(context, alert, notificationId)
        } else {
            openAlertIntent(context, alert.id, notificationId)
        }
''',
    1,
)
open_prediction = '''
    private fun openPredictionIntent(
        context: Context,
        alert: PushAlert,
        requestCode: Int,
    ): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(EXTRA_OPEN_PREDICTION, true)
            putExtra(EXTRA_LOTTERY, alert.lottery)
            putExtra(EXTRA_TARGET_PERIOD, alert.latestTargetPeriod)
        }
        return PendingIntent.getActivity(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }
'''
marker = "\n    private fun openAlertIntent(\n"
if marker not in notify:
    raise SystemExit("open alert intent marker not found")
notify = notify.replace(marker, open_prediction + marker, 1)
write(notify_path, notify)

activity_path = "app/src/main/java/com/tianji/probabilitylab/nativev4/MainActivity.kt"
activity = read(activity_path)
activity = activity.replace(
    "        intent ?: return\n        val openAlertCenter =\n",
    '''        intent ?: return
        val openPrediction =
            intent.getBooleanExtra(PushNotificationManager.EXTRA_OPEN_PREDICTION, false) ||
                intent.getStringExtra(PushNotificationManager.EXTRA_OPEN_PREDICTION)
                    ?.toBooleanStrictOrNull() == true
        if (openPrediction) {
            PushAlertNavigation.openPrediction(
                lottery = intent.getStringExtra(PushNotificationManager.EXTRA_LOTTERY).orEmpty(),
                targetPeriod = intent.getStringExtra(PushNotificationManager.EXTRA_TARGET_PERIOD).orEmpty(),
            )
            return
        }
        val openAlertCenter =
''',
    1,
)
write(activity_path, activity)

app = read(app_path)
app = app.replace(
    "import com.tianji.probabilitylab.nativev4.push.PushAlertNavigation\n",
    "import com.tianji.probabilitylab.nativev4.model.LotteryType\n"
    "import com.tianji.probabilitylab.nativev4.push.PushAlertNavigation\n",
    1,
)
app = app.replace(
    "    val pendingAlertId by PushAlertNavigation.pendingAlertId.collectAsState()\n",
    "    val pendingAlertId by PushAlertNavigation.pendingAlertId.collectAsState()\n"
    "    val pendingPrediction by PushAlertNavigation.pendingPrediction.collectAsState()\n",
    1,
)
prediction_effect = '''
    LaunchedEffect(pendingPrediction) {
        pendingPrediction?.let { target ->
            LotteryType.entries.firstOrNull { it.apiKey == target.lottery }
                ?.let(controller::selectLottery)
            destination = MainDestination.HOME
            showAlertCenter = false
            focusedAlertId = null
            PushAlertNavigation.consumePrediction()
        }
    }
'''
marker = "\n    LaunchedEffect(pendingAlertId) {\n"
if marker not in app:
    raise SystemExit("pending alert effect marker not found")
app = app.replace(marker, prediction_effect + marker, 1)
write(app_path, app)

write(
    "app/src/test/java/com/tianji/probabilitylab/nativev4/push/PushNavigationTest.kt",
    textwrap.dedent(
        '''\
        package com.tianji.probabilitylab.nativev4.push

        import org.junit.Assert.assertEquals
        import org.junit.Assert.assertNull
        import org.junit.Test

        class PushNavigationTest {
            @Test
            fun predictionTargetCanBeOpenedAndConsumed() {
                PushAlertNavigation.openPrediction("azxy10", "21348220")
                assertEquals("azxy10", PushAlertNavigation.pendingPrediction.value?.lottery)
                assertEquals("21348220", PushAlertNavigation.pendingPrediction.value?.targetPeriod)
                PushAlertNavigation.consumePrediction()
                assertNull(PushAlertNavigation.pendingPrediction.value)
            }
        }
        '''
    ),
)

alert_ui = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedPushAlertCenter.kt"
alert_text = read(alert_ui).replace("fontSize = 9.sp", "fontSize = 11.sp").replace(
    "fontSize = 10.sp", "fontSize = 11.sp"
)
write(alert_ui, alert_text)

# Server health metrics for AI and delivery channels.
bootstrap_path = "server/app/bootstrap.py"
bootstrap = read(bootstrap_path)
bootstrap = bootstrap.replace(
    "from . import push_alerts  # noqa: E402\n",
    "from . import push_alerts, telegram_events  # noqa: E402\n",
    1,
)
health_helpers = '''

def _ai_health() -> dict[str, object]:
    jobs = {
        lottery_key: _decode_state(f"ai_job:{lottery_key}") or {}
        for lottery_key in LOTTERIES
    }
    statuses = [str(value.get("status") or "waiting") for value in jobs.values()]
    with database.connection() as db:
        cutoff = int(time.time() * 1000) - 86_400_000
        row = db.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN settled_at IS NOT NULL THEN 1 ELSE 0 END) AS settled
            FROM forecasts
            WHERE source='ai' AND created_at>=?
            """,
            (cutoff,),
        ).fetchone()
    return {
        "jobs": jobs,
        "running": sum(status in {"queued", "running"} for status in statuses),
        "completed": sum(status in {"completed", "duplicate"} for status in statuses),
        "failed": sum(status == "error" for status in statuses),
        "forecasts_24h": int(row["total"] or 0),
        "settled_24h": int(row["settled"] or 0),
    }


def _delivery_health() -> dict[str, object]:
    push_alerts.initialize()
    telegram_events.initialize()
    cutoff = int(time.time() * 1000) - 86_400_000
    with database.connection() as db:
        push_rows = db.execute(
            """
            SELECT
                CASE WHEN installation_id LIKE 'telegram:%' THEN 'telegram' ELSE 'fcm' END AS channel,
                status,
                COUNT(*) AS total
            FROM push_deliveries
            WHERE attempted_at>=?
            GROUP BY channel,status
            """,
            (cutoff,),
        ).fetchall()
        event_rows = db.execute(
            """
            SELECT status,COUNT(*) AS total
            FROM telegram_event_deliveries
            WHERE attempted_at>=?
            GROUP BY status
            """,
            (cutoff,),
        ).fetchall()
        device_row = db.execute(
            """
            SELECT COUNT(*) AS devices,
                   SUM(CASE WHEN fcm_token<>'' THEN 1 ELSE 0 END) AS tokens
            FROM push_devices
            WHERE enabled=1
            """
        ).fetchone()
    channels: dict[str, dict[str, int]] = {"fcm": {}, "telegram": {}}
    for row in push_rows:
        channel = str(row["channel"])
        channels.setdefault(channel, {})[str(row["status"])] = int(row["total"])
    for row in event_rows:
        status = str(row["status"])
        channels.setdefault("telegram", {})[status] = (
            channels.setdefault("telegram", {}).get(status, 0) + int(row["total"])
        )
    return {
        "channels": channels,
        "active_devices": int(device_row["devices"] or 0),
        "fcm_tokens": int(device_row["tokens"] or 0),
        "window_hours": 24,
    }
'''
if "def _ai_health()" not in bootstrap:
    marker = "\n\n@app.get(\n    \"/health/detail\",\n"
    if marker not in bootstrap:
        raise SystemExit("health detail marker not found")
    bootstrap = bootstrap.replace(marker, health_helpers + marker, 1)
bootstrap = bootstrap.replace(
    '''        "maintenance": cleanup_runtime_state(),
        "deployment": deployment_status(SERVICE_VERSION),
        "version": SERVICE_VERSION,
''',
    '''        "maintenance": cleanup_runtime_state(),
        "deployment": deployment_status(SERVICE_VERSION),
        "ai_health": _ai_health(),
        "delivery_health": _delivery_health(),
        "version": SERVICE_VERSION,
''',
    1,
)
write(bootstrap_path, bootstrap)

# Console no longer hides refresh failures and exposes AI/FCM/Telegram health.
console_path = "server/app/console_v3.py"
console = read(console_path)
console = console.replace(
    "  const commit=value=>String(value||'—').slice(0,12);\n",
    "  const commit=value=>String(value||'—').slice(0,12);\n  let lastPlatformSuccess=0;\n",
    1,
)
console = console.replace(
    "      const data=await response.json();\n",
    "      const data=await response.json();\n      lastPlatformSuccess=Date.now();\n",
    1,
)
console = console.replace(
    '''      const backup=data.backup||{};
      const deploy=data.deployment||{};
''',
    '''      const backup=data.backup||{};
      const deploy=data.deployment||{};
      const aiHealth=data.ai_health||{};
      const delivery=data.delivery_health||{};
      const fcm=(delivery.channels||{}).fcm||{};
      const telegram=(delivery.channels||{}).telegram||{};
''',
    1,
)
console = console.replace(
    '''          <article class="v510-platform-card"><span>运行 Commit</span><strong class="v510-commit">${esc(current)}</strong></article>
        </div>
''',
    '''          <article class="v510-platform-card"><span>运行 Commit</span><strong class="v510-commit">${esc(current)}</strong></article>
          <article class="v510-platform-card"><span>AI 任务</span><strong>${Number(aiHealth.running||0)} 运行 · ${Number(aiHealth.failed||0)} 失败</strong></article>
          <article class="v510-platform-card"><span>FCM 24 小时</span><strong>${Number(fcm.sent||0)} 成功 · ${Number(fcm.failed||0)} 失败</strong></article>
          <article class="v510-platform-card"><span>Telegram 24 小时</span><strong>${Number(telegram.sent||0)} 成功 · ${Number(telegram.failed||0)} 失败</strong></article>
        </div>
''',
    1,
)
console = console.replace(
    "    }catch(_error){}\n",
    '''    }catch(_error){
      let section=document.getElementById('v510Platform');
      if(!section){
        const overview=document.getElementById('panel-overview');
        if(!overview)return;
        section=document.createElement('section');section.id='v510Platform';section.className='section v510-platform';overview.appendChild(section);
      }
      section.innerHTML=`<div class="v510-deploy attention"><div class="v510-deploy-main"><div class="v510-deploy-title"><i class="v510-deploy-dot"></i>状态刷新失败</div><div class="v510-deploy-message">控制台暂时无法读取最新服务状态；页面中的旧数据不能视为当前状态，请检查网络后重试。</div></div><div class="v510-deploy-meta"><span>最后成功刷新</span><strong>${lastPlatformSuccess?new Date(lastPlatformSuccess).toLocaleTimeString('zh-CN',{hour12:false}):'尚未成功'}</strong></div></div>`;
    }
''',
    1,
)
write(console_path, console)

# Remove unused legacy entry points while retaining shared components.
screens_path = "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/Screens.kt"
screens = read(screens_path)
screens, count = re.subn(
    r'''@Composable\nfun ForecastScreen\([\s\S]*?\n\}\n\n@Composable\nprivate fun LiveDrawCard''',
    "@Composable\nprivate fun LiveDrawCard",
    screens,
    count=1,
)
if count != 1:
    raise SystemExit(f"legacy forecast removal count={count}")
write(screens_path, screens)

legacy_alert = Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/PushAlertCenter.kt")
if legacy_alert.exists():
    symbol = "PushAlertCenterScreen("
    references = 0
    for file in Path("app/src/main/java").rglob("*.kt"):
        if file == legacy_alert:
            continue
        references += file.read_text(encoding="utf-8").count(symbol)
    if references == 0:
        legacy_alert.unlink()

matrix_path = "docs/UI_REGRESSION_MATRIX.md"
matrix = read(matrix_path)
appendix = '''

## CI 自动界面契约

- 禁止重新出现“1 路 AI 已完成”等内部状态文案。
- 首页不得重复展示两张目标期摘要卡。
- Refined 关键页面禁止 8sp / 9sp 字号。
- 预测完成通知必须支持直接进入预测首页。
- README、Android versionName 与正式发行说明必须一致。
'''
if "## CI 自动界面契约" not in matrix:
    matrix += appendix
write(matrix_path, matrix)

print("v6.1.1 polish applied")
