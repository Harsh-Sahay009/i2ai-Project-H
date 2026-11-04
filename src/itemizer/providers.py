"""The model registry and one provider interface (ADR 0014). A new model is one entry in config/models.yaml.

A new API family is one adapter class plus one line in ADAPTERS. Its `wire_sample` lets the shared contract test in
tests/test_providers.py drive it with no new test code.

API keys stay out of output: errors from a provider carry a status or a class name, never its message or `__cause__`,
because those can quote the request, which holds a note and may hold a key.
"""
from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Protocol, runtime_checkable

import yaml
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, ValidationError, field_validator

from .bootstrap.data import ContractError

_MILLION = Decimal(1_000_000)
_HTTP_TIMEOUT_SECONDS = 600
_FALLBACK_BETA = "server-side-fallback-2026-07-01"
# A reply that is not the shape its API documents. Read errors never reach the caller as they are.
_UNREADABLE = (KeyError, IndexError, TypeError, AttributeError, ValueError)
_TRY_AGAIN = (429, 500, 502, 503, 504)


class _ProviderFailure(Exception):
    """`usage` is what the failed call used, when the provider said so. A cut-off or a refusal still costs money."""

    def __init__(self, message: str, usage: Completion | None = None):
        super().__init__(message)
        self.usage = usage


class ProviderError(_ProviderFailure):
    """The call failed. The note goes to Review as `provider_unavailable`."""


class ProviderRefused(_ProviderFailure):
    """The model declined. It is not a ProviderError, because the note goes to Review for a different reason."""


