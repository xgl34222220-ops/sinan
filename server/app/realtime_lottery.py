from __future__ import annotations

import time
from typing import Any

import httpx

from .lottery import BASE_URL, HEADERS, lottery_client, normalize_next_period, parse_epoch_ms
from .models import DrawModel, LotterySpec


class RealtimeLotteryClient:
    """Low-latency API68 client used only for latest-draw probing.

    The normal LotteryClient remains responsible for historical backfill. This client keeps a
    long-lived connection pool and uses a short timeout so history sync, TLS setup, and slow
    upstream responses cannot hold the realtime probe loop hostage.
    """

    def __init__(self) -> None:
        self._timeout = httpx.Timeout(
            timeout=2.8,
            connect=1.5,
            read=2.8,
            write=2.8,
            pool=1.2,
        )
        self._client = httpx.Client(
            timeout=self._timeout,
            headers=HEADERS,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
        )

    def fetch_latest(
        self,
        spec: LotterySpec,
    ) -> tuple[DrawModel, str, int | None, int | None]:
        url = f"{BASE_URL}/pks/getLotteryPksInfo.do"
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = self._client.get(
                    url,
                    params={"lotCode": spec.lot_code, "_t": int(time.time() * 1000)},
                )
                response.raise_for_status()
                payload: Any = response.json()
                if not isinstance(payload, dict):
                    raise RuntimeError("开奖接口返回格式异常")
                data = lottery_client._unwrap(payload)  # noqa: SLF001 - shared canonical parser
                value = data[0] if isinstance(data, list) and data else data
                if not isinstance(value, dict):
                    raise RuntimeError(f"{spec.name} 最新开奖接口没有返回对象")
                draw = lottery_client._parse_draw(value, spec)  # noqa: SLF001
                if draw is None:
                    raise RuntimeError(f"{spec.name} 最新开奖接口没有有效期号或号码")

                # Keep App/server semantics aligned: nextIssue is authoritative when present.
                reported_next = lottery_client._first_text(  # noqa: SLF001
                    value,
                    "nextIssue",
                    "drawIssue",
                )
                next_period = normalize_next_period(draw.period, reported_next)
                server_time = parse_epoch_ms(
                    lottery_client._first_text(value, "serverTime")  # noqa: SLF001
                )
                next_draw_at = parse_epoch_ms(
                    lottery_client._first_text(  # noqa: SLF001
                        value,
                        "drawTime",
                        "nextDrawTime",
                    )
                )
                return draw, next_period, server_time, next_draw_at
            except Exception as exc:  # noqa: BLE001 - normalize upstream failures
                last_error = exc
                if attempt == 0:
                    time.sleep(0.12)
        raise RuntimeError(f"最新开奖快速探测失败：{last_error}") from last_error

    def close(self) -> None:
        self._client.close()


realtime_lottery_client = RealtimeLotteryClient()
