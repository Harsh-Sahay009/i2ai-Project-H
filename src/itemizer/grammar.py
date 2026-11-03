"""The output grammar: the only form a model's answer may take. Common core: no setting changes it.

`parse_answer` is the single gate. It reads a model's raw text, trusts no provider, and rejects rather than repairs.
Violation details are fixed sentences, so a hostile answer or a note's text cannot reach an error message.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, get_args

from pydantic import BaseModel, ConfigDict

from .bootstrap.data import Note
from .bootstrap.labels import DERIVATIONS, LINE_TYPES, check_item
from .contracts import Basis, ChargeItem, ReasonCode

GRAMMAR_VERSION = "1"
MAX_ITEMS = 12

BASES = get_args(Basis)
REASON_CODES = get_args(ReasonCode)
_ANSWER_KEYS = ("items", "no_charge_stated", "unsure", "reason_code")
_ITEM_KEYS = ("category", "amount", "evidence_text", "line_type", "derivation", "basis")
# `$` would allow a trailing newline, and `\d` would allow digits such as "٨٥", which Decimal reads as 85.
_AMOUNT = re.compile(r"[0-9]{1,7}\.[0-9]{2}")

VIOLATIONS = {
    "not_json": "the answer must be one JSON object with nothing around it",
    "wrong_shape": "the answer must hold exactly the allowed keys, once each, with the right types",
    "bad_amount": "amount must be a string of digits, a point and two digits",
    "unknown_category": "category is not in the approved list",
    "bad_line_type": "line_type is not in its closed list",
    "bad_derivation": "derivation is not in its closed list",
    "bad_basis": "basis is not in its closed list",
    "bad_reason_code": "reason_code is not in its closed list",
    "too_many_items": f"an answer may hold at most {MAX_ITEMS} items",
    "flag_with_items": "no_charge_stated is true, but the answer has items",
    "empty_answer": "the answer has no items, and neither no_charge_stated nor unsure is true",
    "evidence_not_verbatim": "evidence_text is not copied exactly from the note",
    "amount_not_in_evidence": "the amount does not appear in evidence_text",
    "product_mismatch": "the amount is not the product of two numbers in evidence_text",
}
# When these are the only violations left after the retry, the note goes to Review as `evidence_failed`.
EVIDENCE_RULES = frozenset({"evidence_not_verbatim", "amount_not_in_evidence", "product_mismatch"})


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ChargeItem]
    no_charge_stated: bool
    unsure: bool
    reason_code: ReasonCode


@dataclass(frozen=True)
class Violation:
    code: str
    detail: str


@dataclass(frozen=True)
class ParseResult:
    """Either an answer, or the reasons there is none. Never both."""

    answer: Answer | None = None
    violations: list[Violation] = field(default_factory=list)


def answer_schema(codes: Iterable[str]) -> dict:
    """The grammar for the provider. It avoids what structured output rejects, so `parse_answer` checks those rules."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(_ANSWER_KEYS),
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(_ITEM_KEYS),
                    "properties": {
                        "category": {"type": "string", "enum": sorted(set(codes))},  # sorted, so the bytes never change
                        "amount": {"type": "string"},
                        "evidence_text": {"type": "string"},
                        "line_type": {"type": "string", "enum": list(LINE_TYPES)},
                        "derivation": {"type": "string", "enum": list(DERIVATIONS)},
                        "basis": {"type": "string", "enum": list(BASES)},
                    },
                },
            },
            "no_charge_stated": {"type": "boolean"},
            "unsure": {"type": "boolean"},
            "reason_code": {"type": "string", "enum": list(REASON_CODES)},
        },
    }


class _DuplicateKey(Exception):
    pass


def _refuse_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    found = dict(pairs)
    if len(found) != len(pairs):
        raise _DuplicateKey
    return found


def _refuse_constant(_: str) -> None:
    raise ValueError("NaN and Infinity are not JSON")


def _violation(code: str, item_no: int | None = None) -> Violation:
    return Violation(code, VIOLATIONS[code] if item_no is None else f"item {item_no}: {VIOLATIONS[code]}")


def _shape_violations(data: Any) -> list[Violation]:
    """Structure only. A value outside a closed list has its own code, so it is checked with the rules."""
    if not isinstance(data, dict) or set(data) != set(_ANSWER_KEYS):
        return [_violation("wrong_shape")]
    if not all(isinstance(data[flag], bool) for flag in ("no_charge_stated", "unsure")) or not isinstance(data["items"], list):
        return [_violation("wrong_shape")]
    return [_violation("wrong_shape", number) for number, item in enumerate(data["items"], start=1)
            if not isinstance(item, dict) or set(item) != set(_ITEM_KEYS) or not isinstance(item["evidence_text"], str)]


def _check_one(raw: dict, number: int, note: Note, codes: set[str]) -> tuple[ChargeItem | None, list[Violation]]:
    amount = raw["amount"] if isinstance(raw["amount"], str) and _AMOUNT.fullmatch(raw["amount"]) else None
    category = raw["category"] if isinstance(raw["category"], str) else ""  # a list here could not be looked up in a set
    try:
        gold, errors = check_item(note, number, category, amount, raw["evidence_text"], raw["line_type"],
                                  raw["derivation"], codes)
    except ArithmeticError:  # check_item cannot multiply numbers too long for Decimal, and a note can hold any digits
        gold, errors = None, [("product_mismatch", "")]
    found = [_violation(code, number) for code, _ in errors]
    if raw["basis"] not in BASES:
        found.append(_violation("bad_basis", number))
    if found:
        return None, found
    return ChargeItem(**gold.model_dump(), basis=raw["basis"]), []


def parse_answer(raw_text: str, note: Note, codes: Iterable[str]) -> ParseResult:
    """Accept one answer of the exact shape whose every item passes the same checks as a label, or say why not."""
    try:
        data = json.loads(raw_text, object_pairs_hook=_refuse_duplicates, parse_constant=_refuse_constant)
    except _DuplicateKey:
        return ParseResult(violations=[_violation("wrong_shape")])
    except (TypeError, ValueError, RecursionError):
        return ParseResult(violations=[_violation("not_json")])
    shape = _shape_violations(data)
    if shape:
        return ParseResult(violations=shape)

    violations: list[Violation] = []
    if data["reason_code"] not in REASON_CODES:
        violations.append(_violation("bad_reason_code"))
    if len(data["items"]) > MAX_ITEMS:
        violations.append(_violation("too_many_items"))
    if data["no_charge_stated"] and data["items"]:
        violations.append(_violation("flag_with_items"))
    if not data["items"] and not data["no_charge_stated"] and not data["unsure"]:
        violations.append(_violation("empty_answer"))
    allowed = set(codes)
    items: list[ChargeItem] = []
    for number, raw in enumerate(data["items"], start=1):
        item, problems = _check_one(raw, number, note, allowed)
        violations += problems
        if item is not None:
            items.append(item)
    if violations:
        return ParseResult(violations=violations)
    return ParseResult(answer=Answer(items=items, no_charge_stated=data["no_charge_stated"], unsure=data["unsure"],
                                     reason_code=data["reason_code"]))
