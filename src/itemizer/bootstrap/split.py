"""Dataset profile, anonymization scan and the TRAIN / VALIDATION / TEST split (ADR 0012)."""
from __future__ import annotations

import collections
import hashlib
import random
import re
from decimal import Decimal

from .data import Config, ContractError, DisputeRow, Note, Workspace, normalize

TEST_SIZE = 200
TEST_SINGLE = 100
SCOPE_FIGURES = {"rows": 1347, "carriers": 18, "disputed_usd": Decimal("186000")}

EMAIL = re.compile(r"[\w.+-]{1,64}@[\w-]{1,64}\.[\w.-]{1,32}")
PHONE = re.compile(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)")
NAME_CUE = re.compile(r"\b(?:PER|DRIVER|DRVR|DVR|ATTN|CONTACT|SPOKE (?:TO|WITH)|CALLED|APPROVED BY)\s+([A-Z][A-Z'-]{2,})", re.I)
NAME_FROM = re.compile(r"\b[A-Z]{3,} [A-Z]{3,} FROM PPG\b")
NOT_A_NAME = {
    "AND", "ARRIVED", "ASSIST", "ASSISTANCE", "BOL", "CARRIER", "CHARGE", "CHARGES", "CONTRACT", "CUSTOMER", "DAY",
    "DAYS", "DETAINED", "DETENTION", "DOCK", "EMAIL", "FEE", "FOR", "FROM", "HAD", "HAS", "HOUR", "HOURS", "HRS",
    "INVOICE", "LOAD", "LOADED", "LOADING", "LOAD/UNLOAD", "LUMPER", "MILE", "MILES", "NOT", "PALLET", "PALLETS",
    "PPG", "QUOTE", "RATE", "RECEIPT", "SHIPMENT", "SHIPPER", "STOP", "THE", "TIME", "TRUCK", "UNLOAD", "UNLOADED",
    "UNLOADING", "WAIT", "WAITED", "WAITING", "WAS", "WITH",
}


def profile(rows: list[DisputeRow], notes: dict[str, Note]) -> dict:
    """Aggregates only. Notes never appear here."""
    disputed = sum((r.disputed for r in rows), Decimal(0))
    repeated = [r for r in rows if "repeated_invoice" in r.flags]
    reasons = collections.Counter(r.reason for r in rows)
    dates = sorted(r.event_date for r in rows if r.event_date)
    carriers = len({r.carrier for r in rows})
    return {
        "rows": len(rows),
        "blank_note_rows": sum("empty_note" in r.flags for r in rows),
        "distinct_notes": len(notes),
        "formats": len({n.format_key for n in notes.values()}),
        "carriers": carriers,
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "disputed_usd": str(disputed),
        "repeated_invoice_rows": len(repeated),
        "repeated_invoice_usd": str(sum((r.disputed for r in repeated), Decimal(0))),
        "non_positive_delta_rows": sum("non_positive_delta" in r.flags for r in rows),
        "catch_all_reason_share": round(reasons.most_common(1)[0][1] / len(rows), 3) if rows else 0,
        "strata": dict(sorted(collections.Counter(n.stratum for n in notes.values()).items())),
        "repeat_bands": dict(sorted(collections.Counter(n.band for n in notes.values()).items())),
        "scope_comparison": {
            "rows": {"dataset": len(rows), "scope": SCOPE_FIGURES["rows"], "matches": len(rows) == SCOPE_FIGURES["rows"]},
            "carriers": {"dataset": carriers, "scope": SCOPE_FIGURES["carriers"], "matches": carriers == SCOPE_FIGURES["carriers"]},
            "disputed_usd": {"dataset": str(disputed), "scope": "about 186000",
                             "matches": abs(disputed - SCOPE_FIGURES["disputed_usd"]) <= SCOPE_FIGURES["disputed_usd"] / 100},
        },
    }


def scan(notes: dict[str, Note]) -> dict:
    """Look for identifiers in note text. Snippets stay in this local report and are never printed."""
    findings = []
    for fp, note in notes.items():
        for kind, pattern in (("email", EMAIL), ("phone", PHONE)):
            findings += [{"fingerprint": fp, "note_id": note.note_id, "kind": kind, "snippet": m.group(0)}
                         for m in pattern.finditer(note.text)]
        findings += [{"fingerprint": fp, "note_id": note.note_id, "kind": "possible_name", "snippet": m.group(0)}
                     for m in NAME_CUE.finditer(note.text) if m.group(1).upper() not in NOT_A_NAME]
        findings += [{"fingerprint": fp, "note_id": note.note_id, "kind": "possible_name", "snippet": m.group(0)}
                     for m in NAME_FROM.finditer(note.text)]
    return {
        "counts": dict(sorted(collections.Counter(f["kind"] for f in findings).items())),
        "notes_flagged": len({f["fingerprint"] for f in findings}),
        "findings": findings,
    }


