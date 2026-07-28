# GO OIL DMS — Developer Guide

**Version 5.0-enterprise · July 2025**

---

## 1 · Project Layout
```
/app
├── backend/                    FastAPI monolith
│   ├── server.py               entry point + auth + collections CRUD + startup wiring
│   ├── workflow.py             Phase 1 — batches → orders → GRN
│   ├── finance.py              Phase 2 — payments / ledger / cashback / coupons
│   ├── reverse.py              Phase 3 — returns / claims / credit-debit notes
│   ├── analytics.py            Phase 4 — executive KPIs / party360 / scorecards
│   ├── notifications.py        Part E — provider-agnostic notification bus
│   ├── ai_copilot.py           Part F — business analyst LLM copilot
│   ├── integrations.py         Part G — Razorpay/Stripe/GST/Tally/QR scaffolds
│   ├── exports.py              Part D — CSV/XLSX/PDF/Print engine
│   ├── security.py             Part C — rate limit + RBAC + headers + env validation
│   ├── cache_utils.py          Part B — TTL micro-cache
│   ├── seed_data.py            master data seed
│   ├── seed_workflow.py        Phase 1-4 sample-data seed
│   └── requirements.txt
├── frontend/                   React 19 SPA (CRA)
│   ├── src/
│   │   ├── App.js              route-level lazy loading (6 chunks)
│   │   ├── components/
│   │   │   ├── layout/         AppShell + Sidebar (mobile drawer) + Topbar
│   │   │   ├── ai/             AiAssistant drawer
│   │   │   ├── common/         DataTable, ExportMenu, NotificationBell, KpiCard, ...
│   │   │   └── ui/             shadcn primitives
│   │   ├── pages/
│   │   │   ├── modules/        Grouped page bundles (List/Inventory/Finance/Reverse/Analytics/Admin)
│   │   │   ├── Dashboard.jsx
│   │   │   └── Login.jsx
│   │   ├── context/AuthContext.jsx
│   │   └── lib/api.js
│   └── package.json
├── Dockerfile.backend / Dockerfile.frontend / docker-compose.yml / nginx.conf
├── docs/                       DEPLOYMENT.md, ARCHITECTURE.md, API.md, ROLE_MATRIX.md,
│                                SCHEMA.md, WORKFLOWS.md, TESTING.md, ADMIN.md
└── memory/                     PRD.md, test_credentials.md
```

---

## 2 · Local Development
```bash
# Backend
cd /app/backend
pip install -r requirements.txt
# .env must contain MONGO_URL, DB_NAME, JWT_SECRET

# Frontend
cd /app/frontend
yarn install
```
Supervisor is preconfigured; the app auto-starts via:
```bash
sudo supervisorctl restart all
```

Backend hot-reloads on file save (uvicorn `--reload`). Frontend hot-reloads via CRA.

---

## 3 · Coding Rules
1. **URLs / ports never hardcoded**. Backend must read `MONGO_URL`; frontend must read
   `REACT_APP_BACKEND_URL`.
2. **All backend routes prefixed with `/api`** (Kubernetes ingress rule).
3. **UUIDs, never Mongo `ObjectId`** — every doc has an `id: "sku-1234abcd"` string;
   we `strip _id` before returning. Use `strip_id()` helpers or projection `{"_id": 0}`.
4. **Business logic in routers**, not in React. React only orchestrates + displays.
5. **RBAC**: sensitive mutations use `require_admin_role` / `require_finance_role` /
   `require_ops_role` from `security.py`.
6. **New endpoints** must have (a) auth via `Depends(get_current_user)`, (b) input
   validation via Pydantic, (c) an entry in `docs/API.md`, (d) at least one seed record
   or unit test path if it's writeable.
7. **Money in stored records is always `float` (₦)** — display formatting only in UI.
8. **Timestamps** are ISO-8601 UTC strings (`datetime.now(timezone.utc).isoformat()`).

---

## 4 · Adding a New Module
1. Extend `seed_data.py` and/or `seed_workflow.py` with the new collection.
2. Add a router in a new file `backend/<name>.py`:
   ```python
   def build_<name>_router(db, get_current_user):
       router = APIRouter(prefix="/<name>", tags=["<name>"])
       # endpoints…
       return router
   ```
3. Wire it in `server.py` — `include_router(build_<name>_router(...))`.
4. Add MongoDB indexes for hot query paths in `seed_all()` at the top of `server.py`.
5. Register RBAC where necessary.
6. Frontend: put page components in an existing module file inside `pages/modules/`
   and register the path in `App.js`'s route array.
7. Add nav entry in `lib/nav.js`.

---

## 5 · Running Tests
```bash
cd /app
pytest backend/tests/       # unit + integration
```
For end-to-end regression, the platform has two testing subagents:
- `deep_testing_backend_v2` — REST regression across all routers
- `auto_frontend_testing_agent` — Playwright browser tests

See `docs/TESTING.md`.

---

## 6 · Environment Variables (backend)
| Var | Default | Purpose |
|---|---|---|
| `MONGO_URL` | — | Mongo connection string (required) |
| `DB_NAME` | — | Database name (required) |
| `JWT_SECRET` | — | ≥ 32 chars (required) |
| `CORS_ORIGINS` | `*` | Comma-separated |
| `EMERGENT_LLM_KEY` | — | Enables AI Copilot |
| `AI_PROVIDER` / `AI_MODEL` | `openai` / `gpt-5.4` | LLM selection |
| `ENABLE_HSTS` | `false` | Enable HSTS response header |
| `PAYMENT_PROVIDER`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `STRIPE_SECRET_KEY` | scaffold | Payments |
| `EMAIL_PROVIDER`, `SENDGRID_API_KEY`, `EMAIL_FROM` | scaffold | Email |
| `WHATSAPP_PROVIDER`, `SMS_PROVIDER`, `GSTN_API_KEY`, `COMPANY_GSTIN` | scaffold | Other |

---

## 7 · Directory Deep-Dives
- `docs/ARCHITECTURE.md` — module boundaries, data flow, sequence diagrams
- `docs/API.md` — every endpoint with request/response shape
- `docs/SCHEMA.md` — Mongo collections and index catalogue
- `docs/WORKFLOWS.md` — end-to-end operational scenarios
- `docs/ROLE_MATRIX.md` — RBAC matrix
- `docs/DEPLOYMENT.md` — production deploy
- `docs/TESTING.md` — QA procedures
- `docs/ADMIN.md` — operator runbook

Happy shipping.
