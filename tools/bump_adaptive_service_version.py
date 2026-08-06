from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "server/app/service.py"
text = path.read_text(encoding="utf-8")
old = 'SERVICE_VERSION = "1.7.0"'
new = 'SERVICE_VERSION = "1.7.1"'
if text.count(old) != 1:
    raise SystemExit(f"service version match count={text.count(old)}")
path.write_text(text.replace(old, new), encoding="utf-8")

check = root / "server/tests/test_adaptive_deploy_version.py"
check.write_text('''from app.service import SERVICE_VERSION\n\n\ndef test_adaptive_atomic_release_version():\n    assert SERVICE_VERSION == "1.7.1"\n''', encoding="utf-8")
print("service version bumped to 1.7.1")
