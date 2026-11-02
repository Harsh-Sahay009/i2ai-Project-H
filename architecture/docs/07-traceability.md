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

## 7.2 Containers → OpenSpec changes

| C4 container | Change | Capabilities |
|---|---|---|
| *(all — shared contracts)* | add-common-core-contracts | item-schema-contract, run-manifest |
| Configuration Registry | add-configuration-registry | configuration-registry |
| Version & Artifact Registry | add-version-artifact-registry | version-registry |
| Ground Truth Store | add-ground-truth-store | charge-taxonomy, evaluation-sets |
| Agent Tool Library & MCP Server | add-agent-tools | agent-tools, mcp-analyst-tools |
| Guardrail Layer | add-guardrails | guardrails |
| Synthetic Data Generator | add-synthetic-data-generator | synthetic-data |
| KPI Calculator (ablation + agent metrics) | add-guardrail-evaluation | guardrail-evaluation |
| *(repo)* skill folder | add-skill-folder | skill-folder |
| Web UI | add-web-ui | ui-access-control, export-upload, results-explorer, error-review, review-workbench |
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

1. **Foundation:** add-common-core-contracts → add-configuration-registry → add-version-artifact-registry → add-telemetry-episode-store → add-synthetic-data-generator (so every later change tests on synthetic data)
2. **Ground truth (D1, D2):** add-ground-truth-store, labelling part of add-human-review-system
3. **Prototype path (D3, Level 1):** add-data-transformation-check → add-model-router → add-agent-tools → add-guardrails → add-itemization-classifier → add-output-formatter → add-run-console → add-kpi-calculator → add-kpi-dashboard → add-web-ui (access control, upload, run monitor, results explorer)
4. **Final (D4, Level 2):** add-human-review-system → add-web-ui (review, adjudication, labelling, error workbench, KPI view) → add-training-calibration-pipeline
5. **Course deliverables (TP3):** add-guardrail-evaluation → add-skill-folder → poster, demos (docs/10)

Blind labelling for D2 (due 22 Oct) is already past, so the fallback labelling workbook remains the D2 path; the UI labelling page serves DEV and FRESH labelling.
