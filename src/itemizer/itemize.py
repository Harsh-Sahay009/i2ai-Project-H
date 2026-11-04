"""The itemizer: one call per distinct note, then one outcome per row. Amounts are never changed at any step.

An answer reaches a result only through `parse_answer`, on every run, even when it came from the cache. Each request
has its own cache entry, so a retry's prompt does too, and a repeat run replays both without a call. Refusals are cached
because a repeat run must give the same result. Failed calls and spent budgets are not, so a repeat run can recover them.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .bootstrap.data import ContractError, DisputeRow, Note, fingerprint, to_money
from .contracts import NoteResult, RowResult
from .grammar import EVIDENCE_RULES, Violation, answer_schema, parse_answer
from .providers import Completion, ModelSpec, Provider, ProviderError, ProviderRefused, cost_usd

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "itemize_v1.md"
MAX_ATTEMPTS = 2  # one answer, and one retry with its violation codes
_PLACEHOLDER = re.compile(r"\{\{(categories|examples)\}\}")
_CLOSING_TAG = re.compile(r"</(?=\s*untrusted_note)", re.IGNORECASE)
_ZERO = Decimal("0.00")


@dataclass(frozen=True)
class FewShot:
    """One worked example. `answer` is the exact text of an answer the grammar accepted."""

    note: Note
    answer: str


def _fewshot_answer(entry: dict, note: Note) -> str:
    items = []
    for item in entry["items"]:
        if not 0 <= item["start"] < item["end"] <= len(note.text):
            raise ContractError(f"worked example {note.note_id}: an item's offsets are outside the note")
        items.append({"category": item["category"], "amount": item["amount"],
                      "evidence_text": note.text[item["start"]:item["end"]], "line_type": item["line_type"],
                      "derivation": item["derivation"], "basis": item["basis"]})
    return json.dumps({"items": items, "no_charge_stated": False, "unsure": False, "reason_code": "none"}, ensure_ascii=False)


def _load_fewshot(entry: Any, by_id: dict[str, Note], sets: dict[str, str], codes: set[str]) -> FewShot:
    note_id = str(entry.get("note_id")) if isinstance(entry, dict) else "without a note_id"
    if note_id not in by_id:
        raise ContractError(f"worked example {note_id}: the note is not in the dataset")
    if sets.get(note_id) != "TRAIN":
        raise ContractError(f"worked example {note_id}: the note is in {sets.get(note_id, 'no set')}, and examples must "
                            "come from TRAIN")
    note = by_id[note_id]
    try:
        answer = _fewshot_answer(entry, note)
    except (KeyError, TypeError):
        raise ContractError(f"worked example {note_id}: an item is missing a field or has one of the wrong type") from None
    parsed = parse_answer(answer, note, codes)
    if parsed.violations:
        found = ", ".join(sorted({violation.code for violation in parsed.violations}))
        raise ContractError(f"worked example {note_id} breaks the grammar: {found}")
    return FewShot(note=note, answer=answer)


def load_fewshots(path: Path, notes: dict[str, Note], manifest: dict, codes: Iterable[str]) -> list[FewShot]:
    """Worked examples from TRAIN, with their text read from the dataset. A bad one stops the run before any call."""
    if not path.exists():
        raise ContractError(f"worked examples not found: {path}")
    try:
        entries = yaml.safe_load(path.read_text(encoding="utf-8"))["examples"]
    except (yaml.YAMLError, KeyError, TypeError):
        raise ContractError(f"{path.name} does not list examples") from None
    by_id = {note.note_id: note for note in notes.values()}
    sets = {entry["note_id"]: entry["set"] for entry in manifest["notes"]}
    allowed = set(codes)
    return [_load_fewshot(entry, by_id, sets, allowed) for entry in entries]


def _describe_category(category: dict) -> str:
    lines = [f"- `{category['code']}` ({category['name']}): {category['definition']}"]
    for label, key in (("Includes", "includes"), ("Excludes", "excludes")):
        if category.get(key):
            lines.append(f"  {label}: {'; '.join(category[key])}")
    return "\n".join(lines)


def build_user_prompt(note: Note) -> str:
    """The note, marked as data. A closing tag inside it is broken up, so a note cannot end its own quotation."""
    text = _CLOSING_TAG.sub(r"<\\/", note.text)
    return f"<untrusted_note>\n{text}\n</untrusted_note>\nDisputed amount: {note.disputed:.2f}"


def build_system_prompt(categories: list[dict], fewshots: list[FewShot], template: Path = PROMPT_PATH) -> str:
    """The same inputs always give the same bytes, so the provider's prompt cache keeps working."""
    if not template.exists():
        raise ContractError(f"prompt not found: {template}")
    text = template.read_text(encoding="utf-8")
    parts = {
        "categories": "\n".join(_describe_category(c) for c in sorted(categories, key=lambda c: c["code"])),
        "examples": "\n\n".join(f"Example {number}:\n{build_user_prompt(shot.note)}\nAnswer:\n{shot.answer}"
                                for number, shot in enumerate(fewshots, start=1)),
    }
    if set(_PLACEHOLDER.findall(text)) != set(parts):
        raise ContractError(f"{template.name} must hold both {{{{categories}}}} and {{{{examples}}}}")
    return _PLACEHOLDER.sub(lambda match: parts[match[1]], text)  # one pass, so a placeholder inside a note stays as it is


