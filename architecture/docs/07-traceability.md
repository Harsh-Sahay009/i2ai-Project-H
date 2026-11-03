# 7. Traceability: metrics, components, changes

## 7.1 Success metrics → where they are produced and computed

| Metric | Data produced by | Computed by | OpenSpec change |
|---|---|---|---|
| Error a — Bad classification | Classifier (Category Mapper), Ground Truth (gold) | KPI: Item Matcher, Error Taxonomy Classifier | add-itemization-classifier, add-kpi-calculator |
| Error b — Wrong counts | Classifier (items per row) | KPI: Item Matcher | add-itemization-classifier, add-kpi-calculator |
| Error c — Not enough categories (catch-all share) | Category Mapper (`other_unmapped`) | KPI: Metric Engine | add-ground-truth-store, add-kpi-calculator |
| Error d — Not enough categories (reviewer view) | Review System (reason `no_fitting_category`) | KPI: Metric Engine | add-human-review-system, add-kpi-calculator |
| Error e — Reproducibility | Run manifest, Response Cache, Version Registry | KPI: Metric Engine (rerun agreement) | add-common-core-contracts, add-model-router, add-run-console |
| Error f — Low confidence | Confidence Scorer, Outcome Assigner | KPI: Metric Engine (Review share, ECE) | add-itemization-classifier, add-training-calibration-pipeline |
| Error g — Wrong amounts | Extractor, Amount Reconciler, invariants | KPI: Item Matcher, invariant count | add-common-core-contracts, add-itemization-classifier |
| Success a — Accuracy | Classifier + Ground Truth | KPI: Stratum Weighter, Uncertainty, Level Gate | add-kpi-calculator |
| Success b — Cost of inference | Router: Cost Meter | KPI: Metric Engine + price table | add-model-router, add-kpi-calculator |
| Success c — Verification text | Evidence Verifier | KPI: Metric Engine | add-itemization-classifier |
| Success d — AUC | Confidence Scorer | KPI: Metric Engine | add-kpi-calculator |
| Success e — Approval rate | Web UI Review Queue Page → Review System (decisions, blind audit) | KPI: Metric Engine | add-web-ui, add-human-review-system |
| Accountant minutes per dispute | Web UI review timestamps | KPI: Metric Engine | add-web-ui, add-kpi-calculator |
| Coverage ($, rows) | Outcome Assigner | KPI: Metric Engine, Level Gate | add-kpi-calculator |
| Loop health | Review System, Training pipeline | KPI: Loop Health Meter | add-human-review-system, add-training-calibration-pipeline |
| Per-carrier coverage and accuracy | Outcome Assigner, Ground Truth | KPI: Metric Engine | add-kpi-calculator, add-kpi-dashboard |
| Cost-driver summary (Level 3) | Classifier items | KPI: Metric Engine | add-kpi-calculator, add-kpi-dashboard |

## 7.2 Containers → OpenSpec changes

| C4 container | Change | Capabilities |
|---|---|---|
| *(all — shared contracts)* | add-common-core-contracts | item-schema-contract, run-manifest |
| Configuration Registry | add-configuration-registry | configuration-registry |
| Version & Artifact Registry | add-version-artifact-registry | version-registry |
| Ground Truth Store | add-ground-truth-store | charge-taxonomy, evaluation-sets |
| Ground Truth Bootstrap | add-ground-truth-bootstrap | dataset-profile-split, taxonomy-drafting, test-set-preparation |
| Run Console (Acceptance Runner), KPI Dashboard (Methodology Report Builder) | add-delivery-acceptance | deliverable-acceptance, methodology-report |
| Model Router (Model Registry, Provider Interface), Itemization Classifier (Structured Response Parser, Amount Reconciler, Outcome Assigner), Output Formatter, KPI Calculator, Run Console (Model Comparison Runner, Acceptance Runner) | add-d3-thin-path | output-grammar, model-registry, d3-itemization, d3-output, level-evaluation, d3-presentation |
| Agent Tool Library & MCP Server | add-agent-tools | agent-tools, mcp-analyst-tools |
| Guardrail Layer | add-guardrails | guardrails |
| Synthetic Data Generator | add-synthetic-data-generator | synthetic-data |
| KPI Calculator (ablation + agent metrics) | add-guardrail-evaluation | guardrail-evaluation |
| *(repo)* skill folder | add-skill-folder | skill-folder |
| Web UI | add-web-ui | ui-access-control, export-upload, results-explorer, error-review, review-workbench, agent-trace-viewer, kpi-view |
| Run Console | add-run-console | run-console |
| Data Transformation & Check | add-data-transformation-check | data-ingestion |
| Model Router (+ Local Model Runtime) | add-model-router | model-routing |
| Itemization Classifier | add-itemization-classifier | itemization |
| Output Formatter | add-output-formatter | itemized-output |
| Telemetry & Episode Store | add-telemetry-episode-store | telemetry |
| Human Review System | add-human-review-system | review-workflow, adjudication |
| KPI Calculator | add-kpi-calculator | kpi-metrics, level-gates |
| KPI Dashboard | add-kpi-dashboard | kpi-dashboard |
| Training & Calibration Pipeline | add-training-calibration-pipeline | calibration-loop, promotion-gate |

## 7.3 Build order

0. **Bootstrap (D1, D2), first and standalone:** add-ground-truth-bootstrap. It depends on no other change, because D1 and D2 are late and D3 is measured on them.
0a. **D3 thin path, next and standalone:** add-d3-thin-path. D1, D2 and D3 are presented together and the full plan cannot be built in time (ADR 0014), so this is the shortest path to D3's done-when conditions: one model call per distinct note, deterministic checks, the workbook, Level gates and a one-page status. Later changes replace parts of it behind the same contracts.
1. **Foundation:** add-common-core-contracts → add-configuration-registry → add-version-artifact-registry → add-telemetry-episode-store → add-synthetic-data-generator (so every later change tests on synthetic data)
2. **Ground truth store:** add-ground-truth-store, which registers what the bootstrap produced
3. **Full path, after D3:** add-data-transformation-check → add-model-router → add-agent-tools → add-guardrails → add-itemization-classifier → add-output-formatter → add-run-console → add-kpi-calculator → add-kpi-dashboard → add-delivery-acceptance (D3 check) → add-web-ui (access control, upload, run monitor, results explorer)
4. **Final (D4, Level 2):** add-human-review-system → add-web-ui (review, adjudication, labelling, error workbench, agent trace, KPI view) → add-training-calibration-pipeline → add-delivery-acceptance (D4 check, D5 report)
5. **Course deliverables (TP3):** add-guardrail-evaluation → add-skill-folder → poster, demos (docs/10)

D2's labelling uses Excel workbooks from add-ground-truth-bootstrap, because the UI will not exist in time. The UI labelling page serves later TRAIN, VALIDATION and FRESH labelling.

## 7.4 Deliverables → OpenSpec changes

| Deliverable | Tooling | Work done by people |
|---|---|---|
| D1 Charge category list | add-ground-truth-bootstrap, add-ground-truth-store | Team edits the draft; Jake approves in writing |
| D2 Locked test set | add-ground-truth-bootstrap, add-ground-truth-store | Team labels 200 notes; Jake or a PPG accountant reviews 50 |
| D3 Prototype | add-d3-thin-path | Team labels TEST; Jake sees the prototype |
| D4 Final tool | add-delivery-acceptance plus all containers | Team runs the acceptance check |
| D5 Methodology report | add-delivery-acceptance | Team writes the prose; an outside reader tries the rerun |
