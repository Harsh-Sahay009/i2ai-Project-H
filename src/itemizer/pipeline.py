"""From an export to an itemized workbook, and from a finished run to its Level gates."""
from __future__ import annotations

import collections
import dataclasses
import hashlib
import json
import re
import subprocess
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from . import kpi
from .bootstrap import labels as lb
from .bootstrap import split as sp
from .bootstrap import taxonomy as tx
from .bootstrap.data import (
    Config, ContractError, DisputeRow, Note, Workspace, fingerprint, group_notes, load_config, load_export, sha256_file,
)
from .contracts import NoteResult, RowResult, RunManifest
from .grammar import GRAMMAR_VERSION
from .itemize import Budget, Policy, assign_rows, build_system_prompt, itemize_notes, load_fewshots
from .output import write_workbook
from .providers import ModelSpec, get_provider, load_models

CONFIG = Path("config/bootstrap.yaml")
SETTINGS = Path("config/run.yaml")
MODELS = Path("config/models.yaml")
CATEGORIES = Path("taxonomy/categories.yaml")
APPROVAL = Path("taxonomy/approval.yaml")
PROMPT = Path("prompts/itemize_v1.md")
FEWSHOTS = Path("prompts/fewshot_v1.yaml")
SETS = {"train": "TRAIN", "validation": "VALIDATION"}
_RUN_ID = re.compile(r"run_[0-9a-f]{16}")


@dataclasses.dataclass
class Project:
    """The settings, the dataset file and the split that every command here works from."""

    root: Path
    cfg: Config
    ws: Workspace
    settings: dict
    dataset: Path
    rows: list[DisputeRow]
    notes: dict[str, Note]
    split: dict

    @property
    def data_root(self) -> Path:
        return self.root / self.cfg.data_root

    def categories(self) -> list[dict]:
        taxonomy = tx.load_taxonomy(self.root / CATEGORIES)
        problems = tx.validate_taxonomy(taxonomy, self.notes)
        if problems:
            raise ContractError("the taxonomy has problems: " + "; ".join(problems))
        return taxonomy["categories"]


