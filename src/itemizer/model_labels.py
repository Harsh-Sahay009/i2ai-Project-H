"""TEST labels drafted by a model, on the team's decision (ADR 0015).

A draft is a proposal for a person to check. Accuracy against drafts shows how far the tool agrees with them, and not that it
is right, so each one is stored as `model_draft`, and the final seal refuses any left unchecked. The labeller sees the
labelling rules, the category list and the note, and never tool output.
"""
from __future__ import annotations

import collections
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import openpyxl

from . import pipeline
from .bootstrap import labels as lb
from .bootstrap.data import ContractError, Note
from .contracts import NoteResult
from .itemize import _describe_category, itemize_notes

LABEL_PROMPT = Path("prompts/label_v1.md")
FIRST_LABELLER = "claude-opus-5-5-label-high"
SECOND_LABELLER = "claude-opus-5-5-label-xhigh"
_TEST_PACKS = ("label_A", "label_B", "label_single", "label_replacements")
_CLIENT_REVIEW = "packs/client_review.xlsx"


def build_label_prompt(categories: list[dict], template: Path) -> str:
    """The same rules a person gets, leaving out the two lines about working in Excel and not asking a model."""
    if not template.is_file():
        raise ContractError(f"prompt not found: {template}")
    text = template.read_text(encoding="utf-8")
    if "{{rules}}" not in text or "{{categories}}" not in text:
        raise ContractError(f"{template.name} must hold both {{{{rules}}}} and {{{{categories}}}}")
    rules = "\n".join(f"- {line}" for line in lb.INSTRUCTIONS[1:-1])
    described = "\n".join(_describe_category(c) for c in sorted(categories, key=lambda c: c["code"]))
    return text.replace("{{rules}}", rules).replace("{{categories}}", described)


def _write_text(cell, value: str) -> None:
    cell.value = value
    cell.data_type = "s"  # evidence can start with "=", and must not be read back as a formula


def fill_pack(blank: Path, target: Path, results: dict[str, NoteResult]) -> None:
    """Copy a blank pack with the model's answers written in, for the same import a person's workbook goes through."""
    by_id = {result.note_id: result for result in results.values() if result.status == "ok"}
    workbook = openpyxl.load_workbook(blank)
    sheet = workbook["Labels"]
    at = {cell.value: index for index, cell in enumerate(sheet[1])}
    marker = {result.note_id: lb.MODEL_DRAFT if result.reason_code == "none" else f"{lb.MODEL_DRAFT}:{result.reason_code}" for result in by_id.values()}

    def write_item(row, item) -> None:
        row[at["category"]].value = item.category
        row[at["amount"]].value = float(item.amount)
        _write_text(row[at["evidence"]], item.evidence_text)
        row[at["line_type"]].value = item.line_type
        row[at["derivation"]].value = item.derivation

    lines = 0
    written: collections.Counter = collections.Counter()
    for row in sheet.iter_rows(min_row=2):
        lines += 1
        note_id = row[at["note_id"]].value
        result = by_id.get(note_id)
        if result is None:
            continue
        index = written[note_id]
        written[note_id] += 1
        if index == 0:
            row[at["comment"]].value = marker[note_id]
            if result.no_charge_stated:
                row[at["no_charge_stated"]].value = "Y"
        if index < len(result.items):
            write_item(row, result.items[index])
    for note_id, result in by_id.items():  # a note with more charges than its blank lines gets more lines
        for item in result.items[written[note_id]:]:
            lines += 1
            sheet.append([None] * len(at))
            row = sheet[lines + 1]
            row[at["note_id"]].value = note_id
            row[at["item"]].value = item.item
            write_item(row, item)
    target.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(target)


def _accept_first_labeller(project: pipeline.Project, categories: list[dict], today: str) -> dict:
    """Resolve the double-labelled notes as labeller A. The disagreements come first in the workbook people review."""
    ws = project.ws
    report = lb.write_client_pack(ws, project.notes, categories)
    workbook = openpyxl.load_workbook(ws.path(_CLIENT_REVIEW))
    sheet = workbook["Review"]
    decision = [cell.value for cell in sheet[1]].index("decision")
    for row in sheet.iter_rows(min_row=2):
        row[decision].value = "accept_A"
    target = ws.path("packs/filled/client_review.model.xlsx")
    workbook.save(target)
    imported = lb.import_client_review(ws, target, lb.MODEL_ROLE, today, project.notes, {c["code"] for c in categories})
    return {"notes_compared": report["notes_compared"], "cohens_kappa_category": report["cohens_kappa_category"],
            "amount_exact_match": report["amount_exact_match"], "disagreements": len(report["disagreements"]),
            "reviewed": imported["reviewed"], "review_errors": imported["errors"]}


