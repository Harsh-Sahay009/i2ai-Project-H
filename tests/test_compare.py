"""Tests per scenario for `itemizer compare-models`. Every note is invented, and every model is a fake."""
from __future__ import annotations

import json

import pytest
from test_bootstrap import fill_pack
from test_pipeline import NOTE_WORDS, d3  # noqa: F401 (d3 is a fixture)
from typer.testing import CliRunner

from itemizer import compare
from itemizer.bootstrap import labels as lb
from itemizer.bootstrap import split as sp
from itemizer.bootstrap.data import ContractError
from itemizer.cli import app

MODELS = ["claude-opus-5-5", "claude-sonnet-5-5"]
MEASURES = {"model", "run_id", "notes", "valid_first_try", "retried", "review_share", "verified_share", "discrepancy_share", "review_reasons",
            "agreement_with_first", "accuracy_on_labels", "usd", "usd_per_note", "mean_latency_ms", "projected_usd_all_notes",
            "projected_minutes_all_notes"}
runner = CliRunner()


def test_two_models_on_the_same_notes_and_the_same_measures(d3):
    report = compare.compare_models(d3.tmp, MODELS, "train", 30)
    first, second = report["models"]
    assert (first["model"], second["model"]) == tuple(MODELS)
    assert set(first) == set(second) == MEASURES
    assert first["notes"] == second["notes"] == 30
    asked = {model: sorted(call.user for call in d3.calls if call.model == model) for model in MODELS}
    assert asked[MODELS[0]] == asked[MODELS[1]]  # the same notes
    assert len({call.system for call in d3.calls}) == 1  # the same prompt
    assert first["valid_first_try"] == 1.0 and first["agreement_with_first"] is None and second["agreement_with_first"] == 1.0


def test_the_projection_covers_all_notes(d3):
    report = compare.compare_models(d3.tmp, MODELS[:1], "train", 10)
    line = report["models"][0]
    assert report["all_notes"] == len(d3.notes)
    assert float(line["projected_usd_all_notes"]) == pytest.approx(0.004 * len(d3.notes), abs=0.01)  # 1,000 input tokens per note at $4.00 per million
    assert line["projected_minutes_all_notes"] >= 0


def test_disagreement_between_models_is_measured(d3):
    report = compare.compare_models(d3.tmp, MODELS[:1], "train", 30)
    assert report["models"][0]["agreement_with_first"] is None
    d3.wrong_on = "LUMPER"
    second = compare.compare_models(d3.tmp, MODELS, "train", 30)["models"][1]
    assert second["agreement_with_first"] < 1.0


def test_the_report_and_the_table_hold_no_note_text(d3):
    result = runner.invoke(app, ["compare-models", "--models", ",".join(MODELS), "--set", "train", "--limit", "5"])
    assert result.exit_code == 0, result.stderr
    assert not any(word in result.stdout for word in NOTE_WORDS)
    assert "Valid first try" in result.stdout and all(model in result.stdout for model in MODELS)
    written = next((d3.tmp / "data" / "compare").iterdir()).read_text(encoding="utf-8")
    assert not any(word in written for word in NOTE_WORDS)


@pytest.mark.parametrize("name", ["test", "reserve", "all"])
def test_test_is_refused_because_it_never_chooses_between_candidates(d3, name):
    result = runner.invoke(app, ["compare-models", "--models", MODELS[0], "--set", name])
    assert result.exit_code == 2 and "TEST never chooses" in result.stderr and d3.calls == []


def test_a_repeat_comparison_reports_the_same_cost_and_makes_no_calls(d3):
    first = compare.compare_models(d3.tmp, MODELS[:1], "train", 5)["models"][0]
    made = len(d3.calls)
    second = compare.compare_models(d3.tmp, MODELS[:1], "train", 5)["models"][0]
    assert len(d3.calls) == made
    assert second["usd"] == first["usd"] > 0 and second["mean_latency_ms"] == first["mean_latency_ms"] > 0


def test_no_labels_means_no_accuracy_is_shown(d3):
    assert compare.compare_models(d3.tmp, MODELS[:1], "train", 5)["models"][0]["accuracy_on_labels"] is None


def test_labels_add_accuracy_on_those_notes_as_an_aggregate(d3):
    lb.build_packs(d3.ws, d3.manifest, d3.notes, _categories(d3))
    path = d3.ws.path("packs/validation.xlsx")
    fill_pack(path, d3.notes)
    codes = {c["code"] for c in _categories(d3)}
    assert lb.import_labels(d3.ws, "validation", path, "v", d3.notes, codes)["errors"] == 0
    labelled = set(d3.ws.read_json("labels/validation.json")["labels"])
    chosen = sorted(sp.notes_in_set(d3.manifest, "VALIDATION"))[:40]
    expected = sum(fp in labelled for fp in chosen)
    assert expected  # the pack covers some of the first 40
    accuracy = compare.compare_models(d3.tmp, MODELS[:1], "validation", 40)["models"][0]["accuracy_on_labels"]
    assert accuracy["labelled_notes"] == accuracy["answered"] == accuracy["correct"] == expected and accuracy["accuracy"] == 1.0
    report = json.dumps(accuracy)
    assert not any(word in report for word in NOTE_WORDS)


def _categories(d3) -> list[dict]:
    from itemizer.bootstrap import taxonomy as tx
    from itemizer.pipeline import CATEGORIES

    return tx.load_taxonomy(d3.tmp / CATEGORIES)["categories"]


def test_no_models_named_is_refused(d3):
    with pytest.raises(ContractError, match="at least one model"):
        compare.compare_models(d3.tmp, [])


def test_the_table_has_a_column_for_each_model(d3):
    report = compare.compare_models(d3.tmp, MODELS, "train", 3)
    table = compare.format_table(report).splitlines()
    assert table[0].split()[1:] == MODELS
    assert all(line.startswith(label) for line, (_, label, _) in zip(table[1:], compare._TABLE[1:], strict=True))
