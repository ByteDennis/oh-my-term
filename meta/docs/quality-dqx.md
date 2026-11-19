# Quality reporting and future daily Unity Catalog ingestion

The Quality view uses DQX **Core summary metrics** as its reference contract.
It is a compact viewer for recorded results. It does not run DQX and does not
currently connect to Databricks. All displayed runs are fictional fixtures.

## What the page shows

- One summary strip: valid row percentage, input/error/warning rows, and checks
  passed. Error and warning populations may overlap, so they are not added to
  calculate the number of invalid rows.
- A compact check table: severity, evaluated rows, issue rows, pass rate and
  result. Search, issue/severity filters and historical run selection are local
  interactions over the returned history.
- Expanding a check reveals its recorded rule, filter and run. Fingerprints are
  available in a further traceability disclosure.
- Last execution and last synchronization are different. Current fixtures show
  their execution date; synchronization remains `not_connected`, with no fake
  "last synced" timestamp. Tables without recorded runs do not display a pass.

`valid_row_rate = valid_row_count / input_row_count`. This is **not** DQX Studio's
DQ score. Studio documents its score as the average check pass rate and can
apply a pass threshold separately. This Core viewer uses strict zero-violation
check status: errors become Failed, warnings become Warning, zero violations
become Passed. Zero evaluated rows are Not evaluated. No threshold is invented
when the source has not supplied one.

## Mapping implemented now

`quality.py::normalize_dqx()` accepts Core's long summary rows and a matching
checks-table extract. `QualitySource.list_runs(asset_id)` is the history provider
boundary; `metadata()` supplies sample/real provenance, sync state and successful
sync time. The app currently supplies `SampleDQXSource`. The view already reads
those state fields rather than claiming a successful live connection.

| Core source | Viewer mapping |
|---|---|
| `input_row_count`, `error_row_count`, `warning_row_count`, `valid_row_count` metric rows | Summary row counts |
| `check_metrics` JSON: `checked_count`, `error_count`, `warning_count` | Per-check counts and pass rate, using each check's evaluated rows |
| Checks table `criticality` | Error / Warn; kept distinct from the observed result |
| `run_id`, `run_name`, `input_location`, `run_time`, `rule_set_fingerprint` | Snapshot identity and run selector |
| `rule_fingerprint` + `rule_set_fingerprint` | Exact check-definition join; no name-only join |

Core per-check summary metrics require DQX 0.14.0 or later. Older/missing
`check_metrics` is represented as unavailable, not six imaginary passing checks.
Missing required summary counts and contradictory duplicate metrics are rejected.
Repeated observer IDs at different execution times remain distinct snapshots.
Row counts are parsed from string-encoded values; timestamps require explicit
timezones. Checked counts respect per-rule filters. A skipped check can have zero
evaluated rows while still carrying error/warning flags: preserve the flags and
leave its pass rate unavailable. Name-only legacy entries without fingerprints
or evaluated-row counts are outside this adapter's full per-rule contract.
Optional dimension, business
description and column labels can come from check metadata. The fixture's
`user_metadata.columns` / `business_rule` / `dimension` keys are application
conventions, not extra required DQX columns. Raw failing rows are not fetched.

The read-only endpoint is `GET /api/assets/{asset_id}/quality`, contract version
1. Recorded results are separate from the catalog's curated check definitions;
editing a definition does not rewrite a past run. Legacy sample status fields on
asset records remain accepted for compatibility but no longer drive the report.

## Future daily flow — not enabled

1. The existing Databricks job runs DQX and persists its optional summary metrics
   and versioned check definitions in configured UC-managed Delta tables. Unity
   Catalog alone does not generate these DQX metrics.
2. After that job completes, a daily read-only synchronization uses a SQL
   warehouse and a configured identity to read those small result tables. It
   does not rerun the source data checks. The SQL Connector is one supported
   option for a separately hosted FastAPI deployment.
3. Normalize results through the existing adapter, then store an immutable local
   snapshot. Add an ingestion implementation of `QualitySource` to read that
   store. Snapshot storage/import and a live connector are not implemented yet.
4. Track successful sync time independently, reread a configurable overlap window
   for late-arriving runs and deduplicate by execution identity. Report failed or
   stale syncs while retaining the last good snapshot. Do not treat missing runs
   as passing, and do not combine partial metric batches into one execution.

Before the live step, confirm Core vs Studio, installed DQX version, exact
metrics/checks-table FQNs, run configuration, catalog-table mappings, SQL
warehouse access and the daily completion/timezone convention. Studio has a
different storage/reporting model and needs its own adapter; its results should
not be fed into the Core parser unchanged.

`dqx-summary-read.example.sql` is a review template for the two read-only queries.
It has not been executed against Databricks. There is no scheduler, Databricks
credential setup, source-table write, source-row scan, or automatic sync enabled
by this change.

## Primary references

- [DQX Core summary metrics](https://databrickslabs.github.io/dqx/docs/guide/summary_metrics/)
- [Core observer implementation](https://github.com/databrickslabs/dqx/blob/main/src/databricks/labs/dqx/metrics_observer.py)
- [DQX table schemas and relationships](https://databrickslabs.github.io/dqx/docs/reference/table_schemas/)
- [DQX dashboard organization](https://databrickslabs.github.io/dqx/docs/guide/quality_dashboard/)
- [Studio results and score semantics](https://databrickslabs.github.io/dqx/docs/studio/running/)
- [Databricks scheduled jobs](https://docs.databricks.com/aws/en/jobs/scheduled)
- [Databricks SQL Connector](https://docs.databricks.com/aws/en/dev-tools/python-sql-connector)
