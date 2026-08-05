#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "app/src/main/java/com/tianji/probabilitylab/nativev4/ai/AiChatController.kt"
text = path.read_text(encoding="utf-8")

bad_context = """                learningContext = learningContext,\n                wantsPrediction = wantsPrediction,\n                intent = intent,\n            )"""
good_context = """                learningContext = learningContext,\n                wantsPrediction = wantsPrediction,\n            )"""
if text.count(bad_context) != 1:
    raise RuntimeError(f"context cleanup expected 1 match, got {text.count(bad_context)}")
text = text.replace(bad_context, good_context, 1)

bad_duplicate = """                    publisher = publisher,\n                    intent = intent,\n                    intent = intent,\n                )"""
good_duplicate = """                    publisher = publisher,\n                    intent = intent,\n                )"""
if text.count(bad_duplicate) != 2:
    raise RuntimeError(f"duplicate cleanup expected 2 matches, got {text.count(bad_duplicate)}")
text = text.replace(bad_duplicate, good_duplicate)

path.write_text(text, encoding="utf-8")
print("free chat patch cleanup applied")
