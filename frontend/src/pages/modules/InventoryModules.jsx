import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import StatusPill from "@/components/common/StatusPill";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Select, SelectTrigger, SelectContent, SelectItem, SelectValue,
} from "@/components/ui/select";
import { Warehouse, Handshake, Store, Package, TrendingUp } from "lucide-react";

function InventoryBucketBar({ available = 0, reserved = 0, in_transit = 0, damaged = 0 }) {
  const total = available + reserved + in_transit + damaged;
  if (total === 0) return <span className="text-xs text-ink-muted">Empty</span>;
  const p = (v) => (v * 100) / total;
  return (
    <div className="flex items-center gap-2 w-52">
      <div className="h-2 flex-1 rounded-full overflow-hidden bg-slate-100 flex">
        <div title={`Available ${available}`} className="bg-emerald-500 h-full" style={{ width: `${p(available)}%` }} />
        <div title={`Reserved ${reserved}`} className="bg-amber-400 h-full" style={{ width: `${p(reserved)}%` }} />
        <div title={`In transit ${in_transit}`} className="bg-blue-500 h-full" style={{ width: `${p(in_transit)}%` }} />
        <div title={`Damaged ${damaged}`} className="bg-rose-500 h-full" style={{ width: `${p(damaged)}%` }} />
      </div>
      <span className="text-xs text-ink-muted tabular-nums whitespace-nowrap">{total.toLocaleString()}</span>
    </div>
  );
}

function InventoryRowsTable({ rows, loading, testId }) {
  return (
    <DataTable
      data={rows}
      loading={loading}
      testId={testId}
      columns={[
        { key: "sku_code", label: "SKU" },
        { key: "product_name", label: "Product" },
        { key: "pack_size", label: "Pack", type: "chip" },
        { key: "batch_id", label: "Batch", render: (r) => <span className="text-xs font-mono text-ink-muted">{r.batch_id?.slice(-8)}</span> },
        { key: "available", label: "Available", align: "right", render: (r) => <span className="font-semibold text-emerald-700 tabular-nums">{(r.available || 0).toLocaleString()}</span> },
        { key: "reserved", label: "Reserved", align: "right", render: (r) => <span className="text-amber-700 tabular-nums">{(r.reserved || 0).toLocaleString()}</span> },
        { key: "in_transit", label: "In Transit", align: "right", render: (r) => <span className="text-blue-700 tabular-nums">{(r.in_transit || 0).toLocaleString()}</span> },
        { key: "damaged", label: "Damaged", align: "right", render: (r) => <span className="text-rose-700 tabular-nums">{(r.damaged || 0).toLocaleString()}</span> },
        { key: "bar", label: "Distribution", render: (r) => <InventoryBucketBar {...r} /> },
      ]}
    />
  );
}

// ---------- Company Inventory ----------
export function CompanyInventoryPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.get("/workflow/inventory/company")
      .then((r) => setRows(r.data.data || []))
      .finally(() => setLoading(false));
  }, []);
  const totals = rows.reduce((acc, r) => {
    acc.available += r.available || 0; acc.reserved += r.reserved || 0;
    acc.in_transit += r.in_transit || 0; acc.damaged += r.damaged || 0;
    return acc;
  }, { available: 0, reserved: 0, in_transit: 0, damaged: 0 });

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Operations", "Inventory"]}
        title="Company Inventory"
        subtitle="Batch-level stock across every warehouse with FIFO tracking"
      />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Available", value: totals.available, color: "text-emerald-700", bg: "bg-emerald-50" },
          { label: "Reserved", value: totals.reserved, color: "text-amber-700", bg: "bg-amber-50" },
          { label: "In Transit", value: totals.in_transit, color: "text-blue-700", bg: "bg-blue-50" },
          { label: "Damaged", value: totals.damaged, color: "text-rose-700", bg: "bg-rose-50" },
        ].map((t) => (
          <div key={t.label} className="bg-white border border-[#E5E7EB] rounded-xl card-soft p-5">
            <div className="text-[11px] uppercase tracking-[0.22em] text-ink-muted font-semibold">{t.label}</div>
            <div className={`mt-2 font-display font-extrabold text-3xl ${t.color}`}>{t.value.toLocaleString()}</div>
            <div className={`mt-2 h-1 rounded-full ${t.bg}`}></div>
          </div>
        ))}
      </div>
      <InventoryRowsTable rows={rows} loading={loading} testId="company-inventory" />
    </div>
  );
}

