-- Review template only. No Databricks query or scheduler is activated by this file.
-- Replace the three-part identifiers with the observed company table names.
-- Bind values through the SQL Connector's native parameters; do not interpolate
-- input locations or timestamps into query text. Export timestamps with an
-- explicit UTC offset before calling normalize_dqx().

-- Query 1: read complete long-form metric groups in a configurable lookback.
-- Filter the desired input before ranking/grouping executions. Preserve the
-- source run timestamp, observer name and rule-set fingerprint.
SELECT run_id, run_name, input_location, checks_location,
       rule_set_fingerprint, run_time, metric_name, metric_value
FROM `catalog_name`.`schema_name`.`dqx_metrics`
WHERE input_location = :input_location
  AND run_time >= CAST(:from_time AS TIMESTAMP)
  AND metric_name IN (
    'input_row_count', 'error_row_count', 'warning_row_count',
    'valid_row_count', 'check_metrics'
  )
ORDER BY run_time DESC, run_id, metric_name;

-- Query 2: read the exact rules from the checks_location belonging to a selected
-- execution. Bind the actual run-config name, which need not equal run_name.
-- Repeat for each distinct rule-set/config required by the imported history.
SELECT name, criticality, `check`, `filter`, run_config_name,
       rule_fingerprint, rule_set_fingerprint, user_metadata
FROM `catalog_name`.`schema_name`.`dqx_checks`
WHERE rule_set_fingerprint = :rule_set_fingerprint
  AND run_config_name = :run_config_name;
