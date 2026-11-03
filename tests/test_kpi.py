"""Tests per scenario for the KPI Calculator. Every note here is invented, and the expected numbers are worked by hand."""
from __future__ import annotations

import json
import random
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from pytest import approx

from itemizer import kpi
from itemizer.bootstrap.data import ContractError, Note, NoteLabel, fingerprint, format_key, money_tokens
from itemizer.bootstrap.labels import check_item
from itemizer.contracts import ChargeItem, GoldItem, NoteResult, RowResult, RunManifest

CODES = {"detention", "lumper", "base_rate_correction", "tax", "other_unmapped"}
TOLERANCE = Decimal("0.01")
RUN_YAML = Path(__file__).resolve().parents[1] / "config" / "run.yaml"
LEVEL1 = {"cov_usd": 0.80, "cov_rows": 0.25, "acc": 0.95}
LEVEL2 = {"cov_usd": 0.90, "cov_rows": 0.85, "acc": 0.95}
LEVEL3 = {"cov_usd": 0.95, "cov_rows": 0.95, "acc": 0.95}
CLEAN = {"violations": 0}


def plain_item(category: str, amount: str) -> ChargeItem:
    """An item for the matcher, which reads only category and amount."""
    return ChargeItem(item=1, category=category, amount=Decimal(amount), evidence_text=f"{category} {amount}",
                      evidence_start=0, evidence_end=1, line_type="charge", derivation="stated", basis="named_in_note")


def make_row(row_id: str = "R0001", outcome: str = "verified", disputed: str = "10.00", **fields) -> RowResult:
    reasons = {"verified": "adds_up", "discrepancy": "does_not_add_up", "no_charge_stated": "no_charge_in_note",
               "review": "model_unsure"}
    values = {"shipment": "SHIP-A", "invoice": "INV-A", "carrier": "CARR1", "status": "OPEN", "reason": "OTHER",
              "outcome_reason": reasons[outcome], **fields}
    return RowResult(row_id=row_id, disputed=Decimal(disputed), outcome=outcome, **values)


def make_note(text: str, disputed: str = "10.00") -> Note:
    fp = fingerprint(text)
    amount = Decimal(disputed)
    return Note(fingerprint=fp, note_id=f"n_{fp[:8]}", text=text, row_ids=["R0001"], carrier="CARR1", disputed=amount,
                max_disputed=amount, usd=amount, format_key=format_key(text), money_tokens=money_tokens(text), band="1",
                stratum="single")


def accepted(note: Note, category: str, amount: str, evidence: str, number: int = 1, line_type: str = "charge",
             derivation: str = "stated") -> ChargeItem:
    """An item the way the parser accepts one."""
    item, errors = check_item(note, number, category, amount, evidence, line_type, derivation, CODES)
    assert errors == []
    return ChargeItem(**item.model_dump(), basis="named_in_note")


def ok_result(note: Note, items: list[ChargeItem] | None = None, no_charge: bool = False) -> NoteResult:
    return NoteResult(fingerprint=note.fingerprint, note_id=note.note_id, items=items or [], no_charge_stated=no_charge,
                      status="ok", model="fake")


def scored_notes(spec: list[tuple[str, int, bool]]) -> SimpleNamespace:
    """(stratum, rows, correct) per note, with the matcher's inputs built so that each note comes out as stated."""
    entries, results, gold, rows = [], {}, {}, {}
    for number, (stratum, row_count, correct) in enumerate(spec):
        fp, note_id = f"fp{number:04d}", f"n_{number:04d}"
        entries.append({"fingerprint": fp, "note_id": note_id, "set": "TEST", "provisional_stratum": stratum,
                        "rows": row_count, "format_in_train": number % 2 == 0})
        results[fp] = NoteResult(fingerprint=fp, note_id=note_id, status="ok", model="fake",
                                 items=[plain_item("lumper", "85.00" if correct else "90.00")])
        gold[fp] = NoteLabel(fingerprint=fp, note_id=note_id, labeller="a", pack="p", items=[plain_item("lumper", "85.00")])
        rows[fp] = row_count
    return SimpleNamespace(entries=entries, results=results, gold=gold, rows=rows)


def run_accuracy(notes: SimpleNamespace, shares: dict[str, float], seed: int = 7, resamples: int = 200) -> dict:
    return kpi.accuracy(notes.entries, notes.results, notes.gold, notes.rows, shares, seed, resamples, tolerance=TOLERANCE)


# Worked by hand:
#   large  (share 0.1): 3 rows right, 1 row wrong             -> 3/4  = 0.75
#   multi  (share 0.3): 2 rows right, 2 rows right            -> 4/4  = 1.00
#   single (share 0.6): 5 rows right, 1 row wrong, 4 right    -> 9/10 = 0.90
#   weighted = 0.1*0.75 + 0.3*1.00 + 0.6*0.90 = 0.075 + 0.3 + 0.54 = 0.915
#   unweighted = 5 of 7 notes
HAND_NOTES = [("large", 3, True), ("large", 1, False), ("multi", 2, True), ("multi", 2, True),
              ("single", 5, True), ("single", 1, False), ("single", 4, True)]
HAND_SHARES = {"large": 0.1, "multi": 0.3, "single": 0.6}


# --- Wilson ---

def test_wilson_at_n_200_matches_the_hand_values():
    low, high = kpi.wilson(192, 200)
    assert low == approx(0.923067, abs=1e-4) and high == approx(0.979597, abs=1e-4)
    assert kpi.wilson(197, 200)[0] == approx(0.956847, abs=1e-4)


def test_wilson_on_a_small_sample_matches_the_hand_values():
    low, high = kpi.wilson(5, 7)
    assert low == approx(0.358941, abs=1e-4) and high == approx(0.917789, abs=1e-4)


def test_wilson_edges_stay_inside_zero_and_one():
    assert kpi.wilson(0, 10)[0] == approx(0.0, abs=1e-12)
    assert kpi.wilson(10, 10)[1] == approx(1.0, abs=1e-12)
    assert kpi.wilson(0, 0) == (None, None)


# --- Coverage ---

def hand_rows() -> list[RowResult]:
    return [make_row("R1", "verified", "400.00"), make_row("R2", "discrepancy", "300.00", repeated=True),
            make_row("R3", "discrepancy", "300.00", repeated=True), make_row("R4", "no_charge_stated", "100.00"),
            make_row("R5", "review", "400.00"), make_row("R6", "review", "-100.00")]


def test_coverage_counts_rows_and_plain_dollars_by_hand():
    found = kpi.coverage(hand_rows())
    assert (found["rows"]["covered"], found["rows"]["total"]) == (4, 6)
    assert found["rows"]["share"] == approx(4 / 6)
    assert found["rows"]["ci_low"] == approx(0.299991, abs=1e-4) and found["rows"]["ci_high"] == approx(0.903229, abs=1e-4)
    # 400 + 300 + 300 + 100 covered, of a plain sum that also holds the 400 in Review and the -100 credit.
    assert found["usd"]["covered"] == "1100.00" and found["usd"]["total"] == "1400.00"
    assert found["usd"]["share"] == approx(1100 / 1400)
    assert found["usd"]["n"] == 6


