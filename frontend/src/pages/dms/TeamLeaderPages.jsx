import React, { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { dms, inr, niceDate, statusPill } from "./api";
import { PageHeader } from "./OwnerPages";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { TrendingUp, ShoppingCart, ClipboardList, Percent, Handshake, Users, Store, AlertTriangle, LogIn, LogOut, Clock, MapPin, RefreshCw, Truck } from "lucide-react";

// ============================================================================
// TL Dashboard
// ============================================================================
export function TlDashboardPage() {
  const [k, setK] = useState(null);
  useEffect(() => { dms.tlDashboard().then(d => setK(d.kpis)).catch(() => {}); }, []);
  const cards = [
    { label: "Today's Sales",         value: k ? inr(k.today_sales) : "—",     icon: TrendingUp,   tint: "bg-emerald-50 text-emerald-700" },
    { label: "This Month's Sales",    value: k ? inr(k.monthly_sales) : "—",   icon: TrendingUp,   tint: "bg-[#faf6e6] text-[#a67c00]" },
    { label: "Total Orders",          value: k?.total_orders ?? "—",           icon: ShoppingCart, tint: "bg-blue-50 text-blue-700" },
    { label: "Pending Orders",        value: k?.pending_orders ?? "—",         icon: ClipboardList,tint: "bg-amber-50 text-amber-700" },
    { label: "Fulfillment %",         value: k ? `${k.fulfillment_pct}%` : "—",icon: Percent,      tint: "bg-indigo-50 text-indigo-700" },
    { label: "Assigned Distributors", value: k?.assigned_distributors ?? "—",  icon: Handshake,    tint: "bg-purple-50 text-purple-700" },
    { label: "Assigned Salespersons", value: k?.assigned_salespersons ?? "—",  icon: Users,        tint: "bg-fuchsia-50 text-fuchsia-700" },
    { label: "Total Retailers",       value: k?.total_retailers ?? "—",        icon: Store,        tint: "bg-orange-50 text-orange-700" },
    { label: "Stock Alerts",          value: k?.stock_alerts ?? "—",           icon: AlertTriangle,tint: "bg-rose-50 text-rose-700" },
  ];
  return (
    <div>
      <PageHeader title="Team Leader Dashboard" subtitle="Overview of your assigned team and distributors" />
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
        {cards.map(c => (
          <Card key={c.label} className="p-4">
            <div className={`inline-flex h-9 w-9 rounded-lg items-center justify-center mb-2 ${c.tint}`}>
              <c.icon size={18} />
            </div>
            <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">{c.label}</div>
            <div className="text-xl font-bold text-slate-900 mt-1">{c.value}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// TL: Distributors (assigned) with all performance metrics
// ============================================================================
export function TlDistributorsMonitoringPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => { dms.tlDistributors().then(d => setRows(d.data || [])).catch(() => {}); }, []);
  return (
    <div>
      <PageHeader title="My Distributors" subtitle="Performance of your assigned distributors" />
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Distributor</TableHead>
              <TableHead className="text-right">Available Stock</TableHead>
              <TableHead className="text-right">Payable to Owner</TableHead>
              <TableHead className="text-right">Receivable</TableHead>
              <TableHead className="text-right">Today's Sales</TableHead>
              <TableHead className="text-right">Monthly Sales</TableHead>
              <TableHead className="text-right">Revenue</TableHead>
              <TableHead className="text-right">Pending</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={8} className="text-center py-8 text-slate-400">No distributors assigned</TableCell></TableRow>}
            {rows.map(d => (
              <TableRow key={d.id}>
                <TableCell>
                  <div className="font-semibold text-slate-900">{d.name}</div>
                  <div className="text-xs text-slate-500">{d.region}</div>
                </TableCell>
                <TableCell className="text-right font-medium">{d.available_stock} boxes</TableCell>
                <TableCell className="text-right text-rose-700">{inr(d.outstanding_payable_to_owner)}</TableCell>
                <TableCell className="text-right text-amber-700">{inr(d.outstanding_receivable_from_retailers)}</TableCell>
                <TableCell className="text-right">{inr(d.today_sales)}</TableCell>
                <TableCell className="text-right">{inr(d.monthly_sales)}</TableCell>
                <TableCell className="text-right font-semibold">{inr(d.revenue)}</TableCell>
                <TableCell className="text-right">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${d.pending_orders > 0 ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-500"}`}>{d.pending_orders}</span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ============================================================================
// TL: Salespersons (assigned) with live status + assign-to-distributor
// ============================================================================
export function TlSalespersonsPage() {
  const [rows, setRows] = useState([]);
  const [dists, setDists] = useState([]);
  const [assignFor, setAssignFor] = useState(null); // sp obj
  const [pickDist, setPickDist] = useState("");
  const refresh = () => dms.tlSalespersons().then(d => setRows(d.data || [])).catch(() => {});
  useEffect(() => { refresh(); dms.tlDistributors().then(d => setDists(d.data || [])).catch(() => {}); }, []);

  const doAssign = async () => {
    if (!assignFor || !pickDist) return;
    try {
      await dms.assignSpDist({ salesperson_id: assignFor.id, distributor_id: pickDist });
      toast.success(`Assigned ${assignFor.name} to distributor`);
      setAssignFor(null); setPickDist("");
      refresh();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div>
      <PageHeader title="My Salespersons" subtitle="Live status, attendance and today's activity" action={
        <Button variant="outline" size="sm" onClick={refresh}><RefreshCw size={14} className="mr-1" /> Refresh</Button>
      } />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {rows.length === 0 && <Card className="p-8 text-center col-span-full text-sm text-slate-500">No salespersons assigned</Card>}
        {rows.map(s => (
          <Card key={s.id} className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-semibold text-slate-900">{s.name}</div>
                <div className="text-xs text-slate-500">{s.phone}</div>
              </div>
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${s.online ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-500"}`}>
                {s.online ? "● Online" : "○ Offline"}
              </span>
            </div>
            <div className="mt-3 space-y-1 text-sm">
              <Row icon={LogIn}  label="Punch In"      value={s.punch_in ? niceDate(s.punch_in) : "—"} />
              <Row icon={LogOut} label="Punch Out"     value={s.punch_out ? niceDate(s.punch_out) : "—"} />
              <Row icon={MapPin} label="Live Location" value={s.live_location ? `${s.live_location.lat?.toFixed(3)}, ${s.live_location.lng?.toFixed(3)}` : "—"} />
              <Row icon={Store}  label="Today's Visits" value={s.today_visits} />
              <Row icon={ShoppingCart} label="Orders Collected" value={s.orders_today} />
              <Row icon={Users}  label="New Retailers"  value={s.new_retailers_today} />
            </div>
            <Button size="sm" variant="outline" onClick={() => setAssignFor(s)} className="mt-3 w-full" data-testid={`assign-sp-${s.id}`}>
              Assign to Distributor
            </Button>
          </Card>
        ))}
      </div>

      {assignFor && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center z-50" onClick={() => setAssignFor(null)}>
          <Card className="p-5 w-96" onClick={e => e.stopPropagation()}>
            <div className="font-semibold text-slate-900 mb-3">Assign {assignFor.name} to Distributor</div>
            <Select value={pickDist} onValueChange={setPickDist}>
              <SelectTrigger data-testid="assign-dist-picker"><SelectValue placeholder="Select distributor" /></SelectTrigger>
              <SelectContent>
                {dists.map(d => <SelectItem key={d.id} value={d.id}>{d.name} · {d.region}</SelectItem>)}
              </SelectContent>
            </Select>
            <div className="flex gap-2 mt-4">
              <Button variant="outline" className="flex-1" onClick={() => setAssignFor(null)}>Cancel</Button>
              <Button className="flex-1 bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" onClick={doAssign} disabled={!pickDist} data-testid="confirm-assign">Assign</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// TL: Order monitoring with filters
// ============================================================================
export function TlOrdersMonitoringPage() {
  const [orders, setOrders] = useState([]);
  const [dists, setDists] = useState([]);
  const [retailers, setRetailers] = useState([]);
  const [sps, setSps] = useState([]);
  const [f, setF] = useState({ status: "", distributor_id: "", salesperson_id: "", retailer_id: "" });

  const refresh = () => {
    const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v));
    dms.tlOrders(params).then(d => setOrders(d.data || [])).catch(() => {});
  };
  useEffect(() => {
    refresh();
    dms.tlDistributors().then(d => setDists(d.data || [])).catch(() => {});
    dms.tlRetailers().then(d => setRetailers(d.data || [])).catch(() => {});
    dms.tlSalespersons().then(d => setSps(d.data || [])).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [f]);

  return (
    <div>
      <PageHeader title="Order Monitoring" subtitle="All secondary orders across your team" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
        <Filter value={f.status} onChange={v => setF({ ...f, status: v })} placeholder="Any status" options={[
          { v: "", label: "All statuses" }, { v: "pending", label: "Pending" }, { v: "fulfilled", label: "Fulfilled" },
          { v: "dispatched", label: "Dispatched" }, { v: "delivered", label: "Delivered" }, { v: "cancelled", label: "Cancelled" },
        ]} />
        <Filter value={f.distributor_id} onChange={v => setF({ ...f, distributor_id: v })} placeholder="Any distributor" options={[
          { v: "", label: "All distributors" }, ...dists.map(d => ({ v: d.id, label: d.name })),
        ]} />
        <Filter value={f.salesperson_id} onChange={v => setF({ ...f, salesperson_id: v })} placeholder="Any salesperson" options={[
          { v: "", label: "All salespersons" }, ...sps.map(s => ({ v: s.id, label: s.name })),
        ]} />
        <Filter value={f.retailer_id} onChange={v => setF({ ...f, retailer_id: v })} placeholder="Any retailer" options={[
          { v: "", label: "All retailers" }, ...retailers.map(r => ({ v: r.id, label: r.name })),
        ]} />
      </div>
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Order</TableHead>
              <TableHead>Distributor</TableHead>
              <TableHead>Retailer</TableHead>
              <TableHead className="text-right">Total</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Placed</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-8 text-slate-400">No orders match filters</TableCell></TableRow>}
            {orders.map(o => (
              <TableRow key={o.id}>
                <TableCell className="font-mono text-xs">{o.id}</TableCell>
                <TableCell>{o.distributor_name}</TableCell>
                <TableCell>{o.retailer_name}</TableCell>
                <TableCell className="text-right font-medium">{inr(o.total)}</TableCell>
                <TableCell><span className={`px-2 py-0.5 rounded-full text-xs border ${statusPill(o.status)}`}>{o.status}</span></TableCell>
                <TableCell className="text-xs text-slate-500">{niceDate(o.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ============================================================================
// TL: Retailers (assigned)
// ============================================================================
export function TlRetailersPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => { dms.tlRetailers().then(d => setRows(d.data || [])).catch(() => {}); }, []);
  return (
    <div>
      <PageHeader title="My Retailers" subtitle="Retailers under your distributors" />
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Retailer</TableHead>
              <TableHead>Location</TableHead>
              <TableHead className="text-right">Outstanding</TableHead>
              <TableHead className="text-right">Total Purchases</TableHead>
              <TableHead>Last Order</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={5} className="text-center py-8 text-slate-400">No retailers</TableCell></TableRow>}
            {rows.map(r => (
              <TableRow key={r.id}>
                <TableCell>
                  <div className="font-semibold text-slate-900">{r.name}</div>
                  <div className="text-xs text-slate-500">{r.phone}</div>
                </TableCell>
                <TableCell>
                  <div className="text-xs text-slate-600">{r.address}</div>
                  {r.gps_lat && <div className="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5"><MapPin size={10} /> {r.gps_lat.toFixed(3)}, {r.gps_lng.toFixed(3)}</div>}
                </TableCell>
                <TableCell className={`text-right font-medium ${r.outstanding > 0 ? "text-rose-700" : "text-slate-500"}`}>{inr(r.outstanding)}</TableCell>
                <TableCell className="text-right">{inr(r.total_purchases)}</TableCell>
                <TableCell className="text-xs text-slate-500">{r.last_order_at ? niceDate(r.last_order_at) : "Never"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ============================================================================
// TL: Attendance (own punch in/out)
// ============================================================================
export function TlAttendancePage() {
  const [rows, setRows] = useState([]);
  const [today, setToday] = useState(null);
  const refresh = () => dms.tlAttendance().then(d => {
    setRows(d.data || []);
    const t = (d.data || []).find(x => x.date === new Date().toISOString().slice(0,10));
    setToday(t || null);
  }).catch(() => {});
  useEffect(() => { refresh(); }, []);

  const getGps = () => new Promise((resolve) => {
    if (!("geolocation" in navigator)) return resolve({});
    navigator.geolocation.getCurrentPosition(
      pos => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => resolve({}),
    );
  });

  const doIn  = async () => { const g = await getGps(); await dms.tlPunchIn(g).catch(() => {}); toast.success("Punched in"); refresh(); };
  const doOut = async () => { const g = await getGps(); await dms.tlPunchOut(g).catch(e => toast.error(e?.response?.data?.detail || "Failed")); toast.success("Punched out"); refresh(); };

  const workingHrs = (p) => {
    if (!p?.in_at) return "—";
    const a = new Date(p.in_at); const b = p.out_at ? new Date(p.out_at) : new Date();
    return ((b - a) / 3600000).toFixed(2) + " h";
  };

  return (
    <div>
      <PageHeader title="My Attendance" subtitle="Punch in/out and daily hours" />
      <Card className="p-5 mb-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div>
            <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Today</div>
            <div className="text-lg font-bold text-slate-900">
              {today?.in_at ? `In at ${niceDate(today.in_at)}` : "Not punched in"}
              {today?.out_at && <span className="ml-2 text-slate-500">— Out at {niceDate(today.out_at)}</span>}
            </div>
            <div className="text-sm text-slate-600 mt-0.5">Working: <b>{workingHrs(today)}</b></div>
          </div>
          <div className="flex-1" />
          {(!today || !today.in_at) && (
            <Button onClick={doIn} className="bg-emerald-600 hover:bg-emerald-700" data-testid="tl-punch-in"><LogIn size={16} className="mr-2" /> Punch In</Button>
          )}
          {today?.in_at && !today?.out_at && (
            <Button onClick={doOut} className="bg-rose-600 hover:bg-rose-700" data-testid="tl-punch-out"><LogOut size={16} className="mr-2" /> Punch Out</Button>
          )}
        </div>
      </Card>
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            <TableHead>Date</TableHead><TableHead>In</TableHead><TableHead>Out</TableHead><TableHead>Working Hours</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {rows.map(p => (
              <TableRow key={p.id}>
                <TableCell>{p.date}</TableCell>
                <TableCell className="text-xs">{p.in_at ? niceDate(p.in_at) : "—"}</TableCell>
                <TableCell className="text-xs">{p.out_at ? niceDate(p.out_at) : <span className="text-emerald-600">In progress…</span>}</TableCell>
                <TableCell className="font-medium">{workingHrs(p)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ── small helpers ──
function Row({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="flex items-center gap-2 text-slate-600"><Icon size={12} className="text-slate-400" /> {label}</span>
      <span className="font-semibold text-slate-900">{value}</span>
    </div>
  );
}

function Filter({ value, onChange, placeholder, options }) {
  return (
    <Select value={value || "__all__"} onValueChange={v => onChange(v === "__all__" ? "" : v)}>
      <SelectTrigger><SelectValue placeholder={placeholder} /></SelectTrigger>
      <SelectContent>
        {options.map(o => <SelectItem key={o.v || "__all__"} value={o.v || "__all__"}>{o.label}</SelectItem>)}
      </SelectContent>
    </Select>
  );
}
