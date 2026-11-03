"""Tests per scenario for the provisional freeze and the final seal after it. Every note here is invented."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest
from test_bootstrap import categories_for, fill_pack, fill_review, seal_ready, world  # noqa: F401 (world is a fixture)

from itemizer.bootstrap import labels as lb
from itemizer.bootstrap import split as sp
from itemizer.bootstrap.data import ContractError

CODES = {f"cat_{i}" for i in range(12)}
TEAM, CLIENT = "team_provisional", "client_owner"
INVENTED_NOTE_WORDS = ("LUMPER", "STOP", "BASE RATE", "JOHN.DOE", "CREDIT ISSUED")


def disagree_on_all(note, index, answer):
    return {**answer, "category": "cat_1"}


def review(world, role=TEAM, decision="accept_A", skip=0) -> dict:
    return lb.import_client_review(world.ws, fill_review(world, decision, skip), role, "2026-11-04", world.notes, CODES)


def freeze(world) -> dict:
    return lb.seal_provisional(world.ws, world.manifest, world.notes, CODES)


def frozen(world, change_b=None) -> dict:
    """TEST frozen on a team's review, and the pack assignment."""
    packs = seal_ready(world, change_b)
    assert review(world)["errors"] == 0
    freeze(world)
    return packs


def correct(path: Path, note, category: str = "cat_5") -> None:
    """Mark one note `correct` in the review workbook, keeping only its first charge."""
    workbook = openpyxl.load_workbook(path)
    sheet = workbook["Review"]
    at = [c.value for c in sheet[1]].index("decision")
    for row in sheet.iter_rows(min_row=2):
        if row[0].value == note.note_id:
            row[at].value = "correct"
    evidence = note.text.split(" + ")[0]
    amount = float(evidence.rsplit("$", 1)[1])
    workbook["Corrections"].append([note.note_id, None, None, None, 1, category, amount, evidence, "charge", "stated", None, None])
    workbook.save(path)


# ---- not frozen
def test_nothing_is_frozen_at_first(world):
    assert lb.is_test_frozen(world.ws) is False
    with pytest.raises(ContractError, match="not frozen"):
        lb.load_test_gold(world.ws)


# ---- spec: before the client's review
def test_team_resolved_labels_freeze_test_as_provisional(world):
    packs = seal_ready(world, disagree_on_all)
    assert world.ws.read_json("agreement.json")["disagreements"]
    assert review(world, TEAM, "accept_B")["errors"] == 0

    record = freeze(world)

    assert lb.is_test_frozen(world.ws) is True
    gold, status = lb.load_test_gold(world.ws)
    assert status == "provisional"
    assert set(gold) == set(sp.notes_in_set(world.manifest, "TEST")) and len(gold) == 200
    assert gold[packs["label_A"][0]].items[0].category == "cat_1", "the team's decision is the label"
    assert all(isinstance(i.amount, Decimal) for label in gold.values() for i in label.items)
    assert record == world.ws.read_json("provisional_record.json")
    assert record["notes"] == 200 and record["single"] == 100 and record["reviewer_role"] == TEAM
    assert record["sha256"] == lb.sha256_file(world.ws.path("test_provisional.json"))


def test_provisional_freeze_keeps_the_reserve_and_writes_no_final_seal(world):
    seal_ready(world)
    review(world)
    manifest_before = world.ws.path("split_manifest.json").read_bytes()
    reserve = sp.notes_in_set(world.manifest, "RESERVE")
    freeze(world)
    assert reserve and sp.notes_in_set(world.manifest, "RESERVE") == reserve
    assert world.ws.path("split_manifest.json").read_bytes() == manifest_before
    assert not world.ws.read_json("split_manifest.json")["reserve_released"]
    for name in ("seal_record.json", "test_sealed.json", "test_fingerprints.txt"):
        assert not world.ws.exists(name)


@pytest.mark.parametrize("role", [TEAM, CLIENT, "adjudicator"])
def test_a_complete_review_by_any_role_is_enough(world, role):
    seal_ready(world)
    assert review(world, role)["errors"] == 0
    assert freeze(world)["reviewer_role"] == role


