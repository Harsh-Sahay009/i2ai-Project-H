## Context

Components: Model Registry and Provider Interface (Model Router), Structured Response Parser and Amount Reconciler (Itemization Classifier), Output Formatter, KPI Calculator, Run Console. ADR 0014. Placement: the grammar, contracts and invariants are **common core**; models, budgets and tolerances are **configurable layer**. Position: **owned**, with models **accessed** through a **controlled** provider interface.

Authority: **recommend**. The tool proposes items and an outcome, and never decides payment.

## Goals / Non-Goals

**Goals:** D3's done-when conditions; nothing outside the grammar reaches a result; a new model takes one config entry; every number reproducible from a run folder.

**Non-Goals:** agent loop, guardrails, Web UI, registries, dashboard, training pipeline, calibrated confidence. Those come after D3.

## Decisions

### Contracts (`src/itemizer/contracts.py`)

Reuse `GoldItem`, `DisputeRow`, `Note` and `to_money` from `itemizer.bootstrap.data`; do not duplicate them. Add:

- `Basis` = `named_in_note` | `inferred_from_context` | `no_description`
- `ReasonCode` = `none` | `no_amount_stated` | `amount_unclear` | `charge_unclear` | `conflicting_amounts` | `instruction_in_note`
- `ChargeItem(GoldItem)`: adds `basis: Basis`.
- `NoteResult`: `fingerprint`, `note_id`, `items: list[ChargeItem]`, `no_charge_stated: bool`, `status` (`ok` | `review`), `review_reason` (`grammar_failed` | `evidence_failed` | `model_unsure` | `refused` | `provider_unavailable` | `budget_exhausted` | None), `reason_code: ReasonCode`, `attempts: int`, `model: str`, `cost_usd: Decimal`, `latency_ms: int`, `cached: bool`, `violations: list[str]`.
- `RowResult`: `row_id`, `note_id` (None for a blank note), `fingerprint` (None for a blank note), `shipment`, `invoice`, `carrier`, `status`, `reason`, `disputed`, `items_total`, `already_paid_total`, `difference`, `outcome`, `outcome_reason`, `repeated: bool`, `item_count: int`, `note: str`.
- `RunManifest`: `dataset_sha256`, `set_name` (`all` | `train` | `validation`), `limit`, `taxonomy_sha256`, `prompt_sha256`, `fewshot_sha256`, `grammar_version`, `model` (the full registry entry), `config_sha256`, `code_sha`, `code_commit`, `code_dirty`, `split_sha256`. `run_id` = `run_` + first 16 hex of the SHA-256 of its canonical JSON (sorted keys, no whitespace), leaving out `code_commit` and `code_dirty`, which are recorded but change no answer. `code_sha` is a hash of the source and the lockfile. `config_sha256` covers the settings that decide results and the notes the scan decision keeps back. It leaves out `budget` and `runtime`, because they change how a run goes and not what a finished answer says.
- `export_schemas(folder)` writes JSON Schemas for these models and the grammar to `contracts/schemas/`.

### Output grammar (`src/itemizer/grammar.py`)

An answer is exactly this, and nothing else:

```
Answer  := { "items": [Item, ...], "no_charge_stated": bool, "unsure": bool, "reason_code": ReasonCode }
Item    := { "category": <code in the approved list>, "amount": <digits "." two digits>,
             "evidence_text": <text copied exactly from the note>,
             "line_type": "charge" | "tax" | "already_paid",
             "derivation": "stated" | "rate_x_quantity",
             "basis": Basis }
```

The model writes no free prose anywhere. The `AI reason` column is rendered from `basis` by fixed sentences, so an explanation can never hold an invented amount.

Two layers enforce it:

