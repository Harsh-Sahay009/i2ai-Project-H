"""Tests per scenario for the D1/D2 bootstrap. Every note here is invented; no client data is used."""
from __future__ import annotations

import json
import subprocess
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import openpyxl
import pytest
from typer.testing import CliRunner

from itemizer.bootstrap import labels as lb
from itemizer.bootstrap import split as sp
from itemizer.bootstrap import taxonomy as tx
from itemizer.bootstrap.data import (
    COLUMNS, Config, ContractError, Note, NoteLabel, Workspace, find_evidence, fingerprint, group_notes, load_export,
    money_tokens, sha256_file, to_money,
)
from itemizer.cli import app

EXAMPLE_NOTE = "LUMPER FEE $94.75"
EMAIL_NOTE = "SEE JOHN.DOE@EXAMPLE.COM LUMPER $44.44"


def make_export(path: Path, single: int = 300, multi: int = 220, large: int = 110) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "AutoPay"
    header = list(COLUMNS.values())
    sheet.append(header)

    def add(note, delta, repeated=False, carrier="CARR1"):
        billed = 100 + delta
        row = {"SHIPMENT_GID": f"S{sheet.max_row}", "Carrier Invoice": f"I{sheet.max_row}", "Carrier": carrier,
               "Event Date": 44700.5, "Shipment Amount": 100.0, "Invoice Amount": billed, "Delta": delta,
               "Dispute Status": "OPEN", "Reason Code": "OTHER", "Descritipion": note,
               "Invoice Dups Removed": 0 if repeated else billed}
        sheet.append([row[name] for name in header])

    for i in range(single):
        amount = round(20 + i * 0.25, 2)
        for copy in range(5 if i < 10 else 1):
            add(f"LUMPER FEE ${amount:.2f}", amount, repeated=copy > 0)
    for i in range(multi):
        first = round(30 + i * 0.1, 2)
        add(f"DET ${first:.2f} + STOP $10.00 = ${first + 10:.2f}", first + 10)
    for i in range(large):
        add(f"BASE RATE CORRECTION ${200 + i}.00", 200 + i, carrier="CARR2")
    add(None, 15.0)
    add(EMAIL_NOTE, 44.44)
    add("CREDIT ISSUED $5.00", -5.0)
    examples = workbook.create_sheet("Sheet1")
    examples.append(["id1", "original", "itemized"])
    examples.append(["S1", EXAMPLE_NOTE, "LUMPER FEE $94.75"])
    workbook.save(path)


@pytest.fixture
def world(tmp_path):
    export = tmp_path / "export.xlsx"
    make_export(export)
    cfg = Config(source_file="export.xlsx", dataset_class="open_anonymized", source_ref="test", test_reserve_notes=40)
    ws = Workspace(cfg, tmp_path)
    rows, examples = load_export(export)
    notes = group_notes(rows, cfg.large_dispute_usd)
    manifest = sp.build_split(notes, cfg, examples, sha256_file(export))
    ws.write_json("split_manifest.json", manifest)
    return SimpleNamespace(tmp=tmp_path, export=export, cfg=cfg, ws=ws, rows=rows, examples=examples, notes=notes, manifest=manifest)


def proposal(notes: dict[str, Note], fingerprints: list[str], count: int = 12) -> tx.TaxonomyProposal:
    categories = []
    for i in range(count):
        note = notes[fingerprints[i]]
        categories.append(tx.ProposedCategory(
            code=f"cat_{i}", name=f"Category {i}", definition="A kind of charge.", includes=[], excludes=[],
            examples=[tx.ProposedExample(note_id=note.note_id, quote=note.text[:10])]))
    return tx.TaxonomyProposal(categories=categories)


def categories_for(world) -> list[dict]:
    sample = tx.sample_train_notes(world.manifest, world.notes, set(), 50, world.cfg.seed)
    taxonomy, _ = tx.draft_taxonomy(proposal(world.notes, sample), sample, world.notes, "fake", "hash")
    assert tx.validate_taxonomy(taxonomy, world.notes) == []
    return taxonomy["categories"]


