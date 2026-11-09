"""Input contract, notes, gold labels and the working folder for the bootstrap."""
from __future__ import annotations

import datetime as dt
import getpass
import hashlib
import json
import re
import subprocess
import zipfile
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

import openpyxl
import yaml
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import BaseModel, ConfigDict

CENT = Decimal("0.01")
CATCH_ALL = "other_unmapped"

# Column names in the current export (add-data-transformation-check design).
COLUMNS = {
    "shipment": "SHIPMENT_GID",
    "invoice": "Carrier Invoice",
    "carrier": "Carrier",
    "event_date": "Event Date",
    "estimated": "Shipment Amount",
    "billed": "Invoice Amount",
    "disputed": "Delta",
    "status": "Dispute Status",
    "reason": "Reason Code",
    "note": "Descritipion",
    "repeat_marker": "Invoice Dups Removed",
}
# Read when present (ADR 0017). Without SAP BOL, the workbook groups by shipment.
OPTIONAL_COLUMNS = {
    "sap_bol": "SAP BOL",
    "bill_id": "Invoice/Bill ID",
}


class ContractError(Exception):
    """A rule of the bootstrap was broken. The message says which, in plain words."""


class Config(BaseModel):
    source_file: str = ""
    dataset_class: Literal["open_anonymized", "client_confidential"] = "client_confidential"
    source_ref: str | None = None
    large_dispute_usd: Decimal = Decimal("180.00")
    seed: int = 20261102
    validation_share: float = 0.40
    min_validation_notes: int = 100
    test_large_notes: int = 50
    test_reserve_notes: int = 20
    max_stratum_gap_notes: int = 10
    examples_sheet: str = "Sheet1"
    data_root: str = "data"


def load_config(path: Path) -> Config:
    if not path.is_file():
        raise ContractError(f"settings not found: {path}. Run this from the project's folder")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data, strata, split = raw.get("data", {}), raw.get("strata", {}), raw.get("split", {})
    return Config(
        source_file=data.get("source_file", ""),
        dataset_class=data.get("dataset_class", "client_confidential"),
        source_ref=data.get("source_ref"),
        large_dispute_usd=Decimal(str(strata.get("large_dispute_usd", "180.00"))),
        data_root=raw.get("runtime", {}).get("data_root", "data"),
        **{k: split[k] for k in ("seed", "validation_share", "min_validation_notes", "test_large_notes",
                                 "test_reserve_notes", "max_stratum_gap_notes") if k in split},
    )


