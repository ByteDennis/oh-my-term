---
title: "Outputs and who reads them"
date: 2026-09-15
type: note
project: table-recon
tags: [note, reporting]
---

# Outputs and who reads them

## The report bucket

```
s3://example-report/
  latest/
    pointer.json                    the dashboard's only entry point
  history/
    20260917T1402Z-a3f9c1/
      summary.json                  machine-readable: status, finding counts, timing
      run_report.html               all five pairs on one page
      acct/
        index.html                  per-pair detail, self-contained and offline
        row_diff.csv                stage 1: one row per partition
        col_diff.csv                stage 2: one row per column per window
      txn/ ...
    20260916T1402Z-7b21de/          yesterday, immutable
```

`summary.json` is the run in one object:

```jsonc
{
  "run_id": "20260917T1402Z-a3f9c1",
  "status": "DONE",
  "elapsed_s": 1180,
  "pairs": 5,
  "findings": { "row_count_diff": 7, "partition_missing": 2, "col_stat_diff": 11 },
  "errors": [],
  "cost_estimate_usd": 1.42,
  "base": "history/20260917T1402Z-a3f9c1/"
}
```

## Three audiences, three paths

| Who | How they look | What they read |
|---|---|---|
| Business and management | Databricks AI/BI dashboard | three Delta tables in Unity Catalog |
| Technical team | open `index.html`, or download the csv | report bucket, `latest/pointer.json` -> `base` |
| Alerting | scheduled daily read | `findings` and `errors` in `latest/pointer.json` |

**Why does the dashboard read Delta tables rather than S3?** Because the questions
it answers are cross-run: how a metric trended over 30 days, which table has the
most problems. That is SQL's job. Stitching 30 JSON files together from S3 is
making work for yourself.

**Then who is the report bucket for?** Everyone outside Databricks: email
attachments, a static site, another team's tooling. They have no account in the
workspace but they do have read access to a bucket.

> Only ever overwrite `pointer.json` atomically. Updating the files under
> `latest/` one at a time lets the dashboard read a half-old, half-new run.

## Reading a run

```
run 20260917T1402Z-a3f9c1   DONE   19m40s   $1.42

Stage 1 - record count reconciliation
  acct           58 match /  2 count_diff /  1 left_only
  txn            61 match /  0            /  0
  customer       59 match /  2 count_diff /  0
  product_ref    61 match /  0            /  0
  balance_hist   60 match /  3 count_diff /  1 right_only
  -> 7 partitions with unequal counts, 2 missing on one side

Stage 2 - sampled column stats, only on partitions that matched above
  acct       2026-06  ACCT_BAL     n_unique  48,221 vs 48,218
             2026-06  RISK_SCORE   hash_sum  mismatch
             2026-07  RISK_SCORE   hash_sum  mismatch
  customer   2026-07  CUST_SEG     n_missing  1,204 vs 0
  -> 11 (column x window) stats unequal

Next: for each line above, run the full-population confirmation SQL the report
provides.
```

That last line is the point. **Sampling establishes that a problem exists; it does
not draw the conclusion.** Every finding ships with a ready-made full-population
confirmation query that the technical team can run on their side. So far, every
difference sampling flagged has been confirmed at full scale.

## Related

- [[monitoring-and-failure-modes]]
- [[quick-reference]]
