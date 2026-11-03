## ADDED Requirements

### Requirement: Draft from TRAIN notes only
The Taxonomy Drafter MUST use TRAIN notes only, and MUST refuse to send text unless `data.dataset_class` is `open_anonymized` with `data.source_ref` set.

#### Scenario: TEST note in the sample
- **WHEN** the draft sample contains a note assigned to TEST
- **THEN** the draft fails and names the fingerprint

#### Scenario: Dataset class not cleared
- **WHEN** `data.dataset_class` is `client_confidential`
- **THEN** no text is sent and the command stops with an error

### Requirement: Draft content
The draft SHALL contain 12 to 20 categories plus `other_unmapped`, each with a code, name, definition, inclusion and exclusion notes and at least one real example, and SHALL record the model id and prompt hash.

#### Scenario: Too few categories
- **WHEN** the model proposes 9 categories
- **THEN** validation fails and reports the count

### Requirement: Verbatim examples
Every example SHALL be a verbatim substring of its source note, and any example that is not verbatim SHALL be dropped and reported.

#### Scenario: Paraphrased quote
- **WHEN** the model quotes "detention 2 hours" but the note says "DET 2HRS"
- **THEN** the example is dropped and listed in the draft report

### Requirement: Nothing is sent without asking
The command SHALL only write the prompt unless `--send` is given, and a draft loaded with `--proposal-file` SHALL pass the same checks as a model's answer.

#### Scenario: Dry run
- **WHEN** an operator runs `gt draft-taxonomy` without `--send`
- **THEN** no text leaves the machine, and the note count and prompt location are shown

### Requirement: No note text in Git
`taxonomy/categories.yaml` MUST store examples as note fingerprints and offsets, and quotes SHALL be resolved from the dataset only when a document is rendered.

#### Scenario: Quote in the taxonomy file
- **WHEN** the file contains note text in an example
- **THEN** the validator fails

### Requirement: Approval document
The system SHALL generate a document of about two pages listing each category with its definition and real examples, for the client owner to approve.

#### Scenario: Document for Jake
- **WHEN** the operator runs `gt approval-doc`
- **THEN** the document is written under the data root and not under the Git working tree

### Requirement: Written approval recorded
The system SHALL tag a taxonomy as `taxonomy@D1-approved` only with an approval record holding the approver role, the date and the hash of the evidence file, and labels made against a draft SHALL be marked provisional.

#### Scenario: Labelling before approval
- **WHEN** labelling starts before Jake approves
- **THEN** the labels are marked provisional, and sealing requires the approved version or a published mapping to it
