from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator


class MetricsCollector:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.timings: dict[str, float] = {}
        self.data: dict[str, Any] = {"run_id": run_id, "counters": {}}

    @contextmanager
    def time(self, stage: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - started
            self.timings[stage] = round(elapsed, 3)

    def set(self, key: str, value: Any) -> None:
        self.data["counters"][key] = value

    def snapshot(self, *, status: str) -> dict[str, Any]:
        payload = dict(self.data)
        payload["status"] = status
        payload["timings_sec"] = dict(self.timings)
        payload["total_sec"] = round(sum(self.timings.values()), 3)
        return payload
