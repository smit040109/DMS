import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import KpiCard from "@/components/common/KpiCard";
import DataTable from "@/components/common/DataTable";
import StatusPill from "@/components/common/StatusPill";
import { useAuth } from "@/context/AuthContext";
import { useTenant } from "@/context/TenantContext";
import { ROLE_LABELS } from "@/lib/nav";
import { Button } from "@/components/ui/button";
import {
  DollarSign, Truck, Gauge, ShoppingCart, Wallet, Building2, Package,
  Users, BadgeCheck, Calendar, RefreshCw, Presentation, Sparkles, ChevronRight, Clock, AlertTriangle, CheckCircle2, Info
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar,
} from "recharts";

const ICONS = [DollarSign, Truck, Gauge, ShoppingCart, Wallet, Building2, Package, Users, BadgeCheck];

function severityIcon(sev) {
  if (sev === "success") return { Icon: CheckCircle2, cls: "text-emerald-600 bg-emerald-50" };
  if (sev === "warning") return { Icon: AlertTriangle, cls: "text-amber-600 bg-amber-50" };
  if (sev === "info") return { Icon: Info, cls: "text-blue-600 bg-blue-50" };
  return { Icon: Clock, cls: "text-slate-600 bg-slate-100" };
}

function formatAgo(iso) {
  try {
    const dt = new Date(iso);
    const diff = (Date.now() - dt.getTime()) / 1000;
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  } catch { return "—"; }
}

