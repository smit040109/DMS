# Bharat Oil DMS — Simple Distribution Management System

## Current State
Reset from the heavy multi-tenant VayuERP to a **simple, minimum-clicks DMS** built around two workflows:
1. **Primary Sales** — Owner ↔ Distributor
2. **Secondary Sales** — Distributor ↔ Retailer

All money in **INR**, 10 demo users (password `Demo@2026`), mobile-responsive teal/amber brand, in-app notifications.

## Delivered Phases (Owner Enhancements v2 — this sprint)

### Phase 1 · User Management + Impersonation ✅
### Phase 2 · Geo fields + Salesperson GPS pings (60s) ✅
### Phase 3 · Owner Live Map (Leaflet + OSM) ✅
### Phase 4 · Team Leader Module ✅
- `/dms/dashboard/team-leader` — 9 KPIs (today/monthly sales, orders, pending, fulfillment %, assigned dists/SPs, retailers, stock alerts)
- `/dms/tl/distributors` — per-distributor: stock, payable to owner, receivable, today/monthly sales, revenue, pending
- `/dms/tl/salespersons` — online/offline, punch in/out, live location, today visits, orders, new retailers
- `/dms/tl/orders` — filterable by status/distributor/salesperson/retailer
- `/dms/tl/retailers` — outstanding, last order, total purchases, GPS
- `/dms/tl/attendance` + `/tl/punch/in` + `/tl/punch/out`
- Frontend pages: TlDashboard, TlDistributorsMonitoring, TlSalespersons (with "Assign to Distributor"), TlOrdersMonitoring, TlRetailers, TlAttendance, LiveTracking (shared)

### Phase 4 add-on · Owner Insights ✅
- `/dms/owner/tl-performance` — TL ranking w/ total, monthly, today sales + 7-day sparkline
- `/dms/owner/distributor-sales/{did}` — drilldown by retailer / by product (qty boxes+pcs, prices seen, revenue) + recent 30 orders
- Frontend pages: OwnerTlPerformancePage (ranking cards + comparison table), OwnerDistributorSalesListPage → OwnerDistributorSalesDetailPage

### Phase 5 · Regional Manager Module ✅
- `/dms/dashboard/regional-manager` — 9 KPIs (TLs, dists, retailers, SPs, today/monthly sales, outstanding, revenue, fulfillment %)
- `/dms/rm/team-leaders` — ranked TL list
- `/dms/rm/distributors` — read-only
- `/dms/rm/salespersons` — read-only w/ live status
- `/dms/rm/region-performance` — dist-wise, TL-wise, SP-wise sales
- Frontend pages: RmDashboard, RmTeamLeaders, RmRegionPerformance, RmDistributors, RmSalespersons + LiveTracking

### Phase 6 · Ordering UX (Distributor + Retailer) ✅
- Two-step flow: Category tile grid → Product cards with big +/- buttons
- Old (strike-through) + New price displayed side-by-side with "Price ↑" tag when changed
- Sticky footer with `USING NEW PRICE` label — subtotal + GST + total all calculated with new price
- Same treatment in both DistributorBrowsePage and RetailerBrowsePage (box + pcs when applicable)

## Backend regression: 31/31 tests passed (verified by deep_testing_backend_v2)

## Architecture recap
- Backend: FastAPI + Motor (Mongo). Tenant-scoped wrapper auto-injects `tenant_id: tnt-dms-oil` on every read/write.
- Frontend: React 19 + CRA + react-leaflet 5 + Tailwind + shadcn/ui + sonner toasts.
- Auth: JWT (sub, email, role, tenant_id). `AuthContext` stores token in localStorage + cookie.
- Same-origin API calls via ingress `/api/*` — `REACT_APP_BACKEND_URL` is empty so any preview hostname works.

## Demo credentials (all password `Demo@2026`)
- owner@dms.com (Company Owner), acct@dms.com (Owner Accountant)
- dist1@dms.com, dist2@dms.com (Distributors), distacct@dms.com (Distributor Accountant)
- retailer1@dms.com, retailer2@dms.com (Retailers)
- sales@dms.com (Salesperson), tl@dms.com (Team Leader), rm@dms.com (Regional Manager)