def _retry_prompt(user: str, violations: list[Violation]) -> str:
    """`detail` is a fixed sentence and an item number, so no model or note text comes back through it."""
    found = "\n".join(f"- {violation.code}: {violation.detail}" for violation in violations)
    return f"{user}\n\nYour previous answer was rejected for these violations. Answer this note again:\n{found}"


class _BudgetSpent(Exception):
    """A call would have started after the budget ran out."""


class Budget:
    """Limits shared by every thread, checked before each call starts.

    A call's cost is known only when it ends, so calls already running finish, and a run can overrun by what they cost.
    """

    def __init__(self, max_usd: Any, max_minutes: Any, clock: Callable[[], float] = time.monotonic):
        self.max_usd = to_money(max_usd)
        try:
            self._max_seconds = float(max_minutes) * 60
        except (TypeError, ValueError):
            raise ContractError(f"the budget's minutes must be a number, not {max_minutes!r}") from None
        self._clock = clock
        self._started = clock()
        self._spent = Decimal(0)
        self._lock = threading.Lock()

    def can_start(self) -> bool:
        with self._lock:
            return self._spent < self.max_usd and self._clock() - self._started < self._max_seconds

    def charge(self, usd: Decimal) -> None:
        with self._lock:
            self._spent += usd

    @property
    def spent_usd(self) -> Decimal:
        with self._lock:
            return self._spent


@dataclass
class _Usage:
    """What one note used in this run. An answer from the cache counts as an attempt, and costs nothing."""

    attempts: int = 0
    calls: int = 0
    cost: Decimal = Decimal(0)
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    # What the answers cost when first made, replayed from the cache, so comparing models twice reports the same figures.
    measured_cost: Decimal = Decimal(0)
    measured_latency_ms: int = 0

    def add(self, completion: Completion, cost: Decimal) -> None:
        self.cost += cost
        self.latency_ms += completion.latency_ms
        self.input_tokens += completion.input_tokens
        self.output_tokens += completion.output_tokens
        self.cache_read_tokens += completion.cache_read_tokens
        self.cache_write_tokens += completion.cache_write_tokens


def _cache_key(spec: ModelSpec, system: str, user: str, schema: dict) -> str:
    """Everything that can change a reply, so a new model id, server, limit or fallback setting cannot replay an old answer."""
    payload = json.dumps([spec.name, spec.model, spec.effort, spec.base_url, spec.max_tokens, spec.refusal_fallback, system, user, schema],
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _read_cache(path: Path) -> dict | None:
    """An entry that cannot be read counts as missing. Its text is not trusted either way: `parse_answer` checks it."""
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    usable = isinstance(stored, dict) and (stored.get("refused") is True or isinstance(stored.get("text"), str))
    if usable:
        try:
            Decimal(str(stored.get("cost_usd", "0")))
            int(stored.get("latency_ms", 0))
        except (InvalidOperation, OverflowError, TypeError, ValueError):
            usable = False
    return stored if usable else None


def _write_atomic(path: Path, text: str) -> None:
    """Write a temporary file, then rename it, so a reader on another thread never sees half a file."""
    temp = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp, path)
    except OSError as exc:
        if temp:
            Path(temp).unlink(missing_ok=True)
        raise ContractError(f"could not write {path}: {exc.strerror}") from None


