import React, { useEffect, useState, useRef } from "react";
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
import { Upload, Download, Plus, Trash2, FileText, Eye, Printer } from "lucide-react";

const today = () => new Date().toISOString().slice(0, 10);

// tiny helper to trigger blob download
function downloadBlob(blob, name) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name; document.body.appendChild(a); a.click();
  document.body.removeChild(a); window.URL.revokeObjectURL(url);
}

// =====================================================================
// Import / Export Page (owner only)
// =====================================================================
export function ImportExportPage() {
  const [busy, setBusy] = useState("");
  const [importResult, setImportResult] = useState(null);
  const partiesRef = useRef(null);
  const productsRef = useRef(null);
  const saleBillsRef = useRef(null);
  const paymentsRef = useRef(null);

  const doExport = async (label, fn, filename) => {
    setBusy(label);
    try {
      const blob = await fn();
      downloadBlob(blob, `${filename}_${new Date().toISOString().slice(0, 10)}.xlsx`);
      toast.success(`${label} downloaded`);
    } catch (e) { toast.error(e?.response?.data?.detail || `${label} failed`); }
    setBusy("");
  };

  const doImport = async (label, fn, file) => {
    if (!file) return toast.error("Choose an .xlsx file");
    setBusy(label);
    try {
      const res = await fn(file);
      setImportResult({ label, ...res });
      toast.success(`${label} complete`);
    } catch (e) { toast.error(e?.response?.data?.detail || `${label} failed`); }
    setBusy("");
  };

  return (
    <div className="space-y-4">
      <PageHeader title="Import / Export" subtitle="Bulk data operations — Parties, Items, Sale Bills & Payments (import + export)" />

      <div className="grid md:grid-cols-2 gap-4">
        {/* Import Parties */}
        <Card className="p-5 border-emerald-200">
          <div className="flex items-center gap-3 mb-3">
            <Upload className="w-6 h-6 text-emerald-600" />
            <div>
              <div className="font-semibold">Parties (Import / Export)</div>
              <div className="text-xs text-slate-500">Distributors + Retailers via multi-sheet XLSX</div>
            </div>
          </div>
          <input ref={partiesRef} type="file" accept=".xlsx" className="text-sm mb-3 block" data-testid="import-parties-file" />
          <div className="flex gap-2 flex-wrap">
            <Button size="sm" onClick={() => doImport("Parties Import", dms.importParties, partiesRef.current?.files?.[0])} disabled={busy === "Parties Import"} className="bg-emerald-600 hover:bg-emerald-700">
              <Upload className="w-4 h-4 mr-1" />{busy === "Parties Import" ? "Uploading..." : "Import"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => doExport("Parties Export", dms.exportParties, "parties")} data-testid="export-parties-btn">
              <Download className="w-4 h-4 mr-1" />Export
            </Button>
          </div>
        </Card>

        {/* Import Items */}
        <Card className="p-5 border-emerald-200">
          <div className="flex items-center gap-3 mb-3">
            <Upload className="w-6 h-6 text-emerald-600" />
            <div>
              <div className="font-semibold">Items / Products (Import / Export)</div>
              <div className="text-xs text-slate-500">Products with pricing via XLSX</div>
            </div>
          </div>
          <input ref={productsRef} type="file" accept=".xlsx" className="text-sm mb-3 block" data-testid="import-products-file" />
          <div className="flex gap-2 flex-wrap">
            <Button size="sm" onClick={() => doImport("Items Import", dms.importProducts, productsRef.current?.files?.[0])} disabled={busy === "Items Import"} className="bg-emerald-600 hover:bg-emerald-700">
              <Upload className="w-4 h-4 mr-1" />{busy === "Items Import" ? "Uploading..." : "Import"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => doExport("Items Export", dms.exportProducts, "items")} data-testid="export-items-btn">
              <Download className="w-4 h-4 mr-1" />Export
            </Button>
          </div>
        </Card>

        {/* Sale Bills Import + Export */}
        <Card className="p-5 border-amber-200">
          <div className="flex items-center gap-3 mb-3">
            <FileText className="w-6 h-6 text-amber-600" />
            <div>
              <div className="font-semibold">Sale Bills (Import / Export)</div>
              <div className="text-xs text-slate-500">Retailer sale bills — posts to ledger on import</div>
            </div>
          </div>
          <input ref={saleBillsRef} type="file" accept=".xlsx" className="text-sm mb-3 block" data-testid="import-salebills-file" />
          <div className="flex gap-2 flex-wrap">
            <Button size="sm" onClick={() => doImport("Sale Bills Import", dms.importSaleBills, saleBillsRef.current?.files?.[0])} disabled={busy === "Sale Bills Import"} className="bg-amber-600 hover:bg-amber-700">
              <Upload className="w-4 h-4 mr-1" />{busy === "Sale Bills Import" ? "Uploading..." : "Import"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => doExport("Sale Bills Template", dms.saleBillsTemplate, "sale_bills_template")} data-testid="salebills-template-btn">
              <Download className="w-4 h-4 mr-1" />Template
            </Button>
            <Button size="sm" variant="outline" onClick={() => doExport("Sale Bills Export", dms.exportSaleBills, "sale_bills")}>
              <Download className="w-4 h-4 mr-1" />Export
            </Button>
          </div>
        </Card>

        {/* Payments Import + Export */}
        <Card className="p-5 border-amber-200">
          <div className="flex items-center gap-3 mb-3">
            <FileText className="w-6 h-6 text-amber-600" />
            <div>
              <div className="font-semibold">Payments (Import / Export)</div>
              <div className="text-xs text-slate-500">Primary + Secondary payments</div>
            </div>
          </div>
          <input ref={paymentsRef} type="file" accept=".xlsx" className="text-sm mb-3 block" data-testid="import-payments-file" />
          <div className="flex gap-2 flex-wrap">
            <Button size="sm" onClick={() => doImport("Payments Import", dms.importPayments, paymentsRef.current?.files?.[0])} disabled={busy === "Payments Import"} className="bg-amber-600 hover:bg-amber-700">
              <Upload className="w-4 h-4 mr-1" />{busy === "Payments Import" ? "Uploading..." : "Import"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => doExport("Payments Template", dms.paymentsTemplate, "payments_template")} data-testid="payments-template-btn">
              <Download className="w-4 h-4 mr-1" />Template
            </Button>
            <Button size="sm" variant="outline" onClick={() => doExport("Payments Export", dms.exportPayments, "payments")}>
              <Download className="w-4 h-4 mr-1" />Export
            </Button>
          </div>
        </Card>
      </div>

      {importResult && (
        <Card className="p-4 border-emerald-200 bg-emerald-50">
          <div className="font-semibold text-emerald-800 mb-2">{importResult.label} Result</div>
          <pre className="text-xs bg-white p-3 rounded overflow-auto">{JSON.stringify(importResult, null, 2)}</pre>
        </Card>
      )}
    </div>
  );
}

