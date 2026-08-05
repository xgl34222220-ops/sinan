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

test_path = Path("server/tests/test_admin_insights.py")
test_text = test_path.read_text(encoding="utf-8")
old_expectation = 'self.assertEqual("云端 AI", ai_only["items"][0]["source_name"])'
new_expectation = 'self.assertEqual("天机云端 AI", ai_only["items"][0]["source_name"])'
if old_expectation not in test_text:
    raise SystemExit("legacy cloud AI expectation not found")
test_path.write_text(
    test_text.replace(old_expectation, new_expectation, 1),
    encoding="utf-8",
)

print("Fixed nullable cached state handling and cloud AI naming expectation.")
