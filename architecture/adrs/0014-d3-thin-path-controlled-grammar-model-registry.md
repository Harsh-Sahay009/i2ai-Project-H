# 14. D3 as a thin path, with a controlled output grammar and a model registry

Date: 2026-11-02

## Status

Accepted. Sequences [8. Itemization as a bounded tool-calling agent](0008-bounded-tool-calling-agent.md) after D3, and refines [3. Local model by default; external API behind a fail-closed confidentiality gate](0003-local-model-default-external-gated.md) with a model registry.

## Context

The team will present D1, D2 and D3 together, and the full plan cannot be built in time. The team also requires that the model's output follow a controlled grammar, and that other models can be tested easily later.

## Decision

- **Thin path for D3.** One model call per distinct note, followed by the deterministic checks the scope requires. The agent loop, guardrails, Web UI, registries, dashboard and training pipeline come after D3, behind the same contracts.
- **Controlled grammar.** Every answer must be one JSON object with a fixed shape, closed value lists and amounts in a fixed format. The model writes no free prose. Evidence must be copied exactly from the note. Providers enforce the shape where they can, and one parser checks every answer whichever model wrote it. A rejected answer is retried once and then goes to Review. It is never repaired.
- **Model registry.** Models are entries in `config/models.yaml`. A model on a known API takes one entry and no code. A new API family takes one adapter class, and a shared contract test covers it automatically. `itemizer compare-models` runs models on the same TRAIN or VALIDATION notes, and never on TEST.
- **Provisional freeze.** Because the client reviews labels and sees the results in the same meeting, TEST can be frozen on team-resolved labels first. Results are labelled provisional until the client has reviewed the labels and TEST is sealed. The same run can be re-scored after that without using TEST budget.

Alternatives considered:

- Build the agent for D3: more model calls and more code in three days, with no D3 condition that needs it.
- Trust each provider's structured output alone: providers support different schema features, and some have none, so a parser that checks every answer is what makes models comparable.

## Consequences

- A weak model shows up as a low valid-first-try rate and more Review rows, not as bad data in the workbook.
- Level 1 numbers shown at the presentation are provisional, and can change if the client corrects labels.
- Course requirements that depend on the agent and guardrails are still to be built after D3.
