from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

quality = r'''from __future__ import annotations

from dataclasses import dataclass
import math

from .models import DrawModel


@dataclass(frozen=True)
class PositionQuality:
    position: int
    probabilities: list[float]
    top6: list[int]
    top7: list[int]
    boundary_margin: float
    walk_forward_samples: int
    walk_forward_hits: int
    walk_forward_hit_rate: float
    average_log_loss: float
    validation_score: float


@dataclass(frozen=True)
class RecentCopyDiagnostics:
    triggered: bool
    exact_latest_six: bool
    recent_six_unique: int
    top6_recent_six_overlap: int
    recent_seven_unique: int
    top7_contains_recent_seven: bool


def _normalize(values: list[float]) -> list[float]:
    safe = [value if math.isfinite(value) and value > 0 else 1e-12 for value in values]
    total = sum(safe) or 1.0
    return [value / total for value in safe]


def _canonical(history: list[DrawModel], limit: int = 240) -> list[DrawModel]:
    return [
        draw
        for draw in history
        if len(draw.numbers) == 10 and len(set(draw.numbers)) == 10
    ][-limit:]


def _counts(values: list[int], window: int) -> list[float]:
    result = [0.0] * 10
    for number in values[-window:]:
        if 1 <= number <= 10:
            result[number - 1] += 1.0
    return result


def statistical_probabilities(
    history: list[DrawModel],
    position: int,
    *,
    mask_recent: int = 0,
) -> list[float]:
    verified = _canonical(history)
    if mask_recent > 0:
        if len(verified) - mask_recent < 30:
            raise ValueError("隐藏近期样本后不足30期")
        verified = verified[:-mask_recent]
    if len(verified) < 30:
        raise ValueError("至少需要30期有效历史")
    if position not in range(10):
        raise ValueError("名次超出范围")

    values = [draw.numbers[position] for draw in verified]
    count18 = _counts(values, 18)
    count45 = _counts(values, 45)
    count120 = _counts(values, 120)
    size18 = float(min(18, len(values)))
    size45 = float(min(45, len(values)))
    size120 = float(min(120, len(values)))

    long_prior = _normalize([(value + 1.0) / (size120 + 10.0) for value in count120])

    recency_raw = [0.0] * 10
    for index, number in enumerate(values):
        age = len(values) - 1 - index
        recency_raw[number - 1] += math.exp(-age / 24.0)
    recency = _normalize(recency_raw)

    omission_raw: list[float] = []
    for number in range(1, 11):
        latest = -1
        for cursor in range(len(values) - 1, -1, -1):
            if values[cursor] == number:
                latest = cursor
                break
        gap = len(values) if latest < 0 else len(values) - 1 - latest
        omission_raw.append(0.72 + math.exp(-abs(gap - 9.0) / 9.0))
    omission = _normalize(omission_raw)

    current = values[-1]
    successors = [0.0] * 10
    transition_samples = 0
    for index in range(1, len(values)):
        if values[index - 1] == current:
            successors[values[index] - 1] += 1.0
            transition_samples += 1
    transition_shrink = max(7.0, 22.0 - transition_samples)
    transition = _normalize(
        [successors[index] + long_prior[index] * transition_shrink for index in range(10)]
    )

    trend = _normalize(
        [
            math.exp(
                (count18[index] / size18 - count45[index] / size45) * 4.2
            )
            for index in range(10)
        ]
    )
    stability = _normalize(
        [
            1.0
            / (
                0.08
                + abs(count18[index] / size18 - count45[index] / size45)
                + 0.45 * abs(count45[index] / size45 - count120[index] / size120)
            )
            for index in range(10)
        ]
    )

    # Recency is deliberately capped. It may contribute evidence, but cannot by itself
    # turn the most recent distinct values into the entire Top 6.
    weights = (0.25, 0.15, 0.12, 0.23, 0.16, 0.09)
    factors = (long_prior, recency, omission, transition, trend, stability)
    return _normalize(
        [
            sum(factors[factor][number] * weights[factor] for factor in range(6))
            for number in range(10)
        ]
    )


def blend_probabilities(
    primary: list[float],
    secondary: list[float],
    *,
    secondary_weight: float,
) -> list[float]:
    weight = max(0.0, min(1.0, secondary_weight))
    return _normalize(
        [
            primary[index] * (1.0 - weight) + secondary[index] * weight
            for index in range(len(primary))
        ]
    )


def position_quality_profile(
    history: list[DrawModel],
    position: int,
    *,
    max_samples: int = 48,
) -> PositionQuality:
    verified = _canonical(history)
    if len(verified) < 40:
        probabilities = statistical_probabilities(verified, position)
        ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
        return PositionQuality(
            position=position,
            probabilities=probabilities,
            top6=[index + 1 for index in ranked[:6]],
            top7=[index + 1 for index in ranked[:7]],
            boundary_margin=probabilities[ranked[5]] - probabilities[ranked[6]],
            walk_forward_samples=0,
            walk_forward_hits=0,
            walk_forward_hit_rate=0.6,
            average_log_loss=math.log(10.0),
            validation_score=1.0,
        )

    start = max(30, len(verified) - max(12, max_samples))
    hits = 0
    losses: list[float] = []
    samples = 0
    for cursor in range(start, len(verified)):
        prefix = verified[:cursor]
        if len(prefix) < 30:
            continue
        probabilities = statistical_probabilities(prefix, position)
        ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
        actual = verified[cursor].numbers[position]
        if actual in {index + 1 for index in ranked[:6]}:
            hits += 1
        losses.append(-math.log(max(1e-12, probabilities[actual - 1])))
        samples += 1

    current = statistical_probabilities(verified, position)
    ranked = sorted(range(10), key=current.__getitem__, reverse=True)
    boundary = current[ranked[5]] - current[ranked[6]]
    posterior_hit_rate = (hits + 6.0) / (samples + 10.0)
    average_log_loss = sum(losses) / len(losses) if losses else math.log(10.0)
    baseline_loss = math.log(10.0)
    loss_edge = max(-0.35, min(0.35, (baseline_loss - average_log_loss) / baseline_loss))
    validation_score = max(
        0.05,
        1.0
        + (posterior_hit_rate - 0.6) * 5.0
        + loss_edge * 0.9
        + boundary * 4.0,
    )
    return PositionQuality(
        position=position,
        probabilities=current,
        top6=[index + 1 for index in ranked[:6]],
        top7=[index + 1 for index in ranked[:7]],
        boundary_margin=boundary,
        walk_forward_samples=samples,
        walk_forward_hits=hits,
        walk_forward_hit_rate=posterior_hit_rate,
        average_log_loss=average_log_loss,
        validation_score=validation_score,
    )


def recent_copy_diagnostics(
    ranked: list[int],
    history: list[DrawModel],
    position: int,
) -> RecentCopyDiagnostics:
    verified = _canonical(history)
    top6 = {index + 1 for index in ranked[:6]}
    top7 = {index + 1 for index in ranked[:7]}
    recent_six = {draw.numbers[position] for draw in verified[-6:]}
    recent_seven = {draw.numbers[position] for draw in verified[-7:]}
    overlap = len(top6 & recent_six)
    exact = len(recent_six) == 6 and top6 == recent_six
    contains_seven = len(recent_seven) >= 6 and recent_seven.issubset(top7)
    triggered = exact or (len(recent_six) >= 5 and overlap >= 5) or contains_seven
    return RecentCopyDiagnostics(
        triggered=triggered,
        exact_latest_six=exact,
        recent_six_unique=len(recent_six),
        top6_recent_six_overlap=overlap,
        recent_seven_unique=len(recent_seven),
        top7_contains_recent_seven=contains_seven,
    )


def regularize_recent_copy(
    probabilities: list[float],
    history: list[DrawModel],
    position: int,
    *,
    mask_recent: int = 10,
) -> tuple[list[float], bool]:
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
    diagnostics = recent_copy_diagnostics(ranked, history, position)
    if not diagnostics.triggered:
        return _normalize(probabilities), False

    verified = _canonical(history)
    safe_mask = min(mask_recent, max(0, len(verified) - 30))
    adjusted = list(probabilities)
    if safe_mask > 0:
        masked = statistical_probabilities(verified, position, mask_recent=safe_mask)
        adjusted = blend_probabilities(adjusted, masked, secondary_weight=0.68)

    recent_six = {draw.numbers[position] for draw in verified[-6:]}
    adjusted = _normalize(
        [
            value * (0.78 if index + 1 in recent_six else 1.22)
            for index, value in enumerate(adjusted)
        ]
    )

    # Final deterministic guard: an exact clone of six latest distinct values is not
    # accepted when the sixth/seventh boundary is weak. Replace only the weakest edge.
    reranked = sorted(range(10), key=adjusted.__getitem__, reverse=True)
    reranked_top6 = {index + 1 for index in reranked[:6]}
    if len(recent_six) == 6 and reranked_top6 == recent_six:
        inside = min(reranked[:6], key=adjusted.__getitem__)
        outside = max(reranked[6:], key=adjusted.__getitem__)
        boundary = adjusted[inside] - adjusted[outside]
        if boundary < 0.025:
            pivot = (adjusted[inside] + adjusted[outside]) / 2.0
            adjusted[inside] = max(1e-12, pivot * 0.995)
            adjusted[outside] = pivot * 1.005
            adjusted = _normalize(adjusted)
    return adjusted, True
'''

