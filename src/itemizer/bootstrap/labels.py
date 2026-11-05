"""D2: labelling packs, label checks, agreement, client review and sealing.

People write every VALIDATION label. They write TEST labels too, unless the team has a model
draft them (ADR 0015). Accuracy measured against labels a model wrote only shows the tool
agreeing with them, so a draft is marked as one, and the final seal refuses any left unchecked.
These packs have no input for predictions at all.
"""
from __future__ import annotations

import collections
import csv
import json
import random
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.datavalidation import DataValidation

from .data import CENT, ContractError, GoldItem, Note, NoteLabel, Workspace, find_evidence, sha256_file
from .split import TEST_SINGLE, check_manifest, notes_in_set, release_reserve

ROWS_PER_NOTE = 5
DOUBLE_LABELLED = 50
SPOT_CHECK = 15
CLIENT_ROLE = "client_owner"
MODEL_ROLE = "model_provisional"
MODEL_DRAFT = "model_draft"  # the marker in a filled pack's comment column
_PERSON_SOURCES = ("person_checked", "person_corrected")
_REVIEW_PACK = "packs/test_label_review.xlsx"
_REVIEW_LABELS = "labels/test_label_review.json"
LINE_TYPES = ["charge", "tax", "already_paid"]
DERIVATIONS = ["stated", "rate_x_quantity"]
LABEL_COLUMNS = ["note_id", "carrier", "disputed_amount", "note", "item", "category", "amount", "evidence",
                 "line_type", "derivation", "no_charge_stated", "comment"]
_REVIEW_COLUMNS = LABEL_COLUMNS + ["priority", "checked"]
_NUMBER_WITH_THOUSANDS = re.compile(r"\d{1,3}(?:[ ,]\d{3})+(?:\.\d+)?")  # notes write "$1 277.68"
_PLAIN_NUMBER = re.compile(r"\d*\.\d+|\d+")  # includes ".67"

INSTRUCTIONS = [
    "Label each note by reading it yourself. Do not run the tool or ask a model while labelling.",
    "Add one line per charge: category, amount and the exact words the amount comes from (evidence).",
    "Evidence must be copied exactly from the note. Differences in spaces are fine; other changes are rejected.",
    "Totals and subtotals are not charges. For 'A $60 AND B $12 = $72 + GST $3.60 = $75.60', add 60.00, 12.00 and 3.60.",
    "Taxes: use line_type tax. Amounts already paid: use line_type already_paid. Everything else: charge.",
    "Use derivation stated when the note states the amount, even if it also shows a rate: '2 DAYS @ $150 EACH, ADD $300' is 300.00, and '2 DWELL DAYS @$300' is 300.00.",
    "Use derivation rate_x_quantity only when the note gives a rate and a quantity but no total. The amount is the product, with both factors in the evidence.",
    "Balance due with no other amount for that charge: the balance is the item. Choose the category from what the note says it is for, or other_unmapped if it does not say.",
    "Balance due beside listed charges ('FEE $20 BALANCE DUE $21'): list the charges. The balance is a total, not an item, and the row may be flagged. That is expected.",
    "One amount for several named charges, with no breakdown: add one line with category combined_charges.",
    "A number with no description at all: add one line with category other_unmapped.",
    "Spaces can separate thousands: '$1 277.68' is 1277.68.",
    "Never change an amount to make a row add up. If the items do not match the disputed amount, label what the note says.",
    "If the note states no charge, put Y in no_charge_stated and leave the item lines empty.",
    "If a note has more than five charges, copy a line and keep its note_id. Do not look at other labellers' files.",
]


def _write_categories(workbook, categories: list[dict]) -> int:
    sheet = workbook.create_sheet("Categories")
    sheet.append(["code", "name", "definition"])
    for category in categories:
        sheet.append([category["code"], category["name"], category["definition"]])
    return len(categories) + 1


def _dropdown(sheet, column: str, formula: str, last_row: int) -> None:
    rule = DataValidation(type="list", formula1=formula, allow_blank=True)
    sheet.add_data_validation(rule)
    rule.add(f"{column}2:{column}{max(last_row, 2)}")


def _style(sheet, widths: dict[str, int]) -> None:
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A2"


def _instructions(workbook, lines: list[str]) -> None:
    sheet = workbook.active
    sheet.title = "Instructions"
    for line in lines:
        sheet.append([line])
    sheet.column_dimensions["A"].width = 120
    for row in sheet.iter_rows():
        row[0].alignment = Alignment(wrap_text=True, vertical="top")


def _label_sheet(workbook, title: str, category_rows: int) -> tuple:
    sheet = workbook.create_sheet(title)
    sheet.append(LABEL_COLUMNS)
    return sheet, category_rows


def _finish_label_sheet(sheet, category_rows: int) -> None:
    last = sheet.max_row
    _dropdown(sheet, "F", f"Categories!$A$2:$A${category_rows}", last)
    _dropdown(sheet, "I", '"' + ",".join(LINE_TYPES) + '"', last)
    _dropdown(sheet, "J", '"' + ",".join(DERIVATIONS) + '"', last)
    _dropdown(sheet, "K", '"Y"', last)
    _style(sheet, {"A": 14, "B": 24, "C": 19, "D": 60, "E": 6, "F": 26, "G": 12, "H": 48, "I": 16, "J": 22, "K": 21, "L": 32})
    sheet.row_dimensions[1].height = 30
    for cell in sheet[1]:
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    sheet.auto_filter.ref = sheet.dimensions


