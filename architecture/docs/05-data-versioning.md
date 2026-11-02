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

All CAS objects are immutable. "Delete" is a retention action logged in the registry, never an overwrite.

## 5.2 Artifact register

| Artifact | Versioned | Mechanism | Immutable | Notes |
|---|---|---|---|---|
| Raw TMS export (.xlsx), uploaded via Web UI or CLI | Yes | CAS, with uploader role, pseudonymous id and pre-check report | Yes | Confidential; encrypted volume only; the upload is written straight to the CAS, not left in temp storage |
| Normalized snapshot (Parquet) | Yes | CAS + transform code SHA | Yes | Raw note bytes preserved for evidence checks |
| Masking map (placeholder ↔ name) | Yes | CAS, separate folder | Yes | Never leaves team storage; never in outputs |
| Charge taxonomy (D1) | Yes | Git tag + client approval record | Yes per tag | Definitions + examples; version required on every prediction |
| Locked test set (D2) | Yes | CAS, **sealed** (hash recorded in a signed manifest) | Yes | Includes both labellers' raw labels, agreement stats and resolution |
| DEV set, FRESH set | Yes | CAS | Yes per version | Fingerprints disjoint from TEST |
| Prompt templates | Yes | Git tag | Yes per tag | |
| Few-shot example sets | Yes | Git tag + fingerprint list | Yes per tag | Checked disjoint from TEST at publish |
| Domain lexicon (abbreviations, misspellings, carrier aliases) | Yes | Git tag | Yes per tag | Carrier overrides are separate tags |
| Calibration map | Yes | CAS + fit metadata (DEV version) | Yes | |
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
| Published changes | Yes | Record: owner, evidence, version, rollback pointer, validity horizon | Yes | |
| Response cache | Keyed, not versioned | SQLite keyed by hash(prompt, model, params) | — | A cache hit is valid only for identical key; flushed on model change |
| Dashboard HTML | Derived | Regenerated from snapshots | — | Stamped with snapshot ids |
| Web UI session state | No | In memory | — | Not evidence; anything that matters is written as a record above |
| Debug logs | No | Rotated | — | Not evidence |

## 5.3 Run manifest

```yaml
run_id: sha256:…            # hash of everything below
created_at: 2026-11-03T14:02:11Z
environment: prod
input_snapshot: sha256:…    # raw + normalized
taxonomy: taxonomy@D1-approved
prompt_template: itemize@v3
fewshot_set: fewshot@v2
lexicon: lexicon@v4
lexicon_carrier_overrides: { CARRIER_07: lexicon-carrier07@v2 }
calibration_map: sha256:…
config_hash: sha256:…
route: local
models:
  local: { id: "…", digest: "sha256:…", temperature: 0.0, seed: 20261031 }
code: { git_sha: "…", lockfile: "sha256:…", dirty: false }
metric_definitions: metrics@v1
price_table: prices@2026-10
```

## 5.4 Rerun guarantee

`itemizer rerun <run_id>` restores every referenced artifact and re-executes:

* with cache on → byte-identical predictions (asserted).
* with cache off → agreement measured as error (e); differences are reported row by row.

## 5.5 Retention and confidentiality

PPG data stays on team-controlled accounts. CAS lives on an encrypted volume; Git holds no PPG note text (prompts and few-shot sets reference examples by fingerprint, with text resolved from the CAS at runtime). At project end the team follows the client's retention instruction and logs the deletion.
