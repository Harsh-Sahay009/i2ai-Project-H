# Freight Invoice Itemizer — Architecture

C4 model as code (Structurizr DSL) plus design documentation and ADRs. Implementation is specified as OpenSpec changes in `../openspec/changes/`, one per platform component; their tasks are **not yet implemented**.

| Path | Content |
|---|---|
| `workspace.dsl` | C4 model: system context, 19 containers, components per container, dynamic views (weekly run, closed loop, agent loop), deployment view |
| `docs/01-overview.md` | Purpose, outcomes, invariants, slide-to-C4 mapping, deliverables |
| `docs/02-control-architecture.md` | Atlas M4–M6: owned/controlled/accessed, three placements, design rules, exit path, authority ladder |
| `docs/03-configurable-layer.md` | Parameter catalog: every configurable parameter with default, limits, owner, horizon |
| `docs/04-kpi-calculator.md` | Metric definitions for errors a–g and success a–e, populations, matching, weighting, intervals |
| `docs/05-data-versioning.md` | What is versioned, how, and the run manifest |
| `docs/06-telemetry-closed-loop.md` | Three telemetry layers, closed loop, adjudication capacity, recertification |
| `docs/07-traceability.md` | Metrics → components → OpenSpec changes; build order |
| `docs/08-agentic-design.md` | Agent loop, custom tools and docstring standard, guardrails, with/without evaluation, agentic workflows |
| `docs/09-data-protection-synthetic-data.md` | Client data protection; synthetic data generation and quality checks |
| `docs/10-course-requirements.md` | Course requirements, presentation plan, rubric coverage, repo layout, references |
| `adrs/` | Architecture decision records 0001–0013 (0002 superseded by 0007; 0007 amended by 0011–0013) |
| `export/` | Generated Mermaid, C4-PlantUML and JSON views (regenerate after editing the DSL) |

## Render and validate

```bash
# Interactive viewer at http://localhost:8080
docker run -it --rm -p 8080:8080 -v "$PWD/architecture":/usr/local/structurizr structurizr/lite

# Validate and export (Structurizr vNext tooling)
docker run --rm -v "$PWD/architecture":/w structurizr/structurizr validate -w /w/workspace.dsl
docker run --rm -v "$PWD/architecture":/w structurizr/structurizr export -w /w/workspace.dsl -f mermaid -o /w/export/mermaid
docker run --rm -v "$PWD/architecture":/w structurizr/structurizr export -w /w/workspace.dsl -f plantuml/c4plantuml -o /w/export/c4plantuml
```

## OpenSpec

```bash
openspec list                 # 22 changes, 0 tasks done
openspec validate --all --strict
openspec show add-kpi-calculator
```
