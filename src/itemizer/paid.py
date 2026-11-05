"""Reserve worst-case cost before each paid attempt; share the allowance across restarts.

Only the pinned direct OpenAI model/rates below are supported. The context-window charge is
intentionally conservative. Unmetered failures retain their reservation rather than looking free.
"""
from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time

from .bootstrap.data import ContractError
from .providers import ModelSpec, ProviderError, _post_json

MODEL = 'gpt-5.4-mini-2026-03-17'
BASE_URL = 'https://api.openai.com/v1'
CONTEXT_TOKENS = 400000
RATES = {'input': Decimal('0.75'), 'output': Decimal('4.50'),
         'cache_read': Decimal('0.075'), 'cache_write': Decimal('0')}
MILLION = Decimal(1000000)


class SpendingLimitExceeded(ProviderError):
    """The next full reservation would exceed the authorized evaluation allowance."""


def _money(value) -> Decimal:
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            raise ValueError
        return amount
    except (ValueError, InvalidOperation):
        raise ContractError('invalid paid-inference allowance or ledger amount') from None


def _save(path: Path, state: dict) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(descriptor, 'w') as handle:
            json.dump(state, handle, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


class CappedOpenAITransport:
    """A secret-free ledger and a callable compatible with the existing HTTP adapter."""

    def __init__(self, spec: ModelSpec, ledger: Path, limit, transport=None):
        self.spec, self.path, self.limit = spec, Path(ledger), _money(limit)
        self.transport = transport or _post_json
        rates = {'input': spec.input_usd_per_mtok, 'output': spec.output_usd_per_mtok,
                 'cache_read': spec.cache_read_usd_per_mtok, 'cache_write': spec.cache_write_usd_per_mtok}
        if (spec.model != MODEL or spec.base_url != BASE_URL or rates != RATES
                or spec.max_tokens > 128000 or not 0 < self.limit <= 5):
            raise ContractError('paid transport requires the pinned OpenAI model/rates and an allowance up to $5')
        self.identity = {'version': 1, 'model': MODEL, 'base_url': BASE_URL,
                         'rates': {k: str(v) for k, v in RATES.items()},
                         'context_tokens': CONTEXT_TOKENS, 'max_output_tokens': spec.max_tokens,
                         'limit_usd': str(self.limit)}
        self.reservation = (CONTEXT_TOKENS * RATES['input'] + spec.max_tokens * RATES['output']) / MILLION

    @contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _load(self) -> dict:
        if not self.path.exists():
            return {'identity': self.identity, 'calls': [], 'blocked_by_limit': False}
        try:
            state = json.loads(self.path.read_text())
            if state['identity'] != self.identity or not isinstance(state['calls'], list):
                raise ValueError
            for call in state['calls']:
                if (call['status'] not in {'reserved', 'unknown', 'settled'}
                        or _money(call['reservation_usd']) != self.reservation
                        or _money(call['accounted_usd']) > self.reservation
                        or (call['status'] != 'settled' and _money(call['accounted_usd']) != self.reservation)):
                    raise ValueError
            if self._total(state) > self.limit:
                raise ValueError
            return state
        except (OSError, ValueError, TypeError, KeyError):
            raise ContractError('paid-inference ledger is unreadable or its identity/totals changed') from None

    @staticmethod
    def _total(state: dict) -> Decimal:
        return sum((_money(c['accounted_usd']) for c in state['calls']), Decimal(0))

    def summary(self) -> dict:
        with self._locked():
            state = self._load()
            settled = sum((_money(c['accounted_usd']) for c in state['calls']
                           if c['status'] == 'settled'), Decimal(0))
            total = self._total(state)
            return {'limit_usd': str(self.limit), 'settled_usd': str(settled),
                    'unsettled_usd': str(total - settled), 'accounted_usd': str(total),
                    'requests': len(state['calls']), 'blocked_by_limit': state['blocked_by_limit']}

    def _usage_cost(self, reply: dict, maximum_output: int) -> Decimal:
        try:
            usage = reply['usage']
            prompt, output = usage['prompt_tokens'], usage['completion_tokens']
            cached = (usage.get('prompt_tokens_details') or {}).get('cached_tokens', 0)
            if (any(type(v) is not int or v < 0 for v in [prompt, output, cached])
                    or prompt > CONTEXT_TOKENS or output > maximum_output or cached > prompt):
                raise ValueError
            return ((prompt - cached) * RATES['input'] + cached * RATES['cache_read']
                    + output * RATES['output']) / MILLION
        except (TypeError, KeyError, ValueError, AttributeError):
            raise ProviderError('paid response has no usable bounded token usage; reservation retained') from None

    def __call__(self, url: str, headers: dict, body: dict) -> dict:
        if (url != BASE_URL + '/chat/completions' or body.get('model') != MODEL
                or body.get('max_tokens') != self.spec.max_tokens or body.get('stream')
                or body.get('n', 1) != 1):
            raise ContractError('paid request differs from the bounded single-completion protocol')
        wire = {**body, 'max_completion_tokens': self.spec.max_tokens,
                'service_tier': 'default', 'store': False}
        wire.pop('max_tokens')
        reserve = self.reservation
        with self._locked():
            state = self._load()
            if self._total(state) + reserve > self.limit:
                state['blocked_by_limit'] = True
                _save(self.path, state)
                raise SpendingLimitExceeded('authorized paid-inference allowance cannot cover another full reservation')
            call = {'time_unix': time.time(), 'reservation_usd': str(reserve),
                    'accounted_usd': str(reserve), 'status': 'reserved'}
            state['calls'].append(call)
            _save(self.path, state)  # durable before any network call; crashes keep the reservation
            try:
                reply = self.transport(url, headers, wire)
                actual = self._usage_cost(reply, self.spec.max_tokens)
            except Exception:
                call['status'] = 'unknown'
                _save(self.path, state)
                raise
            call.update(accounted_usd=str(actual), status='settled')
            _save(self.path, state)
            return reply


def authorized_transport(root: Path, spec: ModelSpec, requested_budget, dataset_sha256: str) -> CappedOpenAITransport:
    """One dataset-scoped user authorization and one ledger across all evaluation scopes."""
    folder = root / 'data/evaluation'
    try:
        authorization = json.loads((folder / 'openai_spending_authorization.json').read_text())
        limit = _money(authorization['limit_usd'])
        if (authorization['status'] != 'user_authorized' or authorization['dataset_sha256'] != dataset_sha256
                or not 0 < _money(requested_budget) <= limit):
            raise ValueError
    except (OSError, ValueError, TypeError, KeyError):
        raise ContractError('paid inference needs dataset-scoped spending authorization covering the requested budget') from None
    ledger = folder / 'openai_spending.json'
    if not ledger.exists() and any(folder.glob(f'*/cache/{spec.name}/*.json')):
        raise ContractError('paid cache exists without its spending ledger; do not reset the allowance')
    paid = CappedOpenAITransport(spec, ledger, limit)
    paid.summary()  # validate existing history before preparing or executing another scope
    return paid
