from pathlib import Path

root = Path(__file__).resolve().parents[1]

db_path = root / "server/app/db.py"
db = db_path.read_text(encoding="utf-8")
db = db.replace(
    'if model.startswith("tianji-native-cloud-v"): ',
    'if model == "tianji-native-cloud-v4": ',
)
db = db.replace(
    'if model.startswith("tianji-native-cloud-v"):',
    'if model == "tianji-native-cloud-v4":',
)
db_path.write_text(db, encoding="utf-8")

ai_path = root / "server/app/ai_ensemble.py"
ai = ai_path.read_text(encoding="utf-8")
ai = ai.replace(
    " 初次结果与最近集合高度重合，已增加隐藏最近7期的独立AI留出评审。",
    " 初次结果与最近集合高度重合，已增加隐藏最近7期的独立AI留出评审，避免直接复制最新六码。",
)
ai_path.write_text(ai, encoding="utf-8")
