## Why

D3 must run end to end on the export and meet Level 1 on the test set, and the team will present D1, D2 and D3 together. The full plan cannot be built in time, so this change builds the shortest path that meets D3's done-when conditions. Two requirements shape it. The model's output must follow a controlled grammar, so nothing outside the agreed format can reach the accountant. And the team must be able to test other models easily, without changing code.

## What Changes

- **Output grammar:** every model answer must fit one strict format with closed value lists. Providers enforce it where they can, and one parser checks every answer whichever model wrote it.
- **Model registry:** models are listed in `config/models.yaml`. Adding a model on a known API takes one entry, and `itemizer compare-models` runs several on the same notes.
- **Itemizer:** one model call per distinct note, with the deterministic checks from the scope: exact evidence, amounts never edited, rows that do not add up are flagged.
- **Workbook:** `Items`, `Row Summary`, `Largest`, `Run Info` and `Categories` sheets, using the simpler layout the team asked for.
- **Level gates:** coverage from a run on all rows, accuracy from TEST, pass or fail on the measured value with the interval beside it (Option A).
- **Provisional freeze:** because D1, D2 and D3 are presented together, TEST can be frozen on team-resolved labels first, and sealed after the client's review.
- **D3 summary:** one page showing D1, D2 and D3 status for the presentation.

## Capabilities

### New Capabilities
- `output-grammar`: the answer format, its closed lists, the provider-independent parser and retries.
- `model-registry`: model entries, provider adapters, secrets, costs and comparing models.
- `d3-itemization`: note itemization, caching, budgets, row outcomes and the run command.
- `d3-output`: the workbook layout and the largest-disputes view.
- `level-evaluation`: Level gates, TEST budget and provisional freezing.
- `d3-presentation`: the D3 check and one-page status summary.

### Modified Capabilities
<!-- none: related changes are not archived. add-itemization-classifier, add-model-router, add-output-formatter, add-run-console and add-kpi-calculator build on this later. -->

## Impact

- New modules under `src/itemizer/`, new `config/models.yaml` and `config/run.yaml`, new `prompts/` folder. Adds `scipy`.
- Left until after D3: agent loop, guardrails, Web UI, registries, dashboard, training pipeline. Their later changes replace parts of this path behind the same contracts.
- C4: components Model Registry (Model Router), Model Comparison Runner (Run Console), and the Structured Response Parser (Itemization Classifier) becomes the grammar parser. ADR 0014.
