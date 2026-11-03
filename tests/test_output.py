"""Tests per scenario for the workbook. Every note here is invented; no client data is used."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import zipfile
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest

from itemizer.bootstrap.data import ContractError, sha256_file
from itemizer.contracts import ChargeItem, NoteResult, RowResult
from itemizer.output import _EXCEL_CELL_LIMIT, largest_shipments, write_workbook

CATEGORIES = [
    {"code": "lumper", "name": "Lumper fee", "definition": "Paid to unload a truck."},
    {"code": "detention", "name": "Detention", "definition": "Time a truck waited."},
    {"code": "tax", "name": "Tax", "definition": "A tax on a charge."},
    {"code": "other_unmapped", "name": "Other or unmapped", "definition": "Fits no other category."},
]
RUN_INFO = {"run_id": "run_0123456789abcdef", "limit": 30, "code_dirty": False, "model": {"name": "fake", "max_tokens": 16000}}
REASONS = {"verified": "adds_up", "discrepancy": "does_not_add_up", "no_charge_stated": "no_charge_in_note",
           "review": "grammar_failed"}
ITEM_COLUMNS = ["row_id", "item", "category", "amount", "evidence", "outcome", "ai_reason"]
SUMMARY_COLUMNS = ["row_id", "shipment", "carrier_invoice", "carrier", "status", "reason_code", "disputed", "items_total",
                   "already_paid", "difference", "outcome", "outcome_reason", "repeated", "note"]
LARGEST_COLUMNS = ["rank", "shipment", "rows", "largest_dispute", "total_on_rows", "repeated_rows", "share_of_total",
                   "cumulative_share", "outcome", "main_category"]


def item(category="lumper", amount="85.00", evidence="LUMPER $85.00", number=1, line_type="charge", basis="named_in_note"):
    return ChargeItem(item=number, category=category, amount=Decimal(amount), evidence_text=evidence, evidence_start=0,
                      evidence_end=len(evidence), line_type=line_type, derivation="stated", basis=basis)


def answered(fp, *items):
    return NoteResult(fingerprint=fp, note_id=f"n_{fp}", items=list(items), status="ok", model="fake", attempts=1,
                      cost_usd=Decimal("0.01"), latency_ms=900)


def no_charge(fp):
    return NoteResult(fingerprint=fp, note_id=f"n_{fp}", no_charge_stated=True, status="ok", model="fake")


def in_review(fp, reason="grammar_failed"):
    return NoteResult(fingerprint=fp, note_id=f"n_{fp}", status="review", review_reason=reason, model="fake")


def row(row_id="R0002", shipment="PPGTM.S1", disputed="85.00", outcome="verified", fp=None, reason=None, items_total=None,
        difference=None, repeated=False, note="", **fields):
    return RowResult(row_id=row_id, shipment=shipment, invoice=fields.pop("invoice", "INV1"), carrier=fields.pop("carrier", "CARR1"),
                     status=fields.pop("status", "PPGTM.OPEN"), reason=fields.pop("code", "PPGTM.OTHER"), disputed=Decimal(disputed),
                     outcome=outcome, outcome_reason=reason or REASONS[outcome], note_id=f"n_{fp}" if fp else None, fingerprint=fp,
                     items_total=Decimal(items_total) if items_total else None, difference=Decimal(difference) if difference else None,
                     repeated=repeated, note=note, **fields)


def write(path, rows, notes=None, categories=CATEGORIES, run_info=RUN_INFO) -> Path:
    write_workbook(path, rows, notes or {}, categories, run_info)
    return path


def sheet_cells(path, name) -> list[dict]:
    """Each data line of a sheet, as its header name to its cell, read back from the file."""
    sheet = openpyxl.load_workbook(path)[name]
    header = [cell.value for cell in sheet[1]]
    return [dict(zip(header, line)) for line in sheet.iter_rows(min_row=2)]


def sheet_values(path, name) -> list[dict]:
    return [{key: cell.value for key, cell in line.items()} for line in sheet_cells(path, name)]


def all_cells(path):
    return [cell for sheet in openpyxl.load_workbook(path).worksheets for line in sheet.iter_rows() for cell in line]


def holds_a_formula(path) -> bool:
    with zipfile.ZipFile(path) as archive:
        sheets = [archive.read(name) for name in archive.namelist() if name.startswith("xl/worksheets/")]
    return any(re.search(rb"<(?:\w+:)?f[ >]", sheet) for sheet in sheets)


def a_run():
    """Every kind of row: verified, repeated, does not add up, Review, no charge stated and blank."""
    notes = {
        "a": answered("a", item()),
        "b": answered("b", item(evidence="LUMPER $28.40", amount="28.40")),
        "c": in_review("c", "refused"),
        "d": no_charge("d"),
    }
    rows = [
        row("R0002", "PPGTM.S1", "85.00", fp="a", items_total="85.00", difference="0.00", note="LUMPER $85.00"),
        row("R0003", "PPGTM.S1", "85.00", "discrepancy", fp="a", reason="repeated_invoice", items_total="85.00",
            difference="0.00", repeated=True, note="LUMPER $85.00"),
        row("R0004", "PPGTM.S2", "56.80", "discrepancy", fp="b", items_total="28.40", difference="28.40", note="LUMPER $28.40"),
        row("R0005", "PPGTM.S3", "12.00", "review", fp="c", reason="refused", note="NOT CLEAR"),
        row("R0006", "PPGTM.S4", "9.00", "no_charge_stated", fp="d", note="NO CHARGE HERE"),
        row("R0007", "PPGTM.S5", "15.00", "no_charge_stated", reason="empty_note"),
    ]
    return rows, notes


# ---- sheets
@pytest.mark.parametrize("name, columns", [
    ("Items", ITEM_COLUMNS),
    ("Row Summary", SUMMARY_COLUMNS),
    ("Largest", LARGEST_COLUMNS),
    ("Run Info", ["key", "value"]),
    ("Categories", ["code", "name", "definition"]),
])
def test_sheet_columns_are_the_designs(tmp_path, name, columns):
    rows, notes = a_run()
    sheet = openpyxl.load_workbook(write(tmp_path / "x.xlsx", rows, notes))[name]
    assert [cell.value for cell in sheet[1]] == columns


def test_five_sheets_in_order(tmp_path):
    rows, notes = a_run()
    workbook = openpyxl.load_workbook(write(tmp_path / "x.xlsx", rows, notes))
    assert workbook.sheetnames == ["Items", "Row Summary", "Largest", "Run Info", "Categories"]
    assert workbook.active.title == "Items"


def test_one_summary_line_per_row_and_one_item_line_per_charge_per_row(tmp_path):
    notes = {"a": answered("a", item(evidence="LUMPER $85.00"), item("detention", "40.00", "DET $40.00", number=2))}
    rows = [row("R0002", fp="a", disputed="125.00"), row("R0003", fp="a", disputed="125.00")]
    path = write(tmp_path / "x.xlsx", rows, notes)
    assert [line["row_id"] for line in sheet_values(path, "Row Summary")] == ["R0002", "R0003"]
    assert [(line["row_id"], line["item"], line["evidence"]) for line in sheet_values(path, "Items")] == [
        ("R0002", 1, "LUMPER $85.00"), ("R0002", 2, "DET $40.00"), ("R0003", 1, "LUMPER $85.00"), ("R0003", 2, "DET $40.00")]


@pytest.mark.parametrize("kept_row", ["R0006", "R0007", "R0005"], ids=["no_charge_note", "blank_note", "review"])
def test_row_with_no_charges_is_in_the_summary_and_not_in_items(tmp_path, kept_row):
    rows, notes = a_run()
    path = write(tmp_path / "x.xlsx", rows, notes)
    assert kept_row in [line["row_id"] for line in sheet_values(path, "Row Summary")]
    assert kept_row not in [line["row_id"] for line in sheet_values(path, "Items")]


def test_blank_note_is_an_empty_cell(tmp_path):
    rows, notes = a_run()
    blank = next(line for line in sheet_values(write(tmp_path / "x.xlsx", rows, notes), "Row Summary") if line["row_id"] == "R0007")
    assert blank["note"] is None and blank["outcome_reason"] == "empty_note"


def test_no_rows_still_writes_every_sheet(tmp_path):
    path = write(tmp_path / "x.xlsx", [])
    assert sheet_values(path, "Items") == [] and sheet_values(path, "Largest") == []
    assert len(sheet_values(path, "Categories")) == len(CATEGORIES)


# ---- simple ids
def test_several_rows_on_one_shipment_keep_their_ids_and_show_one_shipment(tmp_path):
    rows = [row(f"R{number:04d}", "PPGTM.S77") for number in range(2, 26)]
    lines = sheet_values(write(tmp_path / "x.xlsx", rows), "Row Summary")
    assert len(lines) == 24 and len({line["row_id"] for line in lines}) == 24
    assert {line["shipment"] for line in lines} == {"S77"}


def test_constant_prefix_is_dropped_only_where_it_starts(tmp_path):
    rows = [row(shipment="PPGTM.S1", status="PPGTM.OPEN", code="PPGTM.OTHER", invoice="PPGTM.INV", carrier="PPGTM.C"),
            row("R0003", shipment="X.PPGTM.S2", status="OPEN", code="OTHER")]
    path = write(tmp_path / "x.xlsx", rows)
    first, second = sheet_values(path, "Row Summary")
    assert (first["shipment"], first["status"], first["reason_code"]) == ("S1", "OPEN", "OTHER")
    assert (first["carrier_invoice"], first["carrier"]) == ("PPGTM.INV", "PPGTM.C")
    assert (second["shipment"], second["status"], second["reason_code"]) == ("X.PPGTM.S2", "OPEN", "OTHER")
    assert {line["shipment"] for line in sheet_values(path, "Largest")} == {"S1", "X.PPGTM.S2"}


# ---- items
def test_item_line_shows_the_amount_and_the_exact_words(tmp_path):
    line = sheet_values(write(tmp_path / "x.xlsx", [row(fp="a")], {"a": answered("a", item())}), "Items")[0]
    assert line == {"row_id": "R0002", "item": 1, "category": "Lumper fee", "amount": 85, "evidence": "LUMPER $85.00",
                    "outcome": "verified", "ai_reason": None}


@pytest.mark.parametrize("text", ["  LUMPER  $85.00\tNOW ", "LUMPER\n$85.00", "DÉTENTION $85.00 – 東京", 'A<B>&"C" $85.00'])
def test_evidence_and_note_keep_every_character(tmp_path, text):
    path = write(tmp_path / "x.xlsx", [row(fp="a", note=text)], {"a": answered("a", item(evidence=text))})
    assert sheet_values(path, "Items")[0]["evidence"] == text
    assert sheet_values(path, "Row Summary")[0]["note"] == text


@pytest.mark.parametrize("basis, sentence", [
    ("named_in_note", None),
    ("inferred_from_context", "Category taken from the rest of the note."),
    ("no_description", "The note gives no description of this amount."),
])
def test_ai_reason_is_a_fixed_sentence_from_basis(tmp_path, basis, sentence):
    path = write(tmp_path / "x.xlsx", [row(fp="a")], {"a": answered("a", item(basis=basis))})
    assert sheet_values(path, "Items")[0]["ai_reason"] == sentence


def test_already_paid_line_is_shown_with_its_amount_unchanged(tmp_path):
    notes = {"a": answered("a", item(evidence="BILLED $300.00", amount="300.00"),
                           item(evidence="PAID $100.00", amount="100.00", number=2, line_type="already_paid"))}
    path = write(tmp_path / "x.xlsx", [row(disputed="200.00", fp="a", items_total="300.00", already_paid_total="100.00", difference="0.00")], notes)
    assert [line["amount"] for line in sheet_values(path, "Items")] == [300, 100]
    assert [line["ai_reason"] for line in sheet_values(path, "Items")] == [None, "Already paid: subtracted from the items total."]
    summary = sheet_values(path, "Row Summary")[0]
    assert (summary["disputed"], summary["items_total"], summary["difference"], summary["outcome"]) == (200, 300, 0, "verified")
    assert summary["already_paid"] == 100


# ---- amounts
def test_every_amount_is_a_number_with_two_decimals(tmp_path):
    rows, notes = a_run()
    path = write(tmp_path / "x.xlsx", rows, notes)
    found = [line[column] for name, columns in (("Items", ["amount"]), ("Row Summary", ["disputed", "items_total", "difference"]),
                                                ("Largest", ["largest_dispute", "total_on_rows"]))
             for line in sheet_cells(path, name) for column in columns if line[column].value is not None]
    assert len(found) > 15
    assert all(cell.data_type == "n" and cell.number_format == "#,##0.00" for cell in found)


@pytest.mark.parametrize("amount", ["1277.68", "9999999.99", "0.07", "75.60", "8400.00"])
def test_amounts_read_back_exactly(tmp_path, amount):
    notes = {"a": answered("a", item(amount=amount, evidence=f"LUMPER ${amount}"))}
    path = write(tmp_path / "x.xlsx", [row(disputed=amount, fp="a", items_total=amount, difference="0.00")], notes)
    assert Decimal(str(sheet_values(path, "Items")[0]["amount"])) == Decimal(amount)
    line = sheet_values(path, "Row Summary")[0]
    assert Decimal(str(line["disputed"])) == Decimal(str(line["items_total"])) == Decimal(amount)


def test_totals_never_reached_are_empty_and_not_zero(tmp_path):
    rows, notes = a_run()
    review = next(line for line in sheet_values(write(tmp_path / "x.xlsx", rows, notes), "Row Summary") if line["row_id"] == "R0005")
    assert review["disputed"] == 12 and review["items_total"] is None and review["difference"] is None


def test_negative_dispute_is_a_negative_number(tmp_path):
    cell = sheet_cells(write(tmp_path / "x.xlsx", [row(disputed="-5.00")]), "Row Summary")[0]["disputed"]
    assert cell.value == -5 and cell.data_type == "n"


# ---- discrepancy and review visible
def test_only_discrepancy_and_review_rows_are_highlighted(tmp_path):
    rows, notes = a_run()
    fills = {}
    for line in sheet_cells(write(tmp_path / "x.xlsx", rows, notes), "Row Summary"):
        colours = {(cell.fill.fill_type, cell.fill.fgColor.rgb) for cell in line.values()}
        assert len(colours) == 1, "the whole row carries one fill, empty cells included"
        fills[line["row_id"].value] = colours.pop()
    assert fills["R0002"][0] is None and fills["R0006"][0] is None and fills["R0007"][0] is None
    assert fills["R0003"][0] == fills["R0004"][0] == fills["R0005"][0] == "solid"
    assert fills["R0003"] == fills["R0004"] != fills["R0005"]


def test_filtering_discrepancy_shows_disputed_items_total_difference_and_reason(tmp_path):
    rows, notes = a_run()
    path = write(tmp_path / "x.xlsx", rows, notes)
    assert openpyxl.load_workbook(path)["Row Summary"].auto_filter.ref == "A1:N7"
    found = [line for line in sheet_values(path, "Row Summary") if line["outcome"] == "discrepancy"]
    assert [(line["row_id"], line["outcome_reason"]) for line in found] == [("R0003", "repeated_invoice"), ("R0004", "does_not_add_up")]
    worst = found[1]
    assert (worst["disputed"], worst["items_total"], worst["difference"]) == (56.8, 28.4, 28.4)


def test_review_row_shows_its_reason(tmp_path):
    rows, notes = a_run()
    line = next(line for line in sheet_values(write(tmp_path / "x.xlsx", rows, notes), "Row Summary") if line["outcome"] == "review")
    assert line["outcome_reason"] == "refused"


# ---- formula safety
DANGEROUS = ["=SUM(A1:A9) LUMPER $5.00", "=1+1", "=HYPERLINK(\"http://fake.invalid\")", "+1 LUMPER $5.00", "-$5.00", "-85.00",
             "@SUM(A1) $5.00", "#N/A", "#REF!"]


@pytest.mark.parametrize("text", DANGEROUS + ["$85.00", "57.67"])
def test_a_note_or_evidence_is_stored_as_plain_text(tmp_path, text):
    path = write(tmp_path / "x.xlsx", [row(fp="a", note=text)], {"a": answered("a", item(evidence=text))})
    for cell in (sheet_cells(path, "Items")[0]["evidence"], sheet_cells(path, "Row Summary")[0]["note"]):
        assert cell.value == text, "the words are not changed, not even with an apostrophe"
        assert cell.data_type == "s" and cell.number_format == "@"
    assert not holds_a_formula(path)
    assert "t=\"inlineStr\"" in zipfile.ZipFile(path).read("xl/worksheets/sheet1.xml").decode()


def test_formula_check_finds_a_real_formula(tmp_path):
    workbook = openpyxl.Workbook()
    workbook.active["A1"] = "=1+1"
    workbook.save(tmp_path / "control.xlsx")
    assert holds_a_formula(tmp_path / "control.xlsx")


def test_no_text_anywhere_in_the_workbook_can_become_a_formula(tmp_path):
    categories = [{"code": "=code()", "name": "=NAME()", "definition": "-definition"}]
    notes = {"a": answered("a", item(category="=code()", evidence="=1+1"))}
    rows = [row("=R1", shipment="=S1", invoice="+INV", carrier="@CARR", status="=OPEN", code="-OTHER", fp="a", note="=2+2")]
    path = write(tmp_path / "x.xlsx", rows, notes, categories, {"=key": "=value", "model": {"name": "=fake"}})
    assert not holds_a_formula(path)
    cells = [cell for cell in all_cells(path) if cell.value is not None]
    assert all(cell.data_type != "f" for cell in cells)
    written = {cell.value for cell in cells}
    assert {"=R1", "=S1", "+INV", "@CARR", "=OPEN", "-OTHER", "=NAME()", "-definition", "=key", "=value"} <= written
    assert sheet_values(path, "Largest")[0]["main_category"] == "=NAME()"


@pytest.mark.parametrize("character, shown", [("\x0b", "_x000B_"), ("\x01", "_x0001_"), ("\ud800", "_xD800_"),
                                               ("￾", "_xFFFE_"), ("￿", "_xFFFF_")])
def test_text_xml_cannot_hold_is_escaped_with_nothing_lost(tmp_path, character, shown):
    text = f"LUMPER{character}$85.00"
    path = write(tmp_path / "x.xlsx", [row(fp="a", note=text)], {"a": answered("a", item(evidence=text))})
    assert sheet_values(path, "Items")[0]["evidence"] == f"LUMPER{shown}$85.00"
    assert sheet_values(path, "Row Summary")[0]["note"] == f"LUMPER{shown}$85.00"


def test_text_too_long_for_a_cell_stops_rather_than_being_cut(tmp_path):
    text = "SECRET-NOTE " * (_EXCEL_CELL_LIMIT // 12 + 1)
    with pytest.raises(ContractError, match="Row Summary cell N2 is longer than") as caught:
        write(tmp_path / "x.xlsx", [row(note=text)])
    assert "SECRET-NOTE" not in str(caught.value)
    assert not (tmp_path / "x.xlsx").exists()


def test_text_at_the_limit_is_whole(tmp_path):
    text = "A" * _EXCEL_CELL_LIMIT
    assert sheet_values(write(tmp_path / "x.xlsx", [row(note=text)]), "Row Summary")[0]["note"] == text


# ---- deterministic file
def test_same_inputs_after_a_real_clock_gap_give_the_same_hash(tmp_path):
    rows, notes = a_run()
    first = write(tmp_path / "first.xlsx", rows, notes)
    time.sleep(2.1)  # a zip's clock has two-second steps
    second = write(tmp_path / "second.xlsx", rows, notes)
    assert first.read_bytes() == second.read_bytes()


SEPARATE_PROCESS = """
import json, sys
from pathlib import Path
from itemizer.contracts import NoteResult, RowResult
from itemizer.output import write_workbook
given = json.loads(Path(sys.argv[1]).read_text())
write_workbook(Path(sys.argv[2]), [RowResult.model_validate(r) for r in given["rows"]],
               {k: NoteResult.model_validate(n) for k, n in given["notes"].items()}, given["categories"], given["run_info"])
