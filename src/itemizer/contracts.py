"""Contracts shared by the itemizer, the workbook and the KPIs. Common core: no setting changes them."""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .bootstrap.data import DisputeRow, GoldItem, Note, to_money

__all__ = [
    "Basis", "ChargeItem", "DisputeRow", "GoldItem", "Note", "NoteResult", "Outcome", "OutcomeReason", "ReasonCode",
    "ReviewReason", "RowResult", "RunManifest", "export_schemas", "to_money",
]

Basis = Literal["named_in_note", "inferred_from_context", "no_description"]
ReasonCode = Literal["none", "no_amount_stated", "amount_unclear", "charge_unclear", "conflicting_amounts",
                     "instruction_in_note"]
ReviewReason = Literal["grammar_failed", "evidence_failed", "model_unsure", "refused", "provider_unavailable",
                       "budget_exhausted"]
Outcome = Literal["verified", "discrepancy", "no_charge_stated", "review"]
OutcomeReason = Literal["empty_note", "no_charge_in_note", "does_not_add_up", "repeated_invoice", "adds_up",
                        "grammar_failed", "evidence_failed", "model_unsure", "refused", "provider_unavailable",
                        "budget_exhausted"]

# Real codes come from the taxonomy at runtime, so the exported grammar shows where they go and names none.
PLACEHOLDER_CODES = ["category_code_supplied_at_runtime"]


class ChargeItem(GoldItem):
    """One charge in a model's answer: a gold item's shape, plus what the fixed `ai_reason` sentence is rendered from."""

    basis: Basis


class NoteResult(BaseModel):
    """The answer for one distinct note. Items exist only when the note passed every check."""

    model_config = ConfigDict(extra="forbid")

    fingerprint: str
    note_id: str
    items: list[ChargeItem] = []
    no_charge_stated: bool = False
    status: Literal["ok", "review"]
    review_reason: ReviewReason | None = None
    reason_code: ReasonCode = "none"
    attempts: int = 0
    model: str
    cost_usd: Decimal = Decimal(0)
    latency_ms: int = 0
    cached: bool = False
    violations: list[str] = []

    @model_validator(mode="after")
    def _status_matches_contents(self) -> NoteResult:
        if (self.status == "review") != (self.review_reason is not None):
            raise ValueError("review_reason must be set when status is review, and only then")
        if self.items and (self.status == "review" or self.no_charge_stated):
            raise ValueError("a note in Review or stating no charge carries no items")
        return self


class RowResult(BaseModel):
    """One row's outcome. The totals are None when the row never reached reconciliation."""

    model_config = ConfigDict(extra="forbid")

    row_id: str
    note_id: str | None = None
    fingerprint: str | None = None
    shipment: str
    invoice: str
    carrier: str
    status: str
    reason: str
    disputed: Decimal
    items_total: Decimal | None = None
    already_paid_total: Decimal | None = None
    difference: Decimal | None = None
    outcome: Outcome
    outcome_reason: OutcomeReason
    repeated: bool = False
    item_count: int = 0
    note: str = ""


# Where the code was when the run happened. Recorded, but a commit or a clean tree changes no answer, so neither is in the id.
_NOT_IN_RUN_ID = {"code_commit", "code_dirty"}


class RunManifest(BaseModel):
    """Everything a run's numbers depend on. `model` is the full registry entry, which names a key's variable only."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_sha256: str
    set_name: Literal["all", "train", "validation"]
    limit: int | None = None
    taxonomy_sha256: str
    prompt_sha256: str
    fewshot_sha256: str
    grammar_version: str
    model: dict[str, Any]
    config_sha256: str
    code_sha: str  # a hash of the source and the lockfile
    code_commit: str = ""
    code_dirty: bool
    split_sha256: str | None = None  # None for an export other than the dataset file, whose notes need no split

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json", exclude=_NOT_IN_RUN_ID), sort_keys=True, separators=(",", ":"))

    @property
    def run_id(self) -> str:
        return "run_" + hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()[:16]


def export_schemas(folder: Path) -> list[Path]:
    """Write a JSON Schema for each contract and for the grammar. The same code always writes the same files."""
    from .grammar import answer_schema  # grammar imports this module

    schemas = {name: model.model_json_schema(mode="serialization") for name, model in (
        ("charge_item", ChargeItem), ("note_result", NoteResult), ("row_result", RowResult), ("run_manifest", RunManifest))}
    schemas["answer"] = answer_schema(PLACEHOLDER_CODES)
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for name, schema in sorted(schemas.items()):
        path = folder / f"{name}.json"
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    return written
