# GO OIL DMS — API Documentation

**Base URL:** `${REACT_APP_BACKEND_URL}/api`
**Auth:** `Authorization: Bearer <JWT>` on every endpoint except `/auth/login`, `/auth/register`, `/health`.
**Rate limits:** `/auth/login` 10/min, `/auth/register` 5/min per IP.

For a machine-readable OpenAPI spec, browse `${BACKEND_URL}/docs` (Swagger UI shipped by FastAPI).

---

## Auth

### POST `/auth/login`
```json
{ "email": "admin@gooil.com", "password": "GoOil@2026" }
```
Returns `{ user: {...}, token: "<jwt>" }`. Sets `access_token` HTTP-only cookie.

### POST `/auth/register`
`{ email, password (≥8 + 1 upper + 1 digit), name, role }`

### GET `/auth/me` · POST `/auth/refresh` · POST `/auth/logout`

---

## Collections (generic CRUD)

- `GET /collections/{resource}` — list any resource; supports `?q`, `?limit`, `?sort`, `?filter[key]=value`
- `POST /collections/{resource}` **(admin only)**
- `PUT /collections/{resource}/{id}` **(admin only)**
- `DELETE /collections/{resource}/{id}` **(admin only)**

Available resources: `products`, `skus`, `batches`, `distributors`, `retailers`, `customers`, `warehouses`, `expenses`.

---

## Phase 1 — Operational Workflow (`/workflow/*`)
- `POST /workflow/batches` — create batch
- `POST /workflow/stock-in` — receipt into company inventory
- `POST /workflow/primary-orders` · `PATCH /primary-orders/{id}/approve|reject|cancel`
- `POST /workflow/dispatches` — dispatch approved order
- `POST /workflow/grns` — receive at distributor
- `POST /workflow/secondary-orders` — distributor → retailer
- `POST /workflow/retailer-inventory/adjust`
- `GET /workflow/stock-ledger?sku_id=&limit=`

---

## Phase 2 — Financial Engine (`/finance/*`)
- `POST /finance/payments` — record payment (Cash/UPI/Bank/Cheque) with auto-allocation
- `POST /finance/payments/{id}/reverse`
- `GET /finance/outstanding?party_type=&party_id=`
- `GET /finance/ledger?party_id=&account=`
- `POST /finance/coupons/create` · `POST /finance/coupons/validate` · `POST /finance/coupons/apply`
- `POST /finance/cashback/compute` · `POST /finance/cashback/{id}/approve`
- `POST /finance/customer-orders` · full lifecycle endpoints
- `GET /finance/wallets/{party_type}/{party_id}`
- `POST /finance/reconciliation/run`
- `GET /finance/audit-log?entity_id=&limit=`

Journal invariant: for every `reference_id`, `sum(dr) == sum(cr)`.

---

## Phase 3 — Reverse Logistics (`/reverse/*`)
- Returns: `POST /reverse/returns` · `PATCH /returns/{id}/approve` · `PATCH /returns/{id}/reject`
- Damage: `POST /reverse/damage`
- Claims: `POST /reverse/claims` · `PATCH /claims/{id}/approve|settle`
- Credit/Debit notes: `POST /reverse/credit-notes` · `POST /reverse/debit-notes`
- Replacements: `POST /reverse/replacements`
- Expiry: `GET /reverse/expiry?days=30` · `POST /reverse/expiry/{id}/action`
- Approval matrix: `GET /reverse/approval-matrix` · `POST /reverse/approvals/{id}/decide`
- Exceptions: `POST /reverse/exceptions/scan` · `GET /reverse/exceptions`
- Reports: `GET /reverse/reports/{returns|damage|claims|credit_notes|debit_notes|expiry|replacements|approvals|audit}`

---

## Phase 4 — Business Intelligence (`/analytics/*`)
- `GET /analytics/dimensions` (cached 60s)
- `GET /analytics/kpi/executive?range=today|yesterday|week|month|quarter|year|custom&from=&to=&branch_id=&distributor_id=&retailer_id=&sku_id=`
- `GET /analytics/trace/order/{id}` — 20-node timeline
- `GET /analytics/trace/search?q=`
- `GET /analytics/party360/{distributor|retailer|customer|company}/{id}`
- `GET /analytics/sales`, `/inventory`, `/finance`, `/returns`, `/claims`, `/profitability`
- `GET /analytics/alerts`
- `GET /analytics/scorecards/{distributor|retailer|branch|sales_executive|warehouse|company}` (cached 45s)
- `GET /analytics/ai-context/{executive|sales|finance|inventory}`

---

## Notifications (`/notifications/*`) — Part E
- `GET /notifications?limit=&unread_only=&category=`
- `GET /notifications/unread-count`
- `POST /notifications/mark-read/{id}` · `POST /notifications/mark-all-read` · `DELETE /notifications/{id}`
- `GET /notifications/preferences` · `PUT /notifications/preferences`
- `POST /notifications/send` (self / admin) · `POST /notifications/trigger/{event}` (admin QA)

Events pre-wired for `trigger/*`: `approval_pending`, `low_stock`, `expiry_warning`,
`payment_received`, `invoice_created`, `claim_settled`.

---

## AI Business Copilot (`/ai/copilot/*`) — Part F
- `GET /ai/copilot/status`
- `GET /ai/copilot/suggestions`
- `POST /ai/copilot/ask` body `{ question, session_id?, provider?, model? }`
- `GET /ai/copilot/sessions/{id}` · `DELETE /ai/copilot/sessions/{id}`

Response: `{ session_id, answer, sources: [{endpoint, key_numbers}], intent, model, usage, generated_at }`.
Returns `503` with a helpful message if `EMERGENT_LLM_KEY` is not set.

---

## Exports (`/exports/*`) — Part D
- `GET /exports/collections` — list of 35 exportable resources
- `GET /exports/{resource}?format=csv|xlsx|pdf|print&limit=`
- `POST /exports/render` body `{ rows, columns?, format, title?, subtitle? }` — arbitrary data

Content-types:
- csv → `text/csv` (UTF-8 BOM for Excel compatibility)
- xlsx → `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- pdf → `application/pdf`
- print/html → `text/html`

---

## Integrations (`/integrations/*`) — Part G
- `GET /integrations/status` — which providers configured vs scaffolded
- Payments: `POST /payments/create-order|verify|refund` (Razorpay + Stripe)
- Tax: `GET /tax/validate-gstin?gstin=` · `POST /tax/gstr1-preview`
- Accounting: `GET /accounting/tally-export` — downloads Tally XML voucher import
- Codes: `GET /code/generate?kind=qr|barcode&value=` · `GET /code/lookup?code=`
- Import: `POST /import/excel?collection=products|skus|distributors|retailers|customers` (multipart file)
- Webhooks: `POST /webhooks/emit` (outbound) · `POST /webhooks/inbox` (inbound receiver)
- `GET /integrations/public/health` — public probe

---

## Miscellaneous
- `GET /health` — public liveness probe `{ "status": "ok", "db": "connected" }`
- `GET /admin/users` (admin only)
- `GET /` — service badge

---

## Error envelope
All errors follow FastAPI's `{ "detail": "<message>" }` shape. HTTP codes used:
- `400` — invalid input
- `401` — missing/expired token
- `403` — RBAC denial
- `404` — record not found
- `422` — validation error
- `429` — rate-limit exceeded
- `500` — unexpected server error
- `503` — dependency unavailable (Mongo down, EMERGENT_LLM_KEY missing)

Every response includes security headers set by `SecurityHeadersMiddleware`.
