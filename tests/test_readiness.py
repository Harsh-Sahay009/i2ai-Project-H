"""Offline readiness checks use invented notes and never need a provider or key."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from itemizer.cli import app
from itemizer.bootstrap.data import group_notes, load_export, sha256_file
from test_bootstrap import make_export

ROOT = Path(__file__).resolve().parents[1]


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def local_project(tmp_path, monkeypatch):
    make_export(tmp_path / "export.xlsx", single=2, multi=1, large=1)
    for folder in ("config", "taxonomy", "prompts", "data/bootstrap"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    (tmp_path / "config/bootstrap.yaml").write_text("data:\n  source_file: export.xlsx\n")
    for name in ("run.yaml", "models.yaml"):
        (tmp_path / "config" / name).write_bytes((ROOT / "config" / name).read_bytes())
    rows, _ = load_export(tmp_path / "export.xlsx")
    notes = group_notes(rows, 180)
    first = next(iter(notes.values()))
    categories = [{"code": f"cat_{i}", "name": f"Category {i}", "definition": "A freight charge.",
                   "examples": [{"fingerprint": first.fingerprint, "start": 0, "end": 3}]}
                  for i in range(12)]
    categories.append({"code": "other_unmapped", "name": "Other", "definition": "An unclassified freight charge.", "examples": []})
    (tmp_path / "taxonomy/categories.yaml").write_text(yaml.safe_dump({"categories": categories}))
    manifest = {"dataset_sha256": sha256_file(tmp_path / "export.xlsx"), "pinned_to_train": [],
                "notes": [{"fingerprint": fp, "note_id": n.note_id, "set": "TRAIN"} for fp, n in notes.items()]}
    (tmp_path / "data/bootstrap/split_manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "prompts/fewshot_v1.yaml").write_text("examples: []\n")
    (tmp_path / "prompts/itemize_v1.md").write_text("{{categories}}\n{{examples}}")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_doctor_on_empty_checkout_reports_missing_config_without_writing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = snapshot(tmp_path)
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 2, result.output
    report = json.loads(result.output)
    assert report["setup_ready"] is False
    assert report["checks"]["config"]["status"] == "fail"
    assert report["checks"]["dataset"]["status"] == "blocked"
    assert snapshot(tmp_path) == before


def test_doctor_checks_setup_but_does_not_claim_d3_or_call_a_provider(local_project, monkeypatch):
    from itemizer import providers

    def forbidden(*args, **kwargs):
        pytest.fail("doctor must not instantiate a provider or load secrets")

    monkeypatch.setattr(providers, "get_provider", forbidden)
    monkeypatch.setattr(providers, "load_secret", forbidden)
    (local_project / ".env").write_text("CLAUDE_API_KEY=private-key-never-print\n")
    before = snapshot(local_project)
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["setup_ready"] is True
    assert report["d3_status"] == "not_assessed"
    assert report["model_calls"] == 0
    assert report["artifacts"]["frozen_test"]["status"] == "missing"
    assert report["artifacts"]["run_results"]["status"] == "missing"
    assert "private-key-never-print" not in result.output
    assert "LUMPER" not in result.output and "JOHN.DOE" not in result.output
    assert snapshot(local_project) == before


@pytest.mark.parametrize("change", ["stale", "malformed", "omitted", "unknown_set"])
def test_doctor_detects_unusable_split_without_exposing_contents(local_project, change):
    path = local_project / "data/bootstrap/split_manifest.json"
    manifest = json.loads(path.read_text())
    if change == "stale":
        manifest["dataset_sha256"] = "not-the-dataset-hash"
    elif change == "omitted":
        manifest["notes"].pop()
    elif change == "unknown_set":
        manifest["notes"][0]["set"] = "private-secret-from-bad-file"
    path.write_text("private-secret-from-bad-file" if change == "malformed" else json.dumps(manifest))
    before = snapshot(local_project)
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 2, result.output
    assert json.loads(result.output)["checks"]["split"]["status"] == "fail"
    assert "private-secret-from-bad-file" not in result.output
    assert snapshot(local_project) == before


def test_doctor_rejects_prompt_examples_in_test(local_project):
    path = local_project / "data/bootstrap/split_manifest.json"
    manifest = json.loads(path.read_text())
    taxonomy = yaml.safe_load((local_project / "taxonomy/categories.yaml").read_text())
    taxonomy_example = taxonomy["categories"][0]["examples"][0]["fingerprint"]
    example = next(entry for entry in manifest["notes"] if entry["fingerprint"] != taxonomy_example)
    example["set"] = "TEST"
    path.write_text(json.dumps(manifest))
    (local_project / "prompts/fewshot_v1.yaml").write_text(
        yaml.safe_dump({"examples": [{"note_id": example["note_id"]}]}))
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 2, result.output
    assert json.loads(result.output)["checks"]["examples"]["status"] == "fail"


@pytest.mark.parametrize("source", ["taxonomy", "workbook"])
def test_doctor_checks_actual_examples_even_if_manifest_omits_pins(local_project, source):
    path = local_project / "data/bootstrap/split_manifest.json"
    manifest = json.loads(path.read_text())
    if source == "taxonomy":
        taxonomy = yaml.safe_load((local_project / "taxonomy/categories.yaml").read_text())
        fp = taxonomy["categories"][0]["examples"][0]["fingerprint"]
    else:
        import openpyxl

        rows, _ = load_export(local_project / "export.xlsx")
        note = list(group_notes(rows, 180).values())[1]
        fp = note.fingerprint
        workbook = openpyxl.load_workbook(local_project / "export.xlsx")
        workbook["Sheet1"].cell(2, 2, note.text)
        workbook.save(local_project / "export.xlsx")
        workbook.close()
        manifest["dataset_sha256"] = sha256_file(local_project / "export.xlsx")
    next(entry for entry in manifest["notes"] if entry["fingerprint"] == fp)["set"] = "TEST"
    manifest["pinned_to_train"] = []
    path.write_text(json.dumps(manifest))
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 2, result.output
    assert json.loads(result.output)["checks"]["split"]["status"] == "fail"


def test_doctor_collects_multiple_failures_and_never_trusts_an_approval_file(local_project):
    (local_project / "config/models.yaml").write_text("private-secret-from-bad-file")
    (local_project / "prompts/itemize_v1.md").unlink()
    (local_project / "taxonomy/approval.yaml").write_text("not a real approval")
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 2, result.output
    report = json.loads(result.output)
    assert report["checks"]["models"]["status"] == "fail"
    assert report["checks"]["prompt"]["status"] == "fail"
    assert report["artifacts"]["category_approval"]["status"] == "present_unverified"
    assert report["d3_status"] == "not_assessed"
    assert "private-secret-from-bad-file" not in result.output
