import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Literal
from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict, model_validator

from source import SampleSource
from quality import SampleDQXSource

ROOT = Path(__file__).parent


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Contact(StrictModel):
    team: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=254)


class Source(StrictModel):
    table: str = Field(min_length=1, max_length=120)
    column: str = Field(min_length=1, max_length=120)


class Column(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    data_type: str = Field(min_length=1, max_length=120)
    definition: str = Field(max_length=10000)
    transformation: str = Field(max_length=10000)
    sources: list[Source] = Field(default_factory=list, max_length=100)


class Check(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    column: str = Field(max_length=120)
    rule: str = Field(min_length=1, max_length=10000)
    status: Literal["passed", "warning", "failed", "not_run"]
    observed: str = Field(max_length=10000)
    checked_at: str = Field(max_length=100)


class Asset(StrictModel):
    id: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)
    schema_name: str = Field(min_length=1, max_length=120)
    domain: str = Field(min_length=1, max_length=120)
    description: str = Field(max_length=20000)
    owner: str = Field(min_length=1, max_length=120)
    contacts: list[Contact] = Field(max_length=100)
    consumers: list[Contact] = Field(max_length=100)
    columns: list[Column] = Field(max_length=1000)
    checks: list[Check] = Field(max_length=1000)
    version: int = Field(default=1, ge=1)
    created_at: str | None = Field(default=None, max_length=100)
    updated_at: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def unique_columns(self):
        names = [column.name for column in self.columns]
        if len(names) != len(set(names)):
            raise ValueError("column names must be unique")
        if any(check.column and check.column not in names for check in self.checks):
            raise ValueError("quality checks must reference an existing column")
        return self


class Login(StrictModel):
    password: str = Field(min_length=1, max_length=1024)


def create_app(db_path=None, admin_password=None, quality_source=None):
    path = Path(db_path or os.environ.get("META_DB", ROOT / "data/catalog.sqlite"))
    path.parent.mkdir(parents=True, exist_ok=True)
    password = admin_password if admin_password is not None else os.environ.get("META_ADMIN_PASSWORD", "")
    app = FastAPI(title="Datasaurus metadata", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json",
                  swagger_ui_parameters={"supportedSubmitMethods": ["get"]})
    app.state.db_path = path
    quality_source = quality_source if quality_source is not None else SampleDQXSource()

    @contextmanager
    def db():
        connection = sqlite3.connect(path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    with db() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, version INTEGER NOT NULL, body TEXT NOT NULL, created_at TEXT, updated_at TEXT)")
        existing_columns = {row["name"] for row in connection.execute("PRAGMA table_info(assets)")}
        for column in ("created_at", "updated_at"):
            if column not in existing_columns:
                connection.execute(f"ALTER TABLE assets ADD COLUMN {column} TEXT")
        connection.execute("CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, expires REAL NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, asset TEXT, version INTEGER, changed_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        for asset in SampleSource().discover():
            stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            item = Asset(**asset, created_at=stamp, updated_at=stamp)
            connection.execute("INSERT OR IGNORE INTO assets (id, version, body, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                               (item.id, item.version, item.model_dump_json(), stamp, stamp))

    def all_assets():
        with db() as connection:
            return [{**json.loads(row["body"]), "created_at": row["created_at"], "updated_at": row["updated_at"]}
                    for row in connection.execute("SELECT body, created_at, updated_at FROM assets ORDER BY id")]

    def session_digest(token):
        return hmac.new(password.encode(), token.encode(), hashlib.sha256).hexdigest()

    def is_admin(request):
        if not password:
            return False
        token = request.cookies.get("meta_session", "")
        digest = session_digest(token)
        with db() as connection:
            return bool(connection.execute("SELECT 1 FROM sessions WHERE digest=? AND expires>?", (digest, time.time())).fetchone())

    def same_origin(request: Request):
        origin = request.headers.get("origin")
        allowed = str(request.base_url).rstrip("/")
        if origin and origin != allowed:
            raise HTTPException(403, "Cross-origin changes are not allowed")

    def admin(request: Request):
        same_origin(request)
        if not is_admin(request):
            raise HTTPException(403, "Admin sign-in required")

    @app.get("/api/session")
    def session(request: Request):
        return {"role": "admin" if is_admin(request) else "reader", "admin_enabled": bool(password), "sample_data": True}

    @app.post("/api/auth/login", dependencies=[Depends(same_origin)])
    def login(body: Login, response: Response):
        if not password:
            raise HTTPException(503, "Admin editing is disabled; configure META_ADMIN_PASSWORD on the server")
        if not secrets.compare_digest(body.password.encode(), password.encode()):
            raise HTTPException(401, "Incorrect password")
        token = secrets.token_urlsafe(32)
        with db() as connection:
            connection.execute("DELETE FROM sessions WHERE expires <= ?", (time.time(),))
            connection.execute("INSERT INTO sessions VALUES (?, ?)", (session_digest(token), time.time() + 8 * 3600))
        response.set_cookie("meta_session", token, httponly=True, samesite="strict", max_age=8 * 3600,
                            secure=os.environ.get("META_SECURE_COOKIE") == "1", path="/api")
        return {"role": "admin"}

    @app.post("/api/auth/logout", dependencies=[Depends(same_origin)])
    def logout(request: Request, response: Response):
        with db() as connection:
            connection.execute("DELETE FROM sessions WHERE digest=?", (session_digest(request.cookies.get("meta_session", "")),))
        response.delete_cookie("meta_session", path="/api")
        return {"role": "reader"}

    @app.get("/api/assets")
    def assets():
        return all_assets()

    @app.get("/api/assets/{asset_id}/quality")
    def quality(asset_id: str):
        with db() as connection:
            if not connection.execute("SELECT 1 FROM assets WHERE id=?", (asset_id,)).fetchone():
                raise HTTPException(404, "Table not found")
        return {**quality_source.metadata(), "contract_version": 1,
                "runs": quality_source.list_runs(asset_id)}

    @app.put("/api/assets/{asset_id}", dependencies=[Depends(admin)])
    def update(asset_id: str, body: Asset):
        if body.id != asset_id:
            raise HTTPException(422, "Asset identifier cannot change")
        with db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            values = {row["id"]: json.loads(row["body"]) for row in connection.execute("SELECT id, body FROM assets")}
            if asset_id not in values:
                raise HTTPException(404, "Table not found")
            timestamp = connection.execute("SELECT created_at FROM assets WHERE id=?", (asset_id,)).fetchone()
            body.created_at = timestamp["created_at"]
            body.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            values[asset_id] = body.model_dump()
            for item in values.values():
                for column in item["columns"]:
                    for source in column["sources"]:
                        target = values.get(source["table"])
                        if not target or source["column"] not in {c["name"] for c in target["columns"]}:
                            raise HTTPException(422, "A lineage link references a missing table or column; update dependent links before renaming")
            body.version += 1
            changed = connection.execute("UPDATE assets SET version=?, body=?, updated_at=? WHERE id=? AND version=?",
                                         (body.version, body.model_dump_json(), body.updated_at, asset_id, body.version - 1))
            if changed.rowcount != 1:
                raise HTTPException(409, "This table was edited elsewhere. Reload before saving.")
            connection.execute("INSERT INTO audit (asset, version) VALUES (?, ?)", (asset_id, body.version))
        return body

    @app.get("/api/assets/{asset_id}/impact")
    def impact(asset_id: str, column: str | None = None):
        values = {item["id"]: item for item in all_assets()}
        if asset_id not in values:
            raise HTTPException(404, "Table not found")
        selected = values[asset_id]
        names = {c["name"] for c in selected["columns"]}
        if column is not None and column not in names:
            raise HTTPException(404, "Column not found")
        queue = [(asset_id, name, 0) for name in ([column] if column else names)]
        visited, affected = set(), {}
        while queue:
            table, attr, depth = queue.pop(0)
            if (table, attr) in visited:
                continue
            visited.add((table, attr))
            for item in values.values():
                for field in item["columns"]:
                    if any(s["table"] == table and s["column"] == attr for s in field["sources"]):
                        queue.append((item["id"], field["name"], depth + 1))
                        if item["id"] != asset_id:
                            record = affected.setdefault(item["id"], {"id": item["id"], "name": item["name"], "schema_name": item["schema_name"], "owner": item["owner"], "columns": [], "depth": depth + 1})
                            if field["name"] not in record["columns"]:
                                record["columns"].append(field["name"])
        contacts = {}
        for id in [asset_id, *affected]:
            for contact in values[id]["consumers"] + values[id]["contacts"]:
                contacts[(contact["team"], contact["email"])] = contact
        return {"downstream": sorted(affected.values(), key=lambda x: (x["depth"], x["name"])),
                "contacts": list(contacts.values()), "column": column, "sample_data": True}

    @app.get("/api/health")
    def health():
        return {"status": "ok", "sample_data": True}

    dist = ROOT / "frontend/dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
