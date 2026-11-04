"""Tests per scenario for people checking and correcting TEST labels. Every note is invented, and every model is a fake."""
from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest
from test_bootstrap import fill_review
from test_model_labels import labels  # noqa: F401 (a fixture)
from test_pipeline import CODES, NOTE_WORDS, ROOT, d3  # noqa: F401 (d3 is a fixture)
from typer.testing import CliRunner

from itemizer import acceptance, model_labels, pipeline
from itemizer.bootstrap import labels as lb
from itemizer.bootstrap import split as sp
from itemizer.bootstrap import taxonomy as tx
from itemizer.bootstrap.data import ContractError
from itemizer.cli import app

runner = CliRunner()
REVIEWER = "A Reviewer"


@pytest.fixture
def drafted(labels):  # noqa: F811
    assert model_labels.draft_test_labels(labels.tmp, "2026-11-03")["complete"]
    return labels


@pytest.fixture
def frozen(drafted):
    assert "sha256" in lb.seal_provisional(drafted.ws, drafted.ws.read_json("split_manifest.json"), drafted.notes, CODES)
    return drafted


def write_pack(world) -> Path:
    lb.write_label_review(world.ws, world.ws.read_json("split_manifest.json"), world.notes, tx.load_taxonomy(world.tmp / pipeline.CATEGORIES)["categories"])
    return world.ws.path("packs/test_label_review.xlsx")


def lines_of(path: Path) -> list[dict]:
    sheet = openpyxl.load_workbook(path)["Labels"]
    head = [cell.value for cell in sheet[1]]
    return [dict(zip(head, row, strict=True)) for row in sheet.iter_rows(min_row=2, values_only=True)]


def edit(path: Path, change) -> None:
    """`change(line)` gets each row as a dict of its cells."""
    workbook = openpyxl.load_workbook(path)
    sheet = workbook["Labels"]
    head = [cell.value for cell in sheet[1]]
    for row in sheet.iter_rows(min_row=2):
        change(dict(zip(head, row, strict=True)))
    workbook.save(path)


def do_import(world, path: Path, reviewer: str = REVIEWER) -> dict:
    return lb.import_label_review(world.ws, path, reviewer, "2026-11-04", world.ws.read_json("split_manifest.json"), world.notes, CODES)


def single_charge_note(world) -> str:
    """A note with one charge, from the single-labelled pack."""
    current = lb.current_test_labels(world.ws)
    return next(current[fp].note_id for fp in world.packs["label_single"] if len(current[fp].items) == 1)


def mark_checked(*note_ids):
    def change(line):
        if line["note_id"].value in note_ids and line["item"].value == 1:
            line["checked"].value = "Y"
    return change


def set_category(note_id: str, code: str = "cat_5"):
    def change(line):
        if line["note_id"].value == note_id and line["item"].value == 1:
            line["category"].value = code
    return change


def by_id(world, note_id: str):
    return next(label for label in lb.current_test_labels(world.ws).values() if label.note_id == note_id)


# ---- the workbook
def test_the_workbook_holds_every_test_note_with_its_label(drafted):
    lines = lines_of(write_pack(drafted))
    test = set(sp.notes_in_set(drafted.manifest, "TEST"))
    assert {line["note_id"] for line in lines} == {drafted.notes[fp].note_id for fp in test}
    current = lb.current_test_labels(drafted.ws)
    for fp in test:
        note_lines = [line for line in lines if line["note_id"] == drafted.notes[fp].note_id]
        assert len(note_lines) == len(current[fp].items) + 1  # with one blank line for a missed charge
        assert [Decimal(str(line["amount"])) for line in note_lines[:-1]] == [item.amount for item in current[fp].items]
        assert note_lines[0]["note"] == drafted.notes[fp].text


