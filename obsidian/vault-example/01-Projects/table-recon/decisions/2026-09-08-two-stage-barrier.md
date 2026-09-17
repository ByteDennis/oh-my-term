---
title: "Two stages with a record-count barrier"
date: 2026-09-08
type: decision
status: decided
project: table-recon
tags: [decision]
---

## Context

The current `compare-csv` loop samples both sides and compares column statistics
in one pass. On tables where the two sides do not even hold the same number of
rows, those statistics are guaranteed to differ, and we spend the full download
and scan cost to produce a result nobody can act on.

The question was whether to gate column comparison behind a record-count check,
and the objection was that a barrier would leave the Databricks cluster idle.

## Options

| Option | Pros | Cons |
|---|---|---|
| Single stage, compare everything | simplest; no coordination | wasted cost on partitions that can never match; findings buried in noise |
| Two stages, **global** barrier | clean mental model | every pair waits for the slowest pair; cluster genuinely idles |
| Two stages, **per-pair** barrier | no idling, see below | manifest must be incremental, more moving parts |

## Decision

Two stages, with the barrier applied **per pair**, and the cluster started the
moment the first pair clears it.

## Why

The idling objection does not survive contact with the details:

- Stage 1 runs on a serverless SQL warehouse, so during the barrier there is no
  cluster to idle. It has not been started yet.
- The barrier is per pair, so pair A enters stage 2 while pair B is still counting.
- Within stage 2 there is always independent work available. Deterministic reject
  sampling means the right side's row selection depends only on the manifest, so
  the entire right-side fetch backlog becomes visible the instant a pair clears.

There is a second benefit beyond correctness: every partition excluded at the
barrier saves its left-side download, right-side scan and compute. The higher the
`count_diff` rate, the more we save.

## Consequences

- The manifest must be written incrementally, one file per pair. A single combined
  file would delay the kickstart until the slowest pair cleared.
- Stage 1 timing lands directly on the end-to-end critical path, so
  `stage1/{pair}.json` must carry a `timing` block or we will have no way to
  optimise it later.
- Stage 1's output becomes a deliverable in its own right, with its own report and
  sign-off.

See [[architecture-overview]].