def fill_pack(path: Path, notes: dict[str, Note], change=None) -> None:
    """A stand-in labeller: reads each note and writes its charges. `change` lets a test disagree."""
    by_id = {n.note_id: n for n in notes.values()}
    workbook = openpyxl.load_workbook(path)
    sheet = workbook["Labels"]
    head = [c.value for c in sheet[1]]
    for row in sheet.iter_rows(min_row=2):
        cell = dict(zip(head, row))
        note = by_id[cell["note_id"].value]
        parts = note.text.split(" + ") if " + " in note.text else [note.text]
        parts = [p.split(" = ")[0] for p in parts]
        index = cell["item"].value - 1
        if index >= len(parts):
            continue
        amount = float(parts[index].rsplit("$", 1)[1])
        answer = {"category": "cat_0", "amount": amount, "evidence": parts[index], "line_type": "charge", "derivation": "stated"}
        if change:
            answer = change(note, index, answer)
        for key, value in answer.items():
            cell[key].value = value
    workbook.save(path)


def seal_ready(world, change_b=None) -> dict:
    packs = lb.build_packs(world.ws, world.manifest, world.notes, categories_for(world))
    codes = {c["code"] for c in categories_for(world)}
    for name, labeller, change in (("label_A", "a", None), ("label_B", "b", change_b), ("label_single", "c", None)):
        path = world.ws.path(f"packs/{name}.xlsx")
        fill_pack(path, world.notes, change)
        assert lb.import_labels(world.ws, name, path, labeller, world.notes, codes)["errors"] == 0
    lb.write_client_pack(world.ws, world.notes, categories_for(world))
    return packs


def fill_review(world, decision="accept_A", skip: int = 0) -> Path:
    path = world.ws.path("packs/client_review.xlsx")
    workbook = openpyxl.load_workbook(path)
    sheet = workbook["Review"]
    head = [c.value for c in sheet[1]]
    at = head.index("decision")
    for number, row in enumerate(sheet.iter_rows(min_row=2)):
        if number >= skip:
            row[at].value = decision
    workbook.save(path)
    return path


# ---- input contract
def test_amounts_read_as_cents():
    assert to_money(75.59999999999997) == Decimal("75.60")


def test_row_flags_and_ids(world):
    assert all(r.row_id.startswith("R") for r in world.rows)
    assert len({r.row_id for r in world.rows}) == len(world.rows)
    assert sum("empty_note" in r.flags for r in world.rows) == 1
    assert sum("non_positive_delta" in r.flags for r in world.rows) == 1
    assert sum("repeated_invoice" in r.flags for r in world.rows) == 40


def test_missing_column_is_fatal(tmp_path):
    workbook = openpyxl.Workbook()
    workbook.active.append(["SHIPMENT_GID", "Delta"])
    path = tmp_path / "bad.xlsx"
    workbook.save(path)
    with pytest.raises(ContractError, match="missing columns"):
        load_export(path)


