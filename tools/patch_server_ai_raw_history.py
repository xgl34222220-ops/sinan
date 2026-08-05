#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "server/app/ai_ensemble.py"


def replace_once(old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected one match, got {count}: {old[:140]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

replace_once(
    '''def _call_json(
    config: RuntimeAiConfig,
    *,
    system_prompt: str,
    user_payload: dict[str, Any],
    max_tokens: int,
) -> dict[str, Any]:
''',
    '''def _call_json(
    config: RuntimeAiConfig,
    *,
    system_prompt: str,
    user_payload: dict[str, Any],
    max_tokens: int,
    timeout_seconds: int,
) -> dict[str, Any]:
''',
)
replace_once(
    '''            with httpx.Client(
                timeout=httpx.Timeout(config.timeout_seconds, connect=15.0),
                follow_redirects=True,
            ) as client:
''',
    '''            attempt_timeout = timeout_seconds if attempt == 0 else min(30, timeout_seconds)
            with httpx.Client(
                timeout=httpx.Timeout(attempt_timeout, connect=min(12.0, attempt_timeout)),
                follow_redirects=True,
            ) as client:
''',
)
replace_once(
    '''        value = dict(items[index])
        value.pop("position", None)
        payload.append({"candidate_id": label, "evidence": value})
''',
    '''        value = dict(items[index])
        value.pop("position", None)
        value.pop("number", None)
        payload.append({"candidate_id": label, "evidence": value})
''',
)
replace_once(
    '''    return payload, mapping


def _parse_label_scores''',
    '''    return payload, mapping


def _anonymized_position_history(
    history: list[DrawModel],
    mapping: dict[str, int],
) -> list[dict[str, Any]]:
    return [
        {
            "period": draw.period,
            "values_by_candidate": {
                label: draw.numbers[position]
                for label, position in mapping.items()
            },
        }
        for draw in _canonical_history(history)
    ]


def _anonymized_number_series(
    history: list[DrawModel],
    position: int,
    mapping: dict[str, int],
) -> list[dict[str, Any]]:
    label_by_number = {actual_index + 1: label for label, actual_index in mapping.items()}
    return [
        {
            "period": draw.period,
            "candidate_id": label_by_number[draw.numbers[position]],
        }
        for draw in _canonical_history(history)
    ]


def _parse_label_scores''',
)
replace_once(
    '''    *,
    evidence: list[dict[str, Any]],
    target_period: str,
''',
    '''    *,
    history: list[DrawModel],
    evidence: list[dict[str, Any]],
    target_period: str,
''',
)
replace_once(
    '''            "reviewer": reviewer + 1,
            "candidates": candidates,
        },
        max_tokens=1200,
    )
''',
    '''            "reviewer": reviewer + 1,
            "history_order": "oldest_to_newest",
            "anonymous_raw_draws": _anonymized_position_history(history, mapping),
            "candidates": candidates,
        },
        max_tokens=1200,
        timeout_seconds=55,
    )
''',
)
replace_once(
    '''            "selected_position": position + 1,
            "reviewer": reviewer + 1,
            "candidates": candidates,
        },
        max_tokens=1000,
    )
''',
    '''            "selected_position": position + 1,
            "reviewer": reviewer + 1,
            "history_order": "oldest_to_newest",
            "anonymous_raw_position_series": _anonymized_number_series(
                history,
                position,
                mapping,
            ),
            "candidates": candidates,
        },
        max_tokens=1000,
        timeout_seconds=45,
    )
''',
)
replace_once(
    '''        lambda reviewer: _position_review(
            config,
            evidence=evidence,
''',
    '''        lambda reviewer: _position_review(
            config,
            history=verified,
            evidence=evidence,
''',
)
replace_once(
    '''            lambda reviewer: _position_review(
                config,
                evidence=evidence,
''',
    '''            lambda reviewer: _position_review(
                config,
                history=verified,
                evidence=evidence,
''',
)
replace_once(
    '''        "不得猜测字母对应哪个名次，也不得偏向列表第一项。只能依据每个候选的真实API统计证据，"
''',
    '''        "不得猜测字母对应哪个名次，也不得偏向列表第一项。你会同时看到匿名后的原始开奖序列和程序逐期核验的统计证据，"
''',
)
replace_once(
    '''        "只能依据当前选中名次的真实开奖API证据，对全部10个匿名候选给出0以上相对评分。"
''',
    '''        "你会同时看到该名次匿名后的原始开奖序列与程序逐期核验的统计证据，对全部10个匿名号码候选给出0以上相对评分。"
''',
)
print("patched anonymous raw history and bounded AI deadlines")
