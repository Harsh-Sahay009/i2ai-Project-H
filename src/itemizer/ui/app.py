"""The local page. Every action calls a function the command line also uses, so the page holds no business logic.

It has no login, so it serves this machine only: `itemizer ui` binds to 127.0.0.1, and the middleware refuses another site's Host
or Origin, so a web page open in the same browser cannot start a paid run.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import acceptance, kpi, pipeline
from ..bootstrap.data import ContractError, load_config
from .jobs import JobBusy, JobRunner

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # ui.max_upload_mb in the catalog; a constant until add-configuration-registry
_LOCAL_HOSTS = ("127.0.0.1", "localhost")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_RECENT_RUNS = 10


def _host_name(value: str) -> str:
    return value.rsplit(":", 1)[0].strip("[]") if value else ""


def create_app(root: Path) -> FastAPI:
    app = FastAPI(title="Freight Invoice Itemizer", docs_url=None, redoc_url=None, openapi_url=None)
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
    runner = JobRunner(root)
    app.state.runner = runner
    data_root = root / load_config(root / pipeline.CONFIG).data_root
    uploads = data_root / "uploads"

    def page(request: Request, name: str, status_code: int = 200, **context) -> HTMLResponse:
        return templates.TemplateResponse(request, name, context, status_code=status_code)

    def names() -> dict[str, str]:
        path = uploads / "index.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def upload_path(sha256: str) -> Path:
        if not _SHA256.fullmatch(sha256):
            raise ContractError("That is not an uploaded file.")
        path = uploads / f"{sha256}.xlsx"
        if not path.is_file():
            raise ContractError("That file has not been uploaded.")
        return path

    @app.middleware("http")
    async def this_machine_only(request: Request, call_next):
        if _host_name(request.headers.get("host", "")) not in _LOCAL_HOSTS:
            return PlainTextResponse("This page serves this machine only.", status_code=400)
        if request.method == "POST" and urlparse(request.headers.get("origin", "")).hostname not in _LOCAL_HOSTS:
            return PlainTextResponse("This page only takes requests from itself.", status_code=403)
        return await call_next(request)

    @app.exception_handler(JobBusy)
    async def busy(request: Request, exc: JobBusy):
        return page(request, "error.html", 409, message=str(exc), job_id=exc.job.id)

    @app.exception_handler(ContractError)
    async def stopped(request: Request, exc: ContractError):
        return page(request, "error.html", 400, message=str(exc))

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        return page(request, "error.html", 500, message=f"An unexpected {type(exc).__name__}. Its message is hidden because it can quote a note.")

    def recent_runs() -> list[dict]:
        known = names()
        lines = []
        folders = [path.parent for path in (data_root / "runs").glob("run_*/row_results.json")]
        for folder in sorted(folders, key=lambda path: (path / "row_results.json").stat().st_mtime_ns, reverse=True)[:_RECENT_RUNS]:
            try:
                manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
                rows = json.loads((folder / "row_results.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            lines.append({"run_id": folder.name, "file": known.get(manifest.get("dataset_sha256"), "the dataset file"), "set": manifest.get("set_name"),
                          "rows": len(rows), "outcomes": dict(sorted(collections.Counter(row["outcome"] for row in rows).items()))})
        return lines

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return page(request, "home.html", runs=recent_runs(), max_mb=MAX_UPLOAD_BYTES // (1024 * 1024))

    @app.post("/uploads")
    async def upload(file: UploadFile | None = None):
        if file is None or not file.filename:
            raise ContractError("Choose a file first.")
        if not file.filename.lower().endswith(".xlsx"):
            raise ContractError("Only .xlsx files can be uploaded.")
        uploads.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        handle, temp = tempfile.mkstemp(dir=uploads, suffix=".part")
        size = 0
        try:
            with os.fdopen(handle, "wb") as stream:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise ContractError(f"That file is over the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")
                    digest.update(chunk)
                    stream.write(chunk)
            sha256 = digest.hexdigest()
            os.replace(temp, uploads / f"{sha256}.xlsx")  # named by its content, so a file name never reaches a path
        finally:
            Path(temp).unlink(missing_ok=True)
        known = names()
        known[sha256] = file.filename
        (uploads / "index.json").write_text(json.dumps(known, sort_keys=True), encoding="utf-8")
        return RedirectResponse(f"/uploads/{sha256}", status_code=303)

    @app.get("/uploads/{sha256}", response_class=HTMLResponse)
    def precheck(request: Request, sha256: str):
        path = upload_path(sha256)
        return page(request, "precheck.html", sha256=sha256, file_name=names().get(sha256, "this file"), report=pipeline.inspect_export(root, path))

    @app.post("/uploads/{sha256}/run")
    def start_run(sha256: str):
        path = upload_path(sha256)
        report = pipeline.inspect_export(root, path)  # a disabled button is not a check
        if report["stops"]:
            raise ContractError(report["stops"][0])
        job = runner.start(path, names().get(sha256, "this file"))
        return RedirectResponse(f"/jobs/{job.id}", status_code=303)

    def job_of(job_id: str):
        job = runner.jobs.get(job_id)
        if job is None:
            raise ContractError("That run is not known. The list of runs is on the home page.")
        return job

    @app.get("/jobs/{job_id}", response_class=HTMLResponse)
    def job_page(request: Request, job_id: str):
        job = job_of(job_id)
        return page(request, "job.html", job=job)

    @app.get("/jobs/{job_id}/status")
    def job_status(job_id: str):
        return JSONResponse(job_of(job_id).status())

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def run_page(request: Request, run_id: str):
        manifest, rows, notes = pipeline.read_run(data_root, run_id)
        outcomes = dict(sorted(collections.Counter(row.outcome for row in rows).items()))
        reasons = dict(sorted(collections.Counter(row.outcome_reason for row in rows).items()))
        whole_dataset = manifest.split_sha256 is not None and manifest.set_name == "all" and manifest.limit is None
        snapshot = None
        path = kpi.snapshot_path(data_root, run_id, "d3")
        if whole_dataset and path.exists():
            stored = json.loads(path.read_text(encoding="utf-8"))
            if stored["results_sha256"] == kpi.results_digest(notes):  # a score on other answers is not this run's
                snapshot = stored
        return page(request, "run.html", run_id=run_id, model=manifest.model.get("name"), rows=len(rows), outcomes=outcomes, reasons=reasons,
                    coverage=kpi.coverage(rows), whole_dataset=whole_dataset, snapshot=snapshot, file=names().get(manifest.dataset_sha256, "the dataset file"))

    @app.post("/runs/{run_id}/evaluate")
    def score(run_id: str):
        pipeline.evaluate_run(root, run_id)  # --extra-peek stays on the command line, so it is never one click
        return RedirectResponse(f"/runs/{run_id}", status_code=303)

    @app.get("/runs/{run_id}/download")
    def download(run_id: str):
        pipeline.read_run(data_root, run_id)  # checks the id's pattern before any path is built from it
        return FileResponse(data_root / "runs" / run_id / "itemized.xlsx", media_type=_XLSX, filename=f"itemized_{run_id}.xlsx")

    @app.get("/status", response_class=HTMLResponse)
    def status_page():
        summary = acceptance.d3_check(root)
        text = Path(summary["page"]).read_text(encoding="utf-8")
        return HTMLResponse(text.replace("<body>", "<body><p><a href='/'>Back to upload</a></p>", 1))

    return app