def check_external_send(ws: Workspace) -> set[str]:
    """Refuse an external model unless the dataset is cleared. Returns the notes to leave out of the send."""
    if ws.cfg.dataset_class != "open_anonymized":
        raise ContractError(f"data.dataset_class is {ws.cfg.dataset_class}: no text may go to an external model "
                            "until the file is confirmed as anonymized (ADR 0013)")
    if not ws.cfg.source_ref:
        raise ContractError("data.source_ref is empty: record where the dataset came from and Jake's confirmation")
    report = ws.read_json("scan_report.json")
    if not report["findings"]:
        return set()
    if not ws.exists("scan_decision.json"):
        raise ContractError(f"the scan flagged {report['notes_flagged']} notes: record a decision with "
                            "`gt scan-decision` before any text is sent")
    if ws.read_json("scan_decision.json")["decision"] == "exclude_flagged":
        return {f["fingerprint"] for f in report["findings"]}
    return set()


def _format_hash(note: Note) -> str:
    return hashlib.sha256(note.format_key.encode("utf-8")).hexdigest()[:12]


def _mark_formats(entries: list[dict]) -> None:
    train = {e["format_hash"] for e in entries if e["set"] == "TRAIN"}
    for entry in entries:
        entry["format_in_train"] = entry["format_hash"] in train if entry["set"] == "TEST" else None


def _take(cells: dict[tuple[str, str], list[str]], stratum: str, count: int) -> list[str]:
    """Take `count` notes from one stratum, across repeat bands, in proportion to what each band holds."""
    keys = sorted(k for k in cells if k[0] == stratum)
    available = sum(len(cells[k]) for k in keys)
    if available < count:
        raise ContractError(f"the dataset has {available} {stratum} notes left, and {count} are needed")
    if not count:
        return []
    shares = {k: len(cells[k]) * count / available for k in keys}
    grant = {k: int(shares[k]) for k in keys}
    for key in sorted(keys, key=lambda k: (grant[k] - shares[k], k))[: count - sum(grant.values())]:
        grant[key] += 1
    taken: list[str] = []
    for key in keys:
        taken += cells[key][: grant[key]]
        cells[key] = cells[key][grant[key]:]
    return taken


def build_split(notes: dict[str, Note], cfg: Config, pinned: set[str], dataset_sha256: str, blank_rows: int = 0,
                never_test: set[str] = frozenset()) -> dict:
    """Assign every distinct note to one set. The same seed always gives the same manifest.

    `pinned` notes go to TRAIN. `never_test` notes were read while drafting D1, so they cannot enter TEST or
    RESERVE, but they can still go to TRAIN or VALIDATION like any other note.
    """
    rng = random.Random(cfg.seed)
    assignment = {fp: "TRAIN" for fp in pinned if fp in notes}
    cells: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    held_back: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for fp, note in sorted(notes.items()):
        if fp not in assignment:
            (held_back if fp in never_test else cells)[(note.stratum, note.band)].append(fp)
    for group in (cells, held_back):
        for key in sorted(group):
            rng.shuffle(group[key])

    multi = TEST_SIZE - TEST_SINGLE - cfg.test_large_notes
    for stratum, count in (("single", TEST_SINGLE), ("multi", multi), ("large", cfg.test_large_notes)):
        assignment.update({fp: "TEST" for fp in _take(cells, stratum, count)})

    reserve_single = cfg.test_reserve_notes // 2
    other = cfg.test_reserve_notes - reserve_single
    left_multi = sum(len(v) for k, v in cells.items() if k[0] == "multi")
    left_large = sum(len(v) for k, v in cells.items() if k[0] == "large")
    reserve_large = round(other * left_large / (left_multi + left_large)) if left_multi + left_large else 0
    for stratum, count in (("single", reserve_single), ("multi", other - reserve_large), ("large", reserve_large)):
        assignment.update({fp: "RESERVE" for fp in _take(cells, stratum, count)})

    for key in sorted(held_back):
        cells[key] = sorted(cells.get(key, []) + held_back[key])
        rng.shuffle(cells[key])

    # VALIDATION's share is of everything outside TEST and RESERVE, including notes already fixed in TRAIN.
    remaining = sum(len(v) for v in cells.values())
    fixed_train = sum(s == "TRAIN" for s in assignment.values())
    wanted = round(cfg.validation_share * (fixed_train + remaining))
    share = min(1.0, wanted / remaining) if remaining else 0.0
    for key in sorted(cells):
        members = cells[key]
        cut = round(len(members) * share)
        assignment.update({fp: "VALIDATION" for fp in members[:cut]})
        assignment.update({fp: "TRAIN" for fp in members[cut:]})

    entries = [{
        "fingerprint": fp,
        "note_id": note.note_id,
        "set": assignment[fp],
        "provisional_stratum": note.stratum,
        "repeat_band": note.band,
        "rows": len(note.row_ids),
        "disputed_usd": str(note.usd),
        "format_hash": _format_hash(note),
    } for fp, note in sorted(notes.items())]
    _mark_formats(entries)
    manifest = {
        "dataset_sha256": dataset_sha256,
        "seed": cfg.seed,
        "params": {"validation_share": cfg.validation_share, "test_large_notes": cfg.test_large_notes,
                   "test_reserve_notes": cfg.test_reserve_notes},
        "blank_note_rows": blank_rows,
        "pinned_to_train": sorted(fp for fp in pinned if fp in notes),
        "pinned_not_in_dataset": sum(fp not in notes for fp in pinned),
        "read_while_drafting": sum(fp in notes for fp in never_test),
        "reserve_released": False,
        "notes": entries,
    }
    check_manifest(manifest)
    return manifest


