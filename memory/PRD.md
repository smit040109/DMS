# GO OIL — Distribution Management System (DMS)

## Original problem statement
Enterprise-grade DMS with 28 modules, 8 role dashboards. Phase 1: connected operational engine (Product → Retailer Inventory). Phase 2: connected financial engine (Customer Order → Coupon → Cashback → Invoice → Payment → Ledger → Outstanding → Reconciliation).

## Architecture
- **Backend** (`FastAPI + MongoDB`): 3 routers — `collections` (generic CRUD), `workflow` (Phase 1 operations), `finance` (Phase 2 financials). Ledger + inventory are recomputed from immutable ledger writes.
- **Frontend** (`React + shadcn/ui`): Reusable `AppShell`, `DataTable`, `PageHeader`, `WorkflowActions`. All finance UI added under existing design system — no redesign.

## Phase 1 (delivered v2.0)
`Batch → Stock In → Company Inventory → Primary Order → Approve (FIFO reserve) → Auto-Invoice → Dispatch → GIT → GRN → Distributor Inventory → Secondary Order → ... → Retailer Inventory`. Stock ledger, bucket accounting (available/reserved/in_transit/damaged/returned/expired).

## Phase 2 — Financial Engine (delivered v3.0)
### New backend module `backend/finance.py`
- **Double-entry ledger** (`double_ledger` collection). Chart of accounts: AR (1200), CASH (1000), SALES (4000), TAX_OUT (2100), DISCOUNT (5100), CASHBACK_EXP (5200), CASHBACK_LIAB (2200), AP (2000). Every posting is journal-balanced.
- **Outstanding management** — computed from AR journal. Includes overdue days, credit utilization, collection status. Auto-refresh on every payment/invoice.
- **Payment engine** — multi-method (Cash/UPI/Bank Transfer/Cheque/Card/Wallet). Auto-allocates to invoices oldest-first if none selected. Fully reversible with ledger unwind. Payment allocations tracked separately.
- **Coupon engine** — code-based with validation rules: existence, expiry, usage-limit, min-order, party applicability, one-per-party. Fraud check via `coupon_redemptions` idempotency.
- **Cashback engine** — rule-based (`cashback_rules`): scope (sku/product/category/distributor/retailer/customer/campaign), percent/flat, max cap, daily/monthly caps, approval-required flag. Auto-crediting through **wallets** collection with earn/redeem history in `cashback_transactions`.
- **Customer orders** (`customer_orders`) — retailer → customer sale. Validates retailer inventory FIFO, redeems coupon, computes cashback, generates customer invoice, posts AR ledger, updates outstanding, deducts retailer inventory, credits wallet.
- **Reconciliation** — matches invoices vs payments per party, produces variance report saved to `reconciliation_reports`.
- **Audit log** — every finance action stamped in `audit_log` (actor, action, entity, meta).
- **Auto-post** on startup — every pre-existing Phase 1 invoice back-fills a matching AR/Sales/Tax journal entry so ledger + outstanding are populated day-1.

### Endpoints (`/api/finance/*`)
- Payments: `POST /payments`, `POST /payments/{id}/reverse`
- Coupons: `POST /coupons/create`, `POST /coupons/validate`
- Cashback: `POST /cashback-rules`, `GET /cashback-rules`, `POST /cashback/compute`, `POST /cashback/{id}/approve|reject`
- Customer orders: `POST /customer-orders`, `POST /customer-orders/{id}/pack|deliver|cancel`
- Outstanding: `GET /outstanding`, `GET /outstanding/{pt}/{id}`
- Ledger: `GET /ledger`, `GET /ledger/{pt}/{id}` (with running balance per account)
- Wallet: `GET /wallets/{pt}/{id}`
- Reconciliation: `POST /reconciliation/run`, `GET /reconciliation/reports`
- Audit: `GET /audit-log`

### New Frontend pages (`FinanceModules.jsx`)
- **Payments** with "Record Payment" dialog (party-type + auto-allocation checklist + methods)
- **Outstanding** — tabs by party type, aged with utilization bar
- **Double-Entry Ledger** — account + party-type filters, formatted Dr/Cr columns
- **Cashback Engine** — Rules tab + Pending approvals with one-click approve/reject
- **Coupon Engine** — create dialog + validate dialog (test coupon before use)
- **Customer Orders** — new order dialog with retailer/customer/SKU/coupon/payment; success preview shows invoice + cashback
- **Wallets** — party-type & party selector; balance + lifetime metrics + txn history
- **Reconciliation** — one-click run per party type; report with balanced/variance summary
- **Audit Log** — full action history

## Personas (all password `GoOil@2026`)
See `test_credentials.md`. Nav is role-filtered — Customer sees Invoices/Coupons/Wallet; Distributor Accountant sees Payments/Ledger/Reconciliation/Outstanding.

## Backlog
### P1
- Deep entity trace drawer (order/invoice → dispatch → GRN → payment → ledger timeline)
- Retailer & Customer portal-specific dashboards for their own outstanding/wallet
- Refund / return workflow (partial reverse inventory + credit note)
- Cashback expiry sweep (nightly cron)
- Payment gateway hookup (Stripe/Razorpay for real customer payment collection)

### P2
- Multi-currency
- Server-side pagination on ledger & audit log
- CSV/PDF report exports
- Real-time WebSocket

## Next actions
- Phase 3: Reporting & Analytics engine — build parameterized reports (GSTR, TB, P&L, aged receivables) that read from `double_ledger` + `outstanding`
- Add role-based write authorization on `/finance/*` mutations (currently any authenticated user)
- Add retailer portal "Pay distributor invoice" quick-action
