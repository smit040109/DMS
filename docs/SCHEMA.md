# GO OIL DMS — Database Schema

**Engine:** MongoDB 7 · driver: Motor (async)
**ID convention:** UUID-shaped string like `sku-4b12c9`. Never use MongoDB `ObjectId`
in application code; the `_id` field is stripped from all responses.

---

## 1 · Master data

### `users`
```
id, email (unique), name, role, password_hash, avatar?, party_id?, created_at
```
Index: `email` (unique)

### `branches`, `warehouses`, `distributors`, `retailers`, `customers`, `products`, `skus`, `batches`
Standard master-data shape:
```
id, code?, name, active, created_at, updated_at, [entity-specific fields]
```
Notable extra fields:
- `skus`: `product_id`, `unit`, `pack_size`, `mrp`, `wholesale_price`, `retail_price`, `gst_rate`
- `batches`: `sku_id`, `mfg_date`, `expires_on`, `manufactured_qty`, `qc_status`
- `distributors`, `retailers`: `party_type`, `gstin`, `address`, `phone`, `email`, `credit_limit`

**Indexes** (created at boot in `server.py`):
- `products.code`
- `skus.product_id`, `skus.code`
- `batches.sku_id`, `batches.expires_on`

---

## 2 · Inventory

### `company_inventory`, `distributor_inventory`, `retailer_inventory`
```
id, partner_id? (dist/retailer), sku_id, batch_id, quantities: {
  available, reserved, in_transit, damaged, returned, expired
}, updated_at
```
Invariant: `sum(buckets) == total_received`. Enforced at write.

### `stock_ledger`
Append-only journal of every stock movement:
```
id, timestamp, sku_id, batch_id, reference_type, reference_id,
partner_id?, from_bucket, to_bucket, qty, actor_id
```
Indexes: `(sku_id, timestamp desc)`, `reference_id`.

---

## 3 · Sales workflow

### `primary_orders`
```
id, order_no, distributor_id, branch_id, lines: [{ sku_id, qty, unit_price, discount }],
status: draft|submitted|approved|invoiced|dispatched|received|rejected|cancelled,
total, created_at, approved_at, created_by
```
Indexes: `status+created_at`, `distributor_id`, `order_no`

### `secondary_orders`, `customer_orders`
Same shape, different party links.

### `invoices`
```
id, invoice_no, party_id, party_type, primary_order_id?, lines, total, tax, status,
issued_at, due_date
```
Indexes: `invoice_no`, `(party_id, party_type)`, `status+created_at`, `primary_order_id`

### `dispatches`, `grns`
```
id, order_id, status: created|in_transit|received, items, vehicle_no?, driver?, created_at
```
Indexes: `order_id`, `status+created_at`, `dispatch_id` (on grns)

---

## 4 · Finance

### `double_ledger`
Double-entry accounting journal:
```
id, timestamp, reference_type, reference_id, account, party_id, dr, cr, narration
```
Indexes: `(party_id, timestamp asc)`, `reference_id`, `(account, timestamp asc)`

### `outstanding`
```
_id: (party_id, party_type) unique
opening_balance, total_billed, total_paid, current_balance, aging: { 0_30, 31_60, 61_90, 90_plus }
```

### `payments`
```
id, party_id, party_type, mode: cash|upi|bank|cheque, amount, reference, allocations: [{ invoice_id, amount }],
status: recorded|reversed, created_at
```
Indexes: `(party_id, party_type)`, `(reference, party_id)`, `created_at`

### `wallets`, `coupons`, `coupon_redemptions`, `cashback_rules`, `cashback_transactions`
Documented per finance.py source.

### `audit_log`
Immutable log of every mutating request:
```
id, timestamp, actor_id, action, entity_type, entity_id, changes: { before, after }
```
Indexes: `timestamp desc`, `entity_id`, `(action, timestamp desc)`

---

## 5 · Reverse logistics

### `returns`, `damage`, `claims`, `credit_notes`, `debit_notes`, `replacements`, `expiry_records`
Standard reverse-flow docs — see `reverse.py`. All indexed on `created_at desc` + `party_id` where applicable.

### `approval_requests`, `approval_matrix`
```
approval_requests: id, entity_type, entity_id, amount, status, requested_at, decided_at?, decided_by?
approval_matrix: entity_type, amount_min, amount_max, required_role
```
Indexes: `status+requested_at`, `(entity_type, entity_id)`, `(entity_type, amount_min)`

### `exceptions`
```
id, kind, severity, entity_type, entity_id, detected_at, status: open|acked|resolved, details
```
Indexes: `detected_at desc`, `(status, kind)`

---

## 6 · Notifications & AI

### `notifications`
```
id, recipient_id, title, body, category, severity, entity_type?, entity_id?,
payload, channels: [in_app, email, ...], delivery: { <channel>: {ok, provider, message_id} },
read: bool, created_at, read_at?
```
Indexes: `(recipient_id, created_at desc)`, `created_at desc`, `(read, recipient_id)`

### `notification_preferences`
```
user_id (unique), in_app, email, whatsapp, sms, digest, muted_categories, updated_at
```

### `ai_copilot_sessions`
```
id, user_id, history: [{role, content, timestamp, model?}], created_at, updated_at
```

---

## 7 · Integrations

### `webhook_events`
Log of inbound webhook payloads for later replay/debug.
```
id, received_at, payload, source?
```

---

## 8 · Index catalogue (summary)

~40 indexes across 30 collections. See `seed_all()` in `server.py` for the authoritative list.

---

## 9 · ID prefixes (consistency table)

| Prefix | Collection |
|---|---|
| `usr-` | users |
| `dist-` | distributors |
| `ret-` | retailers |
| `cust-` | customers |
| `prod-` | products |
| `sku-` | skus |
| `bat-` | batches |
| `wh-` | warehouses |
| `po-` | primary_orders |
| `so-` | secondary_orders |
| `co-` | customer_orders |
| `inv-` | invoices |
| `disp-` | dispatches |
| `grn-` | grns |
| `pay-` | payments |
| `ret-` | returns |
| `dam-` | damage |
| `clm-` | claims |
| `cn-` | credit_notes |
| `dn-` | debit_notes |
| `repl-` | replacements |
| `exc-` | exceptions |
| `apr-` | approval_requests |
| `notif-` | notifications |
| `sess-` | ai_copilot_sessions |
| `wh-` | webhook_events |

Adopt matching prefixes for any new collection.
