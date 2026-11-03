"""Tests per scenario for the one-page D1, D2 and D3 status. Every note is invented, and every model is a fake."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from test_bootstrap import fill_review
from test_pipeline import CODES, NOTE_WORDS, ROOT, d3, freeze  # noqa: F401 (d3 is a fixture)
from typer.testing import CliRunner

from itemizer import acceptance, pipeline
from itemizer.bootstrap import labels as lb
from itemizer.bootstrap import taxonomy as tx
from itemizer.bootstrap.data import ContractError
from itemizer.cli import app

runner = CliRunner()


def page(summary: dict) -> str:
    return Path(summary["page"]).read_text(encoding="utf-8")


def evidence(d3) -> Path:
    path = d3.tmp / "saved_email.txt"
    path.write_text("The client has seen the prototype.", encoding="utf-8")
    return path


def evaluated(d3) -> str:
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    pipeline.evaluate_run(d3.tmp, outcome.run_id)
    return outcome.run_id


# ---- every state
def test_nothing_labelled_yet_says_so_and_shows_no_accuracy(d3):
    summary = acceptance.d3_check(d3.tmp)
    assert summary["d2"]["status"] == "not_frozen" and summary["d2"]["labelled_notes"] == 0 and summary["d2"]["target_notes"] == 200
    assert summary["d3"]["status"] == "open" and summary["d3"]["reason"] == "no_run_on_all_rows"
    text = page(summary)
    assert "not_frozen" in text and "No accuracy is shown" in text
    assert "Accuracy on covered rows" not in text and "Level 1 result" not in text


def test_a_run_not_yet_scored_shows_no_accuracy(d3):
    freeze(d3)
    pipeline.run(d3.tmp)
    summary = acceptance.d3_check(d3.tmp)
    assert summary["d3"]["reason"] == "not_evaluated" and "No accuracy is shown" in page(summary)
    assert len(summary["largest_disputes"]) == 10


def test_d1_reports_draft_and_the_category_count(d3):
    d1 = acceptance.d3_check(d3.tmp)["d1"]
    assert d1["status"] == "draft" and d1["categories"] == 12


def test_d1_reports_approved_once_recorded(d3):
    tx.record_approval(d3.tmp / pipeline.CATEGORIES, d3.tmp / pipeline.APPROVAL, "client_owner", "2026-11-05", evidence(d3))
    assert acceptance.d3_check(d3.tmp)["d1"]["status"] == "approved"


# ---- labels still provisional
def test_provisional_labels_mark_every_level_result(d3):
    evaluated(d3)
    summary = acceptance.d3_check(d3.tmp)
    assert summary["d2"]["status"] == "provisional" and summary["d2"]["labelled_notes"] == 200
    assert summary["d2"]["agreement"]["notes_compared"] == 50
    assert summary["d3"]["labels_status"] == "provisional" and summary["d3"]["level1"]["labels_status"] == "provisional"
    text = page(summary)
    assert "These results are <b>provisional</b>" in text and "Level 1 result" in text


def test_each_level_1_condition_shows_its_value_interval_and_n(d3):
    evaluated(d3)
    summary = acceptance.d3_check(d3.tmp)
    text = page(summary)
    shown = "{:.1%}".format
    for key, name in (("cov_usd", "Coverage of disputed dollars"), ("cov_rows", "Coverage of rows"), ("acc", "Accuracy on covered rows")):
        condition = summary["d3"]["level1"]["conditions"][key]
        assert condition["n"] > 0 and condition["ci_low"] is not None
        assert (f"<tr><td>{name}</td><td>{shown(condition['value'])}</td><td>{shown(condition['target'])}</td><td>Yes</td>"
                f"<td>{shown(condition['ci_low'])} to {shown(condition['ci_high'])}</td><td>{condition['n']}</td></tr>") in text
    assert "<th>Range</th><th>n</th>" in text and "without repeated invoices" in text


# ---- the client's review
def test_level_met_with_no_review_stays_open(d3):
    evaluated(d3)
    d3_status = acceptance.d3_check(d3.tmp)["d3"]
    assert d3_status["level1"]["status"] == "pass"
    assert d3_status["status"] == "open" and d3_status["reason"] == "client_review_missing"


def test_a_review_on_provisional_labels_is_not_done_yet(d3):
    evaluated(d3)
    acceptance.record_review(d3.tmp, "2026-11-05", evidence(d3))
    d3_status = acceptance.d3_check(d3.tmp)["d3"]
    assert d3_status["status"] == "open" and d3_status["reason"] == "labels_provisional"
    assert d3_status["client_review"]["date"] == "2026-11-05"


def test_sealed_labels_and_a_recorded_review_close_d3(d3):
    run_id = evaluated(d3)
    assert lb.import_client_review(d3.ws, fill_review(d3), "client_owner", "2026-11-05", d3.notes, CODES)["errors"] == 0
    assert "sha256" in lb.seal(d3.ws, d3.ws.read_json("split_manifest.json"), d3.notes, CODES)
    pipeline.evaluate_run(d3.tmp, run_id)
    path = evidence(d3)
    acceptance.record_review(d3.tmp, "2026-11-05", path)
    summary = acceptance.d3_check(d3.tmp)
    assert summary["d3"]["status"] == "done" and summary["d3"]["reason"] is None and summary["d2"]["status"] == "sealed"
    assert "provisional" not in page(summary)


def test_the_review_records_the_date_and_the_evidence_hash(d3):
    path = evidence(d3)
    record = acceptance.record_review(d3.tmp, "2026-11-05", path)
    from itemizer.bootstrap.data import sha256_file

    assert record == {"date": "2026-11-05", "evidence_sha256": sha256_file(path)}


def test_a_review_needs_real_evidence_and_a_real_date(d3):
    with pytest.raises(ContractError, match="evidence file not found"):
        acceptance.record_review(d3.tmp, "2026-11-05", d3.tmp / "nothing.txt")
    with pytest.raises(ContractError, match="YYYY-MM-DD"):
        acceptance.record_review(d3.tmp, "next week", evidence(d3))


def test_a_level_not_met_keeps_d3_open_with_its_reason(d3):
    settings = yaml.safe_load((d3.tmp / pipeline.SETTINGS).read_text(encoding="utf-8"))
    settings["gates"]["level1"]["acc"] = 1.1  # no run can reach this
    (d3.tmp / pipeline.SETTINGS).write_text(yaml.safe_dump(settings), encoding="utf-8")
    evaluated(d3)
    d3_status = acceptance.d3_check(d3.tmp)["d3"]
    assert d3_status["status"] == "open" and d3_status["reason"] == "target_not_met"


# ---- largest disputes
def test_the_ten_largest_shipments_show_the_largest_dispute_and_the_total_side_by_side(d3):
    evaluated(d3)
    summary = acceptance.d3_check(d3.tmp)
    lines = summary["largest_disputes"]
    assert len(lines) == 10
    tops = [Decimal(line["largest_dispute"]) for line in lines]
    assert tops == sorted(tops, reverse=True)
    assert {"largest_dispute", "total_on_rows", "repeated_rows", "share_of_total"} <= set(lines[0])
    text = page(summary)
    assert "<th>Largest dispute</th><th>Total on rows</th>" in text


# ---- no note text, and the command
def test_the_page_and_its_data_hold_no_note_text(d3):
    evaluated(d3)
    summary = acceptance.d3_check(d3.tmp)
    written = page(summary) + (d3.tmp / "data" / "reports" / "d3_summary.json").read_text(encoding="utf-8")
    assert not any(word in written for word in NOTE_WORDS)


def test_the_summary_is_valid_json_and_the_page_needs_nothing_from_outside(d3):
    evaluated(d3)
    summary = acceptance.d3_check(d3.tmp)
    assert json.loads((d3.tmp / "data" / "reports" / "d3_summary.json").read_text(encoding="utf-8"))["d3"]["status"] == "open"
    assert not any(tag in page(summary) for tag in ("<script", "http://", "https://", "src="))


def test_the_commands_write_the_page_and_record_the_review(d3):
    result = runner.invoke(app, ["acceptance", "d3"])
    assert result.exit_code == 0, result.stderr
    assert "d3_summary.html" in result.stdout and (d3.tmp / "data" / "reports" / "d3_summary.html").exists()
    recorded = runner.invoke(app, ["acceptance", "record-review", "--date", "2026-11-05", "--evidence", str(evidence(d3))])
    assert recorded.exit_code == 0, recorded.stderr
    assert "evidence_sha256" in recorded.stdout


def test_a_development_run_is_not_a_d3_run(d3):
    outcome = pipeline.run(d3.tmp, set_name="train", limit=2)
    with pytest.raises(ContractError, match="all rows"):
        acceptance.d3_check(d3.tmp, outcome.run_id)


# ---- what we ask of the client
def test_the_requests_file_lists_status_only():
    requests = yaml.safe_load((ROOT / "deliverables/requests.yaml").read_text(encoding="utf-8"))["requests"]
    assert requests and all(set(entry) == {"item", "why", "owner", "asked", "status"} for entry in requests)


def test_a_seal_that_was_not_scored_again_keeps_d3_open(d3):
    run_id = evaluated(d3)
    acceptance.record_review(d3.tmp, "2026-11-05", evidence(d3))
    assert lb.import_client_review(d3.ws, fill_review(d3), "client_owner", "2026-11-05", d3.notes, CODES)["errors"] == 0
    assert "sha256" in lb.seal(d3.ws, d3.ws.read_json("split_manifest.json"), d3.notes, CODES)
    stale = acceptance.d3_check(d3.tmp)["d3"]
    assert (stale["status"], stale["reason"]) == ("open", "labels_provisional")  # the snapshot still holds the provisional score
    pipeline.evaluate_run(d3.tmp, run_id)
    assert acceptance.d3_check(d3.tmp)["d3"]["status"] == "done"


def test_a_shipment_holding_a_quarter_of_the_dollars_shows_both_figures_once(d3):
    freeze(d3)
    outcome = pipeline.run(d3.tmp)
    path = outcome.folder / "row_results.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row, amount in zip(rows[:4], ["8400.00", "8000.00", "8000.00", "8000.00"], strict=False):
        row.update(shipment="PPGTM.HUGE", disputed=amount)
    path.write_text(json.dumps(rows), encoding="utf-8")
    summary = acceptance.d3_check(d3.tmp)
    lines = summary["largest_disputes"]
    assert len(lines) == 10 and sum(line["shipment"] == "HUGE" for line in lines) == 1
    top = lines[0]
    assert (top["shipment"], top["rows"], top["largest_dispute"], top["total_on_rows"]) == ("HUGE", 4, "8400.00", "32400.00")
    text = page(summary)
    assert text.count("HUGE") == 1 and "<td>HUGE</td><td>4</td><td>$8,400.00</td><td>$32,400.00</td>" in text
