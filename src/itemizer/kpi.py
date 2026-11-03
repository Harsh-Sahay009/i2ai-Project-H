"""The KPI Calculator: coverage, item matching, weighted accuracy and Level gates (architecture/docs/04-kpi-calculator.md).

Coverage comes from a run on all rows. Accuracy comes from TEST, on covered notes only, weighted back to the real mix of
rows. `evaluate` returns and writes aggregates only: no note text, items, row ids or fingerprints.
"""
from __future__ import annotations

import collections
import datetime as dt
import getpass
import hashlib
import json
import math
import random
import re
import statistics
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from scipy.optimize import linear_sum_assignment

from .bootstrap.data import ContractError, GoldItem, Note, NoteLabel
from .bootstrap.labels import check_item, gold_stratum
from .contracts import NoteResult, RowResult, RunManifest
from .grammar import EVIDENCE_RULES

METRIC_VERSION = "1"
COVERED = frozenset({"verified", "discrepancy", "no_charge_stated"})
_Z = 1.959963984540054  # two-sided 95%
_LABEL_STATUSES = ("provisional", "sealed")
_PAIR_COST = {"match": 0, "category_error": 1, "amount_error": 1, "unmatched": 2}


def wilson(successes: float, n: float) -> tuple[float | None, float | None]:
    """The 95% Wilson interval, or Nones with nothing to measure. `n` may be an effective sample size."""
    if n <= 0:
        return None, None
    p = successes / n
    z2 = _Z * _Z
    denominator = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denominator
    half = _Z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def _rows_block(rows: list[RowResult]) -> dict:
    covered = sum(r.outcome in COVERED for r in rows)
    low, high = wilson(covered, len(rows))
    return {"covered": covered, "total": len(rows), "share": covered / len(rows) if rows else None,
            "ci_low": low, "ci_high": high, "n": len(rows)}


def _usd_block(rows: list[RowResult]) -> dict:
    """Plain sums of `disputed`, as in the scope's figure. Wilson does not apply to dollars directly, so the interval
    uses Kish's effective sample size, which is small when a few rows hold most of the dollars."""
    total = sum((r.disputed for r in rows), Decimal(0))
    covered = sum((r.disputed for r in rows if r.outcome in COVERED), Decimal(0))
    share, effective_n, low, high = None, None, None, None
    if total > 0:  # negative rows can leave a sum with no meaningful share
        share = float(covered / total)
        effective_n = float(sum((abs(r.disputed) for r in rows), Decimal(0)) ** 2 / sum(r.disputed ** 2 for r in rows))
        low, high = wilson(min(max(share, 0.0), 1.0) * effective_n, effective_n)
    # The plain sum is the scope's figure, but a negative row left uncovered makes the share read high, so it is reported.
    return {"covered": str(covered), "total": str(total), "share": share, "ci_low": low, "ci_high": high,
            "n": len(rows), "effective_n": effective_n,
            "negative_rows_not_covered": sum(r.disputed < 0 and r.outcome not in COVERED for r in rows)}


def coverage(row_results: list[RowResult]) -> dict:
    """Rows and dollars covered, and both again without repeated rows. The gates use the figures that include them."""
    kept = [r for r in row_results if not r.repeated]
    return {"rows": _rows_block(row_results), "usd": _usd_block(row_results),
            "without_repeats": {"rows": _rows_block(kept), "usd": _usd_block(kept)}}


def _pair_kind(predicted: GoldItem, gold: GoldItem, tolerance: Decimal) -> str:
    same_category = predicted.category == gold.category
    same_amount = abs(predicted.amount - gold.amount) <= tolerance
    if same_category and same_amount:
        return "match"
    if same_amount:
        return "category_error"
    return "amount_error" if same_category else "unmatched"