class ModelSpec(BaseModel):
    """One registry entry. It names the variable holding a key and never holds the key, so a manifest can record it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    provider: str
    model: str
    api_key_env: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    base_url: str | None = None
    effort: str | None = None
    refusal_fallback: bool
    max_tokens: int = Field(default=16000, gt=0)
    temperature: float | None = 0  # sent by the HTTP adapters. Set it to null for a model that refuses one, as Kimi K3 refuses 0
    input_usd_per_mtok: Decimal = Field(ge=0)
    output_usd_per_mtok: Decimal = Field(ge=0)
    cache_read_usd_per_mtok: Decimal = Field(ge=0)
    cache_write_usd_per_mtok: Decimal = Field(ge=0)

    @field_validator("provider")
    @classmethod
    def _known_provider(cls, value: str) -> str:
        if value not in ADAPTERS:
            raise ValueError(f"provider must be one of {', '.join(sorted(ADAPTERS))}")
        return value


class Completion(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    input_tokens: NonNegativeInt
    output_tokens: NonNegativeInt
    cache_read_tokens: NonNegativeInt = 0
    cache_write_tokens: NonNegativeInt = 0
    stop_reason: str | None = None
    latency_ms: NonNegativeInt = 0


@runtime_checkable
class Provider(Protocol):
    spec: ModelSpec

    def complete(self, system: str, user: str, schema: dict) -> Completion: ...


@dataclass(frozen=True)
class WireSample:
    """What one API really answers, so the shared contract test can drive any adapter."""

    ok: Any  # a good reply
    expected: Completion  # what `ok` must become, with latency_ms 0
    schema_sent: Callable[[tuple, dict], dict]  # finds the schema in the (args, kwargs) sent, in the API's own form
    refusals: tuple = ()  # replies that must raise ProviderRefused, where the API has refusals
    failures: tuple = ()  # replies that must raise ProviderError
    errors: tuple = ()  # exceptions from the client or transport that must become ProviderError


def load_models(path: Path) -> tuple[dict[str, ModelSpec], str]:
    """The registry's entries and its default name. Error messages name fields, never the values found in them."""
    if not path.exists():
        raise ContractError(f"model registry not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        raise ContractError(f"{path.name} is not valid YAML") from None
    entries = raw.get("models") if isinstance(raw, dict) else None
    if not entries or not isinstance(entries, dict):
        raise ContractError(f"{path.name} lists no models")
    models: dict[str, ModelSpec] = {}
    for name, entry in entries.items():
        if not isinstance(entry, dict):
            raise ContractError(f"{path.name}: model {name} is not a set of fields")
        try:
            models[name] = ModelSpec.model_validate({**entry, "name": name})
        except ValidationError as exc:
            problems = "; ".join(f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                                 for error in exc.errors(include_input=False, include_url=False))
            raise ContractError(f"{path.name}: model {name} is invalid: {problems}") from None
    default = raw.get("default")
    if not isinstance(default, str) or default not in models:
        raise ContractError(f"{path.name}: default must name an entry; entries are {', '.join(sorted(models))}")
    return models, default


def _read_dotenv(path: Path) -> dict[str, str]:
    try:
        # A decode error would quote a byte of the file, so bad bytes are replaced rather than raised.
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    found: dict[str, str] = {}
    for line in lines:
        key, separator, value = line.strip().removeprefix("export ").partition("=")
        if not separator or key.startswith("#"):
            continue
        value = value.strip()
        if value[:1] in ("'", '"') and value.count(value[0]) >= 2:
            value = value[1:value.index(value[0], 1)]
        else:
            value = value.split(" #", 1)[0].rstrip()
        found[key.strip()] = value
    return found


def load_secret(name: str, project_root: Path) -> str:
    """The environment first, then `.env` in the project root. The value is never logged, printed or put in an error."""
    value = os.environ.get(name) or _read_dotenv(project_root / ".env").get(name)
    if not value:
        raise ContractError(f"{name} is not set: put it in the environment or in .env in the project root")
    return value


def cost_usd(spec: ModelSpec, completion: Completion) -> Decimal:
    """Unrounded. Cached tokens are reported apart from input tokens, so each token is priced once."""
    return (completion.input_tokens * spec.input_usd_per_mtok
            + completion.output_tokens * spec.output_usd_per_mtok
            + completion.cache_read_tokens * spec.cache_read_usd_per_mtok
            + completion.cache_write_tokens * spec.cache_write_usd_per_mtok) / _MILLION


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


class AnthropicProvider:
    def __init__(self, spec: ModelSpec, client: Any = None, project_root: Path | None = None):
        self.spec = spec
        try:
            import anthropic  # installed with the `llm` extra
        except ImportError:
            raise ContractError("the anthropic package is not installed; install the `llm` extra") from None
        self._sdk = anthropic
        if client is not None:
            self._client = client
        elif spec.api_key_env:
            self._client = anthropic.Anthropic(api_key=load_secret(spec.api_key_env, project_root or Path.cwd()))
        else:
            raise ContractError(f"model {spec.name} needs api_key_env in the registry")

    def complete(self, system: str, user: str, schema: dict) -> Completion:
        output_config: dict[str, Any] = {"format": {"type": "json_schema", "schema": schema}}
        if self.spec.effort:
            output_config["effort"] = self.spec.effort
        fallback = {"betas": [_FALLBACK_BETA], "fallbacks": "default"} if self.spec.refusal_fallback else {}
        started = time.monotonic()
        try:
            reply = self._client.beta.messages.create(
                model=self.spec.model,
                max_tokens=self.spec.max_tokens,
                # The marker sits on the shared prompt: each note is unique, so a marker after it would never be read back.
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
                output_config=output_config,
                **fallback,
            )
        except self._sdk.RateLimitError:
            raise ProviderError(f"{self.spec.name}: rate limited after the client's retries") from None
        except self._sdk.APIStatusError as exc:
            raise ProviderError(f"{self.spec.name}: the API answered with status {exc.status_code}") from None
        except self._sdk.APIConnectionError:
            raise ProviderError(f"{self.spec.name}: could not reach the API") from None
        except self._sdk.AnthropicError as exc:
            raise ProviderError(f"{self.spec.name}: the call failed ({type(exc).__name__})") from None
        except ValueError:  # raised before any call, and every note would hit it, so it stops the run
            raise ContractError(f"model {self.spec.name}: the SDK refuses max_tokens {self.spec.max_tokens} without "
                                "streaming; lower it in the registry") from None
        try:
            return self._read(reply, _elapsed_ms(started))
        except _UNREADABLE:
            raise ProviderError(f"{self.spec.name}: the reply could not be read") from None

    def _read(self, reply: Any, latency_ms: int) -> Completion:
        used = self._used(reply, latency_ms)
        if reply.stop_reason == "refusal":  # checked first: a refused reply can be empty or cut short
            raise ProviderRefused(f"{self.spec.name}: the model declined this note", usage=used)
        if reply.stop_reason == "max_tokens":
            raise ProviderError(f"{self.spec.name}: the answer was cut off at the token limit", usage=used)
        text = next((block.text for block in reply.content if block.type == "text"), None)
        if text is None:
            raise ProviderError(f"{self.spec.name}: the reply holds no text", usage=used)
        if used is None:  # without usage a call would look free, and the budget could not stop a run
            raise ProviderError(f"{self.spec.name}: the reply holds no usage")
        return used.model_copy(update={"text": text})

    @staticmethod
    def _used(reply: Any, latency_ms: int) -> Completion | None:
        """Tokens across every attempt: when a refusal fallback runs, top-level usage covers only the last one.

        All attempts are priced at this entry's rates, so a run that fell back is an estimate.
        """
        usage = getattr(reply, "usage", None)
        if usage is None:
            return None
        attempts = getattr(usage, "iterations", None) or [usage]

        def total(field: str) -> int:
            return sum(getattr(attempt, field, 0) or 0 for attempt in attempts)

        return Completion(text="", input_tokens=total("input_tokens"), output_tokens=total("output_tokens"),
                          cache_read_tokens=total("cache_read_input_tokens"),
                          cache_write_tokens=total("cache_creation_input_tokens"),
                          stop_reason=reply.stop_reason, latency_ms=latency_ms)

    @staticmethod
    def wire_sample() -> WireSample:
        import anthropic

        usage = SimpleNamespace(input_tokens=11, output_tokens=7, cache_read_input_tokens=3, cache_creation_input_tokens=2)
        text = SimpleNamespace(type="text", text="{}")
        thinking = SimpleNamespace(type="thinking", thinking="")

        def reply(stop_reason: str, *content: Any) -> SimpleNamespace:
            return SimpleNamespace(stop_reason=stop_reason, content=list(content), usage=usage)

        return WireSample(
            ok=reply("end_turn", thinking, text),
            expected=Completion(text="{}", input_tokens=11, output_tokens=7, cache_read_tokens=3, cache_write_tokens=2,
                                stop_reason="end_turn"),
            schema_sent=lambda args, kwargs: kwargs["output_config"]["format"]["schema"],
            refusals=(reply("refusal"), reply("refusal", text)),
            failures=(reply("max_tokens", text), reply("end_turn", thinking), SimpleNamespace(stop_reason="end_turn")),
            errors=(anthropic.APIConnectionError(request=None), anthropic.AnthropicError("quotes the request")),
        )


def _post_json(url: str, headers: dict[str, str], body: dict) -> dict:
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


class _HttpProvider:
    """The call and its errors, for APIs reached with the standard library. `client` is a transport(url, headers, body).

    A rate limit, a server error or a dropped connection is tried again. A real server limits a run of 700 calls.
    """

    path = ""
    attempts = 4
    first_delay_seconds = 1.0
    longest_delay_seconds = 60.0

    def __init__(self, spec: ModelSpec, client: Any = None, project_root: Path | None = None):
        if not spec.base_url:
            raise ContractError(f"model {spec.name} needs base_url in the registry")
        self.spec = spec
        self._transport = client if client is not None else _post_json
        self._url = spec.base_url.rstrip("/") + self.path
        self._headers = self._auth(project_root or Path.cwd())

    def _auth(self, project_root: Path) -> dict[str, str]:
        return {}

    def _body(self, system: str, user: str, schema: dict) -> dict:
        raise NotImplementedError

    def _read(self, reply: Any, latency_ms: int) -> Completion:
        raise NotImplementedError

    def _send(self, body: dict) -> Any:
        for attempt in range(self.attempts):
            last = attempt == self.attempts - 1
            delay = self.first_delay_seconds * 2 ** attempt
            try:
                return self._transport(self._url, self._headers, body)
            except urllib.error.HTTPError as exc:
                waited = exc.headers.get("Retry-After") if exc.headers else None
                code = exc.code
                exc.close()
                if code not in _TRY_AGAIN or last:
                    raise ProviderError(f"{self.spec.name}: the server answered with status {code}") from None
                if waited and waited.isdigit():
                    delay = float(waited)
            except urllib.error.URLError as exc:  # the connection dropped, so nothing was answered
                if last:
                    raise ProviderError(f"{self.spec.name}: the request failed ({type(exc).__name__})") from None
            except (OSError, ValueError, http.client.HTTPException) as exc:  # a malformed reply must not stop the whole run
                raise ProviderError(f"{self.spec.name}: the request failed ({type(exc).__name__})") from None
            time.sleep(min(delay, self.longest_delay_seconds))
        raise ProviderError(f"{self.spec.name}: the request failed")  # reached only if attempts is set below 1

    def complete(self, system: str, user: str, schema: dict) -> Completion:
        started = time.monotonic()
        reply = self._send(self._body(system, user, schema))
        try:
            return self._read(reply, _elapsed_ms(started))
        except _UNREADABLE:
            raise ProviderError(f"{self.spec.name}: the reply could not be read") from None


def _chat_messages(system: str, user: str) -> list[dict]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


class OllamaProvider(_HttpProvider):
    path = "/api/chat"

    def _body(self, system: str, user: str, schema: dict) -> dict:
        options: dict[str, Any] = {"num_predict": self.spec.max_tokens}
        if self.spec.temperature is not None:
            options["temperature"] = self.spec.temperature
        return {"model": self.spec.model, "messages": _chat_messages(system, user), "stream": False, "format": schema, "options": options}

    def _read(self, reply: Any, latency_ms: int) -> Completion:
        if reply.get("error"):
            raise ProviderError(f"{self.spec.name}: the server reported an error")
        if reply.get("done_reason") == "length":
            raise ProviderError(f"{self.spec.name}: the answer was cut off at the token limit")
        # Ollama leaves out prompt_eval_count when it reuses a prompt it has already evaluated.
        return Completion(text=reply["message"]["content"], input_tokens=reply.get("prompt_eval_count", 0),
                          output_tokens=reply["eval_count"], stop_reason=reply.get("done_reason"), latency_ms=latency_ms)

    @staticmethod
    def wire_sample() -> WireSample:
        def reply(done_reason: str = "stop") -> dict:
            return {"message": {"role": "assistant", "content": "{}"}, "done_reason": done_reason,
                    "prompt_eval_count": 11, "eval_count": 7}

        return WireSample(
            ok=reply(),
            expected=Completion(text="{}", input_tokens=11, output_tokens=7, stop_reason="stop"),
            schema_sent=lambda args, kwargs: args[2]["format"],
            failures=(reply("length"), {"error": "model not found"}, {"message": None}, {"message": {"content": 5}, "eval_count": 1}, []),
            errors=(OSError("quotes the request"), ValueError("quotes the request"),
                    urllib.error.HTTPError("http://fake.invalid", 500, "quotes the request", None, None)),
        )


class OpenAICompatibleProvider(_HttpProvider):
    path = "/chat/completions"

    def _auth(self, project_root: Path) -> dict[str, str]:
        if not self.spec.api_key_env:
            return {}
        return {"Authorization": f"Bearer {load_secret(self.spec.api_key_env, project_root)}"}

    def _body(self, system: str, user: str, schema: dict) -> dict:
        body: dict[str, Any] = {"model": self.spec.model, "messages": _chat_messages(system, user),
                                "response_format": {"type": "json_schema",
                                                    "json_schema": {"name": "note_answer", "strict": True, "schema": schema}},
                                "max_tokens": self.spec.max_tokens}
        if self.spec.temperature is not None:
            body["temperature"] = self.spec.temperature
        if self.spec.effort:
            body["reasoning_effort"] = self.spec.effort
        return body

    def _read(self, reply: Any, latency_ms: int) -> Completion:
        if reply.get("error"):
            raise ProviderError(f"{self.spec.name}: the server reported an error")
        choice = reply["choices"][0]
        message, finish_reason = choice["message"], choice.get("finish_reason")
        reported = reply.get("usage") or {}
        details = reported.get("prompt_tokens_details") or {}
        cached = reported.get("cached_tokens") or details.get("cached_tokens") or 0
        written = details.get("cache_write_tokens") or 0
        used = Completion(text="", input_tokens=reported.get("prompt_tokens", 0) - cached - written, output_tokens=reported.get("completion_tokens", 0),
                          cache_read_tokens=cached, cache_write_tokens=written, stop_reason=finish_reason, latency_ms=latency_ms)
        if message.get("refusal") or finish_reason == "content_filter":
            raise ProviderRefused(f"{self.spec.name}: the model declined this note", usage=used)
        if finish_reason == "length":
            raise ProviderError(f"{self.spec.name}: the answer was cut off at the token limit", usage=used)
        reply["usage"]["prompt_tokens"], reply["usage"]["completion_tokens"]  # required: without them a call would look free and the budget could not stop a run
        return Completion.model_validate({**used.model_dump(), "text": message["content"]})  # validated, because a reply can hold no text

    @staticmethod
    def wire_sample() -> WireSample:
        def reply(finish_reason: str = "stop", **message: Any) -> dict:
            return {"choices": [{"message": {"role": "assistant", "content": "{}", **message}, "finish_reason": finish_reason}],
                    "usage": {"prompt_tokens": 11, "completion_tokens": 7}}

        return WireSample(
            ok=reply(),
            expected=Completion(text="{}", input_tokens=11, output_tokens=7, stop_reason="stop"),
            schema_sent=lambda args, kwargs: args[2]["response_format"]["json_schema"]["schema"],
            refusals=(reply(refusal="declined", content=None), reply("content_filter")),
            failures=(reply("length"), {"error": {"message": "bad key"}}, {"choices": []},
                      {"choices": [{"message": {"content": "{}"}}]}, reply(content=None), []),
            errors=(OSError("quotes the request"), ValueError("quotes the request"),
                    urllib.error.HTTPError("http://fake.invalid", 401, "quotes the request", None, None)),
        )


ADAPTERS: dict[str, type] = {
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "openai_compatible": OpenAICompatibleProvider,
}


def get_provider(spec: ModelSpec, client: Any = None, project_root: Path | None = None) -> Provider:
    """`client` is the adapter's SDK client or HTTP transport. `project_root` is where `.env` is, by default the working folder."""
    return ADAPTERS[spec.provider](spec, client, project_root)
