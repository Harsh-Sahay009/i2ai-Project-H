# 5. KPIs are computed only from immutable versioned inputs

Date: 2026-10-31

## Status

Accepted

## Context

Accuracy must be weighted back to the real mix, reported with sample size (D5), and compared across runs. Error (e) is reproducibility.

## Decision

A KPI snapshot is a pure function of run manifest, evaluation set version, metric definition version, weights version, price table version and code SHA. Populations TEST, DEV, FRESH and PROD are never mixed. Snapshots are append-only; the dashboard only renders.

## Consequences

Any number in the report can be recomputed. Changing a metric definition is a visible version bump.
