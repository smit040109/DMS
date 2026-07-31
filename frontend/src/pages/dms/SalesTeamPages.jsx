import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { dms, inr, niceDate } from "./api";
import { PageHeader } from "./OwnerPages";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Fingerprint, MapPin, Play, Square, ShoppingCart, Users, Handshake, Store, Plus, Navigation } from "lucide-react";

// Salesperson Dashboard with punch in/out
export function SalespersonDashboardPage() {
  const [kpis, setKpis] = useState(null);
  const [punch, setPunch] = useState(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const load = () => dms.salespersonDashboard().then(d => { setKpis(d.kpis); setPunch(d.today_punch); });
  useEffect(() => { load(); }, []);
  const doPunch = async (kind) => {
    setBusy(true);
    // capture GPS if available
    let coords = { lat: null, lng: null };
    try {
      const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, { timeout: 5000 }));
      coords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    } catch { /* fallback: no gps */ }
    try {
      if (kind === "in") await dms.punchIn(coords); else await dms.punchOut(coords);
      toast.success(`Punched ${kind}`);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };
  const isPunchedIn = punch && !punch.out_at;
  const cards = [
    { label: "Assigned Distributors", value: kpis?.assigned_distributors ?? "—", icon: Handshake, color: "teal" },
    { label: "Assigned Retailers", value: kpis?.assigned_retailers ?? "—", icon: Store, color: "indigo" },
    { label: "Orders Today", value: kpis?.orders_today ?? "—", icon: ShoppingCart, color: "amber" },
  ];
  const colorMap = { teal: "bg-[#faf6e6] text-[#a67c00]", indigo: "bg-indigo-50 text-indigo-700", amber: "bg-amber-50 text-amber-700" };
  return (
    <div>
      <PageHeader title="Salesperson Dashboard" subtitle="Punch in, visit retailers, capture orders" />
      <Card className={`p-6 mb-4 ${isPunchedIn ? "bg-emerald-50 border-emerald-200" : "bg-slate-50"}`}>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-wider text-slate-600 flex items-center gap-1"><Fingerprint size={12} /> Today's attendance</div>
            {isPunchedIn ? (
              <>
                <div className="font-bold text-emerald-800 mt-1">Punched in at {niceDate(punch.in_at)}</div>
                {punch.gps_in?.lat && <div className="text-xs text-emerald-700 flex items-center gap-1 mt-1"><MapPin size={11} /> {punch.gps_in.lat.toFixed(4)}, {punch.gps_in.lng.toFixed(4)}</div>}
              </>
            ) : punch?.out_at ? (
              <div className="font-medium text-slate-700 mt-1">Punched out at {niceDate(punch.out_at)}</div>
            ) : (
              <div className="font-medium text-slate-700 mt-1">Not punched in yet</div>
            )}
          </div>
          <div className="flex gap-2">
            {!isPunchedIn && !punch?.out_at && <Button onClick={() => doPunch("in")} disabled={busy} className="bg-emerald-700 hover:bg-emerald-800" data-testid="punch-in-btn"><Play size={14} className="mr-1" /> Punch In</Button>}
            {isPunchedIn && <Button onClick={() => doPunch("out")} disabled={busy} className="bg-rose-700 hover:bg-rose-800" data-testid="punch-out-btn"><Square size={14} className="mr-1" /> Punch Out</Button>}
          </div>
        </div>
      </Card>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        {cards.map(c => (
          <Card key={c.label} className="p-4">
            <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${colorMap[c.color]}`}><c.icon size={18} /></div>
            <div className="mt-3 text-xs text-slate-500 uppercase tracking-wider">{c.label}</div>
            <div className="mt-1 text-xl font-bold text-slate-900">{c.value}</div>
          </Card>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Card className="p-4 cursor-pointer hover:shadow-md" onClick={() => nav("/dms/salesperson/distributors")}><Handshake size={20} className="text-[#a67c00]" /><div className="mt-2 font-semibold">My Distributors</div><div className="text-xs text-slate-500">View stock & details</div></Card>
        <Card className="p-4 cursor-pointer hover:shadow-md" onClick={() => nav("/dms/salesperson/retailers")}><Store size={20} className="text-[#a67c00]" /><div className="mt-2 font-semibold">My Retailers</div><div className="text-xs text-slate-500">Visit, onboard, place orders</div></Card>
        <Card className="p-4 cursor-pointer hover:shadow-md" onClick={() => nav("/dms/salesperson/new-retailer")}><Plus size={20} className="text-[#a67c00]" /><div className="mt-2 font-semibold">Onboard Retailer</div><div className="text-xs text-slate-500">Add a new retailer on the go</div></Card>
      </div>
    </div>
  );
}

export function SpDistributorsPage() {
  const [list, setList] = useState([]);
  const nav = useNavigate();
  useEffect(() => { dms.listDistributors().then(d => setList(d.data)); }, []);
  return (
    <div>
      <PageHeader title="My Assigned Distributors" subtitle="Distributors your team leader has assigned to you" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {list.map(d => (
          <Card key={d.id} className="p-4">
            <div className="font-semibold">{d.name}</div>
            <div className="text-xs text-slate-500 mt-0.5">{d.email}</div>
            <div className="text-xs text-slate-500">{d.phone}</div>
            <div className="text-xs text-slate-500 mt-1">Region: {d.region || "—"}</div>
          </Card>
        ))}
        {list.length === 0 && <Card className="p-8 col-span-full text-center text-sm text-slate-500">No distributors assigned yet</Card>}
      </div>
    </div>
  );
}

export function SpRetailersPage() {
  const [list, setList] = useState([]);
  const nav = useNavigate();
  useEffect(() => { dms.listRetailers().then(d => setList(d.data)); }, []);
  return (
    <div>
      <PageHeader title="My Retailers" subtitle="Retailers under your assigned distributors"
        action={<Button onClick={() => nav("/dms/salesperson/new-retailer")} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="sp-new-retailer"><Plus size={16} className="mr-1" /> Onboard Retailer</Button>} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {list.map(r => (
          <Card key={r.id} className="p-4">
            <div className="font-semibold">{r.name}</div>
            <div className="text-xs text-slate-500 mt-0.5">{r.phone}</div>
            <div className="text-xs text-slate-500 truncate">{r.address}</div>
            {r.gps_lat && <a href={`https://maps.google.com/?q=${r.gps_lat},${r.gps_lng}`} target="_blank" rel="noreferrer" className="text-[11px] text-[#a67c00] hover:underline flex items-center gap-1 mt-1"><MapPin size={11} /> View on Maps</a>}
            <div className="mt-3 flex gap-2">
              <Button size="sm" variant="outline" className="flex-1" onClick={() => nav(`/dms/salesperson/new-order?retailer_id=${r.id}`)} data-testid={`sp-order-for-${r.id}`}><ShoppingCart size={12} className="mr-1" /> Place Order</Button>
            </div>
          </Card>
        ))}
        {list.length === 0 && <Card className="p-8 col-span-full text-center text-sm text-slate-500">No retailers yet</Card>}
      </div>
    </div>
  );
}

