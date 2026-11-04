"""Tests per scenario for the local upload page. Every note is invented, and every model is a fake."""
from __future__ import annotations

import io
import json
import threading
import time
from pathlib import Path

import openpyxl
import pytest
from fastapi.testclient import TestClient
from test_label_review import do_import, drafted, edit, frozen, set_category, single_charge_note, write_pack  # noqa: F401 (fixtures)
from test_model_labels import labels  # noqa: F401 (a fixture)
from test_pipeline import NOTE_WORDS, StubModel, _other_export, _settings, d3, hash_of  # noqa: F401 (d3 is a fixture)
from typer.testing import CliRunner

from itemizer import pipeline
from itemizer.cli import app as cli_app
from itemizer.ui import app as ui_app

ORIGIN = "http://127.0.0.1:8000"
DISABLED = 'type="submit" disabled'  # the button itself: the word alone is also in the page's stylesheet
runner = CliRunner()


def client_for(world) -> TestClient:
    return TestClient(ui_app.create_app(world.tmp), base_url=ORIGIN, headers={"origin": ORIGIN}, raise_server_exceptions=False)


@pytest.fixture
def web(frozen):  # noqa: F811
    client = client_for(frozen)
    client.world = frozen
    return client


def upload(client: TestClient, path: Path, name: str | None = None):
    return client.post("/uploads", files={"file": (name or path.name, path.read_bytes())}, follow_redirects=False)


def uploaded_files(world) -> list[Path]:
    folder = world.tmp / "data" / "uploads"
    return sorted(folder.glob("*.xlsx")) if folder.exists() else []


def start(client: TestClient, path: Path):
    location = upload(client, path).headers["location"]
    return client.post(f"{location}/run", follow_redirects=False)


def finish(client: TestClient, job_url: str, seconds: float = 60) -> dict:
    stop = time.monotonic() + seconds
    while time.monotonic() < stop:
        status = client.get(f"{job_url}/status").json()
        if status["state"] != "running":
            return status
        time.sleep(0.05)
    raise AssertionError("the job did not finish")


def fresh_file(world, *notes: str) -> Path:
    return _other_export(world.tmp / "fresh.xlsx", list(notes) or ["FRESH CHARGE $50.00", "ANOTHER CHARGE $50.00"])


# ---- upload with checks
def test_a_wrong_type_is_refused_and_nothing_is_stored(web):
    reply = web.post("/uploads", files={"file": ("notes.csv", b"a,b\n1,2\n")}, follow_redirects=False)
    assert reply.status_code == 400 and "Only .xlsx" in reply.text and uploaded_files(web.world) == []


def test_a_file_over_the_limit_is_refused_and_nothing_is_left_behind(web, monkeypatch):
    monkeypatch.setattr(ui_app, "MAX_UPLOAD_BYTES", 10)
    reply = upload(web, web.world.export)
    assert reply.status_code == 400 and "over the" in reply.text
    assert list((web.world.tmp / "data" / "uploads").iterdir()) == []


def test_no_file_chosen_is_a_plain_message(web):
    assert "Choose a file" in web.post("/uploads", follow_redirects=False).text


def test_the_same_file_twice_goes_to_the_same_check_with_no_duplicate(web):
    first, second = upload(web, web.world.export), upload(web, web.world.export)
    assert first.headers["location"] == second.headers["location"] and len(uploaded_files(web.world)) == 1


def test_a_file_is_stored_by_its_content_and_its_name_never_reaches_a_path(web):
    upload(web, fresh_file(web.world), "../../escaped.xlsx")
    stored = uploaded_files(web.world)
    assert len(stored) == 1 and len(stored[0].stem) == 64
    assert not (web.world.tmp / "escaped.xlsx").exists() and not (web.world.tmp / "data" / "escaped.xlsx").exists()


def test_a_file_name_is_escaped_on_the_page(web):
    reply = upload(web, fresh_file(web.world), "<script>alert(1)</script>.xlsx")
    text = web.get(reply.headers["location"]).text
    assert "<script>alert(1)" not in text and "&lt;script&gt;alert(1)" in text


# ---- the pre-check
def test_a_missing_column_is_named_and_the_run_cannot_start(web):
    book = openpyxl.Workbook()
    book.active.append(["SHIPMENT_GID", "Carrier"])
    path = web.world.tmp / "short.xlsx"
    book.save(path)
    location = upload(web, path).headers["location"]
    text = web.get(location).text
    assert "missing columns" in text and "Descritipion" in text and DISABLED in text
    reply = web.post(f"{location}/run", follow_redirects=False)  # a disabled button is not a check
    assert reply.status_code == 400 and web.app.state.runner.jobs == {}


