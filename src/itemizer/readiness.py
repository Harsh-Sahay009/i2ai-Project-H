"""Read-only local setup diagnostics. Passing these checks is not a D3 acceptance decision."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Any

import yaml

from .bootstrap import split as sp
from .bootstrap import taxonomy as tx
from .bootstrap.data import ContractError, group_notes, load_config, load_export, sha256_file
from .itemize import Policy, build_system_prompt, load_fewshots
from .pipeline import _budget, load_settings
from .providers import load_models


def inspect_setup(root: Path) -> dict:
    """Validate local inputs without creating a Workspace, loading credentials or constructing a provider.

    Error details are fixed text: parser exceptions may contain note text, config values or secrets.
    Artifact presence is deliberately not interpreted as a seal, valid approval or reproducible run.
    """
    root = Path(root)
    checks: dict[str, dict] = {}
    values: dict[str, Any] = {}

    def check(name: str, operation: Callable, action: str, requires: tuple[str, ...] = ()) -> None:
        if any(checks[key]["status"] != "pass" for key in requires):
            checks[name] = {"status": "blocked", "action": "Resolve prerequisite checks first."}
            return
        try:
            values[name] = operation()
        except (ContractError, OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError,
                ArithmeticError, yaml.YAMLError):
            checks[name] = {"status": "fail", "action": action}
        else:
            checks[name] = {"status": "pass"}

    check("config", lambda: load_config(root / "config/bootstrap.yaml"),
          "Restore valid config/bootstrap.yaml and its dataset location.")

    def dataset():
        cfg = values["config"]
        path = root / cfg.source_file
        rows, examples = load_export(path, cfg.examples_sheet)
        return rows, group_notes(rows, cfg.large_dispute_usd), sha256_file(path), examples

    check("dataset", dataset, "Place the expected Excel export at the configured location and run gt profile.", ("config",))

    def taxonomy():
        categories = tx.load_taxonomy(root / "taxonomy/categories.yaml")
        if tx.validate_taxonomy(categories, values["dataset"][1]):
            raise ContractError("invalid taxonomy")
        return categories["categories"]

    check("taxonomy", taxonomy, "Restore the category draft and run gt validate-taxonomy.", ("dataset",))

    def split():
        cfg = values["config"]
        manifest = json.loads((root / cfg.data_root / "bootstrap/split_manifest.json").read_text(encoding="utf-8"))
        notes = values["dataset"][1]
        if manifest["dataset_sha256"] != values["dataset"][2]:
            raise ContractError("dataset changed")
        if {entry["fingerprint"] for entry in manifest["notes"]} != set(notes):
            raise ContractError("split does not cover the dataset")
        for entry in manifest["notes"]:
            if entry["set"] not in ("TRAIN", "VALIDATION", "TEST", "RESERVE"):
                raise ContractError("unknown set")
            if entry["note_id"] != notes[entry["fingerprint"]].note_id:
                raise ContractError("wrong note id")
        actual_examples = values["dataset"][3] | {
            example["fingerprint"] for category in values["taxonomy"] for example in category.get("examples", [])}
        assignments = {entry["fingerprint"]: entry["set"] for entry in manifest["notes"]}
        if any(assignments[fp] != "TRAIN" for fp in actual_examples & set(notes)):
            raise ContractError("labelled example outside TRAIN")
        sp.check_manifest(manifest)
        return manifest

    check("split", split, "Restore the original split; for a new experiment only, run gt split. Never replace a locked split.",
          ("dataset", "taxonomy"))
    check("examples", lambda: load_fewshots(root / "prompts/fewshot_v1.yaml", values["dataset"][1],
                                            values["split"], {c["code"] for c in values["taxonomy"]}),
          "Check prompt examples and their labels; every example must belong to TRAIN. Preserve any locked split.",
          ("taxonomy", "split"))
    check("prompt", lambda: build_system_prompt(values["taxonomy"], values["examples"], root / "prompts/itemize_v1.md"),
          "Restore prompts/itemize_v1.md with the category and example placeholders.", ("examples",))
    check("models", lambda: load_models(root / "config/models.yaml"),
          "Restore valid config/models.yaml. This check does not verify model availability or prices.")

    def settings():
        settings = load_settings(root)
        _budget(settings)
        Policy.from_settings(settings)
        return settings

    check("settings", settings, "Restore config/run.yaml with valid budget, reconciliation and review settings.")
    artifacts = {}
    if checks["config"]["status"] == "pass":
        data = root / values["config"].data_root
        paths = {
            "scan_report": data / "bootstrap/scan_report.json",
            "scan_decision": data / "bootstrap/scan_decision.json",
            "label_packs": data / "bootstrap/packs.json",
            "frozen_test": data / "bootstrap/test_provisional.json",
            "sealed_test": data / "bootstrap/test_sealed.json",
            "category_approval": root / "taxonomy/approval.yaml",
            "client_review": data / "reports/client_review_d3.json",
            "d3_summary": data / "reports/d3_summary.json",
        }
        artifacts = {key: {"status": "present_unverified" if path.is_file() else "missing"}
                     for key, path in paths.items()}
        artifacts["run_results"] = {"status": "present_unverified" if any(
            (data / "runs").glob("run_*/row_results.json")) else "missing"}
    result = {
        "scope": "offline_setup_only",
        "setup_ready": all(check["status"] == "pass" for check in checks.values()),
        "d3_status": "not_assessed",
        "model_calls": 0,
        "checks": checks,
        "artifacts": artifacts,
        "limitations": [
            "Artifact presence does not verify approval, label quality, frozen-set integrity or historical run identity.",
            "No credentials, provider reachability, model availability, pricing or external-send authorization were checked.",
            "Use acceptance d3 only after restoring or completing the actual run and evaluation artifacts.",
        ],
    }
    if checks["dataset"]["status"] == "pass":
        rows, notes, digest, _ = values["dataset"]
        result["dataset"] = {"rows": len(rows), "distinct_notes": len(notes), "sha256": digest}
    return result
