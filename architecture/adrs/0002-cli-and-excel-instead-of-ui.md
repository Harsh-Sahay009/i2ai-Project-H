# 2. CLI and Excel review workbook instead of a graphical UI

Date: 2026-10-31

## Status

Superseded by [7. Web UI for upload, results, error review and review](0007-web-ui-for-upload-review-results.md) on 2026-10-31

## Context

Slide 2 shows a "UI" block. The scope (§2) excludes building a user interface. Accountants already work in Excel; D4 requires "one command".

## Decision

The "UI" becomes the Run Console (Typer CLI) for the operator, and an Excel review workbook for accountants and labellers. The dashboard is a static HTML file.

## Consequences

No web server, no authentication surface, data stays on team storage. Review UX is limited to Excel; workbook validation must be strict.
