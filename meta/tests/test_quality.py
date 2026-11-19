from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1]))
from app import create_app
from quality import SampleDQXSource, normalize_dqx


def records(input_count=100, errors=10, warnings=20, valid=75, checked=80, failed=10):
    metrics = {"input_row_count": input_count, "error_row_count": errors,
               "warning_row_count": warnings, "valid_row_count": valid,
               "check_metrics": json.dumps([{"check_name": "same name", "rule_fingerprint": "rule-a",
                    "checked_count": checked, "error_count": failed, "warning_count": 0}])}
    return [{"run_id": "observer-reused-id", "run_name": "daily", "run_time": "2026-11-19T09:00:00Z",
             "input_location": "catalog.schema.orders", "rule_set_fingerprint": "set-a",
             "metric_name": name, "metric_value": str(value)} for name, value in metrics.items()]


def test_overlapping_dataset_populations_and_filtered_denominator():
    run = normalize_dqx(records(), [])[0]
    assert run["valid_row_rate"] == 75
    assert run["checks"][0]["pass_rate"] == 87.5  # 70 / 80, not 90 / 100
    assert run["checks"][0]["criticality"] is None
    assert not run["checks"][0]["definition_available"]


def test_zero_input_and_zero_checked_never_become_passing():
    run = normalize_dqx(records(0, 0, 0, 0, 0, 0), [])[0]
    assert run["valid_row_rate"] is None
    assert run["checks"][0]["pass_rate"] is None
    assert run["checks"][0]["status"] == "not_evaluated"


def test_skipped_check_flags_with_zero_evaluated_rows_are_preserved():
    check = normalize_dqx(records(100, 100, 0, 0, 0, 100), [])[0]["checks"][0]
    assert check["checked_count"] == 0
    assert check["error_count"] == 100
    assert check["status"] == "not_evaluated"
    assert check["pass_rate"] is None


def test_missing_per_check_metrics_are_explicit():
    rows = [row for row in records() if row["metric_name"] != "check_metrics"]
    run = normalize_dqx(rows, [])[0]
    assert run["checks"] == []
    assert not run["per_check_available"]
    with pytest.raises(ValueError, match="missing"):
        normalize_dqx(rows[:-1], [])


def test_reused_observer_id_does_not_merge_distinct_runs():
    first = records()
    second = deepcopy(first)
    for row in second:
        row["run_time"] = "2026-11-20T09:00:00Z"
    runs = normalize_dqx(first + second, [])
    assert len(runs) == 2
    assert runs[0]["snapshot_id"] != runs[1]["snapshot_id"]
    duplicate = deepcopy(first[0])
    duplicate["metric_value"] = "999"
    with pytest.raises(ValueError, match="Conflicting"):
        normalize_dqx(first + [duplicate], [])
    assert len(normalize_dqx(first + first, [])) == 1


def test_definitions_join_by_rule_set_and_fingerprint_not_name():
    definition = {"name": "same name", "rule_set_fingerprint": "set-a", "rule_fingerprint": "rule-a",
                  "criticality": "error", "check": {"function": "is_not_null", "arguments": {"column": "order_id"}}}
    old = {**definition, "rule_set_fingerprint": "older-set", "check": {"function": "different_rule"}}
    check = normalize_dqx(records(), [definition, old])[0]["checks"][0]
    assert check["function"] == "is_not_null"
    assert check["columns"] == ["order_id"]
    assert check["criticality"] == "error"


@pytest.mark.parametrize("args", [(100, 10, 20, 99, 80, 10), (100, 10, 20, 75, 5, 10), (100, -1, 20, 75, 80, 10)])
def test_contradictory_counts_are_rejected(args):
    with pytest.raises(ValueError):
        normalize_dqx(records(*args), [])


def test_quality_api_is_read_only_and_reports_provenance(tmp_path):
    client = TestClient(create_app(tmp_path / "db.sqlite", admin_password=""))
    result = client.get("/api/assets/orders/quality")
    assert result.status_code == 200
    body = result.json()
    assert body["sample_data"] and body["sync_status"] == "not_connected"
    assert body["last_synced_at"] is None
    assert len(body["runs"]) == 7
    assert len(body["runs"][0]["checks"]) == 6
    assert body["runs"][0]["valid_row_rate"] == pytest.approx(99.84)
    assert client.get("/api/assets/customers/quality").json()["runs"] == []
    assert client.get("/api/assets/missing/quality").status_code == 404
    assert client.post("/api/assets/orders/quality", json={}).status_code == 405
    assert SampleDQXSource().list_runs("customers") == []