// =====================================================================
// Direct Sales Page (owner + distributor)
// =====================================================================
export function DirectSalesPage() {
  const { user } = useAuth();
  const [distributors, setDistributors] = useState([]);
  const [retailers, setRetailers] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState({
    distributor_id: "",
    retailer_id: "",
    date: today(),
    bill_no: "",
    notes: "",
    items: [{ product_id: "", qty_boxes: 1, box_price: 0 }],
  });
  const [busy, setBusy] = useState(false);
  const [lastBill, setLastBill] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const d = await dms.listDistributors();
        setDistributors(d.data || d || []);
        // preselect for distributor role
        if (user?.role === "distributor" || user?.role === "distributor_accountant") {
          setForm(f => ({ ...f, distributor_id: user.distributor_id || "" }));
        }
        const p = await dms.listProducts();
        setProducts(p.data || p || []);
      } catch (e) { toast.error("Failed loading masters"); }
    })();
  }, [user]);

  // when distributor changes, load their retailers
  useEffect(() => {
    if (!form.distributor_id) { setRetailers([]); return; }
    (async () => {
      try {
        const r = await dms.listRetailers({ distributor_id: form.distributor_id });
        setRetailers(r.data || r || []);
      } catch (e) { setRetailers([]); }
    })();
  }, [form.distributor_id]);

  const addLine = () => setForm({ ...form, items: [...form.items, { product_id: "", qty_boxes: 1, box_price: 0 }] });
  const rmLine = (i) => setForm({ ...form, items: form.items.filter((_, idx) => idx !== i) });
  const updLine = (i, patch) => {
    const items = [...form.items]; items[i] = { ...items[i], ...patch };
    // auto-fill price from product unit_price if empty
    if (patch.product_id && (!items[i].box_price || items[i].box_price === 0)) {
      const p = products.find(x => x.id === patch.product_id);
      if (p) items[i].box_price = p.unit_price || 0;
    }
    setForm({ ...form, items });
  };

  const subtotal = form.items.reduce((s, it) => s + (Number(it.qty_boxes) * Number(it.box_price || 0)), 0);

  const submit = async () => {
    if (!form.distributor_id) return toast.error("Choose distributor");
    if (!form.retailer_id) return toast.error("Choose retailer");
    const items = form.items.filter(it => it.product_id && Number(it.qty_boxes) > 0);
    if (items.length === 0) return toast.error("Add at least one product line");
    setBusy(true);
    try {
      const bill = await dms.createDirectSale({ ...form, items });
      setLastBill(bill); toast.success(`Bill ${bill.bill_no} created`);
      setForm({ distributor_id: form.distributor_id, retailer_id: "", date: today(), bill_no: "", notes: "", items: [{ product_id: "", qty_boxes: 1, box_price: 0 }] });
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
    setBusy(false);
  };

  return (
    <div className="space-y-4">
      <PageHeader title="+Add Sales (Direct Invoice)" subtitle="Create a retailer bill without a sales order" />

      <Card className="p-5">
        <div className="grid md:grid-cols-3 gap-3 mb-4">
          {user?.role !== "distributor" && user?.role !== "distributor_accountant" && (
            <div><Label>Distributor*</Label>
              <Select value={form.distributor_id} onValueChange={v => setForm({ ...form, distributor_id: v, retailer_id: "" })}>
                <SelectTrigger><SelectValue placeholder="Choose distributor" /></SelectTrigger>
                <SelectContent>{distributors.map(d => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}</SelectContent>
              </Select></div>
          )}
          <div><Label>Retailer*</Label>
            <Select value={form.retailer_id} onValueChange={v => setForm({ ...form, retailer_id: v })}>
              <SelectTrigger><SelectValue placeholder="Choose retailer" /></SelectTrigger>
              <SelectContent>{retailers.map(r => <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>)}</SelectContent>
            </Select></div>
          <div><Label>Date*</Label><Input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} /></div>
          <div><Label>Bill No. (auto)</Label><Input value={form.bill_no} onChange={e => setForm({ ...form, bill_no: e.target.value })} placeholder="Leave blank to auto-generate" /></div>
        </div>

        <div className="border rounded p-3 bg-slate-50">
          <div className="flex items-center justify-between mb-2">
            <div className="font-medium text-sm">Items</div>
            <Button size="sm" variant="outline" onClick={addLine}><Plus className="w-3 h-3 mr-1" />Add Line</Button>
          </div>
          {form.items.map((it, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 mb-2 items-center">
              <div className="col-span-6">
                <Select value={it.product_id} onValueChange={v => updLine(i, { product_id: v })}>
                  <SelectTrigger><SelectValue placeholder="Choose product" /></SelectTrigger>
                  <SelectContent>{products.map(p => <SelectItem key={p.id} value={p.id}>{p.name} ({p.sku_code})</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="col-span-2"><Input type="number" min={1} placeholder="Boxes" value={it.qty_boxes} onChange={e => updLine(i, { qty_boxes: Number(e.target.value) })} /></div>
              <div className="col-span-3"><Input type="number" min={0} placeholder="Box Price" value={it.box_price} onChange={e => updLine(i, { box_price: Number(e.target.value) })} /></div>
              <div className="col-span-1"><Button size="sm" variant="outline" className="text-rose-600" onClick={() => rmLine(i)}><Trash2 className="w-3 h-3" /></Button></div>
            </div>
          ))}
        </div>

        <div className="grid md:grid-cols-2 gap-3 mt-4">
          <div><Label>Notes</Label><Textarea rows={2} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          <div className="flex flex-col items-end justify-end">
            <div className="text-sm text-slate-500">Subtotal</div>
            <div className="text-2xl font-bold text-amber-700">{inr(subtotal)}</div>
            <Button className="mt-3 bg-amber-600 hover:bg-amber-700" onClick={submit} disabled={busy}>
              {busy ? "Creating..." : "Create Bill"}
            </Button>
          </div>
        </div>
      </Card>

      {lastBill && (
        <Card className="p-4 border-emerald-200 bg-emerald-50">
          <div className="font-semibold text-emerald-800">Last Created: {lastBill.bill_no}</div>
          <div className="text-sm text-slate-700">Total: {inr(lastBill.total)} · Items: {lastBill.items?.length || 0}</div>
        </Card>
      )}
    </div>
  );
}

// =====================================================================
// Documents Page (owner + distributor) — Estimate, DC, SR, CN, DN
// =====================================================================
const DOC_TYPES = [
  { value: "estimate", label: "Estimate / Quotation", prefix: "EST" },
  { value: "delivery_challan", label: "Delivery Challan", prefix: "DC" },
  { value: "sale_return", label: "Sale Return", prefix: "SR" },
  { value: "credit_note", label: "Credit Note", prefix: "CN" },
  { value: "debit_note", label: "Debit Note", prefix: "DN" },
];
// Delivery Challan is auto-generated from the Dispatch flow — not creatable here.
const DOC_CREATE_TYPES = DOC_TYPES.filter(t => t.value !== "delivery_challan");

export function DocumentsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState({ type: "", start: "", end: "" });
  const [open, setOpen] = useState(false);
  const [viewOpen, setViewOpen] = useState(false);
  const [viewDoc, setViewDoc] = useState(null);
  const [distributors, setDistributors] = useState([]);
  const [retailers, setRetailers] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState({
    type: "estimate", date: today(),
    party_type: "retailer", party_id: "",
    items: [{ description: "", product_id: "", qty: 1, rate: 0 }],
    gst_pct: 0, notes: "",
  });

  const load = async () => {
    try {
      const params = {};
      Object.entries(filter).forEach(([k, v]) => { if (v) params[k] = v; });
      const d = await dms.listDocuments(params); setRows(d.data || []);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);
  useEffect(() => {
    dms.listDistributors().then(d => setDistributors(d.data || d || []));
    dms.listRetailers().then(r => setRetailers(r.data || r || []));
    dms.listProducts().then(p => setProducts(p.data || p || []));
  }, []);

  const addLine = () => setForm({ ...form, items: [...form.items, { description: "", product_id: "", qty: 1, rate: 0 }] });
  const rmLine = (i) => setForm({ ...form, items: form.items.filter((_, idx) => idx !== i) });
  const updLine = (i, patch) => {
    const items = [...form.items]; items[i] = { ...items[i], ...patch };
    if (patch.product_id) {
      const p = products.find(x => x.id === patch.product_id);
      if (p) { items[i].description = p.name; if (!items[i].rate) items[i].rate = p.unit_price || 0; }
    }
    setForm({ ...form, items });
  };

  const subtotal = form.items.reduce((s, it) => s + (Number(it.qty) * Number(it.rate || 0)), 0);
  const gst_total = subtotal * Number(form.gst_pct || 0) / 100;
  const total = subtotal + gst_total;

  const submit = async () => {
    if (!form.party_id) return toast.error("Choose party");
    const items = form.items.filter(it => it.description && Number(it.qty) > 0);
    if (items.length === 0) return toast.error("Add at least one item");
    try {
      await dms.createDocument({ ...form, items });
      toast.success("Document created"); setOpen(false); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const openView = async (r) => {
    try { const d = await dms.getDocument(r.id); setViewDoc(d); setViewOpen(true); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const parties = form.party_type === "retailer" ? retailers : distributors;
  const label = (v) => DOC_TYPES.find(t => t.value === v)?.label || v;
  const badgeColor = { estimate: "bg-sky-600", delivery_challan: "bg-emerald-600", sale_return: "bg-rose-600", credit_note: "bg-violet-600", debit_note: "bg-amber-600" };

  return (
    <div className="space-y-4">
      <PageHeader title="Documents" subtitle="Estimate • Sale Return (updates stock) • Credit / Debit Note (posts to ledger)"
        action={<Button onClick={() => { setForm({ type: "estimate", date: today(), party_type: "retailer", party_id: "", items: [{ description: "", product_id: "", qty: 1, rate: 0 }], gst_pct: 0, notes: "" }); setOpen(true); }} className="bg-amber-600 hover:bg-amber-700"><Plus className="w-4 h-4 mr-2" />New Document</Button>} />

      <Card className="p-3">
        <div className="flex flex-wrap gap-2 items-end">
          <div><Label className="text-xs">Type</Label>
            <Select value={filter.type || "all"} onValueChange={v => setFilter({ ...filter, type: v === "all" ? "" : v })}>
              <SelectTrigger className="w-56"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="all">All types</SelectItem>{DOC_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}</SelectContent>
            </Select></div>
          <div><Label className="text-xs">From</Label><Input type="date" value={filter.start} onChange={e => setFilter({ ...filter, start: e.target.value })} /></div>
          <div><Label className="text-xs">To</Label><Input type="date" value={filter.end} onChange={e => setFilter({ ...filter, end: e.target.value })} /></div>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <Table>
          <TableHeader><TableRow><TableHead>Doc No.</TableHead><TableHead>Type</TableHead><TableHead>Date</TableHead><TableHead>Party</TableHead><TableHead className="text-right">Total</TableHead><TableHead>By</TableHead><TableHead className="text-right"></TableHead></TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 ? <TableRow><TableCell colSpan={7} className="text-center text-slate-500 py-8">No documents yet.</TableCell></TableRow>
              : rows.map(r => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono text-xs">{r.doc_no}</TableCell>
                  <TableCell><Badge className={badgeColor[r.type] || "bg-slate-500"}>{label(r.type)}</Badge></TableCell>
                  <TableCell>{r.date}</TableCell>
                  <TableCell>{r.party_name}</TableCell>
                  <TableCell className="text-right font-medium">{inr(r.total)}</TableCell>
                  <TableCell className="text-xs">{r.created_by_name || "—"}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="outline" onClick={() => openView(r)}><Eye className="w-3 h-3 mr-1" />View</Button>
                    <Button size="sm" variant="outline" className="ml-1" onClick={() => window.open(`/dms/print/document/${r.id}`, "_blank")}><Printer className="w-3 h-3" /></Button>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      {/* Create Dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader><DialogTitle>New Document</DialogTitle></DialogHeader>
          <div className="space-y-3 max-h-[75vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Type*</Label>
                <Select value={form.type} onValueChange={v => setForm({ ...form, type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{DOC_CREATE_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}</SelectContent>
                </Select></div>
              <div><Label>Date*</Label><Input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} /></div>
              <div><Label>Party Type*</Label>
                <Select value={form.party_type} onValueChange={v => setForm({ ...form, party_type: v, party_id: "" })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="retailer">Retailer</SelectItem><SelectItem value="distributor">Distributor</SelectItem></SelectContent>
                </Select></div>
              <div><Label>Party*</Label>
                <Select value={form.party_id} onValueChange={v => setForm({ ...form, party_id: v })}>
                  <SelectTrigger><SelectValue placeholder="Choose" /></SelectTrigger>
                  <SelectContent>{parties.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
                </Select></div>
            </div>
            {form.type === "sale_return" && (
              <div className="text-xs text-slate-600 bg-amber-50 border border-amber-200 rounded p-2.5">
                <b>Stock effect:</b> Return from a <b>Retailer</b> → your stock <b>increases</b>. Return to <b>Company</b> (party = your distributor) → your stock <b>decreases</b>. Enter product-linked items with quantities in boxes.
              </div>
            )}
            {(form.type === "credit_note" || form.type === "debit_note") && (
              <div className="text-xs text-slate-600 bg-violet-50 border border-violet-200 rounded p-2.5">
                This {form.type === "credit_note" ? "Credit Note" : "Debit Note"} will be posted automatically to the selected party&apos;s ledger.
              </div>
            )}

            <div className="border rounded p-3 bg-slate-50">
              <div className="flex items-center justify-between mb-2">
                <div className="font-medium text-sm">Items</div>
                <Button size="sm" variant="outline" onClick={addLine}><Plus className="w-3 h-3 mr-1" />Add Line</Button>
              </div>
              {form.items.map((it, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 mb-2">
                  <div className="col-span-4">
                    <Select value={it.product_id || "custom"} onValueChange={v => updLine(i, { product_id: v === "custom" ? "" : v })}>
                      <SelectTrigger><SelectValue placeholder="Product (or custom)" /></SelectTrigger>
                      <SelectContent><SelectItem value="custom">— Custom —</SelectItem>{products.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-4"><Input placeholder="Description" value={it.description} onChange={e => updLine(i, { description: e.target.value })} /></div>
                  <div className="col-span-1"><Input type="number" min={0} placeholder="Qty" value={it.qty} onChange={e => updLine(i, { qty: Number(e.target.value) })} /></div>
                  <div className="col-span-2"><Input type="number" min={0} placeholder="Rate" value={it.rate} onChange={e => updLine(i, { rate: Number(e.target.value) })} /></div>
                  <div className="col-span-1"><Button size="sm" variant="outline" className="text-rose-600" onClick={() => rmLine(i)}><Trash2 className="w-3 h-3" /></Button></div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div><Label>GST %</Label><Input type="number" min={0} value={form.gst_pct} onChange={e => setForm({ ...form, gst_pct: Number(e.target.value) })} /></div>
              <div className="col-span-2"><Label>Notes</Label><Textarea rows={2} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
            </div>

            <div className="flex justify-end gap-4 text-sm border-t pt-3">
              <div><span className="text-slate-500">Subtotal: </span>{inr(subtotal)}</div>
              <div><span className="text-slate-500">GST: </span>{inr(gst_total)}</div>
              <div className="font-semibold text-lg text-amber-700"><span className="text-slate-500 text-sm">Total: </span>{inr(total)}</div>
            </div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button className="bg-amber-600 hover:bg-amber-700" onClick={submit}>Create</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Dialog */}
      <Dialog open={viewOpen} onOpenChange={setViewOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>{viewDoc && label(viewDoc.type)} — {viewDoc?.doc_no}</DialogTitle></DialogHeader>
          {viewDoc && (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div><span className="text-slate-500">Date: </span>{viewDoc.date}</div>
                <div><span className="text-slate-500">Party: </span>{viewDoc.party_name}</div>
                <div><span className="text-slate-500">By: </span>{viewDoc.created_by_name || "—"}</div>
              </div>
              <Table>
                <TableHeader><TableRow><TableHead>Description</TableHead><TableHead className="text-right">Qty</TableHead><TableHead className="text-right">Rate</TableHead><TableHead className="text-right">Amount</TableHead></TableRow></TableHeader>
                <TableBody>{(viewDoc.items || []).map((it, i) => (
                  <TableRow key={i}><TableCell>{it.description}</TableCell><TableCell className="text-right">{it.qty}</TableCell><TableCell className="text-right">{inr(it.rate)}</TableCell><TableCell className="text-right">{inr(it.amount)}</TableCell></TableRow>
                ))}</TableBody>
              </Table>
              <div className="flex justify-end gap-4 text-sm border-t pt-3">
                <div><span className="text-slate-500">Subtotal: </span>{inr(viewDoc.subtotal)}</div>
                <div><span className="text-slate-500">GST: </span>{inr(viewDoc.gst_total)}</div>
                <div className="font-semibold text-lg text-amber-700">{inr(viewDoc.total)}</div>
              </div>
              {viewDoc.notes && <div className="text-sm text-slate-600"><strong>Notes:</strong> {viewDoc.notes}</div>}
              <div className="flex justify-end">
                <Button size="sm" variant="outline" onClick={() => window.open(`/dms/print/document/${viewDoc.id}`, "_blank")}><Printer className="w-3 h-3 mr-1" />Print</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// =====================================================================
// Document Print View — standalone printable page (with distinct per-type styling)
// =====================================================================
const DOC_STYLES = {
  estimate: {
    accent: "#3b82f6",           // blue-500
    bg: "bg-blue-50",
    border: "border-blue-500",
    text: "text-blue-700",
    tag: "PROPOSAL",
  },
  delivery_challan: {
    accent: "#059669",           // emerald-600
    bg: "bg-emerald-50",
    border: "border-emerald-600",
    text: "text-emerald-700",
    tag: "DISPATCH",
  },
  sale_return: {
    accent: "#e11d48",           // rose-600
    bg: "bg-rose-50",
    border: "border-rose-600",
    text: "text-rose-700",
    tag: "RETURN",
  },
  credit_note: {
    accent: "#7c3aed",           // violet-600
    bg: "bg-violet-50",
    border: "border-violet-600",
    text: "text-violet-700",
    tag: "CR NOTE",
  },
  debit_note: {
    accent: "#ea580c",           // orange-600
    bg: "bg-orange-50",
    border: "border-orange-600",
    text: "text-orange-700",
    tag: "DR NOTE",
  },
};
const DEFAULT_DOC_STYLE = {
  accent: "#a67c00",
  bg: "bg-amber-50",
  border: "border-amber-600",
  text: "text-amber-700",
  tag: "DOCUMENT",
};

export function DocumentPrintPage() {
  const [doc, setDoc] = useState(null);
  useEffect(() => {
    const id = window.location.pathname.split("/").pop();
    dms.printDocument(id).then(d => setDoc(d)).catch(() => toast.error("Failed"));
  }, []);
  if (!doc) return <div className="p-6 text-slate-500">Loading…</div>;

  const style = DOC_STYLES[doc.type] || DEFAULT_DOC_STYLE;

  return (
    <div className="p-8 max-w-3xl mx-auto bg-white">
      {/* Header — distinct per doc type */}
      <div className={`mb-6 pb-4 border-b-2 ${style.border}`}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className={`text-3xl font-bold ${style.text}`}>{doc.company_name}</h1>
            <div className={`mt-2 inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold tracking-widest ${style.bg} ${style.text} border ${style.border}`}>
              <span>{style.tag}</span>
              <span className="opacity-40">•</span>
              <span>{doc.doc_type_label}</span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs uppercase text-slate-500 tracking-wide">{doc.doc_type_label} No</div>
            <div className={`text-lg font-mono font-semibold ${style.text}`}>{doc.doc_no}</div>
            <div className="text-xs text-slate-500 mt-1">Date: {doc.date}</div>
          </div>
        </div>
      </div>

      {/* Party block */}
      <div className={`p-4 rounded-lg ${style.bg} border ${style.border} mb-5`}>
        <div className="text-xs uppercase font-semibold text-slate-500 mb-1">Party</div>
        <div className="font-semibold text-slate-800">{doc.party_name}</div>
        <div className="grid grid-cols-2 gap-2 mt-2 text-xs text-slate-600">
          {doc.party?.gstin && <div><strong>GSTIN:</strong> {doc.party.gstin}</div>}
          {doc.party?.phone && <div><strong>Phone:</strong> {doc.party.phone}</div>}
          {doc.party?.address && <div className="col-span-2"><strong>Address:</strong> {doc.party.address}</div>}
        </div>
      </div>

      {/* Items */}
      <table className="w-full border-collapse mb-4 text-sm">
        <thead className={style.bg}><tr>
          <th className="border p-2 text-left">Description</th>
          <th className="border p-2 text-right">Qty</th>
          <th className="border p-2 text-right">Rate</th>
          <th className="border p-2 text-right">Amount</th>
        </tr></thead>
        <tbody>{(doc.items || []).map((it, i) => (
          <tr key={i}>
            <td className="border p-2">{it.description}</td>
            <td className="border p-2 text-right">{it.qty}</td>
            <td className="border p-2 text-right">{inr(it.rate)}</td>
            <td className="border p-2 text-right">{inr(it.amount)}</td>
          </tr>
        ))}</tbody>
      </table>

      {/* Totals */}
      <div className="flex justify-end mb-6"><div className="w-64 text-sm space-y-1">
        <div className="flex justify-between"><span>Subtotal</span><span>{inr(doc.subtotal)}</span></div>
        <div className="flex justify-between"><span>GST ({doc.gst_pct}%)</span><span>{inr(doc.gst_total)}</span></div>
        <div className={`flex justify-between font-bold text-lg border-t pt-1`}>
          <span>Total</span><span className={style.text}>{inr(doc.total)}</span>
        </div>
      </div></div>

      {doc.invoice_message && <div className="text-center italic text-slate-600 mb-4">{doc.invoice_message}</div>}
      {doc.invoice_terms && <div className="text-xs text-slate-500 border-t pt-3 whitespace-pre-wrap">{doc.invoice_terms}</div>}
      <div className="mt-6 text-center print:hidden">
        <Button onClick={() => window.print()} style={{ backgroundColor: style.accent }}>
          <Printer className="w-4 h-4 mr-2" />Print
        </Button>
      </div>
    </div>
  );
}
