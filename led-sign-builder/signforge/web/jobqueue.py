"""Priority job queue: premium ahead of free, FIFO within a class, worker
pool, live positions, cooperative cancellation (checked between pipeline
stages via the progress callback)."""

from __future__ import annotations

import heapq
import itertools
import threading
import traceback
from pathlib import Path
from typing import Callable, Optional

from ..params import SignParams
from ..verify import BuildError


class JobCancelled(Exception):
    pass


class JobQueue:
    def __init__(self, workdir: Path, workers: int = 2, on_change: Optional[Callable] = None):
        self.workdir = workdir
        self.jobs: dict[str, dict] = {}
        self._heap: list[tuple[int, int, str]] = []
        self._seq = itertools.count()
        self._cv = threading.Condition()
        self._on_change = on_change
        self._threads = [
            threading.Thread(target=self._worker, daemon=True, name=f"sf-worker-{i}")
            for i in range(workers)
        ]
        for t in self._threads:
            t.start()

    # ---- submission / inspection --------------------------------------------
    def submit(self, job_id: str, params: SignParams, user: dict, priority: int) -> None:
        job = {
            "id": job_id,
            "user_id": user["id"],
            "user": user["email"],
            "name": params.name,
            "params": params,
            "status": "queued",
            "priority": priority,
            "progress": [],
            "cancel": False,
            "outdir": None,
            "zip": None,
            "stats": None,
            "warnings": [],
            "error": None,
        }
        with self._cv:
            self.jobs[job_id] = job
            heapq.heappush(self._heap, (priority, next(self._seq), job_id))
            self._cv.notify()

    def position(self, job_id: str) -> Optional[int]:
        with self._cv:
            queued = sorted(
                (p, s, jid) for (p, s, jid) in self._heap
                if self.jobs.get(jid, {}).get("status") == "queued"
            )
            for i, (_, _, jid) in enumerate(queued):
                if jid == job_id:
                    return i + 1
        return None

    def active_count(self, user_id: Optional[int] = None) -> int:
        with self._cv:
            return sum(
                1
                for j in self.jobs.values()
                if j["status"] in ("queued", "running")
                and (user_id is None or j["user_id"] == user_id)
            )

    def cancel(self, job_id: str) -> bool:
        with self._cv:
            job = self.jobs.get(job_id)
            if not job or job["status"] not in ("queued", "running"):
                return False
            job["cancel"] = True
            if job["status"] == "queued":
                job["status"] = "cancelled"
                job["progress"].append("cancelled while queued")
                self._notify(job)
        return True

    def public(self, job: dict) -> dict:
        out = {k: v for k, v in job.items() if k in
               ("id", "name", "status", "progress", "stats", "warnings", "error", "user")}
        if job["status"] == "queued":
            out["position"] = self.position(job["id"])
        return out

    # ---- worker ---------------------------------------------------------------
    def _notify(self, job: dict) -> None:
        if self._on_change:
            try:
                self._on_change(job)
            except Exception:
                pass

    def _worker(self) -> None:
        from ..pipeline import build

        while True:
            with self._cv:
                while not self._heap:
                    self._cv.wait()
                _, _, job_id = heapq.heappop(self._heap)
                job = self.jobs.get(job_id)
                if not job or job["status"] != "queued":
                    continue
                job["status"] = "running"
            self._notify(job)

            def progress(msg: str, job=job) -> None:
                if job["cancel"]:
                    raise JobCancelled()
                job["progress"].append(msg)

            try:
                outdir = self.workdir / job_id
                result = build(job["params"], outdir, progress=progress)
                job.update(
                    status="done",
                    outdir=str(outdir),
                    stats=result.stats,
                    warnings=result.warnings,
                    zip=next((f for f in result.files if f.endswith(".zip")), None),
                )
            except JobCancelled:
                job["status"] = "cancelled"
                job["progress"].append("cancelled")
            except BuildError as e:
                job.update(status="error", error=str(e))
            except Exception as e:  # pragma: no cover — defensive
                job.update(status="error", error=f"internal: {e}\n{traceback.format_exc(limit=4)}")
            self._notify(job)