def test_disagreements_and_doubts_come_first_and_say_why(drafted):
    current = lb.current_test_labels(drafted.ws)
    agreement = drafted.ws.read_json("agreement.json")
    a_note = drafted.packs["label_A"][0]
    agreement["disagreements"] = [{"fingerprint": a_note, "note_id": drafted.notes[a_note].note_id, "reasons": ["category"]}]
    drafted.ws.write_json("agreement.json", agreement)
    doubtful = next(fp for fp in drafted.packs["label_single"] if drafted.notes[fp].max_disputed < Decimal("180"))
    stored = drafted.ws.read_json("labels/label_single.json")
    stored["labels"][doubtful]["comment"] = "amount_unclear"
    drafted.ws.write_json("labels/label_single.json", stored)
    assert current
    first = [line for line in lines_of(write_pack(drafted)) if line["priority"]]
    assert first[0]["note_id"] == drafted.notes[a_note].note_id and first[0]["priority"] == "labellers_disagreed"
    assert first[1]["note_id"] == drafted.notes[doubtful].note_id and first[1]["priority"] == "model_doubt:amount_unclear"
    assert first[2]["priority"] == "large_dispute"


def test_a_note_already_checked_comes_last(frozen):
    note_id = single_charge_note(frozen)
    path = write_pack(frozen)
    edit(path, mark_checked(note_id))
    do_import(frozen, path)
    lines = lines_of(write_pack(frozen))
    last = [line for line in lines if line["priority"]][-1]
    assert last["note_id"] == note_id and last["priority"] == "already_checked" and last["checked"] == "Y"


def test_no_tool_output_reaches_the_workbook(frozen):
    outcome = pipeline.run(frozen.tmp)
    book = openpyxl.load_workbook(write_pack(frozen))
    assert set(book.sheetnames) == {"Labels", "Instructions", "Categories"}
    head = [cell.value for cell in book["Labels"][1]]
    assert not {"outcome", "outcome_reason", "difference", "ai_reason", "items_total"} & set(head)
    assert outcome.run_id not in str(list(book["Labels"].values))


def test_a_note_starting_with_an_equals_sign_stays_text(drafted):
    path = write_pack(drafted)
    assert all(cell.data_type != "f" for row in openpyxl.load_workbook(path)["Labels"].iter_rows() for cell in row)


def test_the_workbook_cannot_be_written_while_notes_have_no_label(labels):  # noqa: F811
    labels.ws.write_json("client_review.json", {"reviewer_role": lb.MODEL_ROLE, "decisions": {}, "errors": []})
    labels.ws.write_json("labels/label_single.json", {"labels": {}, "errors": []})
    with pytest.raises(ContractError, match="200 TEST notes have no label"):
        write_pack(labels)


# ---- one command for checks and corrections
def test_an_untouched_workbook_changes_nothing(frozen):
    before = frozen.ws.path("test_provisional.json").read_bytes()
    result = do_import(frozen, write_pack(frozen))
    assert result["reviewed"] == 0 and result["corrected"] == 0 and result["errors"] == 0
    assert frozen.ws.path("test_provisional.json").read_bytes() == before


def test_marking_a_label_right_records_the_person(frozen):
    note_id = single_charge_note(frozen)
    path = write_pack(frozen)
    edit(path, mark_checked(note_id))
    result = do_import(frozen, path)
    assert result["reviewed"] == 1 and result["corrected"] == 0
    label = by_id(frozen, note_id)
    assert label.source == "person_checked" and label.labeller == f"person:{REVIEWER}"
    assert result["label_sources"] == {"model_draft": 199, "person_checked": 1}


def test_a_change_without_the_flag_is_taken_as_a_correction(frozen):
    note_id = single_charge_note(frozen)
    path = write_pack(frozen)
    edit(path, set_category(note_id))
    assert do_import(frozen, path)["corrected"] == 1
    label = by_id(frozen, note_id)
    assert label.source == "person_corrected" and label.items[0].category == "cat_5"