def write_pack(path: Path, set_name: str, fingerprints: list[str], notes: dict[str, Note],
               categories: list[dict], suggestions: dict | None = None) -> None:
    """One labelling workbook: notes, carrier, disputed amount and the taxonomy, with no tool output."""
    if suggestions and set_name != "TRAIN":
        raise ContractError(f"{set_name} labels are written by people: model suggestions are allowed only in TRAIN packs")
    workbook = openpyxl.Workbook()
    _instructions(workbook, INSTRUCTIONS)
    category_rows = _write_categories(workbook, categories)
    sheet, _ = _label_sheet(workbook, "Labels", category_rows)
    for fp in fingerprints:
        note = notes[fp]
        suggested = (suggestions or {}).get(note.note_id, [])
        for index in range(max(ROWS_PER_NOTE, len(suggested))):
            first = index == 0
            line = [note.note_id, note.carrier if first else None, float(note.disputed) if first else None,
                    note.text if first else None, index + 1, None, None, None, None, None, None, None]
            if index < len(suggested):
                item = suggested[index]
                line[5:10] = [item["category"], float(item["amount"]), item["evidence"], item["line_type"], item["derivation"]]
                line[11] = "model_suggestion"
            sheet.append(line)
    _finish_label_sheet(sheet, category_rows)
    for row in sheet.iter_rows(min_row=2, max_col=4, min_col=4):
        row[0].alignment = Alignment(wrap_text=True, vertical="top")
    workbook.move_sheet("Labels", offset=-1)
    workbook.active = workbook.sheetnames.index("Labels")
    workbook.save(path)


def choose_packs(manifest: dict, seed: int) -> dict[str, list[str]]:
    """Who labels what: 50 notes twice, across both strata, 150 once, and a spot check of 15 of those."""
    rng = random.Random(seed + 3)
    entries = {e["fingerprint"]: e for e in manifest["notes"]}
    test = notes_in_set(manifest, "TEST")
    singles = sorted(fp for fp in test if entries[fp]["provisional_stratum"] == "single")
    others = sorted(fp for fp in test if entries[fp]["provisional_stratum"] != "single")
    rng.shuffle(singles)
    rng.shuffle(others)
    half = DOUBLE_LABELLED // 2
    double = sorted(singles[:half] + others[: DOUBLE_LABELLED - half])
    rest = sorted(set(test) - set(double))
    rng.shuffle(rest)
    return {
        "label_A": double,
        "label_B": double,
        "label_single": sorted(rest),
        "spot_check": sorted(rest[:SPOT_CHECK]),
        # Large and multi-charge notes first, so the first notes labelled are the scarce ones calibration needs.
        "validation": sorted(notes_in_set(manifest, "VALIDATION"),
                             key=lambda fp: (["large", "multi", "single"].index(entries[fp]["provisional_stratum"]), fp)),
        "train": sorted(notes_in_set(manifest, "TRAIN")),
    }


def build_packs(ws: Workspace, manifest: dict, notes: dict[str, Note], categories: list[dict],
                train_suggestions: dict | None = None) -> dict[str, list[str]]:
    if ws.exists("labels"):
        raise ContractError("labels have been imported, so the packs cannot be rebuilt")
    packs = choose_packs(manifest, ws.cfg.seed)
    if ws.exists("packs.json") and ws.read_json("packs.json") != packs:
        raise ContractError("rebuilding would change who labels what")
    sets = {"validation": "VALIDATION", "train": "TRAIN"}
    for name, members in packs.items():
        write_pack(ws.path(f"packs/{name}.xlsx"), sets.get(name, "TEST"), members, notes, categories,
                   train_suggestions if name == "train" else None)
    ws.write_json("packs.json", packs)
    return packs


def _strict_amount(value) -> Decimal | None:
    try:
        amount = Decimal(str(value).replace(",", "").replace("$", "").strip())
        rounded = amount.quantize(CENT)  # raises on 1e30, Infinity and NaN, which a typed cell can hold
        return rounded if rounded == amount.normalize() or abs(rounded - amount) < Decimal("0.000001") else None
    except (InvalidOperation, ValueError):
        return None


def _products(numbers: list[Decimal]) -> set[Decimal]:
    products = set()
    for index, first in enumerate(numbers):
        for second in numbers[index + 1:]:
            try:
                products.add((first * second).quantize(CENT))
            except InvalidOperation:  # a product too long for Decimal cannot be the amount of a charge
                pass
    return products


def _numbers(text: str) -> list[Decimal]:
    """Every way the text's digits can be read as numbers, so a correct amount is never rejected."""
    tokens = _NUMBER_WITH_THOUSANDS.findall(text) + _PLAIN_NUMBER.findall(text)
    return [Decimal(re.sub(r"[ ,]", "", token)) for token in tokens]


def check_item(note: Note, item_no: int, category: str, amount_raw, evidence: str, line_type: str, derivation: str,
               codes: set[str]) -> tuple[GoldItem | None, list[tuple[str, str]]]:
    """Check one labelled charge against the note. Returns the item, or the reasons it was rejected."""
    errors: list[tuple[str, str]] = []
    if category not in codes:
        errors.append(("unknown_category", f"category {category!r} is not in the taxonomy"))
    amount = _strict_amount(amount_raw)
    if amount is None:
        errors.append(("bad_amount", f"amount {amount_raw!r} must be a number with at most two decimals"))
    if line_type not in LINE_TYPES:
        errors.append(("bad_line_type", f"line_type {line_type!r} must be one of {', '.join(LINE_TYPES)}"))
    if derivation not in DERIVATIONS:
        errors.append(("bad_derivation", f"derivation {derivation!r} must be one of {', '.join(DERIVATIONS)}"))
    span = find_evidence(note.text, evidence)
    if span is None:
        errors.append(("evidence_not_verbatim", "the evidence is not copied exactly from the note"))
    if amount is not None and span is not None:
        numbers = _numbers(evidence)
        if derivation == "rate_x_quantity":
            if amount not in _products(numbers):
                errors.append(("product_mismatch", f"{amount} is not the product of two numbers in the evidence"))
        elif derivation == "stated" and all(n != amount for n in numbers):
            errors.append(("amount_not_in_evidence", f"{amount} does not appear in the evidence"))
    if errors:
        return None, errors
    return GoldItem(item=item_no, category=category, amount=amount, evidence_text=note.text[span[0]:span[1]],
                    evidence_start=span[0], evidence_end=span[1], line_type=line_type, derivation=derivation), []