predictor = r'''from __future__ import annotations

from dataclasses import dataclass

from .forecast_quality import position_quality_profile, regularize_recent_copy
from .models import DrawModel


@dataclass(frozen=True)
class PositionResult:
    position: int
    probabilities: list[float]
    top6: list[int]
    top7: list[int]
    boundary_margin: float
    walk_forward_samples: int
    walk_forward_hit_rate: float
    validation_score: float
    copy_guard_applied: bool


@dataclass(frozen=True)
class NativePrediction:
    selected: PositionResult
    positions: list[PositionResult]
    analysis: str
    risk_note: str


def _position_result(history: list[DrawModel], position: int) -> PositionResult:
    profile = position_quality_profile(history, position)
    probabilities, guarded = regularize_recent_copy(
        profile.probabilities,
        history,
        position,
    )
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
    return PositionResult(
        position=position,
        probabilities=probabilities,
        top6=[index + 1 for index in ranked[:6]],
        top7=[index + 1 for index in ranked[:7]],
        boundary_margin=probabilities[ranked[5]] - probabilities[ranked[6]],
        walk_forward_samples=profile.walk_forward_samples,
        walk_forward_hit_rate=profile.walk_forward_hit_rate,
        validation_score=profile.validation_score,
        copy_guard_applied=guarded,
    )


def predict(history_input: list[DrawModel]) -> NativePrediction:
    history = [
        draw
        for draw in history_input
        if len(draw.numbers) == 10 and len(set(draw.numbers)) == 10
    ][-3000:]
    if len(history) < 30:
        raise ValueError("至少需要 30 期有效历史才能生成预测")

    positions = [_position_result(history, position) for position in range(10)]
    selected = max(
        positions,
        key=lambda item: (
            item.validation_score,
            item.walk_forward_hit_rate,
            item.boundary_margin,
        ),
    )
    hit_percent = selected.walk_forward_hit_rate * 100.0
    margin_percent = selected.boundary_margin * 100.0
    analysis = (
        f"本机云端引擎对十个名次分别执行滚动前向验证后选择第 {selected.position + 1} 名；"
        f"验证样本 {selected.walk_forward_samples} 期，收缩命中率约 {hit_percent:.1f}%，"
        f"当前六码边界差约 {margin_percent:.2f} 个百分点。"
        + (
            " 检测到结果过度贴近最近六码，已使用隐藏近期窗口和边界正则重新排序。"
            if selected.copy_guard_applied
            else ""
        )
    )
    risk_note = (
        "随机开奖没有可保证的可预测规律；滚动验证只能约束算法不凭单期结果拍脑袋。"
        "候选结果不得理解为必中或真实中奖概率。"
    )
    return NativePrediction(selected, positions, analysis, risk_note)
'''

