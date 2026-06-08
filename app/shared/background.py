"""
Background task manager with cross-process persistence.

Uses a JSON file (fcntl-locked) so all uvicorn workers share the same tasks.
"""

import json
import os
import fcntl
import uuid
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable

TASKS_FILE = os.getenv("TASKS_FILE", "/tmp/chauchaapp_tasks.json")


def _now() -> str:
    return datetime.utcnow().isoformat()


class BackgroundTaskManager:
    """Thread-safe + process-safe task tracker backed by a JSON file."""

    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._load()

    # ------------------------------------------------------------------
    # File I/O with fcntl locking (cross-process safe on Linux)
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            with open(TASKS_FILE, "r") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                self._cache = json.load(f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (FileNotFoundError, json.JSONDecodeError):
            self._cache = {}

    def _flush(self) -> None:
        os.makedirs(os.path.dirname(TASKS_FILE) or ".", exist_ok=True)
        with open(TASKS_FILE, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(self._cache, f, indent=2)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _lazy_cleanup(self) -> None:
        cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        self._cache = {
            tid: t
            for tid, t in self._cache.items()
            if t.get("completed_at") is None or t["completed_at"] > cutoff
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_task(self, task_type: str, user_id: str | None = None) -> str:
        task_id = str(uuid.uuid4())
        entry = {
            "task_id": task_id,
            "status": "pending",
            "task_type": task_type,
            "user_id": user_id,
            "created_at": _now(),
            "completed_at": None,
            "result": None,
            "error": None,
        }
        with self._lock:
            self._cache[task_id] = entry
            self._lazy_cleanup()
            self._flush()
        return task_id

    def update_status(self, task_id: str, status: str, **kwargs: Any) -> None:
        with self._lock:
            if task_id in self._cache:
                self._cache[task_id]["status"] = status
                self._cache[task_id].update(kwargs)
                if status in ("completed", "failed"):
                    self._cache[task_id]["completed_at"] = _now()
                self._flush()

    def get_task(self, task_id: str) -> dict | None:
        with self._lock:
            self._load()
            task = self._cache.get(task_id)
            return dict(task) if task else None

    def get_user_tasks(
        self, user_id: str, task_type: str | None = None
    ) -> list[dict]:
        with self._lock:
            self._load()
            return [
                dict(t)
                for t in self._cache.values()
                if t["user_id"] == user_id
                and (task_type is None or t["task_type"] == task_type)
            ]

    def run_in_background(
        self, task_id: str, fn: Callable, *args: Any, **kwargs: Any
    ) -> None:
        """Execute fn in a daemon thread, updating task status automatically.

        Handles both sync and async functions. For async functions, creates
        a dedicated event loop in the thread.
        """
        def wrapper() -> None:
            try:
                if asyncio.iscoroutinefunction(fn):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(fn(*args, **kwargs))
                    finally:
                        loop.close()
                else:
                    result = fn(*args, **kwargs)
                self.update_status(task_id, "completed", result=result)
            except Exception as e:
                self.update_status(task_id, "failed", error=str(e))

        self.update_status(task_id, "processing")
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()


task_manager = BackgroundTaskManager()
