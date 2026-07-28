# GO OIL DMS — Architecture

**Version 5.0-enterprise**

---

## 1 · High-level

```
                ┌──────────────────────────────┐
                │  Users (browsers, mobile)    │
                └──────────────┬───────────────┘
                               │ HTTPS
                    ┌──────────▼─────────┐
                    │  Reverse Proxy /   │
                    │  Kubernetes Ingress│
                    └────┬───────────┬───┘
                    /*  │           │  /api/*
                        ▼           ▼
              ┌────────────────┐  ┌────────────────┐
              │  Frontend      │  │  Backend       │
              │  (Nginx SPA)   │  │  (FastAPI)     │
              └────────────────┘  └────────┬───────┘
                                            │ Motor async driver
                                            ▼
                                   ┌────────────────┐
                                   │  MongoDB       │
                                   └────────────────┘

     side-of-cars:
       - Emergent LLM (OpenAI/Claude/Gemini) — AI Copilot
       - Razorpay / Stripe                    — Payments (scaffolded)
       - SendGrid / SMTP                       — Email     (scaffolded)
       - Twilio / MSG91                        — SMS/WA    (scaffolded)
       - GSTN API                              — Tax       (scaffolded)
       - Tally XML listener                    — Accounting (scaffolded)
```

---

## 2 · Backend module map

| Router | Prefix | Responsibility |
|---|---|---|
| `server.py` | `/api` (+ auth) | Bootstrap, auth, generic `/collections/*` CRUD, health, master data |
| `workflow.py` | `/api/workflow` | **Phase 1** — batches, primary/secondary orders, dispatch, GIT, GRN |
| `finance.py` | `/api/finance` | **Phase 2** — payments, outstanding, double-entry ledger, cashback, coupons |
| `reverse.py` | `/api/reverse` | **Phase 3** — returns, damage, claims, CN/DN, replacements, expiry, exceptions |
| `analytics.py` | `/api/analytics` | **Phase 4** — dimensions, KPIs, order trace, party360, alerts, scorecards, AI context |
| `notifications.py` | `/api/notifications` | **Part E** — in-app + email/wa/sms scaffold bus, preferences |
| `ai_copilot.py` | `/api/ai/copilot` | **Part F** — business analyst LLM assistant |
| `integrations.py` | `/api/integrations` | **Part G** — payment/tax/tally/QR/import/webhook scaffolds |
| `exports.py` | `/api/exports` | **Part D** — CSV/XLSX/PDF/Print for every collection |
| `security.py` | (middleware) | **Part C** — rate limiter, security headers, RBAC guards |
| `cache_utils.py` | (helper) | **Part B** — TTL micro-cache for analytics |

Each router follows the same **factory pattern**:
```python
def build_X_router(db, get_current_user, …) -> APIRouter:
    router = APIRouter(prefix="/X", tags=["X"])
    ...
    return router
```
This keeps them stateless and swap-in-testable.

---

## 3 · Frontend module map

- **Route layer** (`App.js`) — 6 lazy chunks split by domain: `list`, `admin`, `inventory`,
  `finance`, `reverse`, `analytics`. Initial JS only carries AppShell + Dashboard.
- **AppShell** (`components/layout/AppShell.jsx`) — 2-column layout with sidebar drawer
  on mobile, sticky Topbar, Suspense fallback for lazy chunks.
- **DataTable** (`components/common/DataTable.jsx`) — search, filters, export menu, pagination.
- **ExportMenu** (`components/common/ExportMenu.jsx`) — 4-format dropdown; either exports
  the current row-set via `POST /exports/render` or the full server-side collection via
  `GET /exports/{resource}`.
- **NotificationBell** — polls `/notifications/unread-count` every 30s, dropdown with
  mark-read + dismiss + deep-link into entities.
- **AiAssistant** — chats with `/ai/copilot/ask`, shows sources + intent + model, session
  persisted in `sessionStorage`.

---

## 4 · Data flow — Sales order lifecycle

```
[Retailer creates Primary Order]
        │  POST /workflow/primary-orders
        ▼
   primary_orders (status=draft)
        │  POST /workflow/primary-orders/{id}/approve
        ▼   reserves stock (FIFO) from company_inventory
   primary_orders (approved) ─ writes stock_ledger + creates invoice
        │  POST /workflow/dispatches
        ▼
   dispatches (in_transit) ─ writes stock_ledger (in_transit bucket)
        │  POST /workflow/grns
        ▼
   grns (received) ─ writes stock_ledger + distributor_inventory + double_ledger (Sales Dr AR / Cr Sales)
        │
        ▼
   distributor sees stock, invoices, and outstanding balance
```

Double-entry ledger invariant: `sum(dr) == sum(cr)` for every `reference_id`.

---

## 5 · Bucket accounting invariants

Every SKU/batch is tracked across six buckets:
```
available + reserved + in_transit + damaged + returned + expired == total_received
```
This is enforced at write time in `workflow.py` and `reverse.py`. `stock_ledger` records
every transition with `from_bucket / to_bucket` fields.

---

## 6 · Caching strategy

- **Analytics micro-cache** — in-process TTL (30/45/60s) for `/dimensions` and
  `/scorecards/{type}`. Traded staleness for very fast dashboards. Swap for Redis if
  scaling to > 1 backend replica.
- **HTTP layer** — long immutable cache on hashed static assets; no cache on `/api/*`.

---

## 7 · Security posture

- JWT (HS256) 12-hour access token, HTTP-only cookie + Authorization header (frontend
  uses header primarily).
- bcrypt password hashing (12 rounds).
- Rate-limited auth endpoints (`10/min` login, `5/min` register), per-IP.
- Security headers on every response: `X-Content-Type-Options`, `X-Frame-Options: DENY`,
  `Referrer-Policy`, `Permissions-Policy`.
- CORS from env (`*` in dev only).
- RBAC role hierarchy in `security.py` — `super_admin` ⊇ everything.

---

## 8 · Scale-out plan

| Phase | Change |
|---|---|
| 1 (up to ~50 concurrent) | Single backend container, 2 workers. Current sizing. |
| 2 (up to ~500 concurrent) | Backend replicaCount=3, share micro-cache via Redis, MongoDB replica set. |
| 3 (multi-tenant SaaS) | Split routers by domain into services, add API gateway, Kafka event bus, S3 for exports > 5 MB. |

---

Draw diagrams with e.g. `structurizr` once you break out routers into services.
