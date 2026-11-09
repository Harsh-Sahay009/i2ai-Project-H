# Final handoff and rerun guide

This guide reproduces the existing-data candidate export without model calls.
Use [the final report](final_methodology_report.md) for results and limits.

Final closeout verification on November 9: **1,045 tests passed in 298.52 seconds**,
including 20 shipment-export tests. The source-data offline rerun matched the
expected counts below. All eight report PDF pages were rendered and inspected;
Git whitespace checks passed. Private workbook readback verified source-row
coverage, text identifiers, reviewed label counts and the confirmed context
decision. This verification made no additional model/API requests.

## Public versus private inputs

The public repository supplies source, configuration and tests. Obtain these
private artifacts separately through the team's approved channel:

```text
AutoPay Dispute Data 20220815_withExamples.xlsx
data/evaluation/openai-mini-v1/all/note_results.json
data/evaluation/human_adjudication/shipment_overlay_v1.json  # optional decisions
```

The source workbook SHA-256 must be
`e08da6c7fd6e03036d537a13ed0a52748ef81fc5cedea0df7f3ec037bc43c0e5`.
Do not commit private data or credentials. A public clone cannot reproduce a
confidential experiment without receiving its matching private inputs.

## Install and verify

```bash
uv sync --extra llm --extra ui --group dev
PYTHONPATH=src uv run pytest -q
```

Use Python 3.12 or newer. Explicit `PYTHONPATH=src` avoids accidentally importing
another checkout when a virtual environment is shared between worktrees.

## Offline candidate export

```bash
PYTHONPATH=src uv run python -m itemizer.shipment_review \
  --source 'AutoPay Dispute Data 20220815_withExamples.xlsx' \
  --predictions data/evaluation/openai-mini-v1/all/note_results.json \
  --overlay data/evaluation/human_adjudication/shipment_overlay_v1.json \
  --output data/evaluation/shipment-review-v1
```

The optional overlay is an object with `dataset_sha256` and `rows`. Each row
decision has `decision_file`, `expected_sap_bol`, `expected_fingerprint`, optional
`items`, and flags. Every joined source row must carry the same applicable
decision. The source hash and expected BOL/description are checked before the
correction is applied. Omit `--overlay` to inspect raw saved-model candidates.
An overlay from a different/reordered workbook must be re-reviewed, not forced.

Expected output with the recorded 18-note overlay: 1,347 source rows, 1,284
shipment/description groups, 63 repeated join rows, six missing BOL rows, 1,447
expense candidates, 13 context items and 189 flagged groups. JSON is the
canonical interchange output; CSV identifier columns must be imported as text.
This command does not recreate the subsequent AI-reviewed proposal automatically.

## Reviewed and assisted-label snapshots

The following artifacts are private downstream review records, not raw model
responses. Their scripts contain concrete source-case decisions and stay private:

```text
data/evaluation/ai-review-2026-11-09/review.py
data/evaluation/ai-review-2026-11-09/reviewed_report.json
data/evaluation/assisted-labels-2026-11-09/label_source.py
data/evaluation/assisted-labels-2026-11-09/ai_assisted_labels.json
data/evaluation/assisted-labels-2026-11-09/label_lock.json
data/evaluation/assisted-labels-2026-11-09/user_judgment.json
data/evaluation/assisted-labels-2026-11-09/updated_shipment_review.json
```

The final local workbook is
`data/outputs/assisted-labels-2026-11-09/Completed_Labels_and_Reviewed_Output.xlsx`.
It has 50 assisted labels, 245 review decisions, 1,249 proposed expense candidates,
94 context items, a 1,447-item claim audit and all 1,347 source rows. Of the review
decisions, 36 groups remain unresolved; 68 held claim items are excluded from
proposed expense candidates. No independent-human approval is implied.

Preserve both the pre-user-judgment review and its updated version. Do not rerun
the earlier `review.py` and mistake its 1,250-candidate output for the final
1,249-candidate version. The explicit user judgment removes one additional
generic balance from expenses. Read the label lock and user judgment alongside
the updated snapshot. Review is not model tuning or a new accuracy measurement.

## Frozen inference, budgets and acceptance

Keep original Gemini and OpenAI experiments in their matching frozen checkouts.
The final exporter checkout changes the package source hash; it must not be used
to overwrite an earlier protocol. Creating or resuming inference is separate
from this offline handoff and may make paid requests. Do not delete the shared
spending ledger, reuse an experiment name for changed inputs, or mix results
across models. The completed OpenAI experiment cost $1.05022950 of $5 authorized.

The original CLI/UI run workflow remains available in README.md. Its default
provider and gates are separate from the offline review command. Local doctor,
successful tests, completed AI labels and exported workbooks do not certify
independent human review or client acceptance. Record actual acceptance evidence
or a real agreed scope change; do not fabricate approval records to close gates.
