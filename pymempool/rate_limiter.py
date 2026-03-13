import logging
import math
import random
import time
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class HostBudget:
    """Mutable rate-limit state for a single API host."""

    tokens: float
    last_refill_timestamp: float
    next_allowed_at: float = 0.0
    recent_429s: int = 0


class RateLimiter:
    """Conservative per-host token bucket with hard cooldown support."""

    def __init__(
        self,
        rate_limit_per_sec: float = 1.0,
        rate_limit_burst: int = 5,
        max_cooldown: float = 60.0,
        time_func: Callable[[], float] = time.monotonic,
        sleep_func: Callable[[float], None] = time.sleep,
        random_func: Callable[[float, float], float] = random.uniform,
        notifier: Optional[Callable[[str], None]] = None,
    ):
        self.rate_limit_per_sec = max(float(rate_limit_per_sec), 0.0)
        self.rate_limit_burst = max(int(rate_limit_burst), 1)
        self.max_cooldown = max(float(max_cooldown), 1.0)
        self._time_func = time_func
        self._sleep_func = sleep_func
        self._random_func = random_func
        self._notifier = notifier
        self._budgets: dict[str, HostBudget] = {}

    def wait_until_allowed(self, host: str) -> None:
        """Block until the host budget permits one outgoing request."""

        while True:
            now = self._time_func()
            budget = self._get_budget(host)
            self._refill_budget(budget, now)

            if now < budget.next_allowed_at:
                wait_seconds = budget.next_allowed_at - now
                self._notify_cooldown(host, wait_seconds)
                self._sleep(wait_seconds)
                continue

            if self.rate_limit_per_sec <= 0:
                return

            if budget.tokens >= 1:
                budget.tokens -= 1
                return

            wait_seconds = (1 - budget.tokens) / self.rate_limit_per_sec
            self._notify("Rate limited by API; slowing requests.")
            logger.debug("Waiting %.3fs for host %s token refill", wait_seconds, host)
            self._sleep(wait_seconds)

    def punish_429(
        self, host: str, retry_after: Optional[float] = None, attempt: int = 1
    ) -> float:
        """Apply a hard cooldown after a 429 response and return its duration."""

        now = self._time_func()
        budget = self._get_budget(host)
        budget.recent_429s += 1
        penalty_level = max(int(attempt), budget.recent_429s)

        if retry_after is not None and retry_after >= 0:
            cooldown = min(float(retry_after), self.max_cooldown)
        else:
            base = min(float(2 ** max(penalty_level - 1, 0)), self.max_cooldown)
            cooldown = min(
                self.max_cooldown,
                (base / 2.0) + self._random_func(0.0, base / 2.0),
            )

        budget.next_allowed_at = max(budget.next_allowed_at, now + cooldown)
        budget.tokens = 0.0
        self._notify_cooldown(host, cooldown)
        logger.debug(
            "Applied %.3fs cooldown to host %s after 429 (retry_after=%s, attempts=%s)",
            cooldown,
            host,
            retry_after,
            penalty_level,
        )
        return cooldown

    def record_success(self, host: str) -> None:
        """Reset host penalty state after a successful response."""

        budget = self._get_budget(host)
        budget.recent_429s = 0
        now = self._time_func()
        if budget.next_allowed_at <= now:
            budget.next_allowed_at = 0.0

    def pick_host(
        self, hosts: Sequence[str], excluded_hosts: Optional[Collection[str]] = None
    ) -> str:
        """Choose the next host, waiting for the earliest cooldown if necessary."""

        excluded = set(excluded_hosts or [])
        candidates = [host for host in hosts if host not in excluded]
        if not candidates:
            raise ValueError("No candidate hosts available")

        now = self._time_func()
        for host in candidates:
            if self.get_next_allowed_at(host) <= now:
                return host

        host = min(candidates, key=self.get_next_allowed_at)
        wait_seconds = max(self.get_next_allowed_at(host) - now, 0.0)
        self._notify_cooldown(host, wait_seconds)
        logger.debug("All hosts cooling down; waiting %.3fs for %s", wait_seconds, host)
        self._sleep(wait_seconds)
        return host

    def get_next_allowed_at(self, host: str) -> float:
        """Return the host cooldown timestamp."""

        return self._get_budget(host).next_allowed_at

    def get_budget(self, host: str) -> HostBudget:
        """Return the mutable budget for inspection and testing."""

        return self._get_budget(host)

    def now(self) -> float:
        """Return the limiter clock value."""

        return self._time_func()

    def _get_budget(self, host: str) -> HostBudget:
        now = self._time_func()
        budget = self._budgets.get(host)
        if budget is None:
            budget = HostBudget(
                tokens=float(self.rate_limit_burst),
                last_refill_timestamp=now,
            )
            self._budgets[host] = budget
        return budget

    def _refill_budget(self, budget: HostBudget, now: float) -> None:
        if self.rate_limit_per_sec <= 0:
            budget.tokens = float(self.rate_limit_burst)
            budget.last_refill_timestamp = now
            return

        elapsed = max(now - budget.last_refill_timestamp, 0.0)
        if elapsed <= 0:
            return

        budget.tokens = min(
            float(self.rate_limit_burst),
            budget.tokens + (elapsed * self.rate_limit_per_sec),
        )
        budget.last_refill_timestamp = now

    def _notify(self, message: str) -> None:
        if self._notifier is not None:
            self._notifier(message)

    def _notify_cooldown(self, host: str, wait_seconds: float) -> None:
        rounded = max(1, int(math.ceil(wait_seconds))) if wait_seconds > 0 else 0
        self._notify(
            f"Cooling down for {rounded}s before retrying host {host}."
            if rounded
            else f"Cooling down for 0s before retrying host {host}."
        )

    def _sleep(self, wait_seconds: float) -> None:
        if wait_seconds <= 0:
            return
        self._sleep_func(wait_seconds)
