from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"marker not found in {path}: {old[:120]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: str, marker: str, addition: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if addition.strip() in text:
        return
    if marker not in text:
        raise SystemExit(f"append marker not found in {path}")
    file.write_text(text.replace(marker, marker + addition, 1), encoding="utf-8")


replace_once(
    "app/build.gradle.kts",
    '''val cloudBaseUrl = providers.gradleProperty("TIANJI_CLOUD_BASE_URL")
    .orElse("https://tianji-xgl.duckdns.org")
''',
    '''val cloudBaseUrl = providers.gradleProperty("TIANJI_CLOUD_BASE_URL")
    .orElse("https://tianji-xgl.duckdns.org")
val firebaseProjectId = providers.gradleProperty("TIANJI_FIREBASE_PROJECT_ID").orElse("")
val firebaseAppId = providers.gradleProperty("TIANJI_FIREBASE_APP_ID").orElse("")
val firebaseApiKey = providers.gradleProperty("TIANJI_FIREBASE_API_KEY").orElse("")
val firebaseSenderId = providers.gradleProperty("TIANJI_FIREBASE_SENDER_ID").orElse("")
''',
)
replace_once(
    "app/build.gradle.kts",
    '''        buildConfigField("String", "TIANJI_CLOUD_BASE_URL", "\\\"${cloudBaseUrl.get()}\\\"")
''',
    '''        buildConfigField("String", "TIANJI_CLOUD_BASE_URL", "\\\"${cloudBaseUrl.get()}\\\"")
        buildConfigField("String", "TIANJI_FIREBASE_PROJECT_ID", "\\\"${firebaseProjectId.get()}\\\"")
        buildConfigField("String", "TIANJI_FIREBASE_APP_ID", "\\\"${firebaseAppId.get()}\\\"")
        buildConfigField("String", "TIANJI_FIREBASE_API_KEY", "\\\"${firebaseApiKey.get()}\\\"")
        buildConfigField("String", "TIANJI_FIREBASE_SENDER_ID", "\\\"${firebaseSenderId.get()}\\\"")
''',
)
replace_once(
    "app/build.gradle.kts",
    '''    val composeBom = platform("androidx.compose:compose-bom:2026.06.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.core:core-ktx:1.16.0")
''',
    '''    val composeBom = platform("androidx.compose:compose-bom:2026.06.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    val firebaseBom = platform("com.google.firebase:firebase-bom:34.16.0")
    implementation(firebaseBom)
    implementation("com.google.firebase:firebase-messaging")
    implementation("androidx.work:work-runtime-ktx:2.11.2")

    implementation("androidx.core:core-ktx:1.16.0")
''',
)

replace_once(
    "app/src/main/AndroidManifest.xml",
    '''        <service
            android:name=".service.AiForegroundService"
            android:exported="false"
            android:foregroundServiceType="dataSync" />

        <activity
''',
    '''        <service
            android:name=".service.AiForegroundService"
            android:exported="false"
            android:foregroundServiceType="dataSync" />

        <service
            android:name=".push.TianjiMessagingService"
            android:exported="false">
            <intent-filter>
                <action android:name="com.google.firebase.MESSAGING_EVENT" />
            </intent-filter>
        </service>

        <meta-data
            android:name="com.google.firebase.messaging.default_notification_channel_id"
            android:value="tianji_prediction_alerts" />

        <activity
''',
)

Path("app/src/main/java/com/tianji/probabilitylab/nativev4/TianjiApplication.kt").write_text(
    '''package com.tianji.probabilitylab.nativev4

import android.app.Application
import com.tianji.probabilitylab.nativev4.push.PushAlertCoordinator

class TianjiApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        TianjiRuntime.from(this)
        PushAlertCoordinator.initialize(this)
    }
}
''',
    encoding="utf-8",
)

