"""DQX Core summary-metric adapter and an explicitly fictional result source.

Reference: https://databrickslabs.github.io/dqx/docs/reference/table_schemas/
The provider boundary can later read a daily UC snapshot. No remote connection,
quality execution, raw failing records, or scheduler is implemented here.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Protocol


class QualitySource(Protocol):
    def list_runs(self, asset_id: str) -> list[dict]: ...
    def metadata(self) -> dict: ...


def count(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("DQX row counts must be nonnegative integers")
    result = int(value)
    if result < 0:
        raise ValueError("DQX row counts must be nonnegative integers")
    return result


def utc(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("run_time requires an explicit timezone")
    return result.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_dqx(metrics_rows: list[dict], checks_rows: list[dict]) -> list[dict]:
    """Normalize DQX Core's long metric rows without inferring missing counts.

    Run names/IDs can be reused by observers. Timestamp, input, and rule-set
    identity are kept in the grouping key. Definitions join by fingerprints,
    never by a mutable name. Contradictory duplicates fail validation.
    """
    definitions = {}
    for row in checks_rows:
        key = row["rule_set_fingerprint"], row["rule_fingerprint"]
        if key in definitions and definitions[key] != row:
            raise ValueError("Conflicting definitions for the same rule fingerprint")
        definitions[key] = row
    groups = {}
    for row in metrics_rows:
        key = (row["input_location"], row["run_name"], row["run_id"], utc(row["run_time"]), row.get("rule_set_fingerprint"))
        metrics = groups.setdefault(key, {})
        name = row["metric_name"]
        if name in metrics and metrics[name] != row["metric_value"]:
            raise ValueError("Conflicting metric values for the same execution")
        metrics[name] = row["metric_value"]
    runs = []
    for key, metrics in groups.items():
        input_location, run_name, run_id, run_time, rule_set = key
        # Missing summary values are unavailable, not zero or a successful run.
        required = ("input_row_count", "error_row_count", "warning_row_count", "valid_row_count")
        if any(name not in metrics for name in required):
            raise ValueError("Required DQX summary metrics are missing")
        totals = {name: count(metrics[name]) for name in required}
        n, errors, warnings, valid = (totals[name] for name in ("input_row_count", "error_row_count", "warning_row_count", "valid_row_count"))
        union = n - valid
        if any(value > n for value in (errors, warnings, valid)) or not max(errors, warnings) <= union <= min(n, errors + warnings):
            raise ValueError("Inconsistent dataset row counts")
        details = []
        seen = set()
        check_metrics = json.loads(metrics.get("check_metrics", "[]"))
        if not isinstance(check_metrics, list) or any(not isinstance(value, dict) for value in check_metrics):
            raise ValueError("check_metrics must be a JSON array of objects")
        for metric in check_metrics:
            fingerprint = metric.get("rule_fingerprint")
            if not fingerprint or fingerprint in seen:
                raise ValueError("Each per-check result requires a unique rule_fingerprint")
            seen.add(fingerprint)
            checked = count(metric["checked_count"])
            error = count(metric["error_count"])
            warning = count(metric["warning_count"])
            # Core can emit skipped-check flags while checked_count is zero.
            # Preserve those flags without manufacturing a pass rate.
            if checked > n or error + warning > (checked if checked else n) or (error and warning):
                raise ValueError("Inconsistent per-check counts or mixed criticality")
            definition = definitions.get((rule_set, fingerprint), {})
            criticality = definition.get("criticality")
            if criticality not in (None, "error", "warn") or (criticality == "warn" and error) or (criticality == "error" and warning):
                raise ValueError("Per-check counts conflict with recorded criticality")
            metadata = definition.get("user_metadata") or {}
            check = definition.get("check") or {}
            args = check.get("arguments") or {}
            columns = json.loads(metadata["columns"]) if "columns" in metadata else []
            if not columns and args.get("column"):
                columns = [args["column"]]
            if not isinstance(columns, list) or any(not isinstance(c, str) for c in columns):
                raise ValueError("Check columns must be an array of names")
            failures = error + warning
            details.append({
                "name": metric["check_name"], "rule_fingerprint": fingerprint,
                "criticality": criticality, "columns": columns,
                "dimension": metadata.get("dimension"),
                "rule": metadata.get("business_rule"), "function": check.get("function"),
                "arguments": args, "filter": definition.get("filter"),
                "definition_available": bool(definition), "checked_count": checked,
                "error_count": error, "warning_count": warning, "failed_count": failures,
                "pass_rate": (checked - failures) / checked * 100 if checked else None,
                "status": "not_evaluated" if not checked else "failed" if error else "warning" if warning else "passed",
            })
        identity = hashlib.sha256(json.dumps(key).encode()).hexdigest()
        runs.append({"snapshot_id": identity, "run_id": run_id, "run_name": run_name,
                     "run_time": run_time, "input_location": input_location,
                     "rule_set_fingerprint": rule_set, **totals,
                     "valid_row_rate": valid / n * 100 if n else None,
                     "per_check_available": "check_metrics" in metrics,
                     "checks": details})
    return sorted(runs, key=lambda run: (run["run_time"], run["snapshot_id"]), reverse=True)


class SampleDQXSource:
    """Six checks across seven fixed sample runs; no data is read or checked."""
    def __init__(self):
        specs = [
            ("Order identifier is unique", ["order_id"], "error", "Uniqueness", "is_unique", {"columns": '["order_id"]'}, "order_id is unique"),
            ("Order value is nonnegative", ["gross_amount"], "error", "Validity", "is_not_less_than", {"column": "gross_amount", "limit": "0"}, "gross_amount >= 0"),
            ("Refund does not exceed order value", ["refund_amount", "gross_amount"], "warn", "Consistency", "sql_expression", {"expression": "refund_amount <= gross_amount"}, "refund_amount <= gross_amount"),
            ("Order identifier is present", ["order_id"], "error", "Completeness", "is_not_null", {"column": "order_id"}, "order_id IS NOT NULL"),
            ("Customer identifier is present", ["customer_id"], "error", "Completeness", "is_not_null", {"column": "customer_id"}, "customer_id IS NOT NULL"),
            ("Refund amount is nonnegative", ["refund_amount"], "error", "Validity", "is_not_less_than", {"column": "refund_amount", "limit": "0"}, "refund_amount >= 0"),
        ]
        rule_set = hashlib.sha256(b"fictional-dqx-rule-set-v1").hexdigest()
        definitions = []
        for i, (name, columns, criticality, dimension, function, arguments, rule) in enumerate(specs):
            definitions.append({"name": name, "criticality": criticality,
                "rule_set_fingerprint": rule_set,
                "rule_fingerprint": hashlib.sha256(f"fictional-dqx-rule-{i}".encode()).hexdigest(),
                "check": {"function": function, "arguments": arguments},
                "filter": "refund_amount IS NOT NULL" if i == 5 else None,
                "user_metadata": {"dimension": dimension, "business_rule": rule, "columns": json.dumps(columns)}})
        rows = []
        for i, (errors, warnings) in enumerate(zip([8, 10, 7, 6, 16, 14, 12], [18, 21, 17, 20, 36, 33, 31])):
            date = datetime(2026, 11, 13, 9, tzinfo=timezone.utc) + timedelta(days=i)
            per_check = []
            for j, definition in enumerate(definitions):
                per_check.append({"check_name": definition["name"], "rule_fingerprint": definition["rule_fingerprint"],
                    "checked_count": 24800 if j == 5 else 25000,
                    "error_count": errors if j == 0 else min(4, errors) if j == 4 else 0,
                    "warning_count": warnings if j == 2 else 0})
            totals = {"input_row_count": 25000, "error_row_count": errors, "warning_row_count": warnings,
                      # Three rows overlap between error and warning populations.
                      "valid_row_count": 25000 - errors - warnings + 3,
                      "check_metrics": json.dumps(per_check)}
            for name, value in totals.items():
                rows.append({"input_location": "demo_catalog.commerce.orders", "run_name": "orders_daily",
                    "run_id": f"sample-orders-{date.date()}", "run_time": date.isoformat(),
                    "rule_set_fingerprint": rule_set, "metric_name": name, "metric_value": str(value)})
        self.runs = normalize_dqx(rows, definitions)

    def list_runs(self, asset_id):
        return deepcopy(self.runs) if asset_id == "orders" else []

    def metadata(self):
        return {"sample_data": True, "format": "dqx_core_summary",
                "sync_status": "not_connected", "last_synced_at": None}
