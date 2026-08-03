from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


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
