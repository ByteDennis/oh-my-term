---
title: "Walkthrough: one pair, start to finish"
date: 2026-09-12
type: note
project: table-recon
tags: [note, walkthrough]
---

# Walkthrough: one pair, start to finish

Three actors and two buckets.

| Actor | Where | Job |
|---|---|---|
| Producer | local PC | left side: count, pull, stat, upload |
| Consumer | Databricks job | right side: fetch, stat, compare |
| Buckets | S3 | `example-work` for the run, `example-report` for results |

The example: pair `acct`, left side Oracle, right side `main.core.account_daily`,
two months of data, monthly vintage, 30 value columns, 0.5% sampling.

```bash
recon s3-stage1 project.db --config pairs.json \
      --s3 s3://example-work/recon/v1 --gate auto --kickstart
```

## Timeline

| Time | What happens |
|---|---|
| `00:00` | generate `run_id`, begin |
| `00:00 - 00:02` | Databricks preflight: auth, warehouse, table, columns, date type |
| `00:02 - 00:14` | count the right side, one `GROUP BY`, 12 seconds |
| `00:14 - 02:10` | count the left side, about 2 minutes on Oracle |
| `02:10 - 02:11` | reconcile; **this is already the first deliverable** |
| `02:11` | kickstart: `POST /api/2.2/jobs/run-now` with `idempotency_token = run_id` |
| `02:13 - 05:40` | left side pulls the June window while the cluster boots |
| `06:10` | cluster is up and immediately has work: it reads the manifest and fills the class B backlog |
| `06:10 - 09:10` | right side fetches June |
| `09:10` | June's 30 units compare in an instant |
| `06:20 - 09:50` | meanwhile the left side is pulling July |
| `09:15 - 12:20` | right side fetches July, then compares |
| `12:25 - 12:50` | finalize: analysis, report, upload to the report bucket |

Total, one pair, two months, 30 columns: about 13 minutes.

## Why the reconcile step at 02:10 matters

"Which partitions have different record counts" is a conclusion the business
wants on its own. It is not an intermediate state feeding stage 2. It gets its
own report and its own sign-off. In this run: 58 match, 2 count_diff, 1 left_only.
Those 3 partitions never enter stage 2, and every byte of their download, scan and
compute is saved.

## Why kickstart fires at 02:11 and not at 00:00

Two things would go wrong otherwise. If preflight fails, we would have started a
cluster for nothing. And starting later would waste the overlap: those four
minutes of cluster boot are spent doing useful left-side work.

`idempotency_token = run_id` means a producer retry or a flaky network cannot
start a second job run. It is the only lock in the entire design.

## What the cluster does the second it wakes up

It reads `manifest/acct.json` and immediately has the entire class B backlog:
every right-side window it will ever need, visible at once, with no dependency on
the left side. That is the property that makes the barrier free.

## Related

- [[architecture-overview]]
- [[scheduling-five-pairs]]
- [[monitoring-and-failure-modes]]