def load_settings(root: Path) -> dict:
    path = root / SETTINGS
    if not path.exists():
        raise ContractError(f"settings not found: {SETTINGS}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_project(root: Path) -> Project:
    cfg = load_config(root / CONFIG)
    ws = Workspace(cfg, root)
    dataset = root / cfg.source_file
    if not dataset.exists():
        raise ContractError(f"dataset file not found: {cfg.source_file}")
    rows, _ = load_export(dataset, cfg.examples_sheet)
    split = ws.read_json("split_manifest.json")
    if split["dataset_sha256"] != sha256_file(dataset):
        raise ContractError("the dataset file changed after the split was made")
    return Project(root, cfg, ws, load_settings(root), dataset, rows, group_notes(rows, cfg.large_dispute_usd), split)


def choose_model(root: Path, name: str | None) -> ModelSpec:
    specs, default = load_models(root / MODELS)
    name = name or default
    if name not in specs:
        raise ContractError(f"model {name!r} is not in {MODELS}; available: {', '.join(sorted(specs))}")
    return specs[name]


def _code_identity(root: Path) -> tuple[str, str, bool]:
    """A hash of the source and lockfile, then the commit and whether the tree is clean. Only the hash is in the run's id,
    so a commit touching nothing else gives the same run and the same workbook."""
    digest = hashlib.sha256()
    package = Path(__file__).resolve().parent
    for path in sorted(package.rglob("*.py")):
        digest.update(path.relative_to(package).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    lock = root / "uv.lock"
    if lock.exists():
        digest.update(lock.read_bytes())
    code_sha = digest.hexdigest()

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)

    head = git("rev-parse", "--short", "HEAD")
    if head.returncode != 0:
        return code_sha, "no-git", False
    return code_sha, head.stdout.strip(), bool(git("status", "--porcelain", "--", "src", "prompts", "config").stdout.strip())


def _select(project: Project, rows: list[DisputeRow], notes: dict[str, Note], is_dataset: bool, set_name: str | None,
            limit: int | None) -> tuple[list[DisputeRow], dict[str, Note]]:
    """Which rows and notes this run may touch. Labellers must never see tool output on TEST notes."""
    if limit is not None and limit < 1:
        raise ContractError("--limit must be at least 1")
    if limit is not None and set_name is None:
        raise ContractError("--limit needs --set: a Level gate needs a run on all rows, and another export runs whole")
    if set_name is not None and set_name not in SETS:
        raise ContractError(f"--set must be one of {', '.join(sorted(SETS))}. TEST is never a development set.")
    if set_name is not None and not is_dataset:
        raise ContractError("--set applies to the dataset file only")
    if not lb.is_test_frozen(project.ws):
        if is_dataset and set_name is None:
            raise ContractError("a run on all rows waits until TEST is frozen, so labellers never see tool output on TEST "
                                "notes. Use --set train or --set validation until then.")
        held_back = set(sp.notes_in_set(project.split, "TEST") + sp.notes_in_set(project.split, "RESERVE"))
        overlap = 0 if is_dataset else sum(fp in held_back for fp in notes)
        if overlap:  # otherwise a copy of the file under another hash would get round the rule
            raise ContractError(f"this export holds {overlap} notes held back for TEST. It cannot run until TEST is frozen.")
    if set_name is None:
        return rows, notes
    chosen = sorted(sp.notes_in_set(project.split, SETS[set_name]))[:limit]
    wanted = set(chosen)
    return [r for r in rows if r.note.strip() and fingerprint(r.note) in wanted], {fp: notes[fp] for fp in chosen}


def _left_out_of_send(project: Project, spec: ModelSpec, notes: dict[str, Note], is_dataset: bool) -> set[str]:
    """Notes that may not leave this machine. A local model sends nothing out, so nothing is left out for it."""
    if spec.provider == "ollama":
        return set()
    left_out = sp.check_external_send(project.ws)
    if not is_dataset:  # the recorded scan and decision cover the dataset file, and not this one
        flagged = sp.scan(notes)["notes_flagged"]
        if flagged:
            raise ContractError(f"the scan flagged {flagged} notes in this export, which is not the cleared dataset file. "
                                "Nothing was sent. Use a local model, or clean the export.")
    return left_out


def _budget(settings: dict) -> Budget:
    """Missing limits stop the run: treating them as zero would send every note to Review without saying why."""
    try:
        limits = settings["budget"]
        return Budget(limits["max_usd_per_run"], limits["max_minutes_per_run"])
    except (KeyError, TypeError):
        raise ContractError("the run settings need budget.max_usd_per_run and budget.max_minutes_per_run") from None


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def _config_sha(project: Project, left_out: set[str]) -> str:
    """The settings that decide a run's results, and which notes the scan decision keeps back. A budget or a concurrency
    changes how a run goes, and not what a finished answer says, so lowering either keeps the run's identity."""
    deciding = {key: value for key, value in project.settings.items() if key not in ("budget", "runtime")}
    config = json.dumps([deciding, str(project.cfg.large_dispute_usd), sorted(left_out)], sort_keys=True, default=str)
    return hashlib.sha256(config.encode("utf-8")).hexdigest()


def _manifest(project: Project, spec: ModelSpec, export: Path, set_name: str | None, limit: int | None, system: str,
              left_out: set[str]) -> RunManifest:
    is_dataset = sha256_file(export) == project.split["dataset_sha256"]
    code_sha, commit, dirty = _code_identity(project.root)
    return RunManifest(
        dataset_sha256=sha256_file(export),
        set_name=set_name or "all",
        limit=limit,
        taxonomy_sha256=sha256_file(project.root / CATEGORIES),
        prompt_sha256=hashlib.sha256(system.encode("utf-8")).hexdigest(),
        fewshot_sha256=sha256_file(project.root / FEWSHOTS),
        grammar_version=GRAMMAR_VERSION,
        model=spec.model_dump(mode="json"),
        config_sha256=_config_sha(project, left_out),
        code_sha=code_sha,
        code_commit=commit,
        code_dirty=dirty,
        split_sha256=hashlib.sha256(json.dumps(project.split["notes"], sort_keys=True).encode("utf-8")).hexdigest() if is_dataset else None,
    )


@dataclasses.dataclass
class RunOutcome:
    run_id: str
    folder: Path
    workbook: Path
    rows: int
    notes: int
    outcomes: dict[str, int]
    reasons: dict[str, int]
    new_calls_usd: Decimal
    measured_usd: Decimal
    minutes: float
    cached_notes: int
    coverage: dict
    manifest: RunManifest
    note_results: dict[str, NoteResult]
    row_results: list[RowResult]


def run(root: Path, model_name: str | None = None, set_name: str | None = None, limit: int | None = None,
        export: Path | None = None) -> RunOutcome:
    """Itemize an export. Every file goes under the run's folder, named by a hash of everything the run depends on."""
    project = load_project(root)
    spec = choose_model(root, model_name)
    path = Path(export) if export else project.dataset
    if not path.exists():
        raise ContractError(f"export not found: {path}")
    is_dataset = sha256_file(path) == project.split["dataset_sha256"]  # by content, so a copy under another name counts
    if is_dataset:
        rows, notes = project.rows, project.notes
    else:
        rows, _ = load_export(path, project.cfg.examples_sheet)
        notes = group_notes(rows, project.cfg.large_dispute_usd)
    rows, notes = _select(project, rows, notes, is_dataset, set_name, limit)
    if not rows:
        raise ContractError("there are no rows to run")

    categories = project.categories()
    codes = {c["code"] for c in categories}
    fewshots = load_fewshots(root / FEWSHOTS, project.notes, project.split, codes)
    system = build_system_prompt(categories, fewshots, root / PROMPT)
    left_out = _left_out_of_send(project, spec, notes, is_dataset)
    manifest = _manifest(project, spec, path, set_name, limit, system, left_out)
    folder = project.data_root / "runs" / manifest.run_id
    folder.mkdir(parents=True, exist_ok=True)
    _write_json(folder / "manifest.json", {"run_id": manifest.run_id, **manifest.model_dump(mode="json")})

    provider = get_provider(spec, project_root=root)
    budget = _budget(project.settings)
    started = time.monotonic()
    note_results = itemize_notes({fp: n for fp, n in notes.items() if fp not in left_out}, provider, codes, system,
                                 project.data_root / "cache" / "llm", budget,
                                 project.settings.get("runtime", {}).get("concurrency", 8), folder / "telemetry.jsonl")
    for fp in sorted(set(notes) & left_out):
        note_results[fp] = NoteResult(fingerprint=fp, note_id=notes[fp].note_id, status="review", review_reason="refused",
                                      violations=["not_sent_after_scan"], model=spec.name)
    minutes = (time.monotonic() - started) / 60
    row_results = assign_rows(rows, note_results, Policy.from_settings(project.settings))

    _write_json(folder / "note_results.json", {fp: r.model_dump(mode="json") for fp, r in sorted(note_results.items())})
    _write_json(folder / "row_results.json", [r.model_dump(mode="json") for r in row_results])
    measured_coverage = kpi.coverage(row_results)
    outcomes = dict(sorted(collections.Counter(r.outcome for r in row_results).items()))
    workbook = folder / "itemized.xlsx"
    # Only what a rerun repeats goes in the workbook: a cost or a clock would change its hash.
    write_workbook(workbook, row_results, note_results, categories, {
        "run_id": manifest.run_id,
        "model": spec.name,
        "set": manifest.set_name,
        "limit": limit if limit is not None else "none",
        "dataset_sha256": manifest.dataset_sha256,
        "taxonomy_version": tx.load_taxonomy(root / CATEGORIES).get("version", ""),
        "taxonomy_sha256": manifest.taxonomy_sha256,
        "prompt_sha256": manifest.prompt_sha256,
        "grammar_version": manifest.grammar_version,
        "rows": len(row_results),
        "notes": len(note_results),
        "outcomes": outcomes,
        "coverage_rows": measured_coverage["rows"]["share"],
        "coverage_usd": measured_coverage["usd"]["share"],
        "coverage_usd_without_repeats": measured_coverage["without_repeats"]["usd"]["share"],
    })
    telemetry = [json.loads(line) for line in (folder / "telemetry.jsonl").read_text(encoding="utf-8").splitlines()]
    outcome = RunOutcome(
        run_id=manifest.run_id, folder=folder, workbook=workbook, rows=len(row_results), notes=len(note_results),
        outcomes=outcomes,
        reasons=dict(sorted(collections.Counter(r.outcome_reason for r in row_results).items())),
        new_calls_usd=sum((r.cost_usd for r in note_results.values()), Decimal(0)),
        measured_usd=sum((Decimal(line["measured_cost_usd"]) for line in telemetry), Decimal(0)),
        minutes=minutes, cached_notes=sum(r.cached for r in note_results.values()), coverage=measured_coverage,
        manifest=manifest, note_results=note_results, row_results=row_results)
    project.ws.log("run", [path], [workbook], run_id=manifest.run_id, model=spec.name, set=manifest.set_name)
    return outcome


def load_run(project: Project, run_id: str) -> tuple[RunManifest, list[RowResult], dict[str, NoteResult]]:
    if not _RUN_ID.fullmatch(run_id):
        raise ContractError("a run id looks like run_ followed by 16 hex characters")
    folder = project.data_root / "runs" / run_id
    if not (folder / "row_results.json").exists():
        raise ContractError(f"run {run_id} has no results; run `itemizer run` first")
    stored = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    stored.pop("run_id", None)
    manifest = RunManifest.model_validate(stored)
    if manifest.run_id != run_id:
        raise ContractError(f"the manifest in run {run_id} does not match the run's id; the folder was changed")
    rows = [RowResult.model_validate(r) for r in json.loads((folder / "row_results.json").read_text(encoding="utf-8"))]
    notes = {fp: NoteResult.model_validate(r) for fp, r in json.loads((folder / "note_results.json").read_text(encoding="utf-8")).items()}
    return manifest, rows, notes


def latest_full_run(project: Project) -> str | None:
    """The newest run on all rows of the dataset file."""
    found = []
    for path in (project.data_root / "runs").glob("run_*/row_results.json"):
        manifest = json.loads((path.parent / "manifest.json").read_text(encoding="utf-8"))
        if manifest["set_name"] == "all" and manifest["dataset_sha256"] == project.split["dataset_sha256"]:
            found.append((path.stat().st_mtime_ns, path.parent.name))
    return max(found)[1] if found else None


def out_of_date(project: Project, manifest: RunManifest) -> list[str]:
    """Which inputs that decide a run's results have changed since it ran. Labels are not among them: a corrected label is
    scored on the same run. Code is not either, because a KPI fix re-scores the same answers, and the snapshot records it."""
    root = project.root
    changed = []
    if sha256_file(root / CATEGORIES) != manifest.taxonomy_sha256:
        changed.append("the category list")
    if sha256_file(root / FEWSHOTS) != manifest.fewshot_sha256:
        changed.append("the worked examples")
    if GRAMMAR_VERSION != manifest.grammar_version:
        changed.append("the grammar")
    if not changed:  # the prompt is built from the two files above, and building it from a changed list could fail
        categories = project.categories()
        fewshots = load_fewshots(root / FEWSHOTS, project.notes, project.split, {c["code"] for c in categories})
        system = build_system_prompt(categories, fewshots, root / PROMPT)
        if hashlib.sha256(system.encode("utf-8")).hexdigest() != manifest.prompt_sha256:
            changed.append("the prompt")
    spec = ModelSpec.model_validate(manifest.model)
    if _config_sha(project, _left_out_of_send(project, spec, project.notes, True)) != manifest.config_sha256:
        changed.append("the settings in config/run.yaml or the scan decision")
    return changed


# These reasons mean a note never got an answer, and a repeat run recovers it. Scoring now would measure an outage.
UNANSWERED = ("provider_unavailable", "budget_exhausted")


def evaluate_run(root: Path, run_id: str | None = None, milestone: str = "d3", extra_peek: str | None = None) -> dict:
    """Score a run on all rows against TEST. Aggregates only. Scoring the same results again uses no TEST budget.

    Everything refused here is refused before any budget is spent.
    """
    project = load_project(root)
    run_id = run_id or latest_full_run(project)
    if run_id is None:
        raise ContractError("no run on all rows exists yet")
    manifest, rows, note_results = load_run(project, run_id)
    if manifest.dataset_sha256 != project.split["dataset_sha256"]:
        raise ContractError(f"run {run_id} used another export, and Level gates need the dataset file")
    if manifest.set_name != "all" or manifest.limit is not None:
        raise ContractError("Level gates need a run on all rows of the dataset file, with no --set and no --limit")
    changed = out_of_date(project, manifest)
    if changed:
        raise ContractError(f"run {run_id} is out of date: {', '.join(changed)} changed after it ran. Run again, and pass "
                            "--extra-peek with the reason if this milestone's TEST budget is spent")
    unanswered = sum(result.review_reason in UNANSWERED for result in note_results.values())
    if unanswered:
        raise ContractError(f"{unanswered} notes in run {run_id} got no answer, because of a provider failure or a spent budget. "
                            "Run again to recover them. Nothing was charged to the TEST budget")
    rebuilt = assign_rows(project.rows, note_results, Policy.from_settings(project.settings))
    if rebuilt != rows:
        raise ContractError(f"row_results.json in run {run_id} does not follow from its note results and the dataset, so the "
                            "folder was changed. Run again")
    gold, status = lb.load_test_gold(project.ws)
    entries = {e["fingerprint"]: e for e in project.split["notes"]}
    missing = [fp for fp in gold if fp not in entries]
    if missing:
        raise ContractError(f"{len(missing)} frozen TEST notes are not in the split manifest")
    # TEST is what was frozen: a later change to the mix does not alter it until the final seal.
    test_entries = [{**entries[fp], "set": "TEST"} for fp in sorted(gold)]
    snapshot = kpi.evaluate(project.data_root, manifest, milestone, rows, note_results, project.notes,
                            {c["code"] for c in project.categories()}, test_entries, gold, status, project.settings,
                            project.cfg.large_dispute_usd, project.cfg.seed, extra_peek)
    project.ws.log("evaluate", [], [kpi.snapshot_path(project.data_root, run_id, milestone)], run_id=run_id, status=status,
                   budget_event=snapshot["test_budget"]["event"])
    return snapshot