"""


def test_same_hash_across_processes_hash_seeds_and_time_zones(tmp_path):
    rows, notes = a_run()
    given = tmp_path / "given.json"
    given.write_text(json.dumps({"rows": [r.model_dump(mode="json") for r in rows], "categories": CATEGORIES, "run_info": RUN_INFO,
                                 "notes": {k: n.model_dump(mode="json") for k, n in notes.items()}}))
    hashes = set()
    for seed, zone in (("1", "UTC"), ("2", "Asia/Tokyo")):
        out = tmp_path / f"{seed}.xlsx"
        subprocess.run([sys.executable, "-c", SEPARATE_PROCESS, str(given), str(out)], check=True,
                       env={"PYTHONHASHSEED": seed, "TZ": zone}, capture_output=True, timeout=120)
        hashes.add(sha256_file(out))
    assert hashes == {sha256_file(write(tmp_path / "here.xlsx", rows, notes))}


def test_zip_has_fixed_member_order_times_and_system(tmp_path):
    rows, notes = a_run()
    with zipfile.ZipFile(write(tmp_path / "x.xlsx", rows, notes)) as archive:
        members = archive.infolist()
        core = archive.read("docProps/core.xml").decode()
    names = [member.filename for member in members]
    assert names == sorted(names) and names[0] == "[Content_Types].xml"
    assert {member.date_time for member in members} == {(2000, 1, 1, 0, 0, 0)}
    assert {member.create_system for member in members} == {0}
    assert {member.compress_type for member in members} == {zipfile.ZIP_STORED}
    assert core.count("2000-01-01T00:00:00Z") == 2 and "itemizer" in core and "openpyxl" not in core


def test_properties_read_back_as_fixed(tmp_path):
    rows, notes = a_run()
    properties = openpyxl.load_workbook(write(tmp_path / "x.xlsx", rows, notes)).properties
    assert properties.creator == "itemizer" and properties.created.year == properties.modified.year == 2000


def test_rerun_from_cached_answers_gives_the_same_hash(tmp_path):
    rows, notes = a_run()
    cached = {fp: note.model_copy(update={"cached": True, "cost_usd": Decimal(0), "latency_ms": 0, "attempts": 0})
              for fp, note in notes.items()}
    assert sha256_file(write(tmp_path / "a.xlsx", rows, notes)) == sha256_file(write(tmp_path / "b.xlsx", rows, cached))


def test_order_of_note_results_and_run_info_keys_does_not_matter(tmp_path):
    rows, notes = a_run()
    turned_notes = dict(reversed(list(notes.items())))
    turned_info = dict(reversed(list(RUN_INFO.items())))
    turned_info["model"] = dict(reversed(list(RUN_INFO["model"].items())))
    assert sha256_file(write(tmp_path / "a.xlsx", rows, notes)) == sha256_file(write(tmp_path / "b.xlsx", rows, turned_notes, run_info=turned_info))


def test_a_changed_amount_changes_the_hash(tmp_path):
    rows, notes = a_run()
    changed = dict(notes, a=answered("a", item(amount="85.01", evidence="LUMPER $85.01")))
    assert sha256_file(write(tmp_path / "a.xlsx", rows, notes)) != sha256_file(write(tmp_path / "b.xlsx", rows, changed))


# ---- largest
def three_shipments():
    return [row("R0002", "PPGTM.MID", "300.00"), row("R0003", "PPGTM.BIG", "600.00"), row("R0004", "PPGTM.SMALL", "100.00")]


def largest(rows, notes=None):
    return largest_shipments(rows, notes or {}, CATEGORIES)


def test_ranked_by_largest_dispute_with_share_and_cumulative_share():
    lines = largest(three_shipments())
    assert [(line["rank"], line["shipment"], line["largest_dispute"]) for line in lines] == [
        (1, "BIG", Decimal("600.00")), (2, "MID", Decimal("300.00")), (3, "SMALL", Decimal("100.00"))]
    assert [line["share_of_total"] for line in lines] == pytest.approx([0.6, 0.3, 0.1])
    assert [line["cumulative_share"] for line in lines] == pytest.approx([0.6, 0.9, 1.0])
    assert lines[-1]["cumulative_share"] == 1.0


def test_cumulative_share_ends_at_exactly_one_when_shares_do_not_divide_evenly():
    lines = largest([row(f"R{n}", f"S{n}", "33.33") for n in range(7)])
    assert lines[-1]["cumulative_share"] == 1.0
    assert all(a["cumulative_share"] < b["cumulative_share"] for a, b in zip(lines, lines[1:]))


def test_ties_rank_by_shipment_whatever_the_input_order():
    rows = [row("R0002", "S2", "50.00"), row("R0003", "S1", "50.00")]
    assert [line["shipment"] for line in largest(rows)] == ["S1", "S2"]
    assert largest(rows) == largest(rows[::-1])


def test_six_rows_of_two_amounts_with_five_repeated_count_once():
    amounts = ["8400.00", "8400.00", "8400.00", "8000.00", "8000.00", "8000.00"]
    rows = [row(f"R{n:04d}", "PPGTM.HUGE", amount, repeated=n > 0) for n, amount in enumerate(amounts)]
    lines = largest(rows + [row("R0100", "PPGTM.OTHER", "1600.00")])
    huge = lines[0]
    assert len(lines) == 2 and sum(line["shipment"] == "HUGE" for line in lines) == 1
    assert huge["rows"] == 6 and huge["repeated_rows"] == 5
    assert huge["largest_dispute"] == Decimal("8400.00") and huge["total_on_rows"] == Decimal("49200.00")
    assert huge["share_of_total"] == pytest.approx(8400 / 10000), "the largest dispute counted once, not the rows' total"
    assert lines[1]["share_of_total"] == pytest.approx(1600 / 10000)


@pytest.mark.parametrize("outcomes, worst", [
    (["verified", "discrepancy", "review"], "review"),
    (["review", "verified"], "review"),
    (["verified", "no_charge_stated", "discrepancy"], "discrepancy"),
    (["discrepancy", "verified"], "discrepancy"),
    (["verified", "no_charge_stated"], "no_charge_stated"),
    (["verified", "verified"], "verified"),
])
def test_outcome_is_the_worst_across_rows(outcomes, worst):
    rows = [row(f"R{n}", "S1", "10.00", outcome) for n, outcome in enumerate(outcomes)]
    assert largest(rows)[0]["outcome"] == worst


def test_main_category_is_the_largest_charge_in_the_largest_row():
    notes = {"small": answered("small", item("detention", "900.00", "DET $900.00")),
             "big": answered("big", item("lumper", "10.00", "LUMPER $10.00"), item("tax", "20.00", "TAX $20.00", number=2),
                             item("detention", "970.00", "DET $970.00", number=3))}
    rows = [row("R0002", "S1", "900.00", fp="small"), row("R0003", "S1", "1000.00", fp="big")]
    assert largest(rows, notes)[0]["main_category"] == "Detention"
    notes["big"] = answered("big", item("lumper", "970.00", "LUMPER $970.00"), item("detention", "30.00", "DET $30.00", number=2))
    assert largest(rows, notes)[0]["main_category"] == "Lumper fee", "the other row's 900.00 charge does not count"


def test_main_category_ignores_an_amount_already_paid():
    notes = {"a": answered("a", item("lumper", "300.00", "BILLED $300.00"),
                           item("detention", "900.00", "PAID $900.00", number=2, line_type="already_paid"))}
    assert largest([row(disputed="300.00", fp="a")], notes)[0]["main_category"] == "Lumper fee"


def test_main_category_is_tax_when_the_row_holds_only_tax():
    notes = {"a": answered("a", item("tax", "3.60", "GST $3.60", line_type="tax"))}
    assert largest([row(disputed="3.60", fp="a")], notes)[0]["main_category"] == "Tax"


def test_main_category_on_tied_rows_comes_from_the_first_with_charges_whatever_the_order():
    notes = {"a": answered("a", item("lumper")), "b": answered("b", item("detention", "85.00", "DET $85.00")),
             "c": in_review("c")}
    rows = [row("R0003", "S1", "85.00", fp="a"), row("R0002", "S1", "85.00", "review", fp="c"), row("R0004", "S1", "85.00", fp="b")]
    assert largest(rows, notes)[0]["main_category"] == "Lumper fee"
    assert largest(rows[::-1], notes)[0]["main_category"] == "Lumper fee"


@pytest.mark.parametrize("build, note_results", [
    (lambda: row(disputed="100.00", outcome="review", fp="c"), {"c": in_review("c")}),
    (lambda: row(disputed="100.00", outcome="no_charge_stated", reason="empty_note"), {}),
], ids=["review", "blank"])
def test_main_category_is_empty_when_the_largest_row_has_no_charges(build, note_results):
    assert largest([build()], note_results)[0]["main_category"] is None


def test_main_category_never_comes_from_a_smaller_row():
    notes = {"a": answered("a", item())}
    rows = [row("R0002", "S1", "85.00", fp="a"), row("R0003", "S1", "100.00", "no_charge_stated", reason="empty_note")]
    assert largest(rows, notes)[0]["main_category"] is None


@pytest.mark.parametrize("amount", ["0.00", "-5.00"])
def test_shipments_whose_largest_dispute_is_zero_or_less_are_left_out(amount):
    rows = [row("R0002", "KEPT", "100.00"), row("R0003", "GONE", amount), row("R0004", "GONE", "-1.00")]
    lines = largest(rows)
    assert [line["shipment"] for line in lines] == ["KEPT"]
    assert lines[0]["share_of_total"] == 1.0, "what is left out does not count in the total"


def test_a_shipment_with_a_negative_row_stays_when_its_largest_is_positive():
    line = largest([row("R0002", "S1", "100.00"), row("R0003", "S1", "-30.00")])[0]
    assert line["largest_dispute"] == Decimal("100.00") and line["total_on_rows"] == Decimal("70.00")


def test_nothing_positive_gives_no_lines():
    assert largest([row(disputed="0.00"), row("R0003", "S2", "-1.00")]) == []
    assert largest([]) == []


def test_largest_holds_no_note_text():
    rows, notes = a_run()
    assert "LUMPER" not in json.dumps(largest(rows, notes), default=str)


def test_largest_sheet_matches_the_view_and_formats_its_numbers(tmp_path):
    rows, notes = a_run()
    path = write(tmp_path / "x.xlsx", rows, notes)
    view = largest(rows, notes)
    cells = sheet_cells(path, "Largest")
    assert [line["shipment"].value for line in cells] == [line["shipment"] for line in view] == ["S1", "S2", "S5", "S3", "S4"]
    assert [line["rank"].value for line in cells] == [1, 2, 3, 4, 5]
    first = cells[0]
    assert first["largest_dispute"].number_format == "#,##0.00" and first["share_of_total"].number_format == "0.0%"
    assert first["cumulative_share"].data_type == "n" and first["share_of_total"].value == pytest.approx(view[0]["share_of_total"])
    assert first["outcome"].value == "discrepancy" and first["main_category"].value == "Lumper fee"
    assert first["rows"].value == 2 and first["repeated_rows"].value == 1 and first["total_on_rows"].value == 170


# ---- run info and categories
def test_run_info_holds_key_and_value_lines(tmp_path):
    info = {"run_id": "run_1", "limit": None, "code_dirty": True, "rows": 12, "model": {"b": 1, "a": 2}, "folder": Path("data/runs/x")}
    lines = {line["key"]: line["value"] for line in sheet_values(write(tmp_path / "x.xlsx", [], run_info=info), "Run Info")}
    assert lines == {"run_id": "run_1", "limit": None, "code_dirty": True, "rows": 12, "model": '{"a": 2, "b": 1}', "folder": "data/runs/x"}


def test_categories_sheet_lists_code_name_and_definition(tmp_path):
    lines = sheet_values(write(tmp_path / "x.xlsx", []), "Categories")
    assert lines == CATEGORIES


# ---- errors a user can hit
def test_row_with_no_note_result_stops_and_names_the_row(tmp_path):
    with pytest.raises(ContractError, match="row R0002 points to a note that has no result"):
        write(tmp_path / "x.xlsx", [row(fp="missing", note="SECRET-NOTE")])
    assert not (tmp_path / "x.xlsx").exists()


def test_category_outside_the_list_stops_with_no_text_from_the_item(tmp_path):
    notes = {"a": answered("a", item(category="retired_code", evidence="SECRET-NOTE $85.00"))}
    with pytest.raises(ContractError, match="row R0002 holds a category that is not in the category list") as caught:
        write(tmp_path / "x.xlsx", [row(fp="a")], notes)
    assert "SECRET-NOTE" not in str(caught.value) and "retired_code" not in str(caught.value)


def test_a_folder_that_cannot_be_written_is_a_plain_error(tmp_path):
    (tmp_path / "taken").write_text("a file, not a folder")
    with pytest.raises(ContractError, match="could not write the workbook"):
        write(tmp_path / "taken" / "x.xlsx", [])


def test_missing_folder_is_created(tmp_path):
    assert write(tmp_path / "runs" / "run_1" / "itemized.xlsx", []).exists()