def test_a_file_that_is_not_a_workbook_cannot_start(web):
    path = web.world.tmp / "junk.xlsx"
    path.write_bytes(b"not a workbook")
    text = web.get(upload(web, path).headers["location"]).text
    assert "cannot be read" in text and DISABLED in text


def test_a_file_flagged_by_the_scan_gives_a_count_and_no_note_text(web):
    path = fresh_file(web.world, "SEE JANE.ROE@EXAMPLE.ORG CHARGE $50.00")
    text = web.get(upload(web, path).headers["location"]).text
    assert "flagged 1 notes" in text and DISABLED in text and "JANE" not in text


def test_the_dataset_file_needs_no_calls_after_a_run_and_gets_full_kpis(web):
    pipeline.run(web.world.tmp)
    text = web.get(upload(web, web.world.export).headers["location"]).text
    assert "every answer is already stored" in text and "the full KPIs" in text and DISABLED not in text


def test_another_file_says_it_gets_no_accuracy(web):
    text = web.get(upload(web, fresh_file(web.world)).headers["location"]).text
    assert "No accuracy" in text and DISABLED not in text


def test_a_file_holding_held_back_notes_cannot_start_before_the_freeze(drafted):  # noqa: F811
    from itemizer.bootstrap import split as sp

    client = client_for(drafted)
    held_back = drafted.notes[sp.notes_in_set(drafted.manifest, "TEST")[0]].text
    text = client.get(upload(client, fresh_file(drafted, held_back)).headers["location"]).text
    assert "held back for TEST" in text and DISABLED in text


def test_the_dataset_file_cannot_start_before_the_freeze(drafted):  # noqa: F811
    client = client_for(drafted)
    text = client.get(upload(client, drafted.export).headers["location"]).text
    assert "waits until TEST is frozen" in text and DISABLED in text


def test_the_pre_check_agrees_with_what_the_run_does(web):
    path = fresh_file(web.world)
    location = upload(web, path).headers["location"]
    report = pipeline.inspect_export(web.world.tmp, path)
    assert report["new_calls"] == 2 and report["rows"] == 2 and report["notes"] == 2
    calls = len(web.world.calls)
    finish(web, web.post(f"{location}/run", follow_redirects=False).headers["location"])
    assert len(web.world.calls) - calls == 2
    assert pipeline.inspect_export(web.world.tmp, path)["new_calls"] == 0


def test_an_estimate_over_the_budget_stops_the_run(web):
    _settings(web.world, lambda s: s["budget"].update(max_usd_per_run="0.00"))
    location = upload(web, fresh_file(web.world)).headers["location"]
    assert "over the $0.00 limit" in web.get(location).text
    assert web.post(f"{location}/run", follow_redirects=False).status_code == 400


# ---- running
def test_a_run_goes_from_upload_to_the_result_and_the_output(web):
    pipeline.run(web.world.tmp)
    reply = start(web, web.world.export)
    assert reply.status_code == 303
    status = finish(web, reply.headers["location"])
    assert status["state"] == "done" and status["done"] == status["total"] == len(web.world.notes)
    assert "Accepted without reading" in web.get(f"/runs/{status['run_id']}").text


def test_the_same_file_gives_the_same_workbook_as_the_command_line_with_no_calls(web):
    direct = pipeline.run(web.world.tmp)
    digest, calls = hash_of(direct.workbook), len(web.world.calls)
    status = finish(web, start(web, web.world.export).headers["location"])
    assert status["run_id"] == direct.run_id and len(web.world.calls) == calls
    assert hash_of(direct.workbook) == digest


def test_a_second_job_is_refused_and_links_to_the_running_one(web, monkeypatch):
    release = threading.Event()

    class Waits(StubModel):
        def complete(self, system, user, schema):
            release.wait(30)
            return super().complete(system, user, schema)

    monkeypatch.setattr(pipeline, "get_provider", lambda spec, client=None, project_root=None: Waits(spec, web.world.calls))
    first = start(web, fresh_file(web.world))
    second = start(web, web.world.export)
    assert second.status_code == 409 and "in progress" in second.text and first.headers["location"] in second.text
    release.set()
    assert finish(web, first.headers["location"])["state"] == "done"


def test_a_job_carries_on_with_nobody_watching(web):
    start(web, fresh_file(web.world))
    job = next(iter(web.app.state.runner.jobs.values()))
    web.app.state.runner.threads[job.id].join(60)  # no page asked for its status
    assert job.state == "done" and job.run_id in web.get("/").text


