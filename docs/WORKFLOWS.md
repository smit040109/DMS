# GO OIL DMS — Workflow Documentation

**Version 5.0-enterprise**

Every workflow below is idempotent-safe and generates append-only entries in
`stock_ledger` (movements) and `double_ledger` (money) plus one row in `audit_log`.

---

## 1 · Primary order (Company → Distributor)

```
Company Admin         Regional Manager       Warehouse           Distributor
     │                       │                    │                    │
     │ POST /primary-orders  │                    │                    │
     │──────────────────────>│                    │                    │
     │                       │ PATCH /approve     │                    │
     │                       │───(FIFO reserve)──>│                    │
     │                       │                    │ POST /dispatches   │
     │                       │                    │───────────────────>│
     │                       │                    │                    │ POST /grns
     │                       │                    │                    │───(receive)───
     │                       │                    │                    │
     └───── audit_log / stock_ledger / double_ledger updates at every step ─────┘
```

Buckets touched: `available → reserved → in_transit → available (at distributor)`
Journal: `AR (dist) Dr / Sales Cr` at invoice; `Inventory-Dist Dr / Inventory-Company Cr` at GRN.

---

## 2 · Secondary order (Distributor → Retailer)

Similar shape. Retailer files order → distributor approves → dispatch → GRN.
Journal: `AR (ret) Dr / Sales (dist) Cr` on invoice.

---

## 3 · Payment collection

```
1. Distributor pays company. POST /finance/payments  { mode, amount, reference, party_id }
2. Auto-allocation runs FIFO across open invoices for that party.
3. double_ledger:
     Cash/Bank Dr   Amount
     AR (dist)  Cr  Amount
4. outstanding table is refreshed; aging is recomputed.
```

Reversal (`POST /finance/payments/{id}/reverse`) inverts every ledger entry.

---

## 4 · Return

```
Retailer/Distributor:   POST /reverse/returns  { items, reason }
                          → status = pending
Regional Manager:       PATCH /returns/{id}/approve
                          → moves inventory bucket "available → returned"
                          → generates credit_note (auto)
                          → double_ledger:
                               AR (party) Cr  amount
                               Sales returns Dr  amount
Retailer/Distributor:   sees CN reflected in outstanding & wallet
```

Escalation matrix (`approval_matrix`) governs approver role by amount.

---

## 5 · Damage / Expiry / Replacement

- **Damage** — bucket move `available → damaged`; no journal until scrap event.
- **Expiry** — nightly detector marks batches → warning at 30 days;
  action can be `write_off` (double-entry P&L Dr, Inventory Cr) or `return_to_manufacturer`.
- **Replacement** — return + new dispatch chained via `replacement_id`.

---

## 6 · Coupon / Cashback

- Coupon: `POST /coupons/create` → distribute code → user applies at checkout.
  Discount is a `debit_note` linked to the coupon redemption.
- Cashback: rules like "5% back on ₦100k+ orders". Cron computes; `distributor_accountant`
  approves. Approved amount goes to `wallets` and can offset future invoices.

---

## 7 · Exception scan

`POST /reverse/exceptions/scan` runs six detectors:
1. Price mismatch (invoice line vs SKU wholesale)
2. Ledger imbalance (Dr ≠ Cr on a ref)
3. Bucket drift (sum ≠ total_received)
4. Aged in_transit (dispatch not GRN'd in > 7 days)
5. Duplicate payment reference
6. Expired batch still marked available

Each hit produces an `exceptions` doc + a notification to admin.

---

## 8 · Reconciliation

`POST /finance/reconciliation/run` compares:
- `payments` vs `double_ledger` for every day in range
- `outstanding.current_balance` vs `sum(ledger.dr - ledger.cr)` per party
Diffs are recorded and shown in the Reconciliation page.

---

## 9 · Executive summary generation (AI Copilot)

- User opens copilot drawer → asks "Give me a daily executive summary."
- `ai_copilot.py` detects intent → fetches `/analytics/ai-context/executive`
- Builds a compact JSON snapshot (top KPIs, top alerts, aging buckets)
- Sends to LLM with executive-persona system prompt
- Returns answer + `sources: [{endpoint, key_numbers}]`

---

## 10 · Nightly jobs (recommended cron)

Currently these are on-demand endpoints; wire a cron / K8s CronJob for production:
- `POST /reverse/exceptions/scan` — every 30 min
- `POST /finance/reconciliation/run` — daily 02:00
- Expiry sweeper — nightly (already inside `/reverse/expiry?days=30` computation)
- `./scripts/backup.sh` — daily 03:15
