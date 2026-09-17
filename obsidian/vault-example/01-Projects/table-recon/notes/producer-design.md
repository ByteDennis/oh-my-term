---
title: "Producer design (local PC)"
date: 2026-09-10
type: note
project: table-recon
tags: [note, producer]
---

# Producer design

```
recon s3-stage1 {project.db} --config pairs.json --s3 s3://example-work/recon/v1 \
                [--gate auto|manual|ratio:0.3] [--kickstart] [--pair-workers 4]

recon s3-push   {project.db} --config pairs.json --s3 ... --run-id <id> \
                [--sample 0.005] [--vintage month] [--upload-raw] \
                [--wip 200] [--workers 4]
```

Two subcommands rather than one with a `--stage` flag, because their failure
semantics, retry strategies and permissions all differ. Stage 1 needs only read
access to a SQL warehouse; stage 2 additionally needs permission to trigger a job.
Stage 1 failing should stop everything; stage 2 failing can still deliver
partially. With `--gate auto`, `s3-stage1` chains into `s3-push` itself.

## Stage 1 ordering is itself the design

```
1. Databricks preflight        first, because it is the most likely to fail and the cheapest
2. right-side partition counts  all pairs in parallel against one warehouse
3. left-side partition counts   grouped by source, limited by each source's session budget
4. reconcile + gate + write stage1/{pair}.json and manifest/{pair}.json
```

**Preflight goes first.** If Databricks is unreachable we want to fail before
touching a single thing on the left, not after finishing a full Oracle scan only
to discover there is nothing to compare against.

| Check | How | Abort on failure |
|---|---|---|
| auth | OAuth M2M token, `current_user()` | yes |
| warehouse reachable | `SELECT 1` | yes |
| catalog/schema/table exists | `DESCRIBE TABLE EXTENDED` | yes |
| columns exist and map | compare against `col_map` | yes |
| `date_col` exists, `date_type` matches | sample `MIN/MAX(date_col)` | yes |
| job trigger permission | `GET /api/2.2/jobs/get` | warn only, stage 1 does not need it |

**Right before left.** The right side is always one cheap query that settles
within seconds which partitions the right side does not have at all. The left-side
count can then carry a `date IN (partitions the right side has)` bound, which
prunes partitions on Oracle and Hive and avoids scanning data destined to be
`left_only` anyway.

## Stage 2 is a three-stage pipeline, fully overlapped

```
[plan] -> [pull] xW_pull -> [stat] xW_stat -> [upload] xW_up -> S3
manifest   left scan        DuckDB            split by column + PUT
           slow, I/O        CPU               small, network
```

Today `_run_pair` is strictly serial, one bucket at a time through
`pull -> extract -> compare`. Split apart, these become three stages joined by
bounded queues. `W_pull` is the real bottleneck because it is capped by the source
database's session budget (2 to 4 for Oracle). Upload is negligible: units are
kilobytes, 30 columns across 4 threads is about 0.3 seconds.

**Scan by window, deliver by unit.** A window is still pulled with exactly one
query covering all value columns. Splitting into per-column unit files happens
locally at upload time, which is free. One source scan therefore feeds about 30
cloud slots, which is what keeps the producer comfortably ahead of the consumer.

## Dispatch order: round-robin, never depth-first

Today the loop is `for pair: for bucket in sorted(buckets)`. After the split it
**must** rotate across pairs:

```
(pairA, 2026-01) (pairB, 2026-01) (pairC, 2026-01) (pairA, 2026-02) ...
```

The consumer fetches the right side per `(pair, window)`, and each pair hits a
different Databricks table. Depth-first means the ready queue holds units for one
table for long stretches, all concurrency piles onto that single table, and
effective parallelism collapses to one. See
[[2026-09-10-round-robin-dispatch]].

## Backpressure

No rate limiting, just a ceiling:

```
ready_unclaimed = |_INDEX| - |results| - |dead|   # two list counts, cached 30s
while ready_unclaimed > --wip: sleep 15s
```

`--wip` defaults to 200. Hitting it means the consumer is the bottleneck, so the
right response is to add consumer workers, not to throttle the producer.

## Related

- [[architecture-overview]]
- [[consumer-design]]
- [[scheduling-five-pairs]]
