from __future__ import annotations

import json
import math
import time
from typing import Any

from . import ai_ensemble, fixed_target_bridge, telegram_events
from .db import database
from .models import LOTTERIES


# v6.1.3 固定 235780 模式正式进入 main 的时间。
# 只用于迁移升级瞬间被旧 Worker 冻结的真实长周期号档案。
_FIXED_MODE_STARTED_AT_MS = 1_786_068_522_000
_FIXED = tuple(fixed_target_bridge.TARGET_NUMBERS)
_OUTSIDE = tuple(number for number in range(1, 11) if number not in _FIXED)
_BASELINE = fixed_target_bridge.RANDOM_BASELINE
_LOG_BASELINE = -(
    _BASELINE * math.log(_BASELINE)
    + (1.0 - _BASELINE) * math.log(1.0 - _BASELINE)
)
_BRIER_BASELINE = _BASELINE * (1.0 - _BASELINE)
_INSTALLED = False
_ORIGINAL_SETTLE = None
_ORIGINAL_MATERIALIZE = None


def _is_target(number: int) -> bool:
    return int(number) in _FIXED


def _beta_rate(hits: float, total: float, strength: float) -> float:
    return (hits + _BASELINE * strength) / (total + strength)


def _stable_probability(values: list[int]) -> float:
    """Conservative membership estimate; deliberately shrinks hard to the 60% baseline."""
    if not values:
        return _BASELINE

    def window_rate(size: int, strength: float) -> float:
        subset = values[-min(size, len(values)):]
        return _beta_rate(sum(_is_target(value) for value in subset), len(subset), strength)

    p24 = window_rate(24, 18.0)
    p60 = window_rate(60, 24.0)
    p120 = window_rate(120, 30.0)
    p240 = window_rate(240, 36.0)

    decay_hits = 0.0
    decay_total = 0.0
    weight = 1.0
    for value in reversed(values[-192:]):
        decay_total += weight
        decay_hits += weight * int(_is_target(value))
        weight *= 0.97
    decay = _beta_rate(decay_hits, decay_total, 16.0)

    # Only a small transition term is retained. It is strongly shrunk because
    # lottery positions are expected to be close to exchangeable over time.
    state = _is_target(values[-1])
    transition_total = 0
    transition_hits = 0
    for index in range(1, len(values)):
        if _is_target(values[index - 1]) == state:
            transition_total += 1
            transition_hits += int(_is_target(values[index]))
    transition = _beta_rate(transition_hits, transition_total, 24.0)

    raw = (
        p24 * 0.16
        + p60 * 0.22
        + p120 * 0.24
        + p240 * 0.22
        + decay * 0.11
        + transition * 0.05
    )
    reliability = min(1.0, len(values) / 240.0)
    probability = _BASELINE + (raw - _BASELINE) * (0.35 + 0.65 * reliability)
    return max(0.48, min(0.72, probability))


def _current_miss_streak(values: list[int]) -> int:
    streak = 0
    for value in reversed(values):
        if _is_target(value):
            break
        streak += 1
    return streak


