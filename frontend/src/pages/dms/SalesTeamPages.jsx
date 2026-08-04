import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { dms, inr, niceDate, statusPill } from "./api";
import { PageHeader } from "./OwnerPages";
import LocationDocumentsBlock from "./LocationDocumentsBlock";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Fingerprint, MapPin, Play, Square, ShoppingCart, Users, Handshake, Store, Plus, Navigation, Search, LayoutGrid, List as ListIcon, ClipboardList, Edit, Ban, Wallet, IndianRupee, Filter as FilterIcon } from "lucide-react";

// ============================================================================
// Salesperson Dashboard with punch in/out — Phase 1: all cards clickable
// ============================================================================
export function SalespersonDashboardPage() {
  const [kpis, setKpis] = useState(null);
  const [punch, setPunch] = useState(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const load = () => dms.salespersonDashboard().then(d => { setKpis(d.kpis); setPunch(d.today_punch); });
  useEffect(() => { load(); }, []);
  const doPunch = async (kind) => {
    setBusy(true);
    let coords = { lat: null, lng: null };
    try {
      const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, { timeout: 5000 }));
      coords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    } catch { /* fallback */ }
    try {
      if (kind === "in") await dms.punchIn(coords); else await dms.punchOut(coords);
      toast.success(`Punched ${kind}`);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };
  const isPunchedIn = punch && !punch.out_at;
  const cards = [
    { label: "Assigned Distributors", value: kpis?.assigned_distributors ?? "—", icon: Handshake, color: "teal",   to: "/dms/salesperson/distributors" },
    { label: "Assigned Retailers",   value: kpis?.assigned_retailers ?? "—",   icon: Store,     color: "indigo", to: "/dms/salesperson/retailers" },
    { label: "Orders Today",         value: kpis?.orders_today ?? "—",         icon: ShoppingCart, color: "amber", to: "/dms/salesperson/orders" },
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

      {/* KPI cards — clickable */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        {cards.map(c => (
          <Card key={c.label} className="p-4 cursor-pointer hover:shadow-md transition"
                onClick={() => nav(c.to)} data-testid={`sp-kpi-${c.label.toLowerCase().replace(/\s+/g, "-")}`}>
            <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${colorMap[c.color]}`}><c.icon size={18} /></div>
            <div className="mt-3 text-xs text-slate-500 uppercase tracking-wider">{c.label}</div>
            <div className="mt-1 text-xl font-bold text-slate-900">{c.value}</div>
          </Card>
        ))}
      </div>

      {/* Quick actions — Phase 1: added My Orders + Collect Payment */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        <Card className="p-4 cursor-pointer hover:shadow-md" onClick={() => nav("/dms/salesperson/distributors")}><Handshake size={20} className="text-[#a67c00]" /><div className="mt-2 font-semibold">My Distributors</div><div className="text-xs text-slate-500">View stock & details</div></Card>
        <Card className="p-4 cursor-pointer hover:shadow-md" onClick={() => nav("/dms/salesperson/retailers")}><Store size={20} className="text-[#a67c00]" /><div className="mt-2 font-semibold">My Retailers</div><div className="text-xs text-slate-500">Visit, onboard, place orders</div></Card>
        <Card className="p-4 cursor-pointer hover:shadow-md" onClick={() => nav("/dms/salesperson/orders")} data-testid="sp-my-orders-tile"><ClipboardList size={20} className="text-[#a67c00]" /><div className="mt-2 font-semibold">My Orders</div><div className="text-xs text-slate-500">Track / edit / cancel</div></Card>
        <Card className="p-4 cursor-pointer hover:shadow-md" onClick={() => nav("/dms/salesperson/collect")} data-testid="sp-collect-tile"><Wallet size={20} className="text-[#a67c00]" /><div className="mt-2 font-semibold">Receive Cash Payment</div><div className="text-xs text-slate-500">Collect from retailer</div></Card>
      </div>
    </div>
  );
}

export function SpDistributorsPage() {
  const [list, setList] = useState([]);
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

// ============================================================================
// SP: My Retailers — Phase 1: Search + List/Grid toggle
// ============================================================================
export function SpRetailersPage() {
  const [list, setList] = useState([]);
  const [q, setQ] = useState("");
  const [view, setView] = useState("grid"); // 'grid' | 'list'
  const nav = useNavigate();
  useEffect(() => { dms.listRetailers().then(d => setList(d.data || [])); }, []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return list;
    return list.filter(r =>
      (r.name || "").toLowerCase().includes(needle) ||
      (r.phone || "").toLowerCase().includes(needle) ||
      (r.address || "").toLowerCase().includes(needle) ||
      (r.region || "").toLowerCase().includes(needle),
    );
  }, [list, q]);

  return (
    <div>
      <PageHeader title="My Retailers" subtitle={`${filtered.length} of ${list.length} retailers`}
        action={<Button onClick={() => nav("/dms/salesperson/new-retailer")} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="sp-new-retailer"><Plus size={16} className="mr-1" /> Onboard Retailer</Button>} />

      {/* Search + View toggle */}
      <div className="flex flex-col md:flex-row gap-2 mb-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input value={q} onChange={e => setQ(e.target.value)} placeholder="Search by name, phone, address or region…" className="pl-9" data-testid="sp-retailer-search" />
        </div>
        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5 self-start">
          <button onClick={() => setView("grid")} data-testid="sp-ret-view-grid"
                  className={`px-3 py-1.5 text-xs rounded-md flex items-center gap-1 ${view === "grid" ? "bg-[#faf0cf] text-[#8a6600] font-semibold" : "text-slate-600 hover:bg-slate-50"}`}>
            <LayoutGrid size={13} /> Grid
          </button>
          <button onClick={() => setView("list")} data-testid="sp-ret-view-list"
                  className={`px-3 py-1.5 text-xs rounded-md flex items-center gap-1 ${view === "list" ? "bg-[#faf0cf] text-[#8a6600] font-semibold" : "text-slate-600 hover:bg-slate-50"}`}>
            <ListIcon size={13} /> List
          </button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <Card className="p-8 text-center text-sm text-slate-500">{list.length === 0 ? "No retailers yet" : "No retailers match your search"}</Card>
      ) : view === "grid" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map(r => (
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
        </div>
      ) : (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Address</TableHead>
                <TableHead>Region</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map(r => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell className="text-slate-600">{r.phone}</TableCell>
                  <TableCell className="text-xs text-slate-500 max-w-xs truncate">{r.address}</TableCell>
                  <TableCell className="text-xs text-slate-500">{r.region || "—"}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="outline" onClick={() => nav(`/dms/salesperson/new-order?retailer_id=${r.id}`)}>
                      <ShoppingCart size={12} className="mr-1" /> Order
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}

export function SpNewRetailerPage() {
  const [form, setForm] = useState({ name: "", phone: "", address: "", region: "", email: "", password: "Demo@2026", gstin: "", shop_license: "", distributor_id: "", gps_lat: "", gps_lng: "", location_link: "", documents: [] });
  const [dists, setDists] = useState([]);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  useEffect(() => { dms.listDistributors().then(d => { setDists(d.data); if (d.data[0]) setForm(f => ({ ...f, distributor_id: d.data[0].id })); }); }, []);
  const submit = async () => {
    setBusy(true);
    try {
      const body = {
        ...form,
        gps_lat: form.gps_lat === "" ? null : Number(form.gps_lat),
        gps_lng: form.gps_lng === "" ? null : Number(form.gps_lng),
      };
      const r = await dms.createRetailer(body);
      toast.success(`Retailer ${r.name} onboarded`);
      nav(`/dms/salesperson/new-order?retailer_id=${r.id}`);
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };
  return (
    <div className="max-w-2xl mx-auto">
      <PageHeader title="Onboard New Retailer" subtitle="Basic info + location + documents" back="/dms/salesperson/retailers" />
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
          <div><Label>Credit Limit (₹)</Label><Input type="number" value={form.credit_limit || ""} onChange={e => setForm({ ...form, credit_limit: Number(e.target.value) })} /></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Login Email (optional)</Label><Input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></div>
          <div><Label>Password</Label><Input value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>GSTIN (optional)</Label><Input value={form.gstin} onChange={e => setForm({ ...form, gstin: e.target.value })} /></div>
          <div><Label>Shop License (optional)</Label><Input value={form.shop_license} onChange={e => setForm({ ...form, shop_license: e.target.value })} /></div>
        </div>
        <LocationDocumentsBlock
          lat={form.gps_lat}
          lng={form.gps_lng}
          locationLink={form.location_link}
          onLat={(v) => setForm(f => ({ ...f, gps_lat: v }))}
          onLng={(v) => setForm(f => ({ ...f, gps_lng: v }))}
          onLocationLink={(v) => setForm(f => ({ ...f, location_link: v }))}
          documents={form.documents}
          onDocuments={(docs) => setForm(f => ({ ...f, documents: docs }))}
          helpText="Tap Use my current location for the shop's exact GPS pin."
        />
        <Button onClick={submit} disabled={busy || !form.name || !form.phone || !form.address} className="w-full bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="sp-save-retailer">Onboard & Place First Order</Button>
      </Card>
    </div>
  );
}

// ============================================================================
// SP: Order Placement — Phase 1:
//   - category filter chips
//   - always allow "Nos" (pcs) input regardless of mode
//   - supports edit mode (?edit=OID prefills existing items)
// ============================================================================
export function SpNewOrderPage() {
  const params = new URLSearchParams(window.location.search);
  const rid = params.get("retailer_id");
  const editId = params.get("edit");                         // Phase 1: edit mode
  const [data, setData] = useState({ data: [], mode: "box", pending: [] });
  const [cart, setCart] = useState({});
  const [busy, setBusy] = useState(false);
  const [catFilter, setCatFilter] = useState("__all__");
  const [existingOrder, setExistingOrder] = useState(null);
  const nav = useNavigate();

  // Prefill from existing order if editing
  useEffect(() => {
    if (!editId) return;
    dms.getSecondaryOrder(editId).then(o => {
      setExistingOrder(o);
      const c = {};
      (o.items || []).forEach(it => {
        c[it.product_id] = { boxes: it.qty_boxes_ordered || 0, pcs: it.qty_pcs_ordered || 0 };
      });
      setCart(c);
    }).catch(() => toast.error("Could not load order to edit"));
  }, [editId]);

  useEffect(() => {
    const targetRid = rid || existingOrder?.retailer_id;
    if (targetRid) dms.retailerBrowse(targetRid).then(setData);
  }, [rid, existingOrder]);

  const setQty = (pid, field, delta) => setCart(prev => {
    const c = prev[pid] || { boxes: 0, pcs: 0 };
    return { ...prev, [pid]: { ...c, [field]: Math.max(0, (c[field] || 0) + delta) } };
  });

  const items = Object.entries(cart).filter(([, q]) => (q.boxes || 0) + (q.pcs || 0) > 0);

  const total = items.reduce((s, [pid, q]) => {
    const p = data.data.find(x => x.id === pid);
    if (!p) return s;
    const box = p.selling_price; const pcs = box / (p.box_qty || 1);
    const sub = (q.boxes || 0) * box + (q.pcs || 0) * pcs;
    return s + sub + sub * (p.gst_pct / 100);
  }, 0);

  // Category groupings
  const categories = useMemo(() => {
    const set = new Set();
    data.data.forEach(p => { if (p.category_name) set.add(p.category_name); });
    return Array.from(set).sort();
  }, [data.data]);

  const visibleProducts = useMemo(() => {
    if (catFilter === "__all__") return data.data;
    return data.data.filter(p => (p.category_name || "") === catFilter);
  }, [data.data, catFilter]);

  const targetRid = rid || existingOrder?.retailer_id;

  const submit = async () => {
    setBusy(true);
    try {
      const body = {
        items: items.map(([product_id, q]) => ({
          product_id,
          qty_boxes: q.boxes || 0,
          qty_pcs: q.pcs || 0,          // Phase 1: always send pcs (Nos) even in box mode
        })),
      };
      if (editId) {
        await dms.updateSecondaryOrder(editId, body);
        toast.success("Order updated");
        nav("/dms/salesperson/orders");
      } else {
        body.retailer_id = targetRid;
        const o = await dms.placeSecondaryOrder(body);
        toast.success(`Order ${o.order_no} placed`);
        nav("/dms/salesperson/orders");
      }
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };

  if (!targetRid) return <div className="p-8 text-center text-slate-500">retailer_id missing</div>;

  return (
    <div className="pb-32">
      <PageHeader
        title={editId ? `Edit Order · ${existingOrder?.order_no || "…"}` : `Order for ${data.retailer?.name || "…"}`}
        subtitle={`Mode: ${data.mode === "box_pcs" ? "Box + Nos" : "Box (Nos also enterable)"}`}
        back={editId ? "/dms/salesperson/orders" : "/dms/salesperson/retailers"}
      />

      {/* Category filter chips */}
      {categories.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2 items-center">
          <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold flex items-center gap-1"><FilterIcon size={12} /> Category</span>
          <button onClick={() => setCatFilter("__all__")} data-testid="sp-cat-all"
                  className={`px-3 py-1 text-xs rounded-full border ${catFilter === "__all__" ? "bg-[#faf0cf] text-[#8a6600] border-[#c9a227] font-semibold" : "border-slate-200 text-slate-600 hover:bg-slate-50"}`}>
            All ({data.data.length})
          </button>
          {categories.map(c => {
            const count = data.data.filter(p => p.category_name === c).length;
            return (
              <button key={c} onClick={() => setCatFilter(c)} data-testid={`sp-cat-${c}`}
                      className={`px-3 py-1 text-xs rounded-full border ${catFilter === c ? "bg-[#faf0cf] text-[#8a6600] border-[#c9a227] font-semibold" : "border-slate-200 text-slate-600 hover:bg-slate-50"}`}>
                {c} ({count})
              </button>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {visibleProducts.map(p => {
          const q = cart[p.id] || { boxes: 0, pcs: 0 };
          return (
            <Card key={p.id} className="p-4">
              <div className="font-semibold">{p.name}</div>
              <div className="text-[11px] text-slate-500">{p.category_name || "—"}</div>
              <div className="text-xs font-mono text-slate-500">{p.sku_code}</div>
              <div className="mt-2 text-lg font-bold text-[#a67c00]">{inr(p.selling_price)}<span className="text-xs text-slate-500 font-normal">/box</span></div>
              <div className="text-xs text-slate-500">Stock: {p.distributor_stock_boxes} boxes</div>

              {/* Box qty */}
              <div className="mt-3 flex items-center justify-between gap-2">
                <span className="text-xs text-slate-600">Boxes</span>
                <div className="flex items-center gap-1">
                  <button onClick={() => setQty(p.id, "boxes", -1)} className="h-8 w-8 rounded border" data-testid={`sp-box-minus-${p.id}`}>-</button>
                  <span className="w-8 text-center font-semibold">{q.boxes || 0}</span>
                  <button onClick={() => setQty(p.id, "boxes", 1)} className="h-8 w-8 rounded border" data-testid={`sp-box-plus-${p.id}`}>+</button>
                </div>
              </div>

              {/* Nos qty — Phase 1: always available */}
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="text-xs text-slate-600">Nos (pcs)</span>
                <div className="flex items-center gap-1">
                  <button onClick={() => setQty(p.id, "pcs", -1)} className="h-8 w-8 rounded border" data-testid={`sp-pcs-minus-${p.id}`}>-</button>
                  <span className="w-8 text-center font-semibold">{q.pcs || 0}</span>
                  <button onClick={() => setQty(p.id, "pcs", 1)} className="h-8 w-8 rounded border" data-testid={`sp-pcs-plus-${p.id}`}>+</button>
                </div>
              </div>
            </Card>
          );
        })}
        {visibleProducts.length === 0 && <Card className="p-8 col-span-full text-center text-sm text-slate-500">No products in this category</Card>}
      </div>

      <div className="fixed bottom-0 left-0 lg:left-60 right-0 bg-white border-t border-slate-200 shadow-lg">
        <div className="p-4 flex items-center gap-4">
          <div className="flex-1"><div className="text-xs text-slate-500">{items.length} items</div><div className="text-xl font-bold">{inr(total)}</div></div>
          <Button disabled={items.length === 0 || busy} onClick={submit} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white h-11 px-6" data-testid="sp-place-order">
            <ShoppingCart size={16} className="mr-2" /> {editId ? "Update Order" : "Place Order"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// SP: My Orders (Phase 1 — BUG FIX + Edit + Cancel)
// ============================================================================
export function SpOrdersPage() {
  const [orders, setOrders] = useState([]);
  const [busy, setBusy] = useState(false);
  const [cancelFor, setCancelFor] = useState(null);
  const [reason, setReason] = useState("");
  const nav = useNavigate();

  const load = () => dms.listSecondaryOrders().then(d => setOrders(d.data || [])).catch(() => setOrders([]));
  useEffect(() => { load(); }, []);

  const doCancel = async () => {
    if (!cancelFor) return;
    setBusy(true);
    try {
      await dms.cancelSecondaryOrder(cancelFor.id, reason || "Cancelled by salesperson");
      toast.success(`Order ${cancelFor.order_no} cancelled`);
      setCancelFor(null); setReason("");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    setBusy(false);
  };

  return (
    <div>
      <PageHeader title="My Orders" subtitle="Sales orders you placed for your retailers" />
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Order</TableHead>
              <TableHead>Retailer</TableHead>
              <TableHead className="text-right">Items</TableHead>
              <TableHead className="text-right">Total</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Placed</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.length === 0 && <TableRow><TableCell colSpan={7} className="text-center py-8 text-slate-400">No orders yet — place an order from a retailer</TableCell></TableRow>}
            {orders.map(o => (
              <TableRow key={o.id} data-testid={`sp-order-row-${o.id}`}>
                <TableCell className="font-mono text-xs">{o.order_no}</TableCell>
                <TableCell className="font-medium">{o.retailer_name}</TableCell>
                <TableCell className="text-right">{o.items?.length || 0}</TableCell>
                <TableCell className="text-right font-semibold">{inr(o.total)}</TableCell>
                <TableCell><span className={`px-2 py-0.5 rounded-full text-xs border ${statusPill(o.status)}`}>{o.status}</span></TableCell>
                <TableCell className="text-xs text-slate-500">{niceDate(o.created_at)}</TableCell>
                <TableCell className="text-right">
                  {o.status === "pending" ? (
                    <div className="flex gap-1 justify-end">
                      <Button size="sm" variant="outline" onClick={() => nav(`/dms/salesperson/new-order?retailer_id=${o.retailer_id}&edit=${o.id}`)} data-testid={`sp-edit-order-${o.id}`}>
                        <Edit size={12} className="mr-1" /> Edit
                      </Button>
                      <Button size="sm" variant="outline" className="text-rose-700 border-rose-200 hover:bg-rose-50" onClick={() => setCancelFor(o)} data-testid={`sp-cancel-order-${o.id}`}>
                        <Ban size={12} className="mr-1" /> Cancel
                      </Button>
                    </div>
                  ) : (
                    <span className="text-xs text-slate-400">—</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={!!cancelFor} onOpenChange={o => { if (!o) { setCancelFor(null); setReason(""); } }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Cancel order {cancelFor?.order_no}?</DialogTitle></DialogHeader>
          <div className="text-sm text-slate-600">This will mark the order as cancelled and notify the distributor. This cannot be undone.</div>
          <div className="mt-3">
            <Label>Reason (optional)</Label>
            <Textarea rows={2} value={reason} onChange={e => setReason(e.target.value)} placeholder="e.g. Retailer changed mind" data-testid="sp-cancel-reason" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelFor(null)}>Keep Order</Button>
            <Button className="bg-rose-700 hover:bg-rose-800 text-white" disabled={busy} onClick={doCancel} data-testid="sp-cancel-confirm">Confirm Cancel</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================================
// SP: Receive Cash Payment (Phase 1)
// ============================================================================
export function SpCollectPaymentPage() {
  const [retailers, setRetailers] = useState([]);
  const [form, setForm] = useState({ retailer_id: "", amount: "", reference_no: "", description: "" });
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");
  const nav = useNavigate();

  useEffect(() => { dms.listRetailers().then(d => setRetailers(d.data || [])); }, []);

  const filtered = useMemo(() => {
    const n = q.trim().toLowerCase();
    if (!n) return retailers;
    return retailers.filter(r => (r.name || "").toLowerCase().includes(n) || (r.phone || "").toLowerCase().includes(n));
  }, [retailers, q]);

  const selected = retailers.find(r => r.id === form.retailer_id);

  const submit = async () => {
    setBusy(true);
    try {
      const amt = Number(form.amount);
      if (!form.retailer_id || !amt || amt <= 0) { toast.error("Pick retailer and enter amount"); setBusy(false); return; }
      await dms.recordSecondaryPayment({
        retailer_id: form.retailer_id,
        amount: amt,
        reference_no: form.reference_no || undefined,
        description: form.description || "Cash collection",
        method: "cash",
      });
      toast.success(`Collected ${inr(amt)} from ${selected?.name || "retailer"}`);
      setForm({ retailer_id: "", amount: "", reference_no: "", description: "" });
      nav("/dms/salesperson");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    setBusy(false);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <PageHeader title="Receive Cash Payment" subtitle="Record cash collected from a retailer" back="/dms/salesperson" />
      <Card className="p-6 space-y-4">
        {/* Retailer picker */}
        <div>
          <Label>Retailer *</Label>
          <div className="relative mt-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input value={q} onChange={e => setQ(e.target.value)} placeholder="Search retailer…" className="pl-9" data-testid="sp-collect-search" />
          </div>
          <div className="mt-2 max-h-56 overflow-y-auto border border-slate-200 rounded-lg divide-y">
            {filtered.length === 0 && <div className="p-4 text-xs text-slate-500 text-center">No retailers</div>}
            {filtered.map(r => (
              <button key={r.id}
                onClick={() => setForm({ ...form, retailer_id: r.id })}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-slate-50 ${form.retailer_id === r.id ? "bg-[#faf6e6]" : ""}`}
                data-testid={`sp-collect-pick-${r.id}`}>
                <div className="font-medium">{r.name}</div>
                <div className="text-xs text-slate-500">{r.phone} · {r.address}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Amount (₹) *</Label>
            <div className="relative">
              <IndianRupee size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <Input type="number" step="0.01" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} className="pl-8" data-testid="sp-collect-amount" />
            </div>
          </div>
          <div>
            <Label>Reference / Receipt #</Label>
            <Input value={form.reference_no} onChange={e => setForm({ ...form, reference_no: e.target.value })} placeholder="Optional" data-testid="sp-collect-ref" />
          </div>
        </div>
        <div>
          <Label>Note</Label>
          <Textarea rows={2} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Optional" />
        </div>
        <Button onClick={submit} disabled={busy || !form.retailer_id || !form.amount} className="w-full bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="sp-collect-submit">
          <Wallet size={16} className="mr-2" /> Record Cash Payment
        </Button>
      </Card>
    </div>
  );
}

// ============================================================================
// Team Leader Dashboard + Assignments
// ============================================================================
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
