#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
ai_path = root / "server/app/ai.py"
service_path = root / "server/app/service.py"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, got {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


ai_text = ai_path.read_text(encoding="utf-8")
marker = "def analyze(\n"
index = ai_text.find(marker)
if index < 0:
    raise SystemExit("server/app/ai.py: analyze function not found")
wrapper = '''def analyze(
    history: list[DrawModel],
    target_period: str,
    config: RuntimeAiConfig | None = None,
    *,
    recent_positions: list[int] | None = None,
) -> AiPrediction:
    """Generate an AI-only forward prediction through anonymous multi-review consensus."""
    from .ai_ensemble import analyze_ensemble

    active = config or load_ai_config()
    result = analyze_ensemble(
        history,
        target_period,
        active,
        recent_positions=recent_positions,
    )
    return AiPrediction(
        position=result.position,
        probabilities=result.probabilities,
        top6=result.top6,
        top7=result.top7,
        analysis=result.analysis,
        risk_note=result.risk_note,
        model=active.model,
        latency_ms=result.latency_ms,
    )
'''
ai_path.write_text(ai_text[:index] + wrapper, encoding="utf-8")

replace_once(
    service_path,
    "        result = ai.analyze(history, target_period, ai_config)\n",
    '''        recent_ai_positions = [
            forecast.position
            for forecast in database.list_forecasts(spec.key, 20)
            if forecast.source == "ai"
        ][:12]
        result = ai.analyze(
            history,
            target_period,
            ai_config,
            recent_positions=recent_ai_positions,
        )
''',
)
replace_once(
    service_path,
    'SERVICE_VERSION = "1.5.0"\n',
    'SERVICE_VERSION = "1.6.0"\n',
)
print("patched server AI ensemble")
