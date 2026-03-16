# Multi-Region Deployment Runbook

**Version**: 2.0.0  
**Sprint**: 06 (OB-58)  
**Audience**: On-call engineers, DevOps

---

## 1. Overview

ObserveML can be deployed across multiple regions using:

- **Fly.io** for the FastAPI application (automatic anycast routing)
- **ClickHouse Cloud** multi-region replication (or self-hosted ClickHouse Keeper cluster)
- **PostgreSQL** via Supabase (with read replicas) or Fly Postgres (volume replication)
- **Redis** (optional, Sprint 06) — one cluster per region, no cross-region sync needed (cache is local-only)

Target topology:

```
             ┌─────────────────────────────────┐
             │          Cloudflare CDN          │
             └──────────┬──────────┬────────────┘
                        │          │
                 ┌──────▼──┐  ┌────▼──────┐
                 │  EU-West │  │  US-East  │
                 │  Fly app │  │  Fly app  │
                 └────┬─────┘  └─────┬─────┘
                      │              │
         ┌────────────▼──────────────▼────────────┐
         │        ClickHouse Cloud (multi-region)  │
         │         Primary: us-east-1             │
         │         Replica: eu-west-1             │
         └────────────────────────────────────────┘
                      │              │
         ┌────────────▼──────────────▼────────────┐
         │        PostgreSQL (Supabase / Fly PG)   │
         │        Primary write + read replicas    │
         └────────────────────────────────────────┘
```

---

## 2. Fly.io App Configuration

### 2.1 Create apps in each region

```bash
# Primary
fly apps create observeml-api --org <your-org>

# Deploy to primary region
fly deploy --app observeml-api --region iad   # US East

# Scale to EU
fly machine run . --app observeml-api --region cdg --env REGION=eu-west
```

### 2.2 `fly.toml` multi-region snippet

```toml
[build]
  dockerfile = "api/Dockerfile"

[env]
  PORT = "8000"

[[services]]
  internal_port = 8000
  protocol = "tcp"

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [services.concurrency]
    type = "requests"
    soft_limit = 200
    hard_limit = 250
```

### 2.3 Secrets (set per-app)

```bash
fly secrets set \
  POSTGRES_DSN="postgresql://..." \
  CLICKHOUSE_URL="https://..." \
  CLICKHOUSE_USER="default" \
  CLICKHOUSE_PASSWORD="..." \
  REDIS_URL="redis://..." \
  --app observeml-api
```

---

## 3. ClickHouse Replication

### 3.1 ClickHouse Cloud (recommended)

1. In the ClickHouse Cloud console, navigate to your service → **Replicas**.
2. Add replica in target region (e.g. `eu-central-1`).
3. Replication is automatic; read queries can target either node.
4. Set the `CLICKHOUSE_URL` secret in each Fly region to the nearest ClickHouse Cloud endpoint.

### 3.2 Self-hosted (ClickHouse Keeper)

Minimum 3-node Keeper quorum for fault tolerance:

```xml
<!-- config.xml excerpt -->
<keeper_server>
    <tcp_port>9181</tcp_port>
    <server_id>1</server_id>
    <raft_configuration>
        <server>
            <id>1</id><hostname>ch-node-1</hostname><port>9181</port>
        </server>
        <server>
            <id>2</id><hostname>ch-node-2</hostname><port>9181</port>
        </server>
        <server>
            <id>3</id><hostname>ch-node-3</hostname><port>9181</port>
        </server>
    </raft_configuration>
</keeper_server>
```

Create the replicated table with `ReplicatedMergeTree`:

```sql
CREATE TABLE metric_events ON CLUSTER '{cluster}'
(
    org_id       String,
    event_id     UUID   DEFAULT generateUUIDv4(),
    model        String,
    call_site    String,
    latency_ms   Float64,
    input_tokens  Int32  DEFAULT 0,
    output_tokens Int32  DEFAULT 0,
    cost_usd     Float64 DEFAULT 0.0,
    error        UInt8   DEFAULT 0,
    error_code   String  DEFAULT '',
    session_id   String  DEFAULT '',
    trace_id     String  DEFAULT '',
    ts           DateTime DEFAULT now()
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/metric_events', '{replica}')
PARTITION BY toYYYYMM(ts)
ORDER BY (org_id, ts);
```

---

## 4. PostgreSQL Read Replicas

### 4.1 Fly Postgres

