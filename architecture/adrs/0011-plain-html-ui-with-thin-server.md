# 11. Plain HTML UI served by a thin Python server

Date: 2026-11-02

## Status

Accepted. Amends [7. Web UI for upload, results, error review and review](0007-web-ui-for-upload-review-results.md): replaces Streamlit and OIDC login. The pages and rules in ADR 0007 stay.

## Context

The team wants plain HTML instead of Streamlit because it is easier to manage. Uploading an export, starting a run and submitting a review must all work in the browser. A static HTML file cannot store an upload, start a job or save a decision, so the pages need a server.

ADR 0007 also relied on OIDC login and an IP allowlist. Both depended on unanswered questions about PPG's identity provider and network. The dataset decision in ADR 0013 removes the need for them.

## Decision

- **Server-rendered HTML.** FastAPI with Jinja2 templates and plain HTML forms. A small amount of plain JavaScript adds item rows on the review page and polls run status. No Node build step and no React.
- **One process.** `itemizer ui` starts the server. Caddy in front of it provides TLS.
- **Login.** Usernames with hashed passwords, stored on the server and never in Git. A signed session cookie, a CSRF token on every POST, and roles from `ui.role_map` checked on the server for every action.
- **No business logic in the UI.** Every action calls a service function that the CLI also uses, as in ADR 0007.
- **One set of KPI templates.** The KPI View and the static KPI Dashboard render the same Jinja2 and Vega-Lite panels.

Blind labelling, blind audit rows, aggregate-only TEST results, the single review intake and the Excel fallback all stay as ADR 0007 describes them.

Alternatives considered:

- Streamlit (ADR 0007): less code, with built-in login and table editing. Not chosen because the team wants plain HTML.
- Static HTML only: the simplest to deploy, but it cannot upload, start a run or save a review in the browser.
- FastAPI + React: adds a build step and about twice the code (ADR 0007).

## Consequences

- Deployment is one Python process behind a proxy. That is about the same effort as Streamlit, not less. The gain is plain pages the team controls and can test with ordinary HTTP requests.
- There is more UI code than with Streamlit, because login, sessions, CSRF protection, forms and item editing are now the team's own. ADR 0007's estimate of 800–1,200 lines assumed Streamlit, so expect more. The new size has not been measured.
- Password storage, session handling and upload handling become the team's responsibility. `add-web-ui` covers them with tasks and tests.
- PPG users sign in with an account the team issues, so login no longer depends on PPG IT. The server is reachable over HTTPS from any network.
