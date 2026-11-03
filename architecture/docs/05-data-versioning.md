# 5. What is versioned, and how

Atlas M5: an episode becomes experience only when it is **adjudicated, outcome-linked and versioned** — tied to the exact model, prompts, routing rules, thresholds and operating domain that produced it. Error (e) Reproducibility and deliverable D5 ("a reader outside the team can rerun the tool from the report alone") make versioning a hard requirement.

## 5.1 Mechanisms

| Mechanism | Used for |
|---|---|
| **Content-addressed store (CAS)** — `sha256` of canonical bytes; path `cas/<aa>/<hash>` | Data files: snapshots, predictions, outputs, labels, KPI snapshots |
| **Git + semantic tag** — `name@vN` | Human-edited text: config, prompts, lexicon, taxonomy, metric definitions, price table |
| **Pinned digest** | Models: local model digest; external dated snapshot id, never an alias |
| **Lockfile** | Python dependencies (`uv.lock` hash) |
| **Lineage index** (DuckDB `artifacts`, `lineage`) | Parent → child links, so any KPI traces to its inputs |

All CAS objects are immutable. Nothing is ever overwritten.

## 5.2 Artifact register

| Artifact | Versioned | Mechanism | Immutable | Notes |
|---|---|---|---|---|
| Raw TMS export (.xlsx), uploaded via Web UI or CLI | Yes | CAS, with uploader role, pseudonymous id and pre-check report | Yes | Kept out of Git; the upload is written straight to the CAS, not left in temp storage |
| Normalized snapshot (Parquet) | Yes | CAS + transform code SHA | Yes | Raw note bytes preserved for evidence checks; records `data.dataset_class` |
| Dataset profile and anonymization scan | Yes | CAS | Yes | Row, note and carrier counts; names, phones and emails found |
| Split manifest | Yes | CAS, with `split.seed` and the assignment of every note | Yes | Assigns each distinct note to TRAIN, VALIDATION or TEST, and records whether each TEST note's format appears in TRAIN (ADR 0012) |
| Charge taxonomy (D1) | Yes | Git tag + client approval record | Yes per tag | Definitions + example fingerprints and offsets; quotes are resolved from the dataset when rendered; version required on every prediction |
| Taxonomy draft and approval document | Yes | CAS, with model id and prompt hash | Yes | The document holds real quotes, so it stays out of Git |
| Locked test set (D2) | Yes | CAS, **sealed** (hash recorded in a signed manifest) | Yes | Includes both labellers' raw labels, agreement stats, client review and resolution |
| TRAIN set, VALIDATION set, FRESH set | Yes | CAS | Yes per version | Disjoint from each other and from TEST, by note fingerprint |
| Prompt templates | Yes | Git tag | Yes per tag | |
| Few-shot example sets | Yes | Git tag + fingerprint list | Yes per tag | Drawn from TRAIN only; checked at publish |
| Domain lexicon (abbreviations, misspellings, carrier aliases) | Yes | Git tag | Yes per tag | Carrier overrides are separate tags |
| Calibration map | Yes | CAS + fit metadata (VALIDATION version) | Yes | |
| Effective config | Yes | canonical JSON hash in manifest | Yes | Layer files in Git |
| Model identity | Yes | provider + id + digest/snapshot + decoding params | — | Silent upstream change detection compares response fingerprints on a canary set |
| Code | Yes | Git SHA + lockfile hash | — | Dirty working tree blocks `prod` runs |
| **Run manifest** | Yes | CAS; `run_id = hash(manifest)` | Yes | The version tag of the atlas closed loop |
| Predictions (items, outcomes, confidences) | Yes | CAS keyed by run_id | Yes | |
| Output workbook | Yes | CAS hash; run info sheet carries run_id | Yes | |
| Review decisions from the Web UI | Yes | Append-only outcome records with the prediction hash the reviewer saw | Yes | A decision on a stale prediction is rejected |
| Review workbooks (offline fallback, exported and returned) | Yes | CAS | Yes | Returned workbook is evidence for approvals |
| UI audit events (upload, launch, decide, label, download) | Yes | Append-only table in the episode store | Yes | Role + pseudonymous id; no note text |
| Adjudications and closed cases | Yes | Append-only table with run_id | Yes | |
| Replay packs | Yes | CAS: note, manifest, prediction, gold/decision | Yes | |
| Metric definitions | Yes | Git tag | Yes per tag | |
| Stratum weights | Yes | CAS keyed by reference snapshot | Yes | |
| Price table | Yes | Git tag with effective date | Yes per tag | Prices change; costs must be recomputable |
| KPI snapshots | Yes | Append-only + CAS export | Yes | |
| Acceptance results (D3, D4) | Yes | CAS, with run id and client review evidence | Yes | |
| Methodology report (D5) | Yes | CAS, with the KPI snapshot ids it cites | Yes | |
| Published changes | Yes | Record: owner, evidence, version, rollback pointer, validity horizon | Yes | |
| Response cache | Keyed, not versioned | SQLite keyed by hash(prompt, model, params) | — | A cache hit is valid only for identical key; flushed on model change |
| Dashboard HTML | Derived | Regenerated from snapshots | — | Stamped with snapshot ids |
| Web UI session | No | Signed cookie | — | Not evidence; anything that matters is written as a record above |
| Debug logs | No | Rotated | — | Not evidence |

## 5.3 Run manifest

```yaml
run_id: sha256:…            # hash of everything below
created_at: 2026-11-03T14:02:11Z
environment: prod
input_snapshot: sha256:…    # raw + normalized
dataset_class: open_anonymized
split_manifest: sha256:…
taxonomy: taxonomy@D1-approved
prompt_template: itemize@v3
fewshot_set: fewshot@v2
lexicon: lexicon@v4
lexicon_carrier_overrides: { CARRIER_07: lexicon-carrier07@v2 }
calibration_map: sha256:…
config_hash: sha256:…
route: external
models:
  external: { id: "pinned-dated-snapshot-id", temperature: 0.0, seed: 20261031 }
code: { git_sha: "…", lockfile: "sha256:…", dirty: false }
metric_definitions: metrics@v1
price_table: prices@2026-10
```

## 5.4 Rerun guarantee

`itemizer rerun <run_id>` restores every referenced artifact and re-executes:

* with cache on → byte-identical predictions (asserted).
* with cache off → agreement measured as error (e); differences are reported row by row.

## 5.5 Where the data lives

The dataset is public (ADR 0013), and the repo still does not hold it. Git holds no note text: prompts, few-shot sets and taxonomy examples reference notes by fingerprint and offsets, with text resolved from the CAS at runtime.