def test_workspace_refuses_folder_git_would_track(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    with pytest.raises(ContractError, match="not ignored by Git"):
        Workspace(Config(), tmp_path)
    (tmp_path / ".gitignore").write_text("data/\n")
    Workspace(Config(), tmp_path)


# ---- dataset-profile-split
def test_profile_compares_with_the_scope(world):
    report = sp.profile(world.rows, world.notes)
    assert report["scope_comparison"]["rows"] == {"dataset": len(world.rows), "scope": 1347, "matches": False}
    assert "LUMPER" not in json.dumps(report)


def test_scan_blocks_send_until_decision(world):
    world.ws.write_json("scan_report.json", sp.scan(world.notes))
    assert sp.scan(world.notes)["counts"]["email"] == 1
    with pytest.raises(ContractError, match="record a decision"):
        sp.check_external_send(world.ws)
    world.ws.write_json("scan_decision.json", {"decision": "exclude_flagged"})
    assert fingerprint(EMAIL_NOTE) in sp.check_external_send(world.ws)
    world.ws.write_json("scan_decision.json", {"decision": "accept"})
    assert sp.check_external_send(world.ws) == set()


def test_dataset_class_blocks_send(world):
    world.ws.cfg = world.cfg.model_copy(update={"dataset_class": "client_confidential"})
    with pytest.raises(ContractError, match="client_confidential"):
        sp.check_external_send(world.ws)
    world.ws.cfg = world.cfg.model_copy(update={"source_ref": None})
    with pytest.raises(ContractError, match="source_ref"):
        sp.check_external_send(world.ws)


def test_repeated_note_is_one_entry_in_one_set(world):
    note = world.notes[fingerprint("LUMPER FEE $20.00")]
    assert len(note.row_ids) == 5
    assert sum(e["fingerprint"] == note.fingerprint for e in world.manifest["notes"]) == 1


def test_same_format_can_cross_sets_and_is_recorded(world):
    sets = {e["set"] for e in world.manifest["notes"] if world.notes[e["fingerprint"]].format_key == "lumper fee $#"}
    assert {"TEST", "TRAIN", "VALIDATION"} <= sets
    tests = [e for e in world.manifest["notes"] if e["set"] == "TEST"]
    assert all(isinstance(e["format_in_train"], bool) for e in tests)


def test_same_seed_gives_same_manifest(world):
    again = sp.build_split(world.notes, world.cfg, world.examples, sha256_file(world.export))
    assert again == world.manifest
    other = sp.build_split(world.notes, world.cfg.model_copy(update={"seed": 1}), world.examples, sha256_file(world.export))
    assert other["notes"] != world.manifest["notes"]


def test_example_sheet_notes_go_to_train(world):
    fp = fingerprint(EXAMPLE_NOTE)
    assert fp in world.examples
    assert next(e for e in world.manifest["notes"] if e["fingerprint"] == fp)["set"] == "TRAIN"


def test_test_mix_and_reserve(world):
    summary = sp.summarize(world.manifest)
    assert summary["TEST"]["notes"] == 200
    assert summary["TEST"]["strata"] == {"large": 50, "multi": 50, "single": 100}
    assert summary["RESERVE"]["notes"] == 40
    assert sum(summary[s]["notes"] for s in ("TEST", "RESERVE", "TRAIN", "VALIDATION")) == len(world.notes)


def test_too_few_notes_stops_the_split(tmp_path):
    export = tmp_path / "small.xlsx"
    make_export(export, single=50, multi=50, large=20)
    rows, examples = load_export(export)
    with pytest.raises(ContractError, match="notes left"):
        sp.build_split(group_notes(rows, Decimal("180")), Config(), examples, "x")


def test_replacement_plan_matches_the_spec():
    assert lb.plan_replacements(130, 70, 10) == ("single", 20)
    assert lb.plan_replacements(70, 130, 10) == ("other", 20)
    assert lb.plan_replacements(105, 95, 10) == (None, 0)


def test_note_in_two_sets_fails(world):
    broken = {"notes": world.manifest["notes"] + [world.manifest["notes"][0]]}
    with pytest.raises(ContractError, match="note in two sets"):
        sp.check_manifest(broken)


# ---- taxonomy-drafting
def test_draft_sample_is_train_only_and_refuses_others(world):
    sample = tx.sample_train_notes(world.manifest, world.notes, set(), 500, world.cfg.seed)
    sets = {e["fingerprint"]: e["set"] for e in world.manifest["notes"]}
    assert sample and all(sets[fp] == "TRAIN" for fp in sample)
    test_note = next(fp for fp, s in sets.items() if s == "TEST")
    with pytest.raises(ContractError, match="outside TRAIN"):
        tx.assert_train_only(sample + [test_note], world.manifest)


def test_reserve_is_not_used_before_sealing(world):
    sample = tx.sample_train_notes(world.manifest, world.notes, set(), 10_000, world.cfg.seed)
    assert not set(sample) & set(sp.notes_in_set(world.manifest, "RESERVE"))


def test_too_few_categories_fail(world):
    sample = tx.sample_train_notes(world.manifest, world.notes, set(), 50, world.cfg.seed)
    with pytest.raises(ContractError, match="9 categories"):
        tx.draft_taxonomy(proposal(world.notes, sample, 9), sample, world.notes, "fake", "hash")


def test_paraphrased_quote_is_dropped_and_reported(world):
    sample = tx.sample_train_notes(world.manifest, world.notes, set(), 50, world.cfg.seed)
    drafted = proposal(world.notes, sample)
    drafted.categories[0].examples[0].quote = "this was never in the note"
    taxonomy, report = tx.draft_taxonomy(drafted, sample, world.notes, "fake", "hash")
    assert report["dropped_examples"][0]["reason"] == "quote not verbatim"
    assert "cat_0: no real example" in tx.validate_taxonomy(taxonomy, world.notes)


def test_taxonomy_file_cannot_hold_note_text(world):
    categories = categories_for(world)
    taxonomy = {"version": "draft-1", "categories": json.loads(json.dumps(categories))}
    taxonomy["categories"][0]["examples"][0]["quote"] = "LUMPER FEE $20.00"
    assert any("only fingerprint" in p for p in tx.validate_taxonomy(taxonomy))
    taxonomy = {"version": "draft-1", "categories": json.loads(json.dumps(categories))}
    taxonomy["categories"][1]["definition"] = "Like BASE RATE CORRECTION $200.00 in a note"
    assert any("text of a note" in p for p in tx.validate_taxonomy(taxonomy, world.notes))


def test_written_taxonomy_holds_offsets_only(world, tmp_path):
    path = tmp_path / "taxonomy" / "categories.yaml"
    tx.write_taxonomy(path, {"version": "draft-1", "categories": categories_for(world)})
    text = path.read_text()
    assert "fingerprint" in text and "LUMPER" not in text and "BASE RATE" not in text


def test_approval_document_shows_real_quotes(world):
    document = tx.approval_document({"version": "draft-1", "categories": categories_for(world)}, world.notes)
    example = categories_for(world)[0]["examples"][0]
    assert world.notes[example["fingerprint"]].text[example["start"]:example["end"]] in document


def test_approval_is_recorded_and_breaks_if_the_list_changes(world, tmp_path):
    categories_path, approval_path = tmp_path / "categories.yaml", tmp_path / "approval.yaml"
    tx.write_taxonomy(categories_path, {"version": "draft-1", "categories": categories_for(world)})
    assert tx.approved_codes(categories_path, approval_path) is None
    evidence = tmp_path / "email.txt"
    evidence.write_text("Approved.")
    record = tx.record_approval(categories_path, approval_path, "client_owner", "2026-11-03", evidence)
    assert record["tag"] == "taxonomy@D1-approved"
    assert "cat_0" in tx.approved_codes(categories_path, approval_path)
    categories_path.write_text(categories_path.read_text() + "\n# edited\n")
    assert tx.approved_codes(categories_path, approval_path) is None


def test_adapter_sends_schema_and_reads_the_answer(world):
    sample = tx.sample_train_notes(world.manifest, world.notes, set(), 50, world.cfg.seed)
    seen = {}

    def create(**kwargs):
        seen.update(kwargs)
        block = SimpleNamespace(type="text", text=proposal(world.notes, sample).model_dump_json())
        return SimpleNamespace(stop_reason="end_turn", content=[block])

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    result = tx.AnthropicDrafter(client=client).propose("system", "user")
    assert len(result.categories) == 12
    assert seen["model"] == "claude-opus-5-5"
    assert seen["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_adapter_stops_on_refusal(world):
    def create(**kwargs):
        return SimpleNamespace(stop_reason="refusal", content=[])

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    with pytest.raises(ContractError, match="declined"):
        tx.AnthropicDrafter(client=client).propose("system", "user")


# ---- test-set-preparation
def _cells(path: Path) -> list[str]:
    workbook = openpyxl.load_workbook(path)
    return [str(c.value) for sheet in workbook.worksheets for row in sheet.iter_rows() for c in row if c.value is not None]


def test_no_tool_output_in_any_blind_pack(world):
    packs = lb.build_packs(world.ws, world.manifest, world.notes, categories_for(world))
    assert set(packs) == {"label_A", "label_B", "label_single", "spot_check", "validation", "train"}
    for name in ("label_A", "label_B", "label_single", "spot_check", "validation"):
        workbook = openpyxl.load_workbook(world.ws.path(f"packs/{name}.xlsx"))
        sheet = workbook["Labels"]
        head = [c.value for c in sheet[1]]
        assert head == lb.LABEL_COLUMNS
        for column in ("category", "amount", "evidence", "line_type", "derivation", "no_charge_stated", "comment"):
            at = head.index(column)
            assert all(row[at].value is None for row in sheet.iter_rows(min_row=2)), f"{name}.{column} was pre-filled"
        text = " ".join(_cells(world.ws.path(f"packs/{name}.xlsx"))).lower()
        for banned in ("confidence", "prediction", "predicted", "hint", "model_suggestion"):
            assert banned not in text, f"{banned} found in {name}"


def test_suggestions_refused_outside_train(world, tmp_path):
    for set_name in ("TEST", "VALIDATION"):
        with pytest.raises(ContractError, match="written by people"):
            lb.write_pack(tmp_path / "x.xlsx", set_name, [], world.notes, categories_for(world), {"n_1": []})


def test_train_suggestion_is_recorded_as_such(world, tmp_path):
    fp = sp.notes_in_set(world.manifest, "TRAIN")[0]
    note = world.notes[fp]
    suggestion = {note.note_id: [{"category": "cat_0", "amount": 1.0, "evidence": note.text.rsplit(" ", 1)[1], "line_type": "charge", "derivation": "stated"}]}
    amount = float(note.text.rsplit("$", 1)[1])
    suggestion[note.note_id][0]["amount"] = amount
    path = tmp_path / "train.xlsx"
    lb.write_pack(path, "TRAIN", [fp], world.notes, categories_for(world), suggestion)
    labels, errors = lb.parse_lines(lb._read_label_lines(path, "Labels"), {fp}, world.notes, {"cat_0"}, "a", "train")
    assert not errors and labels[fp].source == "model_suggestion_confirmed"


def test_double_labelled_notes_cover_both_strata_and_files_are_separate(world):
    packs = lb.build_packs(world.ws, world.manifest, world.notes, categories_for(world))
    assert packs["label_A"] == packs["label_B"] and len(packs["label_A"]) == 50 and len(packs["label_single"]) == 150
    strata = {e["fingerprint"]: e["provisional_stratum"] for e in world.manifest["notes"]}
    chosen = [strata[fp] for fp in packs["label_A"]]
    assert chosen.count("single") == 25
    assert set(packs["spot_check"]) <= set(packs["label_single"]) and len(packs["spot_check"]) == 15
    fill_pack(world.ws.path("packs/label_A.xlsx"), world.notes)
    workbook = openpyxl.load_workbook(world.ws.path("packs/label_B.xlsx"))
    at = lb.LABEL_COLUMNS.index("category")
    assert all(row[at].value is None for row in workbook["Labels"].iter_rows(min_row=2))


@pytest.mark.parametrize("text, amount, evidence, derivation, code", [
    ("LUMPER 85", "85.00", "lumper fee 85", "stated", "evidence_not_verbatim"),
    ("LUMPER 85", "85.123", "LUMPER 85", "stated", "bad_amount"),
    ("LUMPER 85", "90.00", "LUMPER 85", "stated", "amount_not_in_evidence"),
    ("2 HRS @ 75.00", "160.00", "2 HRS @ 75.00", "rate_x_quantity", "product_mismatch"),
])
def test_label_checks_reject(text, amount, evidence, derivation, code):
    note = Note(fingerprint="f", note_id="n", text=text, row_ids=["R1"], carrier="C", disputed=Decimal(1), max_disputed=Decimal(1),
                usd=Decimal(1), format_key="", money_tokens=1, band="1", stratum="single")
    item, errors = lb.check_item(note, 1, "cat", amount, evidence, "charge", derivation, {"cat"})
    assert item is None and code in [e[0] for e in errors]


def test_label_checks_accept_rate_times_quantity_and_extra_spaces():
    note = Note(fingerprint="f", note_id="n", text="DET  2 HRS @ 75.00 OK", row_ids=["R1"], carrier="C", disputed=Decimal(1), max_disputed=Decimal(1),
                usd=Decimal(1), format_key="", money_tokens=1, band="1", stratum="single")
    item, errors = lb.check_item(note, 1, "cat", 150, "DET 2 HRS @ 75.00", "charge", "rate_x_quantity", {"cat"})
    assert not errors and item.amount == Decimal("150.00")
    assert note.text[item.evidence_start:item.evidence_end] == "DET  2 HRS @ 75.00"


def test_find_evidence_allows_only_whitespace_differences():
    assert find_evidence("A  B", "A B") == (0, 4)
    assert find_evidence("A B", "a b") is None


def test_unlabelled_note_is_reported(world):
    lb.build_packs(world.ws, world.manifest, world.notes, categories_for(world))
    result = lb.import_labels(world.ws, "label_A", world.ws.path("packs/label_A.xlsx"), "a", world.notes, {"cat_0"})
    assert result["notes_accepted"] == 0 and result["error_codes"] == {"not_labelled": 50}


def test_agreement_lists_different_item_counts():
    def label(items):
        return NoteLabel(fingerprint="f", note_id="n", labeller="x", pack="p", items=[
            lb.GoldItem(item=i + 1, category=c, amount=Decimal(a), evidence_text=a, evidence_start=0, evidence_end=1,
                        line_type="charge", derivation="stated") for i, (c, a) in enumerate(items)])
    report = lb.agreement({"f": label([("a", "1.00"), ("b", "2.00")])}, {"f": label([("a", "1.00")])})
    assert report["disagreements"][0]["reasons"] == ["item_count", "amount"]
    assert report["item_count_match"] == 0
    same = lb.agreement({"f": label([("a", "1.00")])}, {"f": label([("b", "1.00")])})
    assert same["disagreements"][0]["reasons"] == ["category"]


def test_kappa_values():
    assert lb._kappa([]) is None
    assert lb._kappa([("a", "a"), ("b", "b")]) == 1.0
    assert lb._kappa([("a", "b"), ("b", "a")]) == -1.0


def test_reviewer_correcting_an_agreed_label_is_recorded(world):
    packs = seal_ready(world)
    path = fill_review(world)
    workbook = openpyxl.load_workbook(path)
    target = world.notes[packs["label_A"][0]]
    review = workbook["Review"]
    head = [c.value for c in review[1]]
    for row in review.iter_rows(min_row=2):
        if row[0].value == target.note_id:
            row[head.index("decision")].value = "correct"
    evidence = target.text.split(" + ")[0].split(" = ")[0]
    amount = float(evidence.rsplit("$", 1)[1])
    workbook["Corrections"].append([target.note_id, None, None, None, 1, "cat_1", amount, evidence, "charge", "stated", None, None])
    workbook.save(path)
    result = lb.import_client_review(world.ws, path, "client_owner", "2026-11-04", world.notes, {f"cat_{i}" for i in range(12)})
    assert result["errors"] == 0 and result["changed_agreed_labels"] == 1
    gold = lb.gold_labels(world.ws)[target.fingerprint]
    assert gold.items[0].category == "cat_1"


def test_seal_refuses_incomplete_review(world):
    seal_ready(world)
    path = fill_review(world, skip=10)
    result = lb.import_client_review(world.ws, path, "client_owner", "2026-11-04", world.notes, {"cat_0"})
    assert result["reviewed"] == 40 and result["error_codes"] == {"not_reviewed": 10}
    with pytest.raises(ContractError, match="has not reviewed 10 of the 50"):
        lb.seal(world.ws, world.manifest, world.notes, {"cat_0"})


def test_seal_refuses_without_approval_and_with_unknown_categories(world):
    seal_ready(world)
    lb.import_client_review(world.ws, fill_review(world), "client_owner", "2026-11-04", world.notes, {"cat_0"})
    with pytest.raises(ContractError, match="no valid client approval"):
        lb.seal(world.ws, world.manifest, world.notes, None)
    with pytest.raises(ContractError, match="outside the approved list"):
        lb.seal(world.ws, world.manifest, world.notes, {"cat_9"})


def test_full_flow_seals_and_releases_the_reserve(world):
    def disagree(note, index, answer):
        return {**answer, "category": "cat_1"} if note.note_id.endswith(("0", "1", "2", "3")) else answer

    seal_ready(world, disagree)
    report = world.ws.read_json("agreement.json")
    assert report["notes_compared"] == 50 and report["disagreements"]
    lb.import_client_review(world.ws, fill_review(world), "client_owner", "2026-11-04", world.notes, {f"cat_{i}" for i in range(12)})
    assert lb.final_strata(world.ws, world.manifest, world.notes)["replace"] == 0
    reserve = set(sp.notes_in_set(world.manifest, "RESERVE"))
    record = lb.seal(world.ws, world.manifest, world.notes, {f"cat_{i}" for i in range(12)})
    assert record["notes"] == 200 and record["sha256"] == sha256_file(world.ws.path("test_sealed.json"))
    lines = world.ws.path("test_fingerprints.txt").read_text().split()
    assert len(lines) == 200 and all(len(line) == 64 for line in lines)
    released = world.ws.read_json("split_manifest.json")
    assert released["reserve_released"] and not sp.notes_in_set(released, "RESERVE")
    sets = {e["fingerprint"]: e["set"] for e in released["notes"]}
    assert {sets[fp] for fp in reserve} <= {"TRAIN", "VALIDATION"}
    with pytest.raises(ContractError, match="already sealed"):
        lb.seal(world.ws, released, world.notes, {f"cat_{i}" for i in range(12)})
    with pytest.raises(ContractError, match="sealed"):
        lb.import_labels(world.ws, "label_A", world.ws.path("packs/label_A.xlsx"), "a", world.notes, {"cat_0"})


def test_replacements_move_notes_from_reserve(world):
    def all_single(note, index, answer):
        return answer

    packs = seal_ready(world, all_single)
    lb.import_client_review(world.ws, fill_review(world), "client_owner", "2026-11-04", world.notes, {f"cat_{i}" for i in range(12)})
    # Make 30 multi-charge notes in the single-labelled pack count as single, so the mix is off.
    stored = world.ws.read_json("labels/label_single.json")
    changed = 0
    for fp in packs["label_single"]:
        if len(stored["labels"][fp]["items"]) > 1 and changed < 30:
            stored["labels"][fp]["items"] = stored["labels"][fp]["items"][:1]
            changed += 1
    world.ws.write_json("labels/label_single.json", stored)
    assert changed == 30
    plan = lb.final_strata(world.ws, world.manifest, world.notes, apply=True)
    assert plan["single"] == 130 and plan["replace"] == 20 and plan["shortage"] == 0
    assert len(world.ws.read_json("packs.json")["label_replacements"]) == 20
    assert len(sp.notes_in_set(world.manifest, "TEST")) == 200


@pytest.mark.parametrize("note, expected", [
    ("DET 2 HRS @ 75.00", 1),
    ("LUMPER $60.00 AND STOP $12.00", 2),
    ("$150 HAZMAT FEE ON BOL 9 999 LBS", 1),
    ("$60 DETENTION 2021-01-02 09:00:00-2021-01-02 10:17:00", 1),
    ("A FEE $50.00 AND B FEE $14.00 = $64.00 + GST $3.20 = $67.20", 3),
    ("FEE $20  BALANCE DUE $21", 1),
    ("X IS NEEDED. BALANCE DUE IS $31.00 + GST $1.00 = $32.00", 2),
    ("ADD $75 FOR PERDIEM 1 DAY @ $75 A DAY", 1),
    ("STILL UNPAID $1 277.68", 1),
    ("57.67", 1),
    (".67 FSC", 1),
    ("WEIGHT 20 000 LBS NO AMOUNT", 0),
])
def test_money_tokens_ignore_dates_weights_and_totals(note, expected):
    assert money_tokens(note) == expected


@pytest.mark.parametrize("text, amount, evidence", [
    ("STILL UNPAID $1 277.68 NOW", "1277.68", "UNPAID $1 277.68"),
    (".67 FSC", "0.67", ".67 FSC"),
    ("SHORT PAID - $ 105.00", "105.00", "SHORT PAID - $ 105.00"),
    ("FEE $63", 63, "FEE $63"),
])
def test_amounts_written_the_way_the_notes_write_them_are_accepted(text, amount, evidence):
    note = Note(fingerprint="f", note_id="n", text=text, row_ids=["R1"], carrier="C", disputed=Decimal(1), max_disputed=Decimal(1),
                usd=Decimal(1), format_key="", money_tokens=1, band="1", stratum="single")
    item, errors = lb.check_item(note, 1, "cat", amount, evidence, "charge", "stated", {"cat"})
    assert not errors and item is not None


def test_stated_total_beside_a_rate_is_accepted_as_stated():
    note = Note(fingerprint="f", note_id="n", text="2 DWELL DAYS @$300", row_ids=["R1"], carrier="C", disputed=Decimal(1), max_disputed=Decimal(1),
                usd=Decimal(1), format_key="", money_tokens=1, band="1", stratum="single")
    item, errors = lb.check_item(note, 1, "cat", 300, "2 DWELL DAYS @$300", "charge", "stated", {"cat"})
    assert not errors and item.amount == Decimal("300.00")


def test_notes_read_while_drafting_never_enter_test_or_reserve(world):
    read = set(sp.notes_in_set(world.manifest, "TRAIN"))
    again = sp.build_split(world.notes, world.cfg.model_copy(update={"seed": 99}), world.examples, sha256_file(world.export), never_test=read)
    assert sp.summarize(again)["TEST"]["notes"] == 200
    assert not read & set(sp.notes_in_set(again, "TEST"))
    assert not read & set(sp.notes_in_set(again, "RESERVE"))
    assert read & set(sp.notes_in_set(again, "VALIDATION")), "read notes may still go to VALIDATION"
    assert world.examples <= set(sp.notes_in_set(again, "TRAIN"))
    share = len(sp.notes_in_set(again, "VALIDATION")) / (len(sp.notes_in_set(again, "VALIDATION")) + len(sp.notes_in_set(again, "TRAIN")))
    assert abs(share - 0.40) < 0.02


def test_validation_pack_puts_scarce_notes_first(world):
    packs = lb.choose_packs(world.manifest, world.cfg.seed)
    entries = {e["fingerprint"]: e["provisional_stratum"] for e in world.manifest["notes"]}
    order = [entries[fp] for fp in packs["validation"]]
    assert order == sorted(order, key=["large", "multi", "single"].index)


def test_scan_finds_a_named_person(tmp_path):
    export = tmp_path / "x.xlsx"
    make_export(export)
    rows, _ = load_export(export)
    notes = group_notes(rows, Decimal("180"))
    named = next(iter(notes.values())).model_copy(update={"text": "ROAD CLOSURE JANE ROE FROM PPG NOTIFIED $5.00"})
    report = sp.scan({named.fingerprint: named})
    assert report["counts"]["possible_name"] == 1


def test_packs_can_be_rebuilt_until_labels_are_imported(world):
    lb.build_packs(world.ws, world.manifest, world.notes, categories_for(world))
    lb.build_packs(world.ws, world.manifest, world.notes, categories_for(world))
    lb.import_labels(world.ws, "label_A", world.ws.path("packs/label_A.xlsx"), "a", world.notes, {"cat_0"})
    with pytest.raises(ContractError, match="cannot be rebuilt"):
        lb.build_packs(world.ws, world.manifest, world.notes, categories_for(world))


# ---- command line
@pytest.fixture
def project(tmp_path, monkeypatch):
    make_export(tmp_path / "export.xlsx")
    config = tmp_path / "config"
    config.mkdir()
    (config / "bootstrap.yaml").write_text(
        "data:\n  source_file: export.xlsx\n  dataset_class: client_confidential\n  source_ref: null\n"
        "split:\n  seed: 7\nruntime:\n  data_root: data\n")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_cli_prints_no_note_text(project):
    runner = CliRunner()
    for command in (["gt", "profile"], ["gt", "scan"], ["gt", "split"]):
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
        for text in ("LUMPER", "BASE RATE", "JOHN.DOE"):
            assert text not in result.output
    log = (project / "data/bootstrap/command_log.jsonl").read_text().splitlines()
    assert [json.loads(line)["command"] for line in log] == ["profile", "scan", "split"]


def test_cli_blocks_external_send_for_confidential_data(project):
    runner = CliRunner()
    runner.invoke(app, ["gt", "split"])
    result = runner.invoke(app, ["gt", "draft-taxonomy"])
    assert result.exit_code == 2 and "client_confidential" in result.output


def test_cli_split_is_locked_once_packs_exist(project):
    runner = CliRunner()
    assert runner.invoke(app, ["gt", "split"]).exit_code == 0
    (project / "config/bootstrap.yaml").write_text(
        "data:\n  source_file: export.xlsx\nsplit:\n  seed: 8\nruntime:\n  data_root: data\n")
    assert "--force" in runner.invoke(app, ["gt", "split"]).output
    (project / "data/bootstrap/packs.json").write_text("{}")
    assert "locked" in runner.invoke(app, ["gt", "split", "--force"]).output


@pytest.mark.parametrize("amount", ["1e30", "NaN", "Infinity", "sNaN"])
def test_a_typed_amount_that_is_not_money_is_a_label_error_and_not_a_crash(amount):
    assert lb._strict_amount(amount) is None


def test_a_very_long_product_is_a_label_error_and_not_a_crash():
    assert lb._products([Decimal("9" * 20), Decimal("9" * 20)]) == set()


def test_final_seal_stores_the_approved_codes_when_a_mapping_is_used(world):
    seal_ready(world)
    assert lb.import_client_review(world.ws, fill_review(world), "client_owner", "2026-11-04", world.notes, {f"cat_{i}" for i in range(12)})["errors"] == 0
    lb.seal(world.ws, world.manifest, world.notes, {"approved_code"}, {"cat_0": "approved_code"})
    labels = world.ws.read_json("test_sealed.json")["labels"].values()
    assert {item["category"] for label in labels for item in label["items"]} == {"approved_code"}
    assert world.ws.read_json("category_mapping.json") == {"cat_0": "approved_code"}


@pytest.mark.parametrize("cell", ["NaN", "Infinity", "SEE THE NOTE ABOUT LUMPER"])
def test_a_cell_that_is_not_an_amount_stops_without_quoting_it(cell):
    with pytest.raises(ContractError) as caught:
        to_money(cell)
    assert cell not in str(caught.value)