def test_a_failure_with_a_plain_message_shows_it(web, monkeypatch):
    def stops(*args, **kwargs):
        raise pipeline.ContractError("A plain reason.")

    monkeypatch.setattr(pipeline, "run", stops)
    status = finish(web, start(web, fresh_file(web.world)).headers["location"])
    assert status["state"] == "failed" and status["message"] == "A plain reason."


def test_an_unexpected_failure_in_a_job_shows_its_type_only(web, monkeypatch):
    def breaks(*args, **kwargs):
        raise ValueError("LUMPER $85.00 quoted by a library")

    monkeypatch.setattr(pipeline, "run", breaks)
    status = finish(web, start(web, fresh_file(web.world)).headers["location"])
    assert status["state"] == "failed" and "unexpected ValueError" in status["message"] and "LUMPER" not in status["message"]


def test_an_unexpected_failure_on_a_page_shows_its_type_only(web, monkeypatch):
    def breaks(*args, **kwargs):
        raise ValueError("LUMPER $85.00 quoted by a library")

    monkeypatch.setattr(pipeline, "inspect_export", breaks)
    reply = web.get(upload(web, fresh_file(web.world)).headers["location"])
    assert reply.status_code == 500 and "unexpected ValueError" in reply.text and "LUMPER" not in reply.text


def test_an_unknown_job_is_a_plain_message(web):
    assert "not known" in web.get("/jobs/nothing").text and web.get("/jobs/nothing/status").status_code == 400


# ---- the output Excel
def test_the_download_is_that_runs_workbook_with_the_expenses(web):
    outcome = pipeline.run(web.world.tmp)
    reply = web.get(f"/runs/{outcome.run_id}/download")
    assert reply.status_code == 200 and reply.content == outcome.workbook.read_bytes()
    assert "spreadsheetml" in reply.headers["content-type"] and outcome.run_id in reply.headers["content-disposition"]
    assert openpyxl.load_workbook(io.BytesIO(reply.content))["Items"].max_row > 1


def test_the_page_warns_that_the_download_holds_tool_output(web):
    outcome = pipeline.run(web.world.tmp)
    assert "holds the tool's answers" in web.get(f"/runs/{outcome.run_id}").text


@pytest.mark.parametrize("run_id", ["not-a-run", "run_XYZ", "run_0123456789abcdef"])
def test_a_bad_run_id_is_refused_and_reads_no_file(web, run_id):
    for url in (f"/runs/{run_id}", f"/runs/{run_id}/download"):
        reply = web.get(url)
        assert reply.status_code == 400 and "spreadsheetml" not in reply.headers["content-type"]


# ---- KPIs on the page
def test_a_run_on_another_file_shows_outcomes_and_no_accuracy(web):
    status = finish(web, start(web, fresh_file(web.world)).headers["location"])
    text = web.get(f"/runs/{status['run_id']}").text
    assert "verified" in text and "Not measured for this file" in text and "Score on the test set" not in text


def test_scoring_from_the_page_shows_the_level_and_who_wrote_the_labels(web):
    outcome = pipeline.run(web.world.tmp)
    assert "Score on the test set" in web.get(f"/runs/{outcome.run_id}").text
    text = web.post(f"/runs/{outcome.run_id}/evaluate", follow_redirects=True).text
    assert "Level 1: <b>pass</b>" in text and "Read this first" in text and "and not that it is right" in text
    assert "Accuracy on covered rows" in text


