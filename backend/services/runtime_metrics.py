"""
Runtime Prometheus metrics for Redis-backed distributed state.
"""
from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram

    _metrics_enabled = True

    _redis_up = Gauge(
        "tawasul_redis_up",
        "Whether Redis runtime connection is up (1) or down (0)",
    )
    _redis_unavailable_total = Counter(
        "tawasul_redis_runtime_unavailable_total",
        "Number of Redis runtime unavailability events",
        ["reason"],
    )
    _redis_lock_acquire_total = Counter(
        "tawasul_redis_lock_acquire_total",
        "Distributed lock acquisition attempts",
        ["namespace", "result"],
    )
    _redis_lock_wait_seconds = Histogram(
        "tawasul_redis_lock_wait_seconds",
        "Wait time for lock coalescing paths",
        ["namespace"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
    )
    _circuit_breaker_open_checks_total = Counter(
        "tawasul_circuit_breaker_open_checks_total",
        "Circuit breaker open-check outcomes",
        ["group", "is_open"],
    )
    _circuit_breaker_events_total = Counter(
        "tawasul_circuit_breaker_events_total",
        "Circuit breaker state transition events",
        ["group", "event"],
    )
    _srs_snapshot_source_total = Counter(
        "tawasul_srs_snapshot_source_total",
        "Source used to return SRS snapshot",
        ["source"],
    )
    _srs_snapshot_lock_contention_total = Counter(
        "tawasul_srs_snapshot_lock_contention_total",
        "Number of SRS snapshot lock-contention events",
    )
    _srs_snapshot_wait_seconds = Histogram(
        "tawasul_srs_snapshot_wait_seconds",
        "Wait time while coalescing SRS snapshot cache misses",
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    )
except Exception:  # noqa: BLE001
    _metrics_enabled = False


def _safe_group(group: str) -> str:
    g = str(group or "unknown").strip().lower()
    return g if g else "unknown"


def set_redis_up(is_up: bool) -> None:
    if not _metrics_enabled:
        return
    _redis_up.set(1 if is_up else 0)


def record_redis_unavailable(reason: str) -> None:
    if not _metrics_enabled:
        return
    _redis_unavailable_total.labels(reason=_safe_group(reason)).inc()


def record_redis_lock_attempt(namespace: str, acquired: bool) -> None:
    if not _metrics_enabled:
        return
    _redis_lock_acquire_total.labels(
        namespace=_safe_group(namespace),
        result="acquired" if acquired else "contended",
    ).inc()


def observe_redis_lock_wait(namespace: str, seconds: float) -> None:
    if not _metrics_enabled:
        return
    _redis_lock_wait_seconds.labels(namespace=_safe_group(namespace)).observe(max(0.0, float(seconds)))


def record_cb_open_check(group: str, is_open: bool) -> None:
    if not _metrics_enabled:
        return
    _circuit_breaker_open_checks_total.labels(
        group=_safe_group(group),
        is_open="true" if is_open else "false",
    ).inc()


def record_cb_event(group: str, event: str) -> None:
    if not _metrics_enabled:
        return
    _circuit_breaker_events_total.labels(
        group=_safe_group(group),
        event=_safe_group(event),
    ).inc()


def record_snapshot_source(source: str) -> None:
    if not _metrics_enabled:
        return
    _srs_snapshot_source_total.labels(source=_safe_group(source)).inc()


def record_snapshot_lock_contention() -> None:
    if not _metrics_enabled:
        return
    _srs_snapshot_lock_contention_total.inc()


def observe_snapshot_wait(seconds: float) -> None:
    if not _metrics_enabled:
        return
    _srs_snapshot_wait_seconds.observe(max(0.0, float(seconds)))
