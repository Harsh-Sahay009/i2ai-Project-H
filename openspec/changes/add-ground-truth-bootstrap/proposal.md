## Why

D1 (due 15 Oct) and D2 (due 22 Oct) are late, and D3 on 5 Nov must be measured on D2. `add-ground-truth-store` only stores and checks these sets. Nothing creates their content, and that change depends on foundation changes that come first in the build order. The team needs a small tool it can run now.

The tool does most of the work, with one limit: **people write the TEST labels.** The scope says two people label 50 notes without seeing the tool's output, and the set "is never used to tune the tool". Accuracy measured against labels the tool wrote would only show the tool agreeing with itself.

## What Changes

- Profile the dataset file, the source of every partition, and scan it for remaining names, phone numbers and emails.
- Build the TRAIN / VALIDATION / TEST split by distinct note, drawing TEST first (ADR 0012).
- **D1:** draft 12 to 20 categories with definitions and real examples from TRAIN notes using the LLM, let the team edit the draft, generate a two-page approval document and record Jake's written approval.
- **D2:** generate labelling workbooks with no tool output, validate returned labels, compute agreement, generate the client review workbook for the 50 double-labelled notes, and seal TEST when every check passes.
- Prepare TRAIN and VALIDATION labelling, which D3 needs for few-shot examples and calibration.

## Capabilities

### New Capabilities
- `dataset-profile-split`: dataset profile, anonymization scan, provisional strata, reserve, split manifest.
- `taxonomy-drafting`: LLM draft of the category list, verbatim example check, approval document, approval record.
- `test-set-preparation`: labelling packs, label validation, agreement report, client review, sealing.

### Modified Capabilities
<!-- none -->

## Impact

- New package `itemizer.bootstrap` with a standalone CLI `itemizer gt` (Typer, openpyxl, pydantic, an optional LLM client). Files under `${runtime.data_root}/bootstrap` and `taxonomy/categories.yaml`.
- Depends on no other change, so it can start immediately. `add-ground-truth-store` and `add-version-artifact-registry` register its outputs later. `add-human-review-system` reuses its pack builder and validator.
- C4: container `bootstrap` and view `Components-GroundTruthBootstrap`. ADR 0012, ADR 0013.
- Needs time from people: the team labels the notes, and Jake or a PPG accountant approves D1 and reviews 50 notes.
