"""Tests per scenario for TEST labels drafted by a model. Every note is invented, and every model is a fake."""
from __future__ import annotations

import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from test_bootstrap import fill_review
from test_pipeline import CODES, NOTE_WORDS, ROOT, StubModel, _settings, d3, hash_of  # noqa: F401 (d3 is a fixture)
from typer.testing import CliRunner

from itemizer import acceptance, model_labels, pipeline
from itemizer.bootstrap import labels as lb
from itemizer.bootstrap import split as sp
from itemizer.bootstrap import taxonomy as tx
from itemizer.bootstrap.data import ContractError, DisputeRow, group_notes
from itemizer.cli import app
from itemizer.contracts import ChargeItem, NoteResult
from itemizer.itemize import build_user_prompt
from itemizer.providers import ProviderRefused

TODAY = "2026-11-03"
runner = CliRunner()


@pytest.fixture
def labels(d3):
    """The d3 project with the labelling prompt, the blank packs and no labels yet."""
    shutil.copy(ROOT / model_labels.LABEL_PROMPT, d3.tmp / model_labels.LABEL_PROMPT)
    categories = tx.load_taxonomy(d3.tmp / pipeline.CATEGORIES)["categories"]
    d3.packs = lb.build_packs(d3.ws, d3.manifest, d3.notes, categories)
    return d3


def draft(world) -> dict:
    return model_labels.draft_test_labels(world.tmp, TODAY)


def provisional(world) -> dict:
    return lb.seal_provisional(world.ws, world.ws.read_json("split_manifest.json"), world.notes, CODES)


# ---- a model drafts only when asked
def test_a_dry_run_sends_nothing_and_says_what_would_go(labels):
    result = runner.invoke(app, ["gt", "draft-test-labels"])
    assert result.exit_code == 0, result.stderr
    assert labels.calls == [] and "Nothing was sent" in result.stdout and '"label_single": 150' in result.stdout
    assert not labels.ws.exists("labels/label_A.json")


def test_drafting_labels_every_test_note_and_nothing_else(labels):
    report = draft(labels)
    assert report["complete"] and {pack: line["errors"] for pack, line in report["packs"].items()} == {"label_A": 0, "label_B": 0, "label_single": 0}
    assert {pack: line["labelled"] for pack, line in report["packs"].items()} == {"label_A": 50, "label_B": 50, "label_single": 150}
    sent = {call.user for call in labels.calls}
    test = set(sp.notes_in_set(labels.manifest, "TEST"))
    assert sent == {build_user_prompt(labels.notes[fp]) for fp in test}
    assert len(labels.calls) == 250  # 50 notes twice, and 150 once


def test_each_pack_uses_its_model(labels):
    report = draft(labels)
    assert report["packs"]["label_A"]["model"] == report["packs"]["label_single"]["model"] == model_labels.FIRST_LABELLER
    assert report["packs"]["label_B"]["model"] == model_labels.SECOND_LABELLER
    specs = {call.model for call in labels.calls}
    assert specs == {model_labels.FIRST_LABELLER, model_labels.SECOND_LABELLER}


def test_the_labellers_are_opus_with_no_fallback():
    registry = yaml.safe_load((ROOT / pipeline.MODELS).read_text(encoding="utf-8"))["models"]
    for name in (model_labels.FIRST_LABELLER, model_labels.SECOND_LABELLER):
        assert registry[name]["model"] == "claude-opus-5-5" and registry[name]["refusal_fallback"] is False


def test_blank_packs_stay_blank_for_people(labels):
    before = hash_of(labels.ws.path("packs/label_A.xlsx"))
    draft(labels)
    assert hash_of(labels.ws.path("packs/label_A.xlsx")) == before
    assert labels.ws.path("packs/filled/label_A.model.xlsx").exists()


def test_a_dataset_not_cleared_is_not_sent(labels):
    text = (labels.tmp / pipeline.CONFIG).read_text(encoding="utf-8").replace("open_anonymized", "client_confidential")
    (labels.tmp / pipeline.CONFIG).write_text(text, encoding="utf-8")
    with pytest.raises(ContractError, match="client_confidential"):
        draft(labels)
    assert labels.calls == []


