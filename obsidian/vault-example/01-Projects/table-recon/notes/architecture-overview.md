---
title: "Split pipeline architecture"
date: 2026-09-08
type: note
project: table-recon
tags: [note, architecture]
---

# Split pipeline: local sampling -> S3 -> Databricks

Splitting today's single-process `compare-csv` loop (one machine pulls both
sides, DuckDB computes stats, compares) into two halves that never block each
other.

- **Producer (local PC)** handles the **left side**, which can be csv, sas,
  hadoop, oracle or athena. It keeps the existing hash-bucket sampling and pushes
  results plus metadata to S3 at `(pair, partition, column)` granularity.
- **Consumer (long-running Databricks job)** reads manifests and data from S3,
  fetches the **right side** (always Databricks), computes stats, compares, and
  writes the report.

Two hard constraints run through everything:

1. **Two stages, and stage 1 is a barrier.** Stage 1 compares only record counts
   per partition. Only partitions where counts match are allowed into stage 2. If
   the counts already differ, sampled column stats will differ too, and that is
   noise rather than a finding.
2. **The two sides are asymmetric.** Left is pluggable. Right is always
   Databricks.

## The barrier does not idle the cluster

That is the obvious objection, and it is wrong for three reasons.

**Stage 1 does not need the big cluster.** On the right side it issues one
`SELECT dt, COUNT(*) GROUP BY dt`, which a serverless SQL warehouse handles in
seconds and bills per query. The job cluster is for stage 2. Nothing idles during
stage 1 because nothing has started.

**The barrier is per pair, not global.** Pair A can enter stage 2 while pair B is
still counting. This is why the manifest has to be incremental, one
`manifest/{pair}.json` at a time, rather than one file written at the end. See
[[2026-09-08-two-stage-barrier]].

**There are always two kinds of work in stage 2.** Deterministic reject sampling
(`hash32(normalized key) < rate x 2^32`) makes the two sides independent: which
rows the right side needs depends only on `key_plan + threshold +
matched_partitions` from the manifest, never on the left-side files.

| Work class | Depends on | Supply |
|---|---|---|
| **A. Compare** (dependent) | left unit file + right stats for that partition | rate-limited by the producer |
| **B. Fetch right + stat** (independent) | only the pair's manifest | fully visible the moment that pair clears the barrier |

The scheduling rule is one sentence: **do A first; when A is empty, speculatively
do B.** B is a backlog that fills up as soon as any pair clears the barrier, so
workers never idle.

This also fixes when to start the cluster: **the moment the first pair clears
stage 1.** The 3-7 minute cold start overlaps with the remaining pairs' stage 1
and with the first window's left-side pull.

> Exception: in fixed-N IN-list mode (`--sample 500`) the right side depends on a
> key list chosen by the left side, so class B is no longer independent. Default
> to fraction sampling (`--sample 0.005`) in the split architecture, because it
> needs zero coordination. See [[consumer-design]].

## Three levels of granularity

Do not mix these up.

| Level | Meaning | Used for |
|---|---|---|
| **partition** | the reconciliation key both sides recognise, a normalised date | **stage 1 granularity** |
| **window** | `bucket_date(partition, vintage)`, the unit of one scan | stage 2 scan granularity |
| **unit** | `(pair, window, column)` | stage 2 delivery and compare granularity |

**Stage 1 must reconcile at partition level, not window level.** Otherwise one day
short by 3 rows knocks out the whole month, or the monthly total coincidentally
matches and hides it. Stage 2 windows are then built only from partitions that
cleared the barrier, which means windows have holes in them.

File-based left sides (csv, sas) have no SQL partitions, only files, so stage 1
also emits a `partition_map` from date to file list. It is used to sum counts per
partition, and to read only the relevant files when stage 2 pulls a window.

## Verdicts

| verdict | Meaning | Enters stage 2 |
|---|---|---|
| `match` | counts equal on both sides | yes |
| `count_diff` | present on both sides, counts differ | no, it is already a finding |
| `left_only` | right side has no such partition | no |
| `right_only` | left side has no such partition | no |

Gate policy is a flag:

- `--gate auto` (default): each pair enters stage 2 as soon as it clears.
- `--gate manual`: run all of stage 1, write the report, then stop and wait for a
  human. Right for onboarding a new table, or when `count_diff` looks high.
- `--gate ratio:0.3`: hold a pair back if `count_diff + single_side` exceeds 30%
  of its partitions. That data has a systemic problem and stage 2 would be waste.
  Other pairs proceed normally.

## Related

- [[s3-layout-and-commit-protocol]]
- [[producer-design]]
- [[consumer-design]]
- [[run-walkthrough]]