(ROOT / "server/app/forecast_quality.py").write_text(quality, encoding="utf-8")
(ROOT / "server/app/predictor.py").write_text(predictor, encoding="utf-8")

path = ROOT / "server/app/ai_ensemble.py"
text = path.read_text(encoding="utf-8")
text = text.replace(
    "from .models import DrawModel, compact_json\n",
    "from .forecast_quality import (\n"
    "    blend_probabilities as blend_validated_probabilities,\n"
    "    position_quality_profile,\n"
    "    recent_copy_diagnostics,\n"
    "    regularize_recent_copy,\n"
    "    statistical_probabilities,\n"
    ")\n"
    "from .models import DrawModel, compact_json\n",
)
text = text.replace(
    "def needs_collapse_review(recent_positions: list[int], selected_position: int) -> bool:\n"
    "    streak = 0\n"
    "    for position in recent_positions:\n"
    "        if position != selected_position:\n"
    "            break\n"
    "        streak += 1\n"
    "    return streak >= 6\n",
    "def needs_collapse_review(recent_positions: list[int], selected_position: int) -> bool:\n"
    "    streak = 0\n"
    "    for position in recent_positions:\n"
    "        if position != selected_position:\n"
    "            break\n"
    "        streak += 1\n"
    "    return streak >= 3\n",
)
old_match = '''def _matches_recent_window(
    ranked: list[int],
    history: list[DrawModel],
    position: int,
    window: int = _RECENT_COPY_WINDOW,
) -> bool:
    recent = _recent_window_set(history, position, window)
    predicted = {index + 1 for index in ranked[:window]}
    return len(recent) >= window - 1 and recent.issubset(predicted)
'''
new_match = '''def _matches_recent_window(
    ranked: list[int],
    history: list[DrawModel],
    position: int,
    window: int = _RECENT_COPY_WINDOW,
) -> bool:
    del window
    return recent_copy_diagnostics(ranked, history, position).triggered
'''
if old_match not in text:
    raise SystemExit("recent-copy matcher block not found")