def test_a_budget_stop_leaves_notes_unlabelled_and_a_repeat_continues(labels):
    _settings(labels, lambda s: (s["budget"].update(max_usd_per_run="0.05"), s["runtime"].update(concurrency=1)))
    stopped = draft(labels)
    made = len(labels.calls)
    stopped_notes = sum(line["no_answer"].get("budget_exhausted", 0) for line in stopped["packs"].values())
    assert not stopped["complete"] and made < 250 and stopped_notes == 250 - made
    assert "agreement" not in stopped
    _settings(labels, lambda s: s["budget"].update(max_usd_per_run="20.00"))
    finished = draft(labels)
    assert finished["complete"] and len(labels.calls) == 250  # the first answers came from the cache
    assert "sha256" in provisional(labels)


def test_the_budget_covers_the_whole_job_and_not_each_pack(labels, monkeypatch):
    budgets = []
    original = pipeline._budget
    monkeypatch.setattr(pipeline, "_budget", lambda settings: budgets.append(1) or original(settings))
    draft(labels)
    assert len(budgets) == 1


# ---- the same checks, and no tool output
def test_the_labeller_gets_the_rules_and_categories_and_no_tool_output(labels):
    trained = pipeline.run(labels.tmp, set_name="train", limit=3)
    tool_system = {call.system for call in labels.calls}
    labels.calls.clear()
    draft(labels)
    systems = {call.system for call in labels.calls}
    assert len(systems) == 1 and not systems & tool_system
    system = systems.pop()
    assert "Evidence must be copied exactly" in system and "`cat_0`" in system and "{{" not in system
    assert "Do not run the tool" not in system and "Answer:" not in system  # no worked examples
    held = json.loads((trained.folder / "note_results.json").read_text(encoding="utf-8"))
    assert not any(result["items"] and result["items"][0]["evidence_text"] in system for result in held.values())


def test_an_answer_that_fails_the_label_checks_is_rejected_at_import(labels, monkeypatch):
    original = model_labels.fill_pack

    def tampered(blank, target, results):
        first = next(iter(results.values()))
        broken = first.items[0].model_copy(update={"evidence_text": "WORDS NOT IN THE NOTE"})
        results[first.fingerprint] = first.model_copy(update={"items": [broken, *first.items[1:]]})
        original(blank, target, results)

    monkeypatch.setattr(model_labels, "fill_pack", tampered)
    report = draft(labels)
    assert not report["complete"] and report["packs"]["label_A"]["error_codes"] == {"evidence_not_verbatim": 1}


def test_a_note_the_model_refuses_stays_unlabelled_and_stops_the_freeze(labels, monkeypatch):
    target = labels.notes[labels.packs["label_single"][0]]

    class Refuses(StubModel):
        def complete(self, system, user, schema):
            if target.text in user:
                raise ProviderRefused("declined")
            return super().complete(system, user, schema)

    monkeypatch.setattr(pipeline, "get_provider", lambda spec, client=None, project_root=None: Refuses(spec, labels.calls))
    report = draft(labels)
    assert not report["complete"] and report["packs"]["label_single"]["no_answer"] == {"refused": 1}
    assert report["packs"]["label_single"]["labelled"] == 149
    assert target.fingerprint not in labels.ws.read_json("labels/label_single.json")["labels"]
    result = runner.invoke(app, ["gt", "seal", "--provisional"])
    assert result.exit_code != 0 and not lb.is_test_frozen(labels.ws)


def test_a_command_with_no_label_for_every_note_says_so(labels, monkeypatch):
    monkeypatch.setattr(pipeline, "get_provider", lambda spec, client=None, project_root=None: StubModel(spec, labels.calls, fail=True))
    result = runner.invoke(app, ["gt", "draft-test-labels", "--send"])
    assert result.exit_code == 1 and "Some notes have no label" in result.stdout
    assert not any(word in result.stdout for word in NOTE_WORDS)


def test_the_command_prints_no_note_text(labels):
    result = runner.invoke(app, ["gt", "draft-test-labels", "--send"])
    assert result.exit_code == 0, result.stderr
    assert not any(word in result.stdout for word in NOTE_WORDS) and '"complete": true' in result.stdout


