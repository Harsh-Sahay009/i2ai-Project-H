## Why

The team wants to show the prototype working at the 5 November meeting: upload the Excel file in a browser, get the output Excel with the expenses, and see the KPIs. It also wants to correct the labels afterwards and see updated results, even if they are worse. Everything but the browser page exists. `add-web-ui` is the full plan, with login, review pages and hosting, and cannot be built in time.

## What Changes

- **Local upload page:** `itemizer ui` starts a page on the presenter's machine: upload, pre-check, run with progress, download the output Excel, see the KPIs and the status page.
- **Local only:** it binds to `127.0.0.1`, with no accounts, and refuses requests from anywhere else, including other web pages open in the same browser.
- **No new logic:** the page calls the same functions as the command line.
- **`--extra-peek` stays on the command line,** so spending past the TEST budget is never one click.
- **Amends the plan:** ADR 0014 left the Web UI out of D3, and CR-2 told the client it comes after D3. ADR 0016 records the change, and the scope page must say so.

## Capabilities

### New Capabilities
- `local-upload-page`: upload, pre-check, run, download and KPI pages, for one person on one machine.

### Modified Capabilities
<!-- none in openspec/specs: changes to level-evaluation, d3-presentation and test-label-review are edited in their own unarchived changes. -->

## Impact

- New `src/itemizer/ui/`, new extra `ui` with `fastapi`, `jinja2`, `python-multipart` and `uvicorn`.
- `itemize_notes` and `pipeline.run` take an optional progress callback, and `pipeline` gains `inspect_export`.
- Later, `add-web-ui` absorbs this page and adds login, hosting and review pages.
