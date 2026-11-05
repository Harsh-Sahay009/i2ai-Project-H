"""A new experiment against received draft labels, without fabricating historical freeze records.

Run `python -m itemizer.independent` to prepare/check the protocol; add --run for inference.
All private inputs, outputs and cache remain under ignored data/evaluation/.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlparse

from . import kpi, pipeline
from .bootstrap.data import ContractError, NoteLabel, sha256_file
from .contracts import NoteResult
from .itemize import Budget, Policy, assign_rows, build_system_prompt, itemize_notes, load_fewshots
from .providers import ProviderError, get_provider


def freeze_inputs(path: Path, payload: dict) -> None:
    if path.exists():
        if json.loads(path.read_text()) != payload:
            raise ContractError("experiment inputs changed; use a new experiment version")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def require_complete(results: dict[str, NoteResult], expected: set[str]) -> None:
    if set(results) != expected or any(r.review_reason in pipeline.UNANSWERED for r in results.values()):
        raise ContractError("incomplete inference run; accuracy is not reported")


def require_authorization(path: Path, dataset_sha256: str) -> None:
    try:
        approval = json.loads(path.read_text())
        valid = approval.get("external_use") == "user_confirmed_written_approval" and approval.get("dataset_sha256") == dataset_sha256
    except (OSError, ValueError, AttributeError):
        valid = False
    if not valid:
        raise ContractError("external inference needs dataset-specific authorization in data/evaluation/external_authorization.json")


def benchmark_weights(strata: dict[str, str], row_counts: dict[str, int]) -> dict[str, float]:
    counts = {key: 0 for key in ("large", "multi", "single")}
    for fp, stratum in strata.items():
        if stratum not in counts or row_counts.get(fp, 0) <= 0:
            raise ContractError("invalid benchmark population strata or row counts")
        counts[stratum] += row_counts[fp]
    total = sum(counts.values())
    if not total:
        raise ContractError("benchmark has no rows")
    return {key: count / total for key, count in counts.items()}


class PacedProvider:
    """One free-tier request at a time, with a circuit breaker after transport/provider failure."""

    def __init__(self, provider, interval: float):
        self.provider, self.spec = provider, provider.spec
        self.interval, self.next_call, self.failed = interval, 0.0, False
        self.lock = threading.Lock()

    def complete(self, system, user, schema):
        with self.lock:
            if self.failed:
                raise ProviderError("provider circuit is open; resume when access recovers")
            delay = self.next_call - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self.next_call = time.monotonic() + self.interval
            try:
                return self.provider.complete(system, user, schema)
            except ProviderError:
                self.failed = True
                raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gemini-3-flash-preview-free")
    parser.add_argument("--scope", choices=("benchmark", "all"), default="benchmark")
    parser.add_argument("--experiment", default="independent-v1")
    parser.add_argument("--interval", type=float, default=4.0)
    parser.add_argument("--minutes", type=float, default=30)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.experiment.replace("-", "").replace("_", "").isalnum() or args.interval < 0 or args.minutes <= 0:
        raise ContractError("invalid experiment name, interval or time limit")
    root = Path.cwd()
    project = pipeline.load_project(root)
    benchmark = root / "data/incoming/alejandro/test_provisional.json"
    received = json.loads(benchmark.read_text())
    gold = {fp: NoteLabel.model_validate(label) for fp, label in received["labels"].items()}
    if len(gold) != 200 or not set(gold) <= set(project.notes):
        raise ContractError("benchmark must contain 200 known notes")
    categories = project.categories()
    codes = {c["code"] for c in categories}
    fewshots = load_fewshots(root / pipeline.FEWSHOTS, project.notes, project.split, codes)
    if set(gold) & {shot.note.fingerprint for shot in fewshots}:
        raise ContractError("benchmark overlaps prompt examples")
    for fp, label in gold.items():
        if label.fingerprint != fp or label.note_id != project.notes[fp].note_id:
            raise ContractError("benchmark note identity is invalid")
        if any(kpi._item_violations(item, project.notes[fp], codes) for item in label.items):
            raise ContractError("benchmark contains invalid reference evidence or amounts")
    spec = pipeline.choose_model(root, args.model)
    authorization = root / "data/evaluation/external_authorization.json"
    if urlparse(spec.base_url or "").hostname not in pipeline._THIS_MACHINE:
        require_authorization(authorization, sha256_file(project.dataset))
    system = build_system_prompt(categories, fewshots, root / pipeline.PROMPT)
    folder = root / "data/evaluation" / args.experiment / args.scope
    protocol = {
        "experiment": args.experiment, "scope": args.scope,
        "dataset_sha256": sha256_file(project.dataset), "benchmark_sha256": sha256_file(benchmark),
        "prompt_sha256": hashlib.sha256(system.encode()).hexdigest(),
        "taxonomy_sha256": sha256_file(root / pipeline.CATEGORIES),
        "settings_sha256": sha256_file(root / pipeline.SETTINGS),
        "code_sha256": pipeline._code_identity(root)[0],
        "model": spec.model_dump(mode="json"), "request_interval_seconds": args.interval,
        "reference_sources": dict(collections.Counter(l.source for l in gold.values())),
        "historical_run_reproduced": False,
        "authorization_sha256": sha256_file(authorization) if authorization.exists() else None,
    }
    freeze_inputs(folder / "protocol.json", protocol)
    chosen = project.notes if args.scope == "all" else {fp: project.notes[fp] for fp in sorted(gold)}
    print(json.dumps({"prepared": True, "scope": args.scope, "notes": len(chosen), "model": spec.name,
                      "inference_requested": args.run}), flush=True)
    if not args.run:
        return 0
    started = time.monotonic()

    def progress(done, total, spent):
        payload = {"done": done, "total": total, "seconds": round(time.monotonic() - started, 1)}
        (folder / "progress.json").write_text(json.dumps(payload))
        if done == total or done % 10 == 0:
            print(json.dumps(payload), flush=True)

    results = itemize_notes(chosen, PacedProvider(get_provider(spec, project_root=root), args.interval), codes,
                            system, folder.parent / "cache", Budget("0.01", args.minutes), 1,
                            folder / "telemetry.jsonl", progress)
    (folder / "note_results.json").write_text(json.dumps({fp: r.model_dump(mode="json") for fp, r in results.items()},
                                                       indent=2, sort_keys=True))
    try:
        require_complete(results, set(chosen))
    except ContractError:
        incomplete = {"status": "incomplete", "accuracy": None, "scope": args.scope,
                      "reasons": dict(collections.Counter(r.review_reason for r in results.values() if r.review_reason)),
                      "seconds": round(time.monotonic() - started, 2)}
        (folder / "summary.json").write_text(json.dumps(incomplete, indent=2))
        print(json.dumps(incomplete), flush=True)
        return 2
    rows = project.rows if args.scope == "all" else [r for r in project.rows if r.row_id in {
        rid for note in chosen.values() for rid in note.row_ids}]
    row_results = assign_rows(rows, results, Policy.from_settings(project.settings))
    development_formats = {n.format_key for fp, n in project.notes.items() if fp not in gold}
    entries = [{"fingerprint": fp, "stratum": received["strata"][fp],
                "format_in_train": project.notes[fp].format_key in development_formats} for fp in sorted(gold)]
    row_counts = {fp: len(n.row_ids) for fp, n in project.notes.items()}
    weights = (kpi.stratum_shares(row_results, project.cfg.large_dispute_usd) if args.scope == "all" else
               benchmark_weights(received["strata"], row_counts))
    agreement = kpi.accuracy(entries, results, gold, row_counts,
                             weights, project.cfg.seed,
                             project.settings["kpi"]["bootstrap_resamples"],
                             tolerance=project.settings["kpi"]["amount_match_tolerance_usd"])
    summary = {
        "status": "complete", "model": spec.name, "scope": args.scope,
        "metric_interpretation": "agreement with model-drafted references, not human-verified accuracy",
        "accuracy_weighting_population": "full_corpus_predicted_strata_approximation" if args.scope == "all" else "benchmark_reference_row_strata",
        "benchmark_notes": len(gold), "inference_notes": len(results), "rows": len(rows),
        "agreement": agreement, "coverage": kpi.coverage(row_results),
        "invariants": kpi.invariants(row_results, results, project.notes, codes,
                                      abs_tolerance=project.settings["reconcile"]["abs_tolerance_usd"]),
        "outcomes": dict(collections.Counter(r.outcome for r in row_results)),
        "seconds": round(time.monotonic() - started, 2),
        "official_d3_acceptance": "not_assessed",
    }
    (folder / "row_results.json").write_text(json.dumps([r.model_dump(mode="json") for r in row_results], indent=2))
    (folder / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    with (folder / "evaluations.jsonl").open("a") as handle:
        handle.write(json.dumps({"results_sha256": kpi.results_digest(results), "benchmark_sha256": protocol["benchmark_sha256"],
                                 "agreement": agreement["weighted"], "seconds": summary["seconds"]}) + "\n")
    print(json.dumps({"status": "complete", "scope": args.scope, "covered_benchmark_notes": agreement["n"],
                      "correct_benchmark_notes": agreement["correct"], "agreement": agreement["unweighted"],
                      "seconds": summary["seconds"]}), flush=True)
    return 0


def run_cli() -> int:
    try:
        return main()
    except Exception as exc:
        print(json.dumps({"status": "stopped", "error_type": type(exc).__name__,
                          "details": "Input/provider error details withheld to protect notes and credentials."}))
        return 2


if __name__ == "__main__":
    raise SystemExit(run_cli())
