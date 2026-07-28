# GO OIL — Distribution Management System (DMS)

## Original problem statement
Build a COMPLETE enterprise-grade Distribution Management System (DMS) for GO OIL with 28 modules and 8 role-based dashboards. Premium industrial/luxury visual language, single-tenant multi-branch, JWT auth with role selection, rich seeded mock data, Claude Sonnet 4.5 AI Copilot.

## Architecture
- **Backend**: FastAPI + MongoDB (motor async). JWT auth with bcrypt hashing + httpOnly cookie fallback to Bearer header. `emergentintegrations` used for Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`).
- **Frontend**: React 19 + React Router 7 + Tailwind + shadcn/ui + Recharts + lucide-react. Manrope (display) + IBM Plex Sans (body). Reusable `AppShell` / `Sidebar` / `Topbar` / `DataTable` / `ModulePage` / `KpiCard` / `StatusPill` / `AiAssistant`.
- **Data**: Rich seeded mock data across every collection on startup (26 products, 75 SKUs, 60 batches, 6 warehouses, 120 inventory rows, 15 distributors, 40 retailers, 60 customers, 200 orders, 100 invoices, 90 dispatches, 60 GRNs, 80 payments, 150 ledger entries, 70 expenses, 50 cashback, 24 coupons, 30 approvals, 40 notifications).

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

Every role sees a role-adaptive KPI header (5 role-specific KPIs) and a role-filtered sidebar (see `/app/frontend/src/lib/nav.js`).

## Implemented (Feb 2026)
- ✅ JWT auth (login, register, logout, /me, /roles) with bcrypt + role guard
- ✅ 8 seeded role users + admin seeding on startup
- ✅ Rich seed data across 22 business collections
- ✅ Role-adaptive dashboard with KPIs, primary trend, status distribution, enterprise data grid, activity timeline, approvals queue
- ✅ 28 module pages routed under `/app/*` (Products, SKUs, Batches, Inventory, Warehouses, Distributors, Retailers, Customers, Primary Orders, Secondary Orders, Invoices, Dispatch, Goods In Transit, GRN, Payments, Ledger, Expenses, Cashback, Coupons, Reports, Analytics, Users, Roles, Master Data, Approvals, Notifications, AI Assistant, Settings)
- ✅ Reusable `DataTable` with search, filters, export, pagination, status pills, currency/date formatting
- ✅ Generic CRUD API `/api/collections/{resource}` (GET/POST/PUT/DELETE)
- ✅ AI Copilot (Claude Sonnet 4.5) via `/api/ai/ask` + right-side sheet + dedicated page
- ✅ Enterprise design language — Manrope + IBM Plex Sans, gold accents only, soft shadows, generous spacing
- ✅ Backend test suite (40/40 pytest) at `/app/backend/tests/backend_test.py`

## Prioritized backlog
### P1 — depth
- Deep entity pages (order detail, invoice PDF preview, distributor 360° view)
- Approval workflow engine with step-by-step routing
- Real inventory movement tracking (dispatch → GIT → GRN reconciliation)
- Advanced filters, saved views, bulk actions
- Notification bell UI with unread badge
- Kanban view for order fulfillment
- Charts on Analytics page (Recharts branch health / SKU revenue)
- Role-based write authorization on `/api/collections/*` mutations

### P2 — polish
- Dark mode
- Real-time updates via WebSocket
- CSV/PDF exports server-side
- Multi-currency
- Server-side pagination
- Import wizards for master data

## Next actions
- Deep-dive into any single module the user prioritizes
- Add role-based write guards (backend testing agent flagged as optional but recommended)
- Real-time WebSocket notifications
- E2E frontend Playwright testing per role
