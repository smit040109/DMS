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

## Update — Artwork-based Coupon Print Engine (official CDR/PDF template)
- Owner's approved CorelDRAW artwork (exported to PDF) is used VERBATIM as the master print template.
- Only dynamic fields are injected: Coupon Value (FRONT), secure v2 QR + Visible Serial (BACK). Artwork never redrawn.
- Assets: backend/assets/coupon_template/{coupon_front.png, coupon_back.png, fonts/, geometry.json, master_source.pdf}.
- Print spec: 12x18 inch paper, 35mm round die-cut, 77/sheet (7x11), auto sheet calc, FRONT+BACK (back mirrored for duplex), mixed values on one sheet.
- Endpoints: GET /api/dms/coupons/batches/{bid}/export-pdf?side=front|back|both ; POST /api/dms/coupons/print-mixed {batch_ids|coupon_ids|items,side}.
- QR stays secure v2 (GOOIL2|ciphertext|signature) — no UUID/secret/signature/db-ids exposed. Backend tested 24/24 pass.

## Update — Login fix + Coupon Box enhancements
- LOGIN FIX: frontend/.env REACT_APP_BACKEND_URL reset to EMPTY (same-origin /api via ingress).
  Added CRA dev "proxy":"http://localhost:8001" in package.json so /api also works on localhost dev.
  Resolves "Network error — is the server reachable?" on the preview URL. Verified by testing agent.
- Fraud Alerts: every fraud-flagged scan now writes an instant owner notification (kind=coupon_fraud,
  title "Fraud alert: <reason>", body = coupon + GPS/IP location, link=/dms/owner/coupons/fraud),
  in the notification-bell schema (recipient_id + created_at).
- Box Label PDF: GET /api/dms/coupons/boxes/{bid}/label-pdf — printable A4 label with big Box Number,
  serial range, distributor, status, date + Code128 barcode. "Label" button on each box row.
- Box Scan History: GET /api/dms/coupons/boxes/{bid}/scan-history — claimed coupons with retailer,
  claimed-by, timestamp and GPS/IP. "History" button opens a dialog on the Box Management page.
- Box Dashboard card: GET /api/dms/coupons/boxes/stats — boxes created/assigned/coupons-in-boxes/claimed;
  shown as a "Coupon Boxes" summary card on the Owner Dashboard.
- Backend 22/23 passed; frontend 4/4 flows passed. Coupon print artwork/engine unchanged.

## Update — Owner-managed logins + full-process onboarding (Aug'26)
- LOGIN: Owner = gooilindia13@gmail.com / Arjun@india13 (from OWNER_EMAIL/OWNER_PASSWORD env). Public
  self-registration DISABLED (/api/auth/register → 403). All other roles log in only with credentials
  the owner creates in-app.
- ONBOARDING: Distributor login is created ONLY after ALL details + KYC + >=1 document. Retailer login
  (when an email is provided) also requires region/gstin/shop_license/password + >=1 document. Enforced
  in backend (create_distributor, create_retailer) AND frontend form validation with clear messages.
- QUICK-CREATE: Owner "New User" panel can no longer create bare distributor/retailer logins
  (OWNER_MANAGEABLE_ROLES excludes them); backend returns 400.
- EDIT: Owner can edit any user's name / phone / login email — including the owner's own account —
  via PATCH /api/dms/owner/users/{uid} and the new Edit dialog on User Management.
- SEED SAFETY: Exactly one owner (matched by role, not just email) + unique index on users.email so
  restarts/redeploys never duplicate the owner. Backend verified 15/15.
