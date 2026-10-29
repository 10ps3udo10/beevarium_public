"""Limites anti-abus en memoire pour les endpoints anonymes.

La beta utilise un seul processus Uvicorn. Cette protection est donc efficace
pour cette topologie, mais doit etre completee par une limite au proxy avant
un passage a plusieurs replicas.
"""

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, *, limit: int, window: timedelta) -> bool:
        if not self.check(key, limit=limit, window=window):
            return False
        self.record(key)
        return True

    def check(self, key: str, *, limit: int, window: timedelta) -> bool:
        now = datetime.now(UTC)
        threshold = now - window
        with self._lock:
            events = self._events[key]
            while events and events[0] <= threshold:
                events.popleft()
            return len(events) < limit

    def record(self, key: str) -> None:
        with self._lock:
            self._events[key].append(datetime.now(UTC))


anonymous_limiter = SlidingWindowLimiter()