def test_a_missed_charge_can_be_added_on_the_blank_line(frozen):
    current = lb.current_test_labels(frozen.ws)
    fp = next(fp for fp in frozen.packs["label_single"] if len(current[fp].items) == 2)
    note = frozen.notes[fp]
    total = note.text.split(" = ")[1]
    path = write_pack(frozen)

    def add(line):
        if line["note_id"].value == note.note_id and line["item"].value == 3:
            line["category"].value = "cat_1"
            line["amount"].value = float(total.lstrip("$"))
            line["evidence"].value = total
            line["line_type"].value = "charge"
            line["derivation"].value = "stated"

    edit(path, add)
    assert do_import(frozen, path)["corrected"] == 1
    assert len(by_id(frozen, note.note_id).items) == 3


def test_a_label_can_be_changed_to_no_charge_stated(frozen):
    note_id = single_charge_note(frozen)
    path = write_pack(frozen)

    def clear(line):
        if line["note_id"].value == note_id:
            for key in ("category", "amount", "evidence", "line_type", "derivation"):
                line[key].value = None
            if line["item"].value == 1:
                line["no_charge_stated"].value = "Y"

    edit(path, clear)
    do_import(frozen, path)
    label = by_id(frozen, note_id)
    assert label.no_charge_stated and label.items == [] and label.source == "person_corrected"


def test_an_invalid_correction_rejects_the_whole_file(frozen):
    good, bad = [lb.current_test_labels(frozen.ws)[fp].note_id for fp in frozen.packs["label_single"][:2]]
    path = write_pack(frozen)
    edit(path, set_category(good))

    def wrong_amount(line):
        if line["note_id"].value == bad and line["item"].value == 1:
            line["amount"].value = 99999.99

    edit(path, wrong_amount)
    before = frozen.ws.path("test_provisional.json").read_bytes()
    result = do_import(frozen, path)
    assert result["errors"] == 1 and result["error_codes"] == {"amount_not_in_evidence": 1} and result["reviewed"] == 0
    assert frozen.ws.path("test_provisional.json").read_bytes() == before and not frozen.ws.exists("labels/test_label_review.json")
    assert by_id(frozen, good).source == "model_draft"
    assert bad in frozen.ws.path("labels/test_label_review.errors.csv").read_text(encoding="utf-8")


def test_a_rejected_file_exits_with_a_message_and_no_note_text(frozen):
    note_id = single_charge_note(frozen)
    path = write_pack(frozen)

    def wrong(line):
        if line["note_id"].value == note_id and line["item"].value == 1:
            line["amount"].value = 99999.99

    edit(path, wrong)
    result = runner.invoke(app, ["gt", "import-label-review", str(path), "--reviewer", REVIEWER, "--date", "2026-11-04"])
    assert result.exit_code == 1 and "Nothing changed" in result.stdout
    assert not any(word in result.stdout for word in NOTE_WORDS)


def test_a_note_outside_test_is_refused(frozen):
    path = write_pack(frozen)
    outsider = frozen.notes[sp.notes_in_set(frozen.manifest, "TRAIN")[0]].note_id

    def rename(line):
        if line["item"].value == 1 and line["priority"].value == "large_dispute":
            line["note_id"].value = outsider

    edit(path, rename)
    assert "unknown_note" in do_import(frozen, path)["error_codes"]


