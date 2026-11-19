# Read-only browser preview

The preview runs the actual React/FastAPI application in a dedicated local
container. It uses a separate catalog volume seeded with fictional records.
Admin editing is disabled for this instance; normal local development can still
configure `META_ADMIN_PASSWORD` independently.

Current local endpoint: `http://127.0.0.1:8127`.

The external HTTPS address is printed by the owned temporary tunnel:

```bash
journalctl --user -u datasaurus-preview-tunnel.service --no-pager -o cat
```

The tunnel address changes if the tunnel is recreated. This is a temporary
review endpoint, not the company's production deployment. The preview container
is named `datasaurus-preview`; its persistent data volume is
`datasaurus-preview-data`. The tunnel is managed as the user service
`datasaurus-preview-tunnel.service`.

To stop external access and then the container:

```bash
systemctl --user stop datasaurus-preview-tunnel.service
docker stop datasaurus-preview
```

Do not remove the data volume when stopping a preview. Real database access,
daily UC ingestion and a permanent company-hosted endpoint are separate work.