def match_note(predicted: list[GoldItem], gold: list[GoldItem], tolerance: Decimal | str) -> dict:
    """Optimal assignment of predicted to gold items. Two notes with no items, each stating no charge, are correct.

    A pair assigned at cost 2 matches nothing, so it counts as one missing and one extra item. Swapped categories tie:
    two category errors and two amount errors both cost 2. A tie goes to pairing by amount, because the amount is what
    the note states, so the scaled cost adds 1 for each amount error without changing which total is lowest.
    """
    tolerance = Decimal(str(tolerance))
    found = collections.Counter()
    if predicted and gold:
        kinds = [[_pair_kind(p, g, tolerance) for g in gold] for p in predicted]
        scale = min(len(predicted), len(gold)) + 1
        costs = [[_PAIR_COST[kind] * scale + (kind == "amount_error") for kind in line] for line in kinds]
        found.update(kinds[p][g] for p, g in zip(*linear_sum_assignment(costs)))
    paired = sum(found.values())
    missing = len(gold) - paired + found["unmatched"]
    extra = len(predicted) - paired + found["unmatched"]
    return {"correct": found["match"] == len(gold) and not extra, "category_errors": found["category_error"],
            "amount_errors": found["amount_error"], "missing": missing, "extra": extra}


def stratum_shares(row_results: list[RowResult], large_usd: Decimal) -> dict[str, float]:
    """The real mix, from the run on all rows. Membership uses the predicted item count, so a row in Review counts as
    `single` unless it is large. The snapshot records this as an approximation (doc 4.6)."""
    counts = collections.Counter(
        "large" if r.disputed >= large_usd else ("multi" if r.item_count >= 2 else "single") for r in row_results)
    return {s: counts[s] / len(row_results) if row_results else 0.0 for s in ("large", "multi", "single")}


@dataclass(frozen=True)
class _Scored:
    stratum: str
    rows: int
    correct: bool
    format_seen: bool


def _row_weighted(notes: list[_Scored]) -> float:
    return sum(n.rows for n in notes if n.correct) / sum(n.rows for n in notes)


def _weighted(by_stratum: dict[str, list[_Scored]], shares: Mapping[str, float]) -> float | None:
    total = sum(shares[s] for s in by_stratum)
    return sum(shares[s] * _row_weighted(notes) for s, notes in by_stratum.items()) / total if total else None


def _bootstrap(by_stratum: dict[str, list[_Scored]], shares: Mapping[str, float], seed: int,
               resamples: int) -> tuple[float, float]:
    """Resample notes within each stratum, so every resample keeps the stratum sizes. Returns the 2.5th and 97.5th
    percentiles."""
    rng = random.Random(seed)
    values = [_weighted({s: rng.choices(notes, k=len(notes)) for s, notes in by_stratum.items()}, shares)
              for _ in range(resamples)]
    cuts = statistics.quantiles(values, n=40, method="inclusive")
    return cuts[0], cuts[-1]


def _proportion(notes: list[_Scored]) -> dict:
    correct = sum(n.correct for n in notes)
    low, high = wilson(correct, len(notes))
    return {"n": len(notes), "correct": correct, "accuracy": correct / len(notes) if notes else None,
            "wilson_low": low, "wilson_high": high}


