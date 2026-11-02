# 1. Overview

## Purpose

PPG pays carriers against an estimated freight charge. When a carrier bills more, a free-text note explains the difference, and accountants read every note by hand. In 86% of the 1,347 sample rows the reason code is the catch-all "other accessorials", so the detail lives only in the note.

The **Freight Invoice Itemizer** reads the weekly Oracle TMS Excel export and returns an itemized table: one dispute row becomes one or more **charge items**, each with a category, an amount and the exact words it came from. Every row ends in one outcome:

| Outcome | Meaning |
|---|---|
| **Verified** | Items add up to the disputed amount (within tolerance). Includes rows marked "no charge stated". |
| **Discrepancy** | Items are clear but do not add up. Flagged for the accountant. |
| **Review** | The tool is not confident. A person handles the row. |

Non-negotiable product characteristics (scope §3), enforced as **invariants** in the common core:

1. Every item shows the exact words it came from (verbatim evidence span).
2. The tool never invents or edits an amount to make a row add up.
3. A row that does not add up is flagged, never silently passed.

## Scope boundary

The project changes only the **processing** step of the dispute lifecycle. Out of scope: how carriers write notes, any connection to Oracle TMS or accounting, pre-trip processing, and the payment decision, which stays with PPG accountants.

> **Scope change (ADR 0007).** The approved scope excludes a user interface. The team now includes a **Web UI** for upload, results, error review, review, adjudication and blind labelling. Scope §Approval requires changes to be agreed in writing, so this needs the client owner's written agreement.

## From the slides to C4

| Slide 2 block | C4 container | Notes |
|---|---|---|
| UI | Web UI (Streamlit) + Run Console (CLI) | ADR 0007: upload, run, results, error review, review, adjudication, labelling, KPIs. The CLI stays as the pipeline owner and the D4 one-command path. |
| Data Transformation and Check | Data Transformation & Check | Adds note fingerprinting and masking. |
| Router | Model Router | Confidentiality gate, fallback, cache, cost meter. |
| API Provider | External LLM API Provider (external) + Local Model Runtime | Two providers behind one interface = exit path. |
| Classificatier | Itemization Classifier | Evidence verifier and amount reconciler enforce invariants. |
| Output Format | Output Formatter | Items sheet, row summary sheet, run info sheet. |
| Human Reviewer System | Human Review System | Review service behind the Web UI; Excel workbook as offline fallback. |
| KPI Calculator | KPI Calculator | See section 4. |
| Daoardshb (Dashboard) | KPI View (Web UI) + KPI Dashboard | Same panel definitions; static HTML kept for D5 and offline reading. |
| Training Algorithm | Training & Calibration Pipeline | Prompt / lexicon / threshold / calibration changes, not weight training. |
| User | PPG Accountant, Operator, Labeler, Client Owner | Split by role and authority. |
| *(new)* | Agent Tool Library & MCP Server | Custom tools for the itemization agent and analyst tools for Claude Code / the client (section 8). |
| *(new)* | Guardrail Layer | Input, tool-call, output, action and privacy guards (section 8). |
| *(new)* | Synthetic Data Generator | SYNTH and ADV sets with quality checks (section 9). |
| *(new)* | Configuration Registry | The configurable layer (section 3). |
| *(new)* | Version & Artifact Registry | Section 5. |
| *(new)* | Ground Truth Store | Taxonomy (D1), locked test set (D2), DEV and FRESH sets. |
| *(new)* | Telemetry & Episode Store | Three telemetry layers and closed cases. |

The four new containers are the **common core** the atlas says every system needs before experience can compound: a logging schema, an evaluation interface, a version registry and a routing contract.

## Deliverables mapping

| Deliverable | Due | Architecture elements |
|---|---|---|
| D1 Charge category list | 15 Oct | Ground Truth Store (taxonomy v1, approval record) |
| D2 Locked test set | 22 Oct | Human Review System (blind labelling), Ground Truth Store (sealed) |
| D3 Prototype, Level 1 | 5 Nov | Run Console, Data Prep, Router, Classifier, Output Formatter, KPI Calculator; Web UI upload + results pages |
| D4 Final tool, Level 2 | 3 Dec | All containers including the full Web UI; <30 min for 1,500 rows |
| D5 Methodology report | 3 Dec | KPI snapshots + run manifests make every number rerunnable |
