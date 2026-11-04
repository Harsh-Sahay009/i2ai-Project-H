## Context

ADR 0012 said people write TEST labels, because "accuracy measured against labels the tool wrote would only show the tool agreeing with itself". That risk remains. The team accepts it for now, so that D3 can be measured, and will review the labels afterwards. Components: Ground Truth Bootstrap (Labelling Pack Builder, Label Validator & Sealer), KPI Calculator, Run Console (Acceptance Runner).

Placement: the label checks and the rule that a draft cannot be sealed are **common core**. Which model drafts is **configurable layer**. Position: labels are **owned**, and the model is **accessed** through the **controlled** provider interface.

Authority: **recommend**. A model draft is a proposal for a person to check, and is never final.

## Goals / Non-Goals

**Goals:** 200 valid TEST labels from Opus, with no tool output in the prompt. Every number that rests on them says so. People can check and correct any label, at any time before the final seal, and re-score with no new model calls.

**Non-Goals:** model-drafted VALIDATION labels; changing the balance-due rule, which stays as written until the team decides; proving the labels are right.

## Decisions

### Drafting (`src/itemizer/model_labels.py`)

`draft_test_labels(root, first_model, second_model, today)`:

1. Runs the external-send checks in `pipeline`, and takes one `Budget` from `budget.max_usd_per_run` for the whole job.
2. Calls `itemize_notes` for `label_A` and `label_single` with `first_model`, and `label_B` with `second_model`, using the system prompt from `prompts/label_v1.md`. That prompt holds `labels.INSTRUCTIONS` and the category list, and no worked examples, so the labeller and the tool share rules but not a prompt. Answers are cached under `data/cache/labels/`, so a repeat costs nothing.
3. Writes each answer into a copy of the blank pack under `data/bootstrap/packs/filled/`, and imports it with `lb.import_labels`. Going through the workbook means a model's label passes exactly the checks a person's does.
4. Writes the client pack, which computes agreement, and accepts labeller A on all 50 double-labelled notes, with role `model_provisional`. Disagreements come first in the review workbook.

Why not read TEST notes in the session and write labels by hand? That would put TEST text in the developer's context, and could not be repeated or costed.

Two registry entries, `refusal_fallback: false` so that every label really is from Opus: `claude-opus-5-5-label-high` (effort `high`, labeller A and the single-labelled notes) and `claude-opus-5-5-label-xhigh` (effort `xhigh`, labeller B). Two passes of one model are not independent people, so their agreement says little, and the page does not present it as more.

The prompt says never to answer `unsure`: a label must exist. Doubt goes in `reason_code` and reaches the label's `comment`, so people check those notes first. A note with no valid answer stays unlabelled, the import reports it, and the freeze stops.

### Marking

`NoteLabel.source` gains `model_draft`, `person_checked` and `person_corrected`. `parse_lines` reads the marker `model_draft` from the comment column, which only `model_labels` writes. A client's `accept_A` or `accept_B` on a draft makes it `person_checked`.

`kpi.evaluate` adds `labels_sources` to the snapshot. `acceptance` shows the counts under D2 and flags any drafts beside the Level result. D3 can only be `done` on sealed labels, and sealing needs every draft checked, so a draft can never reach `done`.

### Review (`bootstrap/labels.py`)

- `write_label_review(ws, notes, categories)` writes `packs/test_label_review.xlsx`: the pack's columns, plus `priority` and `checked`. It holds the current label for each TEST note and no tool output. Notes come in the order disagreement, model doubt, large, multi-charge, no charge, then the rest.
- `import_label_review(ws, path, reviewer, date, notes, codes)`: a note counts as reviewed if `checked` is `Y` or if its label differs from the current one, so a changed label is never ignored because someone forgot the flag. Reviewed notes become `person_checked` or `person_corrected`, with labeller `person:<reviewer>`. Any failure rejects the whole file, and nothing changes.
- It accumulates in `labels/test_label_review.json` and logs each import to `labels/test_label_review_log.jsonl`. `gold_labels` applies it after a model's review, and a client's decisions still win. A note the client decided is refused. Where the team corrected one of the 50 notes, the client's workbook shows it in `team_correction`, and `accept_correction` keeps it.
- After a provisional freeze, the frozen file is updated for the reviewed notes only, and its record gets the new hash, `checked_by_person` and `corrected_after_freeze`. So a client review imported after the freeze still waits for the final seal. A sealed TEST refuses, as before.

### Renaming a category

`gt rename-category <old> <new> [--merge]` changes the code in `taxonomy/categories.yaml`, `prompts/fewshot_v1.yaml`, every `labels/*.json`, `client_review.json` and `test_provisional.json`, updates the frozen record's hash, keeps each label's `source`, and logs to `labels/category_renames.jsonl`. It validates the new list first, so a refusal changes nothing. The review workbook and its import refuse while a current label holds a code outside the list, because find-and-replace there would mark unread drafts as `person_corrected` and pass the final seal's check. A split still needs a person to choose for each note.

### Running the test again

Only labels changed: `itemizer evaluate` re-scores the same run with no model calls and no budget. Categories, prompt or settings changed: the run is out of date, so a new `itemizer run`, then `evaluate --extra-peek "<reason>"`. Both are existing behaviour, and the instruction file explains them.

### Versions and telemetry

Label provenance is on each label (`labeller`, `source`, `comment`). Pack hashes are in `labels/<pack>.json`. Calls go to `data/bootstrap/labels/<pack>.telemetry.jsonl` with counts, cost and codes only. Review imports go to the log above. The snapshot records `labels_sha256` and `labels_sources`.

## Risks / Trade-offs

- [The labeller and the tool are the same model with the same rules] → accuracy reads high and shows agreement, not truth. The page says so until people have checked the labels.
- [Correcting labels after a run exists] → a reviewer who has seen the tool's answers could follow them. The review workbook holds no tool output, the instruction file says not to open run folders, and the record counts corrections made after the freeze.
- [A rule the team later changes, such as balance due] → the affected labels must be corrected, and the prompt change needs a new run with `--extra-peek`.
- [Reviewers mark everything `Y` without reading] → the tool cannot detect it. The log records who and when.
