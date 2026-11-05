# D3 Readiness Implementation Plan

> Execute inline, task by task, with verification checkpoints. Use the systematic-debugging, test-driven-development and verification-before-completion skills for code changes.

**Goal:** Make the existing prototype reproducible from the supplied workbook and prepare honest D3 review materials.

**Architecture:** Retain the CLI, bootstrap contracts, extraction and KPI code. Correct the split's prompt-example inputs; add a read-only readiness command. Keep real data and generated artifacts ignored.

**Tech Stack:** Python, Typer, Pydantic, PyYAML, existing Excel pipeline and pytest.

## 1. Establish baseline

- [x] Clone implementation branch into the class workspace and create `codex/d3-readiness`.
- [x] Install locked dependencies; profile, scan and validate the supplied workbook.
- [x] Preserve the reconstructed split under ignored storage before any correction.
- [x] Run `uv run pytest -q` to completion; record results without claiming historical model results were reproduced.

## 2. Fix example leakage during reconstruction

Files: `src/itemizer/cli.py`, `tests/test_bootstrap.py`.

- [x] Add a CLI regression test that first constructs a split, picks a held-out note as a prompt example, reruns `gt split --force`, and requires that note to be TRAIN and pinned.
- [x] Add tests that malformed/unknown prompt references fail without changing an existing split and that locked packs prevent repartitioning.
- [x] Run `uv run pytest -q tests/test_bootstrap.py -k prompt_example`; require failures before changing implementation.
- [x] Before `build_split`, read `prompts/fewshot_v1.yaml` when present, validate its `examples` list and each `note_id`, map IDs to dataset fingerprints, and add them to `pinned`. Use fixed error messages without echoing untrusted values.
- [x] Rerun regressions, then `uv run itemizer gt split --force` only on this unlocked local reconstruction. Require `load_fewshots` to validate all 12 examples.

## 3. Add local diagnostics

Files: `src/itemizer/readiness.py`, `src/itemizer/cli.py`, `tests/test_readiness.py`.

- [x] Test a missing-config checkout: structured setup failure, no new files, no secrets or model calls.
- [x] Test an invented valid project: required setup passes; missing labels/runs stay missing, with no fabricated D3 pass.
- [x] Test stale/malformed split and held-out prompt examples: specific diagnostic failures with no note text and no file changes.
- [x] Run `uv run pytest -q tests/test_readiness.py`; require red before implementation.
- [x] Implement `inspect_setup(root)` with existing `load_config`, `load_export`, `group_notes`, taxonomy/split validation, `load_fewshots`, `build_system_prompt`, model registry and policy validation. Catch errors into fixed diagnostic messages, skip dependent checks after prerequisite failures, and avoid constructing `Workspace`.
- [x] Register `doctor` to print JSON and exit 2 on failed setup checks. Inventory private artifacts as `missing` or `present_unverified` separately from setup status.
- [x] Require tests to pass and run `uv run itemizer doctor` on the real local reconstruction.

## 4. Prepare handoff and human review

Files: `README.md`, `deliverables/d3_readiness.md`; generated outputs under ignored `data/`.

- [x] Document fresh-clone setup, doctor semantics, original-artifact recovery, human labeling, and model-run prerequisites.
- [x] Produce D1 HTML and blind packs using `gt approval-doc` and `gt label-packs` on the corrected local reconstruction; verify sheet structure and note memberships without importing labels.
- [x] Produce `itemizer acceptance d3` with its actual open state. Do not substitute historical metrics.
- [x] Write a D3 checklist and short demonstration script, with historical-versus-local evidence clearly labeled and proposed review roles explicitly unassigned.
- [x] Record unresolved accounting/data-use questions and the required original artifact handoff.

## 5. Verify and report

- [x] Run new tests and the complete suite after code changes; inspect failures before any fix.
- [x] Review diff and check ignored data with `git status --short`, `git diff --check`, and `git check-ignore`.
- [x] Summarize exact completed work, test evidence, artifact locations, and remaining human inputs. Keep work on the local branch; no merge or external messaging.

## Verification checkpoint

All 884 tests passed in 226.33 seconds on 4 November 2026. All 12 prompt examples validate in TRAIN; doctor reports local setup ready and D3 not assessed. Generated acceptance remains open with no local full-data run. Six blind packs passed membership/blank-cell/dropdown/filter checks and visual review; clipping in headers was corrected in the existing pack formatter. Independent code review found no remaining actionable issues. All source work remains on the local readiness branch; no model calls, client messages, approvals, human labels or historical-result claims were fabricated.