def test_a_partial_review_adds_to_the_last_one(frozen):
    first, second = [fp for fp in frozen.packs["label_single"]][:2]
    path = write_pack(frozen)
    edit(path, mark_checked(frozen.notes[first].note_id))
    do_import(frozen, path, "One")
    path = write_pack(frozen)
    edit(path, mark_checked(frozen.notes[second].note_id))
    result = do_import(frozen, path, "Two")
    assert result["label_sources"] == {"model_draft": 198, "person_checked": 2}
    assert by_id(frozen, frozen.notes[first].note_id).labeller == "person:One"
    log = [json.loads(line) for line in frozen.ws.path("labels/test_label_review_log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [entry["reviewer"] for entry in log] == ["One", "Two"]


def test_a_correction_stays_marked_when_it_is_later_checked_again(frozen):
    note_id = single_charge_note(frozen)
    path = write_pack(frozen)
    edit(path, set_category(note_id))
    do_import(frozen, path)
    result = do_import(frozen, write_pack(frozen), "Someone Else")  # the workbook now marks it Y
    assert result["reviewed"] == 0 and by_id(frozen, note_id).source == "person_corrected"
    assert by_id(frozen, note_id).labeller == f"person:{REVIEWER}"


def test_the_reviewer_must_be_named(frozen):
    with pytest.raises(ContractError, match="name the reviewer"):
        do_import(frozen, write_pack(frozen), "  ")


def test_a_note_the_client_decided_cannot_be_changed(drafted):
    assert lb.import_client_review(drafted.ws, fill_review(drafted), lb.CLIENT_ROLE, "2026-11-05", drafted.notes, CODES)["errors"] == 0
    note_id = drafted.notes[drafted.packs["label_A"][0]].note_id
    path = write_pack(drafted)
    edit(path, set_category(note_id))
    result = do_import(drafted, path)
    assert result["error_codes"] == {"client_decided": 1} and result["reviewed"] == 0


def test_after_the_final_seal_it_refuses(frozen):
    path = write_pack(frozen)
    _check_everything(frozen)
    assert lb.import_client_review(frozen.ws, fill_review(frozen), lb.CLIENT_ROLE, "2026-11-05", frozen.notes, CODES)["errors"] == 0
    assert "sha256" in lb.seal(frozen.ws, frozen.ws.read_json("split_manifest.json"), frozen.notes, CODES)
    with pytest.raises(ContractError, match="TEST is sealed"):
        do_import(frozen, path)
    with pytest.raises(ContractError, match="TEST is sealed"):
        write_pack(frozen)


def _check_everything(world) -> None:
    path = write_pack(world)

    def mark(line):
        if line["item"].value == 1:
            line["checked"].value = "Y"

    edit(path, mark)
    assert do_import(world, path)["errors"] == 0


def test_a_review_before_the_freeze_is_taken_into_it(drafted):
    note_id = single_charge_note(drafted)
    path = write_pack(drafted)
    edit(path, set_category(note_id))
    do_import(drafted, path)
    assert "sha256" in lb.seal_provisional(drafted.ws, drafted.ws.read_json("split_manifest.json"), drafted.notes, CODES)
    label = by_id(drafted, note_id)
    assert label.source == "person_corrected" and label.items[0].category == "cat_5"
    assert drafted.ws.read_json("provisional_record.json").get("corrected_after_freeze", 0) == 0


# ---- correcting a frozen test set
def test_a_correction_after_the_freeze_updates_the_frozen_labels_and_its_record(frozen):
    note_id = single_charge_note(frozen)
    path = write_pack(frozen)
    edit(path, set_category(note_id))
    do_import(frozen, path)
    gold, status = lb.load_test_gold(frozen.ws)  # it checks the file's hash against the record
    assert status == "provisional" and next(label for label in gold.values() if label.note_id == note_id).items[0].category == "cat_5"
    record = frozen.ws.read_json("provisional_record.json")
    assert record["corrected_after_freeze"] == 1 and record["sources"] == {"model_draft": 199, "person_corrected": 1}


def test_a_later_team_import_does_not_pull_in_the_clients_review(frozen):
    client_note = frozen.packs["label_A"][0]
    workbook_path = fill_review(frozen)
    assert lb.import_client_review(frozen.ws, workbook_path, lb.CLIENT_ROLE, "2026-11-05", frozen.notes, CODES)["errors"] == 0
    before = lb.load_test_gold(frozen.ws)[0][client_note]
    path = write_pack(frozen)
    edit(path, set_category(single_charge_note(frozen)))
    do_import(frozen, path)
    assert lb.load_test_gold(frozen.ws)[0][client_note] == before and before.source == "model_draft"


def test_the_page_counts_corrections_after_the_freeze(frozen):
    path = write_pack(frozen)
    edit(path, set_category(single_charge_note(frozen)))
    do_import(frozen, path)
    summary = acceptance.d3_check(frozen.tmp)
    assert summary["d2"]["corrected_after_freeze"] == 1 and summary["d2"]["written_by_model"] == 199 and summary["d2"]["checked_by_person"] == 1
    assert "1 label was corrected after TEST was frozen" in Path(summary["page"]).read_text(encoding="utf-8")


# ---- running the test again
def test_correcting_a_label_and_scoring_again_needs_no_model_and_no_budget(frozen):
    outcome = pipeline.run(frozen.tmp)
    first = pipeline.evaluate_run(frozen.tmp, outcome.run_id)
    calls = len(frozen.calls)
    assert first["accuracy"]["correct"] == first["accuracy"]["n"]
    path = write_pack(frozen)
    edit(path, set_category(single_charge_note(frozen)))
    do_import(frozen, path)
    result = runner.invoke(app, ["evaluate", "--run", outcome.run_id])
    assert result.exit_code == 0, result.stderr
    second = json.loads((frozen.tmp / "data" / "kpi" / f"{outcome.run_id}_d3.json").read_text(encoding="utf-8"))
    assert len(frozen.calls) == calls and second["test_budget"]["event"] == "rescored"
    assert second["labels_sha256"] != first["labels_sha256"]
    assert second["accuracy"]["correct"] == first["accuracy"]["correct"] - 1
    assert second["labels_sources"] == {"model_draft": 199, "person_corrected": 1}


def test_all_checked_then_the_client_and_the_seal_close_d3(frozen):
    run_id = pipeline.run(frozen.tmp).run_id
    pipeline.evaluate_run(frozen.tmp, run_id)
    _check_everything(frozen)
    assert lb.import_client_review(frozen.ws, fill_review(frozen), lb.CLIENT_ROLE, "2026-11-05", frozen.notes, CODES)["errors"] == 0
    assert "sha256" in lb.seal(frozen.ws, frozen.ws.read_json("split_manifest.json"), frozen.notes, CODES)
    snapshot = pipeline.evaluate_run(frozen.tmp, run_id)
    assert snapshot["labels_status"] == "sealed" and "model_draft" not in snapshot["labels_sources"]
    email = frozen.tmp / "email.txt"
    email.write_text("Seen.", encoding="utf-8")
    acceptance.record_review(frozen.tmp, "2026-11-05", email)
    summary = acceptance.d3_check(frozen.tmp)
    assert summary["d3"]["status"] == "done" and summary["d2"]["written_by_model"] == 0


def test_the_client_can_keep_a_team_correction(frozen):
    note = frozen.notes[frozen.packs["label_A"][0]]
    path = write_pack(frozen)
    edit(path, set_category(note.note_id))
    do_import(frozen, path)
    categories = tx.load_taxonomy(frozen.tmp / pipeline.CATEGORIES)["categories"]
    lb.write_client_pack(frozen.ws, frozen.notes, categories)
    review_path = fill_review(frozen)
    workbook = openpyxl.load_workbook(review_path)
    sheet = workbook["Review"]
    head = [cell.value for cell in sheet[1]]
    row = next(row for row in sheet.iter_rows(min_row=2) if row[0].value == note.note_id)
    assert "cat_5" in row[head.index("team_correction")].value
    row[head.index("decision")].value = "accept_correction"
    workbook.save(review_path)
    assert lb.import_client_review(frozen.ws, review_path, lb.CLIENT_ROLE, "2026-11-05", frozen.notes, CODES)["errors"] == 0
    assert lb.gold_labels(frozen.ws)[note.fingerprint].items[0].category == "cat_5"


def test_the_clients_decision_wins_over_a_team_correction_it_did_not_keep(frozen):
    note = frozen.notes[frozen.packs["label_A"][0]]
    original = by_id(frozen, note.note_id).items[0].category
    path = write_pack(frozen)
    edit(path, set_category(note.note_id))
    do_import(frozen, path)
    assert lb.gold_labels(frozen.ws)[note.fingerprint].items[0].category == "cat_5"
    assert lb.import_client_review(frozen.ws, fill_review(frozen, "accept_A"), lb.CLIENT_ROLE, "2026-11-05", frozen.notes, CODES)["errors"] == 0
    assert lb.gold_labels(frozen.ws)[note.fingerprint].items[0].category == original != "cat_5"


def test_accept_correction_needs_a_correction(drafted):
    review_path = fill_review(drafted, decision="accept_correction")
    result = lb.import_client_review(drafted.ws, review_path, lb.CLIENT_ROLE, "2026-11-05", drafted.notes, CODES)
    assert result["error_codes"] == {"correction_missing": 50}


# ---- the instruction file
def test_every_command_in_the_instruction_file_exists():
    text = (ROOT / "deliverables/reviewing_test_labels.md").read_text(encoding="utf-8")
    commands = re.findall(r"itemizer ((?:gt |acceptance )?[a-z][a-z0-9-]*)", text)
    assert len(set(commands)) >= 10
    for command in set(commands):
        result = runner.invoke(app, [*command.split(), "--help"])
        assert result.exit_code == 0, command


def test_every_priority_in_the_instruction_file_is_one_the_workbook_writes():
    text = (ROOT / "deliverables/reviewing_test_labels.md").read_text(encoding="utf-8")
    for word in ("labellers_disagreed", "model_doubt", "large_dispute", "several_charges", "no_charge_stated", "already_checked"):
        assert f"`{word}" in text


# ---- renaming a category
def rename(*args):
    return runner.invoke(app, ["gt", "rename-category", *args])


def codes_of(world) -> set[str]:
    return {category["code"] for category in tx.load_taxonomy(world.tmp / pipeline.CATEGORIES)["categories"]}


def snapshot_of_labels(world) -> dict:
    names = ["labels/label_A.json", "labels/label_B.json", "labels/label_single.json", "client_review.json", "test_provisional.json", "provisional_record.json"]
    return {name: world.ws.path(name).read_text(encoding="utf-8") for name in names} | {
        "list": (world.tmp / pipeline.CATEGORIES).read_text(encoding="utf-8"), "examples": (world.tmp / pipeline.FEWSHOTS).read_text(encoding="utf-8")}


def test_a_rename_reaches_the_list_the_examples_and_every_label_and_keeps_who_wrote_them(frozen):
    before = lb.load_test_gold(frozen.ws)[0]
    result = rename("cat_0", "cat_renamed")
    assert result.exit_code == 0, result.stderr
    assert "cat_0" not in codes_of(frozen) and "cat_renamed" in codes_of(frozen)
    gold, status = lb.load_test_gold(frozen.ws)  # it checks the frozen file against its record
    assert status == "provisional" and {i.category for label in gold.values() for i in label.items} == {"cat_renamed"}
    assert {fp: label.source for fp, label in gold.items()} == {fp: label.source for fp, label in before.items()} and {l.source for l in gold.values()} == {"model_draft"}
    for pack in ("label_A", "label_B", "label_single"):
        assert "cat_0" not in frozen.ws.path(f"labels/{pack}.json").read_text(encoding="utf-8")
    assert "cat_0" not in frozen.ws.path("client_review.json").read_text(encoding="utf-8")
    assert "cat_renamed" in (frozen.tmp / pipeline.FEWSHOTS).read_text(encoding="utf-8")
    assert frozen.ws.read_json("provisional_record.json").get("corrected_after_freeze", 0) == 0
    logged = json.loads(frozen.ws.path("labels/category_renames.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert logged["old"] == "cat_0" and logged["new"] == "cat_renamed"


def test_after_a_rename_the_workbook_round_trips_with_no_correction(frozen):
    rename("cat_0", "cat_renamed")
    before = frozen.ws.path("test_provisional.json").read_bytes()
    result = lb.import_label_review(frozen.ws, write_pack(frozen), REVIEWER, "2026-11-04", frozen.ws.read_json("split_manifest.json"), frozen.notes, codes_of(frozen))
    assert (result["errors"], result["reviewed"], result["corrected"]) == (0, 0, 0)
    assert frozen.ws.path("test_provisional.json").read_bytes() == before


def test_the_final_seal_still_refuses_drafts_after_a_rename(frozen):
    rename("cat_0", "cat_renamed")
    assert lb.import_client_review(frozen.ws, fill_review(frozen), lb.CLIENT_ROLE, "2026-11-05", frozen.notes, codes_of(frozen))["errors"] == 0
    with pytest.raises(ContractError, match="150 TEST labels are model drafts"):
        lb.seal(frozen.ws, frozen.ws.read_json("split_manifest.json"), frozen.notes, codes_of(frozen))


def test_a_rename_makes_the_run_out_of_date_and_the_worked_examples_still_load(frozen):
    outcome = pipeline.run(frozen.tmp)
    rename("cat_0", "cat_renamed")
    project = pipeline.load_project(frozen.tmp)
    changed = pipeline.out_of_date(project, outcome.manifest)
    assert "the category list" in changed and "the worked examples" in changed
    from itemizer.itemize import load_fewshots

    shots = load_fewshots(frozen.tmp / pipeline.FEWSHOTS, project.notes, project.split, codes_of(frozen))
    assert '"category": "cat_renamed"' in shots[0].answer


def test_a_list_edited_by_hand_stops_the_workbook_and_its_import(frozen):
    path = write_pack(frozen)  # written while the codes still matched
    taxonomy = tx.load_taxonomy(frozen.tmp / pipeline.CATEGORIES)
    next(c for c in taxonomy["categories"] if c["code"] == "cat_0")["code"] = "cat_by_hand"
    tx.write_taxonomy(frozen.tmp / pipeline.CATEGORIES, taxonomy)
    with pytest.raises(ContractError, match="rename-category"):
        write_pack(frozen)
    with pytest.raises(ContractError, match="rename-category"):
        lb.import_label_review(frozen.ws, path, REVIEWER, "2026-11-04", frozen.ws.read_json("split_manifest.json"), frozen.notes, codes_of(frozen))


def test_find_and_replace_cannot_mark_unread_drafts_as_corrected(frozen):
    """The defect this guards against: a hand edit plus find-and-replace turned 200 unread drafts into person_corrected."""
    path = write_pack(frozen)
    taxonomy = tx.load_taxonomy(frozen.tmp / pipeline.CATEGORIES)
    next(c for c in taxonomy["categories"] if c["code"] == "cat_0")["code"] = "cat_by_hand"
    tx.write_taxonomy(frozen.tmp / pipeline.CATEGORIES, taxonomy)

    def replace(line):
        if line["category"].value == "cat_0":
            line["category"].value = "cat_by_hand"

    edit(path, replace)
    with pytest.raises(ContractError, match="rename-category"):
        lb.import_label_review(frozen.ws, path, REVIEWER, "2026-11-04", frozen.ws.read_json("split_manifest.json"), frozen.notes, codes_of(frozen))
    assert lb.label_sources(frozen.ws) == {"model_draft": 200}


def test_a_merge_needs_the_flag_and_a_refusal_changes_nothing(frozen):
    before = snapshot_of_labels(frozen)
    result = rename("cat_0", "cat_1")
    assert result.exit_code == 2 and "--merge" in result.stderr
    assert snapshot_of_labels(frozen) == before


def test_a_merge_moves_the_labels_and_the_examples(frozen):
    taxonomy = tx.load_taxonomy(frozen.tmp / pipeline.CATEGORIES)  # one spare, because the list must keep 12
    extra = dict(next(c for c in taxonomy["categories"] if c["code"] == "cat_1"), code="cat_extra")
    taxonomy["categories"].append(extra)
    tx.write_taxonomy(frozen.tmp / pipeline.CATEGORIES, taxonomy)
    result = rename("cat_0", "cat_1", "--merge")
    assert result.exit_code == 0, result.stderr
    gold = lb.load_test_gold(frozen.ws)[0]
    assert "cat_0" not in codes_of(frozen) and {i.category for label in gold.values() for i in label.items} == {"cat_1"}
    merged = next(c for c in tx.load_taxonomy(frozen.tmp / pipeline.CATEGORIES)["categories"] if c["code"] == "cat_1")
    assert len(merged["examples"]) == len(extra["examples"]) + 1


def test_a_merge_that_would_leave_too_few_categories_changes_nothing(frozen):
    before = snapshot_of_labels(frozen)
    result = rename("cat_0", "cat_1", "--merge")
    assert result.exit_code == 2 and "11 categories" in result.stderr
    assert snapshot_of_labels(frozen) == before


@pytest.mark.parametrize("args, words", [
    (["other_unmapped", "anything"], "catch-all"),
    (["no_such_code", "anything"], "not in the list"),
    (["cat_0", "cat_0"], "the same"),
    (["cat_0", "no_such_code", "--merge"], "needs an existing category"),
    (["cat_0", "Bad Code"], "bad code"),
])
def test_a_bad_rename_is_refused_and_changes_nothing(frozen, args, words):
    before = snapshot_of_labels(frozen)
    result = rename(*args)
    assert result.exit_code == 2 and words in result.stderr
    assert snapshot_of_labels(frozen) == before


def test_a_rename_after_the_final_seal_is_refused_and_changes_nothing(frozen):
    _check_everything(frozen)
    assert lb.import_client_review(frozen.ws, fill_review(frozen), lb.CLIENT_ROLE, "2026-11-05", frozen.notes, CODES)["errors"] == 0
    assert "sha256" in lb.seal(frozen.ws, frozen.ws.read_json("split_manifest.json"), frozen.notes, CODES)
    list_before = (frozen.tmp / pipeline.CATEGORIES).read_text(encoding="utf-8")
    result = rename("cat_0", "cat_renamed")
    assert result.exit_code == 2 and "TEST is sealed" in result.stderr
    assert (frozen.tmp / pipeline.CATEGORIES).read_text(encoding="utf-8") == list_before


def test_a_rename_works_before_the_freeze_too(drafted):
    assert rename("cat_0", "cat_renamed").exit_code == 0
    assert {i.category for label in lb.current_test_labels(drafted.ws).values() for i in label.items} == {"cat_renamed"}


# ---- what a person's check shows on the page
def test_the_page_reports_accuracy_on_what_people_checked_and_what_they_changed(frozen):
    first, second = frozen.packs["label_single"][:2]
    pipeline.evaluate_run(frozen.tmp, pipeline.run(frozen.tmp).run_id)
    text = Path(acceptance.d3_check(frozen.tmp)["page"]).read_text(encoding="utf-8")
    assert "Accuracy on labels a person has checked" not in text and "Read this first" in text
    path = write_pack(frozen)
    edit(path, mark_checked(frozen.notes[first].note_id))
    edit(path, set_category(frozen.notes[second].note_id))
    do_import(frozen, path)
    snapshot = pipeline.evaluate_run(frozen.tmp)
    assert snapshot["accuracy_on_checked_labels"]["n"] == 2 and snapshot["accuracy_on_checked_labels"]["correct"] == 1
    assert snapshot["labels_changed_by_people"] == 1 and snapshot["test_budget"]["event"] == "rescored"
    summary = acceptance.d3_check(frozen.tmp)
    text = Path(summary["page"]).read_text(encoding="utf-8")
    assert "Accuracy on labels a person has checked: <b>50.0%</b>, 1 of 2 notes" in text and "People changed 1 label they checked" in text
    assert "198 of the 200 TEST labels behind these figures" in text