Path("app/src/main/java/com/tianji/probabilitylab/nativev4/MainActivity.kt").write_text(
    '''package com.tianji.probabilitylab.nativev4

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import com.tianji.probabilitylab.nativev4.push.PushAlertNavigation
import com.tianji.probabilitylab.nativev4.push.PushNotificationManager
import com.tianji.probabilitylab.nativev4.ui.TianjiApp

class MainActivity : ComponentActivity() {
    private val notificationPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
        )
        handlePushIntent(intent)
        requestNotificationPermission()
        setContent { TianjiApp() }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handlePushIntent(intent)
    }

    private fun handlePushIntent(intent: Intent?) {
        if (intent?.getBooleanExtra(PushNotificationManager.EXTRA_OPEN_ALERT_CENTER, false) == true) {
            PushAlertNavigation.open(
                intent.getLongExtra(PushNotificationManager.EXTRA_ALERT_ID, 0L),
            )
        }
    }

    private fun requestNotificationPermission() {
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
''',
    encoding="utf-8",
)

replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AppShellV2.kt",
    '''import androidx.compose.material.icons.rounded.KeyboardArrowRight
import androidx.compose.material.icons.rounded.Refresh
''',
    '''import androidx.compose.material.icons.rounded.KeyboardArrowRight
import androidx.compose.material.icons.rounded.Notifications
import androidx.compose.material.icons.rounded.Refresh
''',
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AppShellV2.kt",
    '''    canGoBack: Boolean = false,
    onBack: (() -> Unit)? = null,
) {
''',
    '''    canGoBack: Boolean = false,
    onBack: (() -> Unit)? = null,
    unreadAlerts: Int = 0,
    onAlerts: () -> Unit = {},
) {
''',
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/AppShellV2.kt",
    '''        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(colors.glass)
                .border(1.dp, colors.lineStrong, RoundedCornerShape(12.dp))
                .clickable(enabled = !isRefreshing, onClick = onRefresh),
''',
    '''        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(colors.glass)
                .border(1.dp, colors.lineStrong, RoundedCornerShape(12.dp))
                .clickable(onClick = onAlerts),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.Rounded.Notifications,
                contentDescription = "打开预警中心",
                tint = if (unreadAlerts > 0) colors.amber else colors.textSoft,
                modifier = Modifier.size(19.dp),
            )
            if (unreadAlerts > 0) {
                Text(
                    unreadAlerts.coerceAtMost(99).toString(),
                    color = Color.White,
                    fontSize = 7.sp,
                    fontWeight = FontWeight.ExtraBold,
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .clip(CircleShape)
                        .background(colors.red)
                        .padding(horizontal = 3.dp, vertical = 1.dp),
                )
            }
        }
        Spacer(Modifier.width(6.dp))

        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(colors.glass)
                .border(1.dp, colors.lineStrong, RoundedCornerShape(12.dp))
                .clickable(enabled = !isRefreshing, onClick = onRefresh),
''',
)

replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/SettingsHubV2.kt",
    '''import androidx.compose.material.icons.rounded.Info
import androidx.compose.material.icons.rounded.Psychology
''',
    '''import androidx.compose.material.icons.rounded.Info
import androidx.compose.material.icons.rounded.NotificationsActive
import androidx.compose.material.icons.rounded.Psychology
''',
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/SettingsHubV2.kt",
    '''    onAnalyzeAi: (String) -> Unit,
    onAiConcurrencyChanged: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
''',
    '''    onAnalyzeAi: (String) -> Unit,
    onAiConcurrencyChanged: (Int) -> Unit,
    pushUnreadCount: Int,
    onOpenPushAlerts: () -> Unit,
    modifier: Modifier = Modifier,
) {
''',
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/SettingsHubV2.kt",
    '''            appearanceMode = appearanceMode,
            onOpen = { page = it },
            modifier = modifier,
''',
    '''            appearanceMode = appearanceMode,
            pushUnreadCount = pushUnreadCount,
            onOpenPushAlerts = onOpenPushAlerts,
            onOpen = { page = it },
            modifier = modifier,
''',
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/SettingsHubV2.kt",
    '''    appearanceMode: AppearanceMode,
    onOpen: (SettingsPageV2) -> Unit,
    modifier: Modifier,
) {
''',
    '''    appearanceMode: AppearanceMode,
    pushUnreadCount: Int,
    onOpenPushAlerts: () -> Unit,
    onOpen: (SettingsPageV2) -> Unit,
    modifier: Modifier,
) {
''',
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/SettingsHubV2.kt",
    '''        item {
            SettingsEntry(
                Icons.Rounded.ColorLens,
''',
    '''        item {
            SettingsEntry(
                Icons.Rounded.NotificationsActive,
                "预警与推送",
                "三期不中即时提醒、接收范围和历史预警",
                onOpenPushAlerts,
                if (pushUnreadCount > 0) "$pushUnreadCount 条未读" else "已开启",
            )
        }
        item {
            SettingsEntry(
                Icons.Rounded.ColorLens,
''',
)

replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt",
    '''import com.tianji.probabilitylab.nativev4.service.AiForegroundService
''',
    '''import com.tianji.probabilitylab.nativev4.push.PushAlertCoordinator
import com.tianji.probabilitylab.nativev4.push.PushAlertNavigation
import com.tianji.probabilitylab.nativev4.service.AiForegroundService
''',
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt",
    '''    val appearanceMode by appearanceStore.appearance.collectAsState(initial = AppearanceMode.SYSTEM)
    val scope = rememberCoroutineScope()
''',
    '''    val appearanceMode by appearanceStore.appearance.collectAsState(initial = AppearanceMode.SYSTEM)
    val pushAlerts by PushAlertCoordinator.alerts.collectAsState()
    val pushPreferences by PushAlertCoordinator.preferences.collectAsState()
    val pushStatus by PushAlertCoordinator.status.collectAsState()
    val pendingAlertId by PushAlertNavigation.pendingAlertId.collectAsState()
    val scope = rememberCoroutineScope()
''',
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt",
    '''    var destination by rememberSaveable { mutableStateOf(MainDestination.HOME) }
    var showChat by rememberSaveable { mutableStateOf(false) }

    BackHandler(enabled = showChat || destination != MainDestination.HOME) {
        if (showChat) showChat = false else destination = MainDestination.HOME
    }
''',
    '''    var destination by rememberSaveable { mutableStateOf(MainDestination.HOME) }
    var showChat by rememberSaveable { mutableStateOf(false) }
    var showAlertCenter by rememberSaveable { mutableStateOf(false) }
    var focusedAlertId by rememberSaveable { mutableStateOf<Long?>(null) }

    LaunchedEffect(pendingAlertId) {
        pendingAlertId?.let { alertId ->
            focusedAlertId = alertId.takeIf { it > 0L }
            showAlertCenter = true
            PushAlertNavigation.consume()
        }
    }

    BackHandler(enabled = showAlertCenter || showChat || destination != MainDestination.HOME) {
        when {
            showAlertCenter -> {
                showAlertCenter = false
                focusedAlertId = null
            }
            showChat -> showChat = false
            else -> destination = MainDestination.HOME
        }
    }
''',
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt",
    '''                            onRefresh = refreshSafely,
                        )
''',
    '''                            onRefresh = refreshSafely,
                            unreadAlerts = pushAlerts.count { !it.isRead },
                            onAlerts = {
                                focusedAlertId = null
                                showAlertCenter = true
                            },
                        )
''',
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt",
    '''                                        onAiConcurrencyChanged = controller::setAiConcurrency,
                                        onAnalyzeAi = { id -> controller.analyzeWithAi(id) },
                                        modifier = Modifier.fillMaxSize(),
''',
    '''                                        onAiConcurrencyChanged = controller::setAiConcurrency,
                                        onAnalyzeAi = { id -> controller.analyzeWithAi(id) },
                                        pushUnreadCount = pushAlerts.count { !it.isRead },
                                        onOpenPushAlerts = {
                                            focusedAlertId = null
                                            showAlertCenter = true
                                        },
                                        modifier = Modifier.fillMaxSize(),
''',
)
replace_once(
    "app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt",
    '''                if (showChat) {
                    AiChatDialog(
                        controller = chatController,
                        configs = controller.aiConfigs,
                        modelCatalogs = controller.aiAvailableModels,
                        snapshot = state.snapshot,
                        report = state.report,
                        onRefresh = refreshSafely,
                        onDismiss = { showChat = false },
                    )
                }
''',
    '''                if (showChat) {
                    AiChatDialog(
                        controller = chatController,
                        configs = controller.aiConfigs,
                        modelCatalogs = controller.aiAvailableModels,
                        snapshot = state.snapshot,
                        report = state.report,
                        onRefresh = refreshSafely,
                        onDismiss = { showChat = false },
                    )
                }

                if (showAlertCenter) {
                    PushAlertCenterScreen(
                        alerts = pushAlerts,
                        preferences = pushPreferences,
                        status = pushStatus,
                        focusAlertId = focusedAlertId,
                        onPreferencesChange = PushAlertCoordinator::updatePreferences,
                        onRead = PushAlertCoordinator::markRead,
                        onReadAll = PushAlertCoordinator::markAllRead,
                        onRefresh = PushAlertCoordinator::refresh,
                        onClose = {
                            showAlertCenter = false
                            focusedAlertId = null
                        },
                        modifier = Modifier.fillMaxSize(),
                    )
                }
''',
)

