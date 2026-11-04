"""Tests per scenario for the model registry and providers. No network and no real keys: every client is a fake."""
from __future__ import annotations

import http.client
import inspect
import json
import shutil
import traceback
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx2
import pytest
import yaml
from anthropic.resources.beta.messages import Messages

from itemizer.bootstrap.data import ContractError
from itemizer.grammar import answer_schema
from itemizer.providers import (
    ADAPTERS, AnthropicProvider, Completion, ModelSpec, OllamaProvider, OpenAICompatibleProvider, Provider, ProviderError,
    ProviderRefused, WireSample, _post_json, cost_usd, get_provider, load_models, load_secret,
)

REAL_REGISTRY = Path(__file__).resolve().parents[1] / "config" / "models.yaml"
SECRET = "fake-secret-value-do-not-print"
KEY_VAR = "ITEMIZER_TEST_KEY"
SYSTEM = "INVENTED-SYSTEM-PROMPT"
USER = "INVENTED-NOTE-TEXT LUMPER $85.00"
SCHEMA = answer_schema(["lumper", "tax"])
PRICES = {"input_usd_per_mtok": "4.00", "output_usd_per_mtok": "20.00", "cache_read_usd_per_mtok": "0.20", "cache_write_usd_per_mtok": "5.00"}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """No test can reach the project's real .env: the working folder is empty, and the only key is a fake one."""
    monkeypatch.chdir(tmp_path)
    for name in ("CLAUDE_API_KEY", "OTHER_API_KEY", "ANTHROPIC_API_KEY", "MOONSHOT_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(KEY_VAR, SECRET)


class FakeWire:
    """Stands in for any SDK client or HTTP transport: any attribute chain ends in one recorded call."""

    def __init__(self, answer=None):
        self.answer = answer
        self.calls: list[tuple[tuple, dict]] = []

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return self

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


def make_spec(provider: str = "anthropic", **changes) -> ModelSpec:
    return ModelSpec(**{"name": "test-model", "provider": provider, "model": "model-id", "api_key_env": KEY_VAR,
                        "base_url": "http://fake.invalid/v1/", "refusal_fallback": False, **PRICES, **changes})


def everything_printed(error: BaseException) -> str:
    return "".join(traceback.format_exception(error))


def assert_clean(error: BaseException) -> None:
    printed = everything_printed(error)
    for private in (SECRET, USER, SYSTEM, "quotes the request"):
        assert private not in printed


# ---- the shared contract: every adapter in ADAPTERS, with no test code of its own
def check_contract(family: str) -> None:
    sample: WireSample = ADAPTERS[family].wire_sample()
    spec = make_spec(family)
    wire = FakeWire(sample.ok)
    provider = get_provider(spec, client=wire)
    assert isinstance(provider, Provider) and provider.spec == spec

    completion = provider.complete(SYSTEM, USER, SCHEMA)
    assert isinstance(completion, Completion) and completion.latency_ms >= 0
    assert completion.model_copy(update={"latency_ms": 0}) == sample.expected
    assert len(wire.calls) == 1, "a provider makes one call; only its client may retry"
    args, kwargs = wire.calls[0]
    assert sample.schema_sent(args, kwargs) == SCHEMA
    sent = repr(wire.calls[0])
    assert SYSTEM in sent and USER in sent and spec.model in sent

    for reply in sample.refusals:
        wire.answer = reply
        with pytest.raises(ProviderRefused) as caught:
            provider.complete(SYSTEM, USER, SCHEMA)
        assert_clean(caught.value)
    for reply_or_error in sample.failures + sample.errors:
        wire.answer = reply_or_error
        with pytest.raises(ProviderError) as caught:
            provider.complete(SYSTEM, USER, SCHEMA)
        assert_clean(caught.value)
    assert SECRET not in repr(provider) and SECRET not in spec.model_dump_json()


@pytest.mark.parametrize("family", sorted(ADAPTERS))
def test_every_adapter_keeps_the_contract(family):
    check_contract(family)


class _ToyFamily:
    """An API family the code has never seen, written the way the design says: one class and one line in ADAPTERS."""

    def __init__(self, spec, client=None, project_root=None):
        self.spec, self._send = spec, client

    def complete(self, system, user, schema):
        reply = self._send(self.spec.model, system, user, schema)
        if reply == "declined":
            raise ProviderRefused("declined")
        if reply == "broken":
            raise ProviderError("broken")
        return Completion(text=reply, input_tokens=1, output_tokens=2)

    @staticmethod
    def wire_sample():
        return WireSample(ok="{}", expected=Completion(text="{}", input_tokens=1, output_tokens=2),
                          schema_sent=lambda args, kwargs: args[3], refusals=("declined",), failures=("broken",))


def test_a_new_api_family_runs_the_same_contract_with_no_new_test_code(monkeypatch):
    monkeypatch.setitem(ADAPTERS, "toy", _ToyFamily)
    check_contract("toy")
    assert make_spec("toy").provider == "toy"


def test_the_contract_catches_an_adapter_that_breaks_it(monkeypatch):
    class IgnoresRefusals(_ToyFamily):
        def complete(self, system, user, schema):
            self._send(self.spec.model, system, user, schema)
            return Completion(text="{}", input_tokens=1, output_tokens=2)

    monkeypatch.setitem(ADAPTERS, "ignores_refusals", IgnoresRefusals)
    with pytest.raises(pytest.fail.Exception, match="DID NOT RAISE"):
        check_contract("ignores_refusals")


# ---- Anthropic: the exact call, against a fake client
def _anthropic_call(**changes) -> dict:
    wire = FakeWire(AnthropicProvider.wire_sample().ok)
    get_provider(make_spec(**changes), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert wire.calls[0][0] == ()
    return wire.calls[0][1]


def test_anthropic_call_arguments_are_exactly_the_designs():
    assert _anthropic_call(effort="medium") == {
        "model": "model-id",
        "max_tokens": 16000,
        "system": [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": USER}],
        "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}, "effort": "medium"},
    }


def test_anthropic_refusal_fallback_adds_only_the_beta_and_the_fallback():
    without = _anthropic_call(effort="medium")
    assert _anthropic_call(effort="medium", refusal_fallback=True) == {
        **without, "betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}


def test_anthropic_effort_is_left_out_when_the_entry_has_none():
    assert _anthropic_call()["output_config"] == {"format": {"type": "json_schema", "schema": SCHEMA}}


def test_anthropic_max_tokens_comes_from_the_entry():
    assert _anthropic_call(max_tokens=2000)["max_tokens"] == 2000


@pytest.mark.parametrize("fallback", [False, True])
def test_anthropic_sends_no_sampling_or_thinking_settings(fallback):
    sent = _anthropic_call(effort="high", refusal_fallback=fallback)
    assert not {"temperature", "top_p", "top_k", "thinking", "stream", "tools", "tool_choice"} & set(sent)


@pytest.mark.parametrize("fallback", [False, True])
def test_the_installed_sdk_accepts_those_arguments(fallback):
    inspect.signature(Messages.create).bind(None, **_anthropic_call(effort="high", refusal_fallback=fallback))


def test_anthropic_builds_its_client_with_the_key_only_so_default_retries_stay_on(monkeypatch):
    built = []
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kwargs: built.append(kwargs) or FakeWire())
    get_provider(make_spec())
    assert built == [{"api_key": SECRET}]


def test_anthropic_reads_its_key_from_dotenv_in_the_project_root(monkeypatch, tmp_path):
    built = []
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kwargs: built.append(kwargs) or FakeWire())
    monkeypatch.delenv(KEY_VAR)
    root = tmp_path / "project"
    root.mkdir()
    (root / ".env").write_text(f"{KEY_VAR}=from-dotenv\n")
    get_provider(make_spec(), project_root=root)
    assert built == [{"api_key": "from-dotenv"}]


def test_anthropic_without_a_key_variable_stops_before_any_call():
    with pytest.raises(ContractError, match="test-model needs api_key_env"):
        get_provider(make_spec(api_key_env=None))


def test_a_missing_key_stops_before_any_call(monkeypatch):
    monkeypatch.delenv(KEY_VAR)
    for family in ("anthropic", "openai_compatible"):
        with pytest.raises(ContractError, match=KEY_VAR):
            get_provider(make_spec(family))


def test_anthropic_text_is_the_first_text_block_after_any_thinking():
    block = lambda kind, **fields: SimpleNamespace(type=kind, **fields)
    usage = SimpleNamespace(input_tokens=1, output_tokens=2, cache_read_input_tokens=None, cache_creation_input_tokens=None)
    reply = SimpleNamespace(stop_reason="end_turn", usage=usage, content=[
        block("thinking", thinking=""), block("text", text="first"), block("text", text="second")])
    completion = get_provider(make_spec(), client=FakeWire(reply)).complete(SYSTEM, USER, SCHEMA)
    assert completion.text == "first"
    assert (completion.cache_read_tokens, completion.cache_write_tokens) == (0, 0)


# ---- Anthropic: the real SDK over a fake HTTP transport, so its real errors and reply types are what the adapter sees
def _real_client(handler) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=SECRET, max_retries=0, http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)))


