from __future__ import annotations

from collections import defaultdict, deque
import json
import logging
import threading
import time
import uuid
from typing import Deque

from fastapi import Depends, Request
from fastapi.responses import JSONResponse

from .config import settings
from .db import database
from .runtime_optimizations import cleanup_runtime_state, install as install_runtime_optimizations

install_runtime_optimizations()

from .main import app, require_admin_session  # noqa: E402
from .models import LOTTERIES  # noqa: E402
from .service import SERVICE_VERSION  # noqa: E402


logger = logging.getLogger("tianji.http")
_login_lock = threading.Lock()
_login_failures: dict[str, Deque[float]] = defaultdict(deque)
_login_locked_until: dict[str, float] = {}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded[:80]
    return (request.client.host if request.client else "unknown")[:80]


def _prune_failures(ip: str, now: float) -> None:
    failures = _login_failures[ip]
    cutoff = now - settings.login_window_seconds
    while failures and failures[0] < cutoff:
        failures.popleft()
    if not failures:
        _login_failures.pop(ip, None)


def _login_retry_after(ip: str, now: float) -> int:
    with _login_lock:
        locked_until = _login_locked_until.get(ip, 0.0)
        if locked_until <= now:
            _login_locked_until.pop(ip, None)
            _prune_failures(ip, now)
            return 0
        return max(1, int(locked_until - now))


def _record_login_result(ip: str, status_code: int, now: float) -> None:
    with _login_lock:
        if 200 <= status_code < 300:
            _login_failures.pop(ip, None)
            _login_locked_until.pop(ip, None)
            return
        if status_code != 401:
            return
        failures = _login_failures[ip]
        cutoff = now - settings.login_window_seconds
        while failures and failures[0] < cutoff:
            failures.popleft()
        failures.append(now)
        if len(failures) >= settings.login_max_failures:
            _login_locked_until[ip] = now + settings.login_lock_seconds
            failures.clear()


def _same_origin_allowed(request: Request) -> bool:
    fetch_site = request.headers.get("sec-fetch-site", "").lower()
    if fetch_site in {"cross-site", "none"}:
        return False
    origin = request.headers.get("origin", "").strip()
    referer = request.headers.get("referer", "").strip()
    expected_host = request.headers.get("host", request.url.netloc).lower()
    for value in (origin, referer):
        if not value:
            continue
        try:
            from urllib.parse import urlsplit

            return urlsplit(value).netloc.lower() == expected_host
        except ValueError:
            return False
    return True


def _set_security_headers(request: Request, response) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; connect-src 'self'",
    )
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    if forwarded_proto == "https":
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains; preload",
        )
    if request.url.path.startswith("/admin"):
        response.headers.setdefault("Cache-Control", "no-store, max-age=0")


@app.middleware("http")
async def platform_middleware(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get("x-request-id", "").strip()[:96] or uuid.uuid4().hex
    path = request.url.path
    ip = _client_ip(request)

    if path == "/admin/api/login" and request.method == "POST":
        retry_after = _login_retry_after(ip, time.monotonic())
        if retry_after > 0:
            response = JSONResponse(
                status_code=429,
                content={"detail": f"登录失败次数过多，请在 {retry_after} 秒后重试"},
                headers={"Retry-After": str(retry_after)},
            )
            response.headers["X-Request-ID"] = request_id
            _set_security_headers(request, response)
            return response

    if (
        path.startswith("/admin/api/")
        and path != "/admin/api/login"
        and request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and not _same_origin_allowed(request)
    ):
        response = JSONResponse(status_code=403, content={"detail": "跨站管理请求已拒绝"})
        response.headers["X-Request-ID"] = request_id
        _set_security_headers(request, response)
        return response

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        logger.exception(
            json.dumps(
                {
                    "event": "http_request_error",
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "client_ip": ip,
                    "duration_ms": duration_ms,
                },
                ensure_ascii=False,
            )
        )
        raise

    now = time.monotonic()
    if path == "/admin/api/login" and request.method == "POST":
        _record_login_result(ip, response.status_code, now)

    duration_ms = round((time.perf_counter() - started) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    response.headers.setdefault("Server-Timing", f"app;dur={duration_ms}")
    _set_security_headers(request, response)
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "client_ip": ip,
                "duration_ms": duration_ms,
            },
            ensure_ascii=False,
        )
    )
    return response