def _packs_to_draft(project: pipeline.Project) -> dict[str, list[str]]:
    assignments = project.ws.read_json("packs.json")
    return {pack: assignments[pack] for pack in _TEST_PACKS if pack in assignments}


def plan_test_labels(root: Path, first_model: str = FIRST_LABELLER, second_model: str = SECOND_LABELLER) -> dict:
    """What `--send` would do. It sends nothing."""
    project = pipeline.load_project(root)
    pipeline.choose_model(root, first_model)
    pipeline.choose_model(root, second_model)
    pipeline._budget(project.settings)
    return {"dry_run": True, "notes_per_pack": {pack: len(members) for pack, members in _packs_to_draft(project).items()},
            "first_model": first_model, "second_model": second_model,
            "budget_usd": str(project.settings["budget"]["max_usd_per_run"])}


def _spent(path: Path) -> Decimal:
    lines = path.read_text(encoding="utf-8").splitlines()
    return sum((Decimal(json.loads(line)["cost_usd"]) for line in lines), Decimal(0))


def draft_test_labels(root: Path, today: str, first_model: str = FIRST_LABELLER, second_model: str = SECOND_LABELLER) -> dict:
    """Draft and import the TEST labels. A repeat replays the cache, so it continues where a budget or a failure stopped."""
    project = pipeline.load_project(root)
    ws = project.ws
    if ws.exists("seal_record.json") or ws.exists("provisional_record.json"):
        raise ContractError("TEST is frozen, so its labels are changed through `gt import-label-review`")
    categories = project.categories()
    codes = {c["code"] for c in categories}
    system = build_label_prompt(categories, root / LABEL_PROMPT)
    first, second = pipeline.choose_model(root, first_model), pipeline.choose_model(root, second_model)
    left_out = pipeline._left_out_of_send(project, first, project.notes, True) | pipeline._left_out_of_send(project, second, project.notes, True)
    budget = pipeline._budget(project.settings)
    concurrency = project.settings.get("runtime", {}).get("concurrency", 8)
    report: dict = {"packs": {}, "system_prompt_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest()}
    new_spend = Decimal(0)
    for pack, members in _packs_to_draft(project).items():
        blank = ws.path(f"packs/{pack}.xlsx")
        if not blank.is_file():
            raise ContractError(f"the blank pack {pack} does not exist; run `itemizer gt label-packs --replacements`")
        spec = second if pack == "label_B" else first
        wanted: dict[str, Note] = {fp: project.notes[fp] for fp in members if fp not in left_out}
        telemetry = ws.path(f"labels/{pack}.telemetry.jsonl")
        results = itemize_notes(wanted, pipeline.get_provider(spec, project_root=root), codes, system, project.data_root / "cache" / "labels",
                                budget, concurrency, telemetry)
        new_spend += _spent(telemetry)
        filled = ws.path(f"packs/filled/{pack}.model.xlsx")
        fill_pack(blank, filled, results)
        imported = lb.import_labels(ws, pack, filled, spec.name, project.notes, codes)
        no_answer = collections.Counter(result.review_reason for result in results.values() if result.status != "ok")
        report["packs"][pack] = {"model": spec.name, "notes": len(members), "labelled": imported["notes_accepted"], "errors": imported["errors"],
                                 "error_codes": imported["error_codes"], "no_answer": dict(no_answer), "left_out_after_scan": len(members) - len(wanted),
                                 "in_doubt": sum(result.reason_code != "none" for result in results.values()),
                                 "no_charge_stated": sum(result.no_charge_stated for result in results.values())}
    report["spent_this_run_usd"] = str(new_spend)
    complete = all(ws.read_json(f"labels/{pack}.json")["errors"] == [] for pack in report["packs"])
    if complete:
        report["agreement"] = _accept_first_labeller(project, categories, today)
        report["mix"] = lb.final_strata(ws, project.split, project.notes)
    report["complete"] = complete
    ws.log("draft-test-labels", [root / LABEL_PROMPT], [], first_model=first_model, second_model=second_model, spent_usd=str(new_spend), complete=complete)
    return report
