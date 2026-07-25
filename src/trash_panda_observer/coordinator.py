"""Trigger admission and cooldown policy."""

import queue
import time


class EventCoordinator:
    def __init__(self, maximum_pending: int, cooldown_seconds: float) -> None:
        if maximum_pending < 1:
            raise ValueError("maximum_pending must be positive")
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds cannot be negative")
        self.events: queue.Queue[dict] = queue.Queue(maxsize=maximum_pending)
        self.cooldown_seconds = cooldown_seconds
        self.active = False
        self.last_completed = float("-inf")

    def submit(self, event: dict, now: float | None = None) -> str:
        current = time.monotonic() if now is None else now
        if self.active:
            return "burst_active"
        if current - self.last_completed < self.cooldown_seconds:
            return "cooldown"
        try:
            self.events.put_nowait(event)
        except queue.Full:
            return "queue_full"
        return "accepted"

    def begin(self) -> dict:
        event = self.events.get_nowait()
        self.active = True
        return event

    def complete(self, now: float | None = None) -> None:
        self.last_completed = time.monotonic() if now is None else now
        self.active = False
        self.events.task_done()