def test_dollar_interval_uses_the_effective_sample_size_by_hand():
    usd = kpi.coverage(hand_rows())["usd"]
    # (400+300+300+100+400+100)^2 / (400^2+300^2+300^2+100^2+400^2+100^2) = 1600^2 / 520000
    assert usd["effective_n"] == approx(4.923077, abs=1e-5)
    assert usd["ci_low"] == approx(0.361359, abs=1e-4) and usd["ci_high"] == approx(0.959613, abs=1e-4)


def test_one_large_row_narrows_the_effective_sample_size():
    rows = [make_row(f"R{i}", disputed="1.00") for i in range(9)] + [make_row("R9", disputed="1000.00")]
    usd = kpi.coverage(rows)["usd"]
    assert usd["n"] == 10 and usd["effective_n"] < 1.1


def test_coverage_with_and_without_repeats():
    """Spec: a covered shipment has five repeated rows, and both figures appear."""
    rows = [make_row("R0", "verified", "8400.00")] + [make_row(f"R{i}", "discrepancy", "8000.00", repeated=True) for i in range(1, 6)]
    rows.append(make_row("R6", "review", "1000.00"))
    found = kpi.coverage(rows)
    assert found["usd"]["covered"] == "48400.00" and found["usd"]["total"] == "49400.00"
    assert found["usd"]["share"] == approx(48400 / 49400)
    without = found["without_repeats"]
    assert without["usd"]["covered"] == "8400.00" and without["usd"]["total"] == "9400.00"
    assert without["usd"]["share"] == approx(8400 / 9400)
    assert (without["rows"]["covered"], without["rows"]["total"]) == (1, 2)


def test_coverage_of_nothing_does_not_crash():
    found = kpi.coverage([])
    assert found["rows"]["share"] is None and found["rows"]["n"] == 0 and found["rows"]["ci_low"] is None
    assert found["usd"]["share"] is None and found["usd"]["effective_n"] is None


def test_dollar_sum_at_or_below_zero_has_no_share():
    assert kpi.coverage([make_row("R1", "verified", "-5.00")])["usd"]["share"] is None


# --- Item matching ---

def test_swapped_categories_are_two_category_errors():
    """Spec: detention 150 and lumper 85, predicted as detention 85 and lumper 150."""
    gold = [plain_item("detention", "150.00"), plain_item("lumper", "85.00")]
    predicted = [plain_item("detention", "85.00"), plain_item("lumper", "150.00")]
    assert kpi.match_note(predicted, gold, TOLERANCE) == {
        "correct": False, "category_errors": 2, "amount_errors": 0, "missing": 0, "extra": 0}
    assert kpi.match_note(predicted[::-1], gold, TOLERANCE)["category_errors"] == 2


def test_exact_match_in_any_order_is_correct():
    gold = [plain_item("detention", "150.00"), plain_item("lumper", "85.00")]
    assert kpi.match_note(gold[::-1], gold, TOLERANCE)["correct"] is True


def test_two_notes_stating_no_charge_are_correct():
    assert kpi.match_note([], [], TOLERANCE) == {
        "correct": True, "category_errors": 0, "amount_errors": 0, "missing": 0, "extra": 0}


def test_amount_error_needs_a_matching_category():
    found = kpi.match_note([plain_item("lumper", "90.00")], [plain_item("lumper", "85.00")], TOLERANCE)
    assert found == {"correct": False, "category_errors": 0, "amount_errors": 1, "missing": 0, "extra": 0}


def test_tolerance_is_inclusive():
    gold = [plain_item("lumper", "85.00")]
    assert kpi.match_note([plain_item("lumper", "85.01")], gold, "0.01")["correct"] is True
    assert kpi.match_note([plain_item("lumper", "85.02")], gold, "0.01")["amount_errors"] == 1


def test_pair_matching_nothing_is_one_missing_and_one_extra():
    found = kpi.match_note([plain_item("detention", "1.00")], [plain_item("lumper", "85.00")], TOLERANCE)
    assert found == {"correct": False, "category_errors": 0, "amount_errors": 0, "missing": 1, "extra": 1}


def test_extra_and_missing_items_fail_a_note():
    one = [plain_item("lumper", "85.00")]
    two = one + [plain_item("detention", "150.00")]
    assert kpi.match_note(two, one, TOLERANCE) == {
        "correct": False, "category_errors": 0, "amount_errors": 0, "missing": 0, "extra": 1}
    assert kpi.match_note(one, two, TOLERANCE) == {
        "correct": False, "category_errors": 0, "amount_errors": 0, "missing": 1, "extra": 0}
    assert kpi.match_note([], one, TOLERANCE)["missing"] == 1
    assert kpi.match_note(one, [], TOLERANCE)["extra"] == 1


def test_the_assignment_finds_every_cost_zero_pair():
    gold = [plain_item("lumper", "85.00"), plain_item("lumper", "85.00"), plain_item("tax", "4.25")]
    predicted = [plain_item("tax", "4.25"), plain_item("lumper", "85.00"), plain_item("lumper", "85.00")]
    assert kpi.match_note(predicted, gold, TOLERANCE)["correct"] is True
    assert kpi.match_note(predicted[:2], gold, TOLERANCE)["missing"] == 1


# --- Real mix ---

def test_stratum_shares_large_wins_then_item_count():
    rows = [make_row("R1", disputed="500.00", item_count=4), make_row("R2", disputed="180.00"),
            make_row("R3", disputed="20.00", item_count=2), make_row("R4", disputed="20.00", item_count=1),
            make_row("R5", disputed="179.99", item_count=0)]
    assert kpi.stratum_shares(rows, Decimal("180.00")) == {"large": 0.4, "multi": 0.2, "single": 0.4}


def test_stratum_shares_of_nothing():
    assert kpi.stratum_shares([], Decimal("180.00")) == {"large": 0.0, "multi": 0.0, "single": 0.0}


# --- Weighted accuracy ---

def test_weighted_accuracy_by_hand():
    found = run_accuracy(scored_notes(HAND_NOTES), HAND_SHARES)
    assert found["weighted"] == approx(0.915)
    assert found["n"] == 7 and found["test_notes"] == 7 and found["correct"] == 5
    assert found["unweighted"] == approx(5 / 7)
    assert found["wilson_low"] == approx(0.358941, abs=1e-4) and found["wilson_high"] == approx(0.917789, abs=1e-4)
    strata = found["strata"]
    assert strata["large"]["accuracy"] == approx(0.75) and strata["large"]["n"] == 2 and strata["large"]["rows"] == 4
    assert strata["multi"]["accuracy"] == approx(1.0) and strata["multi"]["rows"] == 4
    assert strata["single"]["accuracy"] == approx(0.9) and strata["single"]["rows"] == 10 and strata["single"]["share"] == 0.6
    assert found["dropped_strata"] == []
    assert found["errors"] == {"category_errors": 0, "amount_errors": 2, "missing": 0, "extra": 0}


def test_oversampled_large_notes_contribute_their_real_share():
    """Spec: TEST has 25% large notes and the dataset has 10% large rows."""
    notes = [("large", 1, True)] * 5 + [("single", 1, False)] * 15
    found = run_accuracy(scored_notes(notes), {"large": 0.1, "multi": 0.0, "single": 0.9})
    assert found["weighted"] == approx(0.10)
    assert found["unweighted"] == approx(0.25)