```bash
# Create primary
fly postgres create --name observeml-pg --region iad --initial-cluster-size 1

# Add replica in EU
fly postgres attach observeml-pg --app observeml-api-eu
fly machine run . \
  --app observeml-pg \
  --region cdg \
  --env ROLE=replica
```

The app only writes through the primary DSN. Read-heavy queries (e.g., API key lookups) tolerate replica lag for caching.

### 4.2 Supabase

Use the Supabase **Read Replicas** feature (Pro plan). Set `POSTGRES_DSN` to the pooler endpoint for writes; read replicas are transparent via PgBouncer.

---

## 5. DNS Failover

Using Cloudflare:

1. Add two A/AAAA records for `api.observeml.io`:
   - `iad.fly.dev` (US, primary) — **Proxied, priority 10**
   - `cdg.fly.dev` (EU, secondary) — **Proxied, priority 20**
2. Enable **Load Balancing** with a health-check monitor:
   - Path: `/health`
   - Expected status: `200`
   - Interval: 60 s
3. Set **Geo Routing**: EU traffic → EU pool; all other → US pool; fallback to all.

For pure DNS failover (no load balancer subscription):

```bash
# Point CNAME at Fly's anycast:
api.observeml.io  CNAME  observeml-api.fly.dev
```

Fly's anycast network will route each request to the nearest healthy machine automatically.

---

## 6. Volume Migration (Fly Volumes)

If you use Fly Volumes for local SQLite or file storage (not recommended for production but common in dev):

```bash
# List volumes
fly volumes list --app observeml-api

# Create volume in new region
fly volumes create observeml_data --region cdg --size 10 --app observeml-api

# Snapshot-restore workflow
fly volumes snapshots list --volume <vol-id>
fly volumes create observeml_data --region cdg \
  --snapshot-id <snap-id> --size 10 --app observeml-api
```

---

## 7. Runbook: Promote EU Replica to Primary

Use this when the US-East primary is degraded.

### Checklist

- [ ] Confirm US-East health check failing in Cloudflare dashboard
- [ ] Check ClickHouse Cloud replica lag: `SELECT max(ts) FROM metric_events` on EU node
- [ ] If lag < 60 s, safe to promote
- [ ] In Cloudflare Load Balancer: set EU pool as **Primary**, US pool as **Fallback**
- [ ] Update `POSTGRES_DSN` secret in EU Fly app to point to read replica (now primary)
  ```bash
  fly secrets set POSTGRES_DSN="postgresql://eu-primary/..." --app observeml-api-eu
  fly deploy --app observeml-api-eu
  ```
- [ ] Notify #incidents Slack channel
- [ ] Open postmortem ticket

### Rollback

- [ ] Verify US-East health check passing
- [ ] Switch Cloudflare Load Balancer: US pool back to **Primary**
- [ ] Restore `POSTGRES_DSN` in EU app to point to original replica DSN
- [ ] Deploy EU app

---

## 8. Runbook: Redis Cache Failure

Redis is **fail-open** in ObserveML v2.0.0. A total Redis outage degrades performance but does not cause errors.

- [ ] Check Redis logs / Cloud dashboard for the affected region
- [ ] Restart Redis instance (Cloud console or `fly machine restart`)
- [ ] Observe `MISS` rate drop in API logs
- [ ] No code rollback needed

To disable Redis entirely (emergency):

```bash
fly secrets set REDIS_URL="" --app observeml-api
fly deploy --app observeml-api
```

---

## 9. Monitoring & Alerting

| Alert | Threshold | Action |
|-------|-----------|--------|
| `/health` 5xx | > 3 in 1 min | Page on-call |
| ClickHouse write latency | > 5 s p99 | Check replica lag, scale writes |
| PostgreSQL connections | > 80% pool | Increase PgBouncer pool size |
| Redis memory | > 80% | Flush cache or resize instance |
| Fly app restart count | > 5 in 5 min | Check OOM; scale memory |

Use ObserveML's own `/v1/intelligence/root-cause` and `/v1/intelligence/forecast` endpoints to monitor the monitoring service itself.

---

## 10. References

- [Fly.io Multi-Region Apps](https://fly.io/docs/reference/regions/)
- [ClickHouse Replication](https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/replication)
- [Cloudflare Load Balancing](https://developers.cloudflare.com/load-balancing/)
- [Supabase Read Replicas](https://supabase.com/docs/guides/platform/read-replicas)
