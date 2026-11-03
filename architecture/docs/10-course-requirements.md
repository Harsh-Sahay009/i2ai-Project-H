# 10. Course requirements, presentation and rubric coverage

## 10.1 Technical requirements → where they are met

| # | Requirement | Architecture elements | OpenSpec change(s) | Evidence for judges |
|---|---|---|---|---|
| 1 | Agentic workflow (team) and for the client | Itemization Agent; Claude Code + OpenSpec + Structurizr dev loop; MCP analyst tools + client skill | add-itemization-classifier, add-agent-tools, add-skill-folder | §8.5–8.6; OpenSpec history; agent trace in the UI |
| 2 | Pretrained model incorporated | Hosted LLM as agent engine; open-weights LLM (Ollama) as fallback; pretrained NER | add-model-router, add-itemization-classifier | §8.1; run manifest shows the model identity |
| 3 | ≥ 5 custom agentic tools with LLM-oriented docstrings that make behaviour more deterministic | 8 pipeline tools + 5 MCP analyst tools; docstring linter | add-agent-tools | §8.3; `itemizer tools lint`; tool reference page |
| 4 | Skill folder with `SKILL.md` and templates | `skills/itemizer-weekly-review/`, `skills/itemizer-analyst/`, `skills/itemizer-dev/` | add-skill-folder | Folder in repo; demoed with Claude Code |
| 5 | Evaluation methods | KPI Calculator: errors a–g, success a–e, intervals, weighting, level gates, agent metrics, guardrail ablation | add-kpi-calculator, add-guardrail-evaluation | §4; dashboard |
| 6 | Client data protection / simulated data with quality assurance | Anonymized dataset with a scan before any send, fail-closed gate, Privacy Guard, role checks, no publication; Synthetic Data Generator with fidelity / privacy / validity / utility checks. To confirm with the course (ADR 0013) | add-ground-truth-bootstrap, add-model-router, add-guardrails, add-synthetic-data-generator | §9 |
| 7 | Safety guardrails | Guardrail Layer (input, tool-call, output, action, privacy) + invariants + blind audit | add-guardrails | §8.4 |
| 7a | With vs without guardrails | Guardrail Ablation Evaluator on SYNTH + ADV | add-guardrail-evaluation | §8.4a table + trace pairs |

## 10.2 Presentation plan

| Item | Content | Owner (rotate so all four speak) |
|---|---|---|
| Problem statement | 1,347 disputes, 86% catch-all reason code, $186k disputed, accountants read every note; goal: accept rows without reading the note | Member A |
| Research paper | The course's **required paper** (to confirm). Supporting papers: ReAct (agent loop), indirect prompt injection (guardrails), hidden technical debt (common core) | Member B |
| Code demo: one concept | **"The LLM never does arithmetic."** One note, two runs: (1) guardrails off, the model states "2 hrs @ 75 = 160" and edits a lumper fee to make the row add up; (2) guardrails on, `compute_rate_times_quantity` returns 150.00, `verify_evidence_span` rejects the paraphrase, and the row is flagged Discrepancy, not forced. About 40 lines on screen | Member C |
| Website demo | Upload a synthetic export → watch the run → Results Explorer with highlighted evidence → Agent Trace Viewer (tool calls + guard decisions) → review a row → KPI view with the guardrail ablation table | Member D |
| Business opportunity and challenges | Minutes per dispute saved × monthly volume; overpayment avoided; challenges: data access, note quality, reviewer capacity, model dependency (exit path) | Member A |
| What judges learn about AI | Agents are reliable when tools compute and guards decide; ablation numbers show the gap | All |

Non-technical framing: "The AI reads the note like a clerk would, but it has to use a calculator and a highlighter we built, and a supervisor checks its work before anyone sees it."

## 10.3 Rubric support

| Rubric line | How the design supports it |
|---|---|
| Code demo: technically challenging, sound | Bounded agent + deterministic tools + guard ablation in one script on synthetic data |
| Website demo: creative use of vibe coding | Web UI built with Claude Code from OpenSpec specs; the Agent Trace Viewer is the creative centrepiece |
| Poster | Sections: problem, approach (C4 container diagram), agent loop, tools, guardrails with/without table, evaluation results with intervals, data protection, business value, references |
| GitHub repo organized | Layout in §10.4; README links architecture, specs, skills, demo |
| Kanban board | One card per OpenSpec change (22), columns Backlog / Spec / In progress / Verify / Done, labels by deliverable D1–D5 |
| Research paper | Dedicated poster panel: claim, method, how it shaped one design decision |
| References cited properly | `REFERENCES.md` in APA 7 (below) |
| Problem, rationale, approach | §1 and the control architecture |
| Business opportunities / challenges | Coverage × minutes saved; risks from §8.4 and the exit path |
| Non-technical explanation | Clerk / calculator / supervisor metaphor; diagrams before code |
| Judges learn about AI | Ablation results; telemetry → experience (atlas) |
| Creativity | Atlas-driven architecture; synthetic adversarial carrier notes |
| Team collaboration | Rotating speakers; each member owns OpenSpec changes visible on the board |

## 10.4 Repository layout (target)

```
README.md                 problem, quickstart on synthetic data, links
REFERENCES.md             APA citations
architecture/             C4 DSL, docs, ADRs, exports
openspec/                 changes and archived specs
skills/                   itemizer-weekly-review/, itemizer-analyst/, itemizer-dev/
src/itemizer/             core, config, registry, ingest, router, classify, agent_tools,
                          guardrails, output, telemetry, review, kpi, dashboard, improve,
                          synth, ui, cli
config/                   schema, core, env, carriers
taxonomy/  metrics/       versioned definitions
data/synthetic/           published SYNTH and ADV sets (no PPG data in Git)
demo/                     code demo script, demo walkthrough
tests/
```

## 10.5 References (APA 7)

- Baldwin, C. Y., & Clark, K. B. (2006). Modularity in the design of complex engineering systems. In D. Braha, A. A. Minai, & Y. Bar-Yam (Eds.), *Complex engineered systems* (pp. 175–205). Springer.
- Duncan, W. R. (1994, December). Scoping out a scope statement. *PM Network*. Project Management Institute.
- Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection. In *Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security* (pp. 79–90). ACM.
- Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration of modern neural networks. In *Proceedings of the 34th International Conference on Machine Learning* (pp. 1321–1330). PMLR.
- Jordon, J., Szpruch, L., Houssiau, F., Bottarelli, M., Cherubin, G., Maple, C., Cohen, S. N., & Weller, A. (2022). *Synthetic data: What, why and how?* arXiv. https://arxiv.org/abs/2205.03257
- Rao, A. S., & DeSantis, [initial]. (2026). *The real AI* [Course text, 94-804 AI Strategy, Carnegie Mellon University]. *(Complete author initial and publisher from the syllabus.)*
- Sculley, D., Holt, G., Golovin, D., Davydov, E., Phillips, T., Ebner, D., Chaudhary, V., Young, M., Crespo, J.-F., & Dennison, D. (2015). Hidden technical debt in machine learning systems. In *Advances in Neural Information Processing Systems 28* (pp. 2503–2511).
- Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language models. In *International Conference on Learning Representations*.
- U.S. Food and Drug Administration. (2024). *Marketing submission recommendations for a predetermined change control plan for artificial intelligence-enabled device software functions* [Guidance].
- **Required course paper:** *to be added.*