MESSAGE = {"id": "msg_1", "type": "message", "role": "assistant", "model": "model-id", "stop_reason": "end_turn", "stop_sequence": None,
           "content": [{"type": "thinking", "thinking": "", "signature": "s"}, {"type": "text", "text": "{\"items\": []}"}],
           "usage": {"input_tokens": 11, "output_tokens": 7, "cache_read_input_tokens": 3, "cache_creation_input_tokens": 2}}


def test_the_real_sdk_sends_the_call_and_the_adapter_reads_its_reply():
    seen = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json=MESSAGE)

    completion = get_provider(make_spec(effort="medium", refusal_fallback=True), client=_real_client(handler)).complete(SYSTEM, USER, SCHEMA)
    assert (completion.text, completion.input_tokens, completion.output_tokens) == ("{\"items\": []}", 11, 7)
    assert (completion.cache_read_tokens, completion.cache_write_tokens, completion.stop_reason) == (3, 2, "end_turn")
    assert "server-side-fallback-2026-07-01" in seen[0].headers["anthropic-beta"]
    body = json.loads(seen[0].content)
    assert "cache_control" not in body and body["fallbacks"] == "default"
    assert body["system"] == [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]
    assert body["output_config"] == {"format": {"type": "json_schema", "schema": SCHEMA}, "effort": "medium"}
    assert not {"temperature", "top_p", "top_k", "thinking"} & set(body)