replace_once(
    "server/app/config.py",
    '''    ai_api_key: str
    ai_timeout_seconds: int

    @property
    def ai_enabled(self) -> bool:
''',
    '''    ai_api_key: str
    ai_timeout_seconds: int
    fcm_project_id: str
    fcm_service_account_b64: str
    push_threshold: int

    @property
    def ai_enabled(self) -> bool:
''',
)
replace_once(
    "server/app/config.py",
    '''    @property
    def data_dir(self) -> str:
''',
    '''    @property
    def fcm_enabled(self) -> bool:
        return bool(self.fcm_project_id and self.fcm_service_account_b64)

    @property
    def data_dir(self) -> str:
''',
)
replace_once(
    "server/app/config.py",
    '''        ai_api_key=os.getenv("TIANJI_AI_API_KEY", "").strip(),
        ai_timeout_seconds=_int_env("TIANJI_AI_TIMEOUT_SECONDS", 120, 20, 300),
''',
    '''        ai_api_key=os.getenv("TIANJI_AI_API_KEY", "").strip(),
        ai_timeout_seconds=_int_env("TIANJI_AI_TIMEOUT_SECONDS", 120, 20, 300),
        fcm_project_id=os.getenv("TIANJI_FCM_PROJECT_ID", "").strip(),
        fcm_service_account_b64=os.getenv("TIANJI_FCM_SERVICE_ACCOUNT_B64", "").strip(),
        push_threshold=_int_env("TIANJI_PUSH_THRESHOLD", 3, 3, 10),
''',
)
replace_once(
    "server/requirements.txt",
    '''pydantic==2.11.7
''',
    '''pydantic==2.11.7
google-auth==2.56.0
requests==2.34.2
''',
)
append_once(
    ".env.example",
    "TIANJI_AI_TIMEOUT_SECONDS=120\n",
    '''
# Prediction miss alerts. Keep the service-account JSON outside Git and encode it:
# base64 -w0 firebase-service-account.json
TIANJI_PUSH_THRESHOLD=3
TIANJI_FCM_PROJECT_ID=
TIANJI_FCM_SERVICE_ACCOUNT_B64=
''',
)

