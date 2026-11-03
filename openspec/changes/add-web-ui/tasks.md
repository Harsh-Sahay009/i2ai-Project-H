## 1. Foundation

- [ ] 1.1 Scaffold `itemizer.ui` FastAPI app with a Jinja2 base template, shared navigation and the `itemizer ui` command, with no third-party scripts or analytics
- [ ] 1.2 Add `ui.*` parameters to the parameter schema and defaults
- [ ] 1.3 Implement username and password login with hashed passwords stored outside Git, an account creation command, role map and session timeout
- [ ] 1.4 Implement signed session cookies and a CSRF token on every POST
- [ ] 1.5 Implement server-side permission decorator for every action
- [ ] 1.6 Implement UI audit logger writing to the episode store

## 2. Upload and runs (D3)

- [ ] 2.1 Implement upload with type/size checks, hashing, CAS registration, duplicate detection
- [ ] 2.2 Implement pre-check report using the Input Contract Validator
- [ ] 2.3 Implement background job launcher for `itemizer run` with concurrency limit
- [ ] 2.4 Implement run monitor from action telemetry, with status polling in plain JavaScript
- [ ] 2.5 Mark synthetic uploads, show the synthetic banner and list those runs apart

## 3. Results (D3)

- [ ] 3.1 Implement outcome table with filters and pagination
- [ ] 3.2 Implement note view with evidence highlighting from stored offsets
- [ ] 3.3 Implement outcome explanation from decision telemetry
- [ ] 3.4 Implement workbook download from the registry with hash check

## 4. Errors, KPIs and traces (D4)

- [ ] 4.1 Implement error workbench over KPI error-typed records for TRAIN and PROD, with aggregates only for VALIDATION
- [ ] 4.2 Implement TEST aggregate view and gated example release with audit
- [ ] 4.3 Implement run comparison with version banner
- [ ] 4.4 Implement KPI View on the shared panel templates
- [ ] 4.5 Implement Agent Trace Viewer from tool-call and guard telemetry
- [ ] 4.6 Implement Tool Reference page from the Tool Registry

## 5. Review, adjudication, labelling (D4)

- [ ] 5.1 Implement Review Queue Page with HTML forms for corrected items, reason codes and prediction-hash submission
- [ ] 5.2 Implement blind audit row rendering
- [ ] 5.3 Implement Adjudication Page with self-adjudication guard
- [ ] 5.4 Implement Blind Labelling Page and client review view
- [ ] 5.5 Capture review open/submit timestamps

## 6. Deployment and tests

- [ ] 6.1 Write Caddy config (TLS) and service unit for the team server
- [ ] 6.2 Permission tests: every action × every role
- [ ] 6.3 Leakage tests: labelling pages never receive predictions, and VALIDATION and TEST views never receive row data
- [ ] 6.4 Security tests: CSRF rejection, expired sessions, upload limits, no passwords or note text in logs
- [ ] 6.5 Tests per scenario in all seven capability specs
