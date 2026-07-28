import React from "react";
import ModulePage from "@/components/common/ModulePage";

// Shared column recipes
const money = (key, label, align = "right") => ({ key, label, type: "currency", align });
const status = (key = "status") => ({ key, label: "Status", type: "status" });
const date = (key, label) => ({ key, label, type: "date" });
const chip = (key, label) => ({ key, label, type: "chip" });
const text = (key, label) => ({ key, label });

// ---------- Catalog ----------
export function ProductsPage() {
  return (
    <ModulePage
      resource="products"
      title="Products"
      subtitle="Master product catalog with grades, HSN and lifecycle"
      columns={[
        text("code", "Code"), text("name", "Product"), chip("category", "Category"),
        chip("grade", "Grade"), text("hsn", "HSN"),
        { key: "gst_rate", label: "GST", render: (r) => `${r.gst_rate}%` },
        { key: "active", label: "Status", render: (r) => r.active ? "Active" : "Inactive", type: "status" },
      ]}
      primaryAction={{ label: "New product", icon: (p) => <span {...p}>+</span> }}
    />
  );
}

export function SkusPage() {
  return (
    <ModulePage
      resource="skus"
      title="SKUs"
      subtitle="Pack-level SKUs with pricing, barcode and trade price"
      columns={[
        text("sku_code", "SKU"), text("product_name", "Product"), chip("pack_size", "Pack"),
        text("barcode", "Barcode"),
        money("mrp", "MRP"), money("trade_price", "Trade price"), money("cost", "Cost"),
      ]}
    />
  );
}

export function BatchesPage() {
  return (
    <ModulePage
      resource="batches"
      title="Batches"
      subtitle="Manufacturing batches with QC status and expiry tracking"
      columns={[
        text("batch_no", "Batch"), text("sku_code", "SKU"), text("product_name", "Product"),
        date("manufactured_on", "Manufactured"), date("expires_on", "Expires"),
        { key: "quantity", label: "Qty", align: "right", render: (r) => r.quantity?.toLocaleString() },
        { key: "quality_status", label: "QC Status", type: "status" },
      ]}
    />
  );
}

// ---------- Inventory ----------
export function InventoryPage() {
  return (
    <ModulePage
      resource="inventory"
      title="Inventory"
      subtitle="Live stock positions across warehouses with reorder alerts"
      columns={[
        text("sku_code", "SKU"), text("product_name", "Product"),
        text("warehouse_name", "Warehouse"), chip("pack_size", "Pack"),
        { key: "on_hand", label: "On hand", align: "right", render: (r) => r.on_hand?.toLocaleString() },
        { key: "reserved", label: "Reserved", align: "right", render: (r) => (r.reserved || 0).toLocaleString() },
        { key: "reorder_level", label: "Reorder", align: "right" },
        status(),
        date("last_movement", "Last move"),
      ]}
    />
  );
}

export function WarehousesPage() {
  return (
    <ModulePage
      resource="warehouses"
      title="Warehouses"
      subtitle="Capacity, occupancy and warehouse manager assignments"
      columns={[
        text("name", "Warehouse"), chip("type", "Type"), text("manager", "Manager"),
        { key: "capacity", label: "Capacity", align: "right", render: (r) => `${r.capacity?.toLocaleString()} L` },
        { key: "occupied", label: "Occupied", align: "right", render: (r) => `${r.occupied?.toLocaleString()} L` },
        {
          key: "utilization", label: "Utilization",
          render: (r) => {
            const pct = Math.round((r.occupied / r.capacity) * 100);
            const tone = pct > 85 ? "bg-rose-500" : pct > 65 ? "bg-amber-500" : "bg-emerald-500";
            return (
              <div className="flex items-center gap-2 w-40">
                <div className="h-1.5 bg-slate-100 rounded-full flex-1 overflow-hidden">
                  <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
                </div>
                <span className="text-xs text-ink-muted tabular-nums">{pct}%</span>
              </div>
            );
          },
        },
      ]}
    />
  );
}

// ---------- Network ----------
export function DistributorsPage() {
  return (
    <ModulePage
      resource="distributors"
      title="Distributors"
      subtitle="Partner network, credit health and onboarding pipeline"
      columns={[
        text("code", "Code"), text("name", "Distributor"), text("contact", "Contact"),
        text("gstin", "GSTIN"),
        money("credit_limit", "Credit limit"), money("outstanding", "Outstanding"),
        { key: "rating", label: "Rating", render: (r) => `${r.rating} ★` },
        status(),
      ]}
    />
  );
}

export function RetailersPage() {
  return (
    <ModulePage
      resource="retailers"
      title="Retailers"
      subtitle="Retailer network, cashback status and outstanding"
      columns={[
        text("code", "Code"), text("name", "Retailer"), chip("type", "Type"), text("city", "City"),
        money("outstanding", "Outstanding"), money("cashback_earned", "Cashback"),
        status(),
      ]}
    />
  );
}

export function CustomersPage() {
  return (
    <ModulePage
      resource="customers"
      title="Customers"
      subtitle="End customers, segment breakdown and lifetime value"
      columns={[
        text("code", "Code"), text("name", "Customer"), chip("segment", "Segment"),
        text("city", "City"), text("phone", "Phone"),
        { key: "orders_count", label: "Orders", align: "right" },
        money("ltv", "LTV"),
        status(),
      ]}
    />
  );
}

// ---------- Sales ----------
const orderColumns = [
  text("order_no", "Order"),
  text("party_name", "Party"),
  chip("party_type", "Type"),
  text("branch_id", "Branch"),
  { key: "line_items", label: "Items", align: "right" },
  money("total", "Total"),
  status(),
  chip("sla", "SLA"),
  date("placed_on", "Placed"),
];

