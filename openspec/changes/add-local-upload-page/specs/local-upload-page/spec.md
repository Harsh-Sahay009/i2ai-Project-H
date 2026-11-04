## ADDED Requirements

### Requirement: Upload with checks
The page SHALL accept only `.xlsx` files up to 25 MB, and SHALL store each by the hash of its content, so a file name never reaches a path.

#### Scenario: Wrong type
- **WHEN** a person uploads a csv
- **THEN** the page refuses it with a plain message, and stores nothing

#### Scenario: Too large
- **WHEN** a file is over 25 MB
- **THEN** the page refuses it, and stores nothing

#### Scenario: Same file twice
- **WHEN** a file with a stored hash is uploaded again
- **THEN** it goes to the same pre-check, with no duplicate

### Requirement: Pre-check before any model call
The page SHALL show the rows, distinct notes, new model calls, estimated cost, whether the file gets full KPIs, and anything that stops it, using the same rules as a run. The cost estimate SHALL use the model's prices and MUST be within `budget.max_usd_per_run` for the run to start.

#### Scenario: Missing column
- **WHEN** an export lacks the note column
- **THEN** the pre-check names the column, and the start button is disabled

#### Scenario: Flagged by the scan
- **WHEN** another export holds an email address and the model is external
- **THEN** the pre-check gives a count and no note text, and the start button is disabled

#### Scenario: The AutoPay file
- **WHEN** the dataset file is uploaded after a run on all rows
- **THEN** the pre-check says no new model calls are needed, and that it gets full KPIs

#### Scenario: Another file
- **WHEN** a different file is uploaded
- **THEN** the pre-check says it gets the output Excel and coverage, and no accuracy

### Requirement: Runs through the same pipeline
Starting a run SHALL call the same pipeline as `itemizer run`, on a background thread, with `runtime.concurrency` and `budget.max_usd_per_run` as usual. The page SHALL show progress, and SHALL refuse a second job while one is running.

#### Scenario: Second job
- **WHEN** a run is in progress and a person starts another
- **THEN** the page refuses, and links to the running job

#### Scenario: Browser closed
- **WHEN** the browser closes during a run
- **THEN** the job finishes, and its results are on the home page

#### Scenario: Failure
- **WHEN** a run stops with an unexpected error whose message quotes a note
- **THEN** the page shows the error's type only

### Requirement: Output Excel
A finished run SHALL offer its output workbook for download, and the page MUST warn that it holds tool output on TEST notes.

#### Scenario: Download
- **WHEN** a person downloads a finished run's output
- **THEN** the file is that run's workbook, with the Items sheet of expenses

#### Scenario: Bad run id
- **WHEN** a request names a run id that does not fit the pattern
- **THEN** the page refuses, and reads no file

### Requirement: KPIs on the page
A run's page SHALL show outcomes, coverage and rows and dollars accepted without reading. For a run on all rows of the dataset file, it SHALL also offer scoring and show the Level 1 result, and `/status` SHALL show the status page. Spending past `kpi.test_peek_budget_per_milestone` MUST stay on the command line.

#### Scenario: Scoring refused
- **WHEN** the TEST budget is spent and a person scores a run with different answers
- **THEN** the page shows the refusal, and says to use the command line

#### Scenario: Scoring the same answers
- **WHEN** labels were corrected and a person scores the same answers again
- **THEN** no model is called, no budget is used, and the result updates

### Requirement: This machine only
The server MUST bind to `127.0.0.1`, and MUST refuse a request whose `Host` is not local and a `POST` whose `Origin` is not local.

#### Scenario: Another web page
- **WHEN** a web page on another site posts to the server from the same browser
- **THEN** the server refuses, and starts nothing

#### Scenario: Rebinding
- **WHEN** a request arrives with another site's `Host`
- **THEN** the server refuses