text = text.replace(old_match, new_match)

old_position = '''    position_scores = _aggregate(position_results)
    selected_position = max(range(10), key=position_scores.__getitem__)

    collapse_reviewed = needs_collapse_review(
        recent_positions or [],
        selected_position,
    )
'''
new_position = '''    ai_position_scores = _aggregate(position_results)
    quality_profiles = [
        position_quality_profile(verified, position)
        for position in range(10)
    ]
    validation_scores = _normalize(
        [max(0.05, profile.validation_score) for profile in quality_profiles]
    )
    position_scores = _normalize(
        [
            ai_position_scores[index] * 0.45 + validation_scores[index] * 0.55
            for index in range(10)
        ]
    )
    selected_position = max(range(10), key=position_scores.__getitem__)
    weak_repeat_guarded = False
    recent = recent_positions or []
    ranked_positions = sorted(range(10), key=position_scores.__getitem__, reverse=True)
    if recent and needs_collapse_review(recent, selected_position):
        margin = position_scores[ranked_positions[0]] - position_scores[ranked_positions[1]]
        if margin < 0.012:
            for candidate in ranked_positions[1:]:
                if validation_scores[candidate] >= validation_scores[selected_position] * 0.97:
                    selected_position = candidate
                    weak_repeat_guarded = True
                    break

    collapse_reviewed = needs_collapse_review(
        recent,
        selected_position,
    ) or weak_repeat_guarded
'''
if old_position not in text:
    raise SystemExit("position selection block not found")
