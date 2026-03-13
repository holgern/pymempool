import copy
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_MISSING = object()


@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    stored_at: float


class ResponseCache:
    """Small TTL cache with same-key request coalescing."""

    def __init__(
        self,
        ttl_seconds: float = 3.0,
        time_func: Callable[[], float] = time.monotonic,
        notifier: Optional[Callable[[str], None]] = None,
    ):
        self.ttl_seconds = max(float(ttl_seconds), 0.0)
        self._time_func = time_func
        self._notifier = notifier
        self._entries: dict[str, CacheEntry] = {}
        self._inflight: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def get(self, key: str, allow_stale: bool = False) -> Any:
        """Return a cached value when one is available."""

        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                logger.debug("Cache miss for %s", key)
                return _MISSING

            now = self._time_func()
            if allow_stale or entry.expires_at > now:
                logger.debug(
                    "Cache hit for %s (%s)",
                    key,
                    "stale" if allow_stale and entry.expires_at <= now else "fresh",
                )
                return copy.deepcopy(entry.value)

            logger.debug("Cache expired for %s", key)
            return _MISSING

    def set(self, key: str, value: Any) -> None:
        """Store a cached response."""

        now = self._time_func()
        with self._lock:
            self._entries[key] = CacheEntry(
                value=copy.deepcopy(value),
                expires_at=now + self.ttl_seconds,
                stored_at=now,
            )

    def get_or_load(self, key: str, loader: Callable[[], Any]) -> Any:
        """Load once per key when multiple callers arrive concurrently."""

        cached = self.get(key)
        if cached is not _MISSING:
            return cached

        event, is_owner = self._acquire_inflight(key)
        if not is_owner:
            event.wait()
            cached = self.get(key)
            if cached is not _MISSING:
                return cached
            stale = self.get(key, allow_stale=True)
            if stale is not _MISSING:
                return stale

        try:
            value = loader()
            self.set(key, value)
            return copy.deepcopy(value)
        finally:
            self._release_inflight(key, event)

    def get_stale(self, key: str) -> Any:
        """Return a stale cached value when present."""

        return self.get(key, allow_stale=True)

    def notify_cached_snapshot(self) -> None:
        """Emit a compact user-facing cache notice."""

        if self._notifier is not None:
            self._notifier("Using cached snapshot while upstream rate limit clears.")

    def _acquire_inflight(self, key: str) -> tuple[threading.Event, bool]:
        with self._lock:
            existing = self._inflight.get(key)
            if existing is not None:
                logger.debug("Waiting on inflight request for %s", key)
                return existing, False

            event = threading.Event()
            self._inflight[key] = event
            return event, True

    def _release_inflight(self, key: str, event: threading.Event) -> None:
        with self._lock:
            current = self._inflight.get(key)
            if current is event:
                event.set()
                del self._inflight[key]


__all__ = ["ResponseCache", "_MISSING"]
