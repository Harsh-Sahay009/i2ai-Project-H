# D3 readiness design

The team selected prototype and D3 readiness first on 4 November 2026. Work builds on `d1-d2-d3-thin-path` at `63f440d`, on a separate local branch. No payment decisions, client approvals, human labels, or measured accuracy will be invented.

## Outcome

A fresh checkout can validate the supplied workbook, construct an uncontaminated development/test split, explain its prerequisites, and prepare materials for human review. Extraction and KPI policies stay unchanged. The UI and agent architecture remain outside this increment.

## Observed problem

The current `gt split` pins notes from the example sheet and taxonomy, but misses prompt examples. Reconstructing from the supplied workbook places two prompt examples in TEST and one in VALIDATION. `load_fewshots` correctly rejects that split. Pin every existing prompt example to TRAIN before partitioning, reject malformed or unknown references, and preserve the existing lock on splits after packs or labels exist.

## Readiness command

`itemizer doctor` prints aggregate JSON using local files only. It validates configuration, dataset, taxonomy, split and prompt examples with existing contracts. It inventories frozen labels, historical runs and approvals without treating presence as validity or approval. It does not create directories, read API keys, call providers, alter labels, spend TEST budget, or claim a provider is reachable. Setup diagnostics exit 2 if a required local setup check fails, otherwise 0; passing setup is explicitly distinct from completing D3.

## Evidence and review materials

Keep the supplied workbook and all material containing its notes under ignored storage. Save the pre-fix split before reconstructing. Label new packs and summaries as a local reconstruction, not the original experiment. Generate D1 and blind labeling materials through existing product commands. Do not generate AI labels or send client text externally in this increment. Historical model metrics are attributed to Alejandro's report and are never presented as independently reproduced.

## Acceptance

- Regression tests fail before the split correction and pass afterwards, including a locked-split case.
- All prompt examples belong to TRAIN in the corrected local reconstruction.
- Doctor is read-only, reports multiple missing prerequisites, exposes neither note text nor secrets, and distinguishes setup from D3 completion.
- The full existing suite completes, and new tests pass.
- README contains executable setup and recovery paths; D3 notes state open human/client decisions.
- No workbook, note text, label or key is tracked by Git.

## Remaining external inputs

Only the workbook is available. Recover Alejandro's original `data/bootstrap`, `data/runs`, `data/kpi`, `data/reports`, and relevant approval records to reproduce his experiment. If unavailable, use the explicitly new reconstruction and perform independent labeling. Jake must resolve balance-due interpretation, data-use approval, category approval and client review; no such decision is recorded on his behalf.
