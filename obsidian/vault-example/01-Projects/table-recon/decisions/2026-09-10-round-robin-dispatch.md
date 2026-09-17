---
title: "Dispatch stage 2 units round-robin across pairs"
date: 2026-09-10
type: decision
status: decided
project: table-recon
tags: [decision]
---

## Context

The existing loop is `for pair: for bucket in sorted(buckets)`, which finishes one
table completely before starting the next. Carried into the split architecture,
that ordering decides what the ready queue looks like.

## Decision

Rotate across pairs when dispatching units:

```
(pairA, 2026-01) (pairB, 2026-01) (pairC, 2026-01) (pairA, 2026-02) ...
```

## Why

The consumer fetches the right side per `(pair, window)`, and each pair maps to a
different Databricks table. Depth-first dispatch means the ready queue contains
units for a single table for long stretches, all worker concurrency piles onto that
one table, and effective parallelism collapses towards one.

Rotating means adjacent units land on different right-side tables, so the workers
actually spread out.

## Consequences

- `_run_pair`'s serial bucket loop has to be extracted into a reusable
  `iter_windows(pairs)` generator that supports rotation.
- Stage 1 sorts the opposite way, smallest pair first, because its goal is to get
  *someone* through the barrier early enough to start the cluster. Stage 2 sorts
  largest first, because its goal is to finish. The two stages sorting in opposite
  directions looks wrong at a glance and is correct.

See [[scheduling-five-pairs]].