1. **At the provider:** `answer_schema(codes)` returns a JSON Schema with `enum` lists and `additionalProperties: false` at every level. It avoids what Anthropic's structured output rejects: `pattern`, `minLength`, `maxLength`, `minItems`, `minimum`, `maximum`. Each adapter sends it in its provider's own form.
2. **In our parser, for every provider:** `parse_answer(raw_text, note, codes) -> ParseResult` where `ParseResult` has `answer` (items as `ChargeItem`) or `violations: list[Violation(code, detail)]`. It accepts only one JSON object with no surrounding text, and no extra or missing keys, then checks these rules:
   - `not_json`, `wrong_shape`: not one object of the exact shape.
   - `bad_amount`: amount must match `^\d{1,7}\.\d{2}$`.
   - `unknown_category`, `bad_line_type`, `bad_derivation`, `bad_basis`, `bad_reason_code`: outside the closed lists.
   - `too_many_items`: more than 12 items.
   - `flag_with_items`: `no_charge_stated` is true and items exist.
   - `empty_answer`: no items, not `no_charge_stated`, not `unsure`.
   - `evidence_not_verbatim`, `amount_not_in_evidence`, `product_mismatch`: from `itemizer.bootstrap.labels.check_item`, reused so that labels and the tool follow one rule.

`GRAMMAR_VERSION = "1"` goes into the manifest. Violations are never repaired: a rejected answer is retried once, with the violation codes appended to the request, and then the note goes to Review (`grammar_failed`, or `evidence_failed` if the only violations are evidence rules).

### Model registry and providers (`src/itemizer/providers.py`, `config/models.yaml`)

- `ModelSpec` fields: `name`, `provider`, `model`, `api_key_env` (optional), `base_url` (optional), `effort` (optional), `refusal_fallback: bool`, `max_tokens` (default 16000), `input_usd_per_mtok`, `output_usd_per_mtok`, `cache_read_usd_per_mtok`, `cache_write_usd_per_mtok`.
- `load_models(path) -> tuple[dict[str, ModelSpec], str]`: the entries and the default name.
- `Completion`: `text`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `stop_reason`, `latency_ms`.
- `Provider` protocol: `spec: ModelSpec` and `complete(system, user, schema) -> Completion`. Raises `ProviderError` on failure and `ProviderRefused` on a refusal.
- `get_provider(spec, client=None) -> Provider`, dispatching on `spec.provider` through a dict `ADAPTERS`. Adding an API family means one adapter class plus one line in `ADAPTERS`.
- `cost_usd(spec, completion) -> Decimal`.
- `load_secret(name, project_root) -> str`: the environment variable first, then `.env` in the project root, parsed with the standard library. It must never log, print or include the value in an error message. A missing secret raises `ContractError` naming the variable only.

Adapters:

