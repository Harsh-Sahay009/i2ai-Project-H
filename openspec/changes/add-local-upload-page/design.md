## Context

Component: Web UI (ADR 0007, ADR 0011), the upload, monitor and results part only. Placement: **configurable layer** for the page's limits, with no business logic, because every action calls a service function the command line also uses. Position: **owned**.

Authority: **recommend**. The page shows what the tool proposes, and never decides payment.

The signed scope says the project will not build a user interface, so CR-2 on the scope page needs Jake's written agreement.

## Goals / Non-Goals

**Goals:** a person at the presenter's machine can upload an Excel file, see what the run will cost before it starts, watch it run, download the output Excel, and see the KPIs. It must work for the AutoPay file with no internet, because those answers are cached.

**Non-Goals:** login, hosting, use from another machine, review pages, the results explorer, the agent trace viewer. `add-web-ui` covers those.

## Decisions

### Server (`src/itemizer/ui/app.py`)

`create_app(root) -> FastAPI`, server-rendered with Jinja2 autoescaping and plain forms, as ADR 0011 specifies.

| Route | What it does |
|---|---|
| `GET /` | The upload form, and recent runs |
| `POST /uploads` | Accepts `.xlsx` up to 25 MB, and stores it as `data/uploads/<sha256>.xlsx`, so a file name never reaches a path. The name goes in `data/uploads/index.json` for display |
| `GET /uploads/<sha256>` | Pre-check from `pipeline.inspect_export`. The start button is disabled on any stop |
| `POST /uploads/<sha256>/run` | Starts the job, and refuses while another is running |
| `GET /jobs/<id>`, `GET /jobs/<id>/status` | The page, and the JSON it polls |
| `GET /runs/<run_id>` | Outcomes, coverage, accepted without reading, download, and scoring for a run on all rows of the dataset file |
| `POST /runs/<run_id>/evaluate` | `pipeline.evaluate_run`, with any refusal shown as a message |
| `GET /runs/<run_id>/download` | The run's `itemized.xlsx`, after checking the run id's pattern |
| `GET /status` | `acceptance.d3_check`, and shows its page |

### Local only

There is no login, so the server binds to `127.0.0.1` with no `--host` option. A middleware refuses a `Host` other than `127.0.0.1` or `localhost`, which stops DNS rebinding, and refuses any `POST` whose `Origin` is not local, so a web page open in the same browser cannot start a paid run.

### Jobs (`src/itemizer/ui/jobs.py`)

One job at a time, on a background thread, with state in memory: `running`, `done` or `failed`, notes done and total, elapsed time and cost so far. A `ContractError` shows its message, and anything else shows its type only, as on the command line. The job keeps running if the browser closes.

### Pre-check (`pipeline.inspect_export`)

It uses the same rules as `run`, so they cannot disagree: columns, the rule on held-back notes, and the send checks. It counts notes with no cached answer, using the same key the run uses, and estimates cost from the entry's prices. A file with stops cannot start. Only the dataset file gets full KPIs, because TEST labels exist only for its notes, and the pre-check says so.

### Progress

`itemize_notes` takes `progress(done, total, spent_usd)`, called once per note. A failure inside it is ignored, because progress must not be able to break a run.

### Settings

`config/run.yaml` does not change. A `ui` section would change the settings hash, and make the run out of date. The page's limits are constants until `add-configuration-registry`.

### Versions and telemetry

The page adds no new telemetry. Uploads are stored by content hash, and each run keeps its folder and manifest. The command log records each run.

## Risks / Trade-offs

- [Only works on the presenter's machine] → accepted for the meeting.
- [A new real file holding an email or a name] → the scan stops it before any call, and the page shows a count. Use the AutoPay file.
- [An outage during a new-file upload] → notes go to Review, and the page shows the reason. The AutoPay file comes from the cache.
- [The download holds tool output on TEST notes] → the page warns against opening it before checking labels. The risk is small, because the review workbook already shows Opus's label.