@dataclass(frozen=True)
class _Caller:
    """One model's requests in one run: the cache first, then the model, if the budget allows it."""

    provider: Provider
    system: str
    schema: dict
    folder: Path
    budget: Budget

    def ask(self, user: str, usage: _Usage) -> str:
        spec = self.provider.spec
        path = self.folder / f"{_cache_key(spec, self.system, user, self.schema)}.json"
        stored = _read_cache(path)
        if stored is None and not self.budget.can_start():
            raise _BudgetSpent
        usage.attempts += 1
        if stored is None:
            stored = self._call(user, usage, path)
        else:
            usage.measured_cost += Decimal(str(stored.get("cost_usd", "0")))
            usage.measured_latency_ms += int(stored.get("latency_ms", 0))
        if stored.get("refused"):
            raise ProviderRefused(f"{spec.name}: the model declined this note")
        return stored["text"]

    def _charge(self, completion: Completion | None, usage: _Usage) -> dict:
        """Count what a call used, and return the figures kept beside its answer."""
        if completion is None:
            return {"cost_usd": "0", "latency_ms": 0}
        cost = cost_usd(self.provider.spec, completion)
        self.budget.charge(cost)
        usage.add(completion, cost)
        usage.measured_cost += cost  # here rather than from the cache entry, because a cut-off call is never stored
        usage.measured_latency_ms += completion.latency_ms
        return {"cost_usd": str(cost), "latency_ms": completion.latency_ms}

    def _call(self, user: str, usage: _Usage, path: Path) -> dict:
        usage.calls += 1
        try:
            completion = self.provider.complete(self.system, user, self.schema)
        except ProviderRefused as refused:
            stored: dict = {"refused": True, **self._charge(refused.usage, usage)}
        except ProviderError as failed:  # not stored, so a repeat run tries again, and it still costs what it cost
            self._charge(failed.usage, usage)
            raise
        else:
            stored = {"text": completion.text, **self._charge(completion, usage)}
        _write_atomic(path, json.dumps(stored))
        return stored


def _note_result(note: Note, caller: _Caller, usage: _Usage, violations: list[str], **outcome: Any) -> tuple[NoteResult, _Usage]:
    return NoteResult(fingerprint=note.fingerprint, note_id=note.note_id, violations=violations, attempts=usage.attempts,
                      model=caller.provider.spec.name, cost_usd=usage.cost, latency_ms=usage.latency_ms,
                      cached=usage.attempts > 0 and usage.calls == 0, **outcome), usage


def _itemize_note(note: Note, caller: _Caller, codes: list[str]) -> tuple[NoteResult, _Usage]:
    """`violations` holds the codes of the latest rejected answer, and the last answer alone decides the Review reason."""
    usage = _Usage()
    user = build_user_prompt(note)
    prompt = user
    violations: list[str] = []
    try:
        for _ in range(MAX_ATTEMPTS):
            parsed = parse_answer(caller.ask(prompt, usage), note, codes)
            answer = parsed.answer
            if answer is not None and answer.unsure:  # its items are dropped: a person reads this note
                return _note_result(note, caller, usage, violations, status="review", review_reason="model_unsure",
                                    reason_code=answer.reason_code)
            if answer is not None:
                return _note_result(note, caller, usage, violations, status="ok", items=answer.items,
                                    no_charge_stated=answer.no_charge_stated, reason_code=answer.reason_code)
            violations = [violation.code for violation in parsed.violations]
            prompt = _retry_prompt(user, parsed.violations)
        reason = "evidence_failed" if set(violations) <= EVIDENCE_RULES else "grammar_failed"
    except _BudgetSpent:
        reason = "budget_exhausted"
    except ProviderRefused:
        reason = "refused"
    except ProviderError:
        reason = "provider_unavailable"
    return _note_result(note, caller, usage, violations, status="review", review_reason=reason)


def _telemetry_line(result: NoteResult, usage: _Usage) -> str:
    """Counts and codes only: no note text, no evidence and no secrets."""
    return json.dumps({
        "note_id": result.note_id, "attempts": result.attempts, "violations": result.violations,
        "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
        "cache_read_tokens": usage.cache_read_tokens, "cache_write_tokens": usage.cache_write_tokens,
        "cost_usd": str(result.cost_usd), "latency_ms": result.latency_ms, "cached": result.cached,
        "measured_cost_usd": str(usage.measured_cost), "measured_latency_ms": usage.measured_latency_ms,
        "status": result.status, "review_reason": result.review_reason,
    }, sort_keys=True) + "\n"


def notes_needing_a_call(notes: dict[str, Note], spec: ModelSpec, codes: Iterable[str], system: str, cache_dir: Path) -> int:
    """How many notes have no stored answer, by the same key a run uses."""
    schema = answer_schema(sorted(set(codes)))
    folder = Path(cache_dir) / spec.name
    return sum(_read_cache(folder / f"{_cache_key(spec, system, build_user_prompt(note), schema)}.json") is None for note in notes.values())