def accuracy(test_entries: list[dict], note_results: Mapping[str, NoteResult], gold: Mapping[str, NoteLabel],
             row_counts: Mapping[str, int], stratum_shares: Mapping[str, float], seed: int, resamples: int, *,
             tolerance: Decimal | str) -> dict:
    """Weighted accuracy on covered notes: Σ π_s·acc_s / Σ π_s, over strata with covered notes. Within a stratum each
    note counts for its rows. An entry's stratum is its `stratum` when set, else its `provisional_stratum`."""
    if resamples < 2:
        raise ContractError("kpi.bootstrap_resamples must be at least 2")
    entries = sorted(test_entries, key=lambda e: e["fingerprint"])  # so the bootstrap does not depend on the input order
    unlabelled = sum(e["fingerprint"] not in gold for e in entries)
    if unlabelled:
        raise ContractError(f"{unlabelled} of {len(entries)} TEST notes have no gold label")
    strata_of = {e["fingerprint"]: e.get("stratum") or e["provisional_stratum"] for e in entries}
    unknown = sorted(set(strata_of.values()) - set(stratum_shares))
    if unknown:
        raise ContractError(f"no share in the real mix for strata: {', '.join(unknown)}")

    scored: list[_Scored] = []
    errors = collections.Counter()
    for entry in entries:
        fp = entry["fingerprint"]
        result = note_results.get(fp)
        if result is None or result.status != "ok":
            continue
        match = match_note(result.items, gold[fp].items, tolerance)
        errors.update({k: v for k, v in match.items() if k != "correct"})
        scored.append(_Scored(strata_of[fp], row_counts.get(fp, 0), match["correct"], bool(entry.get("format_in_train"))))
    without_rows = sum(n.rows < 1 for n in scored)
    if without_rows:
        raise ContractError(f"{without_rows} covered TEST notes have no row count")

    groups = {s: [n for n in scored if n.stratum == s] for s in sorted(stratum_shares)}
    kept = {s: notes for s, notes in groups.items() if notes}
    weighted = _weighted(kept, stratum_shares)
    ci_low, ci_high = _bootstrap(kept, stratum_shares, seed, resamples) if weighted is not None else (None, None)
    overall = _proportion(scored)
    held = collections.Counter(strata_of.values())
    return {
        "weighted": weighted, "ci_low": ci_low, "ci_high": ci_high, "n": len(scored), "test_notes": len(entries),
        "correct": overall["correct"], "unweighted": overall["accuracy"],
        "wilson_low": overall["wilson_low"], "wilson_high": overall["wilson_high"],
        "strata": {s: {**_proportion(notes), "accuracy": _row_weighted(notes) if notes else None, "test_notes": held[s],
                       "rows": sum(n.rows for n in notes), "share": stratum_shares[s]} for s, notes in groups.items()},
        "dropped_strata": sorted(set(groups) - set(kept)),
        "formats": {"seen": _proportion([n for n in scored if n.format_seen]),
                    "unseen": _proportion([n for n in scored if not n.format_seen])},
        "errors": {k: errors[k] for k in ("category_errors", "amount_errors", "missing", "extra")},
    }


def _item_violations(item: GoldItem, note: Note | None, codes: set[str]) -> list[str]:
    if note is None:
        return ["evidence_not_verbatim"]
    try:
        _, errors = check_item(note, item.item, item.category, item.amount, item.evidence_text, item.line_type,
                               item.derivation, codes)
    except ArithmeticError:  # check_item cannot multiply numbers too long for Decimal, and a note can hold any digits
        return ["product_mismatch"]
    found = {code for code, _ in errors}  # its messages quote the item, so only the codes are kept
    if note.text[item.evidence_start:item.evidence_end] != item.evidence_text:
        found.add("evidence_not_verbatim")
    return sorted(found)


def _row_violations(row: RowResult, note_results: Mapping[str, NoteResult], abs_tolerance: Decimal) -> list[str]:
    """A row's totals must be what its note's items give, and a row that does not add up must be flagged."""
    if row.fingerprint is None:  # a blank note has nothing to check
        return []
    result = note_results.get(row.fingerprint)
    if result is None:
        return ["row_without_note"]
    if row.items_total is None:
        return ["row_not_reconciled"] if row.outcome in ("verified", "discrepancy") else []
    paid = sum((i.amount for i in result.items if i.line_type == "already_paid"), Decimal(0))
    charged = sum((i.amount for i in result.items if i.line_type != "already_paid"), Decimal(0))
    if (row.items_total, row.already_paid_total, row.difference) != (charged, paid, row.disputed - (charged - paid)):
        return ["amount_changed"]
    return ["unflagged_difference"] if row.outcome == "verified" and abs(row.difference) > abs_tolerance else []


