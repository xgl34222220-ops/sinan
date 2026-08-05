from pathlib import Path

path = Path("server/app/push_alerts.py")
text = path.read_text(encoding="utf-8")
if "import hmac\n" not in text:
    text = text.replace("import hashlib\n", "import hashlib\nimport hmac\n", 1)
text = text.replace("hashlib.compare_digest", "hmac.compare_digest")
if "hashlib.compare_digest" in text:
    raise SystemExit("compare_digest replacement incomplete")
path.write_text(text, encoding="utf-8")
print("server constant-time digest comparison fixed")
