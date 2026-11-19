import copy
from datetime import datetime
import json
from pathlib import Path
import sys
import sqlite3

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from app import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path / "catalog.sqlite", admin_password="test-password"))


def login(client):
    response = client.post("/api/auth/login", json={"password": "test-password"})
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]


def test_reader_is_enforced_by_server(client):
    assert client.get("/api/session").json()["role"] == "reader"
    asset = client.get("/api/assets").json()[0]
    assert client.put(f"/api/assets/{asset['id']}", json=asset).status_code == 403
    assert client.post("/api/auth/login", json={"password": "incorrect"}).status_code == 401
    login(client)
    assert client.get("/api/session").json()["role"] == "admin"
    assert client.post("/api/auth/logout").status_code == 200
    assert client.put(f"/api/assets/{asset['id']}", json=asset).status_code == 403


def test_edit_persists_and_conflicting_revision_is_rejected(client):
    login(client)
    asset = client.get("/api/assets").json()[0]
    original = copy.deepcopy(asset)
    asset["description"] = "Updated business definition"
    saved = client.put(f"/api/assets/{asset['id']}", json=asset)
    assert saved.status_code == 200
    assert saved.json()["version"] == asset["version"] + 1
    assert client.put(f"/api/assets/{asset['id']}", json=original).status_code == 409
    restarted = TestClient(create_app(client.app.state.db_path, admin_password="test-password"))
    assert next(a for a in restarted.get("/api/assets").json() if a["id"] == asset["id"])["description"] == asset["description"]


def test_lineage_references_are_validated(client):
    login(client)
    values = {a["id"]: a for a in client.get("/api/assets").json()}
    order = values["orders"]
    order["columns"][2]["name"] = "renamed_amount"
    assert client.put("/api/assets/orders", json=order).status_code == 422
    modeled = values["net_orders"]
    modeled["columns"][0]["sources"] = [{"table": "missing", "column": "missing"}]
    assert client.put("/api/assets/net_orders", json=modeled).status_code == 422


def test_attribute_impact_traverses_multiple_steps(client):
    amount = client.get("/api/assets/orders/impact?column=gross_amount").json()
    values = {a["id"]: a for a in amount["downstream"]}
    assert set(values) == {"net_orders", "daily_revenue", "channel_performance"}
    assert values["net_orders"]["columns"] == ["net_amount"]
    assert values["daily_revenue"]["depth"] == 2
    assert {"Finance", "Growth Marketing"} <= {c["team"] for c in amount["contacts"]}
    channel = client.get("/api/assets/customers/impact?column=acquisition_channel").json()
    assert "daily_revenue" not in {a["id"] for a in channel["downstream"]}
    assert client.get("/api/assets/orders/impact?column=missing").status_code == 404


def test_forged_role_and_cross_origin_changes_are_rejected(client):
    login(client)
    asset = client.get("/api/assets").json()[0]
    assert client.put(f"/api/assets/{asset['id']}", json=asset, headers={"Origin": "https://other.example"}).status_code == 403
    assert client.post("/api/auth/login", json={"password": "test-password"}, headers={"Origin": "https://other.example"}).status_code == 403
    anonymous = TestClient(client.app)
    assert anonymous.put(f"/api/assets/{asset['id']}", json=asset, headers={"X-Role": "admin"}).status_code == 403


def test_admin_is_disabled_without_configuration(tmp_path):
    client = TestClient(create_app(tmp_path / "catalog.sqlite", admin_password=""))
    assert not client.get("/api/session").json()["admin_enabled"]
    assert client.post("/api/auth/login", json={"password": "anything"}).status_code == 503


def test_creation_and_update_times_are_server_owned_and_persist(client):
    login(client)
    asset = next(a for a in client.get("/api/assets").json() if a["id"] == "orders")
    created = asset["created_at"]
    assert datetime.fromisoformat(created.replace("Z", "+00:00")).tzinfo is not None
    asset["created_at"] = "1900-01-01T00:00:00Z"
    asset["updated_at"] = "1900-01-01T00:00:00Z"
    asset["description"] = "Updated by the timestamp test"
    saved = client.put("/api/assets/orders", json=asset)
    assert saved.status_code == 200
    assert saved.json()["created_at"] == created
    assert saved.json()["updated_at"] >= created
    restarted = TestClient(create_app(client.app.state.db_path, admin_password="test-password"))
    persisted = next(a for a in restarted.get("/api/assets").json() if a["id"] == "orders")
    assert persisted["created_at"] == created
    assert persisted["updated_at"] == saved.json()["updated_at"]


def test_legacy_database_migration_does_not_invent_creation_times(tmp_path):
    from source import SampleSource
    path = tmp_path / "legacy.sqlite"
    original = SampleSource().discover()[0]
    original["version"] = 7
    original["description"] = "Preserve this existing edit"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE assets (id TEXT PRIMARY KEY, version INTEGER NOT NULL, body TEXT NOT NULL)")
        connection.execute("INSERT INTO assets VALUES (?, ?, ?)", (original["id"], 7, json.dumps(original)))
    client = TestClient(create_app(path, admin_password=""))
    asset = next(a for a in client.get("/api/assets").json() if a["id"] == original["id"])
    assert asset["version"] == 7 and asset["description"] == original["description"]
    assert asset["created_at"] is None and asset["updated_at"] is None