export function SpNewRetailerPage() {
  const [form, setForm] = useState({ name: "", phone: "", address: "", region: "", email: "", password: "Demo@2026", gstin: "", shop_license: "", distributor_id: "" });
  const [dists, setDists] = useState([]);
  const [gps, setGps] = useState(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  useEffect(() => { dms.listDistributors().then(d => { setDists(d.data); if (d.data[0]) setForm(f => ({ ...f, distributor_id: d.data[0].id })); }); }, []);
  const captureGps = () => {
    navigator.geolocation.getCurrentPosition(
      pos => { setGps({ lat: pos.coords.latitude, lng: pos.coords.longitude }); toast.success("Location captured"); },
      err => toast.error("GPS unavailable — will save without"),
      { timeout: 5000, enableHighAccuracy: true }
    );
  };
  const submit = async () => {
    setBusy(true);
    try {
      const body = { ...form, gps_lat: gps?.lat, gps_lng: gps?.lng };
      const r = await dms.createRetailer(body);
      toast.success(`Retailer ${r.name} onboarded`);
      nav(`/dms/salesperson/new-order?retailer_id=${r.id}`);
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };
  return (
    <div className="max-w-2xl mx-auto">
      <PageHeader title="Onboard New Retailer" subtitle="Basic info now, documents can be added later" back="/dms/salesperson/retailers" />
      <Card className="p-6 space-y-4">
        <div><Label>Assign to Distributor *</Label>
          <select value={form.distributor_id} onChange={e => setForm({ ...form, distributor_id: e.target.value })} className="mt-1 w-full h-10 px-3 rounded-lg border border-slate-200">
            {dists.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Shop Name *</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="sp-ret-name" /></div>
          <div><Label>Phone *</Label><Input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} /></div>
        </div>
        <div><Label>Address *</Label><Textarea rows={2} value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Region</Label><Input value={form.region} onChange={e => setForm({ ...form, region: e.target.value })} /></div>
          <div>
            <Label>GPS Location</Label>
            <div className="mt-1 flex items-center gap-2">
              <Button type="button" size="sm" variant="outline" onClick={captureGps} data-testid="capture-gps-btn"><Navigation size={14} className="mr-1" /> Capture</Button>
              {gps && <span className="text-xs text-emerald-700">{gps.lat.toFixed(4)}, {gps.lng.toFixed(4)}</span>}
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Login Email (optional)</Label><Input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></div>
          <div><Label>Password</Label><Input value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>GSTIN (optional)</Label><Input value={form.gstin} onChange={e => setForm({ ...form, gstin: e.target.value })} /></div>
          <div><Label>Shop License (optional)</Label><Input value={form.shop_license} onChange={e => setForm({ ...form, shop_license: e.target.value })} /></div>
        </div>
        <Button onClick={submit} disabled={busy || !form.name || !form.phone || !form.address} className="w-full bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="sp-save-retailer">Onboard & Place First Order</Button>
      </Card>
    </div>
  );
}

export function SpNewOrderPage() {
  const params = new URLSearchParams(window.location.search);
  const rid = params.get("retailer_id");
  const [data, setData] = useState({ data: [], mode: "box", pending: [] });
  const [cart, setCart] = useState({});
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  useEffect(() => { if (rid) dms.retailerBrowse(rid).then(setData); }, [rid]);
  const setQty = (pid, field, delta) => setCart(prev => { const c = prev[pid] || { boxes: 0, pcs: 0 }; return { ...prev, [pid]: { ...c, [field]: Math.max(0, (c[field] || 0) + delta) } }; });
  const items = Object.entries(cart).filter(([, q]) => (q.boxes || 0) + (q.pcs || 0) > 0);
  const total = items.reduce((s, [pid, q]) => {
    const p = data.data.find(x => x.id === pid);
    if (!p) return s;
    const box = p.selling_price; const pcs = box / (p.box_qty || 1);
    const sub = (q.boxes || 0) * box + (q.pcs || 0) * pcs;
    return s + sub + sub * (p.gst_pct / 100);
  }, 0);
  const place = async () => {
    setBusy(true);
    try {
      const body = { retailer_id: rid, items: items.map(([product_id, q]) => ({ product_id, qty_boxes: q.boxes || 0, qty_pcs: q.pcs || 0 })) };
      const o = await dms.placeSecondaryOrder(body);
      toast.success(`Order ${o.order_no} placed`);
      nav("/dms/salesperson/retailers");
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };
  if (!rid) return <div className="p-8 text-center text-slate-500">retailer_id missing</div>;
  return (
    <div className="pb-32">
      <PageHeader title={`Order for ${data.retailer?.name || "..."}`} subtitle={`Mode: ${data.mode === "box_pcs" ? "Box + PCS" : "Box only"}`} back="/dms/salesperson/retailers" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {data.data.map(p => {
          const q = cart[p.id] || { boxes: 0, pcs: 0 };
          return (
            <Card key={p.id} className="p-4">
              <div className="font-semibold">{p.name}</div>
              <div className="text-xs font-mono text-slate-500">{p.sku_code}</div>
              <div className="mt-2 text-lg font-bold text-[#a67c00]">{inr(p.selling_price)}<span className="text-xs text-slate-500 font-normal">/box</span></div>
              <div className="text-xs text-slate-500">Stock: {p.distributor_stock_boxes} boxes</div>
              <div className="mt-3 flex items-center justify-between gap-2">
                <span className="text-xs text-slate-600">Boxes</span>
                <div className="flex items-center gap-1">
                  <button onClick={() => setQty(p.id, "boxes", -1)} className="h-8 w-8 rounded border">-</button>
                  <span className="w-8 text-center font-semibold">{q.boxes || 0}</span>
                  <button onClick={() => setQty(p.id, "boxes", 1)} className="h-8 w-8 rounded border">+</button>
                </div>
              </div>
              {data.mode === "box_pcs" && (
                <div className="mt-2 flex items-center justify-between gap-2">
                  <span className="text-xs text-slate-600">PCS</span>
                  <div className="flex items-center gap-1">
                    <button onClick={() => setQty(p.id, "pcs", -1)} className="h-8 w-8 rounded border">-</button>
                    <span className="w-8 text-center font-semibold">{q.pcs || 0}</span>
                    <button onClick={() => setQty(p.id, "pcs", 1)} className="h-8 w-8 rounded border">+</button>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
      <div className="fixed bottom-0 left-0 lg:left-60 right-0 bg-white border-t border-slate-200 shadow-lg">
        <div className="p-4 flex items-center gap-4">
          <div className="flex-1"><div className="text-xs text-slate-500">{items.length} items</div><div className="text-xl font-bold">{inr(total)}</div></div>
          <Button disabled={items.length === 0 || busy} onClick={place} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white h-11 px-6" data-testid="sp-place-order"><ShoppingCart size={16} className="mr-2" /> Place Order</Button>
        </div>
      </div>
    </div>
  );
}

// Team Leader Dashboard + Assignments
export function TeamLeaderDashboardPage() {
  const [kpis, setKpis] = useState(null);
  const nav = useNavigate();
  useEffect(() => { dms.teamLeaderDashboard().then(d => setKpis(d.kpis)); }, []);
  return (
    <div>
      <PageHeader title="Team Leader Dashboard" subtitle="Manage distributors & sales team" />
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
        {[
          { label: "My Distributors", value: kpis?.distributors ?? "—" },
          { label: "Salespersons", value: kpis?.salespersons ?? "—" },
          { label: "Sales MTD", value: kpis ? inr(kpis.sales_mtd) : "—" },
        ].map(c => <Card key={c.label} className="p-4"><div className="text-xs uppercase tracking-wider text-slate-500">{c.label}</div><div className="mt-1 text-xl font-bold">{c.value}</div></Card>)}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Card className="p-4 cursor-pointer hover:shadow-md" onClick={() => nav("/dms/team-leader/distributors")}><Handshake size={20} className="text-[#a67c00]" /><div className="mt-2 font-semibold">My Distributors</div><div className="text-xs text-slate-500">View performance</div></Card>
        <Card className="p-4 cursor-pointer hover:shadow-md" onClick={() => nav("/dms/team-leader/assignments")}><Users size={20} className="text-[#a67c00]" /><div className="mt-2 font-semibold">Assign Distributors to Salesperson</div><div className="text-xs text-slate-500">Manage your sales team's coverage</div></Card>
      </div>
    </div>
  );
}

export function TlDistributorsPage() {
  const [list, setList] = useState([]);
  useEffect(() => { dms.listDistributors().then(d => setList(d.data)); }, []);
  return (
    <div>
      <PageHeader title="My Distributors" subtitle="Distributors assigned to your team" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {list.map(d => (
          <Card key={d.id} className="p-4"><div className="font-semibold">{d.name}</div><div className="text-xs text-slate-500 mt-0.5">{d.email}</div><div className="text-xs text-slate-500">Region: {d.region || "—"}</div></Card>
        ))}
      </div>
    </div>
  );
}

export function TlAssignmentsPage() {
  const [dists, setDists] = useState([]);
  const [sps, setSps] = useState([]);
  const [assigns, setAssigns] = useState([]);
  const load = async () => {
    const [d, s, a] = await Promise.all([dms.listDistributors(), dms.listUsers("salesperson"), dms.listSpDistributors()]);
    setDists(d.data); setSps(s.data); setAssigns(a.data);
  };
  useEffect(() => { load(); }, []);
  const assign = async (spId, dId) => { await dms.assignSpDist({ salesperson_id: spId, distributor_id: dId }); toast.success("Assigned"); load(); };
  const unassign = async (spId, dId) => { await dms.unassignSpDist(spId, dId); toast.success("Removed"); load(); };
  const isAssigned = (spId, dId) => assigns.some(a => a.salesperson_id === spId && a.distributor_id === dId);
  return (
    <div>
      <PageHeader title="Assign Distributors to Salespersons" subtitle="Grant salespersons access to specific distributors" />
      <Card>
        <Table><TableHeader><TableRow><TableHead>Salesperson</TableHead>{dists.map(d => <TableHead key={d.id}>{d.name}</TableHead>)}</TableRow></TableHeader><TableBody>
          {sps.map(sp => (
            <TableRow key={sp.id}>
              <TableCell className="font-medium">{sp.name}<div className="text-xs text-slate-500">{sp.email}</div></TableCell>
              {dists.map(d => {
                const a = isAssigned(sp.id, d.id);
                return (
                  <TableCell key={d.id}>
                    <button onClick={() => a ? unassign(sp.id, d.id) : assign(sp.id, d.id)} className={`px-3 py-1 rounded text-xs font-medium ${a ? "bg-[#faf0cf] text-[#8a6600] hover:bg-[#faf0cf]" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`} data-testid={`assign-${sp.id}-${d.id}`}>{a ? "✓ Assigned" : "Assign"}</button>
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody></Table>
        {sps.length === 0 && <div className="p-8 text-center text-sm text-slate-500">No salespersons found</div>}
      </Card>
    </div>
  );
}

export function RegionalManagerDashboardPage() {
  const [kpis, setKpis] = useState(null);
  useEffect(() => { dms.regionalManagerDashboard().then(d => setKpis(d.kpis)); }, []);
  return (
    <div>
      <PageHeader title="Regional Manager Dashboard" subtitle="Region-wide performance" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Team Leaders", value: kpis?.team_leaders ?? "—" },
          { label: "Distributors", value: kpis?.distributors ?? "—" },
          { label: "Sales MTD", value: kpis ? inr(kpis.sales_mtd) : "—" },
        ].map(c => <Card key={c.label} className="p-4"><div className="text-xs uppercase tracking-wider text-slate-500">{c.label}</div><div className="mt-1 text-xl font-bold">{c.value}</div></Card>)}
      </div>
    </div>
  );
}
