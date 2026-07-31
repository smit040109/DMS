import React, { useEffect, useState } from "react";
import { dms, inr, niceDate } from "./api";
import { PageHeader } from "./OwnerPages";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Trophy, TrendingUp, ShoppingCart, Percent, Handshake, Users, Store, AlertTriangle, IndianRupee, MapPin, LogIn, LogOut } from "lucide-react";

// ============================================================================
// RM Dashboard
// ============================================================================
export function RmDashboardPage() {
  const [k, setK] = useState(null);
  useEffect(() => { dms.rmDashboard().then(d => setK(d.kpis)).catch(() => {}); }, []);
  const cards = [
    { label: "Team Leaders",     value: k?.team_leaders ?? "—",           icon: Users,     tint: "bg-purple-50 text-purple-700" },
    { label: "Distributors",     value: k?.distributors ?? "—",           icon: Handshake, tint: "bg-teal-50 text-teal-700" },
    { label: "Retailers",        value: k?.retailers ?? "—",              icon: Store,     tint: "bg-amber-50 text-amber-700" },
    { label: "Salespersons",     value: k?.salespersons ?? "—",           icon: Users,     tint: "bg-fuchsia-50 text-fuchsia-700" },
    { label: "Today's Sales",    value: k ? inr(k.today_sales) : "—",     icon: TrendingUp,tint: "bg-emerald-50 text-emerald-700" },
    { label: "Monthly Sales",    value: k ? inr(k.monthly_sales) : "—",   icon: TrendingUp,tint: "bg-teal-50 text-teal-700" },
    { label: "Outstanding",      value: k ? inr(k.outstanding) : "—",     icon: IndianRupee,tint: "bg-rose-50 text-rose-700" },
    { label: "Revenue",          value: k ? inr(k.revenue) : "—",         icon: IndianRupee,tint: "bg-indigo-50 text-indigo-700" },
    { label: "Fulfillment %",    value: k ? `${k.fulfillment_pct}%` : "—",icon: Percent,   tint: "bg-blue-50 text-blue-700" },
  ];
  return (
    <div>
      <PageHeader title="Regional Manager Dashboard" subtitle="Overview of your region's performance" />
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
        {cards.map(c => (
          <Card key={c.label} className="p-4">
            <div className={`inline-flex h-9 w-9 rounded-lg items-center justify-center mb-2 ${c.tint}`}><c.icon size={18} /></div>
            <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">{c.label}</div>
            <div className="text-xl font-bold text-slate-900 mt-1">{c.value}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// RM: Team Leader monitoring (with simple ranking)
// ============================================================================
export function RmTeamLeadersPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => { dms.rmTeamLeaders().then(d => setRows(d.data || [])).catch(() => {}); }, []);
  const top = rows[0]?.sales || 0;
  return (
    <div>
      <PageHeader title="Team Leaders" subtitle="Monitoring & simple performance ranking" />
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            <TableHead>Rank</TableHead><TableHead>Team Leader</TableHead>
            <TableHead className="text-right">Sales</TableHead>
            <TableHead className="text-right">Active SPs</TableHead>
            <TableHead className="text-right">Active Dists</TableHead>
            <TableHead className="text-right">Pending</TableHead>
            <TableHead className="text-right">Revenue</TableHead>
            <TableHead>Progress</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={8} className="text-center py-8 text-slate-400">No team leaders assigned</TableCell></TableRow>}
            {rows.map((r, i) => (
              <TableRow key={r.id}>
                <TableCell className="font-bold">
                  #{i + 1}
                  {i === 0 && rows.length > 1 && <Trophy size={14} className="inline ml-1 text-amber-500" />}
                </TableCell>
                <TableCell><div className="font-medium">{r.name}</div><div className="text-xs text-slate-500">{r.email}</div></TableCell>
                <TableCell className="text-right font-semibold text-teal-800">{inr(r.sales)}</TableCell>
                <TableCell className="text-right">{r.active_salespersons}</TableCell>
                <TableCell className="text-right">{r.active_distributors}</TableCell>
                <TableCell className="text-right">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${r.pending_orders > 0 ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-500"}`}>{r.pending_orders}</span>
                </TableCell>
                <TableCell className="text-right">{inr(r.revenue)}</TableCell>
                <TableCell><div className="h-2 w-32 bg-slate-100 rounded-full overflow-hidden"><div className="h-full bg-teal-500" style={{ width: `${top ? Math.max(2, (r.sales / top) * 100) : 0}%` }} /></div></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ============================================================================
// RM: Region Performance (dist-wise, TL-wise, SP-wise bar charts)
// ============================================================================
export function RmRegionPerformancePage() {
  const [d, setD] = useState({ by_distributor: [], by_team_leader: [], by_salesperson: [] });
  useEffect(() => { dms.rmRegionPerformance().then(setD).catch(() => {}); }, []);
  return (
    <div>
      <PageHeader title="Region Performance" subtitle="Distributor-wise, Team Leader-wise, and Salesperson-wise sales" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <BarBlock title="By Distributor" rows={d.by_distributor} />
        <BarBlock title="By Team Leader" rows={d.by_team_leader} />
        <BarBlock title="By Salesperson" rows={d.by_salesperson} />
      </div>
    </div>
  );
}

function BarBlock({ title, rows }) {
  const max = Math.max(1, ...rows.map(r => r.sales));
  return (
    <Card>
      <div className="px-4 py-3 border-b border-slate-100 font-semibold text-slate-900">{title}</div>
      <div className="p-4 space-y-3">
        {rows.length === 0 && <div className="text-center py-6 text-sm text-slate-400">No data yet</div>}
        {rows.map(r => (
          <div key={r.id}>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="truncate">{r.name}</span>
              <span className="font-semibold text-slate-900">{inr(r.sales)}</span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full bg-teal-500" style={{ width: `${Math.max(2, (r.sales / max) * 100)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ============================================================================
// RM: Distributor monitoring (read-only)
// ============================================================================
export function RmDistributorsPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => { dms.rmDistributors().then(d => setRows(d.data || [])).catch(() => {}); }, []);
  return (
    <div>
      <PageHeader title="Distributor Monitoring" subtitle="Read-only view of all distributors in your region" />
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            <TableHead>Distributor</TableHead>
            <TableHead className="text-right">Stock</TableHead>
            <TableHead className="text-right">Pending Payments</TableHead>
            <TableHead className="text-right">Revenue</TableHead>
            <TableHead className="text-right">Retailers</TableHead>
            <TableHead className="text-right">Orders</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-8 text-slate-400">None</TableCell></TableRow>}
            {rows.map(d => (
              <TableRow key={d.id}>
                <TableCell><div className="font-medium">{d.name}</div><div className="text-xs text-slate-500">{d.region}</div></TableCell>
                <TableCell className="text-right">{d.stock} boxes</TableCell>
                <TableCell className="text-right text-rose-700">{inr(d.pending_payments)}</TableCell>
                <TableCell className="text-right font-semibold">{inr(d.revenue)}</TableCell>
                <TableCell className="text-right">{d.retailers}</TableCell>
                <TableCell className="text-right">{d.orders}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ============================================================================
// RM: Salesperson monitoring (read-only, live status)
// ============================================================================
export function RmSalespersonsPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => { dms.rmSalespersons().then(d => setRows(d.data || [])).catch(() => {}); }, []);
  return (
    <div>
      <PageHeader title="Salesperson Monitoring" subtitle="Read-only view: attendance, orders, visits, new retailers" />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {rows.length === 0 && <Card className="p-8 text-center col-span-full text-sm text-slate-500">No salespersons in region</Card>}
        {rows.map(s => (
          <Card key={s.id} className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-semibold text-slate-900">{s.name}</div>
                <div className="text-xs text-slate-500">{s.phone}</div>
              </div>
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${s.online ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-500"}`}>{s.online ? "● Online" : "○ Offline"}</span>
            </div>
            <div className="mt-3 space-y-1 text-sm">
              <Line icon={LogIn}  label="Punch In"  value={s.punch_in ? niceDate(s.punch_in) : "—"} />
              <Line icon={LogOut} label="Punch Out" value={s.punch_out ? niceDate(s.punch_out) : "—"} />
              <Line icon={MapPin} label="Location"  value={s.live_location ? `${s.live_location.lat?.toFixed(3)}, ${s.live_location.lng?.toFixed(3)}` : "—"} />
              <Line icon={Store}  label="Visits"    value={s.today_visits} />
              <Line icon={ShoppingCart} label="Orders" value={s.orders_today} />
              <Line icon={Users}  label="New Retailers" value={s.new_retailers_today} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Line({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="flex items-center gap-2 text-slate-600"><Icon size={12} className="text-slate-400" /> {label}</span>
      <span className="font-semibold text-slate-900">{value}</span>
    </div>
  );
}