- `AnthropicProvider`: `anthropic.Anthropic(api_key=...)`, then `client.beta.messages.create(model=, max_tokens=, system=[{"type":"text","text":system,"cache_control":{"type":"ephemeral"}}], messages=[{"role":"user","content":user}], output_config={"format":{"type":"json_schema","schema":schema}, "effort": spec.effort (if set)})`. When `spec.refusal_fallback`, add `betas=["server-side-fallback-2026-07-01"]` and `fallbacks="default"`. Do not send `temperature`, `top_p`, `top_k`, or `thinking`. `stop_reason == "refusal"` raises `ProviderRefused`; `max_tokens` raises `ProviderError`. Text is the first block with `type == "text"`. Usage comes from `usage.input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, summed over `usage.iterations` when present, because top-level usage covers only the attempt that produced the message. The cache marker sits on the system block because every request ends in a different note, so a marker after the note would never be read back. Map SDK errors to `ProviderError` with a most-specific-first chain (`anthropic.RateLimitError`, `APIStatusError`, `APIConnectionError`). The client's default retries stay on.
- `OllamaProvider`: standard-library HTTP POST to `{base_url}/api/chat` with `stream: false`, `format: schema`, `options: {temperature, num_predict: max_tokens}`, with `temperature` left out when the entry sets it to null. Tokens from `prompt_eval_count` and `eval_count`.
- `OpenAICompatibleProvider`: standard-library HTTP POST to `{base_url}/chat/completions` with `response_format: {"type":"json_schema","json_schema":{"name":"note_answer","strict":true,"schema":schema}}`, `temperature` from the entry (default 0, left out when null), `max_tokens`, `reasoning_effort` from `effort` when set, and a bearer token from `api_key_env`. Tokens from `usage.prompt_tokens` and `usage.completion_tokens`, less any cached or written prompt tokens the server reports. The HTTP adapters try again on a rate limit, a server error or a dropped connection, up to 4 attempts, honouring `Retry-After`. Tokens from `usage.prompt_tokens` and `usage.completion_tokens`.

`ProviderError` and `ProviderRefused` carry the call's usage when the provider reported it, so a cut-off answer or a refusal still counts against the budget. The HTTP adapters take an injectable `transport(url, headers, body) -> dict`, so tests need no network. One shared contract test runs against every adapter in `ADAPTERS`.

### Itemizer (`src/itemizer/itemize.py`)

- `build_system_prompt(categories, fewshots) -> str`: `prompts/itemize_v1.md` with the category list (code, name, definition, includes, excludes) and worked examples filled in. The result must be byte-stable so prompt caching works.
- `load_fewshots(path, notes, manifest)`: `prompts/fewshot_v1.yaml` holds `note_id`, items with offsets, and `source`. It holds no note text, and text is resolved from the dataset at runtime. It raises `ContractError` if any example note is not in TRAIN.
- `build_user_prompt(note) -> str`: the note in `<untrusted_note>` tags plus its disputed amount.
- `itemize_notes(notes, provider, codes, system, cache_dir, budget, concurrency, telemetry) -> dict[fingerprint, NoteResult]`: one call per distinct note on a thread pool, with results in a stable order. A cached answer costs nothing. The cache key is the SHA-256 of model name, model id, effort, `base_url`, `max_tokens`, `refusal_fallback`, system, user and schema, stored as JSON under `cache_dir/<model name>/`.
- `Budget(max_usd, max_minutes)`: thread-safe. Once either limit is reached, notes not yet started become Review with `budget_exhausted`. `ProviderError` after retries becomes Review with `provider_unavailable`; `ProviderRefused` becomes Review with `refused`. `unsure: true` becomes Review with `model_unsure`.
- `assign_rows(rows, note_results, policy) -> list[RowResult]`, in this order:
  1. Blank note: `no_charge_stated`, reason `empty_note`.
  2. Note status is `review`: `review`, with its `review_reason`.
  3. Answer is `no_charge_stated`: `no_charge_stated`, reason `no_charge_in_note`. Under `review.no_charge_stated_policy: review`, it becomes `review` instead.
  4. Compute `items_total` (charge + tax), `already_paid_total`, and `difference = disputed − (items_total − already_paid_total)`. If `|difference| > reconcile.abs_tolerance_usd`: `discrepancy`, reason `does_not_add_up`.
  5. It adds up and the row is flagged `repeated_invoice`, under `review.repeated_invoice_policy: flag_discrepancy`: `discrepancy`, reason `repeated_invoice`.
  6. Otherwise `verified`, reason `adds_up`.

Amounts are never changed at any step.

### Workbook (`src/itemizer/output.py`)

`write_workbook(path, row_results, note_results, categories, run_info)`:

- `Items`: `row_id`, `item`, `category`, `amount`, `evidence`, `outcome`, `ai_reason`. One line per charge per row. `category` shows the category name. `ai_reason` is a fixed sentence: "Already paid: subtracted from the items total." for an `already_paid` line; otherwise blank for `named_in_note`, "Category taken from the rest of the note." or "The note gives no description of this amount."
- `Row Summary`: `row_id`, `shipment`, `carrier_invoice`, `carrier`, `status`, `reason_code`, `disputed`, `items_total`, `already_paid`, `difference`, `outcome`, `outcome_reason`, `repeated`, `note`. `already_paid` is there so a row that adds up only after a payment shows why. `shipment`, `status` and `reason_code` drop the constant `PPGTM.` prefix. Discrepancy and Review rows are highlighted.
- `Largest`: one line per shipment, sorted by `largest_dispute` descending: `rank`, `shipment`, `rows`, `largest_dispute`, `total_on_rows`, `repeated_rows`, `share_of_total`, `cumulative_share`, `outcome`, `main_category`. Share uses each shipment's largest dispute, counted once. `outcome` is the worst across its rows (review, then discrepancy, then the rest). `main_category` is the name of the largest charge in its largest row. Shipments whose largest dispute is 0 or less are left out.
- `Run Info`: key and value lines from `run_info`.
- `Categories`: code, name, definition.

Amounts are numeric cells formatted to two decimals. Identical inputs produce byte-identical files: fix the workbook properties and rewrite the zip with fixed timestamps. `largest_shipments(row_results, note_results, categories)` is exposed for the summary page.

### KPI (`src/itemizer/kpi.py`)

Doc: `architecture/docs/04-kpi-calculator.md`.

- `coverage(row_results) -> dict`: covered means `verified`, `discrepancy` or `no_charge_stated`. Returns rows, dollars (the plain sum of `disputed`, matching the scope's $186,345) and both again without `repeated` rows.
- `match_note(predicted, gold, tolerance) -> dict`: `scipy.optimize.linear_sum_assignment`, with pair cost 0 when category and amount match, 1 when only one matches, 2 otherwise. A note is correct only if every gold item matches at cost 0 and nothing is extra. Returns correctness and counts of category errors, amount errors, missing and extra items. Two `no_charge_stated` notes with no items are correct.
- `accuracy(test_entries, note_results, gold, row_counts, stratum_shares, seed, resamples) -> dict`: covered notes only. Within a stratum, each note is weighted by its row count. `weighted = Σ_s π_s·acc_s / Σ_s π_s` over strata with covered notes. The interval is a seeded stratified bootstrap (2.5th and 97.5th percentiles). Also return n, the unweighted Wilson interval, per-stratum values, and values for formats seen and unseen in TRAIN.
- `stratum_shares(row_results, large_usd)`: from the run on all rows: `large` when `disputed ≥ large_usd`, else `multi` when `item_count ≥ 2`, else `single`.
- `invariants(row_results, note_results, notes, codes) -> dict`: re-run `check_item` on every accepted item, and return the violation count and evidence verifiability rate.
- `level_gate(level, coverage, accuracy, invariants, targets) -> dict` (Option A): each condition has `value`, `target`, `met`, `ci_low`, `ci_high`, `n`, `interval_contains_target`. The level is `pass` when all are met and invariant violations are 0. Otherwise it is `fail`, with reason `invariant_failed` when violations exist.
- `spend_test_budget(path, run_id, milestone, budget, results, extra_peek)`: a JSONL ledger. Re-scoring the same results at the same milestone is free, so labels corrected by the client can be re-scored without running the tool again. A new run, or new results under one run id, past the budget raises `ContractError`, and the refusal is logged. `extra_peek` spends past the budget on purpose: the reason is logged and the status page says TEST was scored more than once. Without it, a category renamed at approval would leave D3 with no way to score the run that uses the approved list. Milestones are a closed list, `kpi.milestones`, so a new name cannot open a fresh budget.
- `evaluate(...)` returns aggregates only and writes a snapshot under `data/kpi/`. It holds no note text, items or row ids for TEST. Per-carrier coverage uses carrier codes and counts. The snapshot records the digest of the results it scored and the run's code and input hashes.
- `pipeline.evaluate_run` refuses before any budget is spent: a run whose category list, worked examples, prompt, grammar or result-deciding settings changed after it ran; a run with notes that got no answer (`provider_unavailable`, `budget_exhausted`), which a repeat run recovers; and rows that do not follow from the note results and the dataset, which it checks by rebuilding them with `assign_rows`. The threat here is a stale folder or a slip. The ledger and digests make a hand edit visible, but do not prove the absence of one.

### Pipeline and commands (`src/itemizer/pipeline.py`, `compare.py`, `cli.py`)

- `run(root, model_name=None, set_name=None, limit=None, export=None) -> RunOutcome`. Files go to `data/runs/<run_id>/`: `manifest.json`, `note_results.json`, `row_results.json`, `telemetry.jsonl`, `itemized.xlsx`. `--set train|validation` runs only those notes and their rows. A run on all rows of the dataset file is refused until TEST is frozen, so labellers never see tool output on TEST notes. `--set test` does not exist. An export other than the dataset file is allowed; all its rows run, and its notes need no split. A copy of the dataset is recognised by its hash, so it follows the dataset's rule. Until TEST is frozen, another export holding TEST or reserve notes is refused. The recorded scan covers only the dataset file, so an external model refuses another export if the scan flags any of its notes; a local model is allowed. `--limit` needs `--set`.
- `compare_models(root, model_names, set_name="train", limit=None) -> dict`: same notes, same prompt, each model. For each model it reports valid-first-try rate, retry rate, Review share, Verified and Discrepancy shares, agreement with the first model on items, cost, mean latency, and the projected cost and minutes for all 729 notes. When TRAIN or VALIDATION labels exist, it adds accuracy on those notes as an aggregate. It refuses TEST. It writes `data/compare/<name>.json`, and prints aggregates only.
- Settings come from `config/run.yaml`. Missing budget settings stop the run, because treating them as zero would send every note to Review without saying why.
- Commands: `itemizer run`, `itemizer evaluate --run <id> --milestone d3`, `itemizer compare-models`, `itemizer models` (lists the registry), `itemizer acceptance d3`, `itemizer acceptance record-review`.
- Commands print counts and paths, never note text. A `ContractError` prints as a plain stop. Any other error prints its type only, because a library's message can quote a note, and `ITEMIZER_DEBUG=1` shows the rest. Crashes never show local variables, which can hold the key.
- Cost figures use the prices in force when an answer was first made, and the cache keeps them. Correcting a price in the registry does not change the cost reported for answers already cached.

### Provisional freeze (`src/itemizer/bootstrap/labels.py`, `cli.py`)

- `gt import-client --role team_provisional` lets a team member resolve disagreements in the review workbook.
- `gt seal --provisional` freezes TEST for evaluation: it requires the 200 notes, valid labels, a complete review by any role and the right mix, and accepts categories in the current list without approval. It writes `test_provisional.json` and `provisional_record.json`, and does not release the reserve.
- `gt seal`, with no flag, stays final and needs `client_owner` review and approval, as now. Final sealing is allowed after a provisional freeze.
- `is_test_frozen(ws)` and `load_test_gold(ws) -> (labels, status)` with `status` of `provisional` or `sealed`.

### D3 check (`src/itemizer/acceptance.py`)

`d3_check(root, run_id=None)` finds the latest run on all rows, reads its Level 1 snapshot, and writes `data/reports/d3_summary.html` and `.json`:

- **D1:** draft or approved, and the category count.
- **D2:** not frozen, provisional or sealed, with labelled note count and agreement.
- **D3:** end-to-end status; Level 1 conditions with values, intervals and n; the labels' status; client review recorded or missing.
- **Largest disputes:** the top 10 shipments, without note text.

D3 stays `open` until `acceptance record-review --date --evidence [--run]` records the client's review of this run (reason `client_review_missing`) and the labels are sealed (reason `labels_provisional`), because the result can still change when the client's labels are sealed. A score that no longer belongs to the run is not shown: the reason is `run_out_of_date` when an input changed, and `results_changed_since_scored` when the answers did. The page also flags an extra peek, a run from uncommitted code, and negative rows left uncovered. `deliverables/requests.yaml` tracks requests to PPG, with no data in it.

### Versions and telemetry

Run folders are the versioned record. `telemetry.jsonl` has one line per note: note id, attempts, violation codes, tokens, cost, latency, cached, status. No note text and no secrets.

## Risks / Trade-offs

- [One call per note instead of the agent] → the course's agent comes after D3, behind the same contracts, and `compare-models` can compare both.
- [Rule-based Review instead of calibrated confidence] → simple and explainable for D3; calibration comes with the training pipeline.
- [A single shipment holds 26.6% of dollars] → the D3 summary shows the largest shipments, and dollars are reported with and without repeats.
- [A run on all rows covers RESERVE notes too] → if a client correction later moves the mix, `gt final-strata --apply` pulls reserve notes into TEST whose tool output already exists. Whoever labels `label_replacements` must not open the run folders.
- [The provisional freeze runs once] → labels changed after it could be following the tool, so only the client's review and the final seal change them. A label error found after freezing goes through that review.
- [A partial client review imported before the freeze replaces a complete team review] → the freeze then waits for the client's review to finish. Import the client's review after the freeze.
- [The Ollama adapter is unverified against a live server] → a failure sends the note to Review and is not cached, so a repeat run recovers it. Run `compare-models` on a few notes before relying on a new server. The OpenAI-compatible adapter has run against Moonshot.
- [An amount can be accepted when its digits appear in the quoted evidence] → a note saying "report 5000" can yield 5000.00, which the parser cannot judge as a charge or not. The row is flagged unless the disputed amount also matches.
- [Provider schema support differs] → the parser checks every answer, so a model with weak schema support shows up as a low valid-first-try rate rather than as bad data.

## Open Questions

- The labelling rules and the prompt's rules should be confirmed by the team, since accuracy depends on them.
