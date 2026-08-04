from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


@dataclass(frozen=True)
class LotterySpec:
    key: str
    name: str
    lot_code: int
    interval_minutes: int
    history_target: int


LOTTERIES: dict[str, LotterySpec] = {
    "xyft": LotterySpec("xyft", "幸运飞艇", 10057, 5, 2000),
    "azxy10": LotterySpec("azxy10", "澳洲幸运10", 10012, 5, 3000),
}


def _contains_chinese(value: str) -> bool:
    return any("\u3400" <= char <= "\u9fff" for char in value)


def _localize_analysis(value: str) -> str:
    text = value.strip()
    if not text:
        return "服务器后台生成并按目标期冻结"
    if _contains_chinese(text):
        return text

    pattern = re.compile(
        r"Position\s+(\d+)\s+shows\s+number\s+(\d+)\s+appearing\s+(\d+)\s+times\s+in\s+last\s+(\d+)\s+draws,?\s*highest\s+frequency\.?\s*Recent\s+trend\s+favors\s+(\d+),?\s*with\s+last\s+draw\s+being\s+(\d+)\.?",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        position, number, count, draws, favored, last = match.groups()
        return (
            f"第{position}名中，号码{number}在最近{draws}期出现{count}次，出现频率最高；"
            f"近期走势偏向号码{favored}，最近一期为号码{last}。"
        )
    return "模型返回的说明不是中文，已隐藏英文原文；请以号码矩阵和真实前向验证结果为准。"


def _localize_risk(value: str) -> str:
    text = value.strip()
    if not text:
        return "随机开奖不可可靠预测，仅用于前向验证"
    if _contains_chinese(text):
        return text

    lowered = text.lower()
    if any(
        phrase in lowered
        for phrase in ("small sample", "randomness", "no guarantee", "future outcome")
    ):
        return "样本量较小，随机性可能造成偏差；不能保证未来结果。"
    return "随机开奖不可可靠预测；英文风险说明已转为中文兜底，仅用于前向验证。"


class DrawModel(BaseModel):
    lottery: str
    period: str
    numbers: list[int] = Field(min_length=10, max_length=10)
    draw_time: str = ""
    source: str = "api68"


class ForecastModel(BaseModel):
    id: int
    lottery: str
    target_period: str
    trained_through_period: str
    position: int = Field(ge=0, le=9)
    top6: list[int]
    top7: list[int]
    probabilities: list[float]
    source: str
    model: str
    analysis: str
    risk_note: str
    created_at_epoch_ms: int
    actual_number: int | None = None
    top6_hit: bool | None = None
    top7_hit: bool | None = None

    @field_validator("analysis")
    @classmethod
    def localize_analysis(cls, value: str) -> str:
        return _localize_analysis(value)

    @field_validator("risk_note")
    @classmethod
    def localize_risk(cls, value: str) -> str:
        return _localize_risk(value)


class SnapshotModel(BaseModel):
    lottery: str
    latest: DrawModel
    next_period: str
    draws: list[DrawModel]
    forecasts: list[ForecastModel]
    synced_at_epoch_ms: int


class HealthModel(BaseModel):
    status: str
    database: str
    worker: str
    ai_enabled: bool
    version: str
    last_worker_heartbeat_epoch_ms: int | None = None


def compact_json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