def test_categories_need_no_approval_but_must_be_in_the_current_list(world):
    seal_ready(world)
    review(world)
    with pytest.raises(ContractError, match="outside the current list: cat_0") as refused:
        lb.seal_provisional(world.ws, world.manifest, world.notes, {"cat_9"})
    assert not lb.is_test_frozen(world.ws)
    assert not any(word in str(refused.value) for word in INVENTED_NOTE_WORDS)
    assert freeze(world)["notes"] == 200, "the same labels pass against the list they use, with no approval on file"


# ---- what it requires
def test_freeze_refuses_fewer_than_200_notes(world):
    seal_ready(world)
    review(world)
    next(e for e in world.manifest["notes"] if e["set"] == "TEST")["set"] = "TRAIN"
    with pytest.raises(ContractError, match="TEST cannot be frozen: TEST has 199 distinct notes, not 200"):
        freeze(world)
    assert not lb.is_test_frozen(world.ws)


def test_freeze_refuses_label_errors_and_missing_packs(world):
    seal_ready(world)
    review(world)
    stored = world.ws.read_json("labels/label_single.json")
    stored["errors"] = [{"note_id": "n_1", "row": 2, "code": "bad_amount", "message": "invented"}]
    world.ws.write_json("labels/label_single.json", stored)
    world.ws.path("labels/label_B.json").unlink()
    with pytest.raises(ContractError) as refused:
        freeze(world)
    assert "label_single has 1 label errors" in str(refused.value)
    assert "label_B has not been imported" in str(refused.value)
    assert not lb.is_test_frozen(world.ws)


def test_freeze_refuses_when_no_review_was_imported(world):
    seal_ready(world)
    with pytest.raises(ContractError, match="the review has not been imported"):
        freeze(world)


def test_freeze_refuses_an_incomplete_review_and_unresolved_disagreements(world):
    seal_ready(world, disagree_on_all)
    assert review(world, skip=10)["reviewed"] == 40
    with pytest.raises(ContractError) as refused:
        freeze(world)
    assert "has not reviewed 10 of the 50" in str(refused.value)
    assert "10 disagreements are unresolved" in str(refused.value)
    assert not lb.is_test_frozen(world.ws)


def test_freeze_refuses_a_review_with_problems(world):
    seal_ready(world)
    assert review(world, decision="correct")["error_codes"] == {"correction_missing": 50}
    with pytest.raises(ContractError, match="the review has 50 problems"):
        freeze(world)


def test_freeze_refuses_a_mix_outside_the_limit(world):
    packs = seal_ready(world)
    review(world)
    stored = world.ws.read_json("labels/label_single.json")
    shortened = [fp for fp in packs["label_single"] if len(stored["labels"][fp]["items"]) > 1][:30]
    for fp in shortened:
        stored["labels"][fp]["items"] = stored["labels"][fp]["items"][:1]
    world.ws.write_json("labels/label_single.json", stored)
    assert len(shortened) == 30
    with pytest.raises(ContractError, match="the labelled mix is 130 single and 70 other"):
        freeze(world)
    assert not lb.is_test_frozen(world.ws)


# ---- a freeze is a freeze
def test_second_freeze_is_refused(world):
    frozen(world)
    before = world.ws.path("test_provisional.json").read_bytes()
    with pytest.raises(ContractError, match="already frozen"):
        freeze(world)
    assert world.ws.path("test_provisional.json").read_bytes() == before


@pytest.mark.parametrize("pack", ["label_A", "label_B", "label_single"])
def test_gold_labels_cannot_be_reimported_after_the_freeze(world, pack):
    frozen(world)
    with pytest.raises(ContractError, match="TEST is frozen"):
        lb.import_labels(world.ws, pack, world.ws.path(f"packs/{pack}.xlsx"), "a", world.notes, CODES)


def test_validation_labels_can_still_be_imported_after_the_freeze(world):
    frozen(world)
    result = lb.import_labels(world.ws, "validation", world.ws.path("packs/validation.xlsx"), "a", world.notes, CODES)
    assert result["pack"] == "validation"


