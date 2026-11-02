## Context

C4 container **Web UI** (10 components: Auth & Role Guard, Upload & Pre-check Page, Run Launcher & Monitor, Results Explorer, Error Review Workbench, Review Queue Page, Adjudication Page, Blind Labelling Page, KPI View, UI Audit Logger). ADR 0007.

Placement: role model, page permissions and the decision intake contract are **common core**; upload limits, page size, session timeout and confidence display are **configurable layer** (`ui.*`). Position: **owned**. The review experience is part of the firm-specific workflow.

Authority: uploading and launching are **supervised** actions (operator or accountant). The UI never edits amounts in predictions and never records payment.

## Goals / Non-Goals

**Goals:** upload-to-results without the CLI; fast review with evidence in context; error analysis that cannot leak TEST; identical data paths for UI and CLI.

**Non-Goals:** payment decisions; editing configuration in the UI; metric computation in the UI; public hosting.

## Decisions

- **Streamlit** (Python, same team skills, `data_editor` for item correction, `st.login` for OIDC). Alternative: FastAPI + React. Rejected for the timeline (about twice the code). The thin-UI rule keeps that migration open: every action is a call to a service function that the CLI also uses.
- **Background runs.** The Run Launcher spawns `itemizer run --snapshot <id> --env <env>` as a subprocess, stores the job's run id and reads progress from action telemetry. At most `ui.max_concurrent_runs` runs at a time; a second launch is refused with the running job shown. Runs keep going if the browser closes.
- **Upload path.** The file is checked against the size limit and type, hashed, written to the CAS, then pre-checked with the Input Contract Validator. The pre-check report is shown before the user can launch. Nothing is held in Streamlit temp storage after registration.
- **Results Explorer.** Reads predictions and decision telemetry by run id. Evidence is highlighted using the stored offsets into the raw note. Each Review or Discrepancy row shows the outcome rule and values that triggered it. The itemized workbook is downloaded from the CAS, so the bytes match the registered hash.
- **Error Review Workbench.** Reads the error-typed rows the KPI Calculator writes for DEV and PROD; it does not run matching itself. TEST shows aggregates only. TEST error examples appear only when `ui.test_error_examples_released` is true, which requires written approval after the final freeze, and every view is logged.
- **Review, adjudication, labelling.** The pages call the Human Review System: the queue comes from the Queue Builder, and decisions go to the Review Decision Intake with the prediction hash the reviewer saw (stale hash → rejected). Audit rows hide outcome and confidence. Adjudicators cannot adjudicate their own review. Labelling pages get notes only: the service never sends predictions to a labelling session.
- **Security.** OIDC with an email-domain allowlist; role map in config; roles checked server-side on every action, not only by hiding pages; session timeout; Caddy TLS and an IP allowlist; no third-party telemetry (Streamlit usage stats off); CSRF and XSRF protection on.
- **Telemetry.** UI audit events (upload, launch, decision, label, adjudication, download, TEST-example view) plus review open/submit timestamps used for accountant minutes per dispute.

## Risks / Trade-offs

- [Streamlit reruns the script on every interaction, which is slow on large tables] → paginate with `ui.page_size_rows` and cache read-only queries by run id.
- [PPG network policy blocks access to the CMU server] → confirm with PPG IT; the fallback Excel workbook keeps the review loop working.
- [Scope creep threatens D4] → D3 ships only access control, upload, run monitor and results explorer; the review pages come in D4.
- [Reviewers trust highlighted evidence too much (automation bias)] → blind audit rows; audit disagreement reported.

## Open Questions

- Written client agreement to the scope change.
- PPG identity provider: can PPG accountants sign in through OIDC, or do they need guest accounts?
- Hosting: CMU VM availability and the data-handling rules that apply to it.
