# 9. Synthetic data for every public artifact

Date: 2026-10-31

## Status

Accepted

## Context

The GitHub repo, poster and live demos are public or shown to judges, and PPG data must stay on team-controlled accounts.

## Decision

A Synthetic Data Generator produces SYNTH (realistic) and ADV (adversarial) sets from aggregate statistics only, with gold labels known by construction. A set is published only after fidelity, privacy, validity and utility checks. CI blocks commits that resemble real exports.

## Consequences

Demos are safe to show. Synthetic numbers are always labelled synthetic and never replace TEST, DEV or FRESH results.
