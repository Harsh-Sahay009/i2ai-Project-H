## ADDED Requirements

### Requirement: Authenticated access only
The Web UI SHALL require OIDC login in `prod`, SHALL accept only identities whose email domain is in `ui.allowed_email_domains` and that appear in `ui.role_map`, and SHALL end sessions after `ui.session_timeout_min` minutes of inactivity.

#### Scenario: Unknown user
- **WHEN** a user from an allowed domain signs in but is not in the role map
- **THEN** the UI shows an access-denied page and logs the attempt

### Requirement: Server-side role enforcement
Every UI action SHALL be authorized on the server against the user's role: upload and launch for operator or accountant; review for accountant or operator; adjudication for adjudicator; labelling for labeler or client owner; error workbench for operator; results and KPIs for all roles.

#### Scenario: Accountant calls the adjudication action
- **WHEN** an accountant session submits an adjudication request directly
- **THEN** the request is rejected with a permission error and logged

### Requirement: UI audit log
The UI SHALL record upload, run launch, review decision, adjudication, label, workbook download and TEST-example view events with role, pseudonymous user id, timestamp and object id, and MUST NOT record note text.

#### Scenario: Who launched a run
- **WHEN** an operator asks who launched a run
- **THEN** the audit log shows the role, pseudonymous id and time of the launch

### Requirement: No configuration editing in the UI
The UI SHALL display configuration values read-only and MUST NOT offer any way to change configurable parameters.

#### Scenario: Threshold page
- **WHEN** an operator opens the settings view
- **THEN** thresholds are shown with owner, version and expiry, and no edit control exists