export default function Dashboard() {
  const { user } = useAuth();
  const { tenant, brandName } = useTenant();
  const [kpis, setKpis] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [activity, setActivity] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    Promise.all([
      api.get("/dashboard/kpis"),
      api.get("/dashboard/analytics"),
      api.get("/dashboard/activity"),
      api.get("/dashboard/tasks"),
      api.get("/collections/secondary-orders"),
    ])
      .then(([k, a, ac, tk, o]) => {
        if (!mounted) return;
        setKpis(k.data.kpis || []);
        setAnalytics(a.data);
        setActivity(ac.data.activity || []);
        setTasks(tk.data.tasks || []);
        setOrders((o.data.data || []).slice(0, 6));
      })
      .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, [user?.role]);

  const trendData = (analytics?.primary_trend || []).map((v, i) => ({
    month: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][i] || `M${i + 1}`,
    value: v,
  }));

  const statusDist = analytics?.orders_by_status || [];

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Operations", "Distribution"]}
        title="Role-adaptive command dashboard"
        subtitle={`Signed in as ${user?.name} · ${ROLE_LABELS[user?.role]}`}
        actions={
          <>
            <Button variant="outline" className="border-[#E5E7EB] h-10" data-testid="dash-refresh">
              <RefreshCw size={14} className="mr-2" /> Refresh
            </Button>
            <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="dash-drill">
              <Presentation size={14} className="mr-2" /> Drill into module
            </Button>
          </>
        }
      />

      {/* Meta strip */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl card-soft p-5 mb-6 grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {[
          { label: "Organization", value: brandName || tenant?.name || "VayuERP Platform", icon: Building2 },
          { label: "Industry", value: (tenant?.industry || "distribution").replace(/\b\w/g, (c) => c.toUpperCase()), icon: Package },
          { label: "Current role", value: ROLE_LABELS[user?.role] || user?.role, icon: BadgeCheck },
          { label: "Currency · TZ", value: `${tenant?.currency || "USD"} · ${tenant?.timezone || "UTC"}`, icon: Calendar },
          { label: "Last sync", value: "Just now", icon: RefreshCw },
          { label: "Alerts", value: `${(analytics?.orders_by_status || []).length ? "Live" : "—"}`, icon: AlertTriangle, tone: "warning" },
        ].map((s) => (
          <div key={s.label} className="min-w-0">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] text-ink-muted font-semibold">
              <s.icon size={13} />{s.label}
            </div>
            <div className={`mt-1.5 text-sm font-semibold truncate ${s.tone === "warning" ? "text-amber-700" : "text-ink"}`}>
              {s.value}
            </div>
          </div>
        ))}
      </div>

      {/* KPIs */}
      <div className="mb-6">
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="font-display font-bold text-xl text-ink">KPI overview</h2>
          <span className="text-xs text-ink-muted">Updated 2 mins ago</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {kpis.map((k, i) => (
            <KpiCard key={k.label} {...k} icon={ICONS[i % ICONS.length]} accent={i === 0} />
          ))}
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-[#E5E7EB] card-soft p-5">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="font-display font-bold text-lg text-ink">Primary trend</h3>
              <p className="text-xs text-ink-muted">Cross-module performance index</p>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full bg-canvas border border-[#E5E7EB] text-ink-muted">Last 12 months</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="gold-area" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#C9A227" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#C9A227" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#F1F5F9" vertical={false} />
              <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fill: "#6B7280", fontSize: 11 }} />
              <YAxis tickLine={false} axisLine={false} tick={{ fill: "#6B7280", fontSize: 11 }} domain={[0, 100]} />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: "1px solid #E5E7EB", fontSize: 12 }}
                labelStyle={{ color: "#1F2937", fontWeight: 600 }}
              />
              <Area type="monotone" dataKey="value" stroke="#A67C00" strokeWidth={2} fill="url(#gold-area)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl border border-[#E5E7EB] card-soft p-5">
          <h3 className="font-display font-bold text-lg text-ink">Status distribution</h3>
          <p className="text-xs text-ink-muted mb-4">Operational health by active workflow</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={statusDist} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#F1F5F9" horizontal={false} />
              <XAxis type="number" hide />
              <YAxis dataKey="status" type="category" tickLine={false} axisLine={false} tick={{ fill: "#6B7280", fontSize: 11 }} width={70} />
              <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #E5E7EB", fontSize: 12 }} />
              <Bar dataKey="count" radius={[0, 6, 6, 0]} fill="#C9A227" barSize={22} />
            </BarChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-2 gap-3 mt-4">
            {statusDist.map((s) => (
              <div key={s.status} className="rounded-lg border border-[#E5E7EB] p-3">
                <div className="text-[11px] text-ink-muted font-semibold uppercase tracking-wider">{s.status}</div>
                <div className="mt-1 font-display font-bold text-ink text-2xl">{s.count}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Enterprise data grid */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-display font-bold text-xl text-ink">Enterprise data grid</h3>
            <p className="text-xs text-ink-muted">Saved views, bulk actions, export, sticky operational headers</p>
          </div>
        </div>
        <DataTable
          data={orders}
          columns={[
            { key: "order_no", label: "Order" },
            { key: "branch_id", label: "Branch", render: (r) => (r.branch_id || "").replace("br-", "").replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) },
            { key: "party_name", label: "Customer" },
            { key: "status", label: "Status", type: "status" },
            { key: "total", label: "Value", type: "currency", align: "right" },
            { key: "sla", label: "SLA", type: "chip" },
          ]}
          loading={loading}
          testId="dashboard-orders"
        />
      </div>

      {/* Activity + tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-[#E5E7EB] card-soft p-5">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="font-display font-bold text-lg text-ink">Activity timeline</h3>
              <p className="text-xs text-ink-muted">Approvals, dispatches, invoices, exceptions</p>
            </div>
            <Button variant="outline" size="sm" className="border-[#E5E7EB] h-8" data-testid="activity-logs">View logs</Button>
          </div>
          <ul className="space-y-3">
            {activity.slice(0, 6).map((a) => {
              const { Icon, cls } = severityIcon(a.severity);
              return (
                <li key={a.id} className="flex items-start gap-3 rounded-lg border border-[#F1F5F9] p-3 hover:bg-canvas transition">
                  <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${cls}`}>
                    <Icon size={16} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold text-ink truncate">{a.title}</div>
                    <div className="text-xs text-ink-muted mt-0.5">
                      {a.module} · {formatAgo(a.created_at)}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="bg-white rounded-xl border border-[#E5E7EB] card-soft p-5">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="font-display font-bold text-lg text-ink">Tasks & approvals queue</h3>
              <p className="text-xs text-ink-muted">Prioritized by SLA and exception severity</p>
            </div>
            <Button className="bg-gold hover:bg-gold-dark text-white h-8" size="sm" data-testid="open-queue">
              <Sparkles size={13} className="mr-1.5" /> Open queue
            </Button>
          </div>
          <ul className="space-y-3">
            {tasks.slice(0, 6).map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-3 rounded-lg border border-[#F1F5F9] p-3 hover:bg-canvas transition">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-ink">{t.title}</div>
                  <div className="text-xs text-ink-muted mt-0.5">{t.module} · {t.requested_by}</div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusPill value={t.sla || "—"} size="sm" />
                  <ChevronRight size={16} className="text-ink-muted" />
                </div>
              </li>
            ))}
            {tasks.length === 0 && (
              <li className="text-sm text-ink-muted text-center py-6">No pending approvals — you're all caught up.</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
