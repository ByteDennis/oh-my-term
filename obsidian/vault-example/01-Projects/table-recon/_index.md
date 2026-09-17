---
title: "table-recon"
type: project
status: active
started: 2026-08-20
tags: [project]
---

# table-recon

Reconciles tables between on-prem sources and Databricks. Stage 1 compares record
counts per partition; stage 2 compares sampled column statistics on the partitions
where counts agreed.

Currently being split from a single-process loop into a producer on a local PC and
a long-running consumer job on Databricks, connected through S3.

## Current focus

- Phase D: consumer running locally against a csv right side, output byte-identical
  to today's `compare-csv`. This is the correctness anchor and nothing connects to
  real Databricks until it passes.
- Instrumenting `timing` in stage 1, because the barrier sits on the critical path.

## Open questions

- Does compliance allow `--upload-raw`? Detail rows and aggregate statistics are
  different review categories, and the answer decides whether cloud-side drill-down
  is possible at all.
- Oracle session budget is 2. Is that negotiable for the month-end window, or do we
  design around it permanently?

## Key decisions

- [[2026-09-08-two-stage-barrier]] - why the barrier does not idle the cluster
- [[2026-09-09-exact-counts-only]] - never gate on catalog statistics
- [[2026-09-10-round-robin-dispatch]] - rotate units across pairs
- [[2026-09-13-findings-vs-errors]] - alerting only on errors

## Notes

- [[architecture-overview]] - start here
- [[s3-layout-and-commit-protocol]]
- [[producer-design]] / [[consumer-design]]
- [[run-walkthrough]] - one pair end to end
- [[scheduling-five-pairs]] - how the queue behaves with five tables
- [[monitoring-and-failure-modes]]
- [[outputs-and-consumers]]
- [[quick-reference]]

## Known risks

1. The barrier adds directly to end-to-end time. If left-side counting is slow
   (large Oracle single-column `GROUP BY`, sas needing file reads), the barrier
   becomes the new bottleneck.
2. The `WHERE` clause for windows with holes is the single most error-prone line.
   Needs unit tests for a hole in the middle, holes at both ends, and a window
   reduced to one day.
3. DuckDB and Spark stat semantics must agree. `n_unique` must be an exact
   `COUNT(DISTINCT)`, `hash_sum` must use the verified expression.
4. The producer is a single point of failure. Heartbeat plus resume means a restart
   continues, but there is no HA.
