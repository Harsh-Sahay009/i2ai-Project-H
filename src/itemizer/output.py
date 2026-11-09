"""The workbook an accountant reads. It shows what a run found and changes nothing.

It has one line per charge per SAP BOL and description (ADR 0017): rows the export repeats collapse into one line, which
lists them, and nothing is allocated across shipments.

Two rules hold for every cell. An amount is a number, written as it was computed. Text is stored as text in Excel's
Text format, so a note such as "=1+1" or "-$5.00" can never become a formula, even after someone edits the cell.
"""
from __future__ import annotations

import collections
import datetime as dt
import io
import json
import re
import zipfile
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.cell.cell import Cell
from openpyxl.packaging.core import DocumentProperties
from openpyxl.styles import Alignment, PatternFill
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.writer.excel import ExcelWriter

from .bootstrap.data import ContractError
from .bootstrap.labels import _style
from .contracts import ChargeItem, NoteResult, RowResult

_CONSTANT_PREFIX = "PPGTM."
_MONEY = "#,##0.00"
_SHARE = "0.0%"
_TEXT = "@"
_EXCEL_CELL_LIMIT = 32767
# What XML cannot hold. openpyxl's own error for these quotes the whole text, so they never reach it.
_UNWRITABLE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_FIXED_TIME = dt.datetime(2000, 1, 1)

AI_REASONS = {
    "named_in_note": None,
    "inferred_from_context": "Category taken from the rest of the note.",
    "no_description": "The note gives no description of this amount.",
}
ALREADY_PAID_REASON = "Already paid: subtracted from the items total."
_HIGHLIGHTS = {
    "discrepancy": PatternFill("solid", fgColor="FFF2CC"),
    "review": PatternFill("solid", fgColor="F8CBAD"),
}
_WORST_FIRST = ("review", "discrepancy", "no_charge_stated", "verified")

# Each sheet's columns, in order, with the number format of its numeric columns.
_ITEMS = {"charge_id": None, "sap_bol": None, "shipment": None, "item": None, "category": None, "amount": _MONEY,
          "evidence": None, "outcome": None, "ai_reason": None, "description": None}
_CHARGE_SUMMARY = {"charge_id": None, "sap_bol": None, "shipment": None, "bill_ids": None, "carrier_invoice": None,
                   "carrier": None, "status": None, "reason_code": None, "disputed": _MONEY, "items_total": _MONEY,
                   "already_paid": _MONEY, "difference": _MONEY, "outcome": None, "outcome_reason": None, "rows": None,
                   "row_ids": None, "same_amount_as": None, "description": None}
_LARGEST = {"rank": None, "sap_bol": None, "shipment": None, "charges": None, "rows": None, "largest_dispute": _MONEY,
            "total_of_charges": _MONEY, "share_of_total": _SHARE, "cumulative_share": _SHARE, "outcome": None,
            "main_category": None}
_RUN_INFO = {"key": None, "value": None}
_CATEGORIES = {"code": None, "name": None, "definition": None}
_SHIPMENT_KEY = "shipment "  # a line's group when its SAP BOL is blank


def _simple_id(value: str) -> str:
    return value.removeprefix(_CONSTANT_PREFIX)


def _names(categories: list[dict]) -> dict[str, str]:
    return {category["code"]: category["name"] for category in categories}


def _row_items(row: RowResult, note_results: dict[str, NoteResult]) -> list[ChargeItem]:
    if row.fingerprint is None:  # a blank note has no result
        return []
    note = note_results.get(row.fingerprint)
    if note is None:
        raise ContractError(f"row {row.row_id} points to a note that has no result")
    return note.items


def _category_name(item: ChargeItem, row: RowResult, names: dict[str, str]) -> str:
    if item.category not in names:
        raise ContractError(f"row {row.row_id} holds a category that is not in the category list")
    return names[item.category]


def _group(row: RowResult) -> str:
    """The SAP BOL a row belongs to, or its shipment when the SAP BOL is blank (ADR 0017)."""
    return row.sap_bol or _SHIPMENT_KEY + row.shipment


def _distinct(values: Iterable[str]) -> str:
    """Distinct non-empty values in first-seen order, so a line never hides a value its rows disagree on."""
    return ", ".join(dict.fromkeys(value for value in values if value))


def _line_outcome(row: RowResult) -> tuple[str, str]:
    """A line is its rows with the repeats collapsed, so the repeat flag does not apply to it. A row is flagged
    `repeated_invoice` only after it adds up, so without the flag it is verified."""
    if row.outcome_reason == "repeated_invoice":
        return "verified", "adds_up"
    return row.outcome, row.outcome_reason


