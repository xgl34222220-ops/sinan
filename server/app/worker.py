from __future__ import annotations

import logging
import signal
import threading
import time

from .config import settings
from .service import run_all_cycles


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("tianji.worker")
stop_event = threading.Event()


def _stop(signum: int, _frame: object) -> None:
    logger.info("收到停止信号 %s，等待当前任务结束", signum)
    stop_event.set()


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    logger.info(
        "天机 Worker 启动：轮询 %s 秒，AI=%s",
        settings.poll_seconds,
        "启用" if settings.ai_enabled else "未配置",
    )
    while not stop_event.is_set():
        cycle_started = time.monotonic()
        try:
            result = run_all_cycles()
            logger.info("任务完成：%s", result)
        except Exception:
            logger.exception("后台任务发生未捕获错误")
        elapsed = time.monotonic() - cycle_started
        wait_seconds = max(1.0, settings.poll_seconds - elapsed)
        stop_event.wait(wait_seconds)
    logger.info("天机 Worker 已停止")


if __name__ == "__main__":
    main()