// ---------- Distributor Inventory ----------
export function DistributorInventoryPage() {
  const [distributors, setDistributors] = useState([]);
  const [distId, setDistId] = useState("");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/collections/distributors").then((r) => {
      const list = r.data.data || [];
      setDistributors(list);
      if (list[0]) setDistId(list[0].id);
    });
  }, []);

  useEffect(() => {
    if (!distId) return;
    setLoading(true);
    api.get(`/workflow/inventory/distributor/${distId}`)
      .then((r) => setRows(r.data.data || []))
      .finally(() => setLoading(false));
  }, [distId]);

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Network", "Distributor Inventory"]}
        title="Distributor Inventory"
        subtitle="Partner-level stock buckets updated after every GRN"
        actions={
          <Select value={distId} onValueChange={setDistId}>
            <SelectTrigger className="w-72 h-10 border-[#E5E7EB]" data-testid="distributor-select"><SelectValue placeholder="Select distributor" /></SelectTrigger>
            <SelectContent>
              {distributors.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
            </SelectContent>
          </Select>
        }
      />
      <InventoryRowsTable rows={rows} loading={loading} testId="distributor-inventory" />
    </div>
  );
}

// ---------- Retailer Inventory ----------
export function RetailerInventoryPage() {
  const [retailers, setRetailers] = useState([]);
  const [retId, setRetId] = useState("");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/collections/retailers").then((r) => {
      const list = r.data.data || [];
      setRetailers(list);
      if (list[0]) setRetId(list[0].id);
    });
  }, []);

  useEffect(() => {
    if (!retId) return;
    setLoading(true);
    api.get(`/workflow/inventory/retailer/${retId}`)
      .then((r) => setRows(r.data.data || []))
      .finally(() => setLoading(false));
  }, [retId]);

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Network", "Retailer Inventory"]}
        title="Retailer Inventory"
        subtitle="Retailer stock — auto-updated after Retailer GRN"
        actions={
          <Select value={retId} onValueChange={setRetId}>
            <SelectTrigger className="w-72 h-10 border-[#E5E7EB]" data-testid="retailer-select"><SelectValue placeholder="Select retailer" /></SelectTrigger>
            <SelectContent>
              {retailers.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
            </SelectContent>
          </Select>
        }
      />
      <InventoryRowsTable rows={rows} loading={loading} testId="retailer-inventory" />
    </div>
  );
}

// ---------- Stock Ledger ----------
export function StockLedgerPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scope, setScope] = useState("all");

  const load = (s) => {
    setLoading(true);
    const q = s && s !== "all" ? `?scope=${s}` : "";
    api.get(`/workflow/stock-ledger${q}`)
      .then((r) => setRows(r.data.data || []))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(scope); }, [scope]);

  const movementBadge = (m) => {
    const map = {
      stock_in: "bg-emerald-100 text-emerald-800",
      reserve: "bg-amber-100 text-amber-800",
      unreserve: "bg-slate-100 text-slate-700",
      dispatch_out: "bg-blue-100 text-blue-800",
      dispatch_settled: "bg-slate-100 text-slate-700",
      grn_in: "bg-emerald-100 text-emerald-800",
      damage: "bg-rose-100 text-rose-800",
      return: "bg-slate-100 text-slate-700",
      expire: "bg-rose-100 text-rose-800",
    };
    return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${map[m] || "bg-slate-100 text-slate-700"}`}>{m}</span>;
  };

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Operations", "Stock Ledger"]}
        title="Stock Ledger"
        subtitle="Immutable log of every stock movement across company, distributor and retailer"
        actions={
          <Tabs value={scope} onValueChange={setScope}>
            <TabsList className="bg-canvas border border-[#E5E7EB]">
              <TabsTrigger value="all" data-testid="ledger-all">All</TabsTrigger>
              <TabsTrigger value="company" data-testid="ledger-company">Company</TabsTrigger>
              <TabsTrigger value="distributor" data-testid="ledger-distributor">Distributor</TabsTrigger>
              <TabsTrigger value="retailer" data-testid="ledger-retailer">Retailer</TabsTrigger>
            </TabsList>
          </Tabs>
        }
      />
      <DataTable
        data={rows}
        loading={loading}
        testId="stock-ledger-table"
        pageSize={15}
        columns={[
          { key: "timestamp", label: "When", type: "date" },
          { key: "movement", label: "Movement", render: (r) => movementBadge(r.movement) },
          { key: "scope", label: "Scope", type: "chip" },
          { key: "sku_code", label: "SKU" },
          { key: "batch_id", label: "Batch", render: (r) => <span className="text-xs font-mono text-ink-muted">{r.batch_id?.slice(-8)}</span> },
          { key: "qty", label: "Qty", align: "right", render: (r) => <span className="font-semibold tabular-nums">{r.qty?.toLocaleString()}</span> },
          { key: "from_bucket", label: "From → To", render: (r) => (
            <span className="text-xs text-ink-muted">{r.from_bucket || "—"} → <span className="text-ink font-semibold">{r.to_bucket || "—"}</span></span>
          )},
          { key: "reference_type", label: "Ref", type: "chip" },
          { key: "notes", label: "Notes" },
        ]}
      />
    </div>
  );
}