def test_a_note_counts_for_its_rows_within_a_stratum():
    found = run_accuracy(scored_notes([("single", 1, True), ("single", 5, False)]), HAND_SHARES)
    assert found["weighted"] == approx(1 / 6)
    assert found["unweighted"] == approx(0.5)


def test_stratum_with_no_covered_notes_is_dropped_and_recorded():
    notes = scored_notes(HAND_NOTES)
    for fp in ("fp0002", "fp0003"):  # the two multi notes
        notes.results[fp] = NoteResult(fingerprint=fp, note_id="n", status="review", review_reason="model_unsure", model="fake")
    found = run_accuracy(notes, HAND_SHARES)
    # (0.1*0.75 + 0.6*0.90) / (0.1 + 0.6) = 0.615 / 0.7
    assert found["weighted"] == approx(0.878571, abs=1e-5)
    assert found["dropped_strata"] == ["multi"]
    assert found["strata"]["multi"]["n"] == 0 and found["strata"]["multi"]["test_notes"] == 2
    assert found["strata"]["multi"]["accuracy"] is None
    assert found["n"] == 5 and found["test_notes"] == 7


def test_stratum_with_no_test_notes_is_dropped_and_recorded():
    found = run_accuracy(scored_notes([("single", 1, True)]), HAND_SHARES)
    assert found["weighted"] == approx(1.0)
    assert found["dropped_strata"] == ["large", "multi"]


def test_notes_in_review_or_without_a_result_are_not_scored():
    notes = scored_notes([("single", 1, True), ("single", 1, False), ("single", 1, False)])
    notes.results["fp0001"] = NoteResult(fingerprint="fp0001", note_id="n", status="review", review_reason="refused", model="fake")
    del notes.results["fp0002"]
    found = run_accuracy(notes, HAND_SHARES)
    assert found["n"] == 1 and found["weighted"] == approx(1.0) and found["test_notes"] == 3


def test_empty_covered_set_does_not_crash():
    notes = scored_notes(HAND_NOTES)
    found = run_accuracy(SimpleNamespace(entries=notes.entries, results={}, gold=notes.gold, rows=notes.rows), HAND_SHARES)
    assert found["weighted"] is None and found["n"] == 0
    assert found["ci_low"] is None and found["ci_high"] is None
    assert found["unweighted"] is None and found["wilson_low"] is None
    assert found["dropped_strata"] == ["large", "multi", "single"]
    assert found["test_notes"] == 7
    gate = kpi.level_gate("level1", gate_coverage(0.9, 0.9), found, CLEAN, LEVEL1)
    assert gate["status"] == "fail" and gate["reason"] == "target_not_met"
    assert gate["conditions"]["acc"] == {"value": None, "target": 0.95, "met": False, "ci_low": None, "ci_high": None,
                                         "n": 0, "interval_contains_target": None}


def test_formats_seen_and_unseen_in_train_are_reported_apart():
    # scored_notes marks even-numbered notes as seen, so the wrong notes (1 and 5) are both unseen.
    found = run_accuracy(scored_notes(HAND_NOTES), HAND_SHARES)
    assert (found["formats"]["seen"]["n"], found["formats"]["seen"]["correct"]) == (4, 4)
    assert (found["formats"]["unseen"]["n"], found["formats"]["unseen"]["correct"]) == (3, 1)
    assert found["formats"]["unseen"]["accuracy"] == approx(1 / 3)
    assert found["formats"]["unseen"]["wilson_low"] is not None


def test_a_set_stratum_wins_over_the_provisional_one():
    notes = scored_notes([("single", 1, True)])
    notes.entries[0]["stratum"] = "large"
    found = run_accuracy(notes, HAND_SHARES)
    assert found["strata"]["large"]["n"] == 1 and found["strata"]["single"]["n"] == 0


def test_note_without_gold_stops_with_a_count_only():
    notes = scored_notes(HAND_NOTES)
    del notes.gold["fp0000"]
    with pytest.raises(ContractError, match="1 of 7 TEST notes have no gold label") as caught:
        run_accuracy(notes, HAND_SHARES)
    assert "fp0000" not in str(caught.value)


def test_covered_note_without_rows_stops_with_a_count_only():
    notes = scored_notes(HAND_NOTES)
    del notes.rows["fp0000"]
    with pytest.raises(ContractError, match="1 covered TEST notes have no row count"):
        run_accuracy(notes, HAND_SHARES)


def test_stratum_without_a_share_stops():
    with pytest.raises(ContractError, match="no share in the real mix for strata: large"):
        run_accuracy(scored_notes([("large", 1, True)]), {"single": 1.0})


def test_too_few_resamples_stops():
    with pytest.raises(ContractError, match="bootstrap_resamples"):
        run_accuracy(scored_notes(HAND_NOTES), HAND_SHARES, resamples=1)


# --- Bootstrap ---

def varied_notes() -> SimpleNamespace:
    return scored_notes([("single" if i % 3 else "multi", 1 + i % 7, i % 5 != 0) for i in range(40)])


def test_bootstrap_is_seeded_and_reproducible():
    first = run_accuracy(varied_notes(), HAND_SHARES, seed=11)
    again = run_accuracy(varied_notes(), HAND_SHARES, seed=11)
    other = run_accuracy(varied_notes(), HAND_SHARES, seed=12)
    assert (first["ci_low"], first["ci_high"]) == (again["ci_low"], again["ci_high"])
    assert (first["ci_low"], first["ci_high"]) != (other["ci_low"], other["ci_high"])


def test_bootstrap_does_not_depend_on_the_order_of_the_entries():
    notes = varied_notes()
    first = run_accuracy(notes, HAND_SHARES)
    random.Random(1).shuffle(notes.entries)
    assert run_accuracy(notes, HAND_SHARES) == first


def test_bootstrap_resamples_within_each_stratum():
    # Pooled resampling would vary the mix of right and wrong. Within strata, every resample is exactly 0.5.
    notes = scored_notes([("large", 1, True)] * 10 + [("single", 1, False)] * 10)
    found = run_accuracy(notes, {"large": 0.5, "multi": 0.0, "single": 0.5})
    assert found["ci_low"] == approx(0.5) and found["ci_high"] == approx(0.5)


def test_bootstrap_percentiles_on_two_notes_by_hand():
    # Each resample is 0, 0.5 or 1, with chances 1/4, 1/2 and 1/4, so the 2.5th and 97.5th percentiles are 0 and 1.
    found = run_accuracy(scored_notes([("single", 1, True), ("single", 1, False)]), HAND_SHARES, resamples=2000)
    assert found["ci_low"] == 0.0 and found["ci_high"] == 1.0


def test_bootstrap_at_n_200_is_close_to_the_normal_width():
    # 192 of 200: standard error sqrt(0.96*0.04/200) = 0.01386, so about 0.96 +- 0.027.
    notes = scored_notes([("single", 1, True)] * 192 + [("single", 1, False)] * 8)
    found = run_accuracy(notes, HAND_SHARES, resamples=2000)
    assert found["weighted"] == approx(0.96)
    assert found["ci_low"] == approx(0.933, abs=0.006) and found["ci_high"] == approx(0.987, abs=0.006)
    assert found["wilson_low"] == approx(0.923, abs=1e-3) and found["wilson_high"] == approx(0.980, abs=1e-3)


# --- Invariants ---

@pytest.fixture
def lumper_note() -> Note:
    return make_note("LUMPER FEE $85.00 PER DRIVER RECEIPT")


