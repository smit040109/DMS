# GO OIL — Distribution Management System (DMS)

## Original problem statement
Build a COMPLETE enterprise-grade DMS with 28 modules and 8 role-based dashboards. Phase 1 must implement the FULL end-to-end business engine from Product creation to Retailer Inventory, where every transaction cascades through: stock movements, inventory buckets, ledger entries and workflow status transitions.

## Architecture
- **Backend**: FastAPI + MongoDB with a **workflow engine** (`/app/backend/workflow.py`) enforcing state transitions, FIFO batch consumption, stock ledger writes and cascading updates. JWT auth. AI Copilot via `emergentintegrations` + Claude Sonnet 4.5.
- **Frontend**: React + shadcn/ui. Reusable `AppShell`, `DataTable`, `ModulePage`, `WorkflowActions` (row-level action buttons with dialogs).

## Data model (Phase 1)
Collections:
- **Reference**: `branches`, `roles`, `users`, `products`, `skus`, `distributors`, `retailers`, `customers`, `warehouses`, `master_data`
- **Transactional (workflow-driven)**: `batches`, `company_inventory`, `distributor_inventory`, `retailer_inventory`, `primary_orders`, `secondary_orders`, `invoices`, `dispatches`, `grns`, `stock_ledger`
- **Inventory bucket schema** (per SKU + Batch + Partner): `{available, reserved, in_transit, damaged, returned, expired}`

## Phase 1 workflow engine — proven end-to-end
`Batch (create)` → `Stock In` → `Company Inventory (available)` → `Primary Order (validate stock + credit)` → `Approve (FIFO reserve)` → `Auto-Invoice` → `Dispatch (dialog: vehicle/driver/LR)` → `Goods In Transit (reserved → in_transit)` → `Receive GRN (in_transit → distributor available)` → `Distributor Inventory` → `Secondary Order (retailer)` → `Approve (reserve distributor stock)` → `Auto-Invoice` → `Dispatch to Retailer` → `Retailer GRN` → `Retailer Inventory (available)`.

Every step:
1. Validates state transition + business rules (stock availability, credit limit)
2. Moves qty between buckets (available/reserved/in_transit/damaged etc.)
3. Appends an immutable `stock_ledger` row
4. Cascades status on the linked entities (order → invoice → dispatch → GRN)

Endpoints under `/api/workflow/*`:
- `POST /workflow/batches`, `POST /workflow/batches/{id}/stock-in`
- `POST /workflow/primary-orders`, `POST /workflow/primary-orders/{id}/approve|reject`
- `POST /workflow/primary-invoices/generate/{order_id}`
- `POST /workflow/invoices/{id}/dispatch`
- `POST /workflow/dispatches/{id}/receive`
- `POST /workflow/secondary-orders`, `POST /workflow/secondary-orders/{id}/approve|reject`
- `POST /workflow/secondary-invoices/generate/{order_id}`
- `GET  /workflow/inventory/company | /distributor/{id} | /retailer/{id}`
- `GET  /workflow/stock-ledger?sku_id&scope&reference_id`
- `GET  /workflow/order/{id}/trace` — full linked trail

## Personas / Roles (all password `GoOil@2026`)
| Role | Email |
|------|-------|
| Super Admin | admin@gooil.com |
| Company Admin | company@gooil.com |
| Regional Manager | regional@gooil.com |
| Sales Executive | sales@gooil.com |
| Distributor | distributor@gooil.com |
| Distributor Accountant | accountant@gooil.com |
| Retailer | retailer@gooil.com |
| Customer | customer@gooil.com |

## Implemented (Feb 2026)
### v1.0 — App shell
- JWT auth, 8 seeded role users, role-adaptive sidebar + dashboard
- 28 module pages
- AI Copilot (Claude Sonnet 4.5)
- Enterprise design system (Manrope + IBM Plex Sans, gold #C9A227 accent, soft shadows)

### v2.0 — Phase 1 workflow engine ✅ NEW
- Full workflow engine at `backend/workflow.py` (~600 lines)
- FIFO batch consumption enforced at reservation time
- Stock ledger — immutable log of every movement, filterable by scope (company/distributor/retailer)
- 3 real inventory views (Company / Distributor / Retailer) with bucket distribution bar
- `Stock Ledger` page with movement-type badges
- `WorkflowActions` component: Stock-In on batches; Approve/Reject on orders; Dispatch dialog on invoices; Receive on dispatches
- Seeded transactional chain — 60 batches, 24 primary orders (spread across pending/approved/invoiced/dispatched/completed/rejected), 9 secondary orders producing retailer inventory
- Insufficient-stock and credit-limit validation on order creation
- `/api/workflow/order/{id}/trace` — end-to-end audit trail per order

## Prioritized backlog
### P1 — depth
- Order & Invoice detail drill-down pages with linked entities (invoice ↔ dispatch ↔ GRN)
- Distributor onboarding wizard (multi-step KYC → credit → warehouse assignment)
- Payments & Ledger wiring (Phase 2 — invoice payment → outstanding reduction → double-entry ledger)
- Cashback & Coupon runtime engine (Phase 2)
- Full audit-log page (who, what, when, why) tied to `stock_ledger` + auth events

### P2 — polish
- Server-side pagination for very large ledgers
- Expiry auto-scan (nightly) → move expired stock buckets
- CSV/PDF report exports
- Real-time WebSocket for status changes

## Next actions
- Phase 2: Payments → Ledger → Cashback → Coupon runtime engine
- Deep entity pages with cross-entity trace visualisation
- Server-side authorization on write endpoints (role guards on `/workflow/*/approve` etc.)
