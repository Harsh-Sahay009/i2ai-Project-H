## Why

The team has decided that Claude Opus drafts the 200 TEST labels, so that D3 can be measured before the 5 November presentation. Labels written by the same model the tool uses cannot show that the tool is right, only how far it agrees with them. So a model's label must be marked as one wherever it counts, a person must be able to check and correct it through a supported path, and the labels can only become final once people have checked them.

## What Changes

- **Model-drafted TEST labels:** `itemizer gt draft-test-labels --send` has Opus label the TEST packs through the API. It uses the labelling rules and never sees tool output. Each label goes through the same checks as a person's, and is stored with `source = model_draft`.
- **Marked everywhere:** the freeze record, KPI snapshot and status page all say how many labels are model drafts, and the page says what that means for accuracy.
- **Human review:** `gt label-review-pack` writes every TEST label to a workbook, and `gt import-label-review` takes back what people checked or changed. Corrections to a frozen test set are now possible, and re-scoring the same run stays free.
- **Final seal:** `gt seal` refuses while any TEST label is an unchecked model draft.
- **Instruction file:** `deliverables/reviewing_test_labels.md` explains how to go through the labels and run the test again.
- **Amends the earlier rule:** `add-ground-truth-bootstrap/test-set-preparation` said people write every TEST label. That spec is edited in place, because the change is not archived, and ADR 0015 records the decision.

## Capabilities

### New Capabilities
- `model-drafted-labels`: drafting TEST labels with a model, and marking them as drafts wherever they count.
- `test-label-review`: the review workbook, importing checks and corrections, re-freezing, and re-scoring.

### Modified Capabilities
<!-- none in openspec/specs: test-set-preparation belongs to add-ground-truth-bootstrap, which is not archived, so it is edited there. -->

## Impact

- New `src/itemizer/model_labels.py`, `prompts/label_v1.md`, two labeller entries in `config/models.yaml`, and `deliverables/reviewing_test_labels.md`.
- `bootstrap/labels.py`, `bootstrap/data.py`, `kpi.py`, `acceptance.py` and `cli.py` change.
- The scope says the team labels the 200 notes and Jake reviews 50, so this goes on the scope change list.
- VALIDATION is unchanged: people still label it, blind.