def reconciled_row(note: Note, disputed: str = "85.00", items: str = "85.00", paid: str = "0", **fields) -> RowResult:
    difference = Decimal(disputed) - (Decimal(items) - Decimal(paid))
    return make_row(fields.pop("row_id", "R1"), fields.pop("outcome", "verified"), disputed, note_id=note.note_id,
                    fingerprint=note.fingerprint, items_total=Decimal(items), already_paid_total=Decimal(paid),
                    difference=difference, item_count=1, **fields)


def test_clean_run_has_no_violations(lumper_note):
    results = {lumper_note.fingerprint: ok_result(lumper_note, [accepted(lumper_note, "lumper", "85.00", "LUMPER FEE $85.00")])}
    found = kpi.invariants([reconciled_row(lumper_note)], results, {lumper_note.fingerprint: lumper_note}, CODES,
                           abs_tolerance="0.01")
    assert found == {"violations": 0, "by_code": {}, "items": 1, "verifiable_items": 1, "verifiability": 1.0}


def check_one(note: Note, item: ChargeItem, row: RowResult | None = None) -> dict:
    results = {note.fingerprint: ok_result(note, [item])}
    return kpi.invariants([row] if row else [], results, {note.fingerprint: note}, CODES, abs_tolerance="0.01")


def test_evidence_that_is_not_verbatim_is_a_violation(lumper_note):
    item = accepted(lumper_note, "lumper", "85.00", "LUMPER FEE $85.00").model_copy(update={"evidence_text": "lumper fee 85.00"})
    found = check_one(lumper_note, item)
    assert found["violations"] == 1 and found["by_code"] == {"evidence_not_verbatim": 1}
    assert found["verifiability"] == 0.0


def test_evidence_that_does_not_match_its_offsets_is_a_violation(lumper_note):
    # Real words from the note, but not the words the item points to.
    item = accepted(lumper_note, "lumper", "85.00", "LUMPER FEE $85.00").model_copy(update={"evidence_start": 3})
    assert check_one(lumper_note, item)["by_code"] == {"evidence_not_verbatim": 1}


def test_an_edited_amount_is_a_violation(lumper_note):
    item = accepted(lumper_note, "lumper", "85.00", "LUMPER FEE $85.00").model_copy(update={"amount": Decimal("90.00")})
    found = check_one(lumper_note, item)
    assert found["by_code"] == {"amount_not_in_evidence": 1} and found["verifiable_items"] == 0


def test_an_unknown_category_is_a_violation_but_the_evidence_stays_verifiable(lumper_note):
    item = accepted(lumper_note, "lumper", "85.00", "LUMPER FEE $85.00").model_copy(update={"category": "yard_fee"})
    found = check_one(lumper_note, item)
    assert found["by_code"] == {"unknown_category": 1} and found["verifiability"] == 1.0


def test_rate_times_quantity_is_checked_as_a_product():
    note = make_note("3 PALLETS @ $20.00 EACH")
    item = accepted(note, "lumper", "60.00", "3 PALLETS @ $20.00", derivation="rate_x_quantity")
    assert check_one(note, item)["violations"] == 0
    assert check_one(note, item.model_copy(update={"amount": Decimal("61.00")}))["by_code"] == {"product_mismatch": 1}


def test_numbers_too_long_to_multiply_are_a_violation_and_not_a_crash():
    long_number = "1" * 60
    note = make_note(f"REF {long_number} X {long_number}")
    item = plain_item("lumper", "1.00").model_copy(update={
        "evidence_text": note.text, "evidence_start": 0, "evidence_end": len(note.text), "derivation": "rate_x_quantity"})
    assert check_one(note, item)["by_code"] == {"product_mismatch": 1}


def test_item_on_a_note_not_in_the_dataset_is_a_violation(lumper_note):
    item = accepted(lumper_note, "lumper", "85.00", "LUMPER FEE $85.00")
    found = kpi.invariants([], {lumper_note.fingerprint: ok_result(lumper_note, [item])}, {}, CODES, abs_tolerance="0.01")
    assert found["by_code"] == {"evidence_not_verbatim": 1}


@pytest.mark.parametrize("update", [{"items_total": Decimal("90.00")}, {"already_paid_total": Decimal("1.00")},
                                    {"difference": Decimal("5.00")}, {"difference": None}])
def test_a_row_total_its_items_do_not_give_is_a_violation(lumper_note, update):
    item = accepted(lumper_note, "lumper", "85.00", "LUMPER FEE $85.00")
    row = reconciled_row(lumper_note, outcome="discrepancy").model_copy(update=update)
    assert check_one(lumper_note, item, row)["by_code"] == {"amount_changed": 1}


def test_already_paid_counts_against_the_charges():
    """Spec's row: a 300.00 charge, 100.00 already paid and 200.00 disputed adds up."""
    note = make_note("DETENTION $300.00 LESS PAID $100.00")
    items = [accepted(note, "detention", "300.00", "DETENTION $300.00"),
             accepted(note, "detention", "100.00", "PAID $100.00", number=2, line_type="already_paid")]
    row = reconciled_row(note, disputed="200.00", items="300.00", paid="100.00")
    found = kpi.invariants([row], {note.fingerprint: ok_result(note, items)}, {note.fingerprint: note}, CODES, abs_tolerance="0.01")
    assert found["violations"] == 0 and found["items"] == 2


def test_a_verified_row_that_does_not_add_up_is_a_violation(lumper_note):
    item = accepted(lumper_note, "lumper", "85.00", "LUMPER FEE $85.00")
    assert check_one(lumper_note, item, reconciled_row(lumper_note, disputed="85.01"))["violations"] == 0  # at the tolerance
    assert check_one(lumper_note, item, reconciled_row(lumper_note, disputed="85.02"))["by_code"] == {"unflagged_difference": 1}
    assert check_one(lumper_note, item, reconciled_row(lumper_note, disputed="85.02", outcome="discrepancy"))["violations"] == 0


def test_a_verified_row_that_never_reconciled_is_a_violation(lumper_note):
    row = make_row("R1", "verified", "85.00", note_id=lumper_note.note_id, fingerprint=lumper_note.fingerprint)
    found = kpi.invariants([row], {lumper_note.fingerprint: ok_result(lumper_note, no_charge=True)},
                           {lumper_note.fingerprint: lumper_note}, CODES, abs_tolerance="0.01")
    assert found["by_code"] == {"row_not_reconciled": 1}


def test_a_row_whose_note_has_no_result_is_a_violation(lumper_note):
    row = reconciled_row(lumper_note)
    assert kpi.invariants([row], {}, {}, CODES, abs_tolerance="0.01")["by_code"] == {"row_without_note": 1}


def test_rows_with_nothing_to_reconcile_are_not_violations(lumper_note):
    blank = make_row("R1", "no_charge_stated", "5.00", outcome_reason="empty_note")
    in_review = make_row("R2", "review", "5.00", note_id=lumper_note.note_id, fingerprint=lumper_note.fingerprint)
    results = {lumper_note.fingerprint: NoteResult(fingerprint=lumper_note.fingerprint, note_id=lumper_note.note_id, status="review",
                                                   review_reason="refused", model="fake")}
    found = kpi.invariants([blank, in_review], results, {lumper_note.fingerprint: lumper_note}, CODES, abs_tolerance="0.01")
    assert found == {"violations": 0, "by_code": {}, "items": 0, "verifiable_items": 0, "verifiability": None}


