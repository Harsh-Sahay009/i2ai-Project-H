# Integration and received-label review — 5 November 2026

Local branch: `codex/integrate-latest`, based on upstream `main` at `5720718`, with the readiness changes from `9e3a406` retained. Nothing is pushed or merged into remote main by this work. The reliable working copy is `/Users/harshsahay/.codex/workspaces/i2ai-Project-H`; the prior Desktop checkout remains intact.

## Integrated behavior

The local upload UI, category-renaming workflow, updated KPI reporting and Kimi adapter/comparison from Alejandro are retained. Our prompt-example split correction, read-only doctor and labeling layout improvements are retained. Only README conflicted; the current upstream guide is preserved with readiness/restoration instructions and runnable `uv run` commands. The November 4 readiness record is kept as a dated checkpoint with an explicit update.

## Received file

The original `test_provisional.json` is copied unchanged to ignored `data/incoming/alejandro/`. SHA-256: `f1c566fe2bf036088765db61ecd0cd8e6f84ea8822416ada6bc21d067ab33697`.

It has 200 labels and 279 items. Every source is `model_draft`; no human verification is asserted. Labels match dataset note identities and their evidence/amount contracts. Its strata are 103 single, 47 multi and 50 large; three notes are marked no-charge. Only 77 labels overlap the reconstructed local TEST set. The original file has no split manifest or freeze provenance record.

## Portable review workbook

`data/incoming/alejandro/test_label_review_portable.xlsx` contains the 200 original notes, draft labels, category definitions, instructions and blank `checked` cells. It includes 200 extra blank item lines, one per note. The original model doubt/large-dispute priorities are carried over; disagreement priority cannot be reconstructed because the two-pass agreement record was not supplied.

The workbook is a standalone review aid. It is **not** imported into the reconstructed experiment, and its existence does not create a seal, freeze or approval. Human reviewers may read/correct these original labels now. Preserve a backup and record actual reviewer identities. Use the supported review import only after the matching original split and review records are restored; never mark the drafts reviewed programmatically.

## Still needed to reproduce Alejandro's result

Recover original `data/bootstrap/` (split, provisional record, packs, labels, agreement and scan decision), `data/runs/`, `data/kpi/`, `data/reports/`, and actual approval evidence if present. Keep them as one consistent experiment. No missing records were fabricated and no original labels were changed.

## Local environment and checks

The integrated dependency set includes UI and LLM extras. In the Desktop checkout, macOS marked the editable package `.pth` hidden, which Python 3.14 skips; a local path file temporarily repaired discovery. iCloud subsequently offloaded Git configuration/index and other files, stalling operations. The working copy was recreated outside Desktop with the available private artifacts and source changes preserved. Cloud placeholders remain in the intact old checkout. The two offloaded aggregate profile/scan reports were regenerated from the identical supplied workbook; split membership and labels were not regenerated. The new environment imports the package normally without the workaround. The local web homepage returned HTTP 200 at `http://127.0.0.1:8899/`; no paid run was started.

Doctor passes on the preserved local reconstruction. The portable workbook was checked against source-derived contents after export, with empty strings normalized to empty cells: 200 note IDs, 279 items, 479 body rows, zero checked cells, five dropdown validations, frozen header/ID column and no formula cells. Previews of instructions, labels, review controls and categories were visually inspected. No model calls or external messages were made.

Verification on the stable checkout: the full integrated suite collected 994 tests and finished with 993 passing and one failure in the default-port test because the running demo occupied port 8899. After stopping the demo, all three port/host command checks passed (including that failed test) in 7.50 seconds. No source changes were needed for this environmental collision. Thus every collected test has passing evidence, though the full invocation itself was not all green. Independent source review found no blockers and `git diff --check` passes for the local changes. Existing upstream whitespace-only warnings are not extraction defects. Stop the demo before a future complete test run.
