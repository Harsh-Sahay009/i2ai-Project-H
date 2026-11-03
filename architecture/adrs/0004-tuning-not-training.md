# 4. "Training Algorithm" means calibration and configuration tuning, not weight training

Date: 2026-10-31

## Status

Accepted. Amended by [12. Separate train, validation and test sets](0012-train-validation-test-split.md): DEV becomes TRAIN and VALIDATION, and promotion no longer uses TEST.

## Context

~1,347 rows and a 200-note test set are too small to fine-tune responsibly, and D2 must never tune the tool.

## Decision

The Training & Calibration Pipeline changes only versioned configurable-layer artifacts: lexicon, few-shot set, prompt template, thresholds, calibration map. It reads DEV labels and closed cases, never TEST labels. Promotion uses one aggregate TEST evaluation per candidate within a peek budget.

## Consequences

Every behaviour change is a published, revertible configuration version. Fine-tuning can be added later behind the same provider interface.
