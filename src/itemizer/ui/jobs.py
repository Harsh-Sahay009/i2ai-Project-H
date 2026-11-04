"""One run at a time, on a background thread. The run carries on if the browser closes."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .. import pipeline
from ..bootstrap.data import ContractError


@dataclass
class Job:
    id: str
    file_name: str
    started: float
    state: str = "running"  # running, done or failed
    done: int = 0
    total: int = 0
    spent_usd: Decimal = Decimal(0)
    finished: float | None = None
    message: str = ""
    run_id: str | None = None

    def status(self) -> dict:
        elapsed = (self.finished or time.monotonic()) - self.started
        return {"state": self.state, "done": self.done, "total": self.total, "elapsed_seconds": round(elapsed), "spent_usd": f"{self.spent_usd:.2f}",
                "message": self.message, "run_id": self.run_id}


class JobBusy(ContractError):
    """A run is in progress. It names the job, so the page can link to it."""

    def __init__(self, job: Job):
        super().__init__(f"A run on {job.file_name} is in progress. Only one runs at a time.")
        self.job = job


class JobRunner:
    def __init__(self, root: Path):
        self.root = root
        self.jobs: dict[str, Job] = {}
        self.threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def start(self, path: Path, file_name: str) -> Job:
        with self._lock:
            running = next((job for job in self.jobs.values() if job.state == "running"), None)
            if running:
                raise JobBusy(running)
            job = Job(id=uuid.uuid4().hex[:12], file_name=file_name, started=time.monotonic())
            self.jobs[job.id] = job
        thread = threading.Thread(target=self._work, args=(job, path), daemon=True)
        self.threads[job.id] = thread
        thread.start()
        return job

    def _work(self, job: Job, path: Path) -> None:
        def progress(done: int, total: int, spent: Decimal) -> None:
            job.done, job.total, job.spent_usd = done, total, spent

        try:
            job.run_id = pipeline.run(self.root, export=path, progress=progress).run_id
            job.state = "done"
        except ContractError as exc:
            job.state, job.message = "failed", str(exc)
        except Exception as exc:  # its message can quote a note, so only its type is shown, as on the command line
            job.state, job.message = "failed", f"An unexpected {type(exc).__name__}. Its message is hidden because it can quote a note."
        job.finished = time.monotonic()