def test_scoring_again_after_a_correction_needs_no_model_and_shows_the_new_figure(web):
    world = web.world
    outcome = pipeline.run(world.tmp)
    before = web.post(f"/runs/{outcome.run_id}/evaluate", follow_redirects=True).text
    assert "<td>100.0%</td><td>95%</td>" in before
    calls = len(world.calls)
    path = write_pack(world)
    edit(path, set_category(single_charge_note(world)))
    do_import(world, path)
    after = web.post(f"/runs/{outcome.run_id}/evaluate", follow_redirects=True).text
    assert len(world.calls) == calls and "<td>100.0%</td><td>95%</td>" not in after
    ledger = (world.tmp / "data" / "kpi" / "test_budget.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["event"] for line in ledger] == ["spent", "rescored"]


def test_scoring_past_the_budget_is_refused_and_points_to_the_command_line(web):
    world = web.world
    web.post(f"/runs/{pipeline.run(world.tmp).run_id}/evaluate")
    other = pipeline.run(world.tmp, model_name="claude-sonnet-5-5")
    reply = web.post(f"/runs/{other.run_id}/evaluate", follow_redirects=False)
    assert reply.status_code == 400 and "--extra-peek" in reply.text and "is spent" in reply.text
    assert 'name="extra_peek"' not in reply.text


def test_a_score_on_other_answers_is_not_shown(web):
    outcome = pipeline.run(web.world.tmp)
    web.post(f"/runs/{outcome.run_id}/evaluate")
    path = outcome.folder / "note_results.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    next(iter(stored.values()))["reason_code"] = "amount_unclear"
    path.write_text(json.dumps(stored), encoding="utf-8")
    text = web.get(f"/runs/{outcome.run_id}").text
    assert "Level 1:" not in text and "has not been scored" in text


def test_the_status_page_is_served_with_the_caveat_first(web):
    web.post(f"/runs/{pipeline.run(web.world.tmp).run_id}/evaluate")
    text = web.get("/status").text
    assert "Back to upload" in text and text.index("Read this first") < text.index("D1: charge category list")


def test_no_page_shows_note_text_except_the_output_itself(web):
    outcome = pipeline.run(web.world.tmp)
    web.post(f"/runs/{outcome.run_id}/evaluate")
    for url in ("/", f"/runs/{outcome.run_id}", "/status"):
        assert not any(word in web.get(url).text for word in NOTE_WORDS), url


# ---- this machine only
def test_a_post_from_another_site_is_refused_and_starts_nothing(web):
    location = upload(web, fresh_file(web.world)).headers["location"]
    reply = web.post(f"{location}/run", headers={"origin": "https://elsewhere.example"})
    assert reply.status_code == 403 and web.app.state.runner.jobs == {}


def test_a_post_with_no_origin_is_refused(web):
    location = upload(web, fresh_file(web.world)).headers["location"]
    del web.headers["origin"]
    assert web.post(f"{location}/run").status_code == 403 and web.app.state.runner.jobs == {}


@pytest.mark.parametrize("origin", ["null", "http://127.0.0.1.elsewhere.example", "http://localhost.elsewhere.example:8000"])
def test_an_origin_that_only_looks_local_is_refused(web, origin):
    assert web.post("/uploads", headers={"origin": origin}).status_code == 403


def test_another_sites_host_is_refused(web):
    reply = web.get("/", headers={"host": "elsewhere.example"})
    assert reply.status_code == 400 and "this machine only" in reply.text


def test_localhost_is_accepted():
    assert ui_app._host_name("localhost:8000") == "localhost" and ui_app._host_name("127.0.0.1") == "127.0.0.1"


def test_the_command_will_not_start_beside_something_already_listening(d3, monkeypatch):
    import socket

    import uvicorn

    started = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **options: started.append(options))
    with socket.socket() as other:
        other.bind(("0.0.0.0", 0))  # as another project's server would, on every address
        other.listen()
        port = other.getsockname()[1]
        result = runner.invoke(cli_app, ["ui", "--port", str(port)])
    assert result.exit_code == 2 and f"already listening on port {port}" in result.stderr and started == []


def test_the_default_port_is_not_one_other_projects_use(d3, monkeypatch):
    import uvicorn

    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **options: seen.update(options))
    assert runner.invoke(cli_app, ["ui"]).exit_code == 0 and seen["port"] == 8899


def test_the_command_binds_to_this_machine_and_has_no_host_option(d3, monkeypatch):
    import uvicorn

    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **options: seen.update(options))
    result = runner.invoke(cli_app, ["ui", "--port", "8931"])
    assert result.exit_code == 0, result.stderr
    assert seen["host"] == "127.0.0.1" and seen["port"] == 8931 and "127.0.0.1:8931" in result.stdout
    assert runner.invoke(cli_app, ["ui", "--host", "0.0.0.0"]).exit_code != 0


# ---- the estimate, measured against the rehearsal
def test_the_estimate_counts_the_cold_start_that_a_small_file_mostly_costs():
    from decimal import Decimal

    spec = pipeline.choose_model(Path(__file__).resolve().parents[1], "claude-opus-5-5")
    assert pipeline._estimate_usd(spec, 6, 8) == Decimal("0.22")  # the rehearsal's 6 notes cost $0.2209
    assert pipeline._estimate_usd(spec, 729, 8) == Decimal("3.58")  # the run on all rows cost $3.65
    assert pipeline._estimate_usd(spec, 0, 8) == Decimal("0.00")

