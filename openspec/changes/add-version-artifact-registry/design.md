## Context

C4 container **Version & Artifact Registry**. Placement: **common core**. Position: **controlled**.

## Goals / Non-Goals

**Goals:** immutable, hash-identified artifacts; lineage from any KPI back to its inputs; restore everything a run needs.

**Non-Goals:** a general data lake; DVC/MLflow adoption (can wrap later behind the same API).

## Decisions

- **CAS layout** `cas/<first2>/<sha256>` with a sidecar JSON (`kind`, `created_at`, `created_by`, `parents`, `schema_version`, `confidential`). Alternative: DVC. Rejected for the prototype: extra tooling for four people; the API keeps the option open.
- **Artifact kinds:** `raw_export`, `snapshot`, `masking_map`, `taxonomy`, `eval_set`, `prompt`, `fewshot_set`, `lexicon`, `calibration_map`, `run_manifest`, `predictions`, `output_workbook`, `review_workbook`, `replay_pack`, `metric_definitions`, `weights`, `price_table`, `kpi_snapshot`, `published_change`.
- **Git-tagged kinds** are registered as `{tag, commit, path, content_hash}` so the CAS also holds their bytes; reruns never depend on the Git remote.
- **Sealed artifacts:** `eval_set` with `sealed=true` is readable only through an access-checked API that admits the KPI Calculator role.
- **Retention:** deletion writes a tombstone with reason and approver; bytes removed, hash and lineage kept.
- **Response cache is not here.** It belongs to the Router and is keyed, not versioned.

## Risks / Trade-offs

- [Disk growth from repeated snapshots] → snapshots deduplicate by hash; 1,500-row exports are small.
- [Confidential data in CAS] → CAS root must be on the encrypted volume; registry refuses a `data_root` outside it.

## Open Questions

- Client retention instruction at project end (delete vs hand over).