# --- Level gate, Option A ---

def gate_coverage(usd: float | None, rows: float | None) -> dict:
    return {"usd": {"share": usd, "ci_low": None if usd is None else usd - 0.02, "ci_high": None if usd is None else usd + 0.02, "n": 1347},
            "rows": {"share": rows, "ci_low": None if rows is None else rows - 0.02, "ci_high": None if rows is None else rows + 0.02, "n": 1347}}


def gate_accuracy(value: float, low: float, high: float, n: int = 200) -> dict:
    return {"weighted": value, "ci_low": low, "ci_high": high, "n": n}


def test_level_passes_with_the_interval_shown():
    """Spec: dollar coverage 0.83, row coverage 0.31, accuracy 0.96 with interval 0.93 to 0.98."""
    gate = kpi.level_gate("level1", gate_coverage(0.83, 0.31), gate_accuracy(0.96, 0.93, 0.98), CLEAN, LEVEL1)
    assert gate["status"] == "pass" and gate["reason"] is None and gate["level"] == "level1"
    assert gate["conditions"]["acc"] == {"value": 0.96, "target": 0.95, "met": True, "ci_low": 0.93, "ci_high": 0.98, "n": 200,
                                         "interval_contains_target": True}
    assert gate["conditions"]["cov_usd"]["value"] == 0.83 and gate["conditions"]["cov_usd"]["n"] == 1347
    assert gate["conditions"]["cov_rows"]["value"] == 0.31 and gate["conditions"]["cov_rows"]["met"] is True
    assert gate["invariant_violations"] == 0


def test_below_the_target_fails_even_when_the_interval_contains_it():
    """Spec: accuracy 0.94 fails. Option A decides on the value and only shows the interval."""
    gate = kpi.level_gate("level1", gate_coverage(0.83, 0.31), gate_accuracy(0.94, 0.91, 0.97), CLEAN, LEVEL1)
    assert gate["status"] == "fail" and gate["reason"] == "target_not_met"
    assert gate["conditions"]["acc"]["met"] is False and gate["conditions"]["acc"]["interval_contains_target"] is True


def test_above_the_target_passes_even_when_the_interval_excludes_it():
    gate = kpi.level_gate("level1", gate_coverage(0.83, 0.31), gate_accuracy(0.97, 0.96, 0.98), CLEAN, LEVEL1)
    assert gate["status"] == "pass" and gate["conditions"]["acc"]["interval_contains_target"] is False


@pytest.mark.parametrize("name, targets", [("level1", LEVEL1), ("level2", LEVEL2), ("level3", LEVEL3)])
def test_one_invariant_violation_fails_every_level(name, targets):
    """Spec: every level fails with `invariant_failed`, whatever the values."""
    gate = kpi.level_gate(name, gate_coverage(0.99, 0.99), gate_accuracy(0.99, 0.98, 1.0), {"violations": 1}, targets)
    assert gate["status"] == "fail" and gate["reason"] == "invariant_failed" and gate["invariant_violations"] == 1
    assert all(condition["met"] for condition in gate["conditions"].values())


def test_invariant_reason_wins_over_a_missed_target():
    gate = kpi.level_gate("level1", gate_coverage(0.1, 0.1), gate_accuracy(0.5, 0.4, 0.6), {"violations": 2}, LEVEL1)
    assert gate["reason"] == "invariant_failed"


def test_same_values_can_pass_one_level_and_fail_the_next():
    values = gate_coverage(0.83, 0.31), gate_accuracy(0.96, 0.93, 0.98)
    assert kpi.level_gate("level1", *values, CLEAN, LEVEL1)["status"] == "pass"
    level2 = kpi.level_gate("level2", *values, CLEAN, LEVEL2)
    assert level2["status"] == "fail" and level2["conditions"]["cov_usd"]["met"] is False


def test_a_value_exactly_on_the_target_passes():
    exact = gate_accuracy(190 / 200, 0.91, 0.97)
    assert kpi.level_gate("level1", gate_coverage(0.8, 0.25), exact, CLEAN, LEVEL1)["status"] == "pass"


def test_float_noise_cannot_fail_a_weighted_value_on_the_target():
    # 19 of 20 right in every stratum is exactly 0.95, whatever the shares. These shares land just under it in floats.
    notes = [(stratum, 1, number < 19) for stratum in ("large", "multi", "single") for number in range(20)]
    found = run_accuracy(scored_notes(notes), {"large": 1 / 30, "multi": 22 / 30, "single": 7 / 30})
    assert found["weighted"] < 0.95 and found["weighted"] == approx(0.95)
    assert kpi.level_gate("level1", gate_coverage(0.8, 0.25), found, CLEAN, LEVEL1)["status"] == "pass"
    assert kpi.level_gate("level1", gate_coverage(0.8, 0.25), gate_accuracy(0.9499, 0.9, 0.97), CLEAN, LEVEL1)["status"] == "fail"


def test_gate_uses_dollars_with_repeats():
    """Spec: the gates use the scope's figure, which includes repeated rows."""
    rows = [make_row("R1", "verified", "100.00"), make_row("R2", "discrepancy", "800.00", repeated=True), make_row("R3", "review", "100.00")]
    found = kpi.coverage(rows)
    assert found["usd"]["share"] == approx(0.9) and found["without_repeats"]["usd"]["share"] == approx(0.5)
    gate = kpi.level_gate("level1", found, gate_accuracy(0.96, 0.93, 0.98), CLEAN, LEVEL1)
    assert gate["conditions"]["cov_usd"]["value"] == approx(0.9) and gate["conditions"]["cov_usd"]["met"] is True


def test_coverage_with_no_share_does_not_meet_its_condition():
    gate = kpi.level_gate("level1", kpi.coverage([]), gate_accuracy(0.96, 0.93, 0.98), CLEAN, LEVEL1)
    assert gate["status"] == "fail" and gate["conditions"]["cov_rows"]["met"] is False
    assert gate["conditions"]["cov_usd"]["interval_contains_target"] is None


@pytest.mark.parametrize("targets", [{"cov_usd": 0.8, "cov_rows": 0.25}, {"cov_usd": "lots", "cov_rows": 0.25, "acc": 0.95}, None])
def test_bad_targets_stop_with_a_plain_message(targets):
    with pytest.raises(ContractError, match="targets for level9"):
        kpi.level_gate("level9", gate_coverage(0.83, 0.31), gate_accuracy(0.96, 0.93, 0.98), CLEAN, targets)


# --- TEST budget ---

def ledger_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_re_evaluating_the_same_run_is_free(tmp_path):
    path = tmp_path / "kpi" / "ledger.jsonl"
    assert kpi.spend_test_budget(path, "run_a", "d3", 1) == {"event": "spent", "budget": 1, "runs_spent": 1, "extra_peeks": 0}
    assert kpi.spend_test_budget(path, "run_a", "d3", 1) == {"event": "rescored", "budget": 1, "runs_spent": 1, "extra_peeks": 0}
    assert kpi.spend_test_budget(path, "run_a", "d3", 1)["event"] == "rescored"
    assert [e["event"] for e in ledger_lines(path)] == ["spent", "rescored", "rescored"]


