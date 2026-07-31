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

### Phase 7 · Coupon Security System + Excel Import/Export ✅
- Products now carry `coupons_per_box` (default 100) + `points_value` (default 10 pts) — editable per product; also imported/exported via Excel
- New collections:
  - `dms_coupons` — coupon_code (globally sequential CPN000001+), batch_id, product_id, assigned_distributor_id, assigned_on/ebill, status (unused/assigned/redeemed), redeemed_by_retailer_id, redeemed_at, points_value
  - `dms_coupon_batches` — one row per generation batch: product, count, start_code, end_code
  - `dms_coupon_fraud_attempts` — coupon_code, retailer, retailer_distributor, coupon_owner_distributor, reason (invalid_code / already_redeemed / not_dispatched / distributor_mismatch), at
- Endpoints (all under `/api/dms`):
  - `POST /owner/coupons/generate` — owner generates N unused coupons for a product (max 100k/batch)
  - `GET /owner/coupons` — filterable by status/product/distributor/retailer
  - `GET /owner/coupons/batches`
  - `GET /owner/coupons/reports/summary` — totals + by_distributor + by_retailer
  - `GET /owner/coupons/reports/fraud` — full fraud attempt log
  - `GET /owner/coupons/reports/history` — redemption history
  - `POST /retailer/coupons/scan` — validates in this exact order: valid code → not-redeemed → assigned → distributor-network match; on any failure logs a fraud attempt with the reason
  - `GET /retailer/coupons/my-history` — retailer's own redemptions + total points
- **Auto-assign on dispatch**: inside `mark_ready_to_go`, for each order line the system pulls next `qty_boxes × coupons_per_box` unused coupons (FIFO by created_at) for that product and stamps `assigned_distributor_id + assigned_on + status=assigned`. Shortfall (empty pool) is recorded in `ebill.coupons_assigned` without blocking dispatch
- **Frontend**:
  - Owner sidebar: **Coupons** (batches, KPIs, filterable list, Generate dialog) + **Coupon Reports** (Distributor/Retailer summary, Redemption history, Fraud attempts tabs)
  - Retailer sidebar: **Scan Coupon** — one-tap redeem UI with success/reject panel + running points balance + last 500 redemptions
- **Excel Import/Export for products**:
  - `GET /owner/products/export` → xlsx (sku, name, category, box_qty, hsn, gst, price, coupons_per_box, points_value, active)
  - `POST /owner/products/import` (multipart .xlsx) → upsert by sku_code; auto-creates missing categories; on price change closes old batch + opens new (same behaviour as PUT)
  - Products page toolbar: **Export** + **Import** buttons (owner-only)

## Backend regression: **Phase 7 = 13/13 passed** (Phase 1-6 previously 31/31)
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
