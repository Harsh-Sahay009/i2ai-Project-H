# 3. Configurable layer — parameter catalog

> Atlas M5: *"Work with the same structure everywhere and different settings in different places: thresholds, prompts and context, domain vocabulary, workflow policy and escalation rules… Each setting still needs limits, an owner and a log, or it turns into configuration debt."*
> Test: *does the structure repeat while the parameters differ?*

## 3.1 Rules for every parameter

1. Declared in the **Parameter Schema** (`config/schema/parameters.schema.json`) with: `key`, `type`, `default`, `min`/`max` or `enum`, `owner_role`, `family`, `validity_horizon_days`, `affects_metrics`. The Web UI shows parameters read-only; changes go through Git and the promotion gate, never through a UI form.
2. Resolved in layers, later wins: **core defaults → environment (`dev`, `prod`) → carrier override → run CLI flag** (CLI flags allowed only for parameters marked `cli_overridable`).
3. A value outside its limits fails the run before stage 1. No silent clamping.
4. The **effective config** is frozen, canonicalized (sorted JSON) and hashed (`config_hash`) into the run manifest.
5. Every change is a Git commit through the **Config Change Log**: who, what, why, evidence link (KPI snapshot id), previous value. Parameters marked `gate: promotion` change only through the promotion gate.
6. Each published value carries a **validity horizon**; the Recertification Scheduler flags expired values.

Owner roles: **Operator** (team, runs the tool), **Eval lead** (team, owns metrics), **Review lead** (PPG accountant), **Client owner** (PPG).

## 3.2 Catalog

### A. Thresholds and tolerances (family `thresholds`, gate: promotion)

