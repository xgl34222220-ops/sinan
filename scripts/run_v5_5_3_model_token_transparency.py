#!/usr/bin/env python3
from pathlib import Path
import runpy

patch = Path(__file__).with_name("apply_v5_5_3_model_token_transparency.py")
text = patch.read_text(encoding="utf-8")
replacements = {
    r'append("\n名次依据：$positionEvidence")': r'append("\\n名次依据：$positionEvidence")',
    r'append("\n候选依据：$candidateEvidence")': r'append("\\n候选依据：$candidateEvidence")',
}
for old, new in replacements.items():
    if text.count(old) != 1:
        raise RuntimeError(f"expected exactly one patch escape match: {old}")
    text = text.replace(old, new, 1)
patch.write_text(text, encoding="utf-8")
runpy.run_path(str(patch), run_name="__main__")