def _stable_position_profile(
    history: list[Any],
    position: int,
    *,
    max_validation_samples: int = 120,
) -> fixed_target_bridge.FixedTargetPositionProfile:
    verified = fixed_target_bridge._canonical(history, 360)
    if len(verified) < 40:
        raise ValueError("固定六码235780预测至少需要40期有效历史")

    values = [draw.numbers[position] for draw in verified]
    current_probability = _stable_probability(values)
    exact_probabilities = fixed_target_bridge._group_distribution(values, current_probability)

    start = max(40, len(verified) - max(40, max_validation_samples))
    samples = 0
    hits = 0
    losses: list[float] = []
    briers: list[float] = []
    running_miss = 0
    max_miss = 0
    for cursor in range(start, len(verified)):
        prefix = [draw.numbers[position] for draw in verified[:cursor]]
        probability = _stable_probability(prefix)
        actual_hit = _is_target(verified[cursor].numbers[position])
        outcome = 1.0 if actual_hit else 0.0
        samples += 1
        hits += int(actual_hit)
        losses.append(-math.log(max(1e-12, probability if actual_hit else 1.0 - probability)))
        briers.append((probability - outcome) ** 2)
        if actual_hit:
            running_miss = 0
        else:
            running_miss += 1
            max_miss = max(max_miss, running_miss)

    hit_rate = _beta_rate(hits, samples, 20.0) if samples else _BASELINE
    average_log_loss = sum(losses) / len(losses) if losses else _LOG_BASELINE
    average_brier = sum(briers) / len(briers) if briers else _BRIER_BASELINE
    reliability = min(1.0, samples / 100.0)

    hit_edge = max(-0.12, min(0.12, hit_rate - _BASELINE))
    loss_edge = max(-0.12, min(0.12, (_LOG_BASELINE - average_log_loss) / _LOG_BASELINE))
    brier_edge = max(-0.12, min(0.12, (_BRIER_BASELINE - average_brier) / _BRIER_BASELINE))
    current_edge = current_probability - _BASELINE

    # No gambler's-fallacy bonus for current miss streak. A position only rises
    # when current estimate and walk-forward evidence point in the same direction.
    score = (
        _BASELINE
        + current_edge * 0.46
        + reliability * hit_edge * 0.32
        + reliability * loss_edge * 0.14
        + reliability * brier_edge * 0.08
    )
    return fixed_target_bridge.FixedTargetPositionProfile(
        position=position,
        target_probability=current_probability,
        exact_probabilities=exact_probabilities,
        validation_samples=samples,
        validation_hits=hits,
        validation_hit_rate=hit_rate,
        average_log_loss=average_log_loss,
        average_brier=average_brier,
        max_miss_streak=max_miss,
        current_miss_streak=_current_miss_streak(values),
        score=score,
    )


def _normalize_scores(values: list[float]) -> list[float]:
    safe = [max(1e-9, float(value)) for value in values]
    total = sum(safe) or 1.0
    return [value / total for value in safe]