export function PrimaryOrdersPage() {
  return (
    <ModulePage
      resource="primary-orders"
      title="Primary Orders"
      subtitle="Distributor → Company orders with approval workflow"
      columns={orderColumns}
    />
  );
}

export function SecondaryOrdersPage() {
  return (
    <ModulePage
      resource="secondary-orders"
      title="Secondary Orders"
      subtitle="Retailer → Distributor orders with fulfilment tracking"
      columns={orderColumns}
    />
  );
}

export function InvoicesPage() {
  return (
    <ModulePage
      resource="invoices"
      title="Invoices"
      subtitle="GST-compliant invoices, ageing and collection status"
      columns={[
        text("invoice_no", "Invoice"), text("party_name", "Party"),
        money("subtotal", "Subtotal"), money("tax", "Tax"), money("total", "Total"),
        money("paid", "Paid"),
        status(),
        date("due_on", "Due"),
      ]}
    />
  );
}

// ---------- Ops ----------
export function DispatchesPage() {
  return (
    <ModulePage
      resource="dispatches"
      title="Dispatch"
      subtitle="Vehicle-loaded dispatches with route and ETA"
      columns={[
        text("dispatch_no", "Dispatch"), text("party_name", "Party"),
        text("vehicle_no", "Vehicle"), text("driver", "Driver"),
        text("route", "Route"),
        { key: "distance_km", label: "Distance", align: "right", render: (r) => `${r.distance_km} km` },
        status(),
        date("eta", "ETA"),
      ]}
    />
  );
}

export function GitPage() {
  // Filters dispatches with in-transit / loaded status via reuse
  return (
    <ModulePage
      resource="dispatches"
      title="Goods In Transit"
      subtitle="Currently loaded and in-transit dispatches"
      columns={[
        text("dispatch_no", "Dispatch"), text("party_name", "Party"),
        text("vehicle_no", "Vehicle"), text("route", "Route"),
        status(),
        date("eta", "ETA"),
      ]}
    />
  );
}

export function GrnPage() {
  return (
    <ModulePage
      resource="grns"
      title="Goods Received Note"
      subtitle="Receipts against dispatches with variance and dispute tracking"
      columns={[
        text("grn_no", "GRN"), text("dispatch_id", "Dispatch"),
        text("received_by", "Received by"), date("received_on", "Received on"),
        chip("condition", "Condition"),
        { key: "variance", label: "Variance", align: "right" },
        status(),
      ]}
    />
  );
}

// ---------- Finance ----------
export function PaymentsPage() {
  return (
    <ModulePage
      resource="payments"
      title="Payments"
      subtitle="Incoming payments across all channels with reconciliation status"
      columns={[
        text("payment_no", "Payment"), text("party_name", "Party"),
        chip("mode", "Mode"), text("reference", "Reference"),
        money("amount", "Amount"),
        date("received_on", "Received"),
        status(),
      ]}
    />
  );
}

export function LedgerPage() {
  return (
    <ModulePage
      resource="ledger"
      title="Ledger"
      subtitle="Party ledger with debits, credits and running balance"
      columns={[
        date("date", "Date"), text("party_name", "Party"),
        chip("particulars", "Particulars"), text("reference", "Reference"),
        money("debit", "Debit"), money("credit", "Credit"), money("balance", "Balance"),
      ]}
    />
  );
}

export function ExpensesPage() {
  return (
    <ModulePage
      resource="expenses"
      title="Expenses"
      subtitle="Operational expenses with vendor and approval tracking"
      columns={[
        text("expense_no", "Expense"), chip("category", "Category"), text("vendor", "Vendor"),
        text("branch_id", "Branch"),
        money("amount", "Amount"), date("date", "Date"), status(),
      ]}
    />
  );
}

// ---------- Rewards ----------
export function CashbackPage() {
  return (
    <ModulePage
      resource="cashback"
      title="Cashback"
      subtitle="Retailer cashback campaigns, earnings and redemptions"
      columns={[
        text("retailer_name", "Retailer"), chip("campaign", "Campaign"),
        money("earned", "Earned"), money("redeemed", "Redeemed"),
        date("issued_on", "Issued"), status(),
      ]}
    />
  );
}

export function CouponsPage() {
  return (
    <ModulePage
      resource="coupons"
      title="Coupons"
      subtitle="Promotional coupons with usage caps and validity"
      columns={[
        text("code", "Code"), chip("campaign", "Campaign"),
        chip("discount_type", "Type"),
        { key: "value", label: "Value", align: "right" },
        { key: "usage", label: "Usage", align: "right", render: (r) => `${r.usage} / ${r.limit}` },
        date("valid_till", "Valid till"), status(),
      ]}
    />
  );
}

// ---------- Admin ----------
export function ApprovalsPage() {
  return (
    <ModulePage
      resource="approvals"
      title="Approval Engine"
      subtitle="Configurable approval workflows with SLA tracking"
      columns={[
        text("id", "ID"), text("title", "Request"),
        chip("module", "Module"), text("requested_by", "Requested by"),
        money("amount", "Amount"),
        chip("sla", "SLA"),
        status(),
        date("created_at", "Created"),
      ]}
    />
  );
}

export function NotificationsPage() {
  return (
    <ModulePage
      resource="notifications"
      title="Notifications"
      subtitle="Platform-wide alerts and system events"
      columns={[
        text("title", "Title"), chip("severity", "Severity"), chip("module", "Module"),
        date("created_at", "Received"),
        { key: "read", label: "Status", render: (r) => (r.read ? "Read" : "Unread"), type: "status" },
      ]}
    />
  );
}
