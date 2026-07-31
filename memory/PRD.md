# Bharat Oil DMS — Simple Distribution Management System

## Current State
Reset from the heavy multi-tenant VayuERP to a **simple, minimum-clicks DMS** built around two workflows:
1. **Primary Sales** — Owner ↔ Distributor
2. **Secondary Sales** — Distributor ↔ Retailer

All money in **INR**, 10 demo users (password `Demo@2026`), mobile-responsive teal/amber brand, in-app notifications.

## Delivered Phases (Latest Sprint — Owner Enhancements v1)

### Phase 1 · User Management + Impersonation ✅
- `POST/GET/PATCH /api/dms/owner/users` — owner creates and lists all system users
- `POST /api/dms/owner/users/{uid}/reset-password` — owner can reset any password
- `POST /api/dms/owner/impersonate/{uid}` — owner logs in as any user (except other owners)
- Frontend page `/dms/owner/users` — filterable table with Name, Role, Login ID, Online/Offline status, Last Login, Reset + Login-As per row
- `AuthContext.startImpersonation()` / `exitImpersonation()` — saves original owner token in localStorage under `go_oil_impersonation` and restores on Exit
- Amber `ImpersonationBanner` at the top of DmsShell shows "Logged in as X — originally Owner" with an Exit button

### Phase 2 · Geo fields + Salesperson GPS pings ✅
- `dms_distributors` + `dms_retailers` now carry `gps_lat`, `gps_lng`, `location_link`
- Create/edit dialogs (Owner Distributors, Distributor's Retailers) accept a Google Maps link OR raw coords; regex auto-extracts lat/lng from pasted URL
- New collection `dms_sp_pings` — one row per salesperson GPS ping, indexed by `salesperson_id + date`
- `POST /api/dms/tracking/ping` — salesperson-only, called every 60 s from `SalespersonGpsPinger` (uses `navigator.geolocation`)
- Backend auto-stamps `users.last_active_at` + `users.last_gps` on every ping so the live map has current coords instantly

### Phase 3 · Owner Live Map ✅
- `GET /api/dms/tracking/live` — returns salespersons (with online status), distributors, retailers as marker data
- `GET /api/dms/tracking/salesperson/{sid}?date=YYYY-MM-DD` — full route: punch in/out, working hours, haversine distance km, ordered ping list, visited distributors/retailers (< 200 m proximity)
- `GET /api/dms/tracking/salesperson/{sid}/history?days=30` — date-wise summary of working hours + ping counts
- Frontend page `/dms/owner/live-tracking` — Leaflet + OpenStreetMap, colour-coded markers (D teal / R amber / S rose or slate for offline), route polyline, side panel with all metrics, date picker + quick-select (Today/Yesterday/7 days ago) + recent 30-day history buttons
- Same page mounted for **team_leader** and **regional_manager** roles; backend narrows visibility via `_sp_visible_ids_for(user)` (TL sees SPs assigned to their distributors, RM sees SPs under their TLs)

## Pending (next phases of the same sprint)
- **Phase 4** — Team Leader module (strict spec: Dashboard, Distributors, Salespersons w/ live status, Order monitoring, Retailers, Attendance, Live Tracking, Notifications)
- **Phase 5** — Regional Manager module (strict spec)
- **Phase 6** — Ordering UX (categories → products → +/- buttons) with old-vs-new price for Distributor + Retailer browse
- **Owner add-ons** — Team Leader Performance Dashboard, Distributor Sales Visibility page

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
