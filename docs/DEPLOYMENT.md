# GO OIL DMS — Deployment Guide

**Version 5.0-enterprise** · Applies to Docker, Docker Compose, and Kubernetes.

---

## 1 · Prerequisites
- Docker ≥ 24
- Docker Compose plugin v2
- 4 CPU / 8 GB RAM (min for a single-node deployment)
- A domain name pointing to your load balancer / reverse proxy
- TLS certificates (Let's Encrypt via Caddy / Traefik / Nginx recommended)

---

## 2 · Environment
Copy the template and fill in values:
```bash
cp .env.production.example .env.production
$EDITOR .env.production
```

**Required**
| Variable | Purpose |
|---|---|
| `MONGO_URL` | e.g. `mongodb://mongo:27017` (Compose) or your Atlas SRV URI |
| `DB_NAME` | Database name |
| `JWT_SECRET` | ≥ 32 char random — `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | Comma-separated list of allowed origins |
| `REACT_APP_BACKEND_URL` | Public URL where the backend is reachable |

**Optional but recommended**
| Variable | Purpose |
|---|---|
| `EMERGENT_LLM_KEY` | Enables AI Business Copilot |
| `ENABLE_HSTS` | `true` if you terminate TLS yourself |
| `PAYMENT_PROVIDER` + keys | Live payments |
| `EMAIL_PROVIDER` + keys | Real email delivery |

---

## 3 · Build & Deploy
```bash
docker compose --env-file .env.production up -d --build
docker compose ps
docker compose logs -f backend
```

Services:
- `mongo` — MongoDB 7 on internal network, volume-persisted
- `backend` — FastAPI on `:8001` with 2 workers
- `frontend` — Nginx serving the SPA on `:3000`

Health probes:
- Backend: `GET /api/health` → `{"status":"ok","db":"connected"}`
- Frontend: `GET /healthz` → `ok`

---

## 4 · Reverse Proxy (recommended)
Put a TLS-terminating reverse proxy in front of both containers. Example Nginx:

```nginx
server {
  listen 443 ssl http2;
  server_name your-domain.com;
  ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

  # Frontend
  location / {
    proxy_pass http://frontend:80;
    proxy_set_header Host $host;
  }
  # Backend API
  location /api/ {
    proxy_pass http://backend:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

---

## 5 · First Login
After the stack is healthy the seed script runs automatically. Log in with the admin
credentials from `.env.production` (`ADMIN_EMAIL` / `ADMIN_PASSWORD`) and rotate the
password immediately.

Available seed personas (all password `GoOil@2026` in dev only — recreate in production):
- `admin@gooil.com` (super_admin)
- `company@gooil.com` (company_admin)
- `distributor@gooil.com` (distributor)
- `retailer@gooil.com` (retailer)
- `customer@gooil.com` (customer)

---

## 6 · Backups
Backups dump Mongo + config files as a single tarball.
```bash
./scripts/backup.sh /var/backups/gooil
```
Schedule via cron:
```
15 3 * * *   cd /opt/gooil && ./scripts/backup.sh /var/backups/gooil >> /var/log/gooil-backup.log 2>&1
```
Restore:
```bash
./scripts/restore.sh /var/backups/gooil/gooil-dms-backup-YYYYMMDD-HHMMSS.tar.gz
```

---

## 7 · Monitoring hooks
- **Uptime**: point your monitor (Uptime Kuma / Datadog synthetic) at `GET /api/health`
- **Log aggregation**: backend logs to stdout — pipe with a Fluent Bit / Loki sidecar
- **Metrics**: response times available via `docker compose logs backend` for now.
  Prometheus scraping can be added by mounting `prometheus_fastapi_instrumentator`.

---

## 8 · Scaling
- **Vertical**: add more workers to the backend by editing the `CMD` line in
  `Dockerfile.backend`. For an 8-core box, 4 workers is a good starting point.
- **Horizontal**: run multiple backend replicas behind a load balancer. Because our
  analytics micro-cache is in-process, expect a small cache-warm penalty on new replicas.
  Swap `cache_utils.TTLCache` for Redis to share cache.

---

## 9 · Kubernetes (optional)
A minimal set of manifests should include:
- `Deployment` × 2 (backend + frontend), matching probes:
  - `livenessProbe: httpGet /api/health` for backend, `/healthz` for frontend
  - `readinessProbe: httpGet /api/health` for backend
- `Service` × 2 (ClusterIP)
- `Ingress` routing `/api/*` → backend Service, everything else → frontend Service
- `Secret` holding env vars from `.env.production`
- Backups: replace the shell script with a `CronJob` running `mongodump` to S3.

---

## 10 · Post-deployment checklist
- [ ] JWT secret rotated to a fresh 48-char value
- [ ] Admin password rotated after first login
- [ ] `CORS_ORIGINS` set to explicit domains (no `*`)
- [ ] TLS enforced (redirect port 80 → 443)
- [ ] Mongo replica set / Atlas backups configured
- [ ] Backup cron scheduled + restore test performed once
- [ ] `EMERGENT_LLM_KEY` set if AI Copilot is desired
- [ ] Rate limiter storage switched to Redis if running >1 backend replica

Enterprise-ready.
