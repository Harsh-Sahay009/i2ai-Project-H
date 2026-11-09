"""Client-requested shipment grouping without invoice allocation."""
from copy import deepcopy

import pytest

from itemizer.bootstrap.data import fingerprint
from itemizer.shipment_review import build_review, load_source, write_review, main


def row(rid, bol="000123", note="STORAGE $300", invoice="I1"):
    return dict(row_id=rid, sap_bol=bol, note=note, invoice_bill_id=invoice,
                carrier_invoice=invoice, shipment="S1", disputed="300.00")


def predictions(note="STORAGE $300", items=None):
    return {fingerprint(note): dict(status="ok", note_id="n_test", items=items or [
        dict(item=1, category="ramp_storage", amount="300.00", line_type="charge",
             evidence_text=note)], no_charge_stated=False)}


def test_join_repetitions_collapse_without_losing_invoice_links():
    out = build_review([row("R1"), row("R2", invoice="I2")], predictions())
    assert len(out["groups"]) == len(out["charges"]) == 1
    assert out["groups"][0]["sap_bol"] == "000123"
    assert out["groups"][0]["source_row_ids"] == ["R1", "R2"]
    assert out["groups"][0]["invoice_bill_ids"] == ["I1", "I2"]
    assert out["charges"][0]["amount"] == "300.00"
    assert out["summary"]["repeated_join_rows"] == 1


def test_distinct_shipments_and_missing_bols_never_collapse():
    out = build_review([row("R1"), row("R2", "000124"), row("R3", None), row("R4", None)], predictions())
    assert len(out["groups"]) == 4
    assert out["summary"]["missing_bol_rows"] == 2
    assert "missing_sap_bol" in out["groups"][2]["flags"]


def test_paid_and_short_paid_items_are_context_without_expense_totals():
    items = [dict(item=1, category="short_paid", amount="8000.00", line_type="charge"),
             dict(item=2, category="tax", amount="400.00", line_type="already_paid")]
    out = build_review([row("R1")], predictions(items=items))
    assert out["charges"] == []
    assert len(out["balance_context"]) == 2


def test_overlay_is_scoped_and_does_not_mutate_saved_predictions():
    original = predictions()
    before = deepcopy(original)
    overlay = {"R1": dict(decision_file="case.json", expected_fingerprint=fingerprint("STORAGE $300"), expected_sap_bol="000123", items=[dict(
        item=1, category="tax", amount="400.00", line_type="charge")], flags=["human_reviewed"])}
    out = build_review([row("R1"), row("R2", "000124")], original, overlay)
    assert [i["amount"] for i in out["charges"]] == ["400.00", "300.00"]
    assert original == before
    assert out["charges"][0]["provenance"] == "human_overlay"


def test_conflicting_overlays_on_one_join_group_fail_closed():
    with pytest.raises(ValueError, match="overlay"):
        build_review([row("R1"), row("R2")], predictions(), {
            "R1": dict(decision_file="case.json", expected_fingerprint=fingerprint("STORAGE $300"), expected_sap_bol="000123", items=[]),
        })


def test_missing_predictions_are_review_records_not_silent_no_charge():
    out = build_review([row("R1")], {})
    assert "missing_prediction" in out["groups"][0]["flags"]
    assert out["groups"][0]["status"] == "review"


def test_multiple_distinct_items_with_same_amount_are_preserved():
    out = build_review([row("R1")], predictions(items=[
        dict(item=1, category="ramp_storage", amount="300.00", line_type="charge"),
        dict(item=2, category="driver_detention", amount="300.00", line_type="charge")]))
    assert len(out["charges"]) == 2


def test_same_category_across_descriptions_is_flagged_not_summed():
    a, b = "STORAGE $300", "STORAGE $225"
    pred = predictions(a) | predictions(b, [dict(item=1, category="ramp_storage", amount="225.00", line_type="charge")])
    out = build_review([row("R1", note=a), row("R2", note=b)], pred)
    assert len(out["charges"]) == 2
    assert all("possible_overlapping_descriptions" in g["flags"] for g in out["groups"])


def test_workbook_loader_uses_bol_not_shipment_or_invoice(tmp_path):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["SAP BOL", "Invoice/Bill ID", "Carrier Invoice", "SHIPMENT_GID", "Descritipion", "Delta"])
    ws.append(["000123", "order1", "inv1", "different_shipment", "STORAGE $300", 300])
    path = tmp_path / "source.xlsx"
    wb.save(path)
    rows = load_source(path)
    assert rows[0]["sap_bol"] == "000123"
    assert rows[0]["invoice_bill_id"] == "order1"
    assert rows[0]["row_id"] == "R0002"
    ws["A2"] = 123
    wb.save(path)
    with pytest.raises(ValueError, match="stored as text"):
        load_source(path)


def test_saved_report_roundtrips_complete_source_rows(tmp_path):
    import json
    report = build_review([row("R1"), row("R2")], predictions())
    write_review(tmp_path, report)
    assert json.loads((tmp_path / "shipment_review.json").read_text()) == report
    assert len((tmp_path / "source_rows.csv").read_text().splitlines()) == 3


def test_unknown_overlay_rows_rejected():
    with pytest.raises(ValueError, match="unknown rows"):
        build_review([row("R1")], predictions(), {"R2": {}})


@pytest.mark.parametrize("evidence", [None, "$75.00"])
def test_generic_balance_does_not_become_unmapped_expense(evidence):
    note = "BALANCE DUE $75.00"
    pred = predictions(note, [dict(item=1, category="other_unmapped", amount="75.00", line_type="charge", evidence_text=evidence)])
    out = build_review([row("R1", note=note)], pred)
    assert out["charges"] == []
    assert out["balance_context"][0]["amount"] == "75.00"
    assert "unmapped_balance_context" in out["groups"][0]["flags"]


def test_unrelated_unmapped_fee_is_not_swallowed_by_a_different_balance():
    note = "DOCUMENT FEE $10.00; BALANCE DUE $75.00"
    pred = predictions(note, [dict(item=1, category="other_unmapped", amount="10.00",
                                 line_type="charge", evidence_text="DOCUMENT FEE $10.00")])
    out = build_review([row("R1", note=note)], pred)
    assert len(out["charges"]) == 1
    assert out["balance_context"] == []


def test_stale_or_unbound_overlay_is_rejected():
    for decision in [dict(decision_file="case.json", items=[]),
                     dict(decision_file="case.json", items=[], expected_fingerprint=fingerprint("OTHER NOTE"), expected_sap_bol="000123"),
                     dict(decision_file="case.json", items=[], expected_fingerprint=fingerprint("STORAGE $300"), expected_sap_bol="000999")]:
        with pytest.raises(ValueError, match="overlay source"):
            build_review([row("R1")], predictions(), {"R1": decision})


def test_real_bol_cannot_collide_with_missing_bol_key():
    out = build_review([row("R1", None), row("R2", "missing:R1")], predictions())
    assert len(out["groups"]) == 2


def test_cli_rejects_overlay_from_different_source_file(tmp_path, monkeypatch):
    import json
    import sys
    source = tmp_path / "source.xlsx"
    source.write_text("changed source")
    overlay = tmp_path / "overlay.json"
    overlay.write_text(json.dumps(dict(dataset_sha256="wrong_hash", rows={})))
    monkeypatch.setattr(sys, "argv", ["shipment-review", "--source", str(source),
        "--predictions", str(tmp_path / "predictions.json"), "--overlay", str(overlay),
        "--output", str(tmp_path / "out")])
    with pytest.raises(ValueError, match="workbook hash"):
        main()
    assert not (tmp_path / "out").exists()