def to_money(value: Any) -> Decimal:
    """Read an amount as Decimal cents. The export stores floats such as 75.59999999999997."""
    try:
        amount = Decimal(str(value)).quantize(CENT, ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        amount = None
    if amount is None or not amount.is_finite():  # the value is not shown, because a shifted cell can hold a note
        raise ContractError("a cell that should hold an amount holds something else") from None
    return amount


class DisputeRow(BaseModel):
    """One row of the export. `row_id` comes from its position, because no ID columns identify a row."""

    row_id: str
    shipment: str
    invoice: str
    carrier: str
    event_date: str
    estimated: Decimal
    billed: Decimal
    disputed: Decimal
    status: str
    reason: str
    note: str
    flags: list[str] = []
    sap_bol: str = ""
    bill_id: str = ""


class Note(BaseModel):
    """One distinct normalized note and the rows that share it."""

    fingerprint: str
    note_id: str
    text: str
    row_ids: list[str]
    carrier: str
    disputed: Decimal
    max_disputed: Decimal
    usd: Decimal
    format_key: str
    money_tokens: int
    band: str
    stratum: str


class GoldItem(BaseModel):
    """One charge in a gold label. It has the same shape as a predicted item, so the KPI matcher can compare them."""

    model_config = ConfigDict(extra="forbid")

    item: int
    category: str
    amount: Decimal
    evidence_text: str
    evidence_start: int
    evidence_end: int
    line_type: Literal["charge", "tax", "already_paid"]
    derivation: Literal["stated", "rate_x_quantity"]


class NoteLabel(BaseModel):
    """One labeller's answer for one note."""

    model_config = ConfigDict(extra="forbid")

    fingerprint: str
    note_id: str
    labeller: str
    pack: str
    no_charge_stated: bool = False
    items: list[GoldItem] = []
    source: Literal["human", "model_suggestion_confirmed", "model_draft", "person_checked", "person_corrected"] = "human"
    comment: str = ""


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def fingerprint(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def format_key(text: str) -> str:
    """The note with its numbers hidden, so notes that differ only in numbers share a format."""
    return re.sub(r"\d+(?:[.,]\d+)*", "#", normalize(text))


# Notes write thousands with a space ("$1 277.68") and hold many numbers that are not money: dates, times,
# weights ("7 408 LBS"), bill numbers. So a money token needs a dollar sign or exactly two decimals.
_MONEY = re.compile(r"\$\s?\d{1,3}(?: \d{3})+(?:\.\d{1,2})?(?![\d.])|\$\s?\d+(?:\.\d{1,2})?|"
                    r"(?<![\d.$:/-])\d{1,3}(?: \d{3})+\.\d{2}(?![\d.])|(?<![\d.$:/-])\d*\.\d{2}(?![\d.%])")
_RUNNING_TOTAL = re.compile(r"=\s*\$?\s*\d[\d ,]*(?:\.\d+)?")
_BALANCE = re.compile(r"BALANCE DUE\s*(?:IS\s*)?\$?\s*\d[\d ,]*(?:\.\d{1,2})?(?![\d.]|\s*\+)", re.I)


def _amounts(text: str) -> set[Decimal]:
    return {Decimal(re.sub(r"[$\s,]", "", token)) for token in _MONEY.findall(text)}


def money_tokens(text: str) -> int:
    """A rough count of distinct charges, used only for provisional strata."""
    stripped = _RUNNING_TOTAL.sub(" ", text)
    found = _amounts(stripped)
    if len(found) > 1:  # a balance due stated beside its charges is a total, not another charge
        without_balance = _amounts(_BALANCE.sub(" ", stripped))
        if without_balance:
            return len(without_balance)
    return len(found)


def repeat_band(rows: int) -> str:
    return "5+" if rows >= 5 else ("2-4" if rows >= 2 else "1")


def _id_text(value: Any) -> str:
    """An ID cell as text. Excel can store an all-digit ID as a number, which must not gain a ".0"."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _event_date(value: Any) -> str:
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, (int, float)):
        return (dt.datetime(1899, 12, 30) + dt.timedelta(days=float(value))).date().isoformat()
    return str(value or "")


def load_export(path: Path, examples_sheet: str = "Sheet1") -> tuple[list[DisputeRow], set[str]]:
    """Read every row of the export, and the fingerprints of notes in the team's example sheet."""
    try:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except (InvalidFileException, zipfile.BadZipFile, KeyError, OSError, ValueError):
        raise ContractError(f"{path.name} cannot be read as an Excel workbook") from None
    try:
        main = next((ws for ws in workbook.worksheets if ws.title != examples_sheet), None)
        if main is None:
            raise ContractError("the workbook has no export sheet")
        rows_iter = main.iter_rows(values_only=True)
        header = [str(c) if c is not None else "" for c in next(rows_iter, ())]
        missing = [name for name in COLUMNS.values() if name not in header]
        if missing:
            raise ContractError(f"missing columns: {', '.join(missing)}")
        at = {key: header.index(name) for key, name in COLUMNS.items()}
        at.update({key: header.index(name) for key, name in OPTIONAL_COLUMNS.items() if name in header})
        rows: list[DisputeRow] = []
        for number, raw in enumerate(rows_iter, start=2):
            if all(cell is None for cell in raw):
                continue
            note = "" if raw[at["note"]] is None else str(raw[at["note"]])
            try:
                disputed = to_money(raw[at["disputed"]])
                to_money(raw[at["repeat_marker"]])
            except ContractError as exc:
                raise ContractError(f"export row {number}: {exc}") from None
            flags = []
            if to_money(raw[at["repeat_marker"]]) == 0:
                flags.append("repeated_invoice")
            if not note.strip():
                flags.append("empty_note")
            if disputed <= 0:
                flags.append("non_positive_delta")
            rows.append(DisputeRow(
                row_id=f"R{number:04d}",
                shipment=str(raw[at["shipment"]]),
                invoice=str(raw[at["invoice"]]),
                carrier=str(raw[at["carrier"]]),
                event_date=_event_date(raw[at["event_date"]]),
                estimated=to_money(raw[at["estimated"]]),
                billed=to_money(raw[at["billed"]]),
                disputed=disputed,
                status=str(raw[at["status"]]),
                reason=str(raw[at["reason"]]),
                note=note,
                flags=flags,
                sap_bol=_id_text(raw[at["sap_bol"]]) if "sap_bol" in at else "",
                bill_id=_id_text(raw[at["bill_id"]]) if "bill_id" in at else "",
            ))
        examples: set[str] = set()
        if examples_sheet in workbook.sheetnames:
            sheet_iter = workbook[examples_sheet].iter_rows(values_only=True)
            sheet_header = [str(c) if c is not None else "" for c in next(sheet_iter)]
            if "original" in sheet_header:
                column = sheet_header.index("original")
                examples = {fingerprint(str(r[column])) for r in sheet_iter if r[column]}
        return rows, examples
    finally:
        workbook.close()


def group_notes(rows: list[DisputeRow], large_dispute_usd: Decimal) -> dict[str, Note]:
    """Collapse rows into distinct notes, in a stable order. Rows with no note have no entry."""
    grouped: dict[str, list[DisputeRow]] = {}
    for row in rows:
        if row.note.strip():
            grouped.setdefault(fingerprint(row.note), []).append(row)
    notes: dict[str, Note] = {}
    seen_ids: set[str] = set()
    for fp in sorted(grouped):
        members = grouped[fp]
        text = members[0].note
        note_id = f"n_{fp[:8]}"
        if note_id in seen_ids:
            raise ContractError(f"note id collision on {note_id}")
        seen_ids.add(note_id)
        top = max(r.disputed for r in members)
        tokens = money_tokens(text)
        stratum = "large" if top >= large_dispute_usd else ("multi" if tokens >= 2 else "single")
        notes[fp] = Note(
            fingerprint=fp,
            note_id=note_id,
            text=text,
            row_ids=[r.row_id for r in members],
            carrier=members[0].carrier,
            disputed=members[0].disputed,
            max_disputed=top,
            usd=sum((max(r.disputed, Decimal(0)) for r in members), Decimal(0)),
            format_key=format_key(text),
            money_tokens=tokens,
            band=repeat_band(len(members)),
            stratum=stratum,
        )
    return notes


def find_evidence(raw_note: str, quote: str) -> tuple[int, int] | None:
    """Locate a quote in the raw note, allowing only whitespace differences (`exact_ws_normalized`)."""
    quote = quote.strip()
    if not quote:
        return None
    pattern = r"\s+".join(re.escape(part) for part in quote.split())
    match = re.search(pattern, raw_note)
    return (match.start(), match.end()) if match else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Workspace:
    """The bootstrap's folder under the data root. It refuses to work in a folder Git would track."""

    def __init__(self, cfg: Config, project_root: Path):
        self.cfg = cfg
        self.project_root = project_root
        self.root = project_root / cfg.data_root / "bootstrap"
        self.root.mkdir(parents=True, exist_ok=True)
        self._ensure_ignored()

    def _ensure_ignored(self) -> None:
        inside = subprocess.run(["git", "-C", str(self.project_root), "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, text=True)
        if inside.returncode != 0:
            return
        ignored = subprocess.run(["git", "-C", str(self.project_root), "check-ignore", "-q", str(self.root)])
        if ignored.returncode != 0:
            raise ContractError(f"{self.root} is not ignored by Git; this repo is public, so data cannot go there")

    def path(self, name: str) -> Path:
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def exists(self, name: str) -> bool:
        return (self.root / name).exists()

    def write_json(self, name: str, payload: Any) -> Path:
        target = self.path(name)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                          encoding="utf-8")
        return target

    def read_json(self, name: str) -> Any:
        target = self.root / name
        if not target.exists():
            raise ContractError(f"{name} does not exist yet; run the earlier step first")
        return json.loads(target.read_text(encoding="utf-8"))

    def log(self, command: str, inputs: list[Path] = [], outputs: list[Path] = [], **extra: Any) -> None:
        """Who ran what, on which inputs, producing which outputs. Imported into the episode store later."""
        entry = {
            "command": command,
            "who": getpass.getuser(),
            "when": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "inputs": {p.name: sha256_file(p) for p in inputs if p.exists()},
            "outputs": {p.name: sha256_file(p) for p in outputs if p.exists()},
            **extra,
        }
        with self.path("command_log.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