def _read_label_lines(path: Path, sheet_name: str) -> list[tuple[int, dict]]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet_name not in workbook.sheetnames:
            raise ContractError(f"{path.name} has no {sheet_name} sheet")
        rows = workbook[sheet_name].iter_rows(values_only=True)
        header = [str(c) if c is not None else "" for c in next(rows)]
        return [(n, dict(zip(header, raw))) for n, raw in enumerate(rows, start=2)]
    finally:
        workbook.close()


def _clean(value) -> str:
    return "" if value is None else str(value).strip()


def parse_lines(lines: list[tuple[int, dict]], allowed: set[str], notes: dict[str, Note], codes: set[str],
                labeller: str, pack: str) -> tuple[dict[str, NoteLabel], list[dict]]:
    """Check returned lines. A note with any failure is rejected and goes back to the labeller."""
    by_id = {notes[fp].note_id: notes[fp] for fp in allowed}
    grouped: dict[str, list[tuple[int, dict]]] = collections.defaultdict(list)
    errors: list[dict] = []
    for number, line in lines:
        note_id = _clean(line.get("note_id"))
        if not note_id:
            continue
        if note_id not in by_id:
            errors.append({"note_id": note_id, "row": number, "code": "unknown_note", "message": "this note is not in this pack"})
            continue
        grouped[note_id].append((number, line))
    labels: dict[str, NoteLabel] = {}
    for note_id, note_lines in sorted(grouped.items()):
        note = by_id[note_id]
        items: list[GoldItem] = []
        bad = False
        flagged = any(_clean(l.get("no_charge_stated")).upper() == "Y" for _, l in note_lines)
        suggested = drafted = False
        comment = ""
        for number, line in note_lines:
            text = _clean(line.get("comment"))
            if text == "model_suggestion":
                suggested = True
            elif text.startswith(MODEL_DRAFT):
                drafted = True
                comment = text.removeprefix(MODEL_DRAFT).lstrip(":")  # the doubt the model reported, if any
            elif text:
                comment = text
            fields = [_clean(line.get(k)) for k in ("category", "amount", "evidence", "line_type", "derivation")]
            if not any(fields):
                continue
            item, problems = check_item(note, len(items) + 1, fields[0], line.get("amount"), fields[2], fields[3], fields[4], codes)
            if problems:
                bad = True
                errors += [{"note_id": note_id, "row": number, "code": code, "message": message} for code, message in problems]
            else:
                items.append(item)
        if flagged and items:
            bad = True
            errors.append({"note_id": note_id, "row": note_lines[0][0], "code": "flag_with_items",
                           "message": "no_charge_stated is Y, but the note also has items"})
        if not flagged and not items and not bad:
            bad = True
            errors.append({"note_id": note_id, "row": note_lines[0][0], "code": "not_labelled", "message": "no items and no no_charge_stated flag"})
        if not bad:
            labels[note.fingerprint] = NoteLabel(
                fingerprint=note.fingerprint, note_id=note_id, labeller=labeller, pack=pack, no_charge_stated=flagged,
                items=items, source="model_suggestion_confirmed" if suggested else (MODEL_DRAFT if drafted else "human"), comment=comment)
    for note_id, note in sorted(by_id.items()):
        if note_id not in grouped:
            errors.append({"note_id": note_id, "row": 0, "code": "not_labelled", "message": "this note is missing from the file"})
    return labels, errors


