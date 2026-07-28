import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import KpiCard from "@/components/common/KpiCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription, DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select, SelectTrigger, SelectContent, SelectItem, SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Undo2, ShieldAlert, HandCoins, FileMinus, FilePlus, Repeat, Timer, GitBranchPlus,
  AlertOctagon, FileBarChart2, Plus, Loader2, CheckCircle2, XCircle, RefreshCw, ScanLine, Layers,
} from "lucide-react";

// ----------------------------------------------------------
// SHARED CONSTANTS
// ----------------------------------------------------------
const RETURN_REASONS = [
  { v: "damaged_product", l: "Damaged Product" },
  { v: "expired_product", l: "Expired Product" },
  { v: "wrong_product", l: "Wrong Product" },
  { v: "short_supply", l: "Short Supply" },
  { v: "over_supply", l: "Over Supply" },
  { v: "transport_damage", l: "Transport Damage" },
  { v: "manufacturing_defect", l: "Manufacturing Defect" },
  { v: "customer_rejection", l: "Customer Rejection" },
];
const RETURN_SCOPES = ["customer", "retailer", "distributor", "company"];
const DAMAGE_SCOPES = ["warehouse", "transport", "distributor", "retailer", "customer"];
const CLAIM_TYPES = ["transport", "insurance", "manufacturer", "retailer", "distributor"];
const CN_REASONS = [
  { v: "return_approved", l: "Return Approved" },
  { v: "over_billing", l: "Over Billing" },
  { v: "wrong_invoice", l: "Wrong Invoice" },
  { v: "price_difference", l: "Price Difference" },
  { v: "partial_return", l: "Partial Return" },
];
const DN_REASONS = [
  { v: "additional_charges", l: "Additional Charges" },
  { v: "penalty", l: "Penalty" },
  { v: "short_payment", l: "Short Payment" },
  { v: "extra_supply", l: "Extra Supply" },
  { v: "transport_charges", l: "Transport Charges" },
];

