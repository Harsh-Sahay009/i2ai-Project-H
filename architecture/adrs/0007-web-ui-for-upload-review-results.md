# 7. Web UI for upload, results, error review and review

Date: 2026-10-31

## Status

Accepted. Supersedes [2. CLI and Excel review workbook instead of a graphical UI](0002-cli-and-excel-instead-of-ui.md).

## Context

ADR 0002 followed the scope (§2), which excludes a user interface. The team has since decided it needs one to:

- upload the weekly export without command-line access,
- explore results with each item's evidence highlighted in the note,
- review errors by type (a–g) during development,
- review, adjudicate and blind-label rows; Excel round-trips are slow and easy to get wrong.

The scope says changes after approval are agreed in writing, so this needs the client owner's written agreement.

## Decision

Add a **Web UI** container (Python + Streamlit, OIDC login) with pages for upload and pre-check, run launch and monitor, results explorer, error review workbench, review queue, adjudication, blind labelling and KPIs.

- **No business logic in the UI.** It launches the existing `itemizer run` pipeline as a background job and submits decisions through the Human Review System's single intake path. The CLI keeps working for operators and for D4's one-command requirement.
- **Roles enforced server-side** from the configured role map: operator, accountant, labeler/adjudicator, client owner.
- **The locked test set stays locked.** The error workbench shows row-level errors only for DEV and PROD; TEST shows aggregates until the final freeze releases error examples for D5.
- **Blind protocols kept.** Labelling pages never receive predictions, and audit-sample review rows hide the outcome and confidence.
- **Confidentiality.** Hosted only on a team-controlled server behind TLS and an IP allowlist; no third-party analytics; uploads go straight into the encrypted CAS.
- The Excel review workbook stays as an **offline fallback**, and the static HTML dashboard stays for D5 and offline reading. Both share definitions with the UI.

Alternatives considered:

- FastAPI + React: more control, but roughly twice the code for a four-person team on a December deadline.
- Excel only (ADR 0002): no upload and poor error review.

## Consequences

- More scope: about 800–1,200 more lines of Python, plus hosting and login setup. The 3 December deadline is unchanged.
- New attack surface: login, uploads, session handling. Covered by role checks, upload limits and an audit log.
- Review timestamps from the UI give a better measure of accountant minutes per dispute than workbook timestamps.
- PPG accountants need network access to the team server; to be confirmed with PPG IT.