def test_second_run_is_refused_and_the_refusal_is_logged(tmp_path):
    """Spec: a different run at a milestone whose budget of 1 is spent."""
    path = tmp_path / "ledger.jsonl"
    kpi.spend_test_budget(path, "run_a", "d3", 1)
    with pytest.raises(ContractError, match="budget for milestone d3 is spent") as caught:
        kpi.spend_test_budget(path, "run_b", "d3", 1)
    assert "run_b" in str(caught.value) and str(path) in str(caught.value)
    last = ledger_lines(path)[-1]
    assert last["event"] == "refused" and last["run_id"] == "run_b" and last["milestone"] == "d3"
    assert last["who"] and last["when"]


def test_a_refusal_spends_nothing(tmp_path):
    path = tmp_path / "ledger.jsonl"
    kpi.spend_test_budget(path, "run_a", "d3", 1)
    for _ in range(2):
        with pytest.raises(ContractError):
            kpi.spend_test_budget(path, "run_b", "d3", 1)
    assert kpi.spend_test_budget(path, "run_a", "d3", 1)["event"] == "rescored"
    assert kpi.spend_test_budget(path, "run_c", "d3", 2) == {"event": "spent", "budget": 2, "runs_spent": 2, "extra_peeks": 0}


def test_budget_is_per_milestone(tmp_path):
    path = tmp_path / "ledger.jsonl"
    kpi.spend_test_budget(path, "run_a", "d3", 1)
    assert kpi.spend_test_budget(path, "run_b", "d4", 1)["event"] == "spent"


def test_budget_of_zero_refuses_the_first_run(tmp_path):
    with pytest.raises(ContractError):
        kpi.spend_test_budget(tmp_path / "ledger.jsonl", "run_a", "d3", 0)


@pytest.mark.parametrize("line", ["not json", "[1, 2]", '{"event": "spent"}'])
def test_a_ledger_it_cannot_read_stops_the_evaluation(tmp_path, line):
    path = tmp_path / "ledger.jsonl"
    path.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(ContractError, match="cannot be read"):
        kpi.spend_test_budget(path, "run_a", "d3", 1)


# --- Evaluate ---

SHIP_A, INV_A = "SHP-INVENTED-A", "INV-INVENTED-A"


@pytest.fixture
def world(tmp_path) -> SimpleNamespace:
    """Five TEST notes on seven rows. Worked by hand:

    rows covered 6 of 7. Dollars covered 85+85+135+900+10+5 = 1220 of 1260. Without the repeated row, 1135 of 1175.
    Row mix: 1 large, 1 multi (item_count 2) and 5 single. The note in Review is not scored, so 4 notes are, all right.
    """
    single = make_note("LUMPER FEE $85.00 PER RECEIPT", "85.00")
    multi = make_note("DETENTION $50.00 PLUS LUMPER $85.00", "135.00")
    large = make_note("BASE RATE CORRECTION $900.00 AGREED", "900.00")
    unclear = make_note("SEE THE ATTACHED MEMO ABOUT THIS BILL", "40.00")
    nothing = make_note("CARRIER CONFIRMED NO EXTRA COST", "10.00")
    all_notes = {n.fingerprint: n for n in (single, multi, large, unclear, nothing)}

    single_item = accepted(single, "lumper", "85.00", "LUMPER FEE $85.00")
    multi_items = [accepted(multi, "detention", "50.00", "DETENTION $50.00"),
                   accepted(multi, "lumper", "85.00", "LUMPER $85.00", number=2)]
    large_item = accepted(large, "base_rate_correction", "900.00", "BASE RATE CORRECTION $900.00")
    results = {
        single.fingerprint: ok_result(single, [single_item]),
        multi.fingerprint: ok_result(multi, multi_items),
        large.fingerprint: ok_result(large, [large_item]),
        unclear.fingerprint: NoteResult(fingerprint=unclear.fingerprint, note_id=unclear.note_id, status="review",
                                        review_reason="model_unsure", reason_code="charge_unclear", model="fake"),
        nothing.fingerprint: ok_result(nothing, no_charge=True),
    }
    place = {"shipment": SHIP_A, "invoice": INV_A}
    rows = [
        reconciled_row(single, row_id="R0001", **place),
        reconciled_row(single, row_id="R0002", outcome="discrepancy", outcome_reason="repeated_invoice", repeated=True, **place),
        reconciled_row(multi, "135.00", "135.00", row_id="R0003", **place).model_copy(update={"item_count": 2}),
        reconciled_row(large, "900.00", "900.00", row_id="R0004", carrier="CARR2", **place),
        make_row("R0005", "review", "40.00", note_id=unclear.note_id, fingerprint=unclear.fingerprint, carrier="CARR2",
                 note=unclear.text, **place),
        make_row("R0006", "no_charge_stated", "10.00", note_id=nothing.note_id, fingerprint=nothing.fingerprint, carrier="CARR2",
                 note=nothing.text, **place),
        make_row("R0007", "no_charge_stated", "5.00", outcome_reason="empty_note", carrier="CARR3", **place),
    ]
    entries = [{"fingerprint": n.fingerprint, "note_id": n.note_id, "set": "TEST", "provisional_stratum": "single",
                "repeat_band": "1", "rows": sum(r.fingerprint == n.fingerprint for r in rows), "disputed_usd": str(n.usd),
                "format_hash": format_key(n.text)[:12], "format_in_train": n is not single} for n in all_notes.values()]

    def label(note: Note, items: list[GoldItem], no_charge: bool = False) -> NoteLabel:
        return NoteLabel(fingerprint=note.fingerprint, note_id=note.note_id, labeller="invented", pack="label_single",
                         no_charge_stated=no_charge, items=[GoldItem(**i.model_dump(exclude={"basis"})) for i in items])

    gold = {single.fingerprint: label(single, [single_item]), multi.fingerprint: label(multi, multi_items),
            large.fingerprint: label(large, [large_item]), unclear.fingerprint: label(unclear, [], no_charge=True),
            nothing.fingerprint: label(nothing, [], no_charge=True)}
    manifest = RunManifest(dataset_sha256="d" * 64, set_name="all", taxonomy_sha256="t" * 64, prompt_sha256="p" * 64,
                           fewshot_sha256="f" * 64, grammar_version="1", model={"name": "fake"}, config_sha256="c" * 64,
                           code_sha="a" * 40, code_dirty=False, split_sha256="s" * 64)
    settings = yaml.safe_load(RUN_YAML.read_text(encoding="utf-8"))
    settings["kpi"]["bootstrap_resamples"] = 200
    return SimpleNamespace(root=tmp_path / "data", manifest=manifest, rows=rows, results=results, notes=all_notes, entries=entries,
                           gold=gold, settings=settings, single=single, multi=multi, unclear=unclear, nothing=nothing,
                           evidence=[i.evidence_text for r in results.values() for i in r.items])


def run_evaluate(world: SimpleNamespace, **changes) -> dict:
    arguments = dict(data_root=world.root, manifest=world.manifest, milestone="d3", row_results=world.rows,
                     note_results=world.results, notes=world.notes, codes=CODES, test_entries=world.entries, gold=world.gold,
                     labels_status="provisional", settings=world.settings, large_usd=Decimal("180.00"), seed=20261102)
    return kpi.evaluate(**{**arguments, **changes})