@pytest.mark.parametrize("status, message", [(429, "rate limited"), (500, "status 500"), (401, "status 401"), (400, "status 400"), (529, "status 529")])
def test_real_sdk_status_errors_become_provider_errors(status, message):
    def handler(request):  # an API error can quote the request, and none of that may come through
        return httpx2.Response(status, json={"type": "error", "error": {"type": "x", "message": f"quotes the request {USER} {SECRET}"}})

    with pytest.raises(ProviderError, match=message) as caught:
        get_provider(make_spec(), client=_real_client(handler)).complete(SYSTEM, USER, SCHEMA)
    assert_clean(caught.value)


@pytest.mark.parametrize("raised", [httpx2.ConnectError("quotes the request"), httpx2.ReadTimeout("quotes the request")], ids=["connection", "timeout"])
def test_real_sdk_connection_errors_become_provider_errors(raised):
    def handler(request):
        raise raised

    with pytest.raises(ProviderError, match="could not reach") as caught:
        get_provider(make_spec(), client=_real_client(handler)).complete(SYSTEM, USER, SCHEMA)
    assert_clean(caught.value)


def test_a_max_tokens_the_sdk_refuses_stops_the_run_with_a_plain_message():
    calls = []
    client = _real_client(lambda request: calls.append(request) or httpx2.Response(200, json=MESSAGE))
    with pytest.raises(ContractError, match="max_tokens 128000") as caught:
        get_provider(make_spec(max_tokens=128000), client=client).complete(SYSTEM, USER, SCHEMA)
    assert calls == []
    assert_clean(caught.value)


def test_real_sdk_refusal_with_no_content_is_a_refusal():
    reply = {**MESSAGE, "stop_reason": "refusal", "content": []}
    with pytest.raises(ProviderRefused):
        get_provider(make_spec(), client=_real_client(lambda request: httpx2.Response(200, json=reply))).complete(SYSTEM, USER, SCHEMA)


