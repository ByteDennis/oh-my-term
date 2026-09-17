---
title: "Findings and errors are separate channels"
date: 2026-09-13
type: decision
status: decided
project: table-recon
tags: [decision, operations]
---

## Context

A run produces two very different kinds of bad news: "these two partitions have
different record counts" and "the service principal's token expired". Early drafts
of the status output put both in the same `errors` list.

## Decision

Two disjoint code namespaces. `F_*` codes are findings: they go in the report and
never alert. `E_*` codes are errors: they alert and have a named owner.

## Why

Findings are the product. A run that discovers seven partitions with unequal
counts has done its job perfectly. If that raises an alert, then the alert fires
every single day, and within two weeks nobody reads it. Worse, when something
genuinely breaks, the one message that matters is buried under hundreds of
routine differences.

## Consequences

- Alert rules only ever read `errors`, never `findings`.
- Every `E_*` code carries an owner in the table so the alert is actionable:
  ops, data engineering, a config change, or a business decision.
- `E_STAT_ENGINE` is called out separately. If local DuckDB and cloud Spark
  compute different statistics for the same data, every conclusion the system has
  produced is suspect. Detection is a per-run spot check: compute one window's
  stats for the same side in both engines and compare.

See [[monitoring-and-failure-modes]].
