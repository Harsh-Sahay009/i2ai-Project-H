"""Tests per scenario for `itemizer run` and `itemizer evaluate`. Every note is invented, and every model is a fake."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace

import openpyxl
import pytest
import yaml
from test_bootstrap import EMAIL_NOTE, categories_for, fill_review, make_export, seal_ready
from typer.testing import CliRunner

from itemizer import kpi, pipeline
from itemizer.bootstrap import labels as lb
from itemizer.bootstrap import split as sp
from itemizer.bootstrap import taxonomy as tx
from itemizer.bootstrap.data import COLUMNS, ContractError, Workspace, group_notes, load_config, load_export, sha256_file
from itemizer.cli import app
from itemizer.providers import Completion, ProviderError, load_models

ROOT = Path(__file__).resolve().parents[1]
CODES = {f"cat_{i}" for i in range(12)} | {"other_unmapped"}
NOTE_WORDS = ("LUMPER", "STOP", "BASE RATE", "JOHN.DOE", "CREDIT ISSUED", "DET ")
SECRET = "sk-test-do-not-print-this-value"
runner = CliRunner()


class StubModel:
    """Writes what a careful reader of these invented notes would write. One call uses 1,000 input tokens, $0.004 on Opus."""

    def __init__(self, spec, log: list, wrong_on: str | None = None, fail: bool = False):
        self.spec = spec
        self.log = log
        self.wrong_on = wrong_on
        self.fail = fail
        self._lock = threading.Lock()

    def complete(self, system: str, user: str, schema: dict) -> Completion:
        with self._lock:
            self.log.append(SimpleNamespace(model=self.spec.name, system=system, user=user))
        if self.fail:
            raise ProviderError("the fake is down")
        text = re.search(r"<untrusted_note>\n(.*)\n</untrusted_note>", user, re.S)[1]
        parts = [part.split(" = ")[0] for part in text.split(" + ")]
        items = [{"category": "cat_1" if self.wrong_on and self.wrong_on in part else "cat_0",
                  "amount": f"{float(part.rsplit('$', 1)[1]):.2f}", "evidence_text": part, "line_type": "charge",
                  "derivation": "stated", "basis": "named_in_note"} for part in parts]
        answer = {"items": items, "no_charge_stated": False, "unsure": False, "reason_code": "none"}
        return Completion(text=json.dumps(answer), input_tokens=1_000, output_tokens=0, latency_ms=10)


def _world(root: Path, reserve: int = 40) -> SimpleNamespace:
    cfg = load_config(root / pipeline.CONFIG)
    ws = Workspace(cfg, root)
    rows, examples = load_export(root / cfg.source_file, cfg.examples_sheet)
    notes = group_notes(rows, cfg.large_dispute_usd)
    manifest = sp.build_split(notes, cfg, examples, sha256_file(root / cfg.source_file))
    ws.write_json("split_manifest.json", manifest)
    return SimpleNamespace(tmp=root, export=root / cfg.source_file, cfg=cfg, ws=ws, rows=rows, examples=examples, notes=notes, manifest=manifest)


@pytest.fixture
def d3(tmp_path, monkeypatch):
    """A project with invented data, the real prompt and settings, a split, a category list and two worked examples."""
    make_export(tmp_path / "export.xlsx")
    (tmp_path / "config").mkdir()
    (tmp_path / "prompts").mkdir()
    (tmp_path / "taxonomy").mkdir()
    for name in ("config/models.yaml", "config/run.yaml", "prompts/itemize_v1.md"):
        shutil.copy(ROOT / name, tmp_path / name)
    (tmp_path / pipeline.CONFIG).write_text(
        "data:\n  source_file: export.xlsx\n  dataset_class: open_anonymized\n  source_ref: invented for tests\n"
        "split:\n  test_reserve_notes: 40\nruntime:\n  data_root: data\n", encoding="utf-8")
    (tmp_path / ".env").write_text(f"CLAUDE_API_KEY={SECRET}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    world = _world(tmp_path)
    world.ws.write_json("scan_report.json", sp.scan(world.notes))
    world.ws.write_json("scan_decision.json", {"decision": "accept"})
    taxonomy, _ = _taxonomy(world)
    tx.write_taxonomy(tmp_path / pipeline.CATEGORIES, taxonomy)
    _write_fewshots(world, sp.notes_in_set(world.manifest, "TRAIN")[:2])

    calls: list = []
    world.calls = calls
    world.broken = set()
    world.wrong_on = None

    def fake_provider(spec, client=None, project_root=None):
        return StubModel(spec, calls, world.wrong_on, spec.name in world.broken)

    monkeypatch.setattr(pipeline, "get_provider", fake_provider)
    return world


def _taxonomy(world) -> tuple[dict, dict]:
    from test_bootstrap import proposal

    sample = tx.sample_train_notes(world.manifest, world.notes, set(), 50, world.cfg.seed)
    return tx.draft_taxonomy(proposal(world.notes, sample), sample, world.notes, "fake", "hash")


def _write_fewshots(world, fingerprints: list[str]) -> None:
    examples = []
    for fp in fingerprints:
        note = world.notes[fp]
        cut = note.text.split(" + ")[0].split(" = ")[0]
        amount = f"{float(cut.rsplit('$', 1)[1]):.2f}"
        items = [{"category": "cat_0", "amount": amount, "start": 0, "end": len(cut), "line_type": "charge", "derivation": "stated",
                  "basis": "named_in_note"}]
        examples.append({"note_id": note.note_id, "source": "invented", "items": items})
    (world.tmp / pipeline.FEWSHOTS).write_text(yaml.safe_dump({"version": "test", "examples": examples}), encoding="utf-8")


def freeze(world, role: str = "team_provisional") -> dict:
    packs = seal_ready(world)
    assert lb.import_client_review(world.ws, fill_review(world), role, "2026-11-04", world.notes, CODES)["errors"] == 0
    record = lb.seal_provisional(world.ws, world.ws.read_json("split_manifest.json"), world.notes, CODES)
    assert "sha256" in record
    return packs


def hash_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_lines(path: Path) -> list[dict]:
    sheet = openpyxl.load_workbook(path)["Row Summary"]
    head = [cell.value for cell in sheet[1]]
    return [dict(zip(head, line, strict=True)) for line in sheet.iter_rows(min_row=2, values_only=True)]


def every_file(folder: Path) -> str:
    """The text of every plain file under a folder, for checks on what was written."""
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(folder.rglob("*")) if path.is_file() and path.suffix != ".xlsx")


# ---- one call per distinct note
def test_one_call_per_distinct_note_and_every_row_has_a_result(d3):
    outcome = pipeline.run(d3.tmp, set_name="train")
    train = set(sp.notes_in_set(d3.manifest, "TRAIN"))
    assert len(d3.calls) == outcome.notes == len(train)
    assert outcome.rows == sum(1 for row in d3.rows if row.note.strip() and row.note and _fp(row.note) in train)
    assert outcome.rows > outcome.notes  # some notes repeat across rows
    assert {row.fingerprint for row in outcome.row_results} == train


def _fp(text: str) -> str:
    from itemizer.bootstrap.data import fingerprint

    return fingerprint(text)


# ---- the run folder
def test_a_run_writes_its_folder_and_records_the_full_model_entry(d3):
    outcome = pipeline.run(d3.tmp, set_name="train", limit=5)
    for name in ("manifest.json", "note_results.json", "row_results.json", "telemetry.jsonl", "itemized.xlsx"):
        assert (outcome.folder / name).exists()
    stored = json.loads((outcome.folder / "manifest.json").read_text(encoding="utf-8"))
    assert stored["run_id"] == outcome.run_id == outcome.folder.name
    assert stored["model"]["name"] == "claude-opus-5-5" and stored["model"]["input_usd_per_mtok"] == "4.00"
    assert stored["set_name"] == "train" and stored["limit"] == 5
    assert outcome.notes == 5 == len(d3.calls)


def test_every_file_keeps_the_key_out(d3):
    outcome = pipeline.run(d3.tmp, set_name="train", limit=5)
    assert SECRET not in every_file(outcome.folder)
    book = openpyxl.load_workbook(outcome.workbook)
    assert not any(SECRET in str(cell) for sheet in book.worksheets for line in sheet.iter_rows(values_only=True) for cell in line)


# ---- reproducible answers
def test_a_rerun_makes_no_calls_and_the_workbook_hash_is_unchanged(d3):
    first = pipeline.run(d3.tmp, set_name="train", limit=12)
    made, digest = len(d3.calls), hash_of(first.workbook)
    second = pipeline.run(d3.tmp, set_name="train", limit=12)
    assert len(d3.calls) == made
    assert second.run_id == first.run_id and hash_of(second.workbook) == digest
    assert second.new_calls_usd == 0 and second.measured_usd == first.new_calls_usd > 0 and second.cached_notes == 12


# ---- runs on all rows wait for TEST
def test_a_run_on_all_rows_waits_until_test_is_frozen(d3):
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2 and "--set train" in result.stderr and d3.calls == []


def test_a_copy_of_the_dataset_under_another_name_is_still_the_dataset(d3):
    copy = d3.tmp / "copy.xlsx"
    shutil.copy(d3.export, copy)
    with pytest.raises(ContractError, match="--set train"):
        pipeline.run(d3.tmp, export=copy)


def test_test_is_not_a_development_set(d3):
    result = runner.invoke(app, ["run", "--set", "test"])
    assert result.exit_code == 2 and "TEST is never" in result.stderr and d3.calls == []


def test_a_limit_needs_a_set(d3):
    freeze(d3)
    with pytest.raises(ContractError, match="--limit needs --set"):
        pipeline.run(d3.tmp, limit=5)


def test_after_the_freeze_a_run_on_all_rows_covers_every_row(d3):
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    assert outcome.rows == len(d3.rows) and outcome.notes == len(d3.notes)
    assert len(run_lines(outcome.workbook)) == len(d3.rows)
    blank = [line for line in run_lines(outcome.workbook) if line["outcome_reason"] == "empty_note"]
    assert len(blank) == 1


# ---- another export
def _other_export(path: Path, notes: list[str]) -> Path:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    header = list(COLUMNS.values())
    sheet.append(header)
    for number, note in enumerate(notes):
        row = {"SHIPMENT_GID": f"X{number}", "Carrier Invoice": f"Y{number}", "Carrier": "CARR9", "Event Date": 44700.5, "Shipment Amount": 100.0,
               "Invoice Amount": 150.0, "Delta": 50.0, "Dispute Status": "OPEN", "Reason Code": "OTHER", "Descritipion": note,
               "Invoice Dups Removed": 150.0}
        sheet.append([row[name] for name in header])
    workbook.save(path)
    return path


def test_another_export_runs_whole_with_no_split(d3):
    path = _other_export(d3.tmp / "other.xlsx", ["FRESH CHARGE $50.00", "ANOTHER CHARGE $50.00"])
    outcome = pipeline.run(d3.tmp, export=path)
    assert outcome.rows == outcome.notes == 2 and outcome.manifest.split_sha256 is None
    assert {line["outcome"] for line in run_lines(outcome.workbook)} == {"verified"}


@pytest.mark.parametrize("held_in", ["TEST", "RESERVE"])
def test_another_export_holding_held_back_notes_waits_for_the_freeze(d3, held_in):
    held_back = d3.notes[sp.notes_in_set(d3.manifest, held_in)[0]].text
    path = _other_export(d3.tmp / "other.xlsx", [held_back, "FRESH CHARGE $50.00"])
    with pytest.raises(ContractError, match="held back for TEST"):
        pipeline.run(d3.tmp, export=path)
    assert d3.calls == []


def test_another_export_flagged_by_the_scan_stays_on_this_machine(d3):
    path = _other_export(d3.tmp / "other.xlsx", ["SEE JANE.ROE@EXAMPLE.ORG CHARGE $50.00"])
    with pytest.raises(ContractError, match="flagged 1 notes") as caught:
        pipeline.run(d3.tmp, export=path)
    assert "JANE" not in str(caught.value) and d3.calls == []
    outcome = pipeline.run(d3.tmp, model_name="local-qwen", export=path)  # a local model sends nothing out
    assert outcome.notes == 1 and len(d3.calls) == 1


# ---- what may be sent
def test_notes_excluded_after_the_scan_are_not_sent_and_go_to_review(d3):
    d3.ws.write_json("scan_decision.json", {"decision": "exclude_flagged"})
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    assert not any("JOHN.DOE" in call.user for call in d3.calls)
    flagged = next(line for line in run_lines(outcome.workbook) if line["note"] == EMAIL_NOTE)
    assert flagged["outcome"] == "review"


def test_a_dataset_not_cleared_is_not_sent(d3):
    text = (d3.tmp / pipeline.CONFIG).read_text(encoding="utf-8").replace("open_anonymized", "client_confidential")
    (d3.tmp / pipeline.CONFIG).write_text(text, encoding="utf-8")
    with pytest.raises(ContractError, match="client_confidential"):
        pipeline.run(d3.tmp, set_name="train", limit=2)
    assert d3.calls == []


# ---- budget and failures
def test_a_spent_budget_sends_the_rest_to_review_and_still_writes_the_workbook(d3):
    settings = yaml.safe_load((d3.tmp / pipeline.SETTINGS).read_text(encoding="utf-8"))
    settings["budget"]["max_usd_per_run"] = "0.01"  # one call costs 0.004, so three calls start
    settings["runtime"]["concurrency"] = 1
    (d3.tmp / pipeline.SETTINGS).write_text(yaml.safe_dump(settings), encoding="utf-8")
    outcome = pipeline.run(d3.tmp, set_name="train", limit=6)
    reasons = [result.review_reason for result in outcome.note_results.values()]
    assert len(d3.calls) == 3 and reasons.count("budget_exhausted") == 3
    assert outcome.workbook.exists()
    assert {"budget_exhausted"} <= {line["outcome_reason"] for line in run_lines(outcome.workbook)}


def test_missing_budget_settings_stop_the_run_before_any_call(d3):
    settings = yaml.safe_load((d3.tmp / pipeline.SETTINGS).read_text(encoding="utf-8"))
    del settings["budget"]
    (d3.tmp / pipeline.SETTINGS).write_text(yaml.safe_dump(settings), encoding="utf-8")
    with pytest.raises(ContractError, match="budget.max_usd_per_run"):
        pipeline.run(d3.tmp, set_name="train", limit=2)
    assert d3.calls == []


def test_a_provider_failure_goes_to_review_and_a_repeat_run_recovers(d3):
    d3.broken.add("claude-opus-5-5")
    down = pipeline.run(d3.tmp, set_name="train", limit=3)
    assert {result.review_reason for result in down.note_results.values()} == {"provider_unavailable"}
    d3.broken.clear()
    back = pipeline.run(d3.tmp, set_name="train", limit=3)
    assert {result.status for result in back.note_results.values()} == {"ok"}


# ---- worked examples
def test_a_worked_example_outside_train_stops_the_run_and_names_the_note(d3):
    outsider = sp.notes_in_set(d3.manifest, "VALIDATION")[0]
    _write_fewshots(d3, [outsider])
    with pytest.raises(ContractError, match=d3.notes[outsider].note_id):
        pipeline.run(d3.tmp, set_name="train", limit=2)
    assert d3.calls == []


def test_prompt_files_in_the_repo_hold_no_note_text():
    text = (ROOT / "prompts/fewshot_v1.yaml").read_text(encoding="utf-8")
    entries = yaml.safe_load(text)["examples"]
    assert entries and all(set(item) <= {"category", "amount", "start", "end", "line_type", "derivation", "basis"} for e in entries for item in e["items"])
    assert all(set(entry) <= {"note_id", "source", "items"} for entry in entries)


# ---- the registry
def test_an_unknown_model_lists_the_available_names(d3):
    result = runner.invoke(app, ["run", "--model", "nobody", "--set", "train"])
    assert result.exit_code == 2 and "claude-opus-5-5" in result.stderr and "claude-haiku-5-5" in result.stderr


def test_a_new_entry_in_the_registry_is_usable_with_no_code_change(d3):
    registry = yaml.safe_load((d3.tmp / pipeline.MODELS).read_text(encoding="utf-8"))
    registry["models"]["claude-next"] = {**registry["models"]["claude-sonnet-5-5"], "model": "claude-next-1"}
    (d3.tmp / pipeline.MODELS).write_text(yaml.safe_dump(registry), encoding="utf-8")
    outcome = pipeline.run(d3.tmp, model_name="claude-next", set_name="train", limit=2)
    stored = json.loads((outcome.folder / "manifest.json").read_text(encoding="utf-8"))
    assert stored["model"]["name"] == "claude-next" and stored["model"]["model"] == "claude-next-1"
    specs, _ = load_models(d3.tmp / pipeline.MODELS)
    assert stored["model"] == specs["claude-next"].model_dump(mode="json")  # the full entry, not only its name
    assert {"provider", "effort", "refusal_fallback", "max_tokens", "api_key_env", "input_usd_per_mtok", "output_usd_per_mtok",
            "cache_read_usd_per_mtok", "cache_write_usd_per_mtok"} <= set(stored["model"])
    assert {call.model for call in d3.calls} == {"claude-next"}


def test_itemizer_models_lists_entries_and_never_the_key(d3):
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0 and "claude-opus-5-5" in result.stdout and "CLAUDE_API_KEY is set" in result.stdout
    assert SECRET not in result.stdout


# ---- commands print counts and paths
def test_commands_print_no_note_text(d3):
    result = runner.invoke(app, ["run", "--set", "train", "--limit", "5"])
    assert result.exit_code == 0
    assert not any(word in result.stdout for word in NOTE_WORDS) and SECRET not in result.stdout
    assert "cost_this_run_usd" in result.stdout


# ---- evaluate
def test_evaluate_scores_all_rows_on_test_and_says_the_labels_are_provisional(d3):
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    snapshot = pipeline.evaluate_run(d3.tmp, outcome.run_id)
    assert snapshot["labels_status"] == "provisional" and snapshot["accuracy_scope"] == "in_sample"
    assert snapshot["levels"]["level1"]["status"] == "pass" and snapshot["levels"]["level1"]["labels_status"] == "provisional"
    assert snapshot["accuracy"]["test_notes"] == 200 and snapshot["invariants"]["violations"] == 0
    assert snapshot["coverage"]["rows"]["total"] == len(d3.rows)
    assert kpi.snapshot_path(d3.tmp / "data", outcome.run_id, "d3").exists()


def test_evaluate_finds_the_newest_run_on_all_rows_by_itself(d3):
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    pipeline.run(d3.tmp, set_name="train", limit=2)
    assert pipeline.evaluate_run(d3.tmp)["run_id"] == outcome.run_id


def test_evaluate_results_hold_aggregates_only(d3):
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    pipeline.evaluate_run(d3.tmp, outcome.run_id)
    written = every_file(d3.tmp / "data" / "kpi")
    assert not any(word in written for word in NOTE_WORDS)
    assert not re.search(r"\bR\d{4}\b", written)


def test_a_development_run_cannot_be_scored_on_test(d3):
    freeze(d3)
    outcome = pipeline.run(d3.tmp, set_name="train", limit=2)
    with pytest.raises(ContractError, match="all rows"):
        pipeline.evaluate_run(d3.tmp, outcome.run_id)
    assert not (d3.tmp / "data" / "kpi" / "test_budget.jsonl").exists()


def test_a_second_run_on_test_is_refused_and_the_refusal_is_logged(d3):
    freeze(d3)
    pipeline.evaluate_run(d3.tmp, pipeline.run(d3.tmp).run_id)
    other = pipeline.run(d3.tmp, model_name="claude-sonnet-5-5")
    with pytest.raises(ContractError):
        pipeline.evaluate_run(d3.tmp, other.run_id)
    events = [json.loads(line)["event"] for line in (d3.tmp / "data" / "kpi" / "test_budget.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events == ["spent", "refused"]


def test_scoring_the_same_run_again_is_free_and_the_status_changes_once_sealed(d3):
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    assert pipeline.evaluate_run(d3.tmp, outcome.run_id)["labels_status"] == "provisional"

    path = fill_review(d3)
    assert lb.import_client_review(d3.ws, path, "client_owner", "2026-11-05", d3.notes, CODES)["errors"] == 0
    record = lb.seal(d3.ws, d3.ws.read_json("split_manifest.json"), d3.notes, CODES)
    assert "sha256" in record

    again = pipeline.evaluate_run(d3.tmp, outcome.run_id)
    assert again["labels_status"] == "sealed" and again["levels"]["level1"]["labels_status"] == "sealed"
    events = [json.loads(line)["event"] for line in (d3.tmp / "data" / "kpi" / "test_budget.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events == ["spent", "rescored"]


def test_a_broken_invariant_fails_every_level(d3):
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    path = outcome.folder / "note_results.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    first = next(result for result in stored.values() if result["items"])
    first["items"][0]["evidence_text"] += " CHANGED"
    path.write_text(json.dumps(stored), encoding="utf-8")
    levels = pipeline.evaluate_run(d3.tmp, outcome.run_id)["levels"]
    assert {level["status"] for level in levels.values()} == {"fail"}
    assert {level["reason"] for level in levels.values()} == {"invariant_failed"}


def test_a_run_folder_whose_manifest_was_changed_is_refused(d3):
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    path = outcome.folder / "manifest.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["limit"] = 3
    path.write_text(json.dumps(stored), encoding="utf-8")
    with pytest.raises(ContractError, match="does not match"):
        pipeline.evaluate_run(d3.tmp, outcome.run_id)


def test_a_run_id_cannot_climb_out_of_the_runs_folder(d3):
    freeze(d3)
    with pytest.raises(ContractError, match="run id looks like"):
        pipeline.evaluate_run(d3.tmp, "../../etc")


def test_evaluate_with_no_run_says_so(d3):
    freeze(d3)
    with pytest.raises(ContractError, match="no run on all rows"):
        pipeline.evaluate_run(d3.tmp)


# ---- the provisional freeze through the command line
def test_gt_seal_provisional_allows_the_run_on_all_rows(d3):
    seal_ready(d3)
    assert lb.import_client_review(d3.ws, fill_review(d3), "team_provisional", "2026-11-04", d3.notes, CODES)["errors"] == 0
    result = runner.invoke(app, ["gt", "seal", "--provisional"])
    assert result.exit_code == 0, result.stderr
    assert lb.is_test_frozen(d3.ws) and pipeline.run(d3.tmp).rows == len(d3.rows)
    assert categories_for(d3)  # the category list is unchanged by the freeze


# ---- the final seal through the command line
def _approve(d3) -> None:
    email = d3.tmp / "approval_email.txt"
    email.write_text("Approved.", encoding="utf-8")
    tx.record_approval(d3.tmp / pipeline.CATEGORIES, d3.tmp / pipeline.APPROVAL, "client_owner", "2026-11-05", email)


def test_gt_seal_after_the_freeze_uses_the_clients_review_and_releases_the_reserve(d3):
    freeze(d3)
    assert sp.notes_in_set(d3.ws.read_json("split_manifest.json"), "RESERVE")
    assert lb.import_client_review(d3.ws, fill_review(d3), "client_owner", "2026-11-05", d3.notes, CODES)["errors"] == 0
    _approve(d3)
    result = runner.invoke(app, ["gt", "seal"])
    assert result.exit_code == 0, result.stderr
    manifest = d3.ws.read_json("split_manifest.json")
    assert manifest["reserve_released"] and not sp.notes_in_set(manifest, "RESERVE")
    assert lb.load_test_gold(d3.ws)[1] == "sealed"


def test_gt_seal_stops_without_the_clients_approval(d3):
    freeze(d3)
    assert lb.import_client_review(d3.ws, fill_review(d3), "client_owner", "2026-11-05", d3.notes, CODES)["errors"] == 0
    result = runner.invoke(app, ["gt", "seal"])
    assert result.exit_code != 0 and "approval" in result.stderr + result.stdout
    assert lb.load_test_gold(d3.ws)[1] == "provisional" and not d3.ws.exists("seal_record.json")


# ---- a score belongs to the run's own inputs
def _ledger(d3) -> list[str]:
    path = d3.tmp / "data" / "kpi" / "test_budget.jsonl"
    if not path.exists():
        return []
    return [json.loads(line)["event"] for line in path.read_text(encoding="utf-8").splitlines()]


def _settings(d3, change) -> None:
    settings = yaml.safe_load((d3.tmp / pipeline.SETTINGS).read_text(encoding="utf-8"))
    change(settings)
    (d3.tmp / pipeline.SETTINGS).write_text(yaml.safe_dump(settings), encoding="utf-8")


def _rename_a_category(d3) -> None:
    taxonomy = tx.load_taxonomy(d3.tmp / pipeline.CATEGORIES)
    next(c for c in taxonomy["categories"] if c["code"] == "cat_5")["code"] = "cat_renamed"
    tx.write_taxonomy(d3.tmp / pipeline.CATEGORIES, taxonomy)


def test_moving_a_gate_after_scoring_is_refused_with_nothing_charged(d3):
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    before = pipeline.evaluate_run(d3.tmp, outcome.run_id)
    _settings(d3, lambda s: s["gates"]["level1"].update(acc=0.10))
    with pytest.raises(ContractError, match="out of date.*config/run.yaml"):
        pipeline.evaluate_run(d3.tmp, outcome.run_id)
    assert _ledger(d3) == ["spent"]
    on_file = json.loads(kpi.snapshot_path(d3.tmp / "data", outcome.run_id, "d3").read_text(encoding="utf-8"))
    assert on_file["levels"]["level1"]["conditions"]["acc"]["target"] == before["levels"]["level1"]["conditions"]["acc"]["target"] == 0.95


def test_changing_a_category_after_the_run_is_refused_with_nothing_charged(d3):
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    _rename_a_category(d3)
    with pytest.raises(ContractError, match="out of date: the category list"):
        pipeline.evaluate_run(d3.tmp, outcome.run_id)
    assert _ledger(d3) == []


def test_a_run_that_uses_the_renamed_list_can_be_scored_on_purpose(d3):
    freeze(d3)
    pipeline.evaluate_run(d3.tmp, pipeline.run(d3.tmp).run_id)
    _rename_a_category(d3)
    new = pipeline.run(d3.tmp)
    with pytest.raises(ContractError, match="--extra-peek"):
        pipeline.evaluate_run(d3.tmp, new.run_id)
    snapshot = pipeline.evaluate_run(d3.tmp, new.run_id, extra_peek="client renamed a category at approval")
    assert snapshot["test_budget"] == {"event": "extra_spent", "budget": 1, "runs_spent": 2, "extra_peeks": 1}
    assert _ledger(d3) == ["spent", "refused", "extra_spent"]


@pytest.mark.parametrize("change", [lambda s: s["budget"].update(max_usd_per_run="99.00"), lambda s: s["runtime"].update(concurrency=2)])
def test_a_budget_or_concurrency_change_keeps_the_runs_identity(d3, change):
    freeze(d3)
    first = pipeline.run(d3.tmp)
    pipeline.evaluate_run(d3.tmp, first.run_id)
    _settings(d3, change)
    second = pipeline.run(d3.tmp)
    assert second.run_id == first.run_id
    assert pipeline.evaluate_run(d3.tmp, second.run_id)["test_budget"]["event"] == "rescored"


def test_a_run_with_unanswered_notes_spends_nothing_and_a_repeat_recovers_it(d3):
    freeze(d3)
    d3.broken.add("claude-opus-5-5")
    down = pipeline.run(d3.tmp)
    with pytest.raises(ContractError, match="got no answer"):
        pipeline.evaluate_run(d3.tmp, down.run_id)
    assert _ledger(d3) == []
    d3.broken.clear()
    back = pipeline.run(d3.tmp)
    assert back.run_id == down.run_id
    assert pipeline.evaluate_run(d3.tmp, back.run_id)["levels"]["level1"]["status"] == "pass"
    assert _ledger(d3) == ["spent"]


def test_new_answers_under_one_run_id_are_a_new_run(d3):
    freeze(d3)
    first = pipeline.run(d3.tmp)
    pipeline.evaluate_run(d3.tmp, first.run_id)
    shutil.rmtree(d3.tmp / "data" / "cache")
    d3.wrong_on = "LUMPER"
    second = pipeline.run(d3.tmp)
    assert second.run_id == first.run_id
    with pytest.raises(ContractError, match="budget for milestone d3 is spent"):
        pipeline.evaluate_run(d3.tmp, second.run_id)


def test_a_milestone_outside_the_list_has_no_budget(d3):
    freeze(d3)
    first, second = pipeline.run(d3.tmp), pipeline.run(d3.tmp, model_name="claude-sonnet-5-5")
    pipeline.evaluate_run(d3.tmp, first.run_id)
    result = runner.invoke(app, ["evaluate", "--run", second.run_id, "--milestone", "d3b"])
    assert result.exit_code == 2 and "not in kpi.milestones" in result.stderr
    assert _ledger(d3) == ["spent"]


@pytest.mark.parametrize("edit", [
    lambda rows: [row.update(outcome="no_charge_stated", outcome_reason="no_charge_in_note") for row in rows if row["outcome"] == "discrepancy"],
    lambda rows: rows.pop(),
    lambda rows: rows[0].update(disputed="0.00"),
])
def test_a_row_file_that_does_not_follow_from_the_notes_is_refused(d3, edit):
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    path = outcome.folder / "row_results.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    edit(rows)
    path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ContractError, match="does not follow"):
        pipeline.evaluate_run(d3.tmp, outcome.run_id)
    assert _ledger(d3) == []


def test_the_scan_decision_is_part_of_the_runs_identity(d3):
    first = pipeline.run(d3.tmp, set_name="train", limit=2)
    d3.ws.write_json("scan_decision.json", {"decision": "exclude_flagged"})
    assert pipeline.run(d3.tmp, set_name="train", limit=2).run_id != first.run_id


def test_a_commit_changing_nothing_keeps_the_run_and_the_workbook(d3):
    def git(*args):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=d3.tmp, check=True, capture_output=True)

    (d3.tmp / ".gitignore").write_text("data/\n.env\n*.xlsx\n", encoding="utf-8")
    git("init", "-q")
    git("add", ".")
    git("commit", "-q", "-m", "first")
    first = pipeline.run(d3.tmp, set_name="train", limit=3)
    digest = hash_of(first.workbook)
    (d3.tmp / "notes.md").write_text("A document changed.", encoding="utf-8")
    git("add", ".")
    git("commit", "-q", "-m", "docs only")
    second = pipeline.run(d3.tmp, set_name="train", limit=3)
    assert second.run_id == first.run_id and hash_of(second.workbook) == digest
    assert second.manifest.code_commit != first.manifest.code_commit


# ---- what is kept back stays back
def _add_model(d3, name: str, **entry) -> None:
    registry = yaml.safe_load((d3.tmp / pipeline.MODELS).read_text(encoding="utf-8"))
    registry["models"][name] = {"refusal_fallback": False, "input_usd_per_mtok": "0", "output_usd_per_mtok": "0", "cache_read_usd_per_mtok": "0",
                                "cache_write_usd_per_mtok": "0", **entry}
    (d3.tmp / pipeline.MODELS).write_text(yaml.safe_dump(registry), encoding="utf-8")


def _not_cleared(d3) -> None:
    text = (d3.tmp / pipeline.CONFIG).read_text(encoding="utf-8").replace("open_anonymized", "client_confidential")
    (d3.tmp / pipeline.CONFIG).write_text(text, encoding="utf-8")


def test_a_remote_server_under_a_local_providers_name_is_external(d3):
    _add_model(d3, "not-local", provider="ollama", model="m", base_url="http://models.example.com:11434")
    _not_cleared(d3)
    with pytest.raises(ContractError, match="client_confidential"):
        pipeline.run(d3.tmp, model_name="not-local", set_name="train", limit=2)
    assert d3.calls == []


@pytest.mark.parametrize("provider, url", [("ollama", "http://localhost:11434"), ("openai_compatible", "http://127.0.0.1:8000/v1")])
def test_a_server_on_this_machine_is_local_under_any_provider_name(d3, provider, url):
    _add_model(d3, "here", provider=provider, model="m", base_url=url)
    _not_cleared(d3)
    assert pipeline.run(d3.tmp, model_name="here", set_name="train", limit=2).notes == 2


def test_a_worked_example_the_scan_keeps_back_stops_the_run(d3):
    flagged = next(fp for fp, note in d3.notes.items() if note.text == EMAIL_NOTE)
    manifest = d3.ws.read_json("split_manifest.json")
    next(entry for entry in manifest["notes"] if entry["fingerprint"] == flagged)["set"] = "TRAIN"
    d3.ws.write_json("split_manifest.json", manifest)
    d3.ws.write_json("scan_decision.json", {"decision": "exclude_flagged"})
    _write_fewshots(d3, [flagged])
    with pytest.raises(ContractError, match=d3.notes[flagged].note_id):
        pipeline.run(d3.tmp, set_name="train", limit=2)
    assert d3.calls == []


def test_a_scan_that_does_not_match_the_dataset_stops_an_external_send(d3):
    d3.ws.write_json("scan_report.json", {"counts": {}, "notes_flagged": 0, "findings": []})
    with pytest.raises(ContractError, match="does not match the dataset"):
        pipeline.run(d3.tmp, set_name="train", limit=2)
    assert d3.calls == []


# ---- a new split, and the role on a review
def test_a_new_split_keeps_notes_with_tool_output_out_of_test_and_reserve(d3):
    outcome = pipeline.run(d3.tmp, set_name="train")
    text = (d3.tmp / pipeline.CONFIG).read_text(encoding="utf-8").replace("split:\n", "split:\n  seed: 99\n")
    (d3.tmp / pipeline.CONFIG).write_text(text, encoding="utf-8")
    result = runner.invoke(app, ["gt", "split", "--force"])
    assert result.exit_code == 0, result.stderr
    manifest = d3.ws.read_json("split_manifest.json")
    held_back = set(sp.notes_in_set(manifest, "TEST") + sp.notes_in_set(manifest, "RESERVE"))
    assert held_back and not held_back & set(outcome.note_results)


def test_a_review_import_needs_a_stated_role(d3):
    freeze(d3)
    before = d3.ws.path("client_review.json").read_bytes()
    result = runner.invoke(app, ["gt", "import-client", str(fill_review(d3)), "--date", "2026-11-05"])
    assert result.exit_code != 0 and d3.ws.path("client_review.json").read_bytes() == before