replace_once(
    "server/app/main.py",
    '''from . import ai
''',
    '''from . import ai, push_alerts
''',
)
replace_once(
    "server/app/main.py",
    '''class PasswordPayload(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


def require_admin_token''',
    '''class PasswordPayload(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class PushPreferencesPayload(BaseModel):
    enabled: bool = True
    xyft_enabled: bool = True
    azxy10_enabled: bool = True
    ai_enabled: bool = True
    native_enabled: bool = True
    escalation_enabled: bool = True


class PushDevicePayload(BaseModel):
    installation_id: str = Field(min_length=8, max_length=128)
    secret: str = Field(min_length=24, max_length=256)
    fcm_token: str = Field(default="", max_length=4096)
    platform: str = Field(default="android", max_length=40)
    app_version: str = Field(default="", max_length=80)
    device_name: str = Field(default="", max_length=160)
    preferences: PushPreferencesPayload = Field(default_factory=PushPreferencesPayload)


def require_admin_token''',
)
replace_once(
    "server/app/main.py",
    '''@app.post("/v1/admin/run", dependencies=[Depends(require_admin_token)])
def run_now_legacy() -> dict[str, object]:
''',
    '''@app.post("/v1/push/devices")
def register_push_device(payload: PushDevicePayload) -> dict[str, Any]:
    try:
        return push_alerts.register_device(
            installation_id=payload.installation_id,
            secret=payload.secret,
            fcm_token=payload.fcm_token,
            platform=payload.platform,
            app_version=payload.app_version,
            device_name=payload.device_name,
            preferences=payload.preferences.model_dump(),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/push/status")
def push_status(
    installation_id: str = Query(min_length=8, max_length=128),
    device_secret: Annotated[str | None, Header(alias="X-Tianji-Device-Secret")] = None,
) -> dict[str, Any]:
    try:
        return push_alerts.device_status(installation_id, device_secret or "")
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.put("/v1/push/devices/{installation_id}/preferences")
def update_push_preferences(
    installation_id: str,
    payload: PushPreferencesPayload,
    device_secret: Annotated[str | None, Header(alias="X-Tianji-Device-Secret")] = None,
) -> dict[str, Any]:
    try:
        return push_alerts.update_preferences(
            installation_id,
            device_secret or "",
            payload.model_dump(),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/v1/push/alerts")
def push_alert_history(
    installation_id: str = Query(min_length=8, max_length=128),
    limit: int = Query(default=100, ge=1, le=200),
    after_id: int = Query(default=0, ge=0),
    device_secret: Annotated[str | None, Header(alias="X-Tianji-Device-Secret")] = None,
) -> dict[str, Any]:
    try:
        return push_alerts.list_alerts(
            installation_id,
            device_secret or "",
            limit=limit,
            after_id=after_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/v1/push/alerts/{alert_id}/read")
def read_push_alert(
    alert_id: int,
    installation_id: str = Query(min_length=8, max_length=128),
    device_secret: Annotated[str | None, Header(alias="X-Tianji-Device-Secret")] = None,
) -> dict[str, Any]:
    try:
        return push_alerts.mark_alert_read(
            installation_id,
            device_secret or "",
            alert_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/push/alerts/read-all")
def read_all_push_alerts(
    installation_id: str = Query(min_length=8, max_length=128),
    device_secret: Annotated[str | None, Header(alias="X-Tianji-Device-Secret")] = None,
) -> dict[str, Any]:
    try:
        return push_alerts.mark_all_read(installation_id, device_secret or "")
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/v1/admin/run", dependencies=[Depends(require_admin_token)])
def run_now_legacy() -> dict[str, object]:
''',
)

replace_once(
    "server/app/service.py",
    '''from . import ai
''',
    '''from . import ai, push_alerts
''',
)
replace_once(
    "server/app/service.py",
    '''SERVICE_VERSION = "1.3.0"
''',
    '''SERVICE_VERSION = "1.4.0"
''',
)
replace_once(
    "server/app/service.py",
    '''    settled = database.settle_forecasts(lottery_key)
    history = database.list_draws(lottery_key, spec.history_target)
''',
    '''    settled = database.settle_forecasts(lottery_key)
    try:
        push_result = push_alerts.process_prediction_alerts(lottery_key)
        database.delete_state(f"push_error:{lottery_key}")
    except Exception as exc:
        push_result = {
            "created_alert_ids": [],
            "delivery": {"sent": 0, "failed": 0, "skipped": 0},
            "error": str(exc)[:500],
        }
        _state(
            f"push_error:{lottery_key}",
            {"message": str(exc)[:500], "at": int(time.time() * 1000)},
        )
    history = database.list_draws(lottery_key, spec.history_target)
''',
)
replace_once(
    "server/app/service.py",
    '''        "settled": settled,
        "generated": generated,
''',
    '''        "settled": settled,
        "push": push_result,
        "generated": generated,
''',
)

print("v5.9.8 push alert migration applied")