def charge_lines(row_results: list[RowResult]) -> list[dict]:
    """One line per SAP BOL and description, in the order of each line's first row (ADR 0017).

    Rows with the same SAP BOL and note but another disputed amount are not repeats of one charge, so the amount is part
    of the key. Each line keeps its rows, and names the other lines on its SAP BOL with the same billed and disputed
    amounts, which may be one charge described twice.
    """
    grouped: dict[tuple, list[RowResult]] = {}
    for row in row_results:
        grouped.setdefault((_group(row), row.fingerprint or "", row.disputed), []).append(row)
    lines = []
    for number, rows in enumerate(grouped.values(), start=1):
        outcome, reason = _line_outcome(rows[0])
        lines.append({"charge_id": f"C{number:04d}", "group": _group(rows[0]), "rows": rows, "row": rows[0],
                      "outcome": outcome, "outcome_reason": reason, "same_amount_as": []})
    same: dict[tuple, list[dict]] = collections.defaultdict(list)
    for line in lines:
        row = line["row"]
        if row.fingerprint is not None and row.billed is not None:  # runs from before ADR 0017 have no billed amount
            same[(line["group"], row.billed, row.disputed)].append(line)
    for matching in same.values():
        for line in matching:
            line["same_amount_as"] = [other["charge_id"] for other in matching if other is not line]
    return lines


def _main_category(top_lines: list[dict], note_results: dict[str, NoteResult], names: dict[str, str]) -> str | None:
    """The largest charge in the largest line. Lines can tie, so the first by row id that has charges decides."""
    for line in sorted(top_lines, key=lambda line: min(row.row_id for row in line["rows"])):
        charges = [item for item in _row_items(line["row"], note_results) if item.line_type != "already_paid"]
        if charges:
            return _category_name(max(charges, key=lambda item: item.amount), line["row"], names)
    return None


def largest_by_sap_bol(row_results: list[RowResult], note_results: dict[str, NoteResult],
                       categories: list[dict]) -> list[dict]:
    """One line per SAP BOL, largest dispute first, keyed by the `Largest` column names. It holds no note text.

    Two lines on one SAP BOL can be one dispute described twice, so the share uses each SAP BOL's largest dispute,
    counted once, and the total of its distinct charges is shown beside it.
    """
    names = _names(categories)
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    for line in charge_lines(row_results):
        groups[line["group"]].append(line)
    largest = {group: max(line["row"].disputed for line in lines) for group, lines in groups.items()}
    kept = sorted((group for group, top in largest.items() if top > 0), key=lambda g: (-largest[g], g))
    total = sum((largest[group] for group in kept), Decimal(0))
    result = []
    running = Decimal(0)
    for rank, group in enumerate(kept, start=1):
        lines, top = groups[group], largest[group]
        running += top
        result.append({
            "rank": rank,
            "sap_bol": lines[0]["row"].sap_bol,
            "shipment": _distinct(_simple_id(line["row"].shipment) for line in lines),
            "charges": len(lines),
            "rows": sum(len(line["rows"]) for line in lines),
            "largest_dispute": top,
            "total_of_charges": sum((line["row"].disputed for line in lines), Decimal(0)),
            "share_of_total": float(top / total),
            "cumulative_share": float(running / total),  # from exact sums, so the last line is exactly 1
            "outcome": min((line["outcome"] for line in lines), key=_WORST_FIRST.index),
            "main_category": _main_category([line for line in lines if line["row"].disputed == top], note_results, names),
        })
    return result


def _put(cell: Cell, value: Any, number_format: str | None) -> None:
    if value is None or value == "":
        return
    if not isinstance(value, str):
        cell.value = value
        if number_format:
            cell.number_format = number_format
        return
    text = _UNWRITABLE.sub(lambda found: f"_x{ord(found[0]):04X}_", value)  # Excel's own escape, so nothing is lost
    if len(text) > _EXCEL_CELL_LIMIT:  # openpyxl would cut it silently, and evidence must stay whole
        raise ContractError(f"{cell.parent.title} cell {cell.coordinate} is longer than Excel's limit of "
                            f"{_EXCEL_CELL_LIMIT} characters, so it cannot be shown whole")
    cell.value = text
    cell.data_type = "s"  # assigning the value made "=..." a formula and "#N/A" an error
    cell.number_format = _TEXT


def _table(sheet: Worksheet, columns: dict[str, str | None], lines: Iterable[list]) -> None:
    formats = list(columns.values())
    sheet.append(list(columns))
    for row_no, line in enumerate(lines, start=2):
        for column_no, (value, number_format) in enumerate(zip(line, formats, strict=True), start=1):
            _put(sheet.cell(row=row_no, column=column_no), value, number_format)


def _wrap(sheet: Worksheet, column: str) -> None:
    for cell in sheet[column][1:]:
        cell.alignment = Alignment(wrap_text=True, vertical="top")