def test_a_doubt_reaches_the_label_for_people_to_check_first(labels, monkeypatch):
    target = labels.notes[labels.packs["label_single"][0]]

    class Doubtful(StubModel):
        def complete(self, system, user, schema):
            reply = super().complete(system, user, schema)
            if target.text not in user:
                return reply
            answer = json.loads(reply.text)
            answer["reason_code"] = "amount_unclear"
            return reply.model_copy(update={"text": json.dumps(answer)})

    monkeypatch.setattr(pipeline, "get_provider", lambda spec, client=None, project_root=None: Doubtful(spec, labels.calls))
    report = draft(labels)
    assert report["packs"]["label_single"]["in_doubt"] == 1
    stored = labels.ws.read_json("labels/label_single.json")["labels"][target.fingerprint]
    assert stored["comment"] == "amount_unclear" and stored["source"] == "model_draft"


# ---- writing into a pack
def _result(note, *items, **fields) -> NoteResult:
    return NoteResult(fingerprint=note.fingerprint, note_id=note.note_id, status="ok", model="fake", items=list(items), **fields)


def _item(number, text, start, amount, category="cat_0") -> ChargeItem:
    return ChargeItem(item=number, category=category, amount=Decimal(amount), evidence_text=text, evidence_start=start, evidence_end=start + len(text),
                      line_type="charge", derivation="stated", basis="named_in_note")


def _pack_for(tmp: Path, text: str):
    row = DisputeRow(row_id="R1", shipment="S", invoice="I", carrier="C", event_date="2022-01-01", estimated=Decimal(1), billed=Decimal(2),
                     disputed=Decimal(1), status="O", reason="X", note=text)
    notes = group_notes([row], Decimal("180.00"))
    note = next(iter(notes.values()))
    blank = tmp / "blank.xlsx"
    lb.write_pack(blank, "TEST", [note.fingerprint], notes, [{"code": "cat_0", "name": "c", "definition": "d"}])
    return notes, note, blank


def _read_back(notes, note, target):
    lines = lb._read_label_lines(target, "Labels")
    return lb.parse_lines(lines, {note.fingerprint}, notes, {"cat_0"}, "model", "label_single")


def test_more_charges_than_blank_lines_all_arrive(tmp_path):
    text = " ".join(f"F{n} ${n}.00" for n in range(1, 9))
    notes, note, blank = _pack_for(tmp_path, text)
    items, at = [], 0
    for n in range(1, 9):
        part = f"F{n} ${n}.00"
        items.append(_item(n, part, text.index(part), f"{n}.00"))
    model_labels.fill_pack(blank, tmp_path / "out.xlsx", {note.fingerprint: _result(note, *items)})
    parsed, errors = _read_back(notes, note, tmp_path / "out.xlsx")
    assert errors == [] and [i.amount for i in parsed[note.fingerprint].items] == [Decimal(n) for n in range(1, 9)]
    assert parsed[note.fingerprint].source == "model_draft"


def test_evidence_starting_with_an_equals_sign_stays_text(tmp_path):
    text = "=$5.00 LUMPER"
    notes, note, blank = _pack_for(tmp_path, text)
    model_labels.fill_pack(blank, tmp_path / "out.xlsx", {note.fingerprint: _result(note, _item(1, "=$5.00", 0, "5.00"))})
    parsed, errors = _read_back(notes, note, tmp_path / "out.xlsx")
    assert errors == [] and parsed[note.fingerprint].items[0].evidence_text == "=$5.00"


def test_no_charge_stated_is_written_as_the_flag(tmp_path):
    notes, note, blank = _pack_for(tmp_path, "NO CHARGE ON THIS ONE")
    model_labels.fill_pack(blank, tmp_path / "out.xlsx", {note.fingerprint: _result(note, no_charge_stated=True)})
    parsed, errors = _read_back(notes, note, tmp_path / "out.xlsx")
    assert errors == [] and parsed[note.fingerprint].no_charge_stated and parsed[note.fingerprint].items == []


