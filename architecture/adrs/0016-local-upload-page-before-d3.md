# 16. A local upload page before D3

Date: 2026-11-03

## Status

Accepted. Amends [14. D3 as a thin path](0014-d3-thin-path-controlled-grammar-model-registry.md), which left the Web UI until after D3, and brings part of [11. Plain HTML UI served by a thin Python server](0011-plain-html-ui-with-thin-server.md) forward without its login.

## Context

The team wants to show the prototype at the 5 November meeting: upload the Excel file, get the output Excel with the expenses, and see the KPIs. The signed scope says the project will not build a user interface, and CR-2 told the client the interface comes after D3.

## Decision

A local page, started with `itemizer ui`, on the presenter's machine. It does upload, pre-check, run with progress, download and KPIs. It has no accounts, so it binds to `127.0.0.1` and refuses requests from other sites. It follows ADR 0011: FastAPI, Jinja2 and plain forms, with no business logic. `add-web-ui` absorbs it later and adds login, hosting and review pages.

Alternatives considered:

- A command-line demo: no new code, and inside the signed scope, but no upload as such. It remains the fallback if the page is not ready by the evening of 4 November.
- A hosted page, so Jake can upload from his own browser: the closest to real use, but it needs hosting, sign-in and the API key on a server, and his uploads would go to the API before he has approved external AI.

## Consequences

- CR-2 must change to say a local page comes before D3, and Jake must agree in writing.
- Jake cannot use it from his own machine.
- Only the dataset file gets accuracy, because TEST labels exist only for its notes.
- Adding code changes every run's code hash. The TEST budget therefore follows what was scored, not the run id, so this does not read as a second peek.