def itemize_notes(notes: dict[str, Note], provider: Provider, codes: Iterable[str], system: str, cache_dir: Path,
                  budget: Budget, concurrency: int, telemetry: Path,
                  progress: Callable[[int, int, Decimal], None] | None = None) -> dict[str, NoteResult]:
    """One call per distinct note. Results and telemetry are sorted by fingerprint, whatever order the threads finish in.

    A ContractError from a call, such as a limit every note would hit, stops the run and cancels the notes not started.
    `progress(done, total, spent)` is told after each note, and a failure inside it cannot stop the run.
    """
    if concurrency < 1:
        raise ContractError("runtime.concurrency must be at least 1")
    allowed = sorted(set(codes))
    caller = _Caller(provider, system, answer_schema(allowed), Path(cache_dir) / provider.spec.name, budget)
    counted = threading.Lock()
    finished_notes = 0

    def work(note: Note) -> tuple[NoteResult, _Usage]:
        nonlocal finished_notes
        outcome = _itemize_note(note, caller, allowed)
        with counted:
            finished_notes += 1
            done_so_far = finished_notes
        if progress is not None:
            try:
                progress(done_so_far, len(notes), budget.spent_usd)
            except Exception:  # only a display, so it must not be able to break a run
                pass
        return outcome

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(work, notes[key]) for key in sorted(notes)]
        try:
            finished, _ = wait(futures, return_when=FIRST_EXCEPTION)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
    for future in finished:
        future.result()  # raises the failure that ended the wait
    done = [future.result() for future in futures]
    _write_atomic(Path(telemetry), "".join(_telemetry_line(result, usage) for result, usage in done))
    return {result.fingerprint: result for result, _ in done}


class Policy(BaseModel):
    """The settings that decide a row's outcome: `reconcile` and `review` in config/run.yaml."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    abs_tolerance_usd: Decimal = Field(ge=0)
    no_charge_stated_policy: Literal["verified", "review"]
    repeated_invoice_policy: Literal["flag_discrepancy", "none"]

    @classmethod
    def from_settings(cls, settings: dict) -> Policy:
        try:
            return cls(abs_tolerance_usd=settings["reconcile"]["abs_tolerance_usd"],
                       no_charge_stated_policy=settings["review"]["no_charge_stated_policy"],
                       repeated_invoice_policy=settings["review"]["repeated_invoice_policy"])
        except (KeyError, TypeError):
            raise ContractError("run settings need reconcile.abs_tolerance_usd, review.no_charge_stated_policy and "
                                "review.repeated_invoice_policy") from None
        except ValidationError as exc:
            problems = "; ".join(f"{error['loc'][0]}: {error['msg']}"
                                 for error in exc.errors(include_input=False, include_url=False))
            raise ContractError(f"run settings are invalid: {problems}") from None


def _assign_row(row: DisputeRow, note_results: dict[str, NoteResult], policy: Policy) -> RowResult:
    repeated = "repeated_invoice" in row.flags
    common: dict[str, Any] = dict(row_id=row.row_id, shipment=row.shipment, invoice=row.invoice, carrier=row.carrier,
                                  status=row.status, reason=row.reason, disputed=row.disputed, repeated=repeated, note=row.note)
    if not row.note.strip():
        return RowResult(**common, outcome="no_charge_stated", outcome_reason="empty_note")
    result = note_results.get(fingerprint(row.note))
    if result is None:
        raise ContractError(f"row {row.row_id}: its note has no result, so the row cannot get an outcome")
    common.update(note_id=result.note_id, fingerprint=result.fingerprint)
    if result.status == "review":
        return RowResult(**common, outcome="review", outcome_reason=result.review_reason)
    if result.no_charge_stated:
        outcome = "review" if policy.no_charge_stated_policy == "review" else "no_charge_stated"
        return RowResult(**common, outcome=outcome, outcome_reason="no_charge_in_note")

    items_total = sum((item.amount for item in result.items if item.line_type != "already_paid"), _ZERO)
    already_paid_total = sum((item.amount for item in result.items if item.line_type == "already_paid"), _ZERO)
    difference = row.disputed - (items_total - already_paid_total)
    if abs(difference) > policy.abs_tolerance_usd:
        outcome, reason = "discrepancy", "does_not_add_up"
    elif repeated and policy.repeated_invoice_policy == "flag_discrepancy":
        outcome, reason = "discrepancy", "repeated_invoice"
    else:
        outcome, reason = "verified", "adds_up"
    return RowResult(**common, items_total=items_total, already_paid_total=already_paid_total, difference=difference,
                     outcome=outcome, outcome_reason=reason, item_count=len(result.items))


def assign_rows(rows: list[DisputeRow], note_results: dict[str, NoteResult], policy: Policy) -> list[RowResult]:
    """One outcome per row, in the rows' order, each row reconciled against its own disputed amount."""
    return [_assign_row(row, note_results, policy) for row in rows]