def strings_in(value) -> list[str]:
    """Every key and every string value, at any depth. Anything other than JSON's own types stops the walk."""
    if isinstance(value, dict):
        return [text for key, inner in value.items() for text in [str(key), *strings_in(inner)]]
    if isinstance(value, list):
        return [text for inner in value for text in strings_in(inner)]
    if isinstance(value, str):
        return [value]
    assert value is None or isinstance(value, (bool, int, float)), f"not an aggregate: {type(value).__name__}"
    return []


def leaks(value, secrets: set[str]) -> list[str]:
    return sorted({secret for text in strings_in(value) for secret in secrets if secret in text})


def world_secrets(world: SimpleNamespace) -> set[str]:
    """Everything that could identify a note or a row, including the short forms of a fingerprint."""
    found = {SHIP_A, INV_A}
    for row in world.rows:
        found |= {row.row_id, row.shipment, row.invoice}
    for note in world.notes.values():
        found |= {note.text, note.note_id, note.fingerprint, note.fingerprint[:8], note.format_key}
    for entry in world.entries:
        found.add(entry["format_hash"])
    return found | set(world.evidence)


def test_the_leak_walker_finds_a_planted_value():
    assert leaks({"a": [{"b": "x R0001 y"}], "R0002": 1}, {"R0001", "R0002", "R0003"}) == ["R0001", "R0002"]
    with pytest.raises(AssertionError):
        strings_in({"amount": Decimal("1.00")})


def test_snapshot_holds_aggregates_only(world):
    """Spec: results contain only aggregates. Walks the result, the file, the history and the ledger."""
    snapshot = run_evaluate(world)
    secrets = world_secrets(world)
    assert len(secrets) > 20 and leaks(snapshot, secrets) == []
    keys = strings_in(snapshot)
    for forbidden in ("items_total", "evidence_text", "row_id", "fingerprint", "note_id", "shipment", "invoice", "note"):
        assert forbidden not in keys
    kpi_folder = world.root / "kpi"
    assert sorted(p.name for p in kpi_folder.iterdir()) == sorted(
        [kpi.snapshot_path(world.root, world.manifest.run_id, "d3").name, "snapshots.jsonl", "test_budget.jsonl"])
    for path in kpi_folder.iterdir():
        text = path.read_text(encoding="utf-8")
        assert [secret for secret in secrets if secret in text] == []


def test_snapshot_on_disk_is_the_result(world):
    snapshot = run_evaluate(world)
    path = kpi.snapshot_path(world.root, world.manifest.run_id, "d3")
    assert json.loads(path.read_text(encoding="utf-8")) == snapshot
    assert snapshot["run_id"] == world.manifest.run_id and snapshot["milestone"] == "d3" and snapshot["population"] == "TEST"


def test_evaluate_numbers_by_hand(world):
    snapshot = run_evaluate(world)
    coverage = snapshot["coverage"]
    assert (coverage["rows"]["covered"], coverage["rows"]["total"]) == (6, 7)
    assert coverage["usd"]["covered"] == "1220.00" and coverage["usd"]["total"] == "1260.00"
    assert coverage["without_repeats"]["usd"]["covered"] == "1135.00" and coverage["without_repeats"]["usd"]["total"] == "1175.00"
    assert snapshot["weights"]["shares"] == {"large": approx(1 / 7), "multi": approx(1 / 7), "single": approx(5 / 7)}
    assert snapshot["weights"]["basis"] == "predicted_item_count"
    accuracy = snapshot["accuracy"]
    assert accuracy["n"] == 4 and accuracy["test_notes"] == 5 and accuracy["weighted"] == approx(1.0)
    assert snapshot["invariants"]["violations"] == 0 and snapshot["invariants"]["items"] == 4
    # Rows 6/7 = 0.857: at least level 2's 0.85 and below level 3's 0.95.
    levels = snapshot["levels"]
    assert [levels[name]["status"] for name in ("level1", "level2", "level3")] == ["pass", "pass", "fail"]
    assert levels["level3"]["reason"] == "target_not_met"
    assert levels["level1"]["conditions"]["cov_rows"]["target"] == 0.25


def test_per_carrier_coverage_has_codes_and_counts(world):
    carriers = run_evaluate(world)["per_carrier"]
    assert sorted(carriers) == ["CARR1", "CARR2", "CARR3"]
    assert (carriers["CARR1"]["rows"]["covered"], carriers["CARR1"]["rows"]["total"]) == (3, 3)
    assert (carriers["CARR2"]["rows"]["covered"], carriers["CARR2"]["rows"]["total"]) == (2, 3)
    assert carriers["CARR2"]["usd"]["covered"] == "910.00" and carriers["CARR2"]["usd"]["total"] == "950.00"
    # CARR2 is below the overall rows and dollars. It is flagged, and the level above still passes.
    assert carriers["CARR2"]["below_overall_rows"] is True and carriers["CARR2"]["below_overall_usd"] is True
    assert carriers["CARR1"]["below_overall_rows"] is False


def test_every_level_is_labelled_provisional(world):
    """Spec: before the client's review, every Level result is labelled provisional."""
    snapshot = run_evaluate(world)
    assert snapshot["labels_status"] == "provisional"
    assert {level["labels_status"] for level in snapshot["levels"].values()} == {"provisional"}


