## Context

C4 container **Web UI** (12 components: Auth & Role Guard, Upload & Pre-check Page, Run Launcher & Monitor, Results Explorer, Error Review Workbench, Review Queue Page, Adjudication Page, Blind Labelling Page, Agent Trace Viewer, Tool Reference Page, KPI View, UI Audit Logger). ADR 0007, ADR 0011.

Placement: role model, page permissions and the decision intake contract are **common core**; upload limits, page size, session timeout and confidence display are **configurable layer** (`ui.*`). Position: **owned**. The review experience is part of the firm-specific workflow.

Authority: uploading and launching are **supervised** actions (operator or accountant). The UI never edits amounts in predictions and never records payment.

## Goals / Non-Goals

**Goals:** upload-to-results without the CLI; fast review with evidence in context; error analysis that cannot leak TEST or VALIDATION; identical data paths for UI and CLI; plain pages the team can read, change and test.

**Non-Goals:** payment decisions; editing configuration in the UI; metric computation in the UI; a JavaScript build step.

## Decisions

- **Plain HTML from a thin server** (ADR 0011). FastAPI with Jinja2 templates and plain HTML forms. A small amount of plain JavaScript adds item rows on the review page and polls run status. Alternatives: Streamlit (less code, not chosen because the team wants plain HTML); static HTML only (cannot upload, start a run or save a review); FastAPI + React (build step, about twice the code). The thin-UI rule stays: every action is a call to a service function that the CLI also uses.
- **Background runs.** The Run Launcher spawns `itemizer run --snapshot <id> --env <env>` as a subprocess, stores the job's run id and reads progress from action telemetry. At most `ui.max_concurrent_runs` runs at a time; a second launch is refused with the running job shown. Runs keep going if the browser closes.
- **Upload path.** The file is checked against the size limit and type, hashed, written to the CAS, then pre-checked with the Input Contract Validator. The pre-check report is shown before the user can launch. Nothing is left in temporary storage after registration.
- **Synthetic demo uploads.** A file that matches a published SYNTH or ADV set is marked synthetic. Its runs carry a banner on every page and are listed apart from real runs.
- **Results Explorer.** Reads predictions and decision telemetry by run id. Evidence is highlighted using the stored offsets into the raw note. Each Review or Discrepancy row shows the outcome rule and values that triggered it. The itemized workbook is downloaded from the CAS, so the bytes match the registered hash.
- **Agent Trace Viewer and Tool Reference.** The viewer reads tool-call and guard telemetry for one row and shows each LLM turn, tool call, guard decision and terminal tool. It follows the same limits as row-level errors. The Tool Reference page lists docstrings and schemas from the Tool Registry.
- **Error Review Workbench.** Reads the error-typed rows the KPI Calculator writes for TRAIN and PROD; it does not run matching itself. VALIDATION shows aggregates only (ADR 0012). TEST shows aggregates only; TEST error examples appear only when `ui.test_error_examples_released` is true, which requires written approval after the final freeze, and every view is logged.
- **KPI View.** Renders KPI snapshots with the Jinja2 and Vega-Lite panels shared with the KPI Dashboard. It never computes metrics.
- **Review, adjudication, labelling.** The pages call the Human Review System: the queue comes from the Queue Builder, and decisions go to the Review Decision Intake with the prediction hash the reviewer saw (stale hash → rejected). Audit rows hide outcome and confidence. Adjudicators cannot adjudicate their own review. Labelling pages get notes only: the service never sends predictions to a labelling session.
- **Security.** Usernames with hashed passwords, stored outside Git; role map in config; roles checked server-side on every action, not only by hiding pages; signed, HTTP-only, HTTPS-only session cookie; session timeout; a CSRF token on every POST; Caddy for TLS; no third-party scripts or analytics.
- **Versions and telemetry.** The UI versions nothing itself; uploads go to the version registry. It records UI audit events (upload, launch, decision, label, adjudication, download, TEST-example view) plus review open/submit timestamps used for accountant minutes per dispute.

## Risks / Trade-offs

- [More code than Streamlit: login, sessions, forms and item editing are the team's own] → start from D3's small page set; add the review pages in D4. The size has not been measured.
- [Security mistakes in hand-written login and forms] → use maintained libraries for password hashing and sessions; tests for CSRF rejection, expired sessions and upload limits.
- [Scope creep threatens D4] → D3 ships only access control, upload, run monitor and results explorer; the review pages come in D4.
- [PPG staff cannot reach the server from their network] → the server uses plain HTTPS with no IP allowlist; the fallback Excel workbook keeps the review loop working.
- [Reviewers trust highlighted evidence too much (automation bias)] → blind audit rows; audit disagreement reported.

## Open Questions

- Written client agreement to the scope change.
- Hosting: CMU VM availability and the rules that apply to it.
- Who issues and rotates accounts for PPG users.
