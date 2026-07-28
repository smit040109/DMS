import React, { useEffect, useMemo, useState, useCallback } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import KpiCard from "@/components/common/KpiCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  ResponsiveContainer, AreaChart, Area, LineChart, Line, BarChart, Bar,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  Treemap, RadialBarChart, RadialBar, FunnelChart, Funnel, LabelList,
} from "recharts";
import {
  Activity, TrendingUp, TrendingDown, DollarSign, Package, ShoppingCart, AlertOctagon,
  Users, Search, Filter, ChevronRight, RefreshCw, Layers, CheckCircle2, XCircle,
  Loader2, ArrowRight, Award, Radar, Target, Zap, BarChart3, PieChart as PieIcon,
  MapPin, Building2, User2, Store, Truck, ClipboardList,
} from "lucide-react";

// ---------------- helpers ----------------
const money = (n) => {
  const v = Number(n) || 0;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
};
const fullMoney = (n) => `$${(Number(n) || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
const dateStr = (v) => { try { return new Date(v).toLocaleDateString(undefined, { day: "2-digit", month: "short" }); } catch { return String(v || ""); } };
const CHART_COLORS = ["#C89A2B", "#8B6914", "#0EA5A4", "#6366F1", "#EC4899", "#F59E0B", "#EF4444", "#10B981", "#3B82F6", "#A855F7"];
const SEV_COLOR = { high: "bg-rose-100 text-rose-700 border-rose-200", medium: "bg-amber-100 text-amber-700 border-amber-200", low: "bg-slate-100 text-slate-600 border-slate-200" };

// Reusable ChartCard
function ChartCard({ title, subtitle, action, children, className = "", testId }) {
  return (
    <div className={`bg-white border border-[#E5E7EB] rounded-xl p-4 ${className}`} data-testid={testId}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-sm font-semibold text-ink">{title}</div>
          {subtitle && <div className="text-[11px] text-ink-muted mt-0.5">{subtitle}</div>}
        </div>
        {action}
      </div>
      <div>{children}</div>
    </div>
  );
}

