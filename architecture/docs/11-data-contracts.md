# 11. Data contracts

Every stage reads and writes one of the shapes below. They are **common core**: no setting changes them, and changing one is a change to `GRAMMAR_VERSION` or to the code a run records in its manifest.

The code is in `src/itemizer/bootstrap/data.py`, `contracts.py` and `grammar.py`. `contracts/schemas/` holds the JSON Schemas, and a test fails if they drift from the code. Every example here is invented.

## 11.1 Where each contract sits

| Contract | Written by | Read by | Stored at |
|---|---|---|---|
| Input row (`DisputeRow`) | The TMS export | Everything | The export file, outside Git |
| Note (`Note`) | `group_notes` | Split, labels, itemizer | Rebuilt from the export |
| Split manifest | `gt split` | Every command that touches notes | `data/bootstrap/split_manifest.json` |
| Gold label (`NoteLabel`, `GoldItem`) | People, through `gt import-labels` and `gt import-client` | KPI Calculator | `data/bootstrap/test_sealed.json` or `test_provisional.json` |
| Answer (`Answer`) | A model | The parser | `data/cache/llm/<model>/` |
| Note result (`NoteResult`) | Itemizer | Row outcomes, workbook, KPI Calculator | `data/runs/<run_id>/note_results.json` |
| Row result (`RowResult`) | Row outcomes | Workbook, KPI Calculator | `data/runs/<run_id>/row_results.json` |
| Run manifest (`RunManifest`) | `itemizer run` | `evaluate`, `acceptance` | `data/runs/<run_id>/manifest.json` |
| Workbook | `itemizer run` | Accountants | `data/runs/<run_id>/itemized.xlsx` |
| KPI snapshot | `itemizer evaluate` | `acceptance d3` | `data/kpi/<run_id>_<milestone>.json` |
| Uploaded file | The local page | `itemizer run`, through the page | `data/uploads/<sha256>.xlsx` |

Everything under `data/` is ignored by Git, because this repo is public. Only code, settings, prompts with offsets, and aggregates are tracked.

## 11.2 Input

An export needs these columns, and a missing one stops the command.

| Field | Column | Notes |
|---|---|---|
| `shipment` | `SHIPMENT_GID` | Shown without the constant `PPGTM.` prefix |
| `invoice` | `Carrier Invoice` | |
| `carrier` | `Carrier` | |
| `event_date` | `Event Date` | |
| `estimated` | `Shipment Amount` | |
| `billed` | `Invoice Amount` | |
| `disputed` | `Delta` | Read as cents, in `Decimal` |
| `status` | `Dispute Status` | |
| `reason` | `Reason Code` | |
| `note` | `Descritipion` | The source file spells it this way |
| flags | `Invoice Dups Removed` | Gives `repeated_invoice`. `empty_note` and `non_positive_delta` come from the row itself |

`row_id` is `R` plus the export row number, because no ID column identifies a row. A note's `fingerprint` is the SHA-256 of its normalized text, and `note_id` is `n_` plus its first 8 characters. Rows sharing a fingerprint share one model call.

A gold label records where it came from in `source`: `human`, `model_suggestion_confirmed` (TRAIN), `model_draft` (ADR 0015), `person_checked` or `person_corrected`. A `model_draft` cannot be sealed.

## 11.3 The answer: the controlled grammar

A model's answer is exactly this, with no other text:

```
Answer := {"items": [Item, ...], "no_charge_stated": bool, "unsure": bool, "reason_code": ReasonCode}
Item   := {"category": <code in the approved list>, "amount": "<digits>.<2 digits>",
           "evidence_text": <text copied exactly from the note>,
           "line_type": "charge" | "tax" | "already_paid",
           "derivation": "stated" | "rate_x_quantity",
           "basis": "named_in_note" | "inferred_from_context" | "no_description"}
ReasonCode := "none" | "no_amount_stated" | "amount_unclear" | "charge_unclear" | "conflicting_amounts" | "instruction_in_note"
```

Two layers enforce it: the provider receives the grammar as a JSON Schema, and one parser checks every answer whichever model wrote it. A rejected answer is retried once with its violation codes and then goes to Review. It is never repaired.

| Violation | Meaning |
|---|---|
| `not_json`, `wrong_shape` | Not one object of exactly this shape |
| `bad_amount` | The amount is not a string of digits, a point and two digits |
| `unknown_category`, `bad_line_type`, `bad_derivation`, `bad_basis`, `bad_reason_code` | Outside a closed list |
| `too_many_items` | More than 12 items |
| `flag_with_items` | `no_charge_stated` is true and items exist |
| `empty_answer` | No items, and neither flag is set |
| `evidence_not_verbatim`, `amount_not_in_evidence`, `product_mismatch` | Fails the same evidence checks that labels pass |

A model writes no prose anywhere. The workbook's `ai_reason` column comes from fixed sentences, so an explanation can never hold an invented amount.

## 11.4 Note and row results

A `NoteResult` has `status` `ok` or `review`. Its `review_reason` is set exactly when the status is `review`, and a note in Review or stating no charge carries no items.

| `review_reason` | Cause |
|---|---|
| `grammar_failed` | Two answers failed the grammar |
| `evidence_failed` | Two answers failed, and the last failed only on evidence rules |
| `model_unsure` | The model answered `unsure`, and its items are dropped |
| `refused` | The model declined, or the scan decision left the note out of the send |
| `provider_unavailable` | The call failed. Not cached, so a repeat run tries again |
| `budget_exhausted` | The run's money or time limit was reached before this note started |

