## 1. Plan and decision

- [x] 1.1 Write ADR 0015 and amend ADR 0012 and the `test-set-preparation` spec
- [x] 1.2 List the change on the scope page

## 2. Settings

- [x] 2.1 Set `budget.max_usd_per_run` to 20.00
- [x] 2.2 Mark the worked examples as confirmed (`add-d3-thin-path` task 7.3)

## 3. Model-drafted labels

- [x] 3.1 Add `source` values, the `model_draft` marker and `prompts/label_v1.md`
- [x] 3.2 Implement `model_labels.draft_test_labels` and `gt draft-test-labels`, with two labeller entries in the registry
- [x] 3.3 Count drafts in the snapshot and on the status page
- [x] 3.4 Refuse the final seal while drafts remain
- [x] 3.5 Tests per scenario in `model-drafted-labels`, on invented notes with no network

## 4. Label review

- [x] 4.1 Implement `gt label-review-pack`
- [x] 4.2 Implement `gt import-label-review`, with the frozen labels updated
- [x] 4.3 Write `deliverables/reviewing_test_labels.md`
- [x] 4.4 Tests per scenario in `test-label-review`, on invented notes with no network
- [x] 4.5 Implement `gt rename-category`, and refuse the workbook and import while labels hold an old code

## 5. Live

- [x] 5.1 Draft the TEST labels with Opus, freeze, run on all rows and evaluate
- [x] 5.2 Check the review workbook round trip on the real labels, with no change to any label
- [x] 5.3 Record cost and results as aggregates in `add-d3-thin-path/live-check.md`