| Key | Type | Default | Limits | Owner | Horizon | Affects |
|---|---|---|---|---|---|---|
| `reconcile.abs_tolerance_usd` | decimal | 0.01 | 0.00 – 1.00 | Client owner | 90 d | Verified vs Discrepancy |
| `reconcile.rel_tolerance` | decimal | 0.000 | 0.000 – 0.005 | Client owner | 90 d | Verified vs Discrepancy |
| `confidence.review_threshold_row` | float | calibrated (≈0.80) | 0.50 – 0.99 | Eval lead | 30 d | f, coverage, accuracy |
| `confidence.review_threshold_item` | float | calibrated (≈0.70) | 0.50 – 0.99 | Eval lead | 30 d | f, coverage |
| `confidence.per_category_override` | map<cat,float> | {} | each 0.50 – 0.99 | Eval lead | 30 d | a |
| `confidence.calibration_map_version` | ref | latest published | must exist in registry | Eval lead | 30 d | AUC, f |
| `strata.large_dispute_usd` | decimal | 180.00 (top decile of the dataset's positive deltas) | 100 – 50,000 | Eval lead | per dataset | weighting, Level 1 |
| `evidence.match_mode` | enum | `exact_ws_normalized` | `exact`, `exact_ws_normalized` | Client owner | — | verification text |

`evidence.match_mode` cannot be relaxed beyond whitespace normalization: anything looser would break the "exact words" invariant.

### B. Prompts and context (family `prompting`, gate: promotion)

| Key | Type | Default | Limits | Owner |
|---|---|---|---|---|
| `prompt.template_version` | ref | `itemize@v1` | exists in registry | Operator |
| `prompt.fewshot_set_version` | ref | `fewshot@v1` | exists; drawn from TRAIN only | Operator |
| `prompt.fewshot_k` | int | 6 | 0 – 20 | Operator |
| `prompt.include_extractor_hints` | bool | true | — | Operator |
| `prompt.include_category_definitions` | bool | true | — | Operator |
| `prompt.max_note_chars` | int | 4000 | 500 – 16000 | Operator |

### C. Domain vocabulary (family `vocabulary`, gate: promotion)

| Key | Type | Default | Limits | Owner |
|---|---|---|---|---|
| `taxonomy.version` | ref | `taxonomy@D1-approved` | must have client approval record | Client owner |
| `taxonomy.catch_all_category` | string | `other_unmapped` | must exist in taxonomy | Client owner |
| `lexicon.version` | ref | `lexicon@v1` | exists in registry | Operator |
| `lexicon.carrier_overrides` | map<carrier,ref> | {} | each exists | Operator |
| `currency.default` | enum | `USD` | `USD`, `CAD` | Operator |
| `codes.standard_list` | enum | `none` | `none`, `x12`, `carrier_xpo` | Client owner (Level 3) |

### D. Routing and model policy (family `routing`)

| Key | Type | Default | Limits | Owner | Gate |
|---|---|---|---|---|---|
| `routing.external_ai_approved` | bool | **false** | true only with `approval_ref`; not needed for `open_anonymized` data | Client owner | written approval |
| `routing.approval_ref` | string | null | required when above is true | Client owner | written approval |
| `routing.route` | enum | `local` in core; `external` in `dev` and `prod` (ADR 0013) | `rules_only`, `local`, `external`, `external_then_local` | Operator | promotion |
| `routing.fallback_order` | list | `[local, rules_only]` | subset of providers | Operator | promotion |
| `model.local.id` | string | pinned tag + digest | digest required | Operator | promotion |
| `model.external.id` | string | pinned dated snapshot id | aliases like `latest` rejected | Operator | promotion |
| `model.temperature` | float | 0.0 | 0.0 – 0.3 | Operator | promotion |
| `model.max_output_tokens` | int | 1500 | 256 – 4096 | Operator | — |
| `model.seed` | int | 20261031 | — | Operator | — |
| `routing.timeout_s` | int | 60 | 5 – 300 | Operator | — |
| `routing.max_retries` | int | 2 | 0 – 5 | Operator | — |
| `routing.cache_enabled` | bool | true | — | Operator | — |
| `budget.max_usd_per_run` | decimal | 10.00 | 0 – 100 | Client owner | — |
| `budget.max_minutes_per_run` | int | 30 | 1 – 120 | Operator | — |

### E. Workflow policy and escalation (family `workflow`)

| Key | Type | Default | Limits | Owner |
|---|---|---|---|---|
| `review.weekly_capacity_rows` | int | 60 | 0 – 1500 | Review lead |
| `review.audit_sample_rate_verified` | float | 0.10 | **0.05** – 1.00 | Review lead (promotion gate to lower) |
| `review.priority` | enum | `disputed_usd_desc` | `disputed_usd_desc`, `confidence_asc` | Review lead |
| `review.blind_audit` | bool | true | — | Review lead |
| `review.require_reason_code_on_edit` | bool | true | — | Review lead |
| `review.no_charge_stated_policy` | enum | `verified` | `verified`, `review` | Client owner |
| `review.repeated_invoice_policy` | enum | `flag_discrepancy` | `flag_discrepancy`, `review` | Client owner |
| `adjudication.min_cases_for_change` | int | 3 | 1 – 50 | Eval lead |

### F. Evaluation and KPI (family `evaluation`, owner Eval lead)

| Key | Type | Default | Limits |
|---|---|---|---|
| `kpi.metric_definitions_version` | ref | `metrics@v1` | exists |
| `kpi.weights_version` | ref | derived per production snapshot | exists |
| `kpi.price_table_version` | ref | `prices@2026-10` | exists, effective date ≤ run date |
| `kpi.local_cost_usd_per_gpu_hour` | decimal | 0.00 | 0 – 10 |
| `kpi.ci_method_proportion` | enum | `wilson` | `wilson`, `clopper_pearson` |
| `kpi.bootstrap_resamples` | int | 2000 | 500 – 20000 |
| `kpi.amount_match_tolerance_usd` | decimal | 0.01 | 0.00 – 0.05 |
| `kpi.reproducibility_reruns` | int | 2 | 1 – 5 |
| `kpi.test_peek_budget_per_milestone` | int | 1 | 1 – 3 |
| `gates.level1` | object | `{cov_usd:0.80, cov_rows:0.25, acc:0.95}` | client-approved |
| `gates.level2` | object | `{cov_usd:0.90, cov_rows:0.85, acc:0.95}` | client-approved |
| `gates.level3` | object | `{cov_usd:0.95, cov_rows:0.95, acc:0.95}` | client-approved |

### G. User interface (family `ui`)

| Key | Type | Default | Limits | Owner | Gate |
|---|---|---|---|---|---|
| `ui.auth_provider` | enum | `local_accounts` | `local_accounts` only in `prod`; `local_dev` allowed in `dev` | Operator | locked in prod |
| `ui.role_map` | map<username,role> | {} | roles ∈ operator, accountant, labeler, adjudicator, client_owner | Client owner (PPG users), Operator (team) | — |
| `ui.max_upload_mb` | int | 20 | 1 – 50 | Operator | — |
| `ui.allowed_upload_types` | list | `[.xlsx]` | subset of `.xlsx`, `.xls` | Operator | — |
| `ui.session_timeout_min` | int | 30 | 5 – 240 | Operator | — |
| `ui.max_concurrent_runs` | int | 1 | 1 – 2 | Operator | — |
| `ui.page_size_rows` | int | 50 | 10 – 500 | Operator | — |
| `ui.show_confidence_as` | enum | `band` | `band`, `band_and_value` | Review lead | — |
| `ui.test_error_examples_released` | bool | false | true only after the final freeze | Eval lead | written approval |
| `ui.allow_workbook_fallback` | bool | true | — | Review lead | — |

Not configurable: blind labelling pages never receive predictions, and audit-sample rows always hide outcome and confidence.

### H. Agent and guardrails (families `agent`, `guardrails`)

| Key | Type | Default | Limits | Owner | Gate |
|---|---|---|---|---|---|
| `agent.max_steps` | int | 8 | 3 – 20 | Operator | promotion |
| `agent.max_calls_per_tool` | int | 3 | 1 – 10 | Operator | promotion |
| `agent.max_resubmits` | int | 1 | 0 – 2 | Operator | promotion |
| `agent.tool_allowlist` | list | the 8 pipeline tools | subset of registered tools; must include both terminal tools | Operator | promotion |
| `agent.system_prompt_version` | ref | `agent-system@v1` | exists in registry | Operator | promotion |
| `guardrails.profile` | enum | `full` | `full` in dev/prod (**locked**); `none`, `no_input`, `no_toolcall`, `no_output`, `no_action`, `no_privacy` only in `experiment` | Eval lead | locked |
| `guardrails.injection_detector_threshold` | float | 0.5 | 0.1 – 0.9 | Eval lead | promotion |
| `mcp.enabled_tools` | list | 5 analyst tools | read-only tools only | Operator | — |
| `mcp.max_rows_per_response` | int | 50 | 1 – 200 | Operator | — |

### I. Synthetic data (family `synth`, owner Eval lead)

| Key | Type | Default | Limits |
|---|---|---|---|
| `synth.seed` | int | 20261031 | — |
| `synth.n_notes` | int | 1000 | 50 – 20000 |
| `synth.adversarial_share` | float | 0.0 for SYNTH, 1.0 for ADV | 0 – 1 |
| `synth.paraphrase_with_local_llm` | bool | false | — |
| `synth.max_jsd` | float | 0.10 | 0.01 – 0.30 |
| `synth.max_shared_ngram` | int | 8 | 5 – 12 |
| `synth.min_spotcheck_agreement` | float | 0.95 | 0.80 – 1.00 |
| `synth.min_utility_spearman` | float | 0.6 | 0.0 – 1.0 |

### J. Runtime (family `runtime`, owner Operator, no gate)

| Key | Type | Default | Limits |
|---|---|---|---|
| `runtime.concurrency` | int | 4 | 1 – 32 |
| `runtime.batch_size_notes` | int | 25 | 1 – 200 |
| `runtime.checkpoint_every_notes` | int | 100 | 10 – 1000 |
| `runtime.data_root` | path | `./data` | must be ignored by Git |
| `runtime.log_level` | enum | `INFO` | — |

### K. Dataset and split (families `data`, `split`; ADR 0012, ADR 0013)

| Key | Type | Default | Limits | Owner | Gate |
|---|---|---|---|---|---|
| `data.dataset_class` | enum | `client_confidential` in core; `open_anonymized` in `dev` and `prod` | `open_anonymized`, `client_confidential` | Client owner | written approval |
| `data.source_ref` | string | null | required when class is `open_anonymized` | Client owner | written approval |
| `split.seed` | int | 20261102 | — | Eval lead | locked after TEST is sealed |
| `split.validation_share` | float | 0.40 | 0.20 – 0.60 of non-TEST notes | Eval lead | locked after first use |
| `split.min_validation_notes` | int | 100 | 50 – 500 | Eval lead | — |
| `split.test_large_notes` | int | 50 | 25 – 100; the rest of the non-single half is multi-charge | Eval lead | locked after TEST is sealed |
| `split.test_reserve_notes` | int | 20 | 0 – 100; unused notes are released after sealing | Eval lead | locked after TEST is sealed |
| `split.max_stratum_gap_notes` | int | 10 | 0 – 30; largest gap from a 100/100 TEST mix | Eval lead | — |

## 3.3 What is *not* configurable

Parameters that would weaken an invariant are not exposed: no flag disables the evidence verifier, the amount-edit prohibition, the confidentiality gate's fail-closed behaviour, the TEST-label access restriction, or the UI's blind labelling and blind audit rules. The only exception is `guardrails.profile`, which can be lowered **only** in the `experiment` environment, which accepts SYNTH and ADV data only and cannot publish changes or outputs (ADR 0010).

## 3.4 Example effective config (illustrative)

```yaml
# config/env/prod.yaml — layered over config/core/defaults.yaml
taxonomy: { version: taxonomy@D1-approved }
data:
  dataset_class: open_anonymized
  source_ref: "where the anonymized dataset was released, and Jake's confirmation"
routing:
  route: external
  fallback_order: [local, rules_only]
model:
  external: { id: "pinned-dated-snapshot-id" }
  local: { id: "qwen3:14b@sha256:…" }
  temperature: 0.0
review:
  weekly_capacity_rows: 60
  audit_sample_rate_verified: 0.10
carriers:
  CARRIER_07:
    lexicon: lexicon-carrier07@v2
```