def check_manifest(manifest: dict) -> None:
    """Every note belongs to exactly one set, and already-labelled notes are in TRAIN."""
    seen = collections.Counter(e["fingerprint"] for e in manifest["notes"])
    twice = [fp for fp, n in seen.items() if n > 1]
    if twice:
        raise ContractError(f"note in two sets: {twice[0]}")
    by_fp = {e["fingerprint"]: e for e in manifest["notes"]}
    for fp in manifest.get("pinned_to_train", []):
        if by_fp[fp]["set"] != "TRAIN":
            raise ContractError(f"already-labelled note is in {by_fp[fp]['set']}, not TRAIN: {by_fp[fp]['note_id']}")


def summarize(manifest: dict) -> dict:
    summary = {}
    for name in ("TEST", "RESERVE", "TRAIN", "VALIDATION"):
        members = [e for e in manifest["notes"] if e["set"] == name]
        summary[name] = {
            "notes": len(members),
            "rows": sum(e["rows"] for e in members),
            "disputed_usd": str(sum((Decimal(e["disputed_usd"]) for e in members), Decimal(0))),
            "strata": dict(sorted(collections.Counter(e["provisional_stratum"] for e in members).items())),
        }
    tests = [e for e in manifest["notes"] if e["set"] == "TEST"]
    summary["TEST"]["format_seen_in_train"] = sum(bool(e["format_in_train"]) for e in tests)
    summary["TEST"]["format_unseen_in_train"] = sum(not e["format_in_train"] for e in tests)
    return summary


def release_reserve(manifest: dict, cfg: Config) -> dict:
    """After sealing, unused reserve notes join TRAIN and VALIDATION. Nobody has seen them, so nothing leaks."""
    rng = random.Random(cfg.seed + 2)
    groups: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for entry in manifest["notes"]:
        if entry["set"] == "RESERVE":
            groups[(entry["provisional_stratum"], entry["repeat_band"])].append(entry)
    for key in sorted(groups):
        members = sorted(groups[key], key=lambda e: e["fingerprint"])
        rng.shuffle(members)
        cut = round(len(members) * cfg.validation_share)
        for index, entry in enumerate(members):
            entry["set"] = "VALIDATION" if index < cut else "TRAIN"
    _mark_formats(manifest["notes"])
    manifest["reserve_released"] = True
    check_manifest(manifest)
    return manifest


def notes_in_set(manifest: dict, name: str) -> list[str]:
    return [e["fingerprint"] for e in manifest["notes"] if e["set"] == name]


def is_note_text_in(value: str, notes: dict[str, Note], minimum: int = 25) -> bool:
    """True when a string in a Git-tracked file contains a whole note."""
    flat = normalize(value)
    return any(len(normalize(n.text)) >= minimum and normalize(n.text) in flat for n in notes.values())
