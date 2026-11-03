# 13. The project uses only an anonymized open dataset

Date: 2026-11-02

## Status

Accepted. Amends [3. Local model by default; external API behind a fail-closed confidentiality gate](0003-local-model-default-external-gated.md) and [7. Web UI for upload, results, error review and review](0007-web-ui-for-upload-review-results.md). [9. Synthetic data for every public artifact](0009-synthetic-data-for-public-artifacts.md) stays in force.

## Context

The team reports that the project will use one dataset only: an anonymized open version of the data. The confidentiality rules in the scope and in ADR 0003 exist to stop identifiable text from reaching an outside AI provider. Using the data does not mean publishing it, and sending anonymized text to a model is a different act from putting it in a public repo.

This ADR records the team's statement. All partitions come from one file, `AutoPay Dispute Data 20220815_withExamples.xlsx`, which stays out of Git.

On 2026-11-02 the team confirmed that this file is free, open and publicly available, so it may go to an external model. It is not fully anonymized: it has the same totals as the client export cited in the scope, its notes hold 15 email addresses and at least 42 phrases that look like names, and most destination addresses are street addresses. Only note text and the disputed amount go to a model, so addresses do not leave. The D1 document quotes around the names.

## Decision

- **Dataset class.** A new parameter `data.dataset_class` takes `open_anonymized` or `client_confidential`. The core default is `client_confidential`; the `dev` and `prod` environments set `open_anonymized`. It is recorded in every run manifest. `data.source_ref` says where the dataset came from and is required for `open_anonymized`.
- **Gate.** The Confidentiality Gate still fails closed. An external call is allowed only when the dataset is `open_anonymized` with a source reference, or when `routing.external_ai_approved` is true with `routing.approval_ref` set.
- **Route.** The `dev` and `prod` environments use `routing.route = external`, with fallback `[local, rules_only]`. The local model stays as the tested fallback and exit path.
- **Masking removed.** The Confidentiality Masker and masking map are no longer built.
- **Checks kept.** The Dataset Profiler scans the notes for remaining names, phone numbers and emails. The Privacy Guard screens every model-bound payload.
- **Still not published.** The dataset stays out of Git. The public repo, poster and demos use synthetic data only, as ADR 0009 says. Taxonomy examples in Git are stored as fingerprints and offsets.
- **Storage.** The encrypted-volume check and deletion tombstones are dropped.

## Consequences

- The external model can be used without masking, which reduces the risk to the 30-minute limit. Cost moves from GPU time to API fees, limited by `budget.max_usd_per_run`. Neither has been measured yet.
- **No FRESH month is expected**, so every accuracy number is labelled in-sample, as the scope allows.
- **No weekly exports are expected.** PROD metrics such as approval rate and audit disagreement exist only for runs on this dataset that people actually review.
- D4's "new export" check uses a synthetic export unless PPG provides another file. Holding out the last month was rejected: August 2022 has only 8 notes that appear in no earlier month.
- If PPG later runs the tool on confidential exports, the `client_confidential` class blocks the external route unless approved in writing, and masking would need to be built then.
- Course requirement 6 now rests on anonymized data, the gate, the Privacy Guard, no publication, and synthetic data with quality checks. The team should confirm this satisfies the course.

## Open items

- Add the public link for the file to `data.source_ref`.
- The scope says changes after approval are agreed in writing. One line from Jake confirming this dataset may go to an external model should be recorded in `data.source_ref`.
