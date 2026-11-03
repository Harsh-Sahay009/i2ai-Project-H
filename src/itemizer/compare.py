"""Run several models on the same notes and report them on the same measures. Aggregates only, and never TEST."""
from __future__ import annotations

import collections
import json
import re
import statistics
from decimal import Decimal
from pathlib import Path

from . import kpi
from .bootstrap.data import ContractError, NoteLabel
from .contracts import NoteResult
from .pipeline import SETS, RunOutcome, load_project, run


def _item_key(result: NoteResult) -> list[tuple[str, Decimal]]:
    return sorted((item.category, item.amount) for item in result.items)


def _agreement(first: dict[str, NoteResult], other: dict[str, NoteResult]) -> float | None:
    """The share of notes where both models answered and gave the same categories and amounts."""
    shared = [fp for fp in first if fp in other and first[fp].status == "ok" and other[fp].status == "ok"]
    return sum(_item_key(first[fp]) == _item_key(other[fp]) for fp in shared) / len(shared) if shared else None


def _accuracy(results: dict[str, NoteResult], labels: dict[str, NoteLabel], tolerance: Decimal) -> dict | None:
    """Accuracy on the notes that have labels and that the model answered. `None` when no compared note has a label."""
    labelled = [fp for fp in results if fp in labels]
    if not labelled:
        return None
    answered = [fp for fp in labelled if results[fp].status == "ok"]
    correct = sum(kpi.match_note(results[fp].items, labels[fp].items, tolerance)["correct"] for fp in answered)
    return {"labelled_notes": len(labelled), "answered": len(answered), "correct": correct,
            "accuracy": correct / len(answered) if answered else None}


def projected_usd(costs: list[Decimal], all_notes: int) -> Decimal:
    """A cold start writes the prompt cache for the first calls at once. That happens once, so it is not scaled up.

    A typical note costs the median, and whatever the sample spent beyond that is added once.
    """
    typical = statistics.median(costs)
    return (typical * all_notes + max(sum(costs) - typical * len(costs), Decimal(0))).quantize(Decimal("0.01"))


def _report_line(name: str, outcome: RunOutcome, first: RunOutcome | None, labels: dict[str, NoteLabel], tolerance: Decimal,
                 all_notes: int, concurrency: int) -> dict:
    results = outcome.note_results
    telemetry = [json.loads(line) for line in (outcome.folder / "telemetry.jsonl").read_text(encoding="utf-8").splitlines()]
    notes = len(results)
    rows = collections.Counter(row.outcome for row in outcome.row_results)
    usd_per_note = outcome.measured_usd / notes if notes else Decimal(0)
    latency = sum(line["measured_latency_ms"] for line in telemetry) / len(telemetry) if telemetry else 0.0
    return {
        "model": name,
        "run_id": outcome.run_id,
        "notes": notes,
        "valid_first_try": sum(r.attempts == 1 and r.status == "ok" for r in results.values()) / notes,
        "retried": sum(r.attempts > 1 for r in results.values()) / notes,
        "review_share": rows["review"] / outcome.rows,
        "verified_share": (rows["verified"] + rows["no_charge_stated"]) / outcome.rows,
        "discrepancy_share": rows["discrepancy"] / outcome.rows,
        "review_reasons": dict(sorted(collections.Counter(r.review_reason for r in results.values() if r.review_reason).items())),
        "agreement_with_first": _agreement(first.note_results, results) if first else None,
        "accuracy_on_labels": _accuracy(results, labels, tolerance),
        "usd": outcome.measured_usd,
        "usd_per_note": usd_per_note,
        "mean_latency_ms": round(latency),
        "projected_usd_all_notes": projected_usd([Decimal(line["measured_cost_usd"]) for line in telemetry], all_notes),
        "projected_minutes_all_notes": round(latency * all_notes / max(concurrency, 1) / 60_000, 1),
    }


_TABLE = (("model", "Model", str), ("valid_first_try", "Valid first try", "{:.1%}".format), ("retried", "Retried", "{:.1%}".format),
          ("review_share", "Review", "{:.1%}".format), ("verified_share", "Verified", "{:.1%}".format),
          ("discrepancy_share", "Discrepancy", "{:.1%}".format),
          ("agreement_with_first", "Agrees with first", lambda v: "n/a" if v is None else f"{v:.1%}"),
          ("accuracy_on_labels", "Accuracy on labels",
           lambda v: "no labels" if v is None or v["accuracy"] is None else f"{v['accuracy']:.1%} of {v['answered']}"),
          ("usd", "Cost USD", lambda v: f"{v:.4f}"), ("mean_latency_ms", "Mean ms", str),
          ("projected_usd_all_notes", "USD, all notes", str), ("projected_minutes_all_notes", "Minutes, all notes", str))


def format_table(report: dict) -> str:
    """One line per measure and one column per model, so a long list of models still reads on a terminal."""
    lines = [[label] + [render(model[key]) for model in report["models"]] for key, label, render in _TABLE]
    widths = [max(len(line[column]) for line in lines) for column in range(len(lines[0]))]
    return "\n".join("  ".join(cell.ljust(width) for cell, width in zip(line, widths, strict=True)).rstrip() for line in lines)


def compare_models(root: Path, model_names: list[str], set_name: str = "train", limit: int | None = None) -> dict:
    """Same notes, same prompt, each model. The first model is the reference for agreement."""
    if set_name not in SETS:
        raise ContractError(f"--set must be one of {', '.join(sorted(SETS))}. TEST never chooses between candidates.")
    if not model_names:
        raise ContractError("name at least one model")
    project = load_project(root)
    pack = {"train": "train", "validation": "validation"}[set_name]
    labels: dict[str, NoteLabel] = {}
    if project.ws.exists(f"labels/{pack}.json"):
        labels = {fp: NoteLabel.model_validate(v) for fp, v in project.ws.read_json(f"labels/{pack}.json")["labels"].items()}
    tolerance = Decimal(str(project.settings["kpi"]["amount_match_tolerance_usd"]))
    concurrency = project.settings.get("runtime", {}).get("concurrency", 8)
    first: RunOutcome | None = None
    lines = []
    for name in model_names:
        outcome = run(root, model_name=name, set_name=set_name, limit=limit)
        lines.append(_report_line(name, outcome, first, labels, tolerance, len(project.notes), concurrency))
        first = first or outcome
    report = {"set": set_name, "limit": limit, "all_notes": len(project.notes), "models": lines}
    label = re.sub(r"[^A-Za-z0-9._-]", "-", "_vs_".join(model_names))[:120]
    target = project.data_root / "compare" / f"{label}_{set_name}_{limit if limit is not None else 'all'}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    project.ws.log("compare-models", [], [target], models=model_names, set=set_name)
    return {**report, "report_path": target}
