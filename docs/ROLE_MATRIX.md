# GO OIL DMS — RBAC Role Matrix

**Version 5.0-enterprise**

Role hierarchy (a superset role grants all children's permissions):

```
super_admin
  ├── company_admin
  │     ├── regional_manager
  │     │     └── sales_executive
  │     ├── distributor
  │     │     └── distributor_accountant
  │     ├── retailer
  │     └── customer
```

`super_admin` bypasses every check. Every other role sees a **role-filtered navigation**
(`frontend/src/lib/nav.js`) and encounters `403` when hitting APIs beyond their permit.

---

## Permission matrix (write actions)

Read = every authenticated user unless marked else. Only writes/mutations are listed here.

| Action / Endpoint | super_admin | company_admin | regional_manager | sales_executive | distributor | dist_accountant | retailer | customer |
|---|---|---|---|---|---|---|---|---|
| `POST /collections/*` (create master data) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `PUT /collections/*` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `DELETE /collections/*` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `GET /admin/users` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POST /workflow/primary-orders` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `PATCH /workflow/primary-orders/{id}/approve` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POST /workflow/dispatches` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `POST /workflow/grns` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `POST /workflow/secondary-orders` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| `POST /finance/payments` | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| `POST /finance/payments/{id}/reverse` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `POST /finance/coupons/create` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POST /finance/coupons/apply` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| `POST /finance/cashback/{id}/approve` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `POST /finance/reconciliation/run` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `POST /reverse/returns` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| `PATCH /reverse/returns/{id}/approve` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POST /reverse/claims` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| `PATCH /reverse/claims/{id}/settle` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `POST /reverse/exceptions/scan` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POST /notifications/send` (to others) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POST /ai/copilot/ask` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `GET /exports/*` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (self-data) |
| `POST /integrations/*` (payment gateways) | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `GET /integrations/accounting/tally-export` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |

---

## Enforcement layers
1. **Route dependency** — `Depends(require_admin_role)` / `require_finance_role` / `require_ops_role` from `security.py`.
2. **Server-side data filtering** — `GET /finance/outstanding` filters by `party_id`
   equal to the current user's party for distributor/retailer/customer roles.
3. **Frontend navigation** — `filterNavForRole()` hides menu items the role can't access
   (defence-in-depth; the API is the source of truth).

---

## Role bootstrap

Seed personas (dev only — replace in production):

| Role | Email | Party |
|---|---|---|
| super_admin | admin@gooil.com | — |
| company_admin | company@gooil.com | GO OIL Holdings |
| regional_manager | regional@gooil.com | West Region |
| sales_executive | sales@gooil.com | West Region |
| distributor | distributor@gooil.com | Apex Marine Ltd |
| distributor_accountant | accountant@gooil.com | Apex Marine Ltd |
| retailer | retailer@gooil.com | Metro Auto Workshop |
| customer | customer@gooil.com | Delta Fleet Corp |
