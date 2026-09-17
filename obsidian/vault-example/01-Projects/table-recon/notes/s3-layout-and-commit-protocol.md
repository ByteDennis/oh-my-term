---
title: "S3 layout and commit protocol"
date: 2026-09-09
type: note
project: table-recon
tags: [note, storage]
---

# S3 layout and commit protocol

```
s3://example-work/recon/v1/
  runs/{run_id}/
    _PREFLIGHT.json                      Databricks health check result
    _STATUS.json                         what is happening right now
    _HEARTBEAT                           producer overwrites every 60s
    stage1/{pair}.json                   verdict for every partition
    stage1/_CLOSED                       all pairs finished stage 1
    manifest/{pair}.json                 incremental: appears on clearing the barrier
    manifest/_CLOSED                     {pairs: [...], expected_units: N}
    units/{pair}/{window}/{column}.json  payload B (stats)
    raw/{pair}/{window}/part-0000.parquet  payload A (optional, wide table)
    _INDEX/{seq:08d}-{unit_id}.json      monotonic "ready" pointer
    results/{unit_id}.json               consumer output
    dead/{unit_id}.json                  exceeded max_attempts
```

## The commit order is the whole protocol

**Write the data object first, then write the pointer object.** A single S3 PUT
is atomic, and since December 2020 LIST is strongly consistent. Because the
consumer only ever scans `_INDEX/` and `manifest/`, it cannot observe a
half-written file.

`_INDEX` entries are named with a zero-padded increasing sequence number. The
consumer remembers the highest sequence it has seen and calls
`list_objects_v2(StartAfter=...)`, which makes listing incremental and independent
of how large the run has grown.

## stage1 and manifest are not the same thing

Do not merge them.

- `stage1/{pair}.json` holds the verdict for **every** partition, including the
  excluded ones, because that is a report a person reads.
- `manifest/{pair}.json` is the **execution plan** for stage 2 and contains only
  partitions that passed.

### stage1/{pair}.json

```jsonc
{
  "run_id": "20260917T1400Z-a3f9c1",
  "pair": "acct_oracle_vs_dbx",
  "left":  {"source": "oracle", "date_col": "RPT_DT", "count_method": "group_by"},
  "right": {"source": "databricks", "catalog": "main", "schema": "core",
            "table": "account_daily", "date_col": "rpt_dt",
            "date_type": "string_dash", "count_method": "group_by"},
  "date_synonyms": {"3000-01-01": "2026-07-01"},
  "bounds": {"from": "2026-06-01", "to": "2026-07-31"},
  "partitions": {
    "2026-06-01": {"left": 1234567, "right": 1234567, "verdict": "match"},
    "2026-06-02": {"left": 1234567, "right": 1234560, "verdict": "count_diff",
                   "delta": -7},
    "2026-06-03": {"left": 998,     "right": null,    "verdict": "left_only"}
  },
  "summary": {"match": 58, "count_diff": 2, "left_only": 1, "right_only": 0},
  "gate_decision": {"policy": "ratio:0.3", "passed": true, "excluded_ratio": 0.049},
  "timing": {"preflight_s": 1.2, "right_count_s": 8.4, "left_count_s": 41.0}
}
```

The `timing` block is not decoration. The barrier sits directly on the end-to-end
critical path, so without these numbers there is no way to know what to optimise
afterwards.

### manifest/{pair}.json

```jsonc
{
  "run_id": "...", "pair": "acct_oracle_vs_dbx",
  "sample": {"mode": "fraction", "rate": 0.005, "threshold": 21474836},
  "vintage": "month",
  "key_cols": ["ACCT_ID", "SUB_ID"],
  "key_plan": [{"pos": 0, "left_norm": "...", "right_norm": "..."}],
  "col_map": {"ACCT_BAL": "acct_bal"},
  "columns": ["ACCT_BAL", "..."],
  "windows": [
    {"bucket": "2026-06", "partitions": ["2026-06-01", "2026-06-04"],
     "n_left": 2469134},
    {"bucket": "2026-07", "partitions": ["..."]}
  ],
  "expected_units": 60
}
```

Note the `partitions` list inside a window: it has holes. That is the point.

`manifest/_CLOSED` carries the total `expected_units`, which is how the consumer
knows no further pairs are coming. **The producer must land every
`manifest/{pair}.json` before writing `_CLOSED`**, or the consumer packs up early.

## Resuming

- Stage 1: if `stage1/{pair}.json` already exists, skip that pair.
- Stage 2: list `_INDEX/` and skip unit ids already present.
- `--force` allocates a new `run_id`, which isolates everything naturally.

## Payload choice

| Option | Contents | Size per unit | Trade-off |
|---|---|---|---|
| **B (default)** | the stats row computed locally by DuckDB: `n_total / n_missing / n_unique / min / max / hash_sum` | ~1 KB | tiny, negligible S3 cost, the queue never stalls on I/O; requires stat semantics to match across engines |
| A | the raw sampled rows, one wide table per window | megabytes | both sides computed in the cloud from the same source; but moving detail rows off-prem is a compliance question |

Default to B. Add `--upload-raw` only to support cloud-side drill-down on
differing columns, and only when compliance allows it. When it does not, drill-down
still works through the existing single-column confirmation query against the
source.

## Cost notes

- `runs/` expires after 30 days, `raw/` after 7.
- Payload B is kilobyte JSON. 900 of them is about 1 MB.
- Payload A must be coalesced to one file per window. Per-column parquet is
  forbidden.
- Incremental listing costs roughly one `ListObjectsV2` per poll. A one-hour run
  polling every 2 seconds is about 1800 requests, or one cent.

## Related

- [[architecture-overview]]
- [[producer-design]]
