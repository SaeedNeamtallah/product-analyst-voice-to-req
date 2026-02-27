"""
Shared resilience helpers: in-memory circuit breaker and async failover execution.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Iterable, Optional, Tuple

import httpx

from backend.services.runtime_metrics import record_cb_event, record_cb_open_check
from telegram_bot.config import bot_settings

async def _send_telegram_alert(message: str) -> None:
    """Send an alert to the Telegram admin if configured."""
    token = bot_settings.telegram_bot_token
    admin_id = bot_settings.telegram_admin_id
    if not token or not admin_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        async with httpx.AsyncClient() as client:
            await client.post(
                url,
                json={"chat_id": admin_id, "text": f"⚠️ Tawasul Alert:\n{message}"},
                timeout=5.0,
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to send Telegram alert: {e}")


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
            
            # Fire an alert in the background
            alert_msg = f"Circuit breaker OPENED for: {key}\nFailures: {failures}\nCooldown: {cooldown_seconds}s"
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_send_telegram_alert(alert_msg))
            except RuntimeError:
                pass # Not running in an async loop or no loop available
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