// Global filter panel — emits (filters) via onChange
function GlobalFilters({ value, onChange, showParty = true, testIdPrefix = "gf" }) {
  const [dims, setDims] = useState(null);
  useEffect(() => { api.get("/analytics/dimensions").then((r) => setDims(r.data)); }, []);
  const update = (patch) => onChange({ ...value, ...patch });
  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-2 items-end bg-white border border-[#E5E7EB] rounded-xl p-3">
      <div>
        <Label className="text-[10px] uppercase tracking-widest text-ink-muted">Range</Label>
        <Select value={value.range || "month"} onValueChange={(v) => update({ range: v })}>
          <SelectTrigger className="h-9 border-[#E5E7EB]" data-testid={`${testIdPrefix}-range`}><SelectValue /></SelectTrigger>
          <SelectContent>{(dims?.ranges || ["today","yesterday","week","month","quarter","year"]).map((r) => (
            <SelectItem key={r} value={r}>{r}</SelectItem>
          ))}</SelectContent>
        </Select>
      </div>
      <div>
        <Label className="text-[10px] uppercase tracking-widest text-ink-muted">Branch</Label>
        <Select value={value.branch_id || "all"} onValueChange={(v) => update({ branch_id: v === "all" ? "" : v })}>
          <SelectTrigger className="h-9 border-[#E5E7EB]" data-testid={`${testIdPrefix}-branch`}><SelectValue placeholder="All" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All branches</SelectItem>
            {(dims?.branches || []).map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      {showParty && (
        <div>
          <Label className="text-[10px] uppercase tracking-widest text-ink-muted">Distributor</Label>
          <Select value={value.distributor_id || "all"} onValueChange={(v) => update({ distributor_id: v === "all" ? "" : v })}>
            <SelectTrigger className="h-9 border-[#E5E7EB]" data-testid={`${testIdPrefix}-dist`}><SelectValue placeholder="All" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All distributors</SelectItem>
              {(dims?.distributors || []).map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      )}
      <div>
        <Label className="text-[10px] uppercase tracking-widest text-ink-muted">SKU</Label>
        <Select value={value.sku_id || "all"} onValueChange={(v) => update({ sku_id: v === "all" ? "" : v })}>
          <SelectTrigger className="h-9 border-[#E5E7EB]" data-testid={`${testIdPrefix}-sku`}><SelectValue placeholder="All" /></SelectTrigger>
          <SelectContent className="max-h-64">
            <SelectItem value="all">All SKUs</SelectItem>
            {(dims?.skus || []).map((b) => <SelectItem key={b.id} value={b.id}>{b.sku_code}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label className="text-[10px] uppercase tracking-widest text-ink-muted">Region</Label>
        <Select value={value.region || "all"} onValueChange={(v) => update({ region: v === "all" ? "" : v })}>
          <SelectTrigger className="h-9 border-[#E5E7EB]" data-testid={`${testIdPrefix}-region`}><SelectValue placeholder="All" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All regions</SelectItem>
            {(dims?.regions || []).map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <Button variant="outline" className="h-9 border-[#E5E7EB]" onClick={() => onChange({ range: value.range || "month" })} data-testid={`${testIdPrefix}-clear`}>
        <RefreshCw size={13} className="mr-1" /> Reset
      </Button>
    </div>
  );
}

// ==========================================================
// EXECUTIVE COMMAND CENTER
// ==========================================================
export function ExecutiveCommandCenter() {
  const nav = useNavigate();
  const [filters, setFilters] = useState({ range: "month" });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState({ count: 0, alerts: [] });

  const load = useCallback(() => {
    setLoading(true);
    const p = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => { if (v) p.set(k, v); });
    Promise.all([
      api.get(`/analytics/kpi/executive?${p.toString()}`),
      api.get("/analytics/alerts"),
    ]).then(([k, a]) => {
      setData(k.data);
      setAlerts(a.data);
    }).finally(() => setLoading(false));
  }, [filters]);
  useEffect(load, [load]);

  const goToDrill = (drill) => {
    if (!drill) return;
    if (drill.startsWith("party360/")) nav(`/app/${drill}`);
    else nav(`/app/${drill}`);
  };

  const KPI_META = [
    { key: "revenue", label: "Revenue", format: money, trend: "up" },
    { key: "sales_count", label: "Sales", format: (v) => v, trend: "up" },
    { key: "inventory_value", label: "Inventory Value", format: money, trend: "up" },
    { key: "inventory_health", label: "Inventory Health", format: (v) => `${v}%`, trend: "up" },
    { key: "order_pipeline", label: "Order Pipeline", format: money, trend: "up" },
    { key: "outstanding", label: "Outstanding", format: money, trend: "down" },
    { key: "collections", label: "Collections", format: money, trend: "up" },
    { key: "cash_flow", label: "Cash Flow", format: money, trend: "up" },
    { key: "claims", label: "Claims", format: money, trend: "down" },
    { key: "returns", label: "Returns", format: money, trend: "down" },
    { key: "replacement_cost", label: "Replacement Cost", format: money, trend: "down" },
    { key: "approval_queue", label: "Approval Queue", format: (v) => v, trend: "down" },
    { key: "exception_count", label: "Exceptions", format: (v) => v, trend: "down" },
    { key: "business_risk_score", label: "Risk Score", format: (v) => `${v}/100`, trend: "down" },
    { key: "company_health_score", label: "Health Score", format: (v) => `${v}/100`, trend: "up" },
  ];

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "BI", "Executive Command Center"]}
        title="Executive Command Center"
        subtitle="Live enterprise decision-support — 15 KPIs, active alerts, trend series"
        actions={<Button variant="outline" className="h-10 border-[#E5E7EB]" onClick={load}><RefreshCw size={14} className="mr-2" /> Refresh</Button>}
      />
      <GlobalFilters value={filters} onChange={setFilters} testIdPrefix="ecc" />
      <div className="mt-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {KPI_META.map((m) => {
          const k = data?.kpis?.[m.key];
          if (!k) return null;
          return (
            <button key={m.key} className="text-left focus:outline-none focus:ring-2 focus:ring-gold/40 rounded-xl"
              onClick={() => goToDrill(k.drill)} data-testid={`ecc-kpi-${m.key}`}>
              <KpiCard label={m.label} value={m.format(k.value)} delta={k.count != null ? `${k.count} txn` : (k.unit || "live")} trend={m.trend} />
            </button>
          );
        })}
      </div>

      <div className="mt-5 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title="Revenue vs Collections vs Returns" subtitle={`Period: ${filters.range || "month"}`} className="lg:col-span-2" testId="ecc-chart-trend">
          {loading ? <div className="h-64 flex items-center justify-center text-ink-muted"><Loader2 className="animate-spin" size={18} /></div> : (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={data?.series || []}>
                <defs>
                  <linearGradient id="gRev" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#C89A2B" stopOpacity={0.6}/><stop offset="95%" stopColor="#C89A2B" stopOpacity={0}/></linearGradient>
                  <linearGradient id="gCol" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#0EA5A4" stopOpacity={0.5}/><stop offset="95%" stopColor="#0EA5A4" stopOpacity={0}/></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                <XAxis dataKey="period" tick={{ fill: "#64748B", fontSize: 11 }} />
                <YAxis tick={{ fill: "#64748B", fontSize: 11 }} tickFormatter={money} />
                <Tooltip formatter={(v) => fullMoney(v)} />
                <Area type="monotone" dataKey="revenue" stroke="#C89A2B" strokeWidth={2} fill="url(#gRev)" />
                <Area type="monotone" dataKey="collections" stroke="#0EA5A4" strokeWidth={2} fill="url(#gCol)" />
                <Line type="monotone" dataKey="returns" stroke="#EF4444" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="claims" stroke="#F59E0B" strokeWidth={2} dot={false} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
        <ChartCard title="Business Health" subtitle="Composite risk vs health score" testId="ecc-chart-radial">
          <ResponsiveContainer width="100%" height={260}>
            <RadialBarChart innerRadius="30%" outerRadius="100%" data={[
              { name: "Health", value: data?.kpis?.company_health_score?.value || 0, fill: "#0EA5A4" },
              { name: "Risk", value: data?.kpis?.business_risk_score?.value || 0, fill: "#EF4444" },
              { name: "Inv Health", value: data?.kpis?.inventory_health?.value || 0, fill: "#C89A2B" },
            ]} startAngle={180} endAngle={0}>
              <RadialBar dataKey="value" cornerRadius={8} label={{ position: "insideStart", fill: "#fff", fontSize: 11 }} />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
              <Tooltip />
            </RadialBarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="mt-4 bg-white border border-[#E5E7EB] rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-semibold text-ink">Active Business Alerts</div>
          <Button variant="outline" size="sm" className="h-8 border-[#E5E7EB]" onClick={() => nav("/app/business-alerts")} data-testid="ecc-view-alerts">
            View all <ChevronRight size={13} className="ml-1" />
          </Button>
        </div>
        {alerts.count === 0 ? <div className="text-ink-muted text-sm py-4 text-center">All clear — no active alerts</div> : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {alerts.alerts.slice(0, 9).map((a) => (
              <button key={a.id} className={`text-left rounded-lg border p-3 hover:shadow-sm transition ${SEV_COLOR[a.severity] || ""}`}
                onClick={() => goToDrill(a.drill)} data-testid={`alert-${a.id}`}>
                <div className="flex items-start justify-between mb-1">
                  <div className="text-[10px] uppercase tracking-widest font-semibold">{a.kind.replace(/_/g, " ")}</div>
                  <AlertOctagon size={13} />
                </div>
                <div className="text-sm font-semibold">{a.title}</div>
                <div className="text-[11px] mt-1 opacity-80">{a.description}</div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ==========================================================
// ORDER TRACE
// ==========================================================
export function OrderTracePage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [trace, setTrace] = useState(null);
  const [busy, setBusy] = useState(false);

  const search = async (query) => {
    if (!query || query.length < 2) return;
    try {
      const r = await api.get(`/analytics/trace/search?q=${encodeURIComponent(query)}`);
      setResults(r.data.results || []);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const openTrace = async (id) => {
    setBusy(true); setSelected(id);
    try {
      const r = await api.get(`/analytics/trace/order/${id}`);
      setTrace(r.data);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  // Auto-load latest primary order on mount
  useEffect(() => {
    (async () => {
      try {
        const r = await api.get("/collections/primary-orders?limit=1");
        const first = r.data.data?.[0];
        if (first) openTrace(first.id);
      } catch (err) { void err; }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "BI", "Order Trace"]}
        title="Live Order Trace"
        subtitle="End-to-end 20-node journey — from Product → Batch → Order → Invoice → Dispatch → GRN → Payment → Ledger → Audit"
      />
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-3 mb-4">
        <div className="flex gap-2">
          <Input placeholder="Search by order no / invoice no / order id..."
            value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search(q)}
            className="h-10" data-testid="trace-search" />
          <Button className="bg-gold hover:bg-gold-dark text-white h-10" onClick={() => search(q)} data-testid="trace-search-btn">
            <Search size={14} className="mr-2" /> Find
          </Button>
        </div>
        {results.length > 0 && (
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {results.map((r) => (
              <button key={r.id} className={`text-left border rounded-lg p-2 hover:bg-canvas ${selected === r.id ? "border-gold bg-gold-tint/50" : "border-[#E5E7EB]"}`}
                onClick={() => openTrace(r.id)} data-testid={`trace-result-${r.id}`}>
                <div className="text-xs font-semibold text-ink">{r.order_no || r.id}</div>
                <div className="text-[11px] text-ink-muted">{r.party_name || "—"} · {r.type} · {money(r.total)}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {busy ? (
        <div className="p-10 text-center text-ink-muted"><Loader2 size={16} className="animate-spin inline mr-2" /> Loading trace...</div>
      ) : trace ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-white border border-[#E5E7EB] rounded-xl p-4" data-testid="trace-timeline">
            <div className="text-sm font-semibold text-ink mb-4">Journey Timeline · {trace.order?.order_no || trace.order?.id}</div>
            <div className="space-y-0">
              {(trace.timeline || []).map((step, i) => {
                const ok = step.status === "ok";
                const na = step.status === "n/a";
                return (
                  <div key={i} className="flex items-start gap-3 py-2 border-l-2 pl-4 relative"
                    style={{ borderColor: ok ? "#0EA5A4" : na ? "#CBD5E1" : "#F59E0B" }}>
                    <div className={`absolute -left-[7px] top-3 w-3 h-3 rounded-full ${ok ? "bg-emerald-500" : na ? "bg-slate-300" : "bg-amber-500"}`} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-semibold text-ink-muted">STEP {step.step}</span>
                        <span className="text-sm font-semibold text-ink">{step.node}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded ${ok ? "bg-emerald-50 text-emerald-700" : na ? "bg-slate-50 text-slate-500" : "bg-amber-50 text-amber-700"}`}>
                          {step.status}
                        </span>
                      </div>
                      <div className="text-[12px] text-ink-muted mt-0.5">
                        {step.label} {step.at && <span className="ml-2 text-[10px]">· {dateStr(step.at)}</span>}
                        {step.id && <span className="ml-2 text-[10px] font-mono">· {step.id}</span>}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="space-y-3">
            <div className="bg-white border border-[#E5E7EB] rounded-xl p-4">
              <div className="text-[10px] uppercase tracking-widest text-ink-muted font-semibold mb-2">Order</div>
              <div className="text-sm font-semibold text-ink">{trace.order?.order_no}</div>
              <div className="text-xs text-ink-muted mt-1">Type: {trace.order_type} · {money(trace.order?.total)} · {trace.order?.status}</div>
              <div className="text-xs text-ink-muted mt-1">Party: {trace.order?.party_name}</div>
            </div>
            {trace.invoice && (
              <div className="bg-white border border-[#E5E7EB] rounded-xl p-4">
                <div className="text-[10px] uppercase tracking-widest text-ink-muted font-semibold mb-2">Invoice</div>
                <div className="text-sm font-semibold text-ink">{trace.invoice.invoice_no}</div>
                <div className="text-xs text-ink-muted">{money(trace.invoice.total)} · {trace.invoice.status}</div>
              </div>
            )}
            {trace.dispatch && (
              <div className="bg-white border border-[#E5E7EB] rounded-xl p-4">
                <div className="text-[10px] uppercase tracking-widest text-ink-muted font-semibold mb-2">Dispatch</div>
                <div className="text-sm font-semibold text-ink">{trace.dispatch.dispatch_no}</div>
                <div className="text-xs text-ink-muted">LR {trace.dispatch.lr_no} · {trace.dispatch.status}</div>
              </div>
            )}
            <div className="bg-white border border-[#E5E7EB] rounded-xl p-4">
              <div className="text-[10px] uppercase tracking-widest text-ink-muted font-semibold mb-2">Audit ({trace.audit_trail?.length || 0})</div>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {(trace.audit_trail || []).slice(0, 8).map((a) => (
                  <div key={a.id} className="text-[11px] text-ink-muted">
                    <span className="font-medium text-ink">{a.action}</span> by {a.actor_email} · {dateStr(a.timestamp)}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-10 text-center text-ink-muted">Search for an order to see its complete journey</div>
      )}
    </div>
  );
}

// ==========================================================
// PARTY 360
// ==========================================================
export function Party360Page() {
  const [type, setType] = useState("distributor");
  const [partyId, setPartyId] = useState("");
  const [parties, setParties] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    const coll = { distributor: "distributors", retailer: "retailers", customer: "customers", company: "branches" }[type];
    api.get(`/collections/${coll}?limit=500`).then((r) => {
      setParties(r.data.data || []);
      if (r.data.data?.[0]) setPartyId(r.data.data[0].id);
    });
  }, [type]);

  useEffect(() => {
    if (!partyId) return;
    setLoading(true);
    api.get(`/analytics/party360/${type}/${partyId}`).then((r) => setData(r.data))
      .catch((e) => toast.error(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [type, partyId]);

  const profile = data?.profile;
  const fin = data?.financials || {};
  const perf = data?.performance || {};

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "BI", "Party 360"]}
        title="Party 360°"
        subtitle="Unified profile — financials, orders, payments, returns, claims, credit/debit notes, inventory, audit"
      />
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-3 mb-4 grid grid-cols-1 md:grid-cols-4 gap-2 items-end">
        <div>
          <Label className="text-[10px] uppercase tracking-widest text-ink-muted">Party type</Label>
          <Select value={type} onValueChange={setType}>
            <SelectTrigger className="h-10 border-[#E5E7EB]" data-testid="p360-type"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="distributor">Distributor</SelectItem>
              <SelectItem value="retailer">Retailer</SelectItem>
              <SelectItem value="customer">Customer</SelectItem>
              <SelectItem value="company">Branch (Company)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="md:col-span-2">
          <Label className="text-[10px] uppercase tracking-widest text-ink-muted">Party</Label>
          <Select value={partyId} onValueChange={setPartyId}>
            <SelectTrigger className="h-10 border-[#E5E7EB]" data-testid="p360-party"><SelectValue placeholder="Select" /></SelectTrigger>
            <SelectContent className="max-h-72">
              {parties.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button variant="outline" className="h-10 border-[#E5E7EB]" onClick={() => partyId && api.get(`/analytics/party360/${type}/${partyId}`).then((r) => setData(r.data))} data-testid="p360-refresh">
          <RefreshCw size={14} className="mr-2" /> Refresh
        </Button>
      </div>

      {loading || !data ? (
        <div className="p-10 text-center text-ink-muted"><Loader2 size={16} className="animate-spin inline mr-2" /> Loading party profile...</div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-4">
            <div className="bg-white border border-[#E5E7EB] rounded-xl p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-12 h-12 rounded-xl bg-gold-tint flex items-center justify-center">
                  {type === "distributor" ? <Truck className="text-gold-dark" /> : type === "retailer" ? <Store className="text-gold-dark" /> : type === "customer" ? <User2 className="text-gold-dark" /> : <Building2 className="text-gold-dark" />}
                </div>
                <div>
                  <div className="text-lg font-bold text-ink">{profile?.name || "—"}</div>
                  <div className="text-xs text-ink-muted">{profile?.email || profile?.region || profile?.id}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-ink-muted">Phone:</span> <span className="text-ink">{profile?.phone || "—"}</span></div>
                <div><span className="text-ink-muted">Branch:</span> <span className="text-ink">{profile?.branch_id || "—"}</span></div>
                <div><span className="text-ink-muted">Credit Limit:</span> <span className="text-ink">{money(fin.credit_limit)}</span></div>
                <div><span className="text-ink-muted">Util:</span> <span className="text-ink">{fin.credit_utilization ?? "—"}%</span></div>
              </div>
            </div>
            <div className="lg:col-span-3 grid grid-cols-2 md:grid-cols-4 gap-3">
              <KpiCard label="Total Billed" value={money(fin.total_billed)} delta={`${perf.invoice_count} inv`} />
              <KpiCard label="Paid" value={money(fin.total_paid)} delta={`${perf.payment_count} pmt`} />
              <KpiCard label="Outstanding" value={money(fin.outstanding)} delta={money(fin.overdue_amount) + " overdue"} trend="down" />
              <KpiCard label="Avg Order" value={money(perf.avg_order_value)} delta={`${perf.return_rate}% ret`} />
              <KpiCard label="Health Score" value={`${data.health_score}/100`} delta={data.health_score >= 70 ? "Healthy" : "At risk"} />
              <KpiCard label="Risk Score" value={`${data.risk_score}/100`} delta={data.risk_score < 30 ? "Low risk" : "Elevated"} trend={data.risk_score < 30 ? "up" : "down"} />
              <KpiCard label="Returns" value={perf.return_rate + "%"} delta={`${data.returns?.length || 0} events`} trend="down" />
              <KpiCard label="Claims" value={perf.claim_count} delta={`${perf.credit_note_count} CN`} trend="down" />
            </div>
          </div>

          <Tabs defaultValue="timeline">
            <TabsList className="bg-canvas border border-[#E5E7EB]">
              <TabsTrigger value="timeline" data-testid="p360-tab-timeline">Timeline</TabsTrigger>
              <TabsTrigger value="invoices" data-testid="p360-tab-inv">Invoices</TabsTrigger>
              <TabsTrigger value="payments" data-testid="p360-tab-pay">Payments</TabsTrigger>
              <TabsTrigger value="orders" data-testid="p360-tab-ord">Orders</TabsTrigger>
              <TabsTrigger value="returns" data-testid="p360-tab-ret">Returns & Claims</TabsTrigger>
              <TabsTrigger value="notes" data-testid="p360-tab-notes">CN/DN</TabsTrigger>
              <TabsTrigger value="inventory" data-testid="p360-tab-inv2">Inventory</TabsTrigger>
              <TabsTrigger value="audit" data-testid="p360-tab-audit">Audit</TabsTrigger>
            </TabsList>
            <TabsContent value="timeline" className="mt-4">
              <div className="bg-white border border-[#E5E7EB] rounded-xl p-4 max-h-[600px] overflow-y-auto">
                <div className="space-y-2">
                  {(data.timeline || []).map((e, i) => (
                    <div key={i} className="flex items-start gap-3 py-2 border-l-2 border-[#E5E7EB] pl-3">
                      <span className={`text-[10px] uppercase font-semibold px-2 py-0.5 rounded ${
                        e.type === "invoice" ? "bg-blue-50 text-blue-700" :
                        e.type === "payment" ? "bg-emerald-50 text-emerald-700" :
                        e.type === "return" ? "bg-amber-50 text-amber-700" :
                        e.type === "claim" ? "bg-purple-50 text-purple-700" :
                        e.type === "credit_note" ? "bg-teal-50 text-teal-700" :
                        "bg-slate-50 text-slate-600"}`}>{e.type}</span>
                      <div className="flex-1 text-xs text-ink">{e.label} <span className="text-ink-muted ml-1">· {dateStr(e.at)}</span></div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>
            <TabsContent value="invoices" className="mt-4">
              <DataTable data={data.invoices || []} testId="p360-invoices" pageSize={10}
                columns={[
                  { key: "invoice_no", label: "Invoice" }, { key: "issued_on", label: "Issued", type: "date" },
                  { key: "total", label: "Total", type: "currency", align: "right" },
                  { key: "paid", label: "Paid", type: "currency", align: "right" },
                  { key: "status", label: "Status", type: "status" },
                ]} />
            </TabsContent>
            <TabsContent value="payments" className="mt-4">
              <DataTable data={data.payments || []} testId="p360-payments" pageSize={10}
                columns={[
                  { key: "id", label: "ID" }, { key: "received_at", label: "Received", type: "date" },
                  { key: "amount", label: "Amount", type: "currency", align: "right" },
                  { key: "method", label: "Method", type: "chip" }, { key: "status", label: "Status", type: "status" },
                ]} />
            </TabsContent>
            <TabsContent value="orders" className="mt-4">
              <DataTable data={[...(data.primary_orders || []), ...(data.secondary_orders || []), ...(data.customer_orders || [])]}
                testId="p360-orders" pageSize={10}
                columns={[
                  { key: "order_no", label: "Order" }, { key: "type", label: "Type", type: "chip" },
                  { key: "total", label: "Total", type: "currency", align: "right" },
                  { key: "status", label: "Status", type: "status" }, { key: "created_at", label: "Created", type: "date" },
                ]} />
            </TabsContent>
            <TabsContent value="returns" className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <ChartCard title="Returns" subtitle={`${data.returns?.length || 0} events`}>
                  <DataTable data={data.returns || []} pageSize={6}
                    columns={[
                      { key: "return_no", label: "Return" }, { key: "reason", label: "Reason", type: "chip" },
                      { key: "total", label: "Value", type: "currency", align: "right" },
                      { key: "status", label: "Status", type: "status" },
                    ]} />
                </ChartCard>
                <ChartCard title="Claims" subtitle={`${data.claims?.length || 0} events`}>
                  <DataTable data={data.claims || []} pageSize={6}
                    columns={[
                      { key: "claim_no", label: "Claim" }, { key: "type", label: "Type", type: "chip" },
                      { key: "amount", label: "Amount", type: "currency", align: "right" },
                      { key: "status", label: "Status", type: "status" },
                    ]} />
                </ChartCard>
              </div>
            </TabsContent>
            <TabsContent value="notes" className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <ChartCard title="Credit Notes" subtitle={`${data.credit_notes?.length || 0}`}>
                  <DataTable data={data.credit_notes || []} pageSize={6}
                    columns={[
                      { key: "cn_no", label: "CN" }, { key: "reason", label: "Reason", type: "chip" },
                      { key: "total", label: "Amount", type: "currency", align: "right" },
                      { key: "created_at", label: "Issued", type: "date" },
                    ]} />
                </ChartCard>
                <ChartCard title="Debit Notes" subtitle={`${data.debit_notes?.length || 0}`}>
                  <DataTable data={data.debit_notes || []} pageSize={6}
                    columns={[
                      { key: "dn_no", label: "DN" }, { key: "reason", label: "Reason", type: "chip" },
                      { key: "total", label: "Amount", type: "currency", align: "right" },
                      { key: "created_at", label: "Issued", type: "date" },
                    ]} />
                </ChartCard>
              </div>
            </TabsContent>
            <TabsContent value="inventory" className="mt-4">
              <DataTable data={data.inventory || []} testId="p360-inventory" pageSize={12}
                columns={[
                  { key: "sku_code", label: "SKU" }, { key: "batch_id", label: "Batch" },
                  { key: "available", label: "Available", align: "right" },
                  { key: "reserved", label: "Reserved", align: "right" },
                  { key: "damaged", label: "Damaged", align: "right" },
                  { key: "returned", label: "Returned", align: "right" },
                ]} />
            </TabsContent>
            <TabsContent value="audit" className="mt-4">
              <DataTable data={data.audit_trail || []} testId="p360-audit" pageSize={15}
                columns={[
                  { key: "action", label: "Action", type: "chip" },
                  { key: "entity_type", label: "Entity" },
                  { key: "actor_email", label: "Actor" },
                  { key: "timestamp", label: "When", type: "date" },
                ]} />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}

// ==========================================================
// SALES ANALYTICS
// ==========================================================
export function SalesAnalyticsPage() {
  const [filters, setFilters] = useState({ range: "month" });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => {
    setLoading(true);
    const p = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => v && p.set(k, v));
    api.get(`/analytics/sales?${p.toString()}`).then((r) => setData(r.data)).finally(() => setLoading(false));
  }, [filters]);
  useEffect(load, [load]);

  return (
    <div className="animate-in-fade">
      <PageHeader crumbs={["Dashboard", "BI", "Sales Analytics"]} title="Sales Analytics" subtitle="Revenue trends, top SKUs, branch mix, funnel" />
      <GlobalFilters value={filters} onChange={setFilters} testIdPrefix="sa" />
      {loading || !data ? <div className="p-10 text-center text-ink-muted mt-4"><Loader2 className="animate-spin inline mr-2" size={16} /> Loading...</div> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            <KpiCard label="Revenue" value={money(data.totals?.revenue)} delta={`${data.totals?.count} invoices`} />
            <KpiCard label="Avg Order Value" value={money(data.totals?.avg_order_value)} delta="per invoice" />
            <KpiCard label="Top Branch" value={data.by_branch?.[0]?.name || "—"} delta={money(data.by_branch?.[0]?.revenue)} />
            <KpiCard label="Top Distributor" value={data.by_distributor?.[0]?.party_name || "—"} delta={money(data.by_distributor?.[0]?.revenue)} />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <ChartCard title="Revenue Time Series" className="lg:col-span-2" testId="sa-timeseries">
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={data.series || []}>
                  <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                  <XAxis dataKey="period" tick={{ fill: "#64748B", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#64748B", fontSize: 11 }} tickFormatter={money} />
                  <Tooltip formatter={(v) => fullMoney(v)} />
                  <Line type="monotone" dataKey="revenue" stroke="#C89A2B" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="tax" stroke="#0EA5A4" strokeWidth={1.5} dot={false} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Order Funnel" testId="sa-funnel">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={data.funnel || []} layout="vertical">
                  <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                  <XAxis type="number" tick={{ fill: "#64748B", fontSize: 11 }} />
                  <YAxis dataKey="stage" type="category" width={80} tick={{ fill: "#64748B", fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#C89A2B" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="Top SKUs" subtitle="By revenue" testId="sa-top-skus">
              <ResponsiveContainer width="100%" height={280}>
                <Treemap data={(data.top_skus || []).map((s) => ({ name: s.sku_code, size: s.revenue, product: s.product_name }))}
                  dataKey="size" stroke="#fff" fill="#C89A2B">
                  <Tooltip formatter={(v, n, p) => [`${money(v)}`, p.payload?.product || ""]} />
                </Treemap>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Revenue by Branch" testId="sa-by-branch">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={data.by_branch || []}>
                  <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                  <XAxis dataKey="name" tick={{ fill: "#64748B", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#64748B", fontSize: 11 }} tickFormatter={money} />
                  <Tooltip formatter={(v) => fullMoney(v)} />
                  <Bar dataKey="revenue" fill="#8B6914" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </>
      )}
    </div>
  );
}

// ==========================================================
// INVENTORY ANALYTICS
// ==========================================================
export function InventoryAnalyticsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    api.get("/analytics/inventory").then((r) => setData(r.data)).finally(() => setLoading(false));
  }, []);
  return (
    <div className="animate-in-fade">
      <PageHeader crumbs={["Dashboard", "BI", "Inventory Analytics"]} title="Inventory Analytics" subtitle="Buckets, scope value, top SKUs, near-expiry" />
      {loading || !data ? <div className="p-10 text-center text-ink-muted"><Loader2 className="animate-spin inline mr-2" size={16} /> Loading...</div> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard label="Total Units" value={data.totals?.total_units?.toLocaleString()} delta="all buckets" />
            <KpiCard label="Total Value" value={money(data.totals?.total_value)} delta="trade price" />
            <KpiCard label="Damaged %" value={`${data.totals?.damaged_pct}%`} delta="of total" trend="down" />
            <KpiCard label="Expired Batches" value={data.expired_batches_count} delta="active" trend="down" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <ChartCard title="Inventory Buckets" testId="ia-buckets">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={data.buckets || []} dataKey="value" nameKey="name" outerRadius={100} innerRadius={50}>
                    {(data.buckets || []).map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Value by Scope" testId="ia-scope">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={data.by_scope_value || []}>
                  <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                  <XAxis dataKey="scope" tick={{ fill: "#64748B", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#64748B", fontSize: 11 }} tickFormatter={money} />
                  <Tooltip formatter={(v) => fullMoney(v)} />
                  <Bar dataKey="value" fill="#0EA5A4" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Top SKUs" subtitle="By inventory value" testId="ia-top-skus">
              <ResponsiveContainer width="100%" height={280}>
                <Treemap data={(data.top_skus || []).map((s) => ({ name: s.sku_code, size: s.value }))} dataKey="size" fill="#C89A2B" stroke="#fff">
                  <Tooltip formatter={(v) => money(v)} />
                </Treemap>
              </ResponsiveContainer>
            </ChartCard>
          </div>
          <div className="mt-4 bg-white border border-[#E5E7EB] rounded-xl p-4">
            <div className="text-sm font-semibold text-ink mb-3">Near-expiry batches</div>
            <DataTable data={data.near_expiry_batches || []} testId="ia-near-expiry" pageSize={10}
              columns={[
                { key: "batch_no", label: "Batch" }, { key: "sku_code", label: "SKU" },
                { key: "manufactured_on", label: "Mfd", type: "date" }, { key: "expires_on", label: "Expires", type: "date" },
              ]} />
          </div>
        </>
      )}
    </div>
  );
}

// ==========================================================
// FINANCE ANALYTICS
// ==========================================================
export function FinanceAnalyticsPage() {
  const [filters, setFilters] = useState({ range: "month" });
  const [data, setData] = useState(null);
  const [prof, setProf] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    const p = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => v && p.set(k, v));
    Promise.all([api.get(`/analytics/finance?${p.toString()}`), api.get(`/analytics/profitability?${p.toString()}`)])
      .then(([f, pr]) => { setData(f.data); setProf(pr.data); })
      .finally(() => setLoading(false));
  }, [filters]);

  return (
    <div className="animate-in-fade">
      <PageHeader crumbs={["Dashboard", "BI", "Finance Analytics"]} title="Finance & Profitability" subtitle="Cash flow, aging, collection rate, waterfall P&L" />
      <GlobalFilters value={filters} onChange={setFilters} showParty={false} testIdPrefix="fa" />
      {loading || !data ? <div className="p-10 text-center text-ink-muted mt-4"><Loader2 className="animate-spin inline mr-2" size={16} /> Loading...</div> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            <KpiCard label="Cash In" value={money(data.totals?.cash_in)} delta="payments" />
            <KpiCard label="Cash Out" value={money(data.totals?.cash_out)} delta="expenses+claims" trend="down" />
            <KpiCard label="Collection Rate" value={`${data.totals?.collection_rate}%`} delta="collected/billed" />
            <KpiCard label="Total Outstanding" value={money(data.totals?.total_outstanding)} delta="receivable" trend="down" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <ChartCard title="Cash Flow" className="lg:col-span-2" testId="fa-cashflow">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={data.series || []}>
                  <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                  <XAxis dataKey="period" tick={{ fill: "#64748B", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#64748B", fontSize: 11 }} tickFormatter={money} />
                  <Tooltip formatter={(v) => fullMoney(v)} />
                  <Bar dataKey="cash_in" fill="#0EA5A4" name="Cash In" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="cash_out" fill="#EF4444" name="Cash Out" radius={[4, 4, 0, 0]} />
                  <Line type="monotone" dataKey="net" stroke="#C89A2B" strokeWidth={2} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Payment Methods" testId="fa-methods">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={data.by_method || []} dataKey="value" nameKey="method" outerRadius={100}>
                    {(data.by_method || []).map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v) => fullMoney(v)} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="AR Aging" subtitle="Days past due" testId="fa-aging">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.aging || []}>
                  <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                  <XAxis dataKey="bucket" tick={{ fill: "#64748B", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#64748B", fontSize: 11 }} tickFormatter={money} />
                  <Tooltip formatter={(v) => fullMoney(v)} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {(data.aging || []).map((_, i) => <Cell key={i} fill={["#0EA5A4","#F59E0B","#EF4444","#7C2D12"][i]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="P&L Waterfall" subtitle={`Margin: ${prof?.margin_pct}%`} testId="fa-waterfall">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={prof?.waterfall || []}>
                  <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                  <XAxis dataKey="label" tick={{ fill: "#64748B", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#64748B", fontSize: 11 }} tickFormatter={money} />
                  <Tooltip formatter={(v) => fullMoney(v)} />
                  <Bar dataKey="value" radius={[4, 4, 4, 4]}>
                    {(prof?.waterfall || []).map((row, i) => (
                      <Cell key={i} fill={row.type === "start" || row.type === "end" ? "#C89A2B" : (row.value < 0 ? "#EF4444" : "#0EA5A4")} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </>
      )}
    </div>
  );
}

// ==========================================================
// BUSINESS ALERTS
// ==========================================================
export function BusinessAlertsPage() {
  const [data, setData] = useState({ count: 0, alerts: [], by_kind: {}, by_severity: {} });
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const nav = useNavigate();
  useEffect(() => {
    setLoading(true);
    api.get("/analytics/alerts").then((r) => setData(r.data)).finally(() => setLoading(false));
  }, [reload]);

  const goto = (drill) => {
    if (!drill) return;
    if (drill.startsWith("party360/")) nav(`/app/${drill}`);
    else nav(`/app/${drill}`);
  };

  return (
    <div className="animate-in-fade">
      <PageHeader crumbs={["Dashboard", "BI", "Business Alerts"]} title="Business Alert Engine"
        subtitle="Live 12-type alerts — low inventory, high outstanding, credit exceeded, payment delay, high returns/claims, pending approvals, near expiry, dispatch delay, exceptions"
        actions={<Button variant="outline" className="h-10 border-[#E5E7EB]" onClick={() => setReload((v) => v + 1)}><RefreshCw size={14} className="mr-2" /> Refresh</Button>}
      />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
        <KpiCard label="Total" value={data.count} delta="active" />
        <KpiCard label="High" value={data.by_severity?.high || 0} delta="critical" trend="down" />
        <KpiCard label="Medium" value={data.by_severity?.medium || 0} delta="review" />
        <KpiCard label="Low" value={data.by_severity?.low || 0} delta="watch" />
        <KpiCard label="Kinds" value={Object.keys(data.by_kind || {}).length} delta="categories" />
      </div>
      {loading ? <div className="p-10 text-center text-ink-muted"><Loader2 className="animate-spin inline mr-2" size={16} /> Loading...</div> : data.alerts.length === 0 ? (
        <div className="p-10 text-center bg-white border border-[#E5E7EB] rounded-xl">
          <CheckCircle2 size={40} className="text-emerald-500 mx-auto mb-2" />
          <div className="text-lg font-semibold text-ink">All clear</div>
          <div className="text-ink-muted text-sm">No active business alerts</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.alerts.map((a) => (
            <button key={a.id} className={`text-left rounded-xl border p-4 hover:shadow-md transition ${SEV_COLOR[a.severity]}`}
              onClick={() => goto(a.drill)} data-testid={`ba-${a.id}`}>
              <div className="flex items-start justify-between mb-2">
                <div className="text-[10px] uppercase tracking-widest font-semibold">{a.kind.replace(/_/g, " ")}</div>
                <AlertOctagon size={14} />
              </div>
              <div className="text-sm font-semibold mb-1">{a.title}</div>
              <div className="text-[11px] opacity-80">{a.description}</div>
              <div className="mt-2 text-[10px] uppercase tracking-widest font-semibold flex items-center gap-1">Drill in <ArrowRight size={11} /></div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ==========================================================
// SCORECARDS
// ==========================================================
export function ScorecardsPage() {
  const [entity, setEntity] = useState("distributor");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    api.get(`/analytics/scorecards/${entity}`).then((r) => setData(r.data)).finally(() => setLoading(false));
  }, [entity]);

  const cols = useMemo(() => {
    if (entity === "distributor") return [
      { key: "name", label: "Distributor" }, { key: "sales_score", label: "Sales", align: "right" },
      { key: "collection_score", label: "Collect", align: "right" }, { key: "return_score", label: "Return", align: "right" },
      { key: "claim_score", label: "Claim", align: "right" }, { key: "overall", label: "Overall", align: "right", render: (r) => (
        <span className="font-semibold">{r.overall} <span className={`ml-1 text-[10px] px-1.5 py-0.5 rounded ${
          r.grade === "A" ? "bg-emerald-100 text-emerald-700" : r.grade === "B" ? "bg-teal-100 text-teal-700" :
          r.grade === "C" ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700"}`}>{r.grade}</span></span>
      )},
      { key: "billed", label: "Billed", type: "currency", align: "right" },
      { key: "returns", label: "Ret", align: "right" }, { key: "claims", label: "Clm", align: "right" },
    ];
    if (entity === "retailer") return [
      { key: "name", label: "Retailer" }, { key: "sales_score", label: "Sales", align: "right" },
      { key: "collection_score", label: "Collect", align: "right" }, { key: "return_score", label: "Return", align: "right" },
      { key: "overall", label: "Overall", align: "right", render: (r) => (
        <span className="font-semibold">{r.overall} <span className={`ml-1 text-[10px] px-1.5 py-0.5 rounded ${
          r.grade === "A" ? "bg-emerald-100 text-emerald-700" : r.grade === "B" ? "bg-teal-100 text-teal-700" :
          r.grade === "C" ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700"}`}>{r.grade}</span></span>
      )},
      { key: "billed", label: "Billed", type: "currency", align: "right" }, { key: "paid", label: "Paid", type: "currency", align: "right" },
    ];
    if (entity === "branch") return [
      { key: "name", label: "Branch" }, { key: "region", label: "Region" },
      { key: "revenue", label: "Revenue", type: "currency", align: "right" },
      { key: "collection_rate", label: "Coll %", align: "right" }, { key: "invoice_count", label: "Inv", align: "right" },
      { key: "overall", label: "Score", align: "right" },
    ];
    if (entity === "sales_executive") return [
      { key: "name", label: "Executive" }, { key: "revenue", label: "Revenue", type: "currency", align: "right" },
      { key: "count", label: "Count", align: "right" }, { key: "overall", label: "Score", align: "right" },
    ];
    if (entity === "warehouse") return [
      { key: "name", label: "Warehouse" }, { key: "grn_count", label: "GRNs", align: "right" },
      { key: "variance_count", label: "Variances", align: "right" }, { key: "accuracy", label: "Accuracy %", align: "right" },
      { key: "overall", label: "Score", align: "right" },
    ];
    return [{ key: "name", label: "Entity" }, { key: "revenue", label: "Revenue", type: "currency", align: "right" },
             { key: "collection_rate", label: "Coll %", align: "right" }, { key: "overall", label: "Score", align: "right" }];
  }, [entity]);

  return (
    <div className="animate-in-fade">
      <PageHeader crumbs={["Dashboard", "BI", "Scorecards"]} title="Business Scorecards"
        subtitle="Auto-calculated performance scores — sales, collections, returns, claims"
      />
      <div className="flex items-center gap-2 mb-4">
        {["distributor", "retailer", "branch", "sales_executive", "warehouse", "company"].map((e) => (
          <Button key={e} variant={entity === e ? "default" : "outline"}
            className={`h-9 ${entity === e ? "bg-gold hover:bg-gold-dark text-white" : "border-[#E5E7EB]"}`}
            onClick={() => setEntity(e)} data-testid={`sc-tab-${e}`}>{e.replace("_", " ")}</Button>
        ))}
      </div>
      {loading || !data ? <div className="p-10 text-center text-ink-muted"><Loader2 className="animate-spin inline mr-2" size={16} /> Loading...</div> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <KpiCard label="Total entities" value={data.count} delta={entity} />
            <KpiCard label="Grade A" value={(data.rows || []).filter((r) => r.grade === "A").length || (data.rows || []).filter((r) => (r.overall || 0) >= 85).length} delta=">= 85" />
            <KpiCard label="Grade B/C" value={(data.rows || []).filter((r) => (r.overall || 0) >= 55 && (r.overall || 0) < 85).length} delta="55-84" />
            <KpiCard label="Grade D" value={(data.rows || []).filter((r) => (r.overall || 0) < 55).length} delta="<55" trend="down" />
          </div>
          {(entity === "distributor" || entity === "retailer" || entity === "branch") && (data.rows || []).length > 0 && (
            <ChartCard title="Top 10 by score" className="mb-4" testId="sc-chart">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={(data.rows || []).slice(0, 10)}>
                  <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                  <XAxis dataKey="name" tick={{ fill: "#64748B", fontSize: 10 }} interval={0} angle={-15} textAnchor="end" height={60} />
                  <YAxis tick={{ fill: "#64748B", fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="overall" fill="#C89A2B" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          )}
          <DataTable data={data.rows || []} columns={cols} testId="sc-table" pageSize={15} />
        </>
      )}
    </div>
  );
}

// ==========================================================
// EXECUTIVE ANALYTICS HUB (Returns + Claims + Profitability compact)
// ==========================================================
export function ExecutiveAnalyticsHub() {
  const [filters, setFilters] = useState({ range: "month" });
  const [returns, setReturns] = useState(null);
  const [claims, setClaims] = useState(null);
  const [prof, setProf] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    const p = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => v && p.set(k, v));
    Promise.all([
      api.get(`/analytics/returns?${p.toString()}`),
      api.get(`/analytics/claims?${p.toString()}`),
      api.get(`/analytics/profitability?${p.toString()}`),
    ]).then(([r, c, pr]) => { setReturns(r.data); setClaims(c.data); setProf(pr.data); }).finally(() => setLoading(false));
  }, [filters]);

  return (
    <div className="animate-in-fade">
      <PageHeader crumbs={["Dashboard", "BI", "Executive Analytics"]} title="Executive Analytics"
        subtitle="Consolidated returns, claims, profitability views"
      />
      <GlobalFilters value={filters} onChange={setFilters} showParty={false} testIdPrefix="ea" />
      {loading || !returns || !claims || !prof ? <div className="p-10 text-center text-ink-muted mt-4"><Loader2 className="animate-spin inline mr-2" size={16} /> Loading...</div> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            <KpiCard label="Returns Count" value={returns.totals?.count} delta={money(returns.totals?.value)} trend="down" />
            <KpiCard label="Claims" value={claims.totals?.count} delta={money(claims.totals?.value)} trend="down" />
            <KpiCard label="Settled Claims" value={money(claims.totals?.settled)} delta="paid out" />
            <KpiCard label="Net Profit" value={money(prof.net_profit)} delta={`${prof.margin_pct}% margin`} />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="Returns by reason" testId="ea-ret-reason">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={returns.by_reason || []}>
                  <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                  <XAxis dataKey="reason" tick={{ fill: "#64748B", fontSize: 10 }} interval={0} angle={-15} textAnchor="end" height={70} />
                  <YAxis tick={{ fill: "#64748B", fontSize: 11 }} tickFormatter={money} />
                  <Tooltip formatter={(v) => fullMoney(v)} />
                  <Bar dataKey="value" fill="#EF4444" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Claims by type" testId="ea-clm-type">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={claims.by_type || []}>
                  <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                  <XAxis dataKey="type" tick={{ fill: "#64748B", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#64748B", fontSize: 11 }} tickFormatter={money} />
                  <Tooltip formatter={(v) => fullMoney(v)} />
                  <Bar dataKey="value" fill="#F59E0B" name="Claimed" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="settled" fill="#0EA5A4" name="Settled" radius={[6, 6, 0, 0]} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
            <ChartCard title="Return trend" testId="ea-ret-trend">
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={returns.series || []}>
                  <CartesianGrid strokeDasharray="2 4" stroke="#E5E7EB" />
                  <XAxis dataKey="period" tick={{ fill: "#64748B", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#64748B", fontSize: 11 }} tickFormatter={money} />
                  <Tooltip formatter={(v) => fullMoney(v)} />
                  <Area type="monotone" dataKey="value" stroke="#EF4444" fill="#FEE2E2" />
                </AreaChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Top returned SKUs" testId="ea-ret-skus">
              <DataTable data={returns.top_skus || []} pageSize={6}
                columns={[
                  { key: "sku_code", label: "SKU" }, { key: "product_name", label: "Product" },
                  { key: "qty", label: "Qty", align: "right" }, { key: "value", label: "Value", type: "currency", align: "right" },
                ]} />
            </ChartCard>
          </div>
        </>
      )}
    </div>
  );
}
