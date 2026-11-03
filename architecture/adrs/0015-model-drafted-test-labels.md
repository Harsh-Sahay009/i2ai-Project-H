# 15. Claude Opus drafts TEST labels until people have checked them

Date: 2026-11-03

## Status

Accepted. Amends [12. Separate train, validation and test sets from one file](0012-train-validation-test-split.md) for TEST labels only.

## Context

D1, D2 and D3 are presented together on 5 November, and no TEST label exists. ADR 0012 has people write TEST labels, because accuracy against labels the tool wrote only shows the tool agreeing with itself. The team has decided to have Claude Opus draft the labels now, so that D3 can be measured, and to review them afterwards.

## Decision

Claude Opus drafts the 200 TEST labels through the API, from the labelling rules, with no tool output. Each label is marked `model_draft`. Every number that rests on drafts says so. People can check or correct any label through a supported command, and re-scoring the same run needs no model calls. The final seal refuses while any draft is unchecked. VALIDATION stays with people.

## Consequences

- Until people have checked the labels, accuracy shows how far the tool agrees with Opus, and not that it is right. Level results are provisional and marked as resting on drafts.
- D2 as the scope defines it, labelled by the team with 50 notes reviewed by the client, is not met by drafts. D3 cannot read `done` until the labels are checked and sealed.
- The scope says the team labels the notes, so this goes on the scope change list.
- Two passes by one model are not two people, so their agreement figure is weak evidence.
