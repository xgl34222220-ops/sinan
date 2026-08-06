from __future__ import annotations

from pathlib import Path

refined = [
    Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedForecastStrategy.kt"),
    Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/RefinedPushAlertCenter.kt"),
    Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/ExperienceOverlays.kt"),
]
text = "\n".join(path.read_text(encoding="utf-8") for path in refined)
forbidden = {
    "1 \u8def AI \u5df2\u5b8c\u6210": "internal route count must not be user-facing",
    "\u8fd0\u884c $running \u00b7 \u5b8c\u6210 $completed": "connection state must not masquerade as prediction completion",
    "fontSize = 8.sp": "key refined screens must not use 8sp",
    "fontSize = 9.sp": "key refined screens must not use 9sp",
}
failures = [message for token, message in forbidden.items() if token in text]
if failures:
    raise SystemExit("; ".join(failures))
app = Path("app/src/main/java/com/tianji/probabilitylab/nativev4/ui/TianjiApp.kt").read_text(encoding="utf-8")
if "HomePredictionFocusStrip(" in app:
    raise SystemExit("home must not duplicate the prediction summary strip")
notification = Path("app/src/main/java/com/tianji/probabilitylab/nativev4/push/PushNotificationManager.kt").read_text(encoding="utf-8")
if "EXTRA_OPEN_PREDICTION" not in notification:
    raise SystemExit("prediction notifications must deep-link to home")
print("ui contract ok")
