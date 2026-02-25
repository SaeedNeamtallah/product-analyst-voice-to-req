"""
Shared resilience helpers: in-memory circuit breaker and async failover execution.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Iterable, Optional, Tuple

from backend.services.runtime_metrics import record_cb_event, record_cb_open_check


class CircuitBreakerRegistry:
    """Process-local circuit breaker registry."""

    def __init__(self) -> None:
        self._state: dict[str, tuple[int, datetime | None]] = {}

    @staticmethod
    def _group(key: str) -> str:
        return str(key or "unknown").split(":", 1)[0]

    def is_open(self, key: str) -> bool:
        failures, opened_until = self._state.get(key, (0, None))
        now = datetime.now(timezone.utc)

        if opened_until and opened_until > now:
            record_cb_open_check(self._group(key), True)
            return True

        if opened_until and opened_until <= now:
            self._state[key] = (failures, None)

        record_cb_open_check(self._group(key), False)
        return False

    def record_success(self, key: str) -> None:
        self._state[key] = (0, None)
        record_cb_event(self._group(key), "success")

    def record_failure(self, key: str, threshold: int = 3, cooldown_seconds: int = 45) -> None:
        current_failures, opened_until = self._state.get(key, (0, None))
        now = datetime.now(timezone.utc)

        if opened_until and opened_until > now:
            record_cb_event(self._group(key), "failure")
            return

        failures = current_failures + 1
        if failures >= max(1, int(threshold)):
            opened_until = now + timedelta(seconds=max(1, int(cooldown_seconds)))
            record_cb_event(self._group(key), "opened")
        else:
            opened_until = None

        self._state[key] = (failures, opened_until)
        record_cb_event(self._group(key), "failure")


circuit_breakers = CircuitBreakerRegistry()


async def run_with_failover(
    providers: Iterable[Tuple[str, Callable[[], Awaitable[Any]]]],
    *,
    breaker_prefix: str,
    failure_threshold: int = 3,
    cooldown_seconds: int = 45,
) -> Tuple[Any, str]:
    """Try providers in order with circuit-breaker short-circuiting.

    Returns tuple of (result, provider_name).
    Raises RuntimeError with aggregated failure reason if all fail.
    """
    last_error: Optional[Exception] = None

    for provider_name, call in providers:
        key = f"{breaker_prefix}:{provider_name}"
        if circuit_breakers.is_open(key):
            continue
        try:
            result = await call()
            circuit_breakers.record_success(key)
            return result, provider_name
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            error_text = str(exc).lower()
            is_rate_limited = (
                "429" in error_text
                or "quota exceeded" in error_text
                or "rate limit" in error_text
                or "too many requests" in error_text
            )
            effective_threshold = 1 if is_rate_limited else failure_threshold
            effective_cooldown = max(cooldown_seconds, 180) if is_rate_limited else cooldown_seconds
            circuit_breakers.record_failure(
                key,
                threshold=effective_threshold,
                cooldown_seconds=effective_cooldown,
            )

    if last_error is None:
        raise RuntimeError("No available providers (all circuit breakers are open)")
    raise RuntimeError(f"All providers failed: {last_error}")
