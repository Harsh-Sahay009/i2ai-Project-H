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


def test_find_evidence_allows_only_whitespace_differences():
    assert find_evidence("A  B", "A B") == (0, 4)
    assert find_evidence("A B", "a b") is None


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


def test_scan_finds_a_named_person(tmp_path):
    export = tmp_path / "x.xlsx"
    make_export(export)
    rows, _ = load_export(export)
    notes = group_notes(rows, Decimal("180"))
    named = next(iter(notes.values())).model_copy(update={"text": "ROAD CLOSURE JANE ROE FROM PPG NOTIFIED $5.00"})
    report = sp.scan({named.fingerprint: named})
    assert report["counts"]["possible_name"] == 1


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