def invariants(row_results: list[RowResult], note_results: Mapping[str, NoteResult], notes: Mapping[str, Note],
               codes: Iterable[str], *, abs_tolerance: Decimal | str) -> dict:
    """Re-run `check_item` on every accepted item, and check each row's amounts against its note's items."""
    allowed, abs_tolerance = set(codes), Decimal(str(abs_tolerance))
    found = collections.Counter()
    items = verifiable = 0
    for fp, result in sorted(note_results.items()):
        for item in result.items:
            problems = _item_violations(item, notes.get(fp), allowed)
            found.update(problems)
            items += 1
            verifiable += not EVIDENCE_RULES.intersection(problems)
    for row in row_results:
        found.update(_row_violations(row, note_results, abs_tolerance))
    return {"violations": sum(found.values()), "by_code": dict(sorted(found.items())), "items": items,
            "verifiable_items": verifiable, "verifiability": verifiable / items if items else None}


def _condition(value: float | None, target: float, measured: Mapping[str, Any]) -> dict:
    low, high = measured["ci_low"], measured["ci_high"]
    # isclose, so float noise cannot fail a value that lands exactly on its target.
    met = value is not None and (value >= target or math.isclose(value, target, rel_tol=1e-12))
    return {"value": value, "target": target, "met": met, "ci_low": low, "ci_high": high, "n": measured["n"],
            "interval_contains_target": None if low is None else low <= target <= high}


def level_gate(level: str, coverage: Mapping[str, Any], accuracy: Mapping[str, Any], invariants: Mapping[str, Any],
               targets: Mapping[str, Any]) -> dict:
    """Option A: a level passes on the measured values, with invariant violations at 0. Intervals are shown, never used.
    `targets` is one level's entry in `gates` of config/run.yaml."""
    try:
        wanted = {name: float(targets[name]) for name in ("cov_usd", "cov_rows", "acc")}
    except (KeyError, TypeError, ValueError):
        raise ContractError(f"the targets for {level} need cov_usd, cov_rows and acc, each a number") from None
    conditions = {"cov_usd": _condition(coverage["usd"]["share"], wanted["cov_usd"], coverage["usd"]),
                  "cov_rows": _condition(coverage["rows"]["share"], wanted["cov_rows"], coverage["rows"]),
                  "acc": _condition(accuracy["weighted"], wanted["acc"], accuracy)}
    violations = invariants["violations"]
    if violations:
        status, reason = "fail", "invariant_failed"
    elif all(c["met"] for c in conditions.values()):
        status, reason = "pass", None
    else:
        status, reason = "fail", "target_not_met"
    return {"level": level, "status": status, "reason": reason, "conditions": conditions,
            "invariant_violations": violations}


def results_digest(note_results: Mapping[str, NoteResult]) -> str:
    """What the answers say, without cost, latency or whether they came from the cache."""
    kept = {fp: result.model_dump(mode="json", exclude={"cost_usd", "latency_ms", "cached"}) for fp, result in note_results.items()}
    return hashlib.sha256(json.dumps(kept, sort_keys=True).encode("utf-8")).hexdigest()


_CHARGED = ("spent", "extra_spent")


def _runs_spent(path: Path, milestone: str) -> dict[tuple[str, str], str]:
    """What is charged to a milestone: each run with the results it was scored on, and the event that charged it. A ledger
    it cannot read stops the evaluation, because TEST must not be peeked at while what was spent is unknown."""
    if not path.exists():
        return {}
    try:
        entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return {(e["run_id"], e.get("results_sha256", "")): e["event"]
                for e in entries if e["milestone"] == milestone and e["event"] in _CHARGED}
    except (ValueError, KeyError, TypeError):
        raise ContractError(f"the TEST budget ledger {path} has a line that cannot be read, "
                            "so what was spent is unknown; repair the file before evaluating") from None