def _filterable(sheet: Worksheet, widths: dict[str, int]) -> None:
    _style(sheet, widths)
    sheet.auto_filter.ref = sheet.dimensions


def _info_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, default=str)
    return value if value is None or isinstance(value, (str, int, float, Decimal)) else str(value)


def _fixed_bytes(workbook: openpyxl.Workbook) -> bytes:
    """The file with no trace of when or where it was written.

    `Workbook.save` stamps the clock into the properties, so ExcelWriter is called directly. A zip records each member's
    time and system. Members are stored, not deflated, because deflated bytes depend on the machine's zlib build.
    """
    workbook.properties = DocumentProperties(creator="itemizer", created=_FIXED_TIME, modified=_FIXED_TIME)
    saved = io.BytesIO()
    ExcelWriter(workbook, zipfile.ZipFile(saved, "w")).save()
    fixed = io.BytesIO()
    with zipfile.ZipFile(saved) as source, zipfile.ZipFile(fixed, "w") as target:
        for name in sorted(source.namelist()):
            member = zipfile.ZipInfo(name, date_time=_FIXED_TIME.timetuple()[:6])
            member.create_system = 0
            target.writestr(member, source.read(name))
    return fixed.getvalue()


def write_workbook(path: Path, row_results: list[RowResult], note_results: dict[str, NoteResult],
                   categories: list[dict], run_info: dict[str, Any]) -> None:
    """Identical inputs give identical bytes.

    So `run_info` must hold only what a rerun repeats: a clock, a cost or a count of cached answers would change the file.
    """
    names = _names(categories)
    workbook = openpyxl.Workbook()

    lines = charge_lines(row_results)
    items = workbook.active
    items.title = "Items"
    _table(items, _ITEMS, [
        [line["charge_id"], line["row"].sap_bol, _simple_id(line["row"].shipment), item.item,
         _category_name(item, line["row"], names), item.amount, item.evidence_text, line["outcome"],
         ALREADY_PAID_REASON if item.line_type == "already_paid" else AI_REASONS[item.basis], line["row"].note]
        for line in lines for item in _row_items(line["row"], note_results)])
    _wrap(items, "G")
    _filterable(items, {"A": 9, "B": 20, "C": 16, "D": 6, "E": 28, "F": 12, "G": 50, "H": 16, "I": 42, "J": 50})

    summary = workbook.create_sheet("Charge Summary")
    _table(summary, _CHARGE_SUMMARY, [
        [line["charge_id"], line["row"].sap_bol, _distinct(_simple_id(r.shipment) for r in line["rows"]),
         _distinct(r.bill_id for r in line["rows"]), _distinct(r.invoice for r in line["rows"]),
         _distinct(r.carrier for r in line["rows"]), _distinct(_simple_id(r.status) for r in line["rows"]),
         _distinct(_simple_id(r.reason) for r in line["rows"]), line["row"].disputed, line["row"].items_total,
         line["row"].already_paid_total, line["row"].difference, line["outcome"], line["outcome_reason"],
         len(line["rows"]), ", ".join(r.row_id for r in line["rows"]), ", ".join(line["same_amount_as"]),
         line["row"].note]
        for line in lines])
    for line, cells in zip(lines, summary.iter_rows(min_row=2), strict=True):
        if line["outcome"] in _HIGHLIGHTS:
            for cell in cells:
                cell.fill = _HIGHLIGHTS[line["outcome"]]
    _wrap(summary, "R")
    _filterable(summary, {"A": 9, "B": 20, "C": 16, "D": 18, "E": 16, "F": 10, "G": 12, "H": 12, "I": 12, "J": 12, "K": 12,
                          "L": 12, "M": 16, "N": 20, "O": 6, "P": 20, "Q": 14, "R": 60})

    largest = workbook.create_sheet("Largest")
    _table(largest, _LARGEST, [[line[column] for column in _LARGEST]
                               for line in largest_by_sap_bol(row_results, note_results, categories)])
    _filterable(largest, {"A": 6, "B": 20, "C": 16, "D": 8, "E": 6, "F": 15, "G": 15, "H": 14, "I": 16, "J": 16, "K": 28})

    info = workbook.create_sheet("Run Info")
    _table(info, _RUN_INFO, [[key, _info_value(run_info[key])] for key in sorted(run_info)])
    _style(info, {"A": 22, "B": 90})

    listed = workbook.create_sheet("Categories")
    _table(listed, _CATEGORIES, [[c["code"], c["name"], c["definition"]] for c in categories])
    _style(listed, {"A": 26, "B": 30, "C": 90})

    data = _fixed_bytes(workbook)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    except OSError:
        raise ContractError(f"could not write the workbook to {path}; close it if it is open, and check the folder") from None
