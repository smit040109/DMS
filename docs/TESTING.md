# GO OIL DMS — Testing Guide

**Version 5.0-enterprise**

---

## 1 · Categories
- **Unit** — pure logic (pricing, discount, ledger balance) — `pytest`
- **Integration** — router → Mongo round-trips — `pytest` with fixtures
- **Regression / E2E** — full user flows — `deep_testing_backend_v2` + `auto_frontend_testing_agent`
- **Load** — response times under concurrent users — locust (not shipped, sample below)
- **Security** — rate limit, RBAC, headers — covered by regression + manual `curl`

---

## 2 · Running unit + integration
```bash
cd /app
pytest -q backend/tests/
```
Fixtures should seed to a **separate** DB (`DB_NAME=go_oil_test`) and drop it after.

---

## 3 · Full regression sweep (~5-10 min)
```
Backend testing agent:  covers all 5 routers + exports + notifications + copilot + integrations
Frontend testing agent: logs in as each persona, walks Phase 1-4 pages, exports, mobile drawer
```
Both drop findings back to `/app/test_result.md`.

---

## 4 · Critical smoke tests (manual)
```bash
# health
curl -fs $BASE/api/health

# login all 8 personas
for e in admin company regional sales distributor accountant retailer customer; do
  curl -s -X POST $BASE/api/auth/login -H 'Content-Type: application/json' \
       -d "{\"email\":\"${e}@gooil.com\",\"password\":\"GoOil@2026\"}" | grep -q token && echo "$e OK"
done

# executive KPIs
curl -s -H "Authorization: Bearer $TOKEN" $BASE/api/analytics/kpi/executive?range=month | jq '.kpis | keys | length'

# 4 export formats
for fmt in csv xlsx pdf print; do
  curl -so /tmp/o.$fmt -w "$fmt %{http_code} %{size_download}\n" \
       -H "Authorization: Bearer $TOKEN" \
       "$BASE/api/exports/invoices?format=$fmt"
done

# exception scan (must be 200 with no ObjectId leak)
curl -s -H "Authorization: Bearer $TOKEN" -X POST $BASE/api/reverse/exceptions/scan | jq '.found'
```

---

## 5 · Performance targets (v5.0)
| Endpoint bracket | Cold | Warm |
|---|---|---|
| Master data lists | <150ms | <120ms |
| Analytics dimensions | <200ms | <130ms |
| Scorecards | <300ms | <150ms |
| Executive KPI | <500ms | <300ms |
| Exports 1k rows (csv/xlsx) | <800ms | — |
| PDF export 500 rows | <1500ms | — |

Investigate any endpoint > 1s.

---

## 6 · Security tests (manual)
```bash
# rate limit — 11 rapid logins should include at least one 429
for i in $(seq 1 12); do
  curl -so /dev/null -w "%{http_code} " -X POST $BASE/api/auth/login \
       -H 'Content-Type: application/json' -d '{"email":"x@x.com","password":"x"}'
done ; echo

# customer forbidden from admin
curl -s -H "Authorization: Bearer $CUST" -w " %{http_code}\n" $BASE/api/admin/users

# no ObjectId leaks — should print 0
curl -s -H "Authorization: Bearer $TOKEN" $BASE/api/collections/invoices | grep -c '"_id"'
```

---

## 7 · Mobile / responsive
Playwright at 375×812 (iPhone-ish) — hamburger, drawer, dashboard KPI grid, table
horizontal scroll. Screenshot artefacts land in `/tmp/`.

---

## 8 · Load testing (sample)
```python
# locustfile.py
from locust import HttpUser, task, between
class DmsUser(HttpUser):
    wait_time = between(0.5, 2)
    def on_start(self):
        r = self.client.post("/api/auth/login", json={"email":"admin@gooil.com","password":"GoOil@2026"})
        self.token = r.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    @task(3)
    def kpi(self): self.client.get("/api/analytics/kpi/executive?range=month", headers=self.headers)
    @task(2)
    def dimensions(self): self.client.get("/api/analytics/dimensions", headers=self.headers)
    @task
    def alerts(self): self.client.get("/api/analytics/alerts", headers=self.headers)
```
Run: `locust -f locustfile.py --headless -u 50 -r 5 --run-time 3m --host $BASE`

---

## 9 · Data-integrity assertions
Every night:
- `sum(dr) == sum(cr)` per `reference_id` in `double_ledger`
- Every SKU: sum of six inventory buckets == `total_received`
- `outstanding.current_balance` == `Σ(dr − cr)` for that party

The exception scanner surfaces violations automatically. Add these to a nightly Grafana alert.
