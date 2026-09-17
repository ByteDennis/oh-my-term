---
title: "Monitoring and failure modes"
date: 2026-09-13
type: note
project: table-recon
tags: [note, operations]
---

# Monitoring and failure modes

## One place to look: `_STATUS.json`

Whoever is working overwrites it every 15 seconds.

```jsonc
{
  "run_id": "20260917T1402Z-a3f9c1",
  "updated_at": "2026-09-17T14:08:32Z",
  "producer": { "alive": true, "heartbeat_age_s": 12 },
  "consumer": { "alive": true, "workers": 4, "idle_ratio": 0.03 },
  "pairs": {
    "acct": {
      "state": "DRAINING",
      "stage1": { "match": 58, "count_diff": 2, "left_only": 1, "took_s": 131 },
      "stage2": { "units_total": 60, "pushed": 60, "compared": 30, "dead": 0 },
      "current": "fetch_right(2026-07)",
      "errors": []
    }
  },
  "overall": { "state": "DRAINING", "pct": 0.50, "eta_s": 190 }
}
```

## Every pair is always in a known state

There is no "not sure where it is".

```
NEW
 └> PREFLIGHT_OK
     └> COUNTING_RIGHT
         └> COUNTING_LEFT
             └> RECONCILED
                 ├> GATE_BLOCKED    difference too large, terminal
                 └> GATE_PASSED
                     └> PUSHING
                         └> PUSH_DONE
                             └> DRAINING
                                 ├> DONE
                                 ├> PARTIAL    some dead units, report still produced
                                 └> FAILED
```

## Findings and errors are different things

This is the most important rule in the monitoring design.

> **Different record counts and different column stats are the product's output,
> not a system malfunction.**

Conflating them has two consequences: alerts fire every day until nobody reads
them, and a genuine failure gets buried under hundreds of differences.

**Class A, findings. No alert, goes in the report.**

| Code | Stage | Meaning |
|---|---|---|
| `F_COUNT_DIFF` | stage 1 | counts differ for a partition |
| `F_LEFT_ONLY` | stage 1 | the right side has no such partition |
| `F_RIGHT_ONLY` | stage 1 | the left side has no such partition |
| `F_STAT_DIFF` | stage 2 | a column's stats differ |

**Class B, errors. Alert, someone has to fix it.**

| Code | Stage | Meaning | Owner |
|---|---|---|---|
| `E_AUTH` | preflight | service principal expired or lacks permission | ops |
| `E_NO_TABLE` | preflight | right-side table missing or renamed | data engineering |
| `E_COL_MISSING` | preflight | a `col_map` column is absent on the right | config |
| `E_DATE_TYPE` | preflight | `date_type` does not match the real format | config |
| `E_LEFT_CONN` | stage 1 | source database or share unreachable | ops |
| `E_LEFT_SLOW` | stage 1 | left-side count timed out | add bounds or an index |
| `E_GATE_BLOCKED` | stage 1 | difference ratio over threshold | business call |
| `E_PULL_FAIL` | stage 2 | left-side download failed after 3 retries | read the traceback |
| `E_RIGHT_SCAN` | stage 2 | Databricks scan failed | read the job log |
| `E_STAT_ENGINE` | stage 2 | DuckDB and Spark disagree on stat semantics | **a code bug, the most serious one** |
| `E_PRODUCER_DEAD` | any | heartbeat stale for over 3 minutes | ops |
| `E_UNITS_MISSING` | finalize | `_CLOSED` said 60, only 57 arrived | check `dead/` |

`E_STAT_ENGINE` deserves special handling. If local DuckDB and cloud Spark compute
different statistics for the same data, then **every conclusion the system has ever
produced is suspect**. It is not an ordinary error; it means stop and read code.
Detection: every run, pick one window, compute the same side's stats in both
engines, and raise this code if they disagree.

## What failures look like

**Preflight fails, the best case, because nothing was wasted:**

```
[preflight] acct
  auth .................... OK
  warehouse ............... OK
  main.core.account_daily . FAIL
      E_NO_TABLE: [TABLE_OR_VIEW_NOT_FOUND] `main`.`core`.`account_daily`
      hint: renamed? try SHOW TABLES IN main.core
[recon] ABORT before touching the left side. Source untouched, no cluster started.
```

**The producer dies mid-run:**

```
[drain] heartbeat stale: 214s since last _HEARTBEAT (limit 180s)
[drain] E_PRODUCER_DEAD -> finalize PARTIAL with what we have
[drain] 30/60 units compared; 2026-07 never arrived
[finalize] PARTIAL -> report bucket (summary.json marks status=PARTIAL)
```

It does not simply crash. The 30 units already compared still produce a report,
marked `PARTIAL`. Once the network is back, rerunning the same command with the
same `run_id` skips already-pushed units via `_INDEX` and resumes from July.

**One unit fails repeatedly:**

```
[drain] unit acct__2026-07__RISK_SCORE attempt 3/3 failed
        E_RIGHT_SCAN: [DELTA_FILE_NOT_FOUND] ... VACUUM during scan?
[drain] -> dead/acct__2026-07__RISK_SCORE.json (traceback inside)
[drain] progress 59/60 + 1 dead = 60 accounted -> finalize PARTIAL
```

## Related

- [[consumer-design]]
- [[outputs-and-consumers]]