def spend_test_budget(path: Path, run_id: str, milestone: str, budget: int, results: str = "", extra_peek: str | None = None) -> dict:
    """Charge a run to a milestone's TEST budget in a JSONL ledger. Re-scoring the same results is free, so labels corrected
    by the client need no new run. Different results under one id are a new run, because they could be a better score.

    `extra_peek` spends past the budget on purpose, for a reason that is logged and shown beside the result. Otherwise a
    category renamed at approval would leave no way to score the run that uses the approved list.
    """
    spent = _runs_spent(path, milestone)
    if (run_id, results) in spent:
        event = "rescored"
    elif len(spent) < budget:
        event = "spent"
    else:
        event = "extra_spent" if extra_peek else "refused"
    runs_spent = len(spent) + (event in _CHARGED)
    extra_peeks = sum(kind == "extra_spent" for kind in spent.values()) + (event == "extra_spent")
    entry = {"event": event, "run_id": run_id, "results_sha256": results, "milestone": milestone, "budget": budget, "runs_spent": runs_spent,
             "who": getpass.getuser(), "when": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    if event == "extra_spent":
        entry["reason"] = extra_peek
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    if event == "refused":
        raise ContractError(f"the TEST budget for milestone {milestone} is spent ({runs_spent} of {budget} runs), so "
                            f"{run_id} was refused and the refusal is logged in {path}. Re-scoring the same results "
                            "stays free. To spend past the budget on purpose, pass --extra-peek with the reason")
    return {"event": event, "budget": budget, "runs_spent": runs_spent, "extra_peeks": extra_peeks}


def snapshot_path(data_root: Path, run_id: str, milestone: str) -> Path:
    return data_root / "kpi" / f"{run_id}_{milestone}.json"


def _per_carrier(row_results: list[RowResult], overall: Mapping[str, Any]) -> dict:
    """Codes and counts. A carrier below the run's overall coverage is flagged, not penalised."""
    grouped: dict[str, list[RowResult]] = collections.defaultdict(list)
    for row in row_results:
        grouped[row.carrier].append(row)

    def below(block: Mapping[str, Any], whole: Mapping[str, Any]) -> bool:
        return block["share"] is not None and whole["share"] is not None and block["share"] < whole["share"]

    report = {}
    for carrier, rows in sorted(grouped.items()):
        rows_block, usd_block = _rows_block(rows), _usd_block(rows)
        report[carrier] = {"rows": rows_block, "usd": usd_block, "below_overall_rows": below(rows_block, overall["rows"]),
                           "below_overall_usd": below(usd_block, overall["usd"])}
    return report


def evaluate(data_root: Path, manifest: RunManifest, milestone: str, row_results: list[RowResult],
             note_results: Mapping[str, NoteResult], notes: Mapping[str, Note], codes: Iterable[str],
             test_entries: list[dict], gold: Mapping[str, NoteLabel], labels_status: str, settings: Mapping[str, Any],
             large_usd: Decimal, seed: int, extra_peek: str | None = None) -> dict:
    """Score a run on TEST against every level in `gates`. Returns and writes aggregates only.

    `settings` is config/run.yaml as parsed, and `labels_status` comes from `load_test_gold`. The budget is charged
    before any label is compared. A refused run writes no snapshot.
    """
    if manifest.set_name != "all" or manifest.limit is not None or manifest.split_sha256 is None:
        raise ContractError("Level gates need a run on all rows of the dataset file, with no --set and no --limit")
    if labels_status not in _LABEL_STATUSES:
        raise ContractError(f"labels_status must be one of {', '.join(_LABEL_STATUSES)}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", milestone):  # it becomes part of a file name
        raise ContractError("a milestone is lower-case letters, digits, '-' and '_', such as d3")
    try:
        budget = settings["kpi"]["test_peek_budget_per_milestone"]
        resamples = settings["kpi"]["bootstrap_resamples"]
        tolerance = Decimal(str(settings["kpi"]["amount_match_tolerance_usd"]))
        abs_tolerance = Decimal(str(settings["reconcile"]["abs_tolerance_usd"]))
        gates = settings["gates"]
        milestones = settings["kpi"]["milestones"]
    except (KeyError, TypeError, InvalidOperation):
        raise ContractError("the run settings need kpi.test_peek_budget_per_milestone, kpi.bootstrap_resamples, "
                            "kpi.amount_match_tolerance_usd, kpi.milestones, reconcile.abs_tolerance_usd and gates") from None
    if milestone not in milestones:
        raise ContractError(f"milestone {milestone} is not in kpi.milestones ({', '.join(milestones)}), so it has no TEST budget")
    if not test_entries or any(e.get("set") != "TEST" for e in test_entries):
        raise ContractError("evaluate scores TEST only, and needs TEST's entries from the split manifest")
    fingerprints = [e["fingerprint"] for e in test_entries]
    unusable = sum(fp not in gold or fp not in notes for fp in fingerprints)
    if unusable:
        raise ContractError(f"{unusable} of {len(fingerprints)} TEST notes have no gold label or are not in the dataset")
    run_id = manifest.run_id
    results = results_digest(note_results)
    charge = spend_test_budget(data_root / "kpi" / "test_budget.jsonl", run_id, milestone, budget, results, extra_peek)

    # Final strata come from the gold items, so provisional and sealed labels are scored the same way.
    entries = [{**e, "stratum": gold_stratum(gold[e["fingerprint"]], notes[e["fingerprint"]], large_usd)}
               for e in test_entries]
    # Under no_charge_stated_policy: review, a note can be `ok` while all its rows are in Review, so it is not covered.
    covered_notes = {r.fingerprint for r in row_results if r.outcome in COVERED}
    shares = stratum_shares(row_results, large_usd)
    measured_coverage = coverage(row_results)
    measured_accuracy = accuracy(entries, {fp: r for fp, r in note_results.items() if fp in covered_notes}, gold,
                                 {e["fingerprint"]: e["rows"] for e in entries}, shares, seed, resamples,
                                 tolerance=tolerance)
    checks = invariants(row_results, note_results, notes, codes, abs_tolerance=abs_tolerance)
    labels = {fp: gold[fp].model_dump(mode="json") for fp in sorted(fingerprints)}
    snapshot = {
        "run_id": run_id,
        "results_sha256": results,
        "run": {field: getattr(manifest, field) for field in ("code_sha", "code_commit", "code_dirty", "grammar_version", "taxonomy_sha256",
                                                              "prompt_sha256", "fewshot_sha256", "config_sha256")} | {"model": manifest.model.get("name")},
        "milestone": milestone,
        "population": "TEST",
        "accuracy_scope": "in_sample",  # until FRESH data arrives (doc 4.1)
        "labels_status": labels_status,
        "labels_sha256": hashlib.sha256(json.dumps(labels, sort_keys=True).encode("utf-8")).hexdigest(),
        "metric_version": METRIC_VERSION,
        "settings": {"seed": seed, "bootstrap_resamples": resamples, "amount_match_tolerance_usd": str(tolerance),
                     "abs_tolerance_usd": str(abs_tolerance), "large_dispute_usd": str(large_usd)},
        "weights": {"shares": shares, "basis": "predicted_item_count"},
        "coverage": measured_coverage,
        "per_carrier": _per_carrier(row_results, measured_coverage),
        "accuracy": measured_accuracy,
        "invariants": checks,
        "levels": {level: {**level_gate(level, measured_coverage, measured_accuracy, checks, targets),
                           "labels_status": labels_status} for level, targets in sorted(gates.items())},
        "test_budget": charge,
    }
    target = snapshot_path(data_root, run_id, milestone)
    target.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (data_root / "kpi" / "snapshots.jsonl").open("a", encoding="utf-8") as handle:  # append-only history (doc 4.8)
        handle.write(json.dumps(snapshot, sort_keys=True) + "\n")
    return snapshot
