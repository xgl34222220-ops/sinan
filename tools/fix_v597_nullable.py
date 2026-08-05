from pathlib import Path

path = Path("app/src/main/java/com/tianji/probabilitylab/nativev4/AppController.kt")
text = path.read_text(encoding="utf-8")
old = '''                        val preservedAi = if (
                            previous?.report?.targetPeriod == loaded.report?.targetPeriod
                        ) {
                            previous.aiForecasts
                        } else {
                            emptyList()
                        }
'''
new = '''                        val preservedAi = if (
                            previous != null &&
                            previous.report?.targetPeriod == loaded.report?.targetPeriod
                        ) {
                            previous.aiForecasts
                        } else {
                            emptyList()
                        }
'''
if old not in text:
    raise SystemExit("nullable cache block not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Fixed nullable cached state handling.")