def _analyze_stable_fixed_target(
    history: list[Any],
    target_period: str,
    config: Any,
    *,
    recent_positions: list[int] | None = None,
    strategy_weights: dict[str, float] | None = None,
) -> Any:
    del recent_positions, strategy_weights
    started = time.monotonic()
    profiles = tuple(_stable_position_profile(history, position) for position in range(10))
    reviews = ai_ensemble._run_prefix_cached(
        fixed_target_bridge.TARGET_REVIEWERS,
        lambda reviewer: fixed_target_bridge._target_position_review(
            config,
            history=history,
            profiles=profiles,
            target_period=target_period,
            reviewer=reviewer,
        ),
    )
    math_scores = _normalize_scores([profile.score for profile in profiles])
    ai_scores = _normalize_scores([
        sum(review.scores[position] for review in reviews) / len(reviews)
        for position in range(10)
    ])
    combined = [math_scores[index] * 0.90 + ai_scores[index] * 0.10 for index in range(10)]
    ranking = sorted(range(10), key=lambda index: combined[index], reverse=True)
    selected = profiles[ranking[0]]
    runner_up = profiles[ranking[1]]

    ai_best = max(range(10), key=lambda index: ai_scores[index])
    ai_support = sum(
        max(range(10), key=lambda index: review.scores[index]) == selected.position
        for review in reviews
    )
    analyses = "；".join(review.analysis for review in reviews if review.analysis)[:240]
    analysis = (
        f"固定目标{fixed_target_bridge.TARGET_LABEL}，只预测十个名次谁更可能进入2/3/5/7/8/10。"
        "新版不再追12期短波动，也不给连续未中任何反弹加分；"
        "使用24/60/120/240期分层收缩、192期衰减和最多120期严格前向验证。"
        f"数学前向证据占90%，AI仅占10%辅助复核。最终第{selected.position + 1}名最高，"
        f"估计进入固定池概率约{selected.target_probability * 100:.1f}%，"
        f"前向命中约{selected.validation_hit_rate * 100:.1f}%/{selected.validation_samples}期，"
        f"二分类LogLoss {selected.average_log_loss:.3f}，Brier {selected.average_brier:.3f}；"
        f"第二候选约{runner_up.target_probability * 100:.1f}%。AI平均首选第{ai_best + 1}名，"
        f"{ai_support}/{len(reviews)}路支持最终名次。"
        + (f" AI摘要：{analyses}" if analyses else "")
    )[:1200]
    risk_note = (
        "每期开奖十个位置中恰有六个会落入固定235780，因此任意固定位置的理论基准就是60%。"
        "若开奖近似随机，任何历史模型都可能长期回到60%附近；系统只能用严格前向成绩压制过拟合，不能保证提高命中。"
    )[:800]

    probabilities = selected.exact_probabilities
    top7 = fixed_target_bridge._top7(probabilities)
    usage = ai_ensemble._merge_usage(reviews)
    prompt_total = usage.get("prompt_cache_hit_tokens", 0) + usage.get("prompt_cache_miss_tokens", 0)
    cache_hit_rate = usage.get("prompt_cache_hit_tokens", 0) / prompt_total if prompt_total else 0.0
    strategy_name = f"ai_fixed_{fixed_target_bridge.TARGET_LABEL}_stable_position_{selected.position + 1}"
    return ai_ensemble.AiEnsembleResult(
        position=selected.position,
        probabilities=probabilities,
        top6=list(_FIXED),
        top7=top7,
        analysis=analysis,
        risk_note=risk_note,
        latency_ms=int((time.monotonic() - started) * 1000),
        position_reviewers=len(reviews),
        number_reviewers=0,
        collapse_reviewed=False,
        recent_copy_reviewed=False,
        request_count=usage.get("request_count", 0),
        prompt_tokens=usage.get("prompt_tokens", 0),
        prompt_cache_hit_tokens=usage.get("prompt_cache_hit_tokens", 0),
        prompt_cache_miss_tokens=usage.get("prompt_cache_miss_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        reasoning_tokens=usage.get("reasoning_tokens", 0),
        cache_hit_rate=cache_hit_rate,
        strategy_probabilities={strategy_name: probabilities},
        strategy_weights={strategy_name: 1.0},
    )


def _is_real_period(value: Any) -> bool:
    text = str(value or "").strip()
    return len(text) >= 6 and text.isdigit()


def _normalize_fixed_mode_rows(lottery: str | None = None) -> int:
    where_lottery = " AND lottery=?" if lottery else ""
    params: tuple[Any, ...] = (_FIXED_MODE_STARTED_AT_MS, lottery) if lottery else (_FIXED_MODE_STARTED_AT_MS,)
    fixed_json = json.dumps(list(_FIXED), separators=(",", ":"))
    changed = 0
    with database.connection() as db:
        rows = db.execute(
            f"""
            SELECT * FROM forecasts
            WHERE source='ai' AND created_at>=?{where_lottery}
            ORDER BY id ASC
            """,
            params,
        ).fetchall()
        for row in rows:
            if not _is_real_period(row["target_period"]):
                continue
            try:
                probabilities = [float(value) for value in json.loads(str(row["probabilities_json"]))]
            except (TypeError, ValueError, json.JSONDecodeError):
                probabilities = [0.1] * 10
            hedge = max(_OUTSIDE, key=lambda number: probabilities[number - 1] if len(probabilities) == 10 else 0.0)
            top7 = [*_FIXED, hedge]
            top7_json = json.dumps(top7, separators=(",", ":"))
            actual = row["actual_number"]
            if actual is None:
                db.execute(
                    "UPDATE forecasts SET top6_json=?,top7_json=? WHERE id=?",
                    (fixed_json, top7_json, int(row["id"])),
                )
            else:
                actual_number = int(actual)
                db.execute(
                    """
                    UPDATE forecasts SET top6_json=?,top7_json=?,top6_hit=?,top7_hit=?
                    WHERE id=?
                    """,
                    (
                        fixed_json,
                        top7_json,
                        int(actual_number in _FIXED),
                        int(actual_number in top7),
                        int(row["id"]),
                    ),
                )
                db.execute(
                    "UPDATE forecast_strategy_predictions SET top6_hit=? WHERE forecast_id=? AND settled_at IS NOT NULL",
                    (int(actual_number in _FIXED), int(row["id"])),
                )
            if str(row["top6_json"]) != fixed_json:
                changed += 1

        # Refresh unsent Telegram event bodies after the DB normalization so an
        # old queued event can never leak a legacy dynamic Top6 again.
        refreshed = db.execute(
            f"""
            SELECT * FROM forecasts
            WHERE source='ai' AND created_at>=?{where_lottery}
            ORDER BY id ASC
            """,
            params,
        ).fetchall()
        for row in refreshed:
            if not _is_real_period(row["target_period"]):
                continue
            prediction_key = f"prediction:{int(row['id'])}"
            sent_prediction = db.execute(
                "SELECT 1 FROM telegram_event_deliveries WHERE event_key=? AND status='sent' LIMIT 1",
                (prediction_key,),
            ).fetchone()
            if sent_prediction is None:
                event = db.execute("SELECT 1 FROM telegram_events WHERE event_key=?", (prediction_key,)).fetchone()
                if event is not None:
                    streak = telegram_events._consecutive_misses_before(db, row)
                    db.execute(
                        "UPDATE telegram_events SET message_html=? WHERE event_key=?",
                        (telegram_events.format_prediction_message(row, streak), prediction_key),
                    )

            win_key = f"win:{int(row['id'])}"
            sent_win = db.execute(
                "SELECT 1 FROM telegram_event_deliveries WHERE event_key=? AND status='sent' LIMIT 1",
                (win_key,),
            ).fetchone()
            if sent_win is None:
                if row["actual_number"] is None or int(row["top6_hit"] or 0) != 1:
                    db.execute("DELETE FROM telegram_events WHERE event_key=?", (win_key,))
                else:
                    event = db.execute("SELECT 1 FROM telegram_events WHERE event_key=?", (win_key,)).fetchone()
                    if event is not None:
                        db.execute(
                            "UPDATE telegram_events SET message_html=? WHERE event_key=?",
                            (telegram_events.format_win_message(row), win_key),
                        )
    return changed


def install() -> None:
    global _INSTALLED, _ORIGINAL_SETTLE, _ORIGINAL_MATERIALIZE
    if _INSTALLED:
        return

    # Replace the fixed-target estimator with a more conservative walk-forward model.
    fixed_target_bridge._fixed_target_probability = _stable_probability
    fixed_target_bridge._build_position_profile = _stable_position_profile
    fixed_target_bridge._analyze_fixed_target = _analyze_stable_fixed_target
    ai_ensemble.analyze_ensemble = _analyze_stable_fixed_target

    _ORIGINAL_SETTLE = database.settle_forecasts
    _ORIGINAL_MATERIALIZE = telegram_events.materialize_events

    def settle_guard(lottery: str) -> int:
        _normalize_fixed_mode_rows(lottery)
        result = _ORIGINAL_SETTLE(lottery)
        _normalize_fixed_mode_rows(lottery)
        return result

    def materialize_guard(lottery_filter: str | None = None) -> int:
        _normalize_fixed_mode_rows(lottery_filter)
        return _ORIGINAL_MATERIALIZE(lottery_filter)

    database.settle_forecasts = settle_guard  # type: ignore[method-assign]
    telegram_events.materialize_events = materialize_guard

    # Correct already-settled v6.1.3 rows (including a false legacy 'recovery hit')
    # as soon as the updated service starts.
    for lottery in LOTTERIES:
        _normalize_fixed_mode_rows(lottery)

    _INSTALLED = True
