# 2. Control architecture (Atlas M4–M6)

The atlas asks for **one** control architecture with five fields: own or control, standardize, configure, differentiate, and the exit path. The firm boundary is the wall, the common path placements are the rooms, the exit path is the door.

## 2.1 Owned, controlled, accessed

| Position | What sits there | Containers |
|---|---|---|
| **Owned** — firm-specific workflow, evaluation, outcomes | Business logic of itemization, taxonomy, evaluation sets, human review, outcome histories, KPIs, the review experience | Itemization Classifier, Ground Truth Store, Human Review System, Web UI, KPI Calculator, Telemetry & Episode Store, Training & Calibration Pipeline, Dashboard, Data Prep |
| **Controlled** — integration and orchestration | Prompt and context management, routing and fallback, policy, logging, configuration, versioning | Model Router, Prompt Builder, Configuration Registry, Version & Artifact Registry, Run Console |
| **Accessed** — external model and service layer | LLM inference, open-weights model, code lists | External LLM API, Local Model Runtime, Standard Charge Code Lists |

The boundary runs between controlled and accessed. We own none of the models, yet we decide which model handles which note, when to fall back, what counts as an acceptable answer (schema + evidence check) and what gets logged.

## 2.2 Three placements (standardize, configure, differentiate)

The unit is the **element**, one level below the container. Each placement names the criterion that drove it and the evidence that would move it.

### Common core (standardize the contract)

| Element | Criterion | Evidence that would move it |
|---|---|---|
| Input contract (export columns, types) | Repeats weekly, every stage consumes it | A second TMS export format |
| Item schema `{row_id, item_id, category, amount, currency, evidence_text, evidence_start, evidence_end, line_type, derivation, confidence}` | Every downstream consumer (Excel, KPI, review) depends on it | None expected within project |
| Row outcome set `{verified, discrepancy, review, no_charge_stated}` | Defined in scope §3 | Client change in writing |
| Invariants: verbatim evidence, never edit amounts, flag non-reconciling rows | Scope "cannot be compromised" | None |
| Provider interface `complete(prompt, schema, params) -> response, usage` | Two providers today, swap expected | — |
| Run manifest and version tag | Required for reproducibility (error e) and D5 | — |
| Telemetry schema (action / decision / outcome, keyed by `case_id`) | Makes runs comparable | — |
| Evaluation interface and metric definitions | Every candidate must pass the same tests | — |
| Adjudication buckets (AI wrong, human wrong, context changed, genuine exception) | Atlas M3/M5 | — |
| Review decision intake (one validation path for UI and fallback workbook) | Every decision must be comparable regardless of surface | — |
| Role model and page permissions | Blind protocols and TEST isolation depend on it | New role requested by PPG |

### Configurable layer (same structure, different settings)

Thresholds, prompts and context, domain vocabulary, workflow policy and escalation rules. Every parameter has **limits, an owner and a log**, otherwise it becomes configuration debt. Full catalog: section 3.

### Local exception (stays close to the expert)

| Element | Why local | Settles when |
|---|---|---|
| The payment decision | Authority ladder: **prohibited** for the tool | Never moves into the system |
| Large disputes above `large_dispute_usd` with novel wording | Rare, high consequence | Enough adjudicated cases to define a pattern |
| Carrier-specific note conventions not yet in the lexicon | Path still argued over | Pattern recurs across ≥ 3 runs → promoted to lexicon (configurable) |
| Level 3 mapping to ANSI X12 vs carrier lists (XPO) | License not settled | License decision |
| Repeated / duplicate invoices policy | Accountant judgment | Client rule in writing |

**Wrong placement cost.** Too common: forcing a carrier rule into the global prompt silently changes other carriers' results. Too local: a per-analyst spreadsheet of abbreviations nobody can version or reuse.

## 2.3 Design rules

* **Architecture** — separately owned modules: extractor, prompt builder, router/provider, evidence verifier, reconciler, scorer.
* **Interfaces** — each module declares inputs, outputs and what it records per run.
* **Tests** — one shared evaluation (KPI Calculator on sealed sets) that any module change must pass, with the same logging and versioning.

A rules-only itemizer, a local-model itemizer and an API-model itemizer must all accept the same snapshot, return the same item schema and pass the same tests. That is the architectural option.

## 2.4 Exit path

| What must stay portable | How |
|---|---|
| Model provider | Provider Interface + contract tests; local model is the tested fallback |
| Episodes and labels | Parquet/DuckDB in an open schema; exportable |
| Prompts, lexicon, taxonomy | Plain files in Git |
| Re-validation cost | Switching provider = one replay on VALIDATION, then the next Level gate on TEST; measured and recorded as `substitution_time` |

## 2.5 Authority ladder per consequential action (M6)

| Action | Rung | Fallback held |
|---|---|---|
| Upload an export (Web UI) | Supervised: operator or accountant role, input contract pre-check shown before a run | Re-upload; raw file kept in CAS |
| Launch a run from the UI | Supervised: operator or accountant; one run at a time per environment | CLI `itemizer run` |
| Read and snapshot the export | Bounded autonomy (no consequence) | Re-read raw file |
| Propose items for a row | **Recommend** | Review outcome / manual reading |
| Label a row Verified | **Recommend** (accountant may accept without reading) | Random audit sample of Verified rows, blind |
| Flag Discrepancy | Recommend | Accountant reads the note |
| Edit an amount | **Prohibited** | — |
| Decide or record payment | **Prohibited** | Stays in PPG accounting |
| Send text to external API | Supervised: only for the anonymized open dataset with a recorded source, or with written approval (ADR 0013) | Local model route |
| Publish a config change | Supervised: operator approval at the promotion gate | Rollback pointer |

Promotion (e.g., shrinking the audit sample) requires operating evidence from the Level gates on TEST or FRESH, reliance evidence (approval rate with audit disagreement), control evidence (confidentiality gate tests), and recovery evidence (rollback rehearsed).
