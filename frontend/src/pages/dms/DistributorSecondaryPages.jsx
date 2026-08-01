import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { dms, inr, niceDate, statusPill } from "./api";
import { PageHeader } from "./OwnerPages";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Plus, ChevronRight, Store, Truck, Receipt, IndianRupee, MapPin, Printer } from "lucide-react";
import LocationDocumentsBlock from "./LocationDocumentsBlock";

// Distributor: retailers list
export function DistRetailersPage() {
  const [list, setList] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({});
  const nav = useNavigate();
  const load = () => dms.listRetailers().then(d => setList(d.data));
  useEffect(() => { load(); }, []);
  const openNew = () => { setForm({ name: "", phone: "", address: "", region: "", email: "", password: "Demo@2026", gstin: "", shop_license: "", credit_limit: 100000 }); setOpen(true); };
  const save = async () => {
    try { await dms.createRetailer(form); toast.success("Retailer added"); setOpen(false); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };
  return (
    <div>
      <PageHeader title="My Retailers" subtitle="Manage retailers under your distribution"
        action={<Button onClick={openNew} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="add-retailer-btn"><Plus size={16} className="mr-1" /> Add Retailer</Button>} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {list.map(r => (
          <Card key={r.id} className="p-4 cursor-pointer hover:shadow-md" onClick={() => nav(`/dms/distributor/retailers/${r.id}`)}>
            <div className="font-semibold">{r.name}</div>
            <div className="text-xs text-slate-500 mt-0.5">{r.phone}</div>
            <div className="text-xs text-slate-500 truncate">{r.address}</div>
            {r.gps_lat && <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1"><MapPin size={10} /> {r.gps_lat.toFixed(4)}, {r.gps_lng.toFixed(4)}</div>}
            <div className="mt-3 text-[#a67c00] text-xs font-medium">Manage → <ChevronRight size={12} className="inline" /></div>
          </Card>
        ))}
      </div>
      {list.length === 0 && <Card className="p-8 text-center text-sm text-slate-500">No retailers yet</Card>}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Add Retailer</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Shop Name *</Label><Input value={form.name || ""} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="ret-name" /></div>
            <div><Label>Phone *</Label><Input value={form.phone || ""} onChange={e => setForm({ ...form, phone: e.target.value })} /></div>
            <div className="col-span-2"><Label>Address *</Label><Textarea rows={2} value={form.address || ""} onChange={e => setForm({ ...form, address: e.target.value })} /></div>
            <div><Label>Region</Label><Input value={form.region || ""} onChange={e => setForm({ ...form, region: e.target.value })} /></div>
            <div><Label>Credit Limit (₹)</Label><Input type="number" value={form.credit_limit || ""} onChange={e => setForm({ ...form, credit_limit: Number(e.target.value) })} /></div>
            <div><Label>Login Email (optional)</Label><Input type="email" value={form.email || ""} onChange={e => setForm({ ...form, email: e.target.value })} data-testid="ret-email" /></div>
            <div><Label>Password</Label><Input value={form.password || ""} onChange={e => setForm({ ...form, password: e.target.value })} /></div>
            <div><Label>GSTIN</Label><Input value={form.gstin || ""} onChange={e => setForm({ ...form, gstin: e.target.value })} /></div>
            <div><Label>Shop License</Label><Input value={form.shop_license || ""} onChange={e => setForm({ ...form, shop_license: e.target.value })} /></div>
            <div className="col-span-2">
              <LocationDocumentsBlock
                lat={form.gps_lat ?? ""}
                lng={form.gps_lng ?? ""}
                locationLink={form.location_link || ""}
                onLat={(v) => setForm(f => ({ ...f, gps_lat: v === "" ? null : Number(v) }))}
                onLng={(v) => setForm(f => ({ ...f, gps_lng: v === "" ? null : Number(v) }))}
                onLocationLink={(v) => setForm(f => ({ ...f, location_link: v }))}
                documents={form.documents || []}
                onDocuments={(docs) => setForm(f => ({ ...f, documents: docs }))}
                helpText="After the retailer logs in, they can update their exact Latitude / Longitude if needed."
              />
            </div>
          </div>
          <DialogFooter><Button onClick={save} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="save-retailer-btn">Create</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function DistRetailerDetailPage() {
  const { id } = useParams();
  const [r, setR] = useState(null);
  const [tab, setTab] = useState("visibility");
  const [vis, setVis] = useState([]);
  const [mode, setMode] = useState("box");
  const load = async () => {
    const [rr, vv, mm] = await Promise.all([dms.getRetailer(id), dms.getRetVisibility(id), dms.getRetMode(id)]);
    setR(rr); setVis(vv.data); setMode(mm.mode);
  };
  useEffect(() => { load(); }, [id]);
  const toggleVis = async (pid, v) => { await dms.setRetVisibility(id, { product_id: pid, visible: v }); setVis(vis.map(x => x.product_id === pid ? { ...x, visible: v } : x)); };
  const changeMode = async (m) => { await dms.setRetMode(id, { mode: m }); setMode(m); toast.success(`Mode: ${m === "box_pcs" ? "Box + PCS" : "Box only"}`); };
  if (!r) return <div className="p-8 text-center text-slate-500">Loading…</div>;
  return (
    <div>
      <PageHeader title={r.name} subtitle={`${r.phone} • ${r.address}`} back="/dms/distributor/retailers" />
      <div className="flex gap-2 mb-4 border-b border-slate-200">
        {[{ k: "visibility", l: "Product Visibility" }, { k: "mode", l: "Selling Mode" }, { k: "info", l: "Details" }].map(t => (
          <button key={t.k} onClick={() => setTab(t.k)} className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === t.k ? "border-[#a67c00] text-[#a67c00]" : "border-transparent text-slate-500 hover:text-slate-700"}`}>{t.l}</button>
        ))}
      </div>
      {tab === "visibility" && (
        <Card>
          <div className="p-4 border-b border-slate-100 text-sm text-slate-600">Turn OFF products this retailer should not see</div>
          <Table><TableHeader><TableRow><TableHead>SKU</TableHead><TableHead>Product</TableHead><TableHead className="text-right">Visible</TableHead></TableRow></TableHeader><TableBody>
            {vis.map(v => (
              <TableRow key={v.product_id}><TableCell className="font-mono text-xs">{v.sku_code}</TableCell><TableCell>{v.product_name}</TableCell><TableCell className="text-right"><Switch checked={v.visible} onCheckedChange={c => toggleVis(v.product_id, c)} /></TableCell></TableRow>
            ))}
          </TableBody></Table>
        </Card>
      )}
      {tab === "mode" && (
        <Card className="p-6 max-w-md">
          <div className="font-semibold text-slate-900 mb-3">How can this retailer order?</div>
          <div className="space-y-2">
            {[{ v: "box", l: "Box only", d: "Retailer can order full boxes only" }, { v: "box_pcs", l: "Box + PCS (pieces)", d: "Retailer can order individual pieces too" }].map(o => (
              <label key={o.v} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer ${mode === o.v ? "border-[#c9a227] bg-[#faf6e6]" : "border-slate-200 hover:bg-slate-50"}`}>
                <input type="radio" checked={mode === o.v} onChange={() => changeMode(o.v)} />
                <div><div className="font-medium text-slate-900">{o.l}</div><div className="text-xs text-slate-500">{o.d}</div></div>
              </label>
            ))}
          </div>
        </Card>
      )}
      {tab === "info" && (
        <Card className="p-6">
          <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
            {[["Name", r.name], ["Phone", r.phone], ["Address", r.address], ["Region", r.region], ["GSTIN", r.kyc?.gstin], ["Shop License", r.kyc?.shop_license], ["Credit Limit", inr(r.credit_limit)], ["GPS", r.gps_lat ? `${r.gps_lat.toFixed(4)}, ${r.gps_lng.toFixed(4)}` : "—"]].map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-slate-100 py-1.5"><span className="text-slate-500">{k}</span><span className="text-slate-900 font-medium">{v || "—"}</span></div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// Distributor: secondary orders (received from retailers) + dispatch
export function DistSecondaryOrdersPage() {
  const [list, setList] = useState([]);
  const nav = useNavigate();
  useEffect(() => { dms.listSecondaryOrders().then(d => setList(d.data)); }, []);
  return (
    <div>
      <PageHeader title="Retailer Orders" subtitle="Orders retailers placed with you — dispatch to complete" />
      <Card>
        <Table><TableHeader><TableRow><TableHead>Order #</TableHead><TableHead>Retailer</TableHead><TableHead>Mode</TableHead><TableHead>Total</TableHead><TableHead>Fulfillment</TableHead><TableHead>Status</TableHead><TableHead>Placed</TableHead></TableRow></TableHeader><TableBody>
          {list.map(o => (
            <TableRow key={o.id} className="cursor-pointer hover:bg-slate-50" onClick={() => nav(`/dms/distributor/retail-orders/${o.id}`)}>
              <TableCell className="font-mono text-sm">{o.order_no}</TableCell>
              <TableCell className="font-medium">{o.retailer_name}</TableCell>
              <TableCell><span className="text-xs bg-slate-100 px-2 py-0.5 rounded">{o.mode === "box_pcs" ? "Box+PCS" : "Box"}</span></TableCell>
              <TableCell className="font-semibold">{inr(o.total)}</TableCell>
              <TableCell><div className="flex items-center gap-2 min-w-[100px]"><div className="w-16 h-1.5 bg-slate-100 rounded overflow-hidden"><div className="h-full bg-[#faf6e6]0" style={{ width: `${o.fulfillment_pct || 0}%` }} /></div><span className="text-xs">{o.fulfillment_pct || 0}%</span></div></TableCell>
              <TableCell><span className={`text-xs px-2 py-1 rounded-full border ${statusPill(o.status)}`}>{o.status.replace(/_/g, " ")}</span></TableCell>
              <TableCell className="text-xs text-slate-500">{niceDate(o.created_at)}</TableCell>
            </TableRow>
          ))}
        </TableBody></Table>
        {list.length === 0 && <div className="p-8 text-center text-sm text-slate-500">No orders</div>}
      </Card>
    </div>
  );
}

export function DistSecondaryOrderDetailPage() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [dispatch, setDispatch] = useState({}); // product_id -> {boxes, pcs}
  const [busy, setBusy] = useState(false);
  const load = () => dms.getSecondaryOrder(id).then(o => {
    setOrder(o);
    const init = {};
    o.items.forEach(it => init[it.product_id] = { boxes: it.qty_boxes_ordered, pcs: it.qty_pcs_ordered });
    setDispatch(init);
  });
  useEffect(() => { load(); }, [id]);
  if (!order) return <div className="p-8 text-center text-slate-500">Loading…</div>;
  const canDispatch = order.status === "pending";
  const doDispatch = async () => {
    if (!window.confirm("Dispatch this order? Bill will be generated and stock deducted.")) return;
    setBusy(true);
    try {
      const items = order.items.map(it => ({ product_id: it.product_id, qty_boxes_dispatched: Number(dispatch[it.product_id]?.boxes || 0), qty_pcs_dispatched: Number(dispatch[it.product_id]?.pcs || 0) }));
      await dms.dispatchSecondary(id, { items });
      toast.success("Dispatched — bill generated");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };
  return (
    <div>
      <PageHeader title={order.order_no} subtitle={`${order.retailer_name} • Placed ${niceDate(order.created_at)}`} back="/dms/distributor/retail-orders"
        action={<div className="flex gap-2">
          {order.bill_id && <Button variant="outline" onClick={() => window.open(`/dms/print/retailer-bill/${order.bill_id}`, "_blank")}><Printer size={14} className="mr-1" /> Print Bill</Button>}
          {canDispatch && <Button onClick={doDispatch} disabled={busy} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="dispatch-btn"><Truck size={14} className="mr-1" /> Dispatch</Button>}
        </div>} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Status</div><div className="mt-1"><span className={`text-sm px-2.5 py-1 rounded-full border ${statusPill(order.status)}`}>{order.status.replace(/_/g, " ")}</span></div></Card>
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Selling Mode</div><div className="mt-1 font-semibold">{order.mode === "box_pcs" ? "Box + PCS" : "Box only"}</div></Card>
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Order Value</div><div className="mt-1 font-bold text-lg">{inr(order.total)}</div></Card>
      </div>
      <Card>
        <div className="p-4 border-b border-slate-100 font-semibold">Items — set dispatch quantities</div>
        <Table><TableHeader><TableRow><TableHead>Product</TableHead><TableHead>Ordered</TableHead><TableHead>Dispatching</TableHead><TableHead>Line Total</TableHead></TableRow></TableHeader><TableBody>
          {order.items.map(it => {
            const d = dispatch[it.product_id] || { boxes: 0, pcs: 0 };
            return (
              <TableRow key={it.product_id}>
                <TableCell><div className="font-medium">{it.product_name}</div>{it.carried_pending && <span className="text-[10px] uppercase bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">Pending Carry-forward</span>}</TableCell>
                <TableCell>{it.qty_boxes_ordered} boxes {it.qty_pcs_ordered > 0 && `+ ${it.qty_pcs_ordered} pcs`}</TableCell>
                <TableCell>
                  {canDispatch ? (
                    <div className="flex items-center gap-2">
                      <Input type="number" min={0} max={it.qty_boxes_ordered} value={d.boxes} onChange={e => setDispatch({ ...dispatch, [it.product_id]: { ...d, boxes: e.target.value } })} className="w-20" />
                      <span className="text-xs text-slate-500">bx</span>
                      {order.mode === "box_pcs" && it.qty_pcs_ordered > 0 && <>
                        <Input type="number" min={0} max={it.qty_pcs_ordered} value={d.pcs} onChange={e => setDispatch({ ...dispatch, [it.product_id]: { ...d, pcs: e.target.value } })} className="w-20" />
                        <span className="text-xs text-slate-500">pcs</span>
                      </>}
                    </div>
                  ) : (
                    <span className="font-semibold">{it.qty_boxes_dispatched} boxes {it.qty_pcs_dispatched > 0 && `+ ${it.qty_pcs_dispatched} pcs`}</span>
                  )}
                </TableCell>
                <TableCell className="font-medium">{inr(it.line_total)}</TableCell>
              </TableRow>
            );
          })}
        </TableBody></Table>
      </Card>
    </div>
  );
}

// Secondary Ledger (used by distributor + distributor_accountant)
export function SecondaryLedgerPage() {
  const [data, setData] = useState({ entries: [], summary: [] });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ retailer_id: "", amount: "", method: "cash" });
  const [retailers, setRetailers] = useState([]);
  const load = () => Promise.all([dms.secondaryLedger(), dms.listRetailers()]).then(([l, r]) => { setData(l); setRetailers(r.data); });
  useEffect(() => { load(); }, []);
  const save = async () => {
    try { await dms.recordSecondaryPayment({ ...form, amount: Number(form.amount) }); toast.success("Payment recorded"); setOpen(false); setForm({ retailer_id: "", amount: "", method: "cash" }); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };
  return (
    <div>
      <PageHeader title="Secondary Sales Ledger" subtitle="Distributor ↔ Retailer transactions"
        action={<Button onClick={() => setOpen(true)} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="record-sec-payment"><IndianRupee size={16} className="mr-1" /> Record Payment</Button>} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
        {data.summary.map(s => (
          <Card key={s.retailer_id} className="p-4">
            <div className="text-sm font-semibold">{s.retailer_name}</div>
            <div className="mt-2 grid grid-cols-3 gap-2 text-center">
              <div><div className="text-[10px] uppercase tracking-wider text-slate-500">Billed</div><div className="font-semibold text-sm">{inr(s.billed)}</div></div>
              <div><div className="text-[10px] uppercase tracking-wider text-slate-500">Paid</div><div className="font-semibold text-emerald-700 text-sm">{inr(s.paid)}</div></div>
              <div><div className="text-[10px] uppercase tracking-wider text-slate-500">Due</div><div className="font-bold text-rose-700 text-sm">{inr(s.outstanding)}</div></div>
            </div>
            <button onClick={() => { setForm({ retailer_id: s.retailer_id, amount: "", method: "cash" }); setOpen(true); }} className="mt-3 w-full text-xs text-[#a67c00] hover:bg-[#faf6e6] py-1.5 rounded">Mark payment</button>
          </Card>
        ))}
      </div>
      <Card>
        <div className="p-4 border-b border-slate-100 font-semibold">Entries</div>
        <Table><TableHeader><TableRow><TableHead>Date</TableHead><TableHead>Retailer</TableHead><TableHead>Reference</TableHead><TableHead>Type</TableHead><TableHead className="text-right">Amount</TableHead></TableRow></TableHeader><TableBody>
          {data.entries.map(e => {
            const rn = retailers.find(r => r.id === e.retailer_id)?.name || e.retailer_id;
            return (
              <TableRow key={e.id}><TableCell className="text-xs text-slate-500">{niceDate(e.at)}</TableCell><TableCell className="font-medium">{rn}</TableCell><TableCell className="font-mono text-xs">{e.reference_no}</TableCell><TableCell><span className={`text-xs px-2 py-0.5 rounded ${e.kind === "invoice" ? "bg-rose-50 text-rose-700" : "bg-emerald-50 text-emerald-700"}`}>{e.kind}</span></TableCell><TableCell className={`text-right font-semibold ${e.kind === "invoice" ? "text-rose-700" : "text-emerald-700"}`}>{e.kind === "invoice" ? "+" : "-"}{inr(e.amount)}</TableCell></TableRow>
            );
          })}
        </TableBody></Table>
      </Card>
      <Dialog open={open} onOpenChange={setOpen}><DialogContent>
        <DialogHeader><DialogTitle>Record Payment from Retailer</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div><Label>Retailer *</Label>
            <Select value={form.retailer_id} onValueChange={v => setForm({ ...form, retailer_id: v })}>
              <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>{retailers.map(r => <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div><Label>Amount (₹) *</Label><Input type="number" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} data-testid="sec-pay-amt" /></div>
          <div><Label>Method</Label>
            <Select value={form.method} onValueChange={v => setForm({ ...form, method: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="cash">Cash</SelectItem><SelectItem value="upi">UPI</SelectItem><SelectItem value="bank_transfer">Bank Transfer</SelectItem><SelectItem value="cheque">Cheque</SelectItem></SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter><Button onClick={save} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="save-sec-payment">Save</Button></DialogFooter>
      </DialogContent></Dialog>
    </div>
  );
}
