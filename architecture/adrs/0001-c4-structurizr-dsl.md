# 1. Architecture as code with C4 and Structurizr DSL

Date: 2026-10-31

## Status

Accepted

## Context

The slide diagram (Architecture Diagram - i2ai project.pptx) captures the blocks but not their contracts, ownership or versioning. D5 requires a reader outside the team to rerun the tool.

## Decision

Model the system in one Structurizr DSL workspace (`architecture/workspace.dsl`) with context, container, component, dynamic and deployment views; keep design docs and ADRs next to it. OpenSpec changes reference container and component names from this workspace.

## Consequences

Diagrams are diffable and reviewed with code. Names in the DSL are the shared vocabulary for specs.
