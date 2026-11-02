## 1. Foundation

- [ ] 1.1 Scaffold `itemizer.ui` Streamlit app with multipage layout, usage stats disabled, XSRF protection on
- [ ] 1.2 Add `ui.*` parameters to the parameter schema and defaults
- [ ] 1.3 Implement OIDC login, domain allowlist, role map and session timeout
- [ ] 1.4 Implement server-side permission decorator for every action
- [ ] 1.5 Implement UI audit logger writing to the episode store

## 2. Upload and runs (D3)

- [ ] 2.1 Implement upload with type/size checks, hashing, CAS registration, duplicate detection
- [ ] 2.2 Implement pre-check report using the Input Contract Validator
- [ ] 2.3 Implement background job launcher for `itemizer run` with concurrency limit
- [ ] 2.4 Implement run monitor from action telemetry

## 3. Results (D3)

- [ ] 3.1 Implement outcome table with filters and pagination
- [ ] 3.2 Implement note view with evidence highlighting from stored offsets
- [ ] 3.3 Implement outcome explanation from decision telemetry
- [ ] 3.4 Implement workbook download from the registry with hash check

## 4. Errors and KPIs (D4)

- [ ] 4.1 Implement error workbench over KPI error-typed records for DEV and PROD
- [ ] 4.2 Implement TEST aggregate view and gated example release with audit
- [ ] 4.3 Implement run comparison with version banner
- [ ] 4.4 Implement KPI View on the shared panel definitions

## 5. Review, adjudication, labelling (D4)

- [ ] 5.1 Implement Review Queue Page with data_editor corrections, reason codes and prediction-hash submission
- [ ] 5.2 Implement blind audit row rendering
- [ ] 5.3 Implement Adjudication Page with self-adjudication guard
- [ ] 5.4 Implement Blind Labelling Page and disagreement resolution view
- [ ] 5.5 Capture review open/submit timestamps

## 6. Deployment and tests

- [ ] 6.1 Write Caddy config (TLS, IP allowlist) and service unit for the team server
- [ ] 6.2 Permission tests: every action × every role
- [ ] 6.3 Leakage tests: labelling and TEST views never receive predictions or row data
- [ ] 6.4 Tests per scenario in all five capability specs