def import_labels(ws: Workspace, pack: str, path: Path, labeller: str, notes: dict[str, Note], codes: set[str]) -> dict:
    packs = ws.read_json("packs.json")
    if pack not in packs:
        raise ContractError(f"unknown pack {pack}; packs are {', '.join(sorted(packs))}")
    if ws.exists("seal_record.json") and pack not in ("validation", "train"):
        raise ContractError("TEST is sealed, so its labels cannot change; a correction needs a new version")
    if ws.exists("provisional_record.json") and pack in ("label_A", "label_B", "label_single"):
        raise ContractError("TEST is frozen, so these labels cannot change; only the client's review can correct them")
    labels, errors = parse_lines(_read_label_lines(path, "Labels"), set(packs[pack]), notes, codes, labeller, pack)
    ws.write_json(f"labels/{pack}.json", {
        "pack": pack, "labeller": labeller, "source_sha256": sha256_file(path), "errors": errors,
        "labels": {fp: label.model_dump(mode="json") for fp, label in labels.items()},
    })
    with ws.path(f"labels/{pack}.errors.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["note_id", "row", "code", "message"])
        writer.writeheader()
        writer.writerows(errors)
    return {"pack": pack, "notes_expected": len(packs[pack]), "notes_accepted": len(labels), "errors": len(errors),
            "error_codes": dict(collections.Counter(e["code"] for e in errors))}


def _stored_labels(ws: Workspace, pack: str) -> dict[str, NoteLabel]:
    return {fp: NoteLabel.model_validate(v) for fp, v in ws.read_json(f"labels/{pack}.json")["labels"].items()}


def _as_tuples(label: NoteLabel) -> list[tuple[str, Decimal]]:
    return sorted((i.category, i.amount) for i in label.items)


def _kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa. None when there is nothing to compare."""
    if not pairs:
        return None
    total = len(pairs)
    observed = sum(a == b for a, b in pairs) / total
    left, right = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    expected = sum(left[c] * right[c] for c in set(left) | set(right)) / (total * total)
    return 1.0 if expected == 1 else round((observed - expected) / (1 - expected), 4)


def agreement(a: dict[str, NoteLabel], b: dict[str, NoteLabel]) -> dict:
    """Compare the two labellers on the double-labelled notes."""
    pairs: list[tuple[str, str]] = []
    disagreements = []
    amount_match = count_match = 0
    shared = sorted(set(a) & set(b))
    for fp in shared:
        left, right = a[fp], b[fp]
        reasons = []
        if left.no_charge_stated != right.no_charge_stated:
            reasons.append("no_charge_flag")
        if len(left.items) != len(right.items):
            reasons.append("item_count")
        else:
            count_match += 1
        left_amounts = sorted(i.amount for i in left.items)
        right_amounts = sorted(i.amount for i in right.items)
        if left_amounts == right_amounts:
            amount_match += 1
        else:
            reasons.append("amount")
        remaining = list(right.items)
        for item in left.items:
            partner = next((other for other in remaining if other.amount == item.amount), None)
            if partner is not None:
                remaining.remove(partner)
                pairs.append((item.category, partner.category))
        if not reasons and _as_tuples(left) != _as_tuples(right):
            reasons.append("category")
        if reasons:
            disagreements.append({"fingerprint": fp, "note_id": left.note_id, "reasons": reasons})
    return {
        "notes_compared": len(shared),
        "cohens_kappa_category": _kappa(pairs),
        "amount_exact_match": amount_match,
        "item_count_match": count_match,
        "disagreements": disagreements,
    }


def _describe(label: NoteLabel) -> str:
    if label.no_charge_stated:
        return "no charge stated"
    return "\n".join(f"{i.item}. {i.category} {i.amount} [{i.evidence_text}]" for i in label.items)


def write_client_pack(ws: Workspace, notes: dict[str, Note], categories: list[dict]) -> dict:
    """All 50 double-labelled notes for Jake or a PPG accountant, not only the disagreements."""
    a, b = _stored_labels(ws, "label_A"), _stored_labels(ws, "label_B")
    packs = ws.read_json("packs.json")
    missing = [fp for fp in packs["label_A"] if fp not in a or fp not in b]
    if missing:
        raise ContractError(f"{len(missing)} double-labelled notes still lack a valid label from both labellers")
    report = agreement(a, b)
    ws.write_json("agreement.json", report)
    flagged = {d["fingerprint"] for d in report["disagreements"]}
    workbook = openpyxl.Workbook()
    _instructions(workbook, [
        "Please review every note on the Review sheet. Each one was labelled twice, separately. A labeller named claude is a model.",
        "In decision, choose accept_A or accept_B, or choose correct and add the right items on the Corrections sheet.",
        "If team_correction is filled, the team changed this label after reading the note. Choose accept_correction to keep it.",
        "Notes marked YES in disagreement differ between the two labellers. Notes marked NO agree, but please still check them.",
        "Totals and subtotals are not charges. Please do not decide here whether a charge should be paid.",
    ] + INSTRUCTIONS[1:3])
    category_rows = _write_categories(workbook, categories)
    review = workbook.create_sheet("Review")
    review.append(["note_id", "carrier", "disputed_amount", "note", "labeller_A", "labeller_B", "disagreement", "decision", "comment", "team_correction"])
    team = _team_review(ws)
    for fp in packs["label_A"]:
        note = notes[fp]
        corrected = team[fp] if fp in team and team[fp].source == "person_corrected" else None
        review.append([note.note_id, note.carrier, float(note.disputed), note.text, _describe(a[fp]), _describe(b[fp]),
                       "YES" if fp in flagged else "NO", None, None, _describe(corrected) if corrected else None])
    _dropdown(review, "H", '"accept_A,accept_B,correct,accept_correction"', review.max_row)
    _style(review, {"A": 13, "B": 10, "C": 10, "D": 50, "E": 40, "F": 40, "G": 12, "H": 12, "I": 25})
    for row in review.iter_rows(min_row=2):
        for cell in row[3:6]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    corrections, _ = _label_sheet(workbook, "Corrections", category_rows)
    _finish_label_sheet(corrections, category_rows)
    workbook.save(ws.path("packs/client_review.xlsx"))
    return report


def _check_review_can_be_replaced(ws: Workspace, reviewer_role: str) -> None:
    """The client's review replaces a team's. Tool output can be seen once TEST is frozen, so a team's review cannot."""
    if ws.exists("seal_record.json"):
        raise ContractError("TEST is sealed, so its review cannot change; a correction needs a new version")
    if reviewer_role == CLIENT_ROLE:
        return
    if ws.exists("provisional_record.json"):
        raise ContractError(f"TEST is frozen, so only the client's review (role {CLIENT_ROLE}) can change its labels")
    if ws.exists("client_review.json") and ws.read_json("client_review.json")["reviewer_role"] == CLIENT_ROLE:
        raise ContractError(f"the client's review is already imported, so a review by {reviewer_role} cannot replace it")


def import_client_review(ws: Workspace, path: Path, reviewer_role: str, date: str, notes: dict[str, Note], codes: set[str]) -> dict:
    _check_review_can_be_replaced(ws, reviewer_role)
    packs = ws.read_json("packs.json")
    a, b = _stored_labels(ws, "label_A"), _stored_labels(ws, "label_B")
    team = _team_review(ws)
    report = ws.read_json("agreement.json")
    flagged = {d["fingerprint"] for d in report["disagreements"]}
    expected = {notes[fp].note_id: fp for fp in packs["label_A"]}
    corrections, errors = parse_lines(
        [item for item in _read_label_lines(path, "Corrections") if _clean(item[1].get("note_id"))],
        set(packs["label_A"]), notes, codes, reviewer_role, "client_review")
    errors = [e for e in errors if not (e["code"] == "not_labelled" and e["row"] == 0)]
    decisions, seen = {}, set()
    for number, line in _read_label_lines(path, "Review"):
        note_id = _clean(line.get("note_id"))
        if note_id not in expected:
            continue
        fp = expected[note_id]
        seen.add(note_id)
        decision = _clean(line.get("decision"))
        if decision == "accept_A":
            label = a[fp]
        elif decision == "accept_B":
            label = b[fp]
        elif decision == "correct":
            label = corrections.get(fp)
            if label is None:
                errors.append({"note_id": note_id, "row": number, "code": "correction_missing", "message": "decision is correct, but the Corrections sheet has no valid items"})
                continue
        elif decision == "accept_correction":
            label = team.get(fp)
            if label is None:
                errors.append({"note_id": note_id, "row": number, "code": "correction_missing", "message": "decision is accept_correction, but the team has not corrected this note"})
                continue
        else:
            errors.append({"note_id": note_id, "row": number, "code": "not_reviewed", "message": "this note has no decision"})
            continue
        if reviewer_role == CLIENT_ROLE and label.source == MODEL_DRAFT:  # the client has now read it
            label = label.model_copy(update={"source": "person_checked"})
        changed = fp not in flagged and _as_tuples(label) != _as_tuples(a[fp])
        decisions[fp] = {"decision": decision, "changed_agreed_label": changed, "was_disagreement": fp in flagged,
                         "label": label.model_dump(mode="json")}
    errors += [{"note_id": n, "row": 0, "code": "not_reviewed", "message": "this note is missing from the review"} for n in sorted(set(expected) - seen)]
    ws.write_json("client_review.json", {"reviewer_role": reviewer_role, "date": date, "source_sha256": sha256_file(path),
                                         "decisions": decisions, "errors": errors})
    return {"reviewed": len(decisions), "expected": len(expected), "errors": len(errors),
            "changed_agreed_labels": sum(d["changed_agreed_label"] for d in decisions.values()),
            "error_codes": dict(collections.Counter(e["code"] for e in errors))}


def gold_labels(ws: Workspace) -> dict[str, NoteLabel]:
    """The labeller's answer, then what people checked or corrected. The client's decision on the 50 notes wins over a team's."""
    gold = dict(_stored_labels(ws, "label_single"))
    if ws.exists("labels/label_replacements.json"):
        gold.update(_stored_labels(ws, "label_replacements"))
    review = ws.read_json("client_review.json")
    decisions = {fp: NoteLabel.model_validate(decision["label"]) for fp, decision in review["decisions"].items()}
    layers = [_team_review(ws), decisions] if review["reviewer_role"] == CLIENT_ROLE else [decisions, _team_review(ws)]
    for layer in layers:
        gold.update(layer)
    return gold


def _team_review(ws: Workspace) -> dict[str, NoteLabel]:
    if not ws.exists(_REVIEW_LABELS):
        return {}
    return {fp: NoteLabel.model_validate(v) for fp, v in ws.read_json(_REVIEW_LABELS)["labels"].items()}


def current_test_labels(ws: Workspace) -> dict[str, NoteLabel]:
    return load_test_gold(ws)[0] if is_test_frozen(ws) else gold_labels(ws)


def _review_priority(label: NoteLabel, note: Note, disagreed: set[str], large_usd: Decimal) -> tuple[int, str]:
    """Which notes most need a person, first."""
    if label.source in _PERSON_SOURCES:
        return 6, "already_checked"
    if note.fingerprint in disagreed:
        return 0, "labellers_disagreed"
    if label.comment:
        return 1, f"model_doubt:{label.comment}"
    if note.max_disputed >= large_usd:
        return 2, "large_dispute"
    if len(label.items) >= 2:
        return 3, "several_charges"
    if label.no_charge_stated:
        return 4, "no_charge_stated"
    return 5, ""


def _write_text(cell, value: str | None) -> None:
    cell.value = value
    if value is not None:
        cell.data_type = "s"  # note text and evidence can start with "=", and must not become formulas


def write_label_review(ws: Workspace, manifest: dict, notes: dict[str, Note], categories: list[dict]) -> dict:
    """Every TEST note with its current label, the notes most in need of a person first. It holds no tool output."""
    if ws.exists("seal_record.json"):
        raise ContractError("TEST is sealed, so its labels cannot change; a correction needs a new version")
    test = notes_in_set(manifest, "TEST")
    current = current_test_labels(ws)
    missing = [fp for fp in test if fp not in current]
    if missing:
        raise ContractError(f"{len(missing)} TEST notes have no label yet, so there is nothing to review for them")
    _refuse_old_codes(current, {category["code"] for category in categories})
    disagreed = {d["fingerprint"] for d in ws.read_json("agreement.json")["disagreements"]}
    ranked = {fp: _review_priority(current[fp], notes[fp], disagreed, ws.cfg.large_dispute_usd) for fp in test}
    workbook = openpyxl.Workbook()
    _instructions(workbook, ["Go through the Labels sheet from the top. deliverables/reviewing_test_labels.md explains the steps.",
                             "Do not open data/runs or any itemized.xlsx while reviewing: those hold the tool's answers.",
                             "If a label is right, put Y in checked. If it is wrong, change it. A changed label counts as checked."] + INSTRUCTIONS[1:-1])
    category_rows = _write_categories(workbook, categories)
    sheet = workbook.create_sheet("Labels")
    sheet.append(_REVIEW_COLUMNS)
    for fp in sorted(test, key=lambda fp: (ranked[fp][0], notes[fp].note_id)):
        note, label = notes[fp], current[fp]
        for index in range(len(label.items) + 1):  # one blank line, for a charge the label missed
            item = label.items[index] if index < len(label.items) else None
            first = index == 0
            sheet.append([note.note_id, note.carrier if first else None, float(note.disputed) if first else None, None, index + 1,
                          item.category if item else None, float(item.amount) if item else None, None, item.line_type if item else None,
                          item.derivation if item else None, "Y" if first and label.no_charge_stated else None, label.comment if first else None,
                          ranked[fp][1] if first else None, "Y" if first and label.source in _PERSON_SOURCES else None])
            row = sheet[sheet.max_row]
            _write_text(row[3], note.text if first else None)
            _write_text(row[7], item.evidence_text if item else None)
    _finish_label_sheet(sheet, category_rows)
    _dropdown(sheet, "N", '"Y"', sheet.max_row)
    sheet.column_dimensions["M"].width = 24
    sheet.column_dimensions["N"].width = 8
    for row in sheet.iter_rows(min_row=2, max_col=4, min_col=4):
        row[0].alignment = Alignment(wrap_text=True, vertical="top")
    workbook.move_sheet("Labels", offset=-1)
    workbook.active = workbook.sheetnames.index("Labels")
    path = ws.path(_REVIEW_PACK)
    workbook.save(path)
    order = collections.Counter(reason.split(":")[0] or "rest" for _, reason in ranked.values())
    return {"notes": len(test), "by_priority": dict(sorted(order.items())), "workbook": str(path.relative_to(ws.project_root))}


def _refuse_old_codes(labels: dict[str, NoteLabel], codes: set[str]) -> None:
    """Find-and-replace in the workbook would mark every unread draft as corrected, and this is the only state that invites it."""
    old = sorted({item.category for label in labels.values() for item in label.items} - set(codes))
    if old:
        raise ContractError(f"current labels hold categories no longer in the list: {', '.join(old)}. Run `itemizer gt rename-category "
                            "<old> <new>` first. Do not use find-and-replace, which marks unread labels as corrected")


def check_not_sealed(ws: Workspace) -> None:
    if ws.exists("seal_record.json"):
        raise ContractError("TEST is sealed, so its labels cannot change; a correction needs a new version")


def _rename_items(label: dict, old: str, new: str) -> int:
    changed = 0
    for item in label.get("items", []):
        if item["category"] == old:
            item["category"] = new
            changed += 1
    return changed


def rename_category(ws: Workspace, old: str, new: str) -> dict:
    """Change a code in every stored label. Each label keeps its `source`, because nobody read a note to do this."""
    check_not_sealed(ws)
    changed: collections.Counter = collections.Counter()
    folder = ws.root / "labels"
    for path in sorted(folder.glob("*.json")) if folder.exists() else []:
        stored = json.loads(path.read_text(encoding="utf-8"))
        changed[path.name] = sum(_rename_items(label, old, new) for label in stored.get("labels", {}).values())
        if changed[path.name]:
            ws.write_json(f"labels/{path.name}", stored)
    if ws.exists("client_review.json"):
        review = ws.read_json("client_review.json")
        changed["client_review.json"] = sum(_rename_items(decision["label"], old, new) for decision in review["decisions"].values())
        ws.write_json("client_review.json", review)
    if ws.exists("provisional_record.json"):
        frozen = ws.read_json("test_provisional.json")
        changed["test_provisional.json"] = sum(_rename_items(label, old, new) for label in frozen["labels"].values())
        digest = sha256_file(ws.write_json("test_provisional.json", frozen))
        record = ws.read_json("provisional_record.json")
        record["sha256"] = digest
        ws.write_json("provisional_record.json", record)
    with ws.path("labels/category_renames.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"old": old, "new": new, "changed": dict(sorted(changed.items()))}, sort_keys=True) + "\n")
    return {name: count for name, count in sorted(changed.items()) if count}


def _label_content(label: NoteLabel) -> tuple:
    return (label.no_charge_stated, sorted((i.category, i.amount, i.evidence_text, i.line_type, i.derivation) for i in label.items))


def _update_frozen(ws: Workspace, reviewed: dict[str, NoteLabel], notes: dict[str, Note], corrected: int) -> None:
    """Change the reviewed notes in the frozen labels and nothing else, so a client's review still waits for the final seal."""
    frozen = ws.read_json("test_provisional.json")
    for fp, label in reviewed.items():
        frozen["labels"][fp] = label.model_dump(mode="json")
        frozen["strata"][fp] = gold_stratum(label, notes[fp], ws.cfg.large_dispute_usd)
    digest = sha256_file(ws.write_json("test_provisional.json", frozen))
    record = ws.read_json("provisional_record.json")
    sources = collections.Counter(label["source"] for label in frozen["labels"].values())
    record.update(sha256=digest, sources=dict(sorted(sources.items())), single=sum(s == "single" for s in frozen["strata"].values()),
                  multi_or_large=sum(s != "single" for s in frozen["strata"].values()),
                  corrected_after_freeze=record.get("corrected_after_freeze", 0) + corrected)
    ws.write_json("provisional_record.json", record)


def import_label_review(ws: Workspace, path: Path, reviewer: str, date: str, manifest: dict, notes: dict[str, Note], codes: set[str]) -> dict:
    """Take back what people checked or changed. Any failure rejects the whole file, and no label changes."""
    if ws.exists("seal_record.json"):
        raise ContractError("TEST is sealed, so its labels cannot change; a correction needs a new version")
    if not reviewer.strip():
        raise ContractError("name the reviewer, because the labels record who checked them")
    test = set(notes_in_set(manifest, "TEST"))
    current = current_test_labels(ws)
    _refuse_old_codes(current, codes)
    lines = _read_label_lines(path, "Labels")
    checked = {_clean(line.get("note_id")) for _, line in lines if _clean(line.get("checked")).upper() == "Y"}
    parsed, errors = parse_lines(lines, test, notes, codes, f"person:{reviewer.strip()}", "test_label_review")
    errors = [e for e in errors if not (e["code"] == "not_labelled" and e["row"] == 0)]  # a partial review is fine
    review = ws.read_json("client_review.json") if ws.exists("client_review.json") else {"reviewer_role": "", "decisions": {}}
    client_decided = set(review["decisions"]) if review["reviewer_role"] == CLIENT_ROLE else set()
    reviewed: dict[str, NoteLabel] = {}
    corrected: list[str] = []
    for fp, label in parsed.items():
        before = current.get(fp)
        changed = before is None or _label_content(label) != _label_content(before)
        if not changed and (label.note_id not in checked or before.source in _PERSON_SOURCES):
            continue  # untouched, or already checked: the workbook marks those Y, and the person who checked it stays on record
        if fp in client_decided:
            if changed:
                errors.append({"note_id": label.note_id, "row": 0, "code": "client_decided", "message": "the client's review decided this note, and that decision stands"})
            continue
        if changed:
            corrected.append(fp)
        reviewed[fp] = label.model_copy(update={"source": "person_corrected" if changed else "person_checked"})
    with ws.path("labels/test_label_review.errors.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["note_id", "row", "code", "message"])
        writer.writeheader()
        writer.writerows(errors)
    if errors:
        return {"errors": len(errors), "error_codes": dict(collections.Counter(e["code"] for e in errors)), "reviewed": 0, "corrected": 0}
    stored = ws.read_json(_REVIEW_LABELS)["labels"] if ws.exists(_REVIEW_LABELS) else {}
    stored.update({fp: label.model_dump(mode="json") for fp, label in reviewed.items()})
    ws.write_json(_REVIEW_LABELS, {"labels": stored})
    if ws.exists("provisional_record.json") and reviewed:
        _update_frozen(ws, reviewed, notes, len(corrected))
    with ws.path("labels/test_label_review_log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"date": date, "reviewer": reviewer.strip(), "source_sha256": sha256_file(path), "reviewed": len(reviewed),
                                 "corrected_note_ids": sorted(notes[fp].note_id for fp in corrected)}, sort_keys=True) + "\n")
    return {"errors": 0, "reviewed": len(reviewed), "corrected": len(corrected), "label_sources": label_sources(ws)}


def gold_stratum(label: NoteLabel, note: Note, large_dispute_usd: Decimal) -> str:
    if note.max_disputed >= large_dispute_usd:
        return "large"
    return "multi" if len(label.items) >= 2 else "single"


def plan_replacements(single_count: int, other_count: int, limit: int) -> tuple[str | None, int]:
    """Which side has too many notes, and how many to replace to come back within the limit."""
    gap = single_count - TEST_SINGLE
    excess = abs(gap) - limit
    if excess <= 0:
        return None, 0
    return ("single" if gap > 0 else "other"), excess


def final_strata(ws: Workspace, manifest: dict, notes: dict[str, Note], apply: bool = False) -> dict:
    """Replace provisional strata with strata from the gold items, and fix the mix from the reserve if needed."""
    packs = ws.read_json("packs.json")
    gold = gold_labels(ws)
    test = notes_in_set(manifest, "TEST")
    strata = {fp: gold_stratum(gold[fp], notes[fp], ws.cfg.large_dispute_usd) for fp in test if fp in gold}
    singles = [fp for fp, s in strata.items() if s == "single"]
    others = [fp for fp, s in strata.items() if s != "single"]
    side, count = plan_replacements(len(singles), len(others), ws.cfg.max_stratum_gap_notes)
    result = {"labelled": len(strata), "single": len(singles), "multi_or_large": len(others), "replace": count, "shortage": 0}
    if not count:
        return result
    rng = random.Random(ws.cfg.seed + 4)
    double = set(packs["label_A"])
    # Notes the client already reviewed are kept, because that review is the scarcest work in D2.
    droppable = sorted(fp for fp in (singles if side == "single" else others) if fp not in double)
    rng.shuffle(droppable)
    entries = {e["fingerprint"]: e for e in manifest["notes"]}
    want_single = side == "other"
    reserve = sorted(fp for fp in notes_in_set(manifest, "RESERVE") if (entries[fp]["provisional_stratum"] == "single") == want_single)
    rng.shuffle(reserve)
    swaps = min(count, len(droppable), len(reserve))
    result["shortage"] = count - swaps
    result["drop_note_ids"] = [notes[fp].note_id for fp in droppable[:swaps]]
    result["add_note_ids"] = [notes[fp].note_id for fp in reserve[:swaps]]
    if apply and swaps:
        for fp in droppable[:swaps]:
            entries[fp]["set"] = "TRAIN"  # labelled and blind to the tool, so it is safe and useful for building
        for fp in reserve[:swaps]:
            entries[fp]["set"] = "TEST"
        packs["label_replacements"] = sorted(reserve[:swaps])
        ws.write_json("packs.json", packs)
        check_manifest(manifest)
    return result


def _review_problems(ws: Workspace, test: list[str]) -> list[str]:
    """What every freeze needs: 200 notes, valid labels, and a complete review that resolves each disagreement."""
    packs = ws.read_json("packs.json")
    problems = []
    if len(set(test)) != 200:
        problems.append(f"TEST has {len(set(test))} distinct notes, not 200")
    for pack in ("label_A", "label_B", "label_single") + (("label_replacements",) if "label_replacements" in packs else ()):
        if not ws.exists(f"labels/{pack}.json"):
            problems.append(f"{pack} has not been imported")
            continue
        errors = ws.read_json(f"labels/{pack}.json")["errors"]
        if errors:
            problems.append(f"{pack} has {len(errors)} label errors")
    if not ws.exists("client_review.json"):
        problems.append("the review has not been imported")
        return problems
    review = ws.read_json("client_review.json")
    missing_review = [fp for fp in packs["label_A"] if fp not in review["decisions"]]
    if missing_review:
        problems.append(f"the reviewer has not reviewed {len(missing_review)} of the {len(packs['label_A'])} double-labelled notes")
    if review["errors"]:
        problems.append(f"the review has {len(review['errors'])} problems")
    unresolved = [d["note_id"] for d in ws.read_json("agreement.json")["disagreements"] if d["fingerprint"] not in review["decisions"]]
    if unresolved:
        problems.append(f"{len(unresolved)} disagreements are unresolved")
    return problems


def _gold_and_mix(ws: Workspace, test: list[str], notes: dict[str, Note]) -> tuple[dict[str, NoteLabel], dict[str, str], list[str]]:
    gold = gold_labels(ws)
    problems = []
    unlabelled = [fp for fp in test if fp not in gold]
    if unlabelled:
        problems.append(f"{len(unlabelled)} TEST notes have no gold label")
    strata = {fp: gold_stratum(gold[fp], notes[fp], ws.cfg.large_dispute_usd) for fp in test if fp in gold}
    singles = sum(s == "single" for s in strata.values())
    if plan_replacements(singles, len(strata) - singles, ws.cfg.max_stratum_gap_notes)[1]:
        problems.append(f"the labelled mix is {singles} single and {len(strata) - singles} other; run `gt final-strata --apply`")
    return gold, strata, problems


def _write_frozen(ws: Workspace, labels_name: str, record_name: str, test: list[str], gold: dict[str, NoteLabel], strata: dict[str, str]) -> dict:
    """Write the frozen labels, then their record. The record comes last because it is what marks TEST as frozen."""
    digest = sha256_file(ws.write_json(labels_name, {
        "labels": {fp: gold[fp].model_dump(mode="json") for fp in sorted(test)},
        "strata": {fp: strata[fp] for fp in sorted(test)},
    }))
    review = ws.read_json("client_review.json")
    singles = sum(s == "single" for s in strata.values())
    record = {"sha256": digest, "notes": len(test), "single": singles, "multi_or_large": len(strata) - singles,
              "agreement": {k: v for k, v in ws.read_json("agreement.json").items() if k != "disagreements"},
              "changed_agreed_labels": sum(d["changed_agreed_label"] for d in review["decisions"].values()),
              "sources": dict(sorted(collections.Counter(gold[fp].source for fp in test).items())),
              "reviewer_role": review["reviewer_role"], "review_date": review["date"]}
    ws.write_json(record_name, record)
    return record


def seal(ws: Workspace, manifest: dict, notes: dict[str, Note], approved: set[str] | None, mapping: dict[str, str] | None = None) -> dict:
    """Seal TEST only when every condition holds. Afterwards TEST can only change through a new version."""
    if ws.exists("seal_record.json"):
        raise ContractError("TEST is already sealed; a correction needs a new version")
    test = notes_in_set(manifest, "TEST")
    problems = _review_problems(ws, test)
    if ws.exists("client_review.json"):
        role = ws.read_json("client_review.json")["reviewer_role"]
        if role != CLIENT_ROLE:
            problems.append(f"the review is by {role}, and the final seal needs the client's review (role {CLIENT_ROLE})")
    if problems:
        return _refuse(problems)
    gold, strata, problems = _gold_and_mix(ws, test, notes)
    drafts = sum(gold[fp].source == MODEL_DRAFT for fp in test if fp in gold)
    if drafts:
        problems.append(f"{drafts} TEST labels are model drafts that no person has checked. See deliverables/reviewing_test_labels.md")
    if approved is None:
        problems.append("the taxonomy has no valid client approval")
    else:
        mapping = mapping or {}
        unknown = {i.category for fp in test if fp in gold for i in gold[fp].items if mapping.get(i.category, i.category) not in approved}
        if unknown:
            problems.append("labels use categories outside the approved list, with no mapping: " + ", ".join(sorted(unknown)))
    if problems:
        return _refuse(problems)

    if mapping:  # the frozen labels use the approved codes, or scoring would count false category errors
        ws.write_json("category_mapping.json", mapping)
        gold = {fp: label.model_copy(update={"items": [i.model_copy(update={"category": mapping.get(i.category, i.category)})
                                                       for i in label.items]})
                for fp, label in gold.items()}
    ws.path("test_fingerprints.txt").write_text("\n".join(sorted(test)) + "\n", encoding="utf-8")
    record = _write_frozen(ws, "test_sealed.json", "seal_record.json", test, gold, strata)
    ws.write_json("split_manifest.json", release_reserve(manifest, ws.cfg))
    return record


def seal_provisional(ws: Workspace, manifest: dict, notes: dict[str, Note], codes: set[str]) -> dict:
    """Freeze TEST on team-resolved labels, so evaluation can start before the client's review.

    It needs no approval and keeps the reserve. It runs once: a run on all rows may follow it, so labels changed
    afterwards could be following the tool. Only the client's review and the final seal change the labels from here.
    """
    if ws.exists("seal_record.json"):
        raise ContractError("TEST is already sealed; a correction needs a new version")
    if ws.exists("provisional_record.json"):
        raise ContractError("TEST is already frozen; the next step is the client's review and the final seal")
    test = notes_in_set(manifest, "TEST")
    problems = _review_problems(ws, test)
    if problems:
        return _refuse(problems, "frozen")
    gold, strata, problems = _gold_and_mix(ws, test, notes)
    unknown = {i.category for fp in test if fp in gold for i in gold[fp].items if i.category not in codes}
    if unknown:
        problems.append("labels use categories outside the current list: " + ", ".join(sorted(unknown)))
    if problems:
        return _refuse(problems, "frozen")
    return _write_frozen(ws, "test_provisional.json", "provisional_record.json", test, gold, strata)


def label_sources(ws: Workspace) -> dict[str, int]:
    """How many current TEST labels came from where: the frozen ones, or the imported ones until then."""
    if is_test_frozen(ws):
        labels = load_test_gold(ws)[0]
    else:
        labels = {}
        for pack in ("label_single", "label_replacements", "label_A"):
            if ws.exists(f"labels/{pack}.json"):
                labels.update(_stored_labels(ws, pack))
    return dict(sorted(collections.Counter(label.source for label in labels.values()).items()))


def is_test_frozen(ws: Workspace) -> bool:
    return ws.exists("seal_record.json") or ws.exists("provisional_record.json")


def load_test_gold(ws: Workspace) -> tuple[dict[str, NoteLabel], str]:
    """TEST's frozen labels and their status: `sealed` once the final seal exists, otherwise `provisional`."""
    if ws.exists("seal_record.json"):
        record, name, status = "seal_record.json", "test_sealed.json", "sealed"
    elif ws.exists("provisional_record.json"):
        record, name, status = "provisional_record.json", "test_provisional.json", "provisional"
    else:
        raise ContractError("TEST is not frozen; run `gt seal --provisional` or `gt seal` first")
    if not ws.exists(name) or sha256_file(ws.path(name)) != ws.read_json(record)["sha256"]:
        raise ContractError(f"{name} is missing or was changed after {record} was written")
    return {fp: NoteLabel.model_validate(v) for fp, v in ws.read_json(name)["labels"].items()}, status


def _refuse(problems: list[str], outcome: str = "sealed") -> dict:
    raise ContractError(f"TEST cannot be {outcome}: " + "; ".join(problems))
