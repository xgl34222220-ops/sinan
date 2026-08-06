from __future__ import annotations

from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: expected exactly one match, got {text.count(old)}")
    target.write_text(text.replace(old, new), encoding="utf-8")


def regex_once(path: str, pattern: str, replacement: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, lambda _: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{path}: regex expected one match, got {count}")
    target.write_text(updated, encoding="utf-8")


write(
    "server/app/adaptive_learning.py",
    r'''
    from __future__ import annotations

    import math
    from typing import Iterable, Mapping

    from .models import DrawModel


    MATH_STRATEGIES = (
        "long_frequency",
        "recent_frequency",
        "recency_decay",
        "omission_hazard",
        "markov_transition",
        "trend",
        "stability",
    )
    AI_STRATEGY = "ai_review"
    DEFAULT_WEIGHTS = {
        "long_frequency": 0.13,
        "recent_frequency": 0.09,
        "recency_decay": 0.08,
        "omission_hazard": 0.08,
        "markov_transition": 0.13,
        "trend": 0.08,
        "stability": 0.06,
        "ai_review": 0.35,
    }
    UNIFORM_LOG_LOSS = math.log(10.0)


    def normalize_probabilities(values: Iterable[float]) -> list[float]:
        safe = [
            float(value) if math.isfinite(float(value)) and float(value) > 0 else 1e-12
            for value in values
        ]
        if len(safe) != 10:
            raise ValueError("策略必须输出10个号码概率")
        total = sum(safe) or 1.0
        return [value / total for value in safe]


    def normalize_strategy_weights(
        current: Mapping[str, float] | None,
        strategies: Iterable[str],
    ) -> dict[str, float]:
        names = tuple(dict.fromkeys(strategies))
        if not names:
            return {}
        supplied = current or {}
        raw = {
            name: max(0.0, float(supplied.get(name, DEFAULT_WEIGHTS.get(name, 0.08))))
            for name in names
        }
        total = sum(raw.values())
        if total <= 0:
            return {name: 1.0 / len(names) for name in names}
        return {name: value / total for name, value in raw.items()}


    def blend_strategy_probabilities(
        components: Mapping[str, list[float]],
        weights: Mapping[str, float] | None,
    ) -> list[float]:
        if not components:
            raise ValueError("缺少可融合的预测策略")
        normalized_components = {
            name: normalize_probabilities(probabilities)
            for name, probabilities in components.items()
        }
        active = normalize_strategy_weights(weights, normalized_components)
        return normalize_probabilities(
            sum(active[name] * normalized_components[name][index] for name in normalized_components)
            for index in range(10)
        )


    def _canonical(history: list[DrawModel], limit: int = 3000) -> list[DrawModel]:
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


    def _intervals(values: list[int], number: int) -> tuple[list[int], int]:
        positions = [index for index, value in enumerate(values) if value == number]
        intervals = [positions[index] - positions[index - 1] for index in range(1, len(positions))]
        current_gap = len(values) if not positions else len(values) - 1 - positions[-1]
        return intervals, current_gap


    def strategy_components(
        history: list[DrawModel],
        position: int,
        *,
        mask_recent: int = 0,
    ) -> dict[str, list[float]]:
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

        long_frequency = normalize_probabilities(
            (count120[index] + 1.0) / (size120 + 10.0)
            for index in range(10)
        )
        recent_frequency = normalize_probabilities(
            0.62 * (count18[index] + 0.8) / (size18 + 8.0)
            + 0.38 * (count45[index] + 1.2) / (size45 + 12.0)
            for index in range(10)
        )

        recency_raw = [0.0] * 10
        for index, number in enumerate(values):
            age = len(values) - 1 - index
            recency_raw[number - 1] += math.exp(-age / 24.0)
        recency_decay = normalize_probabilities(recency_raw)

        hazard_raw: list[float] = []
        for number in range(1, 11):
            intervals, current_gap = _intervals(values, number)
            if not intervals:
                hazard_raw.append(0.1)
                continue
            bandwidth = max(1, round(math.sqrt(len(intervals)) / 2))
            at_risk = sum(1 for gap in intervals if gap >= max(1, current_gap - bandwidth))
            nearby = sum(1 for gap in intervals if abs(gap - current_gap) <= bandwidth)
            empirical = (nearby + 1.0) / (at_risk + 10.0)
            hazard_raw.append(0.65 * empirical + 0.35 * 0.1)
        omission_hazard = normalize_probabilities(hazard_raw)

        current = values[-1]
        successors = [0.0] * 10
        transition_samples = 0
        for index in range(1, len(values)):
            if values[index - 1] == current:
                successors[values[index] - 1] += 1.0
                transition_samples += 1
        shrink = max(8.0, 24.0 - transition_samples)
        markov_transition = normalize_probabilities(
            successors[index] + long_frequency[index] * shrink
            for index in range(10)
        )

        trend = normalize_probabilities(
            math.exp((count18[index] / size18 - count45[index] / size45) * 4.0)
            for index in range(10)
        )
        stability = normalize_probabilities(
            long_frequency[index]
            / (
                0.06
                + abs(count18[index] / size18 - count45[index] / size45)
                + 0.45 * abs(count45[index] / size45 - count120[index] / size120)
            )
            for index in range(10)
        )
        return {
            "long_frequency": long_frequency,
            "recent_frequency": recent_frequency,
            "recency_decay": recency_decay,
            "omission_hazard": omission_hazard,
            "markov_transition": markov_transition,
            "trend": trend,
            "stability": stability,
        }


    def prediction_loss(probabilities: list[float], actual_number: int) -> dict[str, float | bool]:
        normalized = normalize_probabilities(probabilities)
        if actual_number not in range(1, 11):
            raise ValueError("实际号码超出范围")
        actual_index = actual_number - 1
        log_loss = -math.log(max(1e-12, normalized[actual_index]))
        brier = sum(
            (probability - (1.0 if index == actual_index else 0.0)) ** 2
            for index, probability in enumerate(normalized)
        )
        ranked = sorted(range(10), key=normalized.__getitem__, reverse=True)
        return {
            "log_loss": log_loss,
            "brier": brier,
            "top6_hit": actual_index in ranked[:6],
            "combined_loss": 0.8 * log_loss + 0.2 * (brier / 0.9) * UNIFORM_LOG_LOSS,
        }


    def _bounded_normalize(
        values: Mapping[str, float],
        *,
        floor: float = 0.025,
        cap: float = 0.55,
    ) -> dict[str, float]:
        names = tuple(values)
        if not names:
            return {}
        safe = {name: max(1e-12, float(values[name])) for name in names}
        for _ in range(8):
            total = sum(safe.values()) or 1.0
            safe = {name: value / total for name, value in safe.items()}
            low = [name for name, value in safe.items() if value < floor]
            high = [name for name, value in safe.items() if value > cap]
            if not low and not high:
                break
            fixed = {name: floor for name in low}
            fixed.update({name: cap for name in high})
            free = [name for name in names if name not in fixed]
            remaining = max(0.0, 1.0 - sum(fixed.values()))
            free_total = sum(safe[name] for name in free) or 1.0
            safe = {
                name: fixed.get(name, remaining * safe[name] / free_total)
                for name in names
            }
        total = sum(safe.values()) or 1.0
        return {name: value / total for name, value in safe.items()}


    def update_strategy_weights(
        current: Mapping[str, float],
        losses: Mapping[str, float],
        *,
        learning_rate: float = 0.22,
    ) -> dict[str, float]:
        names = tuple(losses)
        weights = normalize_strategy_weights(current, names)
        updated = {
            name: weights[name]
            * math.exp(
                -learning_rate
                * max(-UNIFORM_LOG_LOSS, min(UNIFORM_LOG_LOSS, losses[name] - UNIFORM_LOG_LOSS))
            )
            for name in names
        }
        return _bounded_normalize(updated)
    ''',
)


write(
    "server/app/forecast_quality.py",
    r'''
    from __future__ import annotations

    from dataclasses import dataclass
    import math

    from .adaptive_learning import (
        blend_strategy_probabilities,
        normalize_strategy_weights,
        strategy_components,
    )
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


    def _canonical(history: list[DrawModel], limit: int = 3000) -> list[DrawModel]:
        return [
            draw
            for draw in history
            if len(draw.numbers) == 10 and len(set(draw.numbers)) == 10
        ][-limit:]


    def statistical_components(
        history: list[DrawModel],
        position: int,
        *,
        mask_recent: int = 0,
    ) -> dict[str, list[float]]:
        return strategy_components(history, position, mask_recent=mask_recent)


    def statistical_probabilities(
        history: list[DrawModel],
        position: int,
        *,
        mask_recent: int = 0,
        strategy_weights: dict[str, float] | None = None,
    ) -> list[float]:
        components = statistical_components(history, position, mask_recent=mask_recent)
        return blend_strategy_probabilities(components, strategy_weights)


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
        strategy_weights: dict[str, float] | None = None,
    ) -> PositionQuality:
        verified = _canonical(history)
        if len(verified) < 40:
            probabilities = statistical_probabilities(
                verified,
                position,
                strategy_weights=strategy_weights,
            )
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
            probabilities = statistical_probabilities(
                prefix,
                position,
                strategy_weights=strategy_weights,
            )
            ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
            actual = verified[cursor].numbers[position]
            if actual in {index + 1 for index in ranked[:6]}:
                hits += 1
            losses.append(-math.log(max(1e-12, probabilities[actual - 1])))
            samples += 1

        current = statistical_probabilities(
            verified,
            position,
            strategy_weights=strategy_weights,
        )
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
        strategy_weights: dict[str, float] | None = None,
    ) -> tuple[list[float], bool]:
        ranked = sorted(range(10), key=probabilities.__getitem__, reverse=True)
        diagnostics = recent_copy_diagnostics(ranked, history, position)
        if not diagnostics.triggered:
            return _normalize(probabilities), False

        verified = _canonical(history)
        safe_mask = min(mask_recent, max(0, len(verified) - 30))
        adjusted = list(probabilities)
        if safe_mask > 0:
            masked = statistical_probabilities(
                verified,
                position,
                mask_recent=safe_mask,
                strategy_weights=strategy_weights,
            )
            adjusted = blend_probabilities(adjusted, masked, secondary_weight=0.68)

        recent_six = {draw.numbers[position] for draw in verified[-6:]}
        adjusted = _normalize(
            [
                value * (0.78 if index + 1 in recent_six else 1.22)
                for index, value in enumerate(adjusted)
            ]
        )
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
    ''',
)


write(
    "server/app/predictor.py",
    r'''
    from __future__ import annotations

    from dataclasses import dataclass, field

    from .adaptive_learning import normalize_strategy_weights
    from .forecast_quality import (
        position_quality_profile,
        regularize_recent_copy,
        statistical_components,
    )
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
        strategy_probabilities: dict[str, list[float]] = field(default_factory=dict)
        strategy_weights: dict[str, float] = field(default_factory=dict)


    @dataclass(frozen=True)
    class NativePrediction:
        selected: PositionResult
        positions: list[PositionResult]
        analysis: str
        risk_note: str


    def _position_result(
        history: list[DrawModel],
        position: int,
        strategy_weights: dict[str, float] | None,
    ) -> PositionResult:
        components = statistical_components(history, position)
        active_weights = normalize_strategy_weights(strategy_weights, components)
        profile = position_quality_profile(
            history,
            position,
            strategy_weights=active_weights,
        )
        probabilities, guarded = regularize_recent_copy(
            profile.probabilities,
            history,
            position,
            strategy_weights=active_weights,
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
            strategy_probabilities=components,
            strategy_weights=active_weights,
        )


    def predict(
        history_input: list[DrawModel],
        strategy_weights: dict[str, float] | None = None,
    ) -> NativePrediction:
        history = [
            draw
            for draw in history_input
            if len(draw.numbers) == 10 and len(set(draw.numbers)) == 10
        ][-3000:]
        if len(history) < 30:
            raise ValueError("至少需要 30 期有效历史才能生成预测")

        positions = [
            _position_result(history, position, strategy_weights)
            for position in range(10)
        ]
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
        leaders = sorted(
            selected.strategy_weights.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        leader_text = "、".join(f"{name} {weight * 100:.1f}%" for name, weight in leaders)
        analysis = (
            f"自适应云端引擎对十个名次分别执行滚动前向验证后选择第 {selected.position + 1} 名；"
            f"验证样本 {selected.walk_forward_samples} 期，收缩命中率约 {hit_percent:.1f}%，"
            f"当前六码边界差约 {margin_percent:.2f} 个百分点。"
            f"策略权重由每期开奖后的真实损失在线更新，当前主要策略：{leader_text}。"
            + (
                " 检测到结果过度贴近最近六码，已使用隐藏近期窗口和边界正则重新排序。"
                if selected.copy_guard_applied
                else ""
            )
        )
        risk_note = (
            "随机开奖没有可保证的可预测规律；在线学习只会根据真实前向结果调整策略权重，"
            "不能把随机波动变成确定规律。候选结果不得理解为必中或真实中奖概率。"
        )
        return NativePrediction(selected, positions, analysis, risk_note)
    ''',
)


replace_once(
    "server/app/db.py",
    "import json\nimport os",
    "import json\nimport math\nimport os",
)
replace_once(
    "server/app/db.py",
    "from .config import settings\nfrom .models import DrawModel, ForecastModel",
    "from .adaptive_learning import prediction_loss, update_strategy_weights\nfrom .config import settings\nfrom .models import DrawModel, ForecastModel",
)
replace_once(
    "server/app/db.py",
    """      \n                CREATE TABLE IF NOT EXISTS service_state (""",
    """\n                CREATE TABLE IF NOT EXISTS forecast_strategy_predictions (\n                    forecast_id INTEGER NOT NULL,\n                    lottery TEXT NOT NULL,\n                    source TEXT NOT NULL,\n                    strategy TEXT NOT NULL,\n                    probabilities_json TEXT NOT NULL,\n                    weight_at_prediction REAL NOT NULL,\n                    log_loss REAL,\n                    brier_score REAL,\n                    top6_hit INTEGER,\n                    settled_at INTEGER,\n                    created_at INTEGER NOT NULL,\n                    PRIMARY KEY (forecast_id, strategy),\n                    FOREIGN KEY (forecast_id) REFERENCES forecasts(id) ON DELETE CASCADE\n                );\n                CREATE INDEX IF NOT EXISTS forecast_strategy_lottery_created\n                    ON forecast_strategy_predictions(lottery, source, created_at DESC);\n\n                CREATE TABLE IF NOT EXISTS strategy_learning (\n                    lottery TEXT NOT NULL,\n                    source TEXT NOT NULL,\n                    strategy TEXT NOT NULL,\n                    weight REAL NOT NULL,\n                    samples INTEGER NOT NULL DEFAULT 0,\n                    ema_log_loss REAL NOT NULL DEFAULT 0,\n                    ema_brier REAL NOT NULL DEFAULT 0,\n                    top6_hits INTEGER NOT NULL DEFAULT 0,\n                    top6_misses INTEGER NOT NULL DEFAULT 0,\n                    updated_at INTEGER NOT NULL,\n                    PRIMARY KEY (lottery, source, strategy)\n                );\n\n                CREATE TABLE IF NOT EXISTS service_state (""",
)

regex_once(
    "server/app/db.py",
    r"    def settle_forecasts\(self, lottery: str\) -> int:\n.*?\n    def list_forecasts\(",
    r'''    def get_strategy_weights(self, lottery: str, source: str) -> dict[str, float]:
        with self.connection() as db:
            rows = db.execute(
                """
                SELECT strategy, weight
                FROM strategy_learning
                WHERE lottery = ? AND source = ?
                """,
                (lottery, source),
            ).fetchall()
        return {str(row["strategy"]): float(row["weight"]) for row in rows}

    def save_strategy_predictions(
        self,
        *,
        forecast_id: int,
        lottery: str,
        source: str,
        probabilities_by_strategy: dict[str, list[float]],
        weights: dict[str, float],
    ) -> None:
        if not probabilities_by_strategy:
            return
        now = int(time.time() * 1000)
        rows = [
            (
                forecast_id,
                lottery,
                source,
                strategy,
                json.dumps(probabilities, separators=(",", ":")),
                max(0.0, float(weights.get(strategy, 0.0))),
                now,
            )
            for strategy, probabilities in probabilities_by_strategy.items()
            if len(probabilities) == 10
        ]
        with self.connection() as db:
            db.executemany(
                """
                INSERT OR REPLACE INTO forecast_strategy_predictions(
                    forecast_id, lottery, source, strategy, probabilities_json,
                    weight_at_prediction, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    @staticmethod
    def _settle_strategy_learning(
        db: sqlite3.Connection,
        *,
        forecast_id: int,
        lottery: str,
        source: str,
        actual_number: int,
        settled_at: int,
    ) -> None:
        rows = db.execute(
            """
            SELECT strategy, probabilities_json, weight_at_prediction
            FROM forecast_strategy_predictions
            WHERE forecast_id = ? AND settled_at IS NULL
            """,
            (forecast_id,),
        ).fetchall()
        if not rows:
            return

        metrics: dict[str, dict[str, float | bool]] = {}
        snapshot_weights: dict[str, float] = {}
        for row in rows:
            strategy = str(row["strategy"])
            probabilities = json.loads(row["probabilities_json"])
            metrics[strategy] = prediction_loss(probabilities, actual_number)
            snapshot_weights[strategy] = max(0.0, float(row["weight_at_prediction"]))

        current_rows = db.execute(
            """
            SELECT strategy, weight, samples, ema_log_loss, ema_brier,
                   top6_hits, top6_misses
            FROM strategy_learning
            WHERE lottery = ? AND source = ?
            """,
            (lottery, source),
        ).fetchall()
        current = {str(row["strategy"]): dict(row) for row in current_rows}
        current_weights = {
            strategy: float(current.get(strategy, {}).get("weight", snapshot_weights[strategy]))
            for strategy in metrics
        }
        updated_weights = update_strategy_weights(
            current_weights,
            {strategy: float(value["combined_loss"]) for strategy, value in metrics.items()},
        )

        for strategy, value in metrics.items():
            previous = current.get(strategy, {})
            samples = int(previous.get("samples", 0)) + 1
            old_log = float(previous.get("ema_log_loss", value["log_loss"]))
            old_brier = float(previous.get("ema_brier", value["brier"]))
            alpha = 0.12 if samples <= 30 else 0.06
            ema_log = old_log * (1.0 - alpha) + float(value["log_loss"]) * alpha
            ema_brier = old_brier * (1.0 - alpha) + float(value["brier"]) * alpha
            hit = bool(value["top6_hit"])
            db.execute(
                """
                INSERT INTO strategy_learning(
                    lottery, source, strategy, weight, samples,
                    ema_log_loss, ema_brier, top6_hits, top6_misses, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lottery, source, strategy) DO UPDATE SET
                    weight = excluded.weight,
                    samples = excluded.samples,
                    ema_log_loss = excluded.ema_log_loss,
                    ema_brier = excluded.ema_brier,
                    top6_hits = excluded.top6_hits,
                    top6_misses = excluded.top6_misses,
                    updated_at = excluded.updated_at
                """,
                (
                    lottery,
                    source,
                    strategy,
                    updated_weights[strategy],
                    samples,
                    ema_log,
                    ema_brier,
                    int(previous.get("top6_hits", 0)) + int(hit),
                    int(previous.get("top6_misses", 0)) + int(not hit),
                    settled_at,
                ),
            )
            db.execute(
                """
                UPDATE forecast_strategy_predictions SET
                    log_loss = ?, brier_score = ?, top6_hit = ?, settled_at = ?
                WHERE forecast_id = ? AND strategy = ?
                """,
                (
                    float(value["log_loss"]),
                    float(value["brier"]),
                    int(hit),
                    settled_at,
                    forecast_id,
                    strategy,
                ),
            )

    def strategy_learning_summary(self, lottery: str, source: str) -> list[dict[str, object]]:
        with self.connection() as db:
            rows = db.execute(
                """
                SELECT strategy, weight, samples, ema_log_loss, ema_brier,
                       top6_hits, top6_misses, updated_at
                FROM strategy_learning
                WHERE lottery = ? AND source = ?
                ORDER BY weight DESC, strategy ASC
                """,
                (lottery, source),
            ).fetchall()
        return [dict(row) for row in rows]

    def settle_forecasts(self, lottery: str) -> int:
        with self.connection() as db:
            pending = db.execute(
                """
                SELECT id, target_period, position_index, top6_json, top7_json, source
                FROM forecasts
                WHERE lottery = ? AND settled_at IS NULL
                ORDER BY id ASC
                """,
                (lottery,),
            ).fetchall()
            settled = 0
            now = int(time.time() * 1000)
            for row in pending:
                draw = db.execute(
                    "SELECT numbers_json FROM draws WHERE lottery = ? AND period = ?",
                    (lottery, row["target_period"]),
                ).fetchone()
                if draw is None:
                    continue
                numbers = json.loads(draw["numbers_json"])
                position = int(row["position_index"])
                if position < 0 or position >= len(numbers):
                    continue
                actual = int(numbers[position])
                top6 = set(json.loads(row["top6_json"]))
                top7 = set(json.loads(row["top7_json"]))
                db.execute(
                    """
                    UPDATE forecasts SET
                        actual_number = ?, top6_hit = ?, top7_hit = ?, settled_at = ?
                    WHERE id = ?
                    """,
                    (actual, int(actual in top6), int(actual in top7), now, row["id"]),
                )
                self._settle_strategy_learning(
                    db,
                    forecast_id=int(row["id"]),
                    lottery=lottery,
                    source=str(row["source"]),
                    actual_number=actual,
                    settled_at=now,
                )
                settled += 1
            return settled

    def list_forecasts(''',
)

replace_once(
    "server/app/service.py",
    'SERVICE_VERSION = "1.6.0"',
    'SERVICE_VERSION = "1.7.0"',
)
replace_once(
    "server/app/service.py",
    """        result = ai.analyze(
            history,
            target_period,
            ai_config,
            recent_positions=recent_ai_positions,
        )""",
    """        strategy_weights = database.get_strategy_weights(spec.key, "ai")
        result = ai.analyze(
            history,
            target_period,
            ai_config,
            recent_positions=recent_ai_positions,
            strategy_weights=strategy_weights,
        )""",
)
replace_once(
    "server/app/service.py",
    """        if inserted is not None:
            try:
                telegram_events.process(spec.key)""",
    """        if inserted is not None:
            database.save_strategy_predictions(
                forecast_id=inserted,
                lottery=spec.key,
                source="ai",
                probabilities_by_strategy=result.strategy_probabilities,
                weights=result.strategy_weights,
            )
            try:
                telegram_events.process(spec.key)""",
)
replace_once(
    "server/app/service.py",
    """    with _record_stage(stages, "settle_forecasts"):
        settled = database.settle_forecasts(lottery_key)""",
    """    with _record_stage(stages, "settle_forecasts"):
        settled = database.settle_forecasts(lottery_key)
        learning_summary = {
            "native": database.strategy_learning_summary(lottery_key, "native"),
            "ai": database.strategy_learning_summary(lottery_key, "ai"),
        }
        _state(f"learning:{lottery_key}", learning_summary)""",
)
replace_once(
    "server/app/service.py",
    'native_model = "tianji-native-cloud-v2"',
    'native_model = "tianji-native-cloud-v3"',
)
replace_once(
    "server/app/service.py",
    """                with _record_stage(stages, "generate_native"):
                    native = predict(history)""",
    """                with _record_stage(stages, "generate_native"):
                    native_weights = database.get_strategy_weights(lottery_key, "native")
                    native = predict(history, strategy_weights=native_weights)""",
)
replace_once(
    "server/app/service.py",
    """                    if inserted is not None:
                        generated.append("native")""",
    """                    if inserted is not None:
                        database.save_strategy_predictions(
                            forecast_id=inserted,
                            lottery=lottery_key,
                            source="native",
                            probabilities_by_strategy=selected.strategy_probabilities,
                            weights=selected.strategy_weights,
                        )
                        generated.append("native")""",
)
replace_once(
    "server/app/service.py",
    '        "settled": settled,',
    '        "settled": settled,\n        "learning": learning_summary,',
)

replace_once(
    "server/app/ai.py",
    "from dataclasses import dataclass",
    "from dataclasses import dataclass, field",
)
replace_once(
    "server/app/ai.py",
    """    cache_hit_rate: float = 0.0


@dataclass(frozen=True)""",
    """    cache_hit_rate: float = 0.0
    strategy_probabilities: dict[str, list[float]] = field(default_factory=dict)
    strategy_weights: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)""",
)
replace_once(
    "server/app/ai.py",
    """    *,
    recent_positions: list[int] | None = None,
) -> AiPrediction:""",
    """    *,
    recent_positions: list[int] | None = None,
    strategy_weights: dict[str, float] | None = None,
) -> AiPrediction:""",
)
replace_once(
    "server/app/ai.py",
    """        active,
        recent_positions=recent_positions,
    )""",
    """        active,
        recent_positions=recent_positions,
        strategy_weights=strategy_weights,
    )""",
)
replace_once(
    "server/app/ai.py",
    """        reasoning_tokens=result.reasoning_tokens,
        cache_hit_rate=result.cache_hit_rate,
    )""",
    """        reasoning_tokens=result.reasoning_tokens,
        cache_hit_rate=result.cache_hit_rate,
        strategy_probabilities=result.strategy_probabilities,
        strategy_weights=result.strategy_weights,
    )""",
)

replace_once(
    "server/app/ai_ensemble.py",
    """import httpx

from .forecast_quality import (""",
    """import httpx

from .adaptive_learning import (
    blend_strategy_probabilities,
    normalize_strategy_weights,
)
from .forecast_quality import (""",
)
replace_once(
    "server/app/ai_ensemble.py",
    """    regularize_recent_copy,
    statistical_probabilities,
)""",
    """    regularize_recent_copy,
    statistical_components,
    statistical_probabilities,
)""",
)
replace_once(
    "server/app/ai_ensemble.py",
    """    cache_hit_rate: float


@dataclass(frozen=True)""",
    """    cache_hit_rate: float
    strategy_probabilities: dict[str, list[float]] = field(default_factory=dict)
    strategy_weights: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)""",
)
replace_once(
    "server/app/ai_ensemble.py",
    """    *,
    recent_positions: list[int] | None = None,
) -> AiEnsembleResult:""",
    """    *,
    recent_positions: list[int] | None = None,
    strategy_weights: dict[str, float] | None = None,
) -> AiEnsembleResult:""",
)
replace_once(
    "server/app/ai_ensemble.py",
    """    position_scores = _normalize(
        [
            ai_position_scores[index] * 0.45 + validation_scores[index] * 0.55
            for index in range(10)
        ]
    )""",
    """    math_weight_total = sum(
        value for name, value in (strategy_weights or {}).items() if name != "ai_review"
    )
    position_mix = normalize_strategy_weights(
        {
            "ai_review": (strategy_weights or {}).get("ai_review", 0.35),
            "walk_forward": math_weight_total or 0.65,
        },
        ("ai_review", "walk_forward"),
    )
    position_scores = _normalize(
        [
            ai_position_scores[index] * position_mix["ai_review"]
            + validation_scores[index] * position_mix["walk_forward"]
            for index in range(10)
        ]
    )""",
)
replace_once(
    "server/app/ai_ensemble.py",
    """        position_scores = _normalize(
            [
                ai_position_scores[index] * 0.45 + validation_scores[index] * 0.55
                for index in range(10)
            ]
        )""",
    """        position_scores = _normalize(
            [
                ai_position_scores[index] * position_mix["ai_review"]
                + validation_scores[index] * position_mix["walk_forward"]
                for index in range(10)
            ]
        )""",
)
replace_once(
    "server/app/ai_ensemble.py",
    """    objective_probabilities = statistical_probabilities(verified, selected_position)
    primary_probabilities = blend_validated_probabilities(
        primary_ai_probabilities,
        objective_probabilities,
        secondary_weight=0.45,
    )""",
    """    math_components = statistical_components(verified, selected_position)
    strategy_probabilities = dict(math_components)
    strategy_probabilities["ai_review"] = primary_ai_probabilities
    active_strategy_weights = normalize_strategy_weights(
        strategy_weights,
        strategy_probabilities,
    )
    primary_probabilities = blend_strategy_probabilities(
        strategy_probabilities,
        active_strategy_weights,
    )""",
)
replace_once(
    "server/app/ai_ensemble.py",
    """        holdout_objective = statistical_probabilities(
            verified,
            selected_position,
            mask_recent=_RECENT_COPY_WINDOW,
        )
        holdout_probabilities = blend_validated_probabilities(
            holdout_ai_probabilities,
            holdout_objective,
            secondary_weight=0.55,
        )""",
    """        holdout_components = statistical_components(
            verified,
            selected_position,
            mask_recent=_RECENT_COPY_WINDOW,
        )
        holdout_strategy_probabilities = dict(holdout_components)
        holdout_strategy_probabilities["ai_review"] = holdout_ai_probabilities
        holdout_probabilities = blend_strategy_probabilities(
            holdout_strategy_probabilities,
            active_strategy_weights,
        )""",
)
replace_once(
    "server/app/ai_ensemble.py",
    """        probabilities, copy_guard_applied = regularize_recent_copy(
            probabilities,
            verified,
            selected_position,
        )""",
    """        probabilities, copy_guard_applied = regularize_recent_copy(
            probabilities,
            verified,
            selected_position,
            strategy_weights=active_strategy_weights,
        )""",
)
replace_once(
    "server/app/ai_ensemble.py",
    """    if recent_copy_reviewed:
        analysis = (
            analysis
            + " 初次结果与最近6/7期集合高度重合，已增加隐藏最近7期的独立留出评审、统计前向裁决和最近集合正则，避免直接复制最新六码。"
        )[:560]

    usage = _merge_usage""",
    """    if recent_copy_reviewed:
        analysis = (
            analysis
            + " 初次结果与最近6/7期集合高度重合，已增加隐藏最近7期的独立留出评审、统计前向裁决和最近集合正则，避免直接复制最新六码。"
        )[:560]
    learning_leaders = sorted(
        active_strategy_weights.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:3]
    learning_text = "、".join(
        f"{name} {weight * 100:.1f}%" for name, weight in learning_leaders
    )
    analysis = (
        analysis
        + f" 当前融合权重由已结算预测在线学习，主要策略：{learning_text}；不中会自动降权，不再使用固定融合比例。"
    )[:720]

    usage = _merge_usage""",
)
replace_once(
    "server/app/ai_ensemble.py",
    """        reasoning_tokens=usage["reasoning_tokens"],
        cache_hit_rate=round(cache_hit_rate, 6),
    )""",
    """        reasoning_tokens=usage["reasoning_tokens"],
        cache_hit_rate=round(cache_hit_rate, 6),
        strategy_probabilities=strategy_probabilities,
        strategy_weights=active_strategy_weights,
    )""",
)

write(
    "server/tests/test_adaptive_learning.py",
    r'''
    from __future__ import annotations

    import tempfile
    import unittest

    from app.adaptive_learning import (
        blend_strategy_probabilities,
        prediction_loss,
        strategy_components,
        update_strategy_weights,
    )
    from app.db import Database
    from app.models import DrawModel


    def history(count: int = 160) -> list[DrawModel]:
        rows: list[DrawModel] = []
        base = list(range(1, 11))
        for index in range(count):
            shift = (index * 3 + index // 7) % 10
            numbers = base[shift:] + base[:shift]
            rows.append(
                DrawModel(
                    lottery="xyft",
                    period=str(100000 + index),
                    numbers=numbers,
                )
            )
        return rows


    class AdaptiveLearningTests(unittest.TestCase):
        def test_components_are_distinct_normalized_probabilities(self) -> None:
            components = strategy_components(history(), 0)
            self.assertGreaterEqual(len(components), 7)
            for probabilities in components.values():
                self.assertEqual(len(probabilities), 10)
                self.assertAlmostEqual(sum(probabilities), 1.0, places=8)
            unique = {tuple(round(value, 8) for value in item) for item in components.values()}
            self.assertGreater(len(unique), 3)

        def test_good_strategy_gains_weight_and_bad_strategy_loses_weight(self) -> None:
            good = [0.04] * 10
            bad = [0.106] * 10
            good[2] = 0.64
            bad[2] = 0.046
            good_loss = prediction_loss(good, 3)["combined_loss"]
            bad_loss = prediction_loss(bad, 3)["combined_loss"]
            updated = update_strategy_weights(
                {"good": 0.5, "bad": 0.5},
                {"good": float(good_loss), "bad": float(bad_loss)},
            )
            self.assertGreater(updated["good"], 0.5)
            self.assertLess(updated["bad"], 0.5)
            self.assertAlmostEqual(sum(updated.values()), 1.0, places=8)

        def test_settlement_persists_scores_and_updates_next_weights(self) -> None:
            with tempfile.TemporaryDirectory() as directory:
                database = Database(f"{directory}/adaptive.db")
                forecast_id = database.save_forecast(
                    lottery="xyft",
                    target_period="200001",
                    trained_through_period="200000",
                    position=0,
                    top6=[1, 2, 3, 4, 5, 6],
                    top7=[1, 2, 3, 4, 5, 6, 7],
                    probabilities=[0.1] * 10,
                    source="native",
                    model="test-adaptive",
                    analysis="测试",
                    risk_note="测试",
                )
                assert forecast_id is not None
                good = [0.04] * 10
                bad = [0.106] * 10
                good[2] = 0.64
                bad[2] = 0.046
                database.save_strategy_predictions(
                    forecast_id=forecast_id,
                    lottery="xyft",
                    source="native",
                    probabilities_by_strategy={"good": good, "bad": bad},
                    weights={"good": 0.5, "bad": 0.5},
                )
                database.save_draws(
                    [
                        DrawModel(
                            lottery="xyft",
                            period="200001",
                            numbers=[3, 1, 2, 4, 5, 6, 7, 8, 9, 10],
                        )
                    ]
                )
                self.assertEqual(database.settle_forecasts("xyft"), 1)
                weights = database.get_strategy_weights("xyft", "native")
                self.assertGreater(weights["good"], weights["bad"])
                summary = database.strategy_learning_summary("xyft", "native")
                self.assertEqual({item["samples"] for item in summary}, {1})
                self.assertEqual(sum(int(item["top6_hits"]) for item in summary), 1)

        def test_blend_follows_updated_weights(self) -> None:
            left = [0.7] + [0.3 / 9] * 9
            right = [0.3 / 9] * 9 + [0.7]
            blended = blend_strategy_probabilities(
                {"left": left, "right": right},
                {"left": 0.8, "right": 0.2},
            )
            self.assertGreater(blended[0], blended[9])


    if __name__ == "__main__":
        unittest.main()
    ''',
)

print("adaptive online learning changes applied")
