"""Thread-safe sliding-window rate limiter.

Allows at most ``max_requests`` per ``window_seconds`` for each key. The key is
an agent id in the kernel and a client address in the HTTP server. The clock is
injectable so behaviour can be tested without sleeping.
"""

import math
import threading
import time
from collections import deque
from typing import Callable, Deque, Dict, Tuple


class RateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 50000,
    ):
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.max_requests = max_requests
        self.window_seconds = float(window_seconds)
        self._clock = clock
        self._max_keys = max_keys
        self._lock = threading.Lock()
        self._events: Dict[str, Deque[float]] = {}

    def check(self, key: str) -> Tuple[bool, int]:
        """Record an attempt for ``key``.

        Returns ``(allowed, retry_after_ms)``. When ``allowed`` is False the
        attempt is not counted and ``retry_after_ms`` says how long until the
        oldest request in the window expires.
        """
        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= self.max_requests:
                retry_after = events[0] + self.window_seconds - now
                return False, max(1, int(math.ceil(retry_after * 1000)))

            events.append(now)
            if len(self._events) > self._max_keys:
                self._evict(cutoff)
            return True, 0

    def _evict(self, cutoff: float) -> None:
        stale = [
            key
            for key, events in self._events.items()
            if not events or events[-1] <= cutoff
        ]
        for key in stale:
            del self._events[key]