def test_corrected_labels_rescore_for_free_and_status_changes(world):
    """Spec: the client changes labels, and the same run is evaluated again once TEST is sealed."""
    first = run_evaluate(world)
    corrected = dict(world.gold)
    label = corrected[world.single.fingerprint]
    moved = label.items[0].model_copy(update={"category": "detention"})
    corrected[world.single.fingerprint] = label.model_copy(update={"items": [moved]})
    second = run_evaluate(world, gold=corrected, labels_status="sealed")

    assert first["test_budget"]["event"] == "spent" and second["test_budget"]["event"] == "rescored"
    assert {level["labels_status"] for level in second["levels"].values()} == {"sealed"}
    assert first["labels_sha256"] != second["labels_sha256"]
    assert second["accuracy"]["correct"] == 3 and second["accuracy"]["errors"]["category_errors"] == 1
    events = [e["event"] for e in ledger_lines(world.root / "kpi" / "test_budget.jsonl")]
    assert events == ["spent", "rescored"]
    history = (world.root / "kpi" / "snapshots.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["labels_status"] for line in history] == ["provisional", "sealed"]


def test_second_run_is_refused_before_anything_is_written(world):
    """Spec: a different run at a milestone whose budget of 1 is spent."""
    run_evaluate(world)
    other = world.manifest.model_copy(update={"code_sha": "b" * 40})
    assert other.run_id != world.manifest.run_id
    with pytest.raises(ContractError, match="is spent"):
        run_evaluate(world, manifest=other)
    assert not kpi.snapshot_path(world.root, other.run_id, "d3").exists()
    last = ledger_lines(world.root / "kpi" / "test_budget.jsonl")[-1]
    assert last["event"] == "refused" and last["run_id"] == other.run_id
    assert len((world.root / "kpi" / "snapshots.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_recomputing_gives_the_same_numbers(world):
    first, second = run_evaluate(world), run_evaluate(world)
    first.pop("test_budget"), second.pop("test_budget")
    assert first == second


@pytest.mark.parametrize("update", [{"set_name": "train"}, {"limit": 30}, {"split_sha256": None}])
def test_a_run_not_on_all_dataset_rows_spends_no_budget(world, update):
    with pytest.raises(ContractError, match="all rows of the dataset file"):
        run_evaluate(world, manifest=world.manifest.model_copy(update=update))
    assert not (world.root / "kpi" / "test_budget.jsonl").exists()


def test_broken_invariant_fails_every_level_through_evaluate(world):
    """Spec: one accepted item's evidence is not verbatim."""
    result = world.results[world.single.fingerprint]
    tampered = result.items[0].model_copy(update={"evidence_text": "lumper fee 85"})
    results = {**world.results, world.single.fingerprint: result.model_copy(update={"items": [tampered]})}
    snapshot = run_evaluate(world, note_results=results)
    assert snapshot["invariants"]["by_code"] == {"evidence_not_verbatim": 1}
    assert snapshot["invariants"]["verifiability"] == approx(3 / 4)
    assert {(level["status"], level["reason"]) for level in snapshot["levels"].values()} == {("fail", "invariant_failed")}


def test_final_strata_come_from_the_gold_items(world):
    # Every entry says provisional `single`. The gold says otherwise, which is what a frozen TEST scores on.
    strata = run_evaluate(world)["accuracy"]["strata"]
    assert (strata["large"]["n"], strata["multi"]["n"], strata["single"]["n"]) == (1, 1, 2)
    assert strata["single"]["test_notes"] == 3  # the note in Review is held in TEST and is not scored


def test_note_whose_rows_are_all_in_review_is_not_covered(world):
    """Under `no_charge_stated_policy: review`, the note is `ok` but its rows are in Review."""
    rows = [r.model_copy(update={"outcome": "review"}) if r.fingerprint == world.nothing.fingerprint else r for r in world.rows]
    assert run_evaluate(world, row_results=rows)["accuracy"]["n"] == 3


def test_nothing_covered_does_not_crash_and_meets_nothing(world):
    rows = [r.model_copy(update={"outcome": "review", "items_total": None, "already_paid_total": None, "difference": None}) for r in world.rows]
    snapshot = run_evaluate(world, row_results=rows)
    assert snapshot["accuracy"]["weighted"] is None and snapshot["accuracy"]["n"] == 0
    assert snapshot["coverage"]["rows"]["share"] == 0.0
    assert snapshot["levels"]["level1"]["status"] == "fail" and snapshot["levels"]["level1"]["reason"] == "target_not_met"
    assert snapshot["levels"]["level1"]["conditions"]["acc"]["met"] is False


def test_the_match_tolerance_comes_from_the_settings(world):
    label = world.gold[world.single.fingerprint]
    close = label.items[0].model_copy(update={"amount": Decimal("85.03")})
    gold = {**world.gold, world.single.fingerprint: label.model_copy(update={"items": [close]})}
    assert run_evaluate(world, gold=gold)["accuracy"]["errors"]["amount_errors"] == 1
    loose = {**world.settings, "kpi": {**world.settings["kpi"], "amount_match_tolerance_usd": "0.05"}}
    assert run_evaluate(world, gold=gold, settings=loose)["accuracy"]["errors"]["amount_errors"] == 0


def test_test_note_with_no_label_stops_with_a_count_only(world):
    gold = dict(world.gold)
    del gold[world.single.fingerprint]
    with pytest.raises(ContractError, match="1 of 5 TEST notes") as caught:
        run_evaluate(world, gold=gold)
    assert not leaks({"message": str(caught.value)}, world_secrets(world))
    assert not (world.root / "kpi" / "test_budget.jsonl").exists()  # incomplete labels must not cost a run its budget


def test_entries_outside_test_are_refused(world):
    entries = [{**entry, "set": "VALIDATION"} for entry in world.entries]
    for bad in (entries, []):
        with pytest.raises(ContractError, match="scores TEST only"):
            run_evaluate(world, test_entries=bad)
    assert not (world.root / "kpi" / "test_budget.jsonl").exists()


def test_the_levels_come_from_config_run_yaml(world):
    levels = run_evaluate(world)["levels"]
    assert {name: {key: c["target"] for key, c in level["conditions"].items()} for name, level in levels.items()} == {
        "level1": LEVEL1, "level2": LEVEL2, "level3": LEVEL3}


@pytest.mark.parametrize("changes, message", [
    ({"labels_status": "final"}, "labels_status must be"),
    ({"milestone": "../d3"}, "a milestone is"),
    ({"settings": {"kpi": {}}}, "run settings need"),
])
def test_bad_arguments_stop_before_any_budget_is_spent(world, changes, message):
    with pytest.raises(ContractError, match=message):
        run_evaluate(world, **changes)
    assert not (world.root / "kpi" / "test_budget.jsonl").exists()


# ---- what a charge is tied to
def test_different_results_under_one_run_id_are_a_new_run(tmp_path):
    path = tmp_path / "budget.jsonl"
    kpi.spend_test_budget(path, "run_a", "d3", 1, "results_one")
    assert kpi.spend_test_budget(path, "run_a", "d3", 1, "results_one")["event"] == "rescored"
    with pytest.raises(ContractError, match="budget for milestone d3 is spent"):
        kpi.spend_test_budget(path, "run_a", "d3", 1, "results_two")


def test_an_extra_peek_is_counted_logged_with_its_reason_and_needs_a_reason(tmp_path):
    path = tmp_path / "budget.jsonl"
    kpi.spend_test_budget(path, "run_a", "d3", 1, "r")
    with pytest.raises(ContractError, match="--extra-peek"):
        kpi.spend_test_budget(path, "run_b", "d3", 1, "r")
    charge = kpi.spend_test_budget(path, "run_b", "d3", 1, "r", "client renamed a category")
    assert charge == {"event": "extra_spent", "budget": 1, "runs_spent": 2, "extra_peeks": 1}
    assert json.loads(path.read_text(encoding="utf-8").splitlines()[-1])["reason"] == "client renamed a category"
    assert kpi.spend_test_budget(path, "run_b", "d3", 1, "r") == {"event": "rescored", "budget": 1, "runs_spent": 2, "extra_peeks": 1}


def test_a_reason_is_not_used_while_budget_remains(tmp_path):
    assert kpi.spend_test_budget(tmp_path / "budget.jsonl", "run_a", "d3", 1, "r", "not needed")["event"] == "spent"


def test_the_results_digest_ignores_cost_latency_and_the_cache():
    base = NoteResult(fingerprint="f", note_id="n_f", status="ok", model="m", no_charge_stated=True)
    replay = base.model_copy(update={"cost_usd": Decimal("1.00"), "latency_ms": 9, "cached": True})
    other = base.model_copy(update={"reason_code": "amount_unclear"})
    assert kpi.results_digest({"f": base}) == kpi.results_digest({"f": replay}) != kpi.results_digest({"f": other})


def test_negative_rows_left_uncovered_are_reported():
    def row(disputed, outcome):
        return RowResult(row_id="R1", shipment="S", invoice="I", carrier="C", status="O", reason="X", disputed=Decimal(disputed), outcome=outcome,
                         outcome_reason="adds_up" if outcome == "verified" else "model_unsure")
    block = kpi.coverage([row("700", "verified"), row("300", "review"), row("-300", "review")])["usd"]
    assert block["negative_rows_not_covered"] == 1 and block["share"] == 1.0
