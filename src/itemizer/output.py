"""The workbook an accountant reads. It shows what a run found and changes nothing.

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
_ITEMS = {"row_id": None, "item": None, "category": None, "amount": _MONEY, "evidence": None, "outcome": None,
          "ai_reason": None}
_ROW_SUMMARY = {"row_id": None, "shipment": None, "carrier_invoice": None, "carrier": None, "status": None,
                "reason_code": None, "disputed": _MONEY, "items_total": _MONEY, "already_paid": _MONEY, "difference": _MONEY, "outcome": None,
                "outcome_reason": None, "repeated": None, "note": None}
_LARGEST = {"rank": None, "shipment": None, "rows": None, "largest_dispute": _MONEY, "total_on_rows": _MONEY,
            "repeated_rows": None, "share_of_total": _SHARE, "cumulative_share": _SHARE, "outcome": None,
            "main_category": None}
_RUN_INFO = {"key": None, "value": None}
_CATEGORIES = {"code": None, "name": None, "definition": None}


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


def _main_category(top_rows: list[RowResult], note_results: dict[str, NoteResult], names: dict[str, str]) -> str | None:
    """The largest charge in the largest row. Rows can tie, so the first by row_id that has charges decides."""
    for row in sorted(top_rows, key=lambda r: r.row_id):
        charges = [item for item in _row_items(row, note_results) if item.line_type != "already_paid"]
        if charges:
            return _category_name(max(charges, key=lambda item: item.amount), row, names)
    return None


def largest_shipments(row_results: list[RowResult], note_results: dict[str, NoteResult],
                      categories: list[dict]) -> list[dict]:
    """One line per shipment, largest dispute first, keyed by the `Largest` column names. It holds no note text.

    A repeated dispute is one dispute, so shares use each shipment's largest dispute, counted once.
    """
    names = _names(categories)
    shipments: dict[str, list[RowResult]] = collections.defaultdict(list)
    for row in row_results:
        shipments[row.shipment].append(row)
    largest = {shipment: max(row.disputed for row in rows) for shipment, rows in shipments.items()}
    kept = sorted((shipment for shipment, top in largest.items() if top > 0), key=lambda s: (-largest[s], s))
    total = sum((largest[shipment] for shipment in kept), Decimal(0))
    lines = []
    running = Decimal(0)
    for rank, shipment in enumerate(kept, start=1):
        rows, top = shipments[shipment], largest[shipment]
        running += top
        lines.append({
            "rank": rank,
            "shipment": _simple_id(shipment),
            "rows": len(rows),
            "largest_dispute": top,
            "total_on_rows": sum((row.disputed for row in rows), Decimal(0)),
            "repeated_rows": sum(row.repeated for row in rows),
            "share_of_total": float(top / total),
            "cumulative_share": float(running / total),  # from exact sums, so the last line is exactly 1
            "outcome": min((row.outcome for row in rows), key=_WORST_FIRST.index),
            "main_category": _main_category([row for row in rows if row.disputed == top], note_results, names),
        })
    return lines


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

    items = workbook.active
    items.title = "Items"
    _table(items, _ITEMS, [
        [row.row_id, item.item, _category_name(item, row, names), item.amount, item.evidence_text, row.outcome,
         ALREADY_PAID_REASON if item.line_type == "already_paid" else AI_REASONS[item.basis]]
        for row in row_results for item in _row_items(row, note_results)])
    _wrap(items, "E")
    _filterable(items, {"A": 9, "B": 6, "C": 28, "D": 12, "E": 50, "F": 16, "G": 42})

    summary = workbook.create_sheet("Row Summary")
    _table(summary, _ROW_SUMMARY, [
        [row.row_id, _simple_id(row.shipment), row.invoice, row.carrier, _simple_id(row.status), _simple_id(row.reason),
         row.disputed, row.items_total, row.already_paid_total, row.difference, row.outcome, row.outcome_reason,
         row.repeated, row.note]
        for row in row_results])
    for row, cells in zip(row_results, summary.iter_rows(min_row=2), strict=True):
        if row.outcome in _HIGHLIGHTS:
            for cell in cells:
                cell.fill = _HIGHLIGHTS[row.outcome]
    _wrap(summary, "N")
    _filterable(summary, {"A": 9, "B": 16, "C": 16, "D": 10, "E": 12, "F": 12, "G": 12, "H": 12, "I": 12, "J": 12, "K": 16,
                          "L": 20, "M": 10, "N": 60})

    largest = workbook.create_sheet("Largest")
    _table(largest, _LARGEST, [[line[column] for column in _LARGEST]
                               for line in largest_shipments(row_results, note_results, categories)])
    _filterable(largest, {"A": 6, "B": 16, "C": 6, "D": 15, "E": 14, "F": 13, "G": 14, "H": 16, "I": 16, "J": 28})

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