def test_frozen_labels_changed_or_missing_are_refused(world):
    frozen(world)
    name = "test_provisional.json"
    original = world.ws.path(name).read_text(encoding="utf-8")
    world.ws.path(name).write_text(original.replace('"cat_0"', '"cat_1"'), encoding="utf-8")
    with pytest.raises(ContractError, match=f"{name} is missing or was changed after provisional_record.json"):
        lb.load_test_gold(world.ws)
    world.ws.path(name).unlink()
    with pytest.raises(ContractError, match="missing or was changed"):
        lb.load_test_gold(world.ws)


def test_record_holds_no_note_text(world):
    frozen(world)
    text = world.ws.path("provisional_record.json").read_text(encoding="utf-8")
    assert not any(word in text for word in INVENTED_NOTE_WORDS)


# ---- which review counts
def test_client_review_overwrites_the_team_review(world):
    packs = seal_ready(world, disagree_on_all)
    fp = packs["label_A"][0]
    review(world, TEAM, "accept_B")
    stored = world.ws.read_json("client_review.json")
    assert stored["reviewer_role"] == TEAM and stored["decisions"][fp]["label"]["items"][0]["category"] == "cat_1"
    review(world, CLIENT, "accept_A")
    stored = world.ws.read_json("client_review.json")
    assert stored["reviewer_role"] == CLIENT and stored["decisions"][fp]["label"]["items"][0]["category"] == "cat_0"
    assert lb.gold_labels(world.ws)[fp].items[0].category == "cat_0"


def test_a_team_can_redo_its_own_review_before_the_freeze(world):
    seal_ready(world)
    assert review(world, TEAM, skip=10)["reviewed"] == 40
    assert review(world, TEAM)["reviewed"] == 50


def test_client_review_after_the_freeze_changes_nothing_until_the_final_seal(world):
    packs = frozen(world)
    before = lb.load_test_gold(world.ws)
    target = world.notes[packs["label_A"][0]]
    path = fill_review(world)
    correct(path, target)
    assert lb.import_client_review(world.ws, path, CLIENT, "2026-11-05", world.notes, CODES)["errors"] == 0
    assert lb.load_test_gold(world.ws) == before
    assert lb.gold_labels(world.ws)[target.fingerprint].items[0].category == "cat_5"


def test_team_review_cannot_replace_the_clients(world):
    seal_ready(world)
    review(world, CLIENT)
    before = world.ws.path("client_review.json").read_bytes()
    with pytest.raises(ContractError, match="client's review is already imported"):
        review(world, TEAM)
    assert world.ws.path("client_review.json").read_bytes() == before


def test_team_review_after_the_freeze_is_refused(world):
    frozen(world)
    before = world.ws.path("client_review.json").read_bytes()
    with pytest.raises(ContractError, match="only the client's review"):
        review(world, TEAM)
    assert world.ws.path("client_review.json").read_bytes() == before


# ---- final seal
@pytest.mark.parametrize("role", [TEAM, "adjudicator"])
def test_final_seal_rejects_any_review_but_the_clients(world, role):
    seal_ready(world)
    review(world, role)
    with pytest.raises(ContractError, match=f"the review is by {role}.*client_owner"):
        lb.seal(world.ws, world.manifest, world.notes, CODES)
    assert not world.ws.exists("seal_record.json") and not lb.is_test_frozen(world.ws)


def test_final_seal_after_the_freeze_still_rejects_the_team_review(world):
    frozen(world)
    reserve = sp.notes_in_set(world.manifest, "RESERVE")
    with pytest.raises(ContractError, match="the review is by team_provisional"):
        lb.seal(world.ws, world.manifest, world.notes, CODES)
    assert lb.load_test_gold(world.ws)[1] == "provisional"
    assert sp.notes_in_set(world.manifest, "RESERVE") == reserve


def test_final_seal_after_the_freeze_still_needs_approved_categories(world):
    frozen(world)
    review(world, CLIENT)
    with pytest.raises(ContractError, match="no valid client approval"):
        lb.seal(world.ws, world.manifest, world.notes, None)
    with pytest.raises(ContractError, match="outside the approved list"):
        lb.seal(world.ws, world.manifest, world.notes, {"cat_9"})
    assert lb.load_test_gold(world.ws)[1] == "provisional"