const money = (n) => `$${(Number(n) || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
const shortDate = (v) => { try { return new Date(v).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }); } catch { return String(v || ""); } };

// ==========================================================
// RETURNS
// ==========================================================
export function ReturnsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [reload, setReload] = useState(0);
  const [tab, setTab] = useState("all");

  const load = () => {
    setLoading(true);
    const s = tab === "all" ? "" : `?status=${tab}`;
    api.get(`/reverse/returns${s}`).then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  };
  useEffect(load, [reload, tab]);

  const approve = async (id) => {
    try {
      await api.post(`/reverse/returns/${id}/approve`, { comment: "Approved" });
      toast.success("Return approved → inventory adjusted, credit note issued");
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const reject = async (id) => {
    try {
      await api.post(`/reverse/returns/${id}/reject`, { reason: "Rejected" });
      toast.success("Return rejected");
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const openReplacement = async (r) => {
    try {
      const p = await api.post("/reverse/replacements", {
        return_id: r.id, scope: r.scope, party_id: r.party_id, party_type: r.party_type,
        distributor_id: r.distributor_id, retailer_id: r.retailer_id, customer_id: r.customer_id,
        lines: r.lines,
      });
      toast.success(`Replacement ${p.data.replacement_no} created — pending approval`);
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  const counts = rows.reduce((acc, r) => { acc[r.status] = (acc[r.status] || 0) + 1; return acc; }, {});

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Reverse Logistics", "Returns"]}
        title="Return Management"
        subtitle="Multi-scope returns with 8 reason codes — auto approval chain, inventory adjustment and credit note issue"
        actions={<NewReturnDialog open={open} onOpenChange={setOpen} onDone={() => setReload((v) => v + 1)} />}
      />
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <KpiCard label="Total" value={rows.length} delta={`${counts.completed || 0} completed`} />
        <KpiCard label="Pending" value={counts.pending || 0} delta="new" />
        <KpiCard label="Under Review" value={counts.under_review || 0} delta="awaiting approvers" />
        <KpiCard label="Approved" value={counts.approved || 0} delta="ready for CN" />
        <KpiCard label="Rejected" value={counts.rejected || 0} delta="closed" />
      </div>
      <Tabs value={tab} onValueChange={setTab} className="mb-3">
        <TabsList className="bg-canvas border border-[#E5E7EB]">
          {["all", "pending", "under_review", "approved", "completed", "rejected"].map((t) =>
            <TabsTrigger key={t} value={t} data-testid={`ret-tab-${t}`}>{t.replace("_", " ")}</TabsTrigger>
          )}
        </TabsList>
      </Tabs>
      <DataTable
        data={rows} loading={loading} testId="returns-table" pageSize={12}
        columns={[
          { key: "return_no", label: "Return" },
          { key: "scope", label: "Scope", type: "chip" },
          { key: "reason", label: "Reason", type: "chip", render: (r) => (RETURN_REASONS.find((x) => x.v === r.reason)?.l || r.reason) },
          { key: "party_name", label: "Party" },
          { key: "invoice_no", label: "Invoice" },
          { key: "total", label: "Value", type: "currency", align: "right" },
          { key: "status", label: "Status", type: "status" },
          { key: "created_at", label: "Requested", type: "date" },
          { key: "actions", label: "", render: (r) => (
            <div className="flex gap-1">
              {(r.status === "pending" || r.status === "under_review") && (
                <>
                  <Button size="sm" className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => approve(r.id)} data-testid={`ret-approve-${r.id}`}>
                    <CheckCircle2 size={13} className="mr-1" /> Approve
                  </Button>
                  <Button size="sm" variant="outline" className="h-8 border-rose-200 text-rose-700" onClick={() => reject(r.id)} data-testid={`ret-reject-${r.id}`}>
                    <XCircle size={13} className="mr-1" /> Reject
                  </Button>
                </>
              )}
              {r.status === "completed" && (
                <Button size="sm" variant="outline" className="h-8 border-gold text-gold-dark" onClick={() => openReplacement(r)} data-testid={`ret-replace-${r.id}`}>
                  <Repeat size={13} className="mr-1" /> Replace
                </Button>
              )}
            </div>
          )},
        ]}
      />
    </div>
  );
}

function NewReturnDialog({ open, onOpenChange, onDone }) {
  const [form, setForm] = useState({
    scope: "customer", reason: "damaged_product", party_id: "", party_type: "customer",
    invoice_id: "", remarks: "",
    lines: [{ sku_id: "", batch_id: "", qty: 1, price: 0 }],
  });
  const [parties, setParties] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [skus, setSkus] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    api.get("/collections/skus?limit=500").then((r) => setSkus(r.data.data || []));
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const coll = form.party_type === "distributor" ? "distributors" : form.party_type === "retailer" ? "retailers" : "customers";
    api.get(`/collections/${coll}?limit=300`).then((r) => setParties(r.data.data || []));
  }, [open, form.party_type]);
  useEffect(() => {
    if (!form.party_id) { setInvoices([]); return; }
    api.get("/collections/invoices?limit=300").then((r) => {
      setInvoices((r.data.data || []).filter((i) => i.party_id === form.party_id));
    });
  }, [form.party_id]);

  const submit = async () => {
    setBusy(true);
    try {
      const body = { ...form, lines: form.lines.filter((l) => l.sku_id && l.qty > 0) };
      const p = await api.post("/reverse/returns", body);
      toast.success(`Return ${p.data.return_no} created — pending approval`);
      onOpenChange(false); onDone?.();
      setForm({ ...form, remarks: "", lines: [{ sku_id: "", batch_id: "", qty: 1, price: 0 }] });
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  const updateLine = (idx, patch) => {
    const lines = [...form.lines];
    lines[idx] = { ...lines[idx], ...patch };
    setForm({ ...form, lines });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="return-open">
          <Plus size={15} className="mr-2" /> New return
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>New Return Request</DialogTitle>
          <DialogDescription>Triggers approval chain → inventory adjustment → auto credit note posting.</DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-3 gap-3">
          <div><Label>Scope</Label>
            <Select value={form.scope} onValueChange={(v) => setForm({ ...form, scope: v, party_type: v })}>
              <SelectTrigger data-testid="ret-scope"><SelectValue /></SelectTrigger>
              <SelectContent>{RETURN_SCOPES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div><Label>Reason</Label>
            <Select value={form.reason} onValueChange={(v) => setForm({ ...form, reason: v })}>
              <SelectTrigger data-testid="ret-reason"><SelectValue /></SelectTrigger>
              <SelectContent>{RETURN_REASONS.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div><Label>Party</Label>
            <Select value={form.party_id} onValueChange={(v) => setForm({ ...form, party_id: v })}>
              <SelectTrigger data-testid="ret-party"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>{parties.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="col-span-3"><Label>Original invoice (optional)</Label>
            <Select value={form.invoice_id || "none"} onValueChange={(v) => setForm({ ...form, invoice_id: v === "none" ? "" : v })}>
              <SelectTrigger data-testid="ret-invoice"><SelectValue placeholder="Select invoice" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">— none —</SelectItem>
                {invoices.map((i) => <SelectItem key={i.id} value={i.id}>{i.invoice_no} — {money(i.total)}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-3">
            <Label>Return lines</Label>
            <div className="space-y-2 mt-1">
              {form.lines.map((ln, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-5">
                    <Select value={ln.sku_id} onValueChange={(v) => {
                      const sku = skus.find((s) => s.id === v);
                      updateLine(idx, { sku_id: v, price: sku?.mrp || sku?.trade_price || 0 });
                    }}>
                      <SelectTrigger data-testid={`ret-sku-${idx}`}><SelectValue placeholder="SKU" /></SelectTrigger>
                      <SelectContent className="max-h-64">
                        {skus.map((s) => <SelectItem key={s.id} value={s.id}>{s.sku_code} — {s.product_name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-3"><Input placeholder="Batch id (optional)" value={ln.batch_id || ""} onChange={(e) => updateLine(idx, { batch_id: e.target.value })} data-testid={`ret-batch-${idx}`} /></div>
                  <div className="col-span-2"><Input type="number" value={ln.qty} onChange={(e) => updateLine(idx, { qty: parseInt(e.target.value, 10) || 0 })} data-testid={`ret-qty-${idx}`} /></div>
                  <div className="col-span-2"><Input type="number" value={ln.price} onChange={(e) => updateLine(idx, { price: parseFloat(e.target.value) || 0 })} data-testid={`ret-price-${idx}`} /></div>
                </div>
              ))}
              <Button size="sm" variant="outline" onClick={() => setForm({ ...form, lines: [...form.lines, { sku_id: "", batch_id: "", qty: 1, price: 0 }] })}>+ Add line</Button>
            </div>
          </div>
          <div className="col-span-3">
            <Label>Remarks</Label>
            <Textarea value={form.remarks} onChange={(e) => setForm({ ...form, remarks: e.target.value })} data-testid="ret-remarks" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="bg-gold hover:bg-gold-dark text-white" disabled={busy || !form.party_id || !form.lines[0]?.sku_id} onClick={submit} data-testid="ret-submit">
            {busy ? <Loader2 size={14} className="animate-spin" /> : "Submit return"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==========================================================
// DAMAGE
// ==========================================================
export function DamagePage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    setLoading(true);
    api.get("/reverse/damage").then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  }, [reload]);
  const totalValue = rows.reduce((s, r) => s + (r.estimated_value || 0), 0);
  const byScope = rows.reduce((a, r) => { a[r.scope] = (a[r.scope] || 0) + 1; return a; }, {});
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Reverse Logistics", "Damage"]}
        title="Damage Management"
        subtitle="Track damaged inventory by scope — warehouse, transport, distributor, retailer, customer"
        actions={<NewDamageDialog open={open} onOpenChange={setOpen} onDone={() => setReload((v) => v + 1)} />}
      />
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <KpiCard label="Total incidents" value={rows.length} delta={money(totalValue)} />
        {DAMAGE_SCOPES.map((s) => <KpiCard key={s} label={s} value={byScope[s] || 0} delta="cases" />)}
      </div>
      <DataTable
        data={rows} loading={loading} testId="damage-table" pageSize={15}
        columns={[
          { key: "damage_no", label: "Damage" },
          { key: "scope", label: "Scope", type: "chip" },
          { key: "sku_code", label: "SKU" },
          { key: "product_name", label: "Product" },
          { key: "batch_id", label: "Batch" },
          { key: "qty", label: "Qty", align: "right" },
          { key: "estimated_value", label: "Value", type: "currency", align: "right" },
          { key: "reason", label: "Reason" },
          { key: "created_at", label: "Recorded", type: "date" },
        ]}
      />
    </div>
  );
}

function NewDamageDialog({ open, onOpenChange, onDone }) {
  const [form, setForm] = useState({ scope: "warehouse", sku_id: "", batch_id: "", partner_id: "", qty: 1, reason: "", estimated_value: 0 });
  const [skus, setSkus] = useState([]);
  const [batches, setBatches] = useState([]);
  const [partners, setPartners] = useState([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!open) return;
    api.get("/collections/skus?limit=500").then((r) => setSkus(r.data.data || []));
    api.get("/collections/batches?limit=500").then((r) => setBatches(r.data.data || []));
  }, [open]);
  useEffect(() => {
    if (!["distributor", "retailer", "customer"].includes(form.scope)) { setPartners([]); return; }
    const coll = form.scope === "distributor" ? "distributors" : form.scope === "retailer" ? "retailers" : "customers";
    api.get(`/collections/${coll}?limit=300`).then((r) => setPartners(r.data.data || []));
  }, [form.scope]);
  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/reverse/damage", form);
      toast.success("Damage recorded — inventory moved to damaged bucket");
      onOpenChange(false); onDone?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  const skuBatches = batches.filter((b) => b.sku_id === form.sku_id);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="damage-open">
          <Plus size={15} className="mr-2" /> Record damage
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader><DialogTitle>Record Damage Incident</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Scope</Label>
            <Select value={form.scope} onValueChange={(v) => setForm({ ...form, scope: v })}>
              <SelectTrigger data-testid="dmg-scope"><SelectValue /></SelectTrigger>
              <SelectContent>{DAMAGE_SCOPES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          {["distributor", "retailer", "customer"].includes(form.scope) && (
            <div><Label>Partner</Label>
              <Select value={form.partner_id} onValueChange={(v) => setForm({ ...form, partner_id: v })}>
                <SelectTrigger data-testid="dmg-partner"><SelectValue placeholder="Select" /></SelectTrigger>
                <SelectContent>{partners.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          )}
          <div><Label>SKU</Label>
            <Select value={form.sku_id} onValueChange={(v) => setForm({ ...form, sku_id: v, batch_id: "" })}>
              <SelectTrigger data-testid="dmg-sku"><SelectValue placeholder="SKU" /></SelectTrigger>
              <SelectContent className="max-h-64">{skus.map((s) => <SelectItem key={s.id} value={s.id}>{s.sku_code}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div><Label>Batch</Label>
            <Select value={form.batch_id} onValueChange={(v) => setForm({ ...form, batch_id: v })}>
              <SelectTrigger data-testid="dmg-batch"><SelectValue placeholder="Batch" /></SelectTrigger>
              <SelectContent className="max-h-64">{skuBatches.map((b) => <SelectItem key={b.id} value={b.id}>{b.batch_no}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div><Label>Qty damaged</Label><Input type="number" value={form.qty} onChange={(e) => setForm({ ...form, qty: parseInt(e.target.value, 10) || 0 })} data-testid="dmg-qty" /></div>
          <div><Label>Estimated value</Label><Input type="number" value={form.estimated_value} onChange={(e) => setForm({ ...form, estimated_value: parseFloat(e.target.value) || 0 })} data-testid="dmg-value" /></div>
          <div className="col-span-2"><Label>Reason</Label><Textarea value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} data-testid="dmg-reason" /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="bg-gold hover:bg-gold-dark text-white" onClick={submit} disabled={busy || !form.sku_id || !form.batch_id || form.qty <= 0} data-testid="dmg-submit">
            {busy ? <Loader2 size={14} className="animate-spin" /> : "Record damage"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==========================================================
// CLAIMS
// ==========================================================
export function ClaimsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    setLoading(true);
    api.get("/reverse/claims").then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  }, [reload]);
  const settle = async (r) => {
    try {
      await api.post(`/reverse/claims/${r.id}/settle`, { settlement_amount: r.amount });
      toast.success("Claim settled — cash journal posted");
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const byType = rows.reduce((a, r) => { a[r.type] = (a[r.type] || 0) + 1; return a; }, {});
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Reverse Logistics", "Claims"]}
        title="Claim Management"
        subtitle="Transport, Insurance, Manufacturer, Retailer and Distributor claims — with approval and settlement"
        actions={<NewClaimDialog open={open} onOpenChange={setOpen} onDone={() => setReload((v) => v + 1)} />}
      />
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        {CLAIM_TYPES.map((t) => <KpiCard key={t} label={t} value={byType[t] || 0} delta="claims" />)}
      </div>
      <DataTable
        data={rows} loading={loading} testId="claims-table" pageSize={15}
        columns={[
          { key: "claim_no", label: "Claim" },
          { key: "type", label: "Type", type: "chip" },
          { key: "party_name", label: "Party" },
          { key: "reason", label: "Reason" },
          { key: "amount", label: "Amount", type: "currency", align: "right" },
          { key: "settlement_amount", label: "Settled", type: "currency", align: "right" },
          { key: "status", label: "Status", type: "status" },
          { key: "created_at", label: "Filed", type: "date" },
          { key: "actions", label: "", render: (r) => (
            r.status === "approved" ? (
              <Button size="sm" className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => settle(r)} data-testid={`clm-settle-${r.id}`}>
                <HandCoins size={13} className="mr-1" /> Settle
              </Button>
            ) : <span className="text-xs text-ink-muted">—</span>
          )},
        ]}
      />
    </div>
  );
}

function NewClaimDialog({ open, onOpenChange, onDone }) {
  const [form, setForm] = useState({
    type: "transport", party_id: "", party_type: "distributor", party_name: "",
    invoice_id: "", amount: 0, reason: "",
  });
  const [parties, setParties] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!open) return;
    const coll = form.party_type === "distributor" ? "distributors" : form.party_type === "retailer" ? "retailers" : "customers";
    api.get(`/collections/${coll}?limit=300`).then((r) => setParties(r.data.data || []));
    api.get("/collections/invoices?limit=300").then((r) => setInvoices(r.data.data || []));
  }, [open, form.party_type]);
  const submit = async () => {
    setBusy(true);
    try {
      const p = parties.find((x) => x.id === form.party_id);
      await api.post("/reverse/claims", { ...form, party_name: p?.name || "" });
      toast.success("Claim submitted — approval chain triggered");
      onOpenChange(false); onDone?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="claim-open">
          <Plus size={15} className="mr-2" /> New claim
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader><DialogTitle>File Claim</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Type</Label>
            <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v, party_type: v === "transport" || v === "insurance" || v === "manufacturer" ? "distributor" : v })}>
              <SelectTrigger data-testid="clm-type"><SelectValue /></SelectTrigger>
              <SelectContent>{CLAIM_TYPES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div><Label>Against party</Label>
            <Select value={form.party_type} onValueChange={(v) => setForm({ ...form, party_type: v, party_id: "" })}>
              <SelectTrigger data-testid="clm-party-type"><SelectValue /></SelectTrigger>
              <SelectContent>{["distributor", "retailer", "customer"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="col-span-2"><Label>Party</Label>
            <Select value={form.party_id} onValueChange={(v) => setForm({ ...form, party_id: v })}>
              <SelectTrigger data-testid="clm-party"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>{parties.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="col-span-2"><Label>Invoice (optional)</Label>
            <Select value={form.invoice_id || "none"} onValueChange={(v) => setForm({ ...form, invoice_id: v === "none" ? "" : v })}>
              <SelectTrigger data-testid="clm-invoice"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">— none —</SelectItem>
                {invoices.slice(0, 100).map((i) => <SelectItem key={i.id} value={i.id}>{i.invoice_no}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div><Label>Amount</Label><Input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })} data-testid="clm-amount" /></div>
          <div className="col-span-2"><Label>Reason / narrative</Label><Textarea value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} data-testid="clm-reason" /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="bg-gold hover:bg-gold-dark text-white" onClick={submit} disabled={busy || !form.party_id || !(form.amount > 0)} data-testid="clm-submit">
            {busy ? <Loader2 size={14} className="animate-spin" /> : "Submit claim"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==========================================================
// CREDIT NOTES
// ==========================================================
export function CreditNotesPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    setLoading(true);
    api.get("/reverse/credit-notes").then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  }, [reload]);
  const total = rows.reduce((s, r) => s + (r.total || 0), 0);
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Reverse Logistics", "Credit Notes"]}
        title="Credit Note Engine"
        subtitle="Auto issued on return approval; also manual — reduces AR, updates outstanding, tax adjusted"
        actions={<NewCreditNoteDialog open={open} onOpenChange={setOpen} onDone={() => setReload((v) => v + 1)} />}
      />
      <div className="grid grid-cols-3 gap-3 mb-4">
        <KpiCard label="Total notes" value={rows.length} delta="issued" />
        <KpiCard label="Total value" value={money(total)} delta="AR reduced" />
        <KpiCard label="Auto CN (returns)" value={rows.filter((r) => r.reason === "return_approved").length} delta="from returns" />
      </div>
      <DataTable
        data={rows} loading={loading} testId="credit-notes-table" pageSize={15}
        columns={[
          { key: "cn_no", label: "CN No" },
          { key: "reason", label: "Reason", type: "chip", render: (r) => (CN_REASONS.find((x) => x.v === r.reason)?.l || r.reason) },
          { key: "party_name", label: "Party" },
          { key: "invoice_id", label: "Invoice" },
          { key: "subtotal", label: "Subtotal", type: "currency", align: "right" },
          { key: "tax", label: "Tax", type: "currency", align: "right" },
          { key: "total", label: "Total", type: "currency", align: "right" },
          { key: "status", label: "Status", type: "status" },
          { key: "created_at", label: "Issued", type: "date" },
        ]}
      />
    </div>
  );
}

function NewCreditNoteDialog({ open, onOpenChange, onDone }) {
  const [form, setForm] = useState({
    reason: "over_billing", party_id: "", party_type: "distributor",
    invoice_id: "", subtotal: 0, tax: 0, total: 0, remarks: "",
  });
  const [parties, setParties] = useState([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!open) return;
    const coll = form.party_type === "distributor" ? "distributors" : form.party_type === "retailer" ? "retailers" : "customers";
    api.get(`/collections/${coll}?limit=300`).then((r) => setParties(r.data.data || []));
  }, [open, form.party_type]);
  const submit = async () => {
    setBusy(true);
    try {
      const subtotal = Number(form.subtotal) || 0;
      const tax = form.tax ? Number(form.tax) : Math.round(subtotal * 0.18 * 100) / 100;
      const total = form.total ? Number(form.total) : subtotal + tax;
      await api.post("/reverse/credit-notes", { ...form, subtotal, tax, total, lines: [] });
      toast.success("Credit note posted — outstanding updated");
      onOpenChange(false); onDone?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="cn-open">
          <Plus size={15} className="mr-2" /> Manual credit note
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle>Issue Credit Note</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Reason</Label>
            <Select value={form.reason} onValueChange={(v) => setForm({ ...form, reason: v })}>
              <SelectTrigger data-testid="cn-reason"><SelectValue /></SelectTrigger>
              <SelectContent>{CN_REASONS.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div><Label>Party type</Label>
            <Select value={form.party_type} onValueChange={(v) => setForm({ ...form, party_type: v, party_id: "" })}>
              <SelectTrigger data-testid="cn-party-type"><SelectValue /></SelectTrigger>
              <SelectContent>{["distributor", "retailer", "customer"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="col-span-2"><Label>Party</Label>
            <Select value={form.party_id} onValueChange={(v) => setForm({ ...form, party_id: v })}>
              <SelectTrigger data-testid="cn-party"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>{parties.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div><Label>Subtotal</Label><Input type="number" value={form.subtotal} onChange={(e) => setForm({ ...form, subtotal: e.target.value })} data-testid="cn-subtotal" /></div>
          <div><Label>Tax (auto if blank)</Label><Input type="number" value={form.tax} onChange={(e) => setForm({ ...form, tax: e.target.value })} data-testid="cn-tax" /></div>
          <div className="col-span-2"><Label>Remarks</Label><Textarea value={form.remarks} onChange={(e) => setForm({ ...form, remarks: e.target.value })} data-testid="cn-remarks" /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="bg-gold hover:bg-gold-dark text-white" onClick={submit} disabled={busy || !form.party_id || !(Number(form.subtotal) > 0)} data-testid="cn-submit">
            {busy ? <Loader2 size={14} className="animate-spin" /> : "Issue CN"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==========================================================
// DEBIT NOTES
// ==========================================================
export function DebitNotesPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    setLoading(true);
    api.get("/reverse/debit-notes").then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  }, [reload]);
  const total = rows.reduce((s, r) => s + (r.total || 0), 0);
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Reverse Logistics", "Debit Notes"]}
        title="Debit Note Engine"
        subtitle="Additional charges, penalty, transport, extra supply, short payment — increases AR, updates outstanding"
        actions={<NewDebitNoteDialog open={open} onOpenChange={setOpen} onDone={() => setReload((v) => v + 1)} />}
      />
      <div className="grid grid-cols-3 gap-3 mb-4">
        <KpiCard label="Total notes" value={rows.length} delta="issued" />
        <KpiCard label="Total charge" value={money(total)} delta="AR added" />
        <KpiCard label="Reasons" value={new Set(rows.map((r) => r.reason)).size} delta="unique" />
      </div>
      <DataTable
        data={rows} loading={loading} testId="debit-notes-table" pageSize={15}
        columns={[
          { key: "dn_no", label: "DN No" },
          { key: "reason", label: "Reason", type: "chip", render: (r) => (DN_REASONS.find((x) => x.v === r.reason)?.l || r.reason) },
          { key: "party_name", label: "Party" },
          { key: "invoice_id", label: "Invoice" },
          { key: "amount", label: "Amount", type: "currency", align: "right" },
          { key: "tax", label: "Tax", type: "currency", align: "right" },
          { key: "total", label: "Total", type: "currency", align: "right" },
          { key: "status", label: "Status", type: "status" },
          { key: "created_at", label: "Issued", type: "date" },
        ]}
      />
    </div>
  );
}

function NewDebitNoteDialog({ open, onOpenChange, onDone }) {
  const [form, setForm] = useState({
    reason: "additional_charges", party_id: "", party_type: "distributor",
    invoice_id: "", amount: 0, remarks: "",
  });
  const [parties, setParties] = useState([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!open) return;
    const coll = form.party_type === "distributor" ? "distributors" : form.party_type === "retailer" ? "retailers" : "customers";
    api.get(`/collections/${coll}?limit=300`).then((r) => setParties(r.data.data || []));
  }, [open, form.party_type]);
  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/reverse/debit-notes", { ...form, amount: Number(form.amount) || 0 });
      toast.success("Debit note posted — outstanding updated");
      onOpenChange(false); onDone?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="dn-open">
          <Plus size={15} className="mr-2" /> New debit note
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle>Issue Debit Note</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div><Label>Reason</Label>
            <Select value={form.reason} onValueChange={(v) => setForm({ ...form, reason: v })}>
              <SelectTrigger data-testid="dn-reason"><SelectValue /></SelectTrigger>
              <SelectContent>{DN_REASONS.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div><Label>Party type</Label>
            <Select value={form.party_type} onValueChange={(v) => setForm({ ...form, party_type: v, party_id: "" })}>
              <SelectTrigger data-testid="dn-party-type"><SelectValue /></SelectTrigger>
              <SelectContent>{["distributor", "retailer", "customer"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="col-span-2"><Label>Party</Label>
            <Select value={form.party_id} onValueChange={(v) => setForm({ ...form, party_id: v })}>
              <SelectTrigger data-testid="dn-party"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>{parties.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="col-span-2"><Label>Amount (base)</Label><Input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} data-testid="dn-amount" /></div>
          <div className="col-span-2"><Label>Remarks</Label><Textarea value={form.remarks} onChange={(e) => setForm({ ...form, remarks: e.target.value })} data-testid="dn-remarks" /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="bg-gold hover:bg-gold-dark text-white" onClick={submit} disabled={busy || !form.party_id || !(Number(form.amount) > 0)} data-testid="dn-submit">
            {busy ? <Loader2 size={14} className="animate-spin" /> : "Issue DN"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==========================================================
// REPLACEMENTS
// ==========================================================
export function ReplacementsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    setLoading(true);
    api.get("/reverse/replacements").then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  }, [reload]);
  const counts = rows.reduce((a, r) => { a[r.status] = (a[r.status] || 0) + 1; return a; }, {});
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Reverse Logistics", "Replacements"]}
        title="Replacement Engine"
        subtitle="Approved returns → new dispatch → GIT → GRN — full traceability from return to received replacement"
        actions={<Button variant="outline" className="h-10 border-[#E5E7EB]" onClick={() => setReload((v) => v + 1)}><RefreshCw size={14} className="mr-2" /> Refresh</Button>}
      />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard label="Total" value={rows.length} delta="all replacements" />
        <KpiCard label="Pending" value={counts.pending || 0} delta="awaiting approval" />
        <KpiCard label="Completed" value={counts.completed || 0} delta="delivered" />
        <KpiCard label="Rejected" value={counts.rejected || 0} delta="closed" />
      </div>
      <DataTable
        data={rows} loading={loading} testId="replacements-table" pageSize={12}
        columns={[
          { key: "replacement_no", label: "Replacement" },
          { key: "return_id", label: "From Return" },
          { key: "scope", label: "Scope", type: "chip" },
          { key: "party_name", label: "Party" },
          { key: "total", label: "Value", type: "currency", align: "right" },
          { key: "status", label: "Status", type: "status" },
          { key: "dispatch_id", label: "Dispatch", render: (r) => r.dispatch_id ? <span className="text-xs text-emerald-700">{r.dispatch_id}</span> : <span className="text-ink-muted text-xs">—</span> },
          { key: "grn_id", label: "GRN", render: (r) => r.grn_id ? <span className="text-xs text-emerald-700">{r.grn_id}</span> : <span className="text-ink-muted text-xs">—</span> },
          { key: "created_at", label: "Created", type: "date" },
        ]}
      />
    </div>
  );
}

// ==========================================================
// EXPIRY
// ==========================================================
export function ExpiryPage() {
  const [data, setData] = useState({ near_expiry: [], expired: [], blocked: [], destroyed: [], return_to_company: [], count: {} });
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [days, setDays] = useState(30);
  useEffect(() => {
    setLoading(true);
    api.get(`/reverse/expiry?days=${days}`).then((r) => setData(r.data || {})).finally(() => setLoading(false));
  }, [reload, days]);

  const doAction = async (batch_id, action) => {
    try {
      await api.post(`/reverse/expiry/${batch_id}/action`, { action, reason: `${action} via ExpiryPage` });
      toast.success(`Batch ${action} — inventory moved to expired`);
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  const cols = [
    { key: "batch_no", label: "Batch" },
    { key: "sku_code", label: "SKU" },
    { key: "product_name", label: "Product" },
    { key: "manufactured_on", label: "Mfd", type: "date" },
    { key: "expires_on", label: "Expires", type: "date" },
    { key: "stock_qty", label: "Stock", align: "right" },
    { key: "actions", label: "", render: (r) => (
      <div className="flex gap-1">
        <Button size="sm" variant="outline" className="h-8" onClick={() => doAction(r.id, "block")}>Block</Button>
        <Button size="sm" variant="outline" className="h-8 border-rose-200 text-rose-700" onClick={() => doAction(r.id, "destroy")}>Destroy</Button>
        <Button size="sm" variant="outline" className="h-8 border-gold text-gold-dark" onClick={() => doAction(r.id, "return_to_company")}>Return to Co.</Button>
      </div>
    ) },
  ];

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Reverse Logistics", "Expiry"]}
        title="Expiry Management"
        subtitle="Near-expiry alerts, expired stock, block/destroy/return-to-company workflows"
        actions={
          <div className="flex items-center gap-2">
            <Label className="text-xs text-ink-muted">Window</Label>
            <Select value={String(days)} onValueChange={(v) => setDays(parseInt(v, 10))}>
              <SelectTrigger className="w-28 h-10 border-[#E5E7EB]" data-testid="exp-days"><SelectValue /></SelectTrigger>
              <SelectContent>{[7, 15, 30, 60, 90, 180].map((n) => <SelectItem key={n} value={String(n)}>{n} days</SelectItem>)}</SelectContent>
            </Select>
            <Button variant="outline" className="h-10 border-[#E5E7EB]" onClick={() => setReload((v) => v + 1)}><RefreshCw size={14} className="mr-2" /> Refresh</Button>
          </div>
        }
      />
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <KpiCard label="Near expiry" value={data.count?.near || 0} delta={`≤ ${days} days`} />
        <KpiCard label="Expired" value={data.count?.expired || 0} delta="attention" />
        <KpiCard label="Blocked" value={data.count?.blocked || 0} delta="quarantine" />
        <KpiCard label="Destroyed" value={data.count?.destroyed || 0} delta="disposed" />
        <KpiCard label="Returned to Co." value={data.count?.return_to_company || 0} delta="RTV" />
      </div>
      <Tabs defaultValue="near">
        <TabsList className="bg-canvas border border-[#E5E7EB]">
          <TabsTrigger value="near" data-testid="exp-tab-near">Near expiry</TabsTrigger>
          <TabsTrigger value="expired" data-testid="exp-tab-expired">Expired</TabsTrigger>
          <TabsTrigger value="blocked" data-testid="exp-tab-blocked">Blocked / Destroyed / RTV</TabsTrigger>
        </TabsList>
        <TabsContent value="near" className="mt-4">
          <DataTable data={data.near_expiry || []} loading={loading} columns={cols} testId="near-expiry-table" pageSize={15} />
        </TabsContent>
        <TabsContent value="expired" className="mt-4">
          <DataTable data={data.expired || []} loading={loading} columns={cols} testId="expired-table" pageSize={15} />
        </TabsContent>
        <TabsContent value="blocked" className="mt-4">
          <DataTable data={[...(data.blocked || []), ...(data.destroyed || []), ...(data.return_to_company || [])]}
            loading={loading} testId="expiry-records-table" pageSize={15}
            columns={[
              { key: "batch_no", label: "Batch" },
              { key: "sku_code", label: "SKU" },
              { key: "action", label: "Action", type: "chip" },
              { key: "qty_affected", label: "Qty", align: "right" },
              { key: "reason", label: "Reason" },
              { key: "created_by", label: "By" },
              { key: "created_at", label: "When", type: "date" },
            ]}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ==========================================================
// APPROVAL ENGINE
// ==========================================================
export function ApprovalEnginePage() {
  const [tab, setTab] = useState("requests");
  const [requests, setRequests] = useState([]);
  const [matrix, setMatrix] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get("/reverse/approval-requests"),
      api.get("/reverse/approval-matrix"),
    ]).then(([a, b]) => {
      setRequests(a.data.data || []);
      setMatrix(b.data.data || []);
    }).finally(() => setLoading(false));
  }, [reload]);

  const approve = async (id) => {
    try {
      const r = await api.post(`/reverse/approval-requests/${id}/approve`, { comment: "Approved" });
      toast.success(r.data.executed ? "Approved & executed downstream" : "Step approved");
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const reject = async (id) => {
    try {
      await api.post(`/reverse/approval-requests/${id}/reject`, { reason: "Rejected" });
      toast.success("Rejected — entity marked");
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  const counts = requests.reduce((a, r) => { a[r.status] = (a[r.status] || 0) + 1; return a; }, {});

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Reverse Logistics", "Approval Engine"]}
        title="Enterprise Approval Engine"
        subtitle="Matrix-driven multi-level approvals — every action fully audit-logged"
        actions={<Button variant="outline" className="h-10 border-[#E5E7EB]" onClick={() => setReload((v) => v + 1)}><RefreshCw size={14} className="mr-2" /> Refresh</Button>}
      />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard label="Pending" value={counts.pending || 0} delta="awaiting action" />
        <KpiCard label="Approved" value={counts.approved || 0} delta="executed" />
        <KpiCard label="Rejected" value={counts.rejected || 0} delta="closed" />
        <KpiCard label="Matrix rules" value={matrix.length} delta="configured" />
      </div>
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-canvas border border-[#E5E7EB]">
          <TabsTrigger value="requests" data-testid="ap-tab-req">Approval Requests</TabsTrigger>
          <TabsTrigger value="matrix" data-testid="ap-tab-mat">Approval Matrix</TabsTrigger>
        </TabsList>
        <TabsContent value="requests" className="mt-4">
          <DataTable
            data={requests} loading={loading} testId="approval-requests-table" pageSize={15}
            columns={[
              { key: "id", label: "Req" },
              { key: "entity_type", label: "Entity", type: "chip" },
              { key: "entity_id", label: "Entity ID" },
              { key: "amount", label: "Amount", type: "currency", align: "right" },
              { key: "current_level", label: "Level", align: "right" },
              { key: "steps", label: "Chain", render: (r) => (
                <div className="flex gap-1 items-center">
                  {(r.steps || []).map((s, i) => (
                    <span key={i} title={s.role + (s.actor ? ` — ${s.actor}` : "")}
                      className={`text-[10px] px-2 py-0.5 rounded ${
                        s.status === "approved" ? "bg-emerald-100 text-emerald-700" :
                        s.status === "rejected" ? "bg-rose-100 text-rose-700" :
                        "bg-slate-100 text-slate-600"
                      }`}>{s.role.split("_")[0]}</span>
                  ))}
                </div>
              ) },
              { key: "status", label: "Status", type: "status" },
              { key: "summary", label: "Summary" },
              { key: "requested_at", label: "Requested", type: "date" },
              { key: "actions", label: "", render: (r) => (
                r.status === "pending" ? (
                  <div className="flex gap-1">
                    <Button size="sm" className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => approve(r.id)} data-testid={`ap-approve-${r.id}`}>
                      <CheckCircle2 size={13} className="mr-1" /> Approve
                    </Button>
                    <Button size="sm" variant="outline" className="h-8 border-rose-200 text-rose-700" onClick={() => reject(r.id)} data-testid={`ap-reject-${r.id}`}>
                      <XCircle size={13} className="mr-1" /> Reject
                    </Button>
                  </div>
                ) : <span className="text-xs text-ink-muted">—</span>
              )},
            ]}
          />
        </TabsContent>
        <TabsContent value="matrix" className="mt-4">
          <DataTable
            data={matrix} loading={loading} testId="approval-matrix-table" pageSize={20}
            columns={[
              { key: "entity_type", label: "Entity", type: "chip" },
              { key: "amount_min", label: "Amount ≥", type: "currency", align: "right" },
              { key: "amount_max", label: "Amount <", type: "currency", align: "right", render: (r) => r.amount_max >= 999999999 ? "∞" : money(r.amount_max) },
              { key: "levels", label: "Approval chain", render: (r) => (
                <div className="flex gap-1 flex-wrap">
                  {(r.levels || []).map((l, i) => (
                    <span key={i} className="text-[10px] rounded bg-gold-tint text-ink px-2 py-0.5">L{l.level}: {l.role}</span>
                  ))}
                </div>
              ) },
            ]}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ==========================================================
// EXCEPTIONS
// ==========================================================
export function ExceptionsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setLoading(true);
    api.get("/reverse/exceptions").then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  }, [reload]);
  const scan = async () => {
    setBusy(true);
    try {
      const r = await api.post("/reverse/exceptions/scan");
      toast.success(`Scan complete — ${r.data.found} new exception${r.data.found === 1 ? "" : "s"}`);
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  const resolve = async (id) => {
    try { await api.post(`/reverse/exceptions/${id}/resolve`, { resolution: "Resolved via UI" });
      toast.success("Exception resolved"); setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const dismiss = async (id) => {
    try { await api.post(`/reverse/exceptions/${id}/resolve`, { status: "dismissed", resolution: "Dismissed" });
      toast.success("Dismissed"); setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const counts = rows.reduce((a, r) => { a[r.status] = (a[r.status] || 0) + 1; a[r.severity] = (a[r.severity] || 0) + 1; return a; }, {});
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Reverse Logistics", "Exceptions"]}
        title="Exception Engine"
        subtitle="Automatic anomaly detection — 8 checks: negative inv, duplicate invoice/payment/claim, credit exceeded, expired dispatch, variance, price mismatch"
        actions={
          <Button className="bg-gold hover:bg-gold-dark text-white h-10" onClick={scan} disabled={busy} data-testid="exc-scan">
            {busy ? <Loader2 size={14} className="animate-spin mr-2" /> : <ScanLine size={14} className="mr-2" />} Run scan
          </Button>
        }
      />
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <KpiCard label="Total" value={rows.length} delta="all-time" />
        <KpiCard label="Open" value={counts.open || 0} delta="require action" />
        <KpiCard label="Resolved" value={counts.resolved || 0} delta="closed" />
        <KpiCard label="High severity" value={counts.high || 0} delta="critical" />
        <KpiCard label="Medium" value={counts.medium || 0} delta="review" />
      </div>
      <DataTable
        data={rows} loading={loading} testId="exceptions-table" pageSize={15}
        columns={[
          { key: "kind", label: "Kind", type: "chip" },
          { key: "severity", label: "Severity", render: (r) => (
            <span className={`inline-flex px-2 py-0.5 rounded text-[11px] font-medium ${
              r.severity === "high" ? "bg-rose-100 text-rose-700" :
              r.severity === "medium" ? "bg-amber-100 text-amber-700" :
              "bg-slate-100 text-slate-600"}`}>{r.severity}</span>
          )},
          { key: "entity_type", label: "Entity" },
          { key: "entity_id", label: "Entity ID" },
          { key: "description", label: "Description" },
          { key: "status", label: "Status", type: "status" },
          { key: "detected_at", label: "Detected", type: "date" },
          { key: "actions", label: "", render: (r) => (
            r.status === "open" ? (
              <div className="flex gap-1">
                <Button size="sm" className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => resolve(r.id)} data-testid={`exc-resolve-${r.id}`}>Resolve</Button>
                <Button size="sm" variant="outline" className="h-8" onClick={() => dismiss(r.id)} data-testid={`exc-dismiss-${r.id}`}>Dismiss</Button>
              </div>
            ) : <span className="text-xs text-ink-muted">—</span>
          )},
        ]}
      />
    </div>
  );
}

// ==========================================================
// REPORTS HUB
// ==========================================================
const REPORT_MENU = [
  { key: "returns", label: "Return Report", icon: Undo2 },
  { key: "damage", label: "Damage Report", icon: ShieldAlert },
  { key: "claims", label: "Claim Report", icon: HandCoins },
  { key: "credit_notes", label: "Credit Note Report", icon: FileMinus },
  { key: "debit_notes", label: "Debit Note Report", icon: FilePlus },
  { key: "expiry", label: "Expiry Report", icon: Timer },
  { key: "replacements", label: "Replacement Report", icon: Repeat },
  { key: "approvals", label: "Approval Report", icon: GitBranchPlus },
  { key: "audit", label: "Audit Report", icon: FileBarChart2 },
];

export function ReportsHubPage() {
  const [active, setActive] = useState("returns");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/reverse/reports/${active}`).then((r) => setReport(r.data)).finally(() => setLoading(false));
  }, [active]);

  const rows = report?.rows || [];
  const summary = report ? Object.entries(report).filter(([k]) => !["rows", "report"].includes(k)) : [];

  const exportCsv = () => {
    if (!rows.length) return;
    const keys = Object.keys(rows[0]).filter((k) => typeof rows[0][k] !== "object" || rows[0][k] === null);
    const csv = [keys.join(","), ...rows.map((r) => keys.map((k) => JSON.stringify(r[k] ?? "")).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `${active}-report.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Reverse Logistics", "Reports"]}
        title="Reports Hub"
        subtitle="9 enterprise reports — reverse logistics, financials and audit"
        actions={<Button variant="outline" className="h-10 border-[#E5E7EB]" onClick={exportCsv} disabled={!rows.length}><FileBarChart2 size={14} className="mr-2" /> Export CSV</Button>}
      />
      <div className="grid grid-cols-3 lg:grid-cols-9 gap-2 mb-5">
        {REPORT_MENU.map((r) => {
          const Icon = r.icon;
          return (
            <button key={r.key} onClick={() => setActive(r.key)}
              className={`flex flex-col items-center gap-1 rounded-xl border p-3 text-xs font-medium transition ${
                active === r.key ? "border-gold bg-gold-tint/70 text-ink" : "border-[#E5E7EB] bg-white hover:bg-canvas text-ink-muted"}`}
              data-testid={`report-${r.key}`}>
              <Icon size={20} strokeWidth={1.6} className={active === r.key ? "text-gold-dark" : ""} />
              <span className="text-center leading-tight">{r.label}</span>
            </button>
          );
        })}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-3 mb-4">
        {summary.map(([k, v]) => (
          <div key={k} className="bg-white border border-[#E5E7EB] rounded-xl p-3">
            <div className="text-[10px] uppercase tracking-widest text-ink-muted font-semibold mb-1">{k.replace(/_/g, " ")}</div>
            {typeof v === "object" && v ? (
              <div className="flex flex-wrap gap-1">
                {Object.entries(v).map(([k2, v2]) => (
                  <span key={k2} className="text-[11px] rounded-md bg-gold-tint text-ink px-2 py-0.5">{k2}: {String(v2)}</span>
                ))}
              </div>
            ) : (
              <div className="text-lg font-semibold text-ink tabular-nums">{typeof v === "number" ? v.toLocaleString() : String(v)}</div>
            )}
          </div>
        ))}
      </div>
      <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-ink-muted"><Loader2 size={16} className="animate-spin inline mr-2" /> Loading report...</div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-ink-muted">No rows for this report.</div>
        ) : (
          <div className="overflow-x-auto max-h-[520px]">
            <table className="min-w-full text-sm">
              <thead className="bg-canvas sticky top-0">
                <tr>{Object.keys(rows[0]).filter((k) => typeof rows[0][k] !== "object" || rows[0][k] === null).map((k) => (
                  <th key={k} className="text-left px-3 py-2 text-[11px] uppercase tracking-widest text-ink-muted font-semibold border-b border-[#E5E7EB]">{k}</th>
                ))}</tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} className="border-b border-[#F1F5F9] hover:bg-canvas/50">
                    {Object.keys(rows[0]).filter((k) => typeof rows[0][k] !== "object" || rows[0][k] === null).map((k) => (
                      <td key={k} className="px-3 py-2 text-ink text-xs">
                        {k.includes("_at") || k === "expires_on" || k === "manufactured_on" ? shortDate(r[k]) :
                         typeof r[k] === "number" ? r[k].toLocaleString() :
                         String(r[k] ?? "—").slice(0, 60)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