text = text.replace(old_position, new_position)

old_challenge = '''        position_results.extend(challenge_results)
        position_scores = _aggregate(position_results)
        selected_position = max(range(10), key=position_scores.__getitem__)
'''
new_challenge = '''        position_results.extend(challenge_results)
        ai_position_scores = _aggregate(position_results)
        position_scores = _normalize(
            [
                ai_position_scores[index] * 0.45 + validation_scores[index] * 0.55
                for index in range(10)
            ]
        )
        selected_position = max(range(10), key=position_scores.__getitem__)
'''
if old_challenge not in text:
    raise SystemExit("challenge block not found")
text = text.replace(old_challenge, new_challenge)

old_numbers = '''    primary_probabilities = _aggregate(number_results)
    probabilities = primary_probabilities
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)

    recent_copy_reviewed = _matches_recent_window(
        ranked,
        verified,
        selected_position,
    )
'''
new_numbers = '''    primary_ai_probabilities = _aggregate(number_results)
    objective_probabilities = statistical_probabilities(verified, selected_position)
    primary_probabilities = blend_validated_probabilities(
        primary_ai_probabilities,
        objective_probabilities,
        secondary_weight=0.45,
    )
    probabilities = primary_probabilities
    ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)

    recent_copy_reviewed = _matches_recent_window(
        ranked,
        verified,
        selected_position,
    )
    copy_guard_applied = False
'''
if old_numbers not in text:
    raise SystemExit("number primary block not found")
text = text.replace(old_numbers, new_numbers)

old_holdout = '''        holdout_probabilities = _aggregate(holdout_results)
        probabilities = _blend_probabilities(
            primary_probabilities,
            holdout_probabilities,
        )
        ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
'''
new_holdout = '''        holdout_ai_probabilities = _aggregate(holdout_results)
        holdout_objective = statistical_probabilities(
            verified,
            selected_position,
            mask_recent=_RECENT_COPY_WINDOW,
        )
        holdout_probabilities = blend_validated_probabilities(
            holdout_ai_probabilities,
            holdout_objective,
            secondary_weight=0.55,
        )
        probabilities = _blend_probabilities(
            primary_probabilities,
            holdout_probabilities,
        )
        probabilities, copy_guard_applied = regularize_recent_copy(
            probabilities,
            verified,
            selected_position,
        )
        ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
'''
if old_holdout not in text:
    raise SystemExit("holdout block not found")
text = text.replace(old_holdout, new_holdout)

text = text.replace(
    '        f"{len(position_results)}轮匿名名次评审选择第{selected_position + 1}名，"\n',
    '        f"{len(position_results)}轮匿名名次评审结合滚动前向验证选择第{selected_position + 1}名，"\n',
)
text = text.replace(
    '            analysis + " 已触发连续同名次反偏置复核，未人为强制轮换。"\n',
    '            analysis + " 已触发连续同名次复核；弱边界时由前向验证较优名次裁决，不再机械锁死。"\n',
)
text = text.replace(
    '            + " 初次Top 7与最近7期候选集合高度重合，已增加隐藏最近7期的独立留出评审；最终结果由完整历史评审与留出评审加权汇总，并非程序换号。"\n',
    '            + " 初次结果与最近6/7期集合高度重合，已增加隐藏最近7期的独立留出评审、统计前向裁决和最近集合正则，避免直接复制最新六码。"\n',
)
text = text.replace(
    '            "这是开奖前冻结的AI多轮相对排序。号码阶段保留完整历史先后顺序，但每轮都将号码随机映射为A至J，"\n',
    '            "这是开奖前冻结的AI多轮相对排序，并由滚动前向验证约束名次与号码。号码阶段保留完整历史先后顺序，但每轮都将号码随机映射为A至J，"\n',
)
path.write_text(text, encoding="utf-8")

