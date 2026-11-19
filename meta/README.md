# Datasaurus

A FastAPI + React proof of concept with a compact single-page catalog. It is a
standalone sample application; it does not integrate with the OpenMetadata
product or any real database yet.

## Run locally

Requires Python 3.11+ and Node 20.19+ (Node 24 recommended).

```bash
cd meta
uv sync --frozen
cd frontend
npm ci
npm run build
cd ..
uv run uvicorn app:app --host 127.0.0.1 --port 8127
```

Open **http://127.0.0.1:8127**. FastAPI serves both `/api` and the built React
application, so there is one origin and one process to deploy. For frontend
development, run `npm run dev` in `frontend/` alongside the API; Vite proxies
`/api` to port 8127. API documentation is at `/api/docs`.

Without `uv`, create a Python virtual environment and install `requirements.txt`,
then run `python -m uvicorn app:app --host 127.0.0.1 --port 8127`.

## Admin and reader views

Browsing is anonymous and read-only. Admin editing is disabled until the server
receives `META_ADMIN_PASSWORD`. In Bash/Git Bash, enter a chosen password
without placing it in shell history:

```bash
read -rsp 'Choose an admin password: ' META_ADMIN_PASSWORD
echo
export META_ADMIN_PASSWORD
uv run uvicorn app:app --host 127.0.0.1 --port 8127
```

Use **Admin sign-in** in the page. Authenticated admins can edit table details,
attribute definitions, transformations and lineage sources, check definitions,
ownership, consumers, and contacts. Recorded run results are read-only. Reader writes are
rejected by the API, regardless of frontend state. Sign-in uses an HttpOnly,
SameSite cookie with an eight-hour session. Sign-out revokes it. Changing or
disabling the server password invalidates old sessions. This shared-password
model is for the prototype; company SSO and named-user auditing are future work.

SQLite persists edits in `meta/data/catalog.sqlite` (`META_DB` overrides it).
Source assets seed only when missing; restarts preserve changes. Revision checks
reject conflicting updates, and every successful edit records a revision/time.
Referenced attributes cannot be renamed/deleted while lineage still points to
them. There is no new-table/delete-table flow in this initial PoC.

## What is demonstrated

- Catalog search, domain filter, and a simple overview before details.
- Attribute business definitions and transformation logic.
- Clickable table lineage with expandable attribute mappings.
- Attribute-specific, transitive downstream impact and affected team contacts.
- Compact DQX Core summary reporting, per-check metrics and sample run history.
- Admin forms and durable, validated edits.
- Responsive layouts and keyboard-accessible tabs/dialogs.

The five views are Overview, Attributes, Lineage, Quality and Impact. Contacts
are part of Impact; the compact owner menu in the shared summary also exposes
table contacts. Clicking an email copies its address without opening a mail app.
Admin contact editing is grouped with table details.

Quality now uses a compact summary strip and a filterable check table, with
rule details collapsed by default. The viewer is backed by a tested DQX Core
metric normalizer and seven fictional runs, not a live database connection.
See [DQX reporting and daily ingestion design](docs/quality-dqx.md) for mappings,
metric definitions and the planned read-only Unity Catalog sync.

The current editable English management report and rendered previews are in
[reports/weekly-report](reports/weekly-report/README.md): site structure and
business use on page 1, progress and next steps on page 2.

The footer shows the selected catalog record's creation time on the left and
metadata update time on the right. These values are persisted and owned by the
server. Older records without trustworthy timestamps show a dash; a migration
does not invent a historical creation date. Quality execution/sync timestamps
remain separate from metadata record timestamps. Reader pages omit the old
sample-data banners; the quality result badge uses "Preview" and the data-source
API still identifies fictional results accurately.

All five tables and all people are fictional; contact emails use
`example.invalid`. Impact is derived from recorded source-attribute links and
consumer/owner contacts. Missing lineage means unknown dependencies, not a
guarantee of no impact.

## Future database and check integration

`source.py` contains a small `MetadataSource.discover()` interface and the sample
provider. A future connector can discover technical names/types, then merge them
without overwriting curated definitions, ownership, contacts, or lineage.
Connection management, discovery/import jobs, SQL lineage parsing, actual quality
execution and recurring scheduling are **not implemented**. Sample results never
query a database or execute the displayed rule text.

## Containers and GitLab deployment

```bash
docker compose -f compose.yml up --build
```

The container serves FastAPI and React together; a named volume persists the
catalog. Admin editing follows the same environment setting as above. The default
Compose port binds only to localhost. A company reverse proxy can provide HTTPS
and the chosen internal hostname. Set `META_SECURE_COOKIE=1` for HTTPS deployments,
preserve the public Host/Origin through the proxy, and configure trusted forwarded
headers as appropriate for that proxy.

GitLab calls its automation **CI/CD pipelines**. `gitlab-ci.example.yml` provides
API tests, a React build, and an optional manual container-image build/push.
It is an example to include in the company's pipeline, not an active root CI file.
The image job needs a Docker-capable runner with the GitLab Docker-in-Docker TLS
cert volume configured, a container registry, and a permitted build/push identity.
No deployment credentials or company hostname are stored here.

The later deployment job should pull the versioned image onto the company's
server/container platform, mount persistent storage, provide runtime secrets,
and register its environment URL. That job needs the actual company target and
runner configuration, so no live deployment has been performed.

[GitLab Pages](https://docs.gitlab.com/user/project/pages/) serves static assets
and cannot run FastAPI. It can host React separately if an API host is supplied;
the current same-origin container avoids requiring that split.
[GitLab environments](https://docs.gitlab.com/ci/environments/) track deployments
to company-managed application servers.

## Verification

```bash
uv run pytest tests/test_api.py -q
uv run pytest tests/test_quality.py -q
uv run python tests/browser_smoke.py
```

The browser check requires Chrome on PATH or a Playwright Chromium installation
(`uv run playwright install chromium`). Build the frontend first. It starts its
own temporary API with a random password and disposable database, checks reader
and admin behavior, and stops its processes. Screenshots and its result JSON go
under the repository's ignored `plans/evidence/` directory.
`TEST_BROWSER=/path/to/chromium` optionally selects a browser executable.