def test_final_seal_after_the_freeze_uses_the_clients_labels_and_releases_the_reserve(world):
    packs = frozen(world)
    target = world.notes[packs["label_A"][0]]
    provisional, status = lb.load_test_gold(world.ws)
    assert status == "provisional" and provisional[target.fingerprint].items[0].category == "cat_0"
    frozen_bytes = world.ws.path("test_provisional.json").read_bytes()
    reserve = set(sp.notes_in_set(world.manifest, "RESERVE"))

    path = fill_review(world)
    correct(path, target)
    assert lb.import_client_review(world.ws, path, CLIENT, "2026-11-05", world.notes, CODES)["errors"] == 0
    record = lb.seal(world.ws, world.manifest, world.notes, CODES)

    sealed, status = lb.load_test_gold(world.ws)
    assert status == "sealed" and lb.is_test_frozen(world.ws)
    assert sealed[target.fingerprint].items[0].category == "cat_5"
    assert record["reviewer_role"] == CLIENT and record["review_date"] == "2026-11-05"
    assert record["sha256"] == lb.sha256_file(world.ws.path("test_sealed.json"))
    released = world.ws.read_json("split_manifest.json")
    sets = {e["fingerprint"]: e["set"] for e in released["notes"]}
    assert released["reserve_released"] and {sets[fp] for fp in reserve} <= {"TRAIN", "VALIDATION"}
    assert world.ws.path("test_provisional.json").read_bytes() == frozen_bytes, "the provisional record is kept"


def test_final_seal_without_a_provisional_freeze_loads_as_sealed(world):
    seal_ready(world)
    review(world, CLIENT)
    lb.seal(world.ws, world.manifest, world.notes, CODES)
    gold, status = lb.load_test_gold(world.ws)
    assert status == "sealed" and len(gold) == 200
    assert not world.ws.exists("provisional_record.json")


def test_after_the_final_seal_nothing_can_change(world):
    frozen(world)
    review(world, CLIENT)
    lb.seal(world.ws, world.manifest, world.notes, CODES)
    with pytest.raises(ContractError, match="already sealed"):
        freeze(world)
    for role in (TEAM, CLIENT):
        with pytest.raises(ContractError, match="sealed"):
            review(world, role)
    world.ws.path("test_sealed.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="test_sealed.json is missing or was changed"):
        lb.load_test_gold(world.ws)


def test_mix_moved_by_the_client_can_still_be_fixed_from_the_reserve(world):
    """This is why the freeze keeps the reserve: a client's correction can move the mix, and it must not block the seal."""
    world.ws.cfg = world.cfg.model_copy(update={"max_stratum_gap_notes": 0})
    packs = frozen(world)
    provisional, _ = lb.load_test_gold(world.ws)
    target = next(world.notes[fp] for fp in packs["label_A"] if " + " in world.notes[fp].text)
    path = fill_review(world)
    correct(path, target)
    assert lb.import_client_review(world.ws, path, CLIENT, "2026-11-05", world.notes, CODES)["errors"] == 0
    with pytest.raises(ContractError, match="the labelled mix is 101 single and 99 other"):
        lb.seal(world.ws, world.manifest, world.notes, CODES)

    plan = lb.final_strata(world.ws, world.manifest, world.notes, apply=True)
    assert plan["replace"] == 1 and plan["shortage"] == 0
    added = world.ws.read_json("packs.json")["label_replacements"]
    pack = world.ws.path("packs/label_replacements.xlsx")
    lb.write_pack(pack, "TEST", added, world.notes, categories_for(world))
    fill_pack(pack, world.notes)
    assert lb.import_labels(world.ws, "label_replacements", pack, "c", world.notes, CODES)["errors"] == 0

    lb.seal(world.ws, world.manifest, world.notes, CODES)
    sealed, status = lb.load_test_gold(world.ws)
    assert status == "sealed" and len(sealed) == 200
    assert added[0] in sealed and added[0] not in provisional
    assert json.loads(world.ws.path("seal_record.json").read_text())["single"] == 100