service = ROOT / "server/app/service.py"
service_text = service.read_text(encoding="utf-8")
service_text = service_text.replace(
    'native_model = "tianji-native-cloud-v1"',
    'native_model = "tianji-native-cloud-v2"',
)
service.write_text(service_text, encoding="utf-8")

# Update the collapse contract and add explicit regression coverage.
test_ai = ROOT / "server/tests/test_ai_ensemble.py"
test_text = test_ai.read_text(encoding="utf-8")
test_text = test_text.replace(
    "    def test_collapse_review_requires_six_consecutive_same_positions(self) -> None:\n"
    "        self.assertFalse(needs_collapse_review([0, 0, 0, 0, 0], 0))\n"
    "        self.assertTrue(needs_collapse_review([0, 0, 0, 0, 0, 0], 0))\n"
    "        self.assertFalse(needs_collapse_review([0, 0, 1, 0, 0, 0], 0))\n",
    "    def test_collapse_review_starts_after_three_consecutive_same_positions(self) -> None:\n"
    "        self.assertFalse(needs_collapse_review([0, 0], 0))\n"
    "        self.assertTrue(needs_collapse_review([0, 0, 0], 0))\n"
    "        self.assertFalse(needs_collapse_review([0, 0, 1, 0], 0))\n",
)
test_ai.write_text(test_text, encoding="utf-8")

quality_test = r'''from __future__ import annotations

import unittest

from app.forecast_quality import (
    position_quality_profile,
    recent_copy_diagnostics,
    regularize_recent_copy,
)
from app.models import DrawModel


def history(count: int = 120) -> list[DrawModel]:
    draws: list[DrawModel] = []
    for index in range(count):
        shift = index % 10
        numbers = list(range(1, 11))
        numbers = numbers[shift:] + numbers[:shift]
        draws.append(
            DrawModel(
                lottery="azxy10",
                period=str(21348000 + index),
                numbers=numbers,
                draw_time="",
                source="api68",
            )
        )
    return draws


class ForecastQualityTests(unittest.TestCase):
    def test_position_quality_uses_walk_forward_samples(self) -> None:
        profile = position_quality_profile(history(), 0)
        self.assertGreaterEqual(profile.walk_forward_samples, 12)
        self.assertGreater(profile.validation_score, 0)
        self.assertAlmostEqual(sum(profile.probabilities), 1.0)
        self.assertEqual(len(profile.top6), 6)

    def test_exact_latest_six_copy_is_detected_and_broken_on_weak_boundary(self) -> None:
        draws = history()
        latest_six = {draw.numbers[0] for draw in draws[-6:]}
        self.assertEqual(len(latest_six), 6)
        probabilities = [0.04] * 10
        for number in latest_six:
            probabilities[number - 1] = 0.14
        total = sum(probabilities)
        probabilities = [value / total for value in probabilities]
        ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
        self.assertTrue(recent_copy_diagnostics(ranked, draws, 0).exact_latest_six)
        adjusted, applied = regularize_recent_copy(probabilities, draws, 0)
        adjusted_ranked = sorted(range(10), key=adjusted.__getitem__, reverse=True)
        self.assertTrue(applied)
        self.assertNotEqual(
            {index + 1 for index in adjusted_ranked[:6]},
            latest_six,
        )
        self.assertAlmostEqual(sum(adjusted), 1.0)


if __name__ == "__main__":
    unittest.main()
'''
(ROOT / "server/tests/test_forecast_quality.py").write_text(quality_test, encoding="utf-8")

workflow = ROOT / ".github/workflows/repair-prediction-degeneracy.yml"
script = ROOT / "tools/repair_prediction_degeneracy.py"
workflow.unlink(missing_ok=True)
script.unlink(missing_ok=True)