# ---- marked wherever they count
def test_drafts_are_stored_as_drafts_with_the_models_name(labels):
    draft(labels)
    for pack, model in (("label_A", model_labels.FIRST_LABELLER), ("label_B", model_labels.SECOND_LABELLER), ("label_single", model_labels.FIRST_LABELLER)):
        stored = labels.ws.read_json(f"labels/{pack}.json")["labels"].values()
        assert {label["source"] for label in stored} == {"model_draft"} and {label["labeller"] for label in stored} == {model}


def test_a_model_review_is_recorded_as_a_models(labels):
    draft(labels)
    review = labels.ws.read_json("client_review.json")
    assert review["reviewer_role"] == lb.MODEL_ROLE and {d["decision"] for d in review["decisions"].values()} == {"accept_A"}
    assert len(review["decisions"]) == 50


def test_the_snapshot_and_the_page_say_the_labels_are_drafts(labels):
    draft(labels)
    assert "sha256" in provisional(labels)
    outcome = pipeline.run(labels.tmp)
    snapshot = pipeline.evaluate_run(labels.tmp, outcome.run_id)
    assert snapshot["labels_sources"] == {"model_draft": 200} and snapshot["labels_status"] == "provisional"
    summary = acceptance.d3_check(labels.tmp)
    assert summary["d2"]["written_by_model"] == 200 and summary["d2"]["checked_by_person"] == 0
    text = Path(summary["page"]).read_text(encoding="utf-8")
    assert "200 of the 200 TEST labels behind these figures were written by Claude Opus" in text
    assert "shows how far the tool agrees with those labels, and not that it is right" in text
    assert text.index("Read this first") < text.index("D1: charge category list")
    assert "200 of the labels are drafts written by Claude Opus" in text


def test_a_person_labelled_test_set_carries_no_draft_flag(d3):
    from test_pipeline import freeze

    freeze(d3)
    pipeline.evaluate_run(d3.tmp, pipeline.run(d3.tmp).run_id)
    text = Path(acceptance.d3_check(d3.tmp)["page"]).read_text(encoding="utf-8")
    assert "written by Claude Opus" not in text


# ---- a draft cannot be final
def test_the_final_seal_refuses_while_drafts_remain(labels):
    draft(labels)
    provisional(labels)
    assert lb.import_client_review(labels.ws, fill_review(labels), lb.CLIENT_ROLE, "2026-11-05", labels.notes, CODES)["errors"] == 0
    with pytest.raises(ContractError, match="150 TEST labels are model drafts"):
        lb.seal(labels.ws, labels.ws.read_json("split_manifest.json"), labels.notes, CODES)
    assert lb.load_test_gold(labels.ws)[1] == "provisional"


def test_a_client_accepting_a_draft_counts_as_a_persons_check(labels):
    draft(labels)
    assert lb.import_client_review(labels.ws, fill_review(labels), lb.CLIENT_ROLE, "2026-11-05", labels.notes, CODES)["errors"] == 0
    decisions = labels.ws.read_json("client_review.json")["decisions"].values()
    assert {decision["label"]["source"] for decision in decisions} == {"person_checked"}


def test_draft_labels_cannot_be_redrafted_once_frozen(labels):
    draft(labels)
    provisional(labels)
    with pytest.raises(ContractError, match="import-label-review"):
        draft(labels)


def test_validation_labels_are_not_drafted(labels):
    draft(labels)
    validation = set(sp.notes_in_set(labels.manifest, "VALIDATION"))
    assert not any(labels.notes[fp].text in call.user for fp in validation for call in labels.calls)
    assert not labels.ws.exists("labels/validation.json")


def test_the_mix_is_reported_after_drafting(labels):
    report = draft(labels)
    assert {"labelled", "single", "multi_or_large", "replace"} <= set(report["mix"]) and report["mix"]["labelled"] == 200


def test_the_labels_prompt_needs_its_placeholders(tmp_path):
    path = tmp_path / "bad.md"
    path.write_text("no placeholders", encoding="utf-8")
    with pytest.raises(ContractError, match="must hold both"):
        model_labels.build_label_prompt([], path)