# ---- the HTTP adapters: the exact requests, and the transport
def test_ollama_request_is_exactly_the_designs():
    wire = FakeWire(OllamaProvider.wire_sample().ok)
    get_provider(make_spec("ollama", api_key_env=None, base_url="http://localhost:11434"), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert wire.calls[0] == (("http://localhost:11434/api/chat", {}, {
        "model": "model-id",
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": USER}],
        "stream": False,
        "format": SCHEMA,
        "options": {"temperature": 0, "num_predict": 16000},
    }), {})


def test_ollama_counts_no_input_tokens_when_it_reuses_an_evaluated_prompt():
    reply = {"message": {"content": "{}"}, "done_reason": "stop", "eval_count": 7}
    assert get_provider(make_spec("ollama"), client=FakeWire(reply)).complete(SYSTEM, USER, SCHEMA).input_tokens == 0


def test_openai_compatible_request_is_exactly_the_designs():
    wire = FakeWire(OpenAICompatibleProvider.wire_sample().ok)
    get_provider(make_spec("openai_compatible", base_url="https://api.example.com/v1"), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert wire.calls[0] == (("https://api.example.com/v1/chat/completions", {"Authorization": f"Bearer {SECRET}"}, {
        "model": "model-id",
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": USER}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "note_answer", "strict": True, "schema": SCHEMA}},
        "temperature": 0,
        "max_tokens": 16000,
    }), {})


def test_openai_compatible_with_no_key_variable_sends_no_token():
    wire = FakeWire(OpenAICompatibleProvider.wire_sample().ok)
    get_provider(make_spec("openai_compatible", api_key_env=None), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert wire.calls[0][0][1] == {}


@pytest.mark.parametrize("family", ["ollama", "openai_compatible"])
def test_http_adapters_need_a_base_url(family):
    with pytest.raises(ContractError, match="test-model needs base_url"):
        get_provider(make_spec(family, base_url=None), client=FakeWire())


@pytest.mark.parametrize("family", ["ollama", "openai_compatible"])
def test_http_failures_keep_the_key_and_the_note_out_of_the_error(family):
    def transport(url, headers, body):
        raise OSError(f"quotes the request {headers} {body}")

    with pytest.raises(ProviderError, match=r"failed \(OSError\)") as caught:
        get_provider(make_spec(family), client=transport).complete(SYSTEM, USER, SCHEMA)
    assert_clean(caught.value)


def test_http_status_is_reported_and_nothing_else():
    error = urllib.error.HTTPError("http://fake.invalid", 503, "quotes the request", None, None)
    with pytest.raises(ProviderError, match="status 503") as caught:
        get_provider(make_spec("ollama"), client=FakeWire(error)).complete(SYSTEM, USER, SCHEMA)
    assert_clean(caught.value)


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self._payload


def test_the_default_transport_posts_json(monkeypatch):
    seen = []

    def urlopen(request, timeout):
        seen.append((request, timeout))
        return _FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    assert _post_json("http://fake.invalid/x", {"Authorization": "Bearer k"}, {"a": 1}) == {"ok": True}
    request, timeout = seen[0]
    assert (request.full_url, request.get_method(), request.data) == ("http://fake.invalid/x", "POST", b'{"a": 1}')
    assert request.get_header("Authorization") == "Bearer k" and request.get_header("Content-type") == "application/json"
    assert timeout > 0


@pytest.mark.parametrize("family", ["ollama", "openai_compatible"])
@pytest.mark.parametrize("failure, message", [
    (urllib.error.URLError("quotes the request"), r"failed \(URLError\)"),
    (TimeoutError("quotes the request"), r"failed \(TimeoutError\)"),
    (urllib.error.HTTPError("http://fake.invalid", 500, "quotes the request", None, None), "status 500"),
    (_FakeResponse(b"<html>quotes the request</html>"), r"failed \(JSONDecodeError\)"),
    (_FakeResponse(b"[1, 2]"), "could not be read"),
], ids=["no connection", "timeout", "status", "not json", "json of another shape"])
def test_the_default_transports_failures_become_provider_errors(monkeypatch, family, failure, message):
    def urlopen(request, timeout):
        if isinstance(failure, BaseException):
            raise failure
        return failure

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    with pytest.raises(ProviderError, match=message) as caught:
        get_provider(make_spec(family)).complete(SYSTEM, USER, SCHEMA)
    assert_clean(caught.value)


# ---- secrets
def test_load_secret_reads_the_environment_first(tmp_path):
    (tmp_path / ".env").write_text(f"{KEY_VAR}=from-file\n")
    assert load_secret(KEY_VAR, tmp_path) == SECRET


def test_load_secret_falls_back_to_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv(KEY_VAR)
    (tmp_path / ".env").write_text(f"{KEY_VAR}=from-file\n")
    assert load_secret(KEY_VAR, tmp_path) == "from-file"


def test_an_empty_environment_variable_falls_back_to_dotenv(tmp_path, monkeypatch):
    monkeypatch.setenv(KEY_VAR, "")
    (tmp_path / ".env").write_text(f"{KEY_VAR}=from-file\n")
    assert load_secret(KEY_VAR, tmp_path) == "from-file"


@pytest.mark.parametrize("line, expected", [
    ("KEY=plain", "plain"),
    ("  KEY = spaced  ", "spaced"),
    ("export KEY=exported", "exported"),
    ('KEY="double quoted"', "double quoted"),
    ("KEY='single quoted'", "single quoted"),
    ('KEY="has # inside"', "has # inside"),
    ("KEY=value # a comment", "value"),
    ("KEY=has=equals", "has=equals"),
    ("KEY=has#hash", "has#hash"),
])
def test_dotenv_lines_are_read_with_the_standard_library(tmp_path, monkeypatch, line, expected):
    monkeypatch.delenv("KEY", raising=False)
    (tmp_path / ".env").write_text(f"# a comment\n\nOTHER=x\nno equals sign here\n{line}\n")
    assert load_secret("KEY", tmp_path) == expected


def test_a_commented_out_key_is_not_read(tmp_path, monkeypatch):
    monkeypatch.delenv(KEY_VAR)
    (tmp_path / ".env").write_text(f"#{KEY_VAR}=old-value\n")
    with pytest.raises(ContractError, match=KEY_VAR):
        load_secret(KEY_VAR, tmp_path)


def test_the_missing_key_error_names_the_variable_and_no_value(tmp_path, monkeypatch):
    monkeypatch.setenv("SOME_OTHER_KEY", SECRET)
    (tmp_path / ".env").write_text(f"SOME_OTHER_KEY={SECRET}\nEMPTY_KEY=\n")
    for name in ("ABSENT_KEY", "EMPTY_KEY"):
        with pytest.raises(ContractError, match=name) as caught:
            load_secret(name, tmp_path)
        assert SECRET not in everything_printed(caught.value)


def test_a_missing_dotenv_is_a_missing_key_and_not_a_crash(tmp_path):
    with pytest.raises(ContractError, match="ABSENT_KEY"):
        load_secret("ABSENT_KEY", tmp_path / "no-such-folder")


def test_unreadable_bytes_in_dotenv_do_not_quote_the_file(tmp_path):
    (tmp_path / ".env").write_bytes(b"BROKEN=\xff\xfe" + SECRET.encode() + b"\n")
    with pytest.raises(ContractError, match="ABSENT_KEY") as caught:
        load_secret("ABSENT_KEY", tmp_path)
    assert SECRET not in everything_printed(caught.value)


def test_load_secret_prints_and_logs_nothing(tmp_path, capfd, caplog, monkeypatch):
    load_secret(KEY_VAR, tmp_path)
    monkeypatch.delenv(KEY_VAR)
    (tmp_path / ".env").write_text(f"{KEY_VAR}={SECRET}\n")
    load_secret(KEY_VAR, tmp_path)
    printed = capfd.readouterr()
    assert SECRET not in printed.out + printed.err + caplog.text


def test_an_entry_dump_holds_the_variables_name_and_never_its_value():
    for family in sorted(set(ADAPTERS)):
        spec = make_spec(family)
        get_provider(spec, client=FakeWire())
        for dumped in (spec.model_dump_json(), json.dumps(spec.model_dump(mode="json")), repr(spec), str(spec)):
            assert KEY_VAR in dumped and SECRET not in dumped


def test_a_key_pasted_into_the_registry_is_refused_and_not_repeated(tmp_path):
    for field in ("api_key_env", "api_key"):
        path = tmp_path / "models.yaml"
        entry = {"provider": "anthropic", "model": "m", "refusal_fallback": False, field: f"sk-{SECRET}", **PRICES}
        path.write_text(yaml.safe_dump({"default": "m", "models": {"m": entry}}))
        with pytest.raises(ContractError, match=field) as caught:
            load_models(path)
        assert SECRET not in everything_printed(caught.value)


# ---- the registry
def _real_entry_names() -> set[str]:
    return set(yaml.safe_load(REAL_REGISTRY.read_text(encoding="utf-8"))["models"])


def test_every_entry_in_the_real_registry_loads():
    models, default = load_models(REAL_REGISTRY)
    assert set(models) == _real_entry_names() and default == "claude-opus-5-5"
    assert {spec.provider for spec in models.values()} == set(ADAPTERS)
    assert all(name == spec.name and spec.max_tokens == 16000 for name, spec in models.items())
    assert models["claude-opus-5-5"].input_usd_per_mtok == Decimal("4.00")
    assert models["claude-haiku-5-5"].refusal_fallback is False, "Haiku has no server-side fallback"


def test_every_entry_in_the_real_registry_works_with_its_adapter(monkeypatch):
    models, _ = load_models(REAL_REGISTRY)
    for spec in models.values():
        if spec.api_key_env:
            monkeypatch.setenv(spec.api_key_env, "fake")
    for name, spec in models.items():
        sample = ADAPTERS[spec.provider].wire_sample()
        wire = FakeWire(sample.ok)
        assert get_provider(spec, client=wire).complete(SYSTEM, USER, SCHEMA).text == sample.expected.text, name
        assert spec.model in repr(wire.calls[0])


def test_a_new_model_on_a_known_api_needs_one_entry_and_no_code(tmp_path, monkeypatch):
    """Scenario: New model on a known API."""
    monkeypatch.setenv("CLAUDE_API_KEY", "fake")
    copy = tmp_path / "models.yaml"
    shutil.copy(REAL_REGISTRY, copy)
    with copy.open("a", encoding="utf-8") as handle:
        handle.write('\n  my-new-claude:\n    provider: anthropic\n    model: claude-some-new-model\n    api_key_env: CLAUDE_API_KEY\n'
                     '    effort: low\n    refusal_fallback: false\n    max_tokens: 4000\n    input_usd_per_mtok: "1.00"\n'
                     '    output_usd_per_mtok: "2.00"\n    cache_read_usd_per_mtok: "0.10"\n    cache_write_usd_per_mtok: "1.25"\n')
    models, default = load_models(copy)
    assert default == "claude-opus-5-5" and set(models) == _real_entry_names() | {"my-new-claude"}
    wire = FakeWire(AnthropicProvider.wire_sample().ok)
    get_provider(models["my-new-claude"], client=wire).complete(SYSTEM, USER, SCHEMA)
    sent = wire.calls[0][1]
    assert (sent["model"], sent["max_tokens"], sent["output_config"]["effort"]) == ("claude-some-new-model", 4000, "low")
    recorded = models["my-new-claude"].model_dump(mode="json")
    assert recorded["model"] == "claude-some-new-model" and recorded["input_usd_per_mtok"] == "1.00"


def _write_registry(path: Path, **top) -> Path:
    path.write_text(yaml.safe_dump(top))
    return path


GOOD_ENTRY = {"provider": "anthropic", "model": "m", "refusal_fallback": False, **PRICES}


@pytest.mark.parametrize("top, message", [
    ({"default": "a", "models": {}}, "lists no models"),
    ({"default": "a"}, "lists no models"),
    ({"default": "a", "models": ["a"]}, "lists no models"),
    ({"default": "b", "models": {"a": GOOD_ENTRY}}, "default must name an entry; entries are a"),
    ({"models": {"a": GOOD_ENTRY}}, "default must name an entry"),
    ({"default": ["a"], "models": {"a": GOOD_ENTRY}}, "default must name an entry"),
    ({"default": "a", "models": {"a": "claude"}}, "model a is not a set of fields"),
    ({"default": "a", "models": {"a": {**GOOD_ENTRY, "provider": "nobody"}}}, "provider must be one of anthropic, ollama, openai_compatible"),
    ({"default": "a", "models": {"a": {**GOOD_ENTRY, "temprature": 0}}}, "temprature"),
    ({"default": "a", "models": {"a": {k: v for k, v in GOOD_ENTRY.items() if k != "input_usd_per_mtok"}}}, "input_usd_per_mtok"),
    ({"default": "a", "models": {"a": {k: v for k, v in GOOD_ENTRY.items() if k != "refusal_fallback"}}}, "refusal_fallback"),
    ({"default": "a", "models": {"a": {**GOOD_ENTRY, "input_usd_per_mtok": "free"}}}, "input_usd_per_mtok"),
    ({"default": "a", "models": {"a": {**GOOD_ENTRY, "output_usd_per_mtok": "-1"}}}, "output_usd_per_mtok"),
    ({"default": "a", "models": {"a": {**GOOD_ENTRY, "max_tokens": 0}}}, "max_tokens"),
])
def test_a_bad_registry_stops_with_a_plain_message(tmp_path, top, message):
    with pytest.raises(ContractError, match=message):
        load_models(_write_registry(tmp_path / "models.yaml", **top))


def test_a_missing_or_broken_registry_stops_with_a_plain_message(tmp_path):
    with pytest.raises(ContractError, match="not found"):
        load_models(tmp_path / "none.yaml")
    broken = tmp_path / "broken.yaml"
    broken.write_text("models: [unclosed")
    with pytest.raises(ContractError, match="not valid YAML"):
        load_models(broken)
    empty = tmp_path / "empty.yaml"
    empty.write_text("")
    with pytest.raises(ContractError, match="lists no models"):
        load_models(empty)


def test_the_name_comes_from_the_entrys_key(tmp_path):
    models, _ = load_models(_write_registry(tmp_path / "models.yaml", default="a", models={"a": {**GOOD_ENTRY, "name": "ignored"}}))
    assert models["a"].name == "a"


def test_an_entry_cannot_be_changed_after_loading():
    with pytest.raises(ValueError):
        make_spec().max_tokens = 1


# ---- cost
def test_cached_tokens_are_priced_at_the_cache_read_price():
    """Scenario: Cached tokens."""
    assert cost_usd(make_spec(), Completion(text="", input_tokens=0, output_tokens=0, cache_read_tokens=1000)) == Decimal("0.0002")


def test_each_kind_of_token_has_its_own_price():
    usage = Completion(text="", input_tokens=1_000_000, output_tokens=1_000_000, cache_read_tokens=1_000_000, cache_write_tokens=1_000_000)
    assert cost_usd(make_spec(), usage) == Decimal("29.20")
    assert isinstance(cost_usd(make_spec(), usage), Decimal)


def test_a_free_local_model_costs_nothing():
    spec = make_spec("ollama", **{key: "0" for key in PRICES})
    assert cost_usd(spec, Completion(text="", input_tokens=500, output_tokens=500)) == 0


@pytest.mark.parametrize("field", ["input_tokens", "output_tokens"])
def test_a_reply_with_nonsense_usage_is_refused(field):
    with pytest.raises(ValueError):
        Completion(**{"text": "", "input_tokens": 1, "output_tokens": 1, field: -1})


# ---- usage on every path that costs money
def _anthropic_reply(stop_reason, usage, *content):
    return SimpleNamespace(stop_reason=stop_reason, content=list(content), usage=usage)


def test_cost_counts_every_attempt_when_a_refusal_fallback_ran():
    declined = SimpleNamespace(type="message", input_tokens=100, output_tokens=10, cache_read_input_tokens=1, cache_creation_input_tokens=2)
    served = SimpleNamespace(type="fallback_message", input_tokens=200, output_tokens=20, cache_read_input_tokens=3, cache_creation_input_tokens=4)
    usage = SimpleNamespace(input_tokens=200, output_tokens=20, cache_read_input_tokens=3, cache_creation_input_tokens=4, iterations=[declined, served])
    reply = _anthropic_reply("end_turn", usage, SimpleNamespace(type="text", text="{}"))
    completion = get_provider(make_spec("anthropic"), client=FakeWire(reply)).complete(SYSTEM, USER, SCHEMA)
    assert (completion.input_tokens, completion.output_tokens, completion.cache_read_tokens, completion.cache_write_tokens) == (300, 30, 4, 6)


@pytest.mark.parametrize("stop_reason, failure", [("refusal", ProviderRefused), ("max_tokens", ProviderError)])
def test_a_refused_or_cut_off_answer_reports_what_it_used(stop_reason, failure):
    usage = SimpleNamespace(input_tokens=11, output_tokens=7, cache_read_input_tokens=0, cache_creation_input_tokens=0)
    with pytest.raises(failure) as caught:
        get_provider(make_spec("anthropic"), client=FakeWire(_anthropic_reply(stop_reason, usage))).complete(SYSTEM, USER, SCHEMA)
    assert (caught.value.usage.input_tokens, caught.value.usage.output_tokens) == (11, 7)


@pytest.mark.parametrize("finish_reason, message, failure", [("length", {}, ProviderError), ("stop", {"refusal": "no"}, ProviderRefused)])
def test_an_openai_compatible_failure_reports_what_it_used(finish_reason, message, failure):
    reply = {"choices": [{"message": {"content": "{}", **message}, "finish_reason": finish_reason}], "usage": {"prompt_tokens": 11, "completion_tokens": 7}}
    with pytest.raises(failure) as caught:
        get_provider(make_spec("openai_compatible"), client=FakeWire(reply)).complete(SYSTEM, USER, SCHEMA)
    assert (caught.value.usage.input_tokens, caught.value.usage.output_tokens) == (11, 7)


@pytest.mark.parametrize("family", ["ollama", "openai_compatible"])
@pytest.mark.parametrize("failure", [http.client.IncompleteRead(b"half"), http.client.BadStatusLine("nonsense")])
def test_a_malformed_http_reply_is_a_provider_error_and_not_a_crash(family, failure):
    with pytest.raises(ProviderError, match="the request failed"):
        get_provider(make_spec(family, base_url="http://fake.invalid"), client=FakeWire(failure)).complete(SYSTEM, USER, SCHEMA)


# ---- what a real server needed: found against Moonshot on 2026-11-04
@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    waits = []
    monkeypatch.setattr("itemizer.providers.time.sleep", waits.append)
    return waits


def _http_error(code, retry_after=None):
    headers = {"Retry-After": retry_after} if retry_after else None
    return urllib.error.HTTPError("http://fake.invalid", code, "quotes the request", headers, None)


class Scripted(FakeWire):
    """Raises or answers from a list, one per call."""

    def __init__(self, *answers):
        super().__init__()
        self.answers = list(answers)

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer


def test_a_null_temperature_is_left_out_of_the_request():
    wire = FakeWire(OpenAICompatibleProvider.wire_sample().ok)
    get_provider(make_spec("openai_compatible", temperature=None), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert "temperature" not in wire.calls[0][0][2]


def test_a_null_temperature_is_left_out_for_ollama_too():
    wire = FakeWire(OllamaProvider.wire_sample().ok)
    get_provider(make_spec("ollama", temperature=None), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert wire.calls[0][0][2]["options"] == {"num_predict": 16000}


def test_a_set_temperature_is_sent():
    wire = FakeWire(OpenAICompatibleProvider.wire_sample().ok)
    get_provider(make_spec("openai_compatible", temperature=0.5), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert wire.calls[0][0][2]["temperature"] == 0.5


def test_effort_goes_to_the_server_as_reasoning_effort():
    wire = FakeWire(OpenAICompatibleProvider.wire_sample().ok)
    get_provider(make_spec("openai_compatible", effort="medium"), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert wire.calls[0][0][2]["reasoning_effort"] == "medium"


def test_cached_and_written_prompt_tokens_are_priced_apart():
    reply = OpenAICompatibleProvider.wire_sample().ok
    reply["usage"] = {"prompt_tokens": 100, "completion_tokens": 7, "prompt_tokens_details": {"cached_tokens": 60, "cache_write_tokens": 10}}
    found = get_provider(make_spec("openai_compatible"), client=FakeWire(reply)).complete(SYSTEM, USER, SCHEMA)
    assert (found.input_tokens, found.cache_read_tokens, found.cache_write_tokens, found.output_tokens) == (30, 60, 10, 7)


def test_cached_tokens_at_the_top_of_usage_count_too():
    reply = OpenAICompatibleProvider.wire_sample().ok
    reply["usage"] = {"prompt_tokens": 100, "completion_tokens": 7, "cached_tokens": 40}
    found = get_provider(make_spec("openai_compatible"), client=FakeWire(reply)).complete(SYSTEM, USER, SCHEMA)
    assert (found.input_tokens, found.cache_read_tokens) == (60, 40)


@pytest.mark.parametrize("family", ["ollama", "openai_compatible"])
def test_a_rate_limit_is_tried_again_and_the_answer_arrives(family, no_waiting):
    good = ADAPTERS[family].wire_sample().ok
    wire = Scripted(_http_error(429), _http_error(503), good)
    found = get_provider(make_spec(family, base_url="http://fake.invalid"), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert found.text == "{}" and len(wire.calls) == 3 and no_waiting == [1.0, 2.0]


def test_retry_after_says_how_long_to_wait(no_waiting):
    wire = Scripted(_http_error(429, "7"), OpenAICompatibleProvider.wire_sample().ok)
    get_provider(make_spec("openai_compatible"), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert no_waiting == [7.0]


def test_a_long_retry_after_is_capped(no_waiting):
    wire = Scripted(_http_error(429, "9000"), OpenAICompatibleProvider.wire_sample().ok)
    get_provider(make_spec("openai_compatible"), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert no_waiting == [60.0]


def test_a_rate_limit_that_never_clears_goes_to_review(no_waiting):
    wire = Scripted(*[_http_error(429) for _ in range(4)])
    with pytest.raises(ProviderError, match="status 429"):
        get_provider(make_spec("openai_compatible"), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert len(wire.calls) == 4


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_a_request_the_server_will_never_accept_is_not_tried_again(code, no_waiting):
    wire = Scripted(_http_error(code))
    with pytest.raises(ProviderError, match=f"status {code}"):
        get_provider(make_spec("openai_compatible"), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert len(wire.calls) == 1 and no_waiting == []


def test_a_dropped_connection_is_tried_again(no_waiting):
    wire = Scripted(urllib.error.URLError("quotes the request"), OpenAICompatibleProvider.wire_sample().ok)
    assert get_provider(make_spec("openai_compatible"), client=wire).complete(SYSTEM, USER, SCHEMA).text == "{}"
    assert len(wire.calls) == 2


def test_a_timeout_is_not_tried_again_because_it_may_have_been_billed(no_waiting):
    wire = Scripted(TimeoutError("quotes the request"))
    with pytest.raises(ProviderError):
        get_provider(make_spec("openai_compatible"), client=wire).complete(SYSTEM, USER, SCHEMA)
    assert len(wire.calls) == 1


def test_the_kimi_entry_names_the_variable_and_holds_no_key():
    specs, default = load_models(Path(__file__).resolve().parents[1] / "config" / "models.yaml")
    kimi = specs["kimi-k3"]
    assert default == "claude-opus-5-5" and kimi.provider == "openai_compatible" and kimi.temperature is None
    assert kimi.api_key_env == "MOONSHOT_API_KEY" and kimi.base_url == "https://api.moonshot.ai/v1" and not kimi.refusal_fallback
    assert "sk-" not in (Path(__file__).resolve().parents[1] / "config" / "models.yaml").read_text(encoding="utf-8")

