## ADDED Requirements

### Requirement: Review queue page
The Review Queue Page SHALL show the capacity-bounded queue from the Human Review System and SHALL let reviewers approve, edit (corrected items) or reject each row with a reason code, submitting through the Review Decision Intake together with the prediction hash displayed.

#### Scenario: Stale prediction
- **WHEN** a reviewer submits a decision for a row whose prediction changed after the page loaded
- **THEN** the decision is rejected and the reviewer is shown the current prediction

#### Scenario: Corrected amount
- **WHEN** a reviewer corrects an item amount
- **THEN** the correction is stored as an outcome record and the tool's prediction is unchanged

### Requirement: Blind audit rows
Audit-sample rows MUST be shown without the tool's outcome and confidence.

#### Scenario: Audit row
- **WHEN** a reviewer opens an audit-sample Verified row
- **THEN** items and note are shown and the outcome and confidence band are hidden

### Requirement: Adjudication page
The Adjudication Page SHALL let an adjudicator assign one of AI wrong, human wrong, context changed or genuine exception with a reason code, and MUST refuse adjudication of a case the same user reviewed.

#### Scenario: Self-adjudication
- **WHEN** a user tries to adjudicate their own review decision
- **THEN** the action is refused

### Requirement: Blind labelling page
The Blind Labelling Page SHALL show only the note and taxonomy, SHALL never receive predictions or another labeller's labels, and SHALL offer the client reviewer a view to review all 50 double-labelled notes and resolve disagreements.

#### Scenario: Second labeller
- **WHEN** the second labeller opens a note already labelled by the first
- **THEN** no labels or predictions are shown

### Requirement: Review time capture
The UI SHALL record when a row is opened and when its decision is submitted, so that accountant minutes per dispute can be computed.

#### Scenario: Minutes per dispute
- **WHEN** a reviewer opens a row at 10:02:10 and submits at 10:03:40
- **THEN** the outcome record carries both timestamps
