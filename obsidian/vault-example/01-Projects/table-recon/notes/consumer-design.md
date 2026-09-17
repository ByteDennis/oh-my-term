---
title: "Consumer design (Databricks job)"
date: 2026-09-11
type: note
project: table-recon
tags: [note, consumer]
---

# Consumer design

```
recon s3-drain --s3 s3://example-work/recon/v1 --run-id <id|latest> \
               --workers 8 --idle-timeout 900 --prefetch-depth 3
```

## Why a single coordinator with a thread pool

| Option | Verdict |
|---|---|
| one Databricks job run per unit | no: 30-60 s overhead per run, plus cluster churn |
| a Delta `work_queue` table with workers racing on `MERGE` | no: concurrent MERGE throws `ConcurrentAppendException`, needing partition isolation and retries; not worth the complexity |
| **one long-running job, a coordinator on the driver, N worker threads** | **recommended** |

## The drain loop

```python
while True:
    poll_manifests()          # newly cleared pairs -> append to class B backlog
    poll_index()              # incremental list of _INDEX/, StartAfter=last_seq
    a = queue_a.pop()         # left unit arrived AND right stats for that window ready
    if a: run(compare, a); continue
    b = next_prefetch()       # next unfetched window in manifest order
    if b: run(fetch_right_and_stat, b); continue
    if manifests_closed() and all_done(): break
    if stale_heartbeat(): abort_with_partial_report()
    backoff_sleep()           # 1 -> 2 -> 4 ... capped at 30s
```

Right-side stats are computed **per window**, so one fetch feeds every column in
that window.

> **The single easiest line in this system to get wrong.** The `WHERE` clause for
> the right-side fetch must use the manifest's partition list **with its holes**,
> built from the same contiguous-run intervals. Using the bucket's first and last
> day instead silently pulls back the partitions stage 1 excluded, and the compare
> results come out unequal for reasons nobody can trace. This needs a unit test
> covering a hole in the middle, holes at both ends, and a window reduced to a
> single day.

`--prefetch-depth` (default 3) caps how far class B may run ahead of the producer.
Without it the cluster burns through every right-side scan in the first ten minutes
and then genuinely idles, and a mid-run producer failure wastes all of it.

## Fixed-N fallback

With `--sample 500` the right side depends on a key list chosen by the left, so
class B stops being independent. The producer then inserts a **phase 1.5** after
stage 1: one narrow key-only query per passing window, packaged into
`manifest/{pair}.keys.json` and uploaded once. Class B is fully visible again.
Phase 1.5 costs roughly one narrow query per window, usually less than the first
window's data pull, so it stays off the critical path.

## Exit conditions

Normal: `manifest/_CLOSED` exists **and** `|results| + |dead| == expected_units`.

Two safety nets:

- `_HEARTBEAT` older than `3 x interval` means the producer died. Emit a partial
  report and exit non-zero.
- `--idle-timeout` (default 15 min) with no new units and no class B work left.
  This stops the cluster burning money when the producer dies and even the
  heartbeat stops.

## Retries and dead letters

Each unit carries `attempts`. On failure it goes back to the tail of the queue
with exponential backoff. Past 3 attempts it is written to `dead/{unit_id}.json`
with the traceback, counted as accounted-for, and no longer blocks exit. Results
are keyed by `unit_id`, so the whole thing is idempotent.

One dead unit never stalls a run. The report says plainly that the column was not
compared, rather than pretending it passed.

## Sizing

With producer rate lambda units/min, per-worker service rate mu, and W workers:

- `W*mu > lambda`: the consumer idles in steady state and fills gaps with class B
  prefetch. Once prefetch is exhausted it genuinely idles. The correct response is
  **fewer workers**, not a bigger queue.
- `W*mu < lambda`: the consumer is the bottleneck and the producer hits `--wip`.
  Add workers; autoscale does this automatically.
- Ideal `W = ceil(lambda/mu)`, plus one for the tail.

Comparing two stat rows takes milliseconds, so class A is never the bottleneck.
The right-side scan in class B is. In practice `W = ceil(t_scan_right /
t_pull_left)`, which is usually 2 to 4. **Start at W=4 and let `--wip` and
`idle_ratio` tell you which way to move.**

## Related

- [[architecture-overview]]
- [[monitoring-and-failure-modes]]
