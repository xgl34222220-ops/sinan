from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .models import DrawModel, LotterySpec


BASE_URL = "https://api.api68.com"
CHINA_ZONE = ZoneInfo("Asia/Shanghai")
HEADERS = {
    "Accept": "application/json",
    "Cache-Control": "no-cache",
    "Referer": "https://www.168kai.com/",
    "User-Agent": "TianjiCloud/1.2",
}


class LotteryClient:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout = httpx.Timeout(timeout_seconds, connect=7.0)

    def fetch_latest(self, spec: LotterySpec) -> tuple[DrawModel, str, int | None, int | None]:
        url = f"{BASE_URL}/pks/getLotteryPksInfo.do"
        payload = self._request(url, {"lotCode": spec.lot_code, "_t": self._now_ms()})
        data = self._unwrap(payload)
        if isinstance(data, list):
            value = data[0] if data else None
        else:
            value = data
        if not isinstance(value, dict):
            raise RuntimeError(f"{spec.name} 最新开奖接口没有返回对象")
        draw = self._parse_draw(value, spec)
        if draw is None:
            raise RuntimeError(f"{spec.name} 最新开奖接口没有有效期号或号码")

        # API68 的 drawIssue 在部分彩种会返回旧的正在开奖期，不能优先当作下一期。
        # nextIssue 才是首选；无论上游返回什么，都必须保证目标期严格晚于最新已开奖期。
        reported_next = self._first_text(value, "nextIssue", "drawIssue")
        next_period = normalize_next_period(draw.period, reported_next)
        server_time = parse_epoch_ms(self._first_text(value, "serverTime"))
        next_draw_at = parse_epoch_ms(self._first_text(value, "drawTime", "nextDrawTime"))
        return draw, next_period, server_time, next_draw_at

    def fetch_date(self, spec: LotterySpec, target_date: date) -> list[DrawModel]:
        url = f"{BASE_URL}/pks/getPksHistoryList.do"
        payload = self._request(
            url,
            {
                "lotCode": spec.lot_code,
                "date": target_date.isoformat(),
                "pageSize": 2000,
                "_t": self._now_ms(),
            },
        )
        data = self._unwrap(payload)
        if isinstance(data, dict):
            data = data.get("list") or data.get("data") or []
        if not isinstance(data, list):
            return []
        draws = [self._parse_draw(item, spec) for item in data if isinstance(item, dict)]
        return merge_draws([draw for draw in draws if draw is not None])

    def fetch_recent(self, spec: LotterySpec, days: int) -> tuple[list[DrawModel], str, int | None, int | None]:
        today = datetime.now(CHINA_ZONE).date()
        dates = [today - timedelta(days=offset) for offset in range(max(1, days))]
        all_draws: list[DrawModel] = []
        worker_count = min(6, len(dates))
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures = {pool.submit(self.fetch_date, spec, target): target for target in dates}
            for future in as_completed(futures):
                try:
                    all_draws.extend(future.result())
                except Exception:
                    # 单日历史失败不能阻止最新期开奖同步；下一轮继续补齐并结算。
                    continue
        latest, next_period, server_time, next_draw_at = self.fetch_latest(spec)
        all_draws.append(latest)
        merged = merge_draws(all_draws)[-spec.history_target :]
        if not merged:
            raise RuntimeError(f"{spec.name} 没有可用开奖历史")
        return merged, next_period, server_time, next_draw_at

    def _request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for _ in range(2):
            try:
                with httpx.Client(timeout=self.timeout, headers=HEADERS, follow_redirects=True) as client:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise RuntimeError("开奖接口返回格式异常")
                    return payload
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"开奖接口请求失败：{last_error}") from last_error

    @staticmethod
    def _unwrap(root: dict[str, Any]) -> Any:
        result = root.get("result")
        if isinstance(result, dict):
            return result.get("data", result)
        if result is not None:
            return result
        return root.get("data")

    def _parse_draw(self, value: dict[str, Any], spec: LotterySpec) -> DrawModel | None:
        period = self._first_text(value, "preDrawIssue", "issue", "period", "drawIssue")
        raw_numbers = self._first_text(value, "preDrawCode", "drawCode", "numbers", "code")
        numbers: list[int] = []
        normalized = raw_numbers.replace("|", ",").replace(" ", ",")
        for token in normalized.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                number = int(token)
            except ValueError:
                continue
            if 1 <= number <= 10:
                numbers.append(number)
            if len(numbers) == 10:
                break
        if not period or len(numbers) != 10 or len(set(numbers)) != 10:
            return None
        return DrawModel(
            lottery=spec.key,
            period=period,
            numbers=numbers,
            draw_time=self._first_text(value, "preDrawTime", "openTime", "time"),
            source="api68",
        )

    @staticmethod
    def _first_text(value: dict[str, Any], *keys: str) -> str:
        for key in keys:
            item = value.get(key)
            if item is None:
                continue
            text = str(item).strip()
            if text:
                return text
        return ""

    @staticmethod
    def _now_ms() -> int:
        return int(datetime.now(tz=CHINA_ZONE).timestamp() * 1000)


def merge_draws(draws: list[DrawModel]) -> list[DrawModel]:
    unique: dict[tuple[str, str], DrawModel] = {}
    for draw in draws:
        unique[(draw.lottery, draw.period)] = draw
    return sorted(unique.values(), key=lambda item: period_sort_key(item.period))


def period_sort_key(period: str) -> tuple[int, str]:
    return len(period), period


def normalize_next_period(latest_period: str, reported_next: str) -> str:
    candidate = reported_next.strip()
    if candidate and period_sort_key(candidate) > period_sort_key(latest_period):
        return candidate
    return increment_period(latest_period)


def increment_period(period: str) -> str:
    index = len(period)
    while index > 0 and period[index - 1].isdigit():
        index -= 1
    if index == len(period):
        return "待同步"
    prefix, digits = period[:index], period[index:]
    try:
        return prefix + str(int(digits) + 1).zfill(len(digits))
    except ValueError:
        return "待同步"


def parse_epoch_ms(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    try:
        number = Decimal(text)
        if number > Decimal("100000000000"):
            return int(number)
        if number > Decimal("1000000000"):
            return int(number * 1000)
    except InvalidOperation:
        pass
    patterns = (
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    )
    for pattern in patterns:
        try:
            parsed = datetime.strptime(text[:19], pattern).replace(tzinfo=CHINA_ZONE)
            return int(parsed.timestamp() * 1000)
        except ValueError:
            continue
    return None


lottery_client = LotteryClient()
