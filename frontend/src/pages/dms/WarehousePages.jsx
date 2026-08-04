import React, { useEffect, useMemo, useState } from "react";
import { dms, inr } from "./api";
import { PageHeader } from "./OwnerPages";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { Plus, Trash2, Edit, Building2, ArrowLeftRight, Package, Boxes } from "lucide-react";

const today = () => new Date().toISOString().slice(0, 10);
const canWrite = (role) => ["owner", "owner_accountant", "super_admin"].includes(role);
const canOwner = (role) => ["owner", "super_admin"].includes(role);

// ============================================================
// Godowns Page — list, create, edit, delete + drill into inventory
// ============================================================
export function GodownsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", address: "", manager_name: "", phone: "", capacity_boxes: 0, notes: "" });
  const [invOpen, setInvOpen] = useState(false);
  const [invGodown, setInvGodown] = useState(null);
  const [invRows, setInvRows] = useState([]);
  const [invTotals, setInvTotals] = useState({ total_boxes: 0, total_value: 0 });

  const load = async () => {
    try { const d = await dms.listGodowns(); setRows(d.data || []); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed to load"); }
  };
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm({ name: "", address: "", manager_name: "", phone: "", capacity_boxes: 0, notes: "" }); setOpen(true); };
  const openEdit = (r) => { setEditing(r); setForm({ ...r }); setOpen(true); };
  const save = async () => {
    if (!form.name?.trim()) return toast.error("Godown name required");
    try {
      if (editing) await dms.updateGodown(editing.id, form);
      else await dms.createGodown(form);
      toast.success("Saved"); setOpen(false); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };
  const del = async (r) => {
    if (!window.confirm(`Delete godown ${r.name}?`)) return;
    try { await dms.deleteGodown(r.id); toast.success("Deleted"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Delete failed"); }
  };
  const openInv = async (r) => {
    setInvGodown(r);
    try {
      const d = await dms.godownInventory(r.id);
      setInvRows(d.data || []); setInvTotals({ total_boxes: d.total_boxes || 0, total_value: d.total_value || 0 });
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    setInvOpen(true);
  };

  return (
    <div className="space-y-4">
      <PageHeader title="Godowns" subtitle="Warehouse master — capacity + inventory per godown"
        action={canOwner(user?.role) && <Button onClick={openNew} className="bg-amber-600 hover:bg-amber-700"><Plus className="w-4 h-4 mr-2" />New Godown</Button>} />

      <Card className="overflow-hidden">
        <Table>
          <TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Manager</TableHead><TableHead>Phone</TableHead><TableHead>Address</TableHead><TableHead className="text-right">Capacity</TableHead><TableHead className="text-right">Stock (Boxes)</TableHead><TableHead>Status</TableHead><TableHead className="text-right"></TableHead></TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 ? <TableRow><TableCell colSpan={8} className="text-center text-slate-500 py-8">No godowns.</TableCell></TableRow>
              : rows.map(r => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell>{r.manager_name || "—"}</TableCell>
                  <TableCell className="font-mono text-xs">{r.phone || "—"}</TableCell>
                  <TableCell className="text-xs">{r.address || "—"}</TableCell>
                  <TableCell className="text-right">{r.capacity_boxes || 0}</TableCell>
                  <TableCell className="text-right font-semibold">{r.total_boxes || 0}</TableCell>
                  <TableCell><Badge className={r.active ? "bg-emerald-600" : "bg-slate-500"}>{r.active ? "Active" : "Inactive"}</Badge></TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="outline" onClick={() => openInv(r)}><Boxes className="w-3 h-3 mr-1" />Inventory</Button>
                    {canOwner(user?.role) && <Button size="sm" variant="outline" className="ml-1" onClick={() => openEdit(r)}><Edit className="w-3 h-3" /></Button>}
                    {canOwner(user?.role) && <Button size="sm" variant="outline" className="ml-1 text-rose-600" onClick={() => del(r)}><Trash2 className="w-3 h-3" /></Button>}
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent><DialogHeader><DialogTitle>{editing ? "Edit Godown" : "New Godown"}</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3 py-2">
            <div className="col-span-2"><Label>Name*</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
            <div><Label>Manager</Label><Input value={form.manager_name} onChange={e => setForm({ ...form, manager_name: e.target.value })} /></div>
            <div><Label>Phone</Label><Input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} /></div>
            <div className="col-span-2"><Label>Address</Label><Textarea rows={2} value={form.address || ""} onChange={e => setForm({ ...form, address: e.target.value })} /></div>
            <div><Label>Capacity (Boxes)</Label><Input type="number" value={form.capacity_boxes} onChange={e => setForm({ ...form, capacity_boxes: e.target.value })} /></div>
            <div className="col-span-2"><Label>Notes</Label><Textarea rows={2} value={form.notes || ""} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button className="bg-amber-600 hover:bg-amber-700" onClick={save}>{editing ? "Update" : "Create"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={invOpen} onOpenChange={setInvOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader><DialogTitle>{invGodown?.name} — Inventory</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <Card className="p-3"><div className="text-xs uppercase text-slate-500">Total Boxes</div><div className="text-xl font-bold">{invTotals.total_boxes}</div></Card>
            <Card className="p-3"><div className="text-xs uppercase text-slate-500">Total Value</div><div className="text-xl font-bold text-amber-700">{inr(invTotals.total_value)}</div></Card>
          </div>
          <div className="max-h-[60vh] overflow-y-auto">
            <Table>
              <TableHeader><TableRow><TableHead>Product</TableHead><TableHead>SKU</TableHead><TableHead>Pack</TableHead><TableHead className="text-right">Boxes</TableHead><TableHead className="text-right">Unit Price</TableHead><TableHead className="text-right">Value</TableHead></TableRow></TableHeader>
              <TableBody>
                {invRows.length === 0 ? <TableRow><TableCell colSpan={6} className="text-center text-slate-500 py-6">No stock in this godown.</TableCell></TableRow>
                  : invRows.map(r => (
                    <TableRow key={r.id}>
                      <TableCell className="font-medium">{r.product_name}</TableCell>
                      <TableCell className="font-mono text-xs">{r.sku_code}</TableCell>
                      <TableCell className="text-xs">{r.pack_size || "—"}</TableCell>
                      <TableCell className="text-right">{r.qty_boxes}</TableCell>
                      <TableCell className="text-right">{inr(r.unit_price)}</TableCell>
                      <TableCell className="text-right font-medium">{inr(r.value)}</TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================
// Stock Transfers Page — list + new transfer form
// ============================================================
export function StockTransfersPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [products, setProducts] = useState([]);
  const [godowns, setGodowns] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    date: today(),
    from_type: "owner",
    from_godown_id: "",
    to_type: "godown",
    to_godown_id: "",
    notes: "",
    items: [{ product_id: "", qty_boxes: 1 }],
  });
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState(null);

  const load = async () => {
    try { const d = await dms.listStockTransfers(); setRows(d.data || []); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed to load"); }
  };
  useEffect(() => {
    load();
    dms.listProducts().then(d => setProducts(d.data || d || []));
    dms.listGodowns().then(d => setGodowns(d.data || []));
  }, []);

  const openNew = () => {
    setForm({ date: today(), from_type: "owner", from_godown_id: "", to_type: "godown", to_godown_id: "", notes: "", items: [{ product_id: "", qty_boxes: 1 }] });
    setOpen(true);
  };
  const addLine = () => setForm({ ...form, items: [...form.items, { product_id: "", qty_boxes: 1 }] });
  const rmLine = (i) => setForm({ ...form, items: form.items.filter((_, idx) => idx !== i) });
  const updateLine = (i, patch) => {
    const items = [...form.items]; items[i] = { ...items[i], ...patch }; setForm({ ...form, items });
  };

  const save = async () => {
    if (form.from_type === "godown" && !form.from_godown_id) return toast.error("Choose source godown");
    if (form.to_type === "godown" && !form.to_godown_id) return toast.error("Choose destination godown");
    if (form.from_type === "godown" && form.to_type === "godown" && form.from_godown_id === form.to_godown_id) return toast.error("Source and destination godowns can't be the same");
    if (form.from_type === "owner" && form.to_type === "owner") return toast.error("Source and destination can't both be Owner");
    const items = form.items.filter(it => it.product_id && Number(it.qty_boxes) > 0);
    if (items.length === 0) return toast.error("Add at least one product line");
    try {
      await dms.createStockTransfer({ ...form, items });
      toast.success("Transfer created"); setOpen(false); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Transfer failed"); }
  };

  const openDetail = async (r) => {
    try { const d = await dms.getStockTransfer(r.id); setDetail(d); setDetailOpen(true); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div className="space-y-4">
      <PageHeader title="Stock Transfers" subtitle="Move stock between owner warehouse and godowns"
        action={canOwner(user?.role) && <Button onClick={openNew} className="bg-amber-600 hover:bg-amber-700"><Plus className="w-4 h-4 mr-2" />New Transfer</Button>} />

      <Card className="overflow-hidden">
        <Table>
          <TableHeader><TableRow><TableHead>Transfer No.</TableHead><TableHead>Date</TableHead><TableHead>From</TableHead><TableHead>To</TableHead><TableHead className="text-right">Boxes</TableHead><TableHead>By</TableHead><TableHead className="text-right"></TableHead></TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 ? <TableRow><TableCell colSpan={7} className="text-center text-slate-500 py-8">No transfers yet.</TableCell></TableRow>
              : rows.map(r => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono">{r.transfer_no}</TableCell>
                  <TableCell>{r.date}</TableCell>
                  <TableCell><Badge variant="outline">{r.from_godown_name}</Badge></TableCell>
                  <TableCell><ArrowLeftRight className="w-3 h-3 inline mr-1 text-slate-400" /><Badge variant="outline">{r.to_godown_name}</Badge></TableCell>
                  <TableCell className="text-right font-semibold">{r.total_boxes}</TableCell>
                  <TableCell className="text-xs">{r.created_by_name || "—"}</TableCell>
                  <TableCell className="text-right"><Button size="sm" variant="outline" onClick={() => openDetail(r)}>View</Button></TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader><DialogTitle>New Stock Transfer</DialogTitle></DialogHeader>
          <div className="space-y-3 max-h-[70vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Date*</Label><Input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} /></div>
              <div></div>
              <div><Label>From*</Label>
                <Select value={form.from_type} onValueChange={v => setForm({ ...form, from_type: v, from_godown_id: v === "owner" ? "" : form.from_godown_id })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="owner">Owner Warehouse</SelectItem><SelectItem value="godown">Godown</SelectItem></SelectContent>
                </Select></div>
              <div>
                {form.from_type === "godown" && (<><Label>Source Godown*</Label>
                  <Select value={form.from_godown_id} onValueChange={v => setForm({ ...form, from_godown_id: v })}>
                    <SelectTrigger><SelectValue placeholder="Choose" /></SelectTrigger>
                    <SelectContent>{godowns.map(g => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}</SelectContent>
                  </Select></>)}
              </div>
              <div><Label>To*</Label>
                <Select value={form.to_type} onValueChange={v => setForm({ ...form, to_type: v, to_godown_id: v === "owner" ? "" : form.to_godown_id })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="godown">Godown</SelectItem><SelectItem value="owner">Owner Warehouse</SelectItem></SelectContent>
                </Select></div>
              <div>
                {form.to_type === "godown" && (<><Label>Destination Godown*</Label>
                  <Select value={form.to_godown_id} onValueChange={v => setForm({ ...form, to_godown_id: v })}>
                    <SelectTrigger><SelectValue placeholder="Choose" /></SelectTrigger>
                    <SelectContent>{godowns.map(g => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}</SelectContent>
                  </Select></>)}
              </div>
            </div>

            <div className="border rounded p-3 bg-slate-50">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium">Items</div>
                <Button size="sm" variant="outline" onClick={addLine}><Plus className="w-3 h-3 mr-1" />Add Line</Button>
              </div>
              {form.items.map((it, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 mb-2 items-center">
                  <div className="col-span-8">
                    <Select value={it.product_id} onValueChange={v => updateLine(i, { product_id: v })}>
                      <SelectTrigger><SelectValue placeholder="Choose product" /></SelectTrigger>
                      <SelectContent>{products.map(p => <SelectItem key={p.id} value={p.id}>{p.name} ({p.sku_code})</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-3"><Input type="number" min={1} value={it.qty_boxes} onChange={e => updateLine(i, { qty_boxes: Number(e.target.value) })} placeholder="Boxes" /></div>
                  <div className="col-span-1"><Button size="sm" variant="outline" className="text-rose-600" onClick={() => rmLine(i)}><Trash2 className="w-3 h-3" /></Button></div>
                </div>
              ))}
            </div>

            <div><Label>Notes</Label><Textarea rows={2} value={form.notes || ""} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button className="bg-amber-600 hover:bg-amber-700" onClick={save}>Create Transfer</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Transfer {detail?.transfer_no}</DialogTitle></DialogHeader>
          {detail && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-500">Date: </span>{detail.date}</div>
                <div><span className="text-slate-500">By: </span>{detail.created_by_name}</div>
                <div><span className="text-slate-500">From: </span><Badge variant="outline">{detail.from_godown_name}</Badge></div>
                <div><span className="text-slate-500">To: </span><Badge variant="outline">{detail.to_godown_name}</Badge></div>
              </div>
              <Table>
                <TableHeader><TableRow><TableHead>Product</TableHead><TableHead>SKU</TableHead><TableHead className="text-right">Boxes</TableHead></TableRow></TableHeader>
                <TableBody>{(detail.items || []).map((it, i) => (<TableRow key={i}><TableCell>{it.product_name}</TableCell><TableCell className="font-mono text-xs">{it.sku_code}</TableCell><TableCell className="text-right">{it.qty_boxes}</TableCell></TableRow>))}</TableBody>
              </Table>
              {detail.notes && <div className="text-sm text-slate-600"><strong>Notes:</strong> {detail.notes}</div>}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