A `RowResult` gets one outcome, by the first rule that fits. `difference` is `disputed − (items_total − already_paid_total)`, and amounts are never changed.

| Order | Condition | `outcome` | `outcome_reason` |
|---|---|---|---|
| 1 | Blank note | `no_charge_stated` | `empty_note` |
| 2 | Note in Review | `review` | The note's `review_reason` |
| 3 | The note states no charge | `no_charge_stated`, or `review` under the setting | `no_charge_in_note` |
| 4 | The difference is beyond `reconcile.abs_tolerance_usd` | `discrepancy` | `does_not_add_up` |
| 5 | It adds up and the invoice is repeated, under `flag_discrepancy` | `discrepancy` | `repeated_invoice` |
| 6 | Otherwise | `verified` | `adds_up` |

The totals are empty, never 0, for rows that never reached reconciliation.

## 11.5 The workbook

| Sheet | One line per | Columns |
|---|---|---|
| `Items` | Charge on a row | `row_id`, `item`, `category`, `amount`, `evidence`, `outcome`, `ai_reason` |
| `Row Summary` | Row | `row_id`, `shipment`, `carrier_invoice`, `carrier`, `status`, `reason_code`, `disputed`, `items_total`, `already_paid`, `difference`, `outcome`, `outcome_reason`, `repeated`, `note` |
| `Largest` | Shipment, largest dispute first | `rank`, `shipment`, `rows`, `largest_dispute`, `total_on_rows`, `repeated_rows`, `share_of_total`, `cumulative_share`, `outcome`, `main_category` |
| `Run Info` | Setting | `key`, `value` |
| `Categories` | Category | `code`, `name`, `definition` |

Identical inputs give a byte-identical file. So `Run Info` holds only what a rerun repeats, and never a clock, a cost or a count of cached answers.

## 11.6 The run manifest

A run's folder is named by a hash of everything its numbers depend on: `dataset_sha256`, `set_name`, `limit`, `taxonomy_sha256`, `prompt_sha256`, `fewshot_sha256`, `grammar_version`, `model` (the full registry entry, which names a key's variable and never holds the key), `config_sha256`, `code_sha` and `split_sha256`. `run_id` is `run_` plus the first 16 hex characters of the SHA-256 of its canonical JSON. A folder whose manifest no longer matches its id is refused.

`code_commit` and `code_dirty` are recorded too, but are not in the id, because a commit that touches nothing else changes no answer. `config_sha256` covers the settings that decide results and the notes the scan decision keeps back. It leaves out `budget` and `runtime`, so lowering either keeps a run's identity.

## 11.7 KPI snapshot

`itemizer evaluate` writes aggregates only, with no note text, items or row ids. Coverage comes from the run on all rows, and accuracy from TEST on covered notes, weighted back to the real mix. Each condition has `value`, `target`, `met`, `ci_low`, `ci_high`, `n` and `interval_contains_target`. A level passes when every measured value reaches its target and invariant violations are 0, and results say whether the labels are `provisional` or `sealed`. A level whose work is not built reports `work_not_built`, whatever its numbers. Beside coverage, the snapshot reports rows and dollars `accepted_without_reading`, and accuracy on labels a person has checked. Metric definitions are in [doc 4](04-kpi-calculator.md).

A score belongs to its run. `evaluate` refuses, with nothing charged, a run whose category list, worked examples, prompt, grammar or result-deciding settings changed after it ran, a run with notes that got no answer, and rows that do not follow from its note results. Each milestone in `kpi.milestones` has a TEST budget. A charge follows what was scored: the answers, the prompt, the category list and the result-deciding settings. Scoring the same again is free, whatever the run id, and different answers under one run id count as a new run. `--extra-peek <reason>` spends past the budget on purpose, is logged, and is flagged on the status page.

## 11.8 How to test another model

**A model on a known API takes one entry and no code.**

1. Add an entry to `config/models.yaml`:

   ```yaml
   my-new-model:
     provider: anthropic           # anthropic | ollama | openai_compatible
     model: the-provider-model-id
     api_key_env: CLAUDE_API_KEY   # the name of the variable, never the key
     effort: medium
     refusal_fallback: false
     input_usd_per_mtok: "2.00"
     output_usd_per_mtok: "10.00"
     cache_read_usd_per_mtok: "0.20"
     cache_write_usd_per_mtok: "2.50"
   ```

2. Check it is listed and its key is found: `itemizer models`.
3. Compare it with the current model on the same notes:

   ```bash
   itemizer compare-models --models claude-opus-5-5,my-new-model --set train --limit 30
   ```

   This prints a table and writes `data/compare/`: valid-first-try rate, retries, Review, Verified and Discrepancy shares, agreement with the first model, cost, latency, and projected cost and minutes for all notes. A repeat comparison uses the cache, so it makes no new calls, and its costs are those from when each answer was first made.
4. Agreement is not accuracy. Choose a model on labelled VALIDATION notes. TEST never chooses between candidates, and the command refuses it.
5. Use it: `itemizer run --model my-new-model`, or make it the `default` in the registry.

**A new API family takes one adapter and one line.** Add a class to `src/itemizer/providers.py` with `complete(system, user, schema) -> Completion` and a static `wire_sample()`, then add it to `ADAPTERS`. The shared contract test runs against it with no new test code. The grammar goes through the same parser, so a model with weak schema support shows up as a low valid-first-try rate and not as bad data.

The Ollama and OpenAI-compatible adapters have only been tested against recorded reply shapes, so try a few notes first.