def _decode_state(key: str) -> dict[str, object] | None:
    value = database.get_state(key)
    if value is None:
        return None
    try:
        decoded = json.loads(value[0])
        if isinstance(decoded, dict):
            return decoded
        return {"value": decoded, "updated_at_epoch_ms": value[1]}
    except json.JSONDecodeError:
        return {"value": value[0], "updated_at_epoch_ms": value[1]}


def _heartbeat_detail() -> dict[str, object]:
    value = database.get_state("worker_heartbeat")
    if value is None:
        return {"status": "waiting", "fresh": False, "updated_at_epoch_ms": None}
    payload: dict[str, object]
    try:
        decoded = json.loads(value[0])
        payload = decoded if isinstance(decoded, dict) else {"value": decoded}
    except json.JSONDecodeError:
        payload = {"value": value[0]}
    now_ms = int(time.time() * 1000)
    max_age_ms = max(180_000, settings.poll_seconds * 4_000)
    fresh = now_ms - value[1] <= max_age_ms
    payload.update(
        {
            "status": "ok" if fresh else "stale",
            "fresh": fresh,
            "updated_at_epoch_ms": value[1],
            "age_ms": max(0, now_ms - value[1]),
        }
    )
    return payload


# Replace the legacy compatibility health route. Liveness remains independent from
# database and Worker readiness so Docker can restart only truly dead API processes.
app.routes[:] = [route for route in app.routes if getattr(route, "path", None) != "/health"]


@app.get("/health", include_in_schema=False)
def health_compatibility() -> dict[str, object]:
    database_ok = database.ping()
    heartbeat = _heartbeat_detail()
    ready = database_ok and bool(heartbeat.get("fresh"))
    return {
        "status": "ok" if ready else "degraded",
        "database": "ok" if database_ok else "error",
        "worker": heartbeat.get("status"),
        "version": SERVICE_VERSION,
    }


@app.get("/health/live", include_in_schema=False)
def health_live() -> dict[str, object]:
    return {"status": "ok", "version": SERVICE_VERSION}


@app.get("/health/ready", include_in_schema=False)
def health_ready():
    database_ok = database.ping()
    heartbeat = _heartbeat_detail()
    ready = database_ok and bool(heartbeat.get("fresh"))
    payload = {
        "status": "ok" if ready else "degraded",
        "database": "ok" if database_ok else "error",
        "worker": heartbeat.get("status"),
        "version": SERVICE_VERSION,
    }
    return JSONResponse(status_code=200 if ready else 503, content=payload)


@app.get(
    "/health/detail",
    dependencies=[Depends(require_admin_session)],
    include_in_schema=False,
)
def health_detail() -> dict[str, object]:
    cycles = {}
    for lottery_key in LOTTERIES:
        cycles[lottery_key] = _decode_state(f"cycle:{lottery_key}")
    database_ok = database.ping()
    heartbeat = _heartbeat_detail()
    return {
        "status": "ok" if database_ok and heartbeat.get("fresh") else "degraded",
        "database": {"ok": database_ok, "path": settings.database_path},
        "worker": heartbeat,
        "cycles": cycles,
        "backup": _decode_state("backup_status"),
        "maintenance": cleanup_runtime_state(),
        "version": SERVICE_VERSION,
    }


if not settings.docs_enabled:
    hidden_paths = {"/docs", "/docs/oauth2-redirect", "/openapi.json"}
    app.routes[:] = [route for route in app.routes if getattr(route, "path", None) not in hidden_paths]
