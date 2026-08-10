import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { dms, inr, niceDate } from "./api";
import { PageHeader, EmptyState } from "./OwnerPages";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Plus, FileText, Calendar, Package, ArrowRight, TrendingUp, Layers, Lock } from "lucide-react";

// ============================================================================
// Price Circular — list all batches
// ============================================================================
export function PriceCircularsPage() {
  const nav = useNavigate();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await dms.listPriceCirculars();
      setList(r.data || []);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  return (
    <div>
      <PageHeader
        title="Price Circular"
        subtitle="Monthly price batches — full pricing history is preserved"
        action={
          <Button onClick={() => nav("/dms/owner/price-circulars/new")} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white shadow-sm" data-testid="new-circular-btn">
            <Plus size={16} className="mr-1" /> New Price Circular
          </Button>
        }
      />

      {loading && <div className="p-8 text-center text-sm text-slate-500">Loading…</div>}

      {!loading && list.length === 0 && (
        <EmptyState icon={FileText} title="No price circulars yet" description="Create your first Price Circular to publish pricing." />
      )}

      <div className="grid gap-3">
        {list.map(c => (
          <Card key={c.id} className="p-5 border-[#c9a227]/15 shadow-sm hover:shadow-md transition cursor-pointer bg-gradient-to-r from-white via-white to-[#faf6e6]/40"
                onClick={() => nav(`/dms/owner/price-circulars/${c.id}`)}
                data-testid={`circular-${c.id}`}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 min-w-0">
                <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-[#faf0cf] to-[#c9a227]/25 flex items-center justify-center shrink-0">
                  <Layers size={20} className="text-[#a67c00]" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <div className="font-display font-bold text-slate-900 text-lg">{c.title}</div>
                    {c.is_active && <span className="text-[10px] uppercase tracking-wider font-bold bg-[#c9a227] text-white px-2 py-0.5 rounded">Active</span>}
                  </div>
                  <div className="text-sm text-slate-500 mt-1 flex items-center gap-3 flex-wrap">
                    <span className="inline-flex items-center gap-1"><Calendar size={12} /> Effective {c.effective_date}</span>
                    <span className="inline-flex items-center gap-1"><Package size={12} /> {c.lines_count} products</span>
                    <span className="inline-flex items-center gap-1 text-[#a67c00] font-semibold">{c.batch_label}</span>
                  </div>
                  {c.notes && <div className="text-xs text-slate-500 mt-1">{c.notes}</div>}
                </div>
              </div>
              <ArrowRight size={18} className="text-slate-400 mt-2 shrink-0" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Price Circular — view detail (all lines)
// ============================================================================
export function PriceCircularDetailPage() {
  const { id } = useParams();
  const [circular, setCircular] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const c = await dms.getPriceCircular(id);
        if (mounted) setCircular(c);
      } catch (e) {
        toast.error(e.response?.data?.detail || "Failed to load");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [id]);

  if (loading) return <div className="p-8 text-center text-sm text-slate-500">Loading…</div>;
  if (!circular) return <EmptyState icon={FileText} title="Not found" />;

  // group lines by category
  const grouped = {};
  (circular.lines || []).forEach(l => {
    const k = l.category_name || "Uncategorised";
    if (!grouped[k]) grouped[k] = [];
    grouped[k].push(l);
  });

  return (
    <div>
      <PageHeader
        title={circular.title}
        subtitle={`${circular.batch_label} · Effective ${circular.effective_date} · ${circular.lines?.length || 0} products`}
        back="/dms/owner/price-circulars"
      />

      {Object.entries(grouped).map(([cat, rows]) => (
        <Card key={cat} className="mb-4 overflow-hidden border-[#c9a227]/15 shadow-sm">
          <div className="px-4 py-2.5 bg-gradient-to-r from-[#faf6e6] to-white border-b border-[#c9a227]/20 flex items-center justify-between">
            <div className="font-display font-bold text-[#8a6600] text-sm uppercase tracking-wide">{cat}</div>
            <div className="text-xs text-slate-500">{rows.length}</div>
          </div>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50/50">
                  <TableHead>Material Description</TableHead>
                  <TableHead>Grade</TableHead>
                  <TableHead>Pack Size</TableHead>
                  <TableHead className="text-right">MRP</TableHead>
                  <TableHead className="text-right">DLP</TableHead>
                  <TableHead>Margin</TableHead>
                  <TableHead>Cash Coupon</TableHead>
                  <TableHead>FOC</TableHead>
                  <TableHead>Monthly Gift</TableHead>
                  <TableHead>Trade Disc.</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map(l => (
                  <TableRow key={l.id} className={l.is_active ? "" : "opacity-50"}>
                    <TableCell className="font-medium text-slate-900">{l.material_description}</TableCell>
                    <TableCell><span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">{l.grade_specs || "-"}</span></TableCell>
                    <TableCell>{l.pack_size}</TableCell>
                    <TableCell className="text-right text-slate-700">{inr(l.mrp)}</TableCell>
                    <TableCell className="text-right font-bold text-[#8a6600]">{inr(l.dlp)}</TableCell>
                    <TableCell><span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded font-semibold">{l.distributor_margin_pct}%</span></TableCell>
                    <TableCell className="text-xs text-slate-600">{l.cash_coupon || "—"}</TableCell>
                    <TableCell className="text-xs text-slate-600">{l.foc_benefits || "—"}</TableCell>
                    <TableCell className="text-xs text-slate-600">{l.monthly_gift || "—"}</TableCell>
                    <TableCell className="text-xs">{l.trade_discount ? <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-semibold">{l.trade_discount}</span> : "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      ))}
    </div>
  );
}

// ============================================================================
// New Price Circular — create with prefilled current prices for editing
// ============================================================================
export function NewPriceCircularPage() {
  const nav = useNavigate();
  const [products, setProducts] = useState([]);
  const [cats, setCats] = useState([]);
  const [circulars, setCirculars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [title, setTitle] = useState("");
  const [effDate, setEffDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [lineMap, setLineMap] = useState({});      // product_id -> { mrp, dlp, margin, cash_coupon, foc_benefits, monthly_gift, trade_discount, include }
  const [catFilter, setCatFilter] = useState("all");
  const [q, setQ] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [pRes, cRes, ccRes] = await Promise.all([dms.listProducts(), dms.listCategories(), dms.listPriceCirculars()]);
        const p = pRes.data || []; const c = cRes.data || []; const cs = ccRes.data || [];
        setProducts(p); setCats(c); setCirculars(cs);
        // For each product, prefill from active latest circular line if available
        const latest = cs[0];
        let latestLines = {};
        if (latest) {
          try {
            const det = await dms.getPriceCircular(latest.id);
            (det.lines || []).forEach(l => { latestLines[l.product_id] = l; });
          } catch { /* ignore */ }
        }
        const initMap = {};
        p.forEach(pr => {
          const ln = latestLines[pr.id] || {};
          initMap[pr.id] = {
            include: false,
            mrp: ln.mrp || "",
            dlp: ln.dlp ?? pr.unit_price ?? "",
            margin: ln.distributor_margin_pct || "",
            cash_coupon: ln.cash_coupon || "",
            foc_benefits: ln.foc_benefits || "",
            monthly_gift: ln.monthly_gift || "",
            trade_discount: ln.trade_discount || "",
            previous_dlp: ln.dlp ?? pr.unit_price,
          };
        });
        setLineMap(initMap);
      } finally { setLoading(false); }
    })();
  }, []);

  const filtered = products.filter(p => {
    if (catFilter !== "all" && p.category_id !== catFilter) return false;
    if (q) {
      const s = q.toLowerCase();
      const hay = `${p.material_description || p.name} ${p.grade_specs} ${p.pack_size}`.toLowerCase();
      if (!hay.includes(s)) return false;
    }
    return true;
  });

  const toggleInclude = (pid) => setLineMap(m => ({ ...m, [pid]: { ...m[pid], include: !m[pid].include } }));
  const patch = (pid, patchObj) => setLineMap(m => ({ ...m, [pid]: { ...m[pid], ...patchObj } }));
  const includeAllFiltered = () => {
    const next = { ...lineMap };
    filtered.forEach(p => { next[p.id] = { ...next[p.id], include: true }; });
    setLineMap(next);
  };
  const clearAll = () => {
    const next = { ...lineMap };
    Object.keys(next).forEach(k => { next[k] = { ...next[k], include: false }; });
    setLineMap(next);
  };

  const includedCount = Object.values(lineMap).filter(v => v.include).length;

  const save = async () => {
    if (!title.trim()) { toast.error("Title is required"); return; }
    if (!effDate) { toast.error("Effective date is required"); return; }
    const lines = [];
    for (const [pid, v] of Object.entries(lineMap)) {
      if (!v.include) continue;
      if (v.dlp === "" || v.dlp === null || isNaN(Number(v.dlp))) {
        toast.error("DLP is required for every included product");
        return;
      }
      lines.push({
        product_id: pid,
        mrp: v.mrp === "" ? 0 : Number(v.mrp),
        dlp: Number(v.dlp),
        distributor_margin_pct: v.margin === "" ? 0 : Number(v.margin),
        cash_coupon: v.cash_coupon,
        foc_benefits: v.foc_benefits,
        monthly_gift: v.monthly_gift,
        trade_discount: v.trade_discount,
      });
    }
    if (lines.length === 0) { toast.error("Include at least one product"); return; }
    setSaving(true);
    try {
      await dms.createPriceCircular({ title: title.trim(), effective_date: effDate, notes: notes.trim(), lines });
      toast.success(`New Price Circular created with ${lines.length} products`);
      nav("/dms/owner/price-circulars");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-sm text-slate-500">Loading…</div>;

  return (
    <div>
      <PageHeader
        title="New Price Circular"
        subtitle="Publish a new price batch — old prices are preserved as history"
        back="/dms/owner/price-circulars"
        action={
          <Button onClick={save} disabled={saving || includedCount === 0} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white shadow-sm" data-testid="save-circular-btn">
            {saving ? "Publishing…" : `Publish (${includedCount} products)`}
          </Button>
        }
      />

      <Card className="p-4 mb-4 border-[#c9a227]/25">
        <div className="grid md:grid-cols-3 gap-3">
          <div className="md:col-span-2"><Label>Circular Title *</Label><Input value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. GO OIL Price Circular — JUL'26" data-testid="circular-title-input" /></div>
          <div><Label>Effective Date *</Label><Input type="date" value={effDate} onChange={e => setEffDate(e.target.value)} data-testid="circular-date-input" /></div>
          <div className="md:col-span-3"><Label>Notes (optional)</Label><Textarea rows={2} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Any remarks for this circular" /></div>
        </div>
      </Card>

      <div className="flex flex-wrap gap-2 mb-3 items-center">
        <div className="flex-1 min-w-[200px]"><Input placeholder="Search product…" value={q} onChange={e => setQ(e.target.value)} /></div>
        <div className="w-56">
          <Select value={catFilter} onValueChange={setCatFilter}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {cats.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button variant="outline" onClick={includeAllFiltered} className="border-[#c9a227] text-[#8a6600] hover:bg-[#faf6e6]">Include all filtered</Button>
        <Button variant="outline" onClick={clearAll}>Clear all</Button>
      </div>

      <Card className="overflow-hidden border-[#c9a227]/15 shadow-sm">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50/50">
                <TableHead className="w-10">✓</TableHead>
                <TableHead>Material / Grade / Pack</TableHead>
                <TableHead className="text-right">MRP</TableHead>
                <TableHead className="text-right">DLP</TableHead>
                <TableHead>Margin %</TableHead>
                <TableHead>Cash Coupon</TableHead>
                <TableHead>FOC</TableHead>
                <TableHead>Monthly Gift</TableHead>
                <TableHead>Trade Disc.</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map(p => {
                const v = lineMap[p.id] || {};
                return (
                  <TableRow key={p.id} className={v.include ? "bg-[#faf6e6]/30" : ""}>
                    <TableCell>
                      <input type="checkbox" checked={!!v.include} onChange={() => toggleInclude(p.id)} className="w-4 h-4 accent-[#c9a227]" />
                    </TableCell>
                    <TableCell>
                      <div className="font-medium text-slate-900 text-sm">{p.material_description || p.name}</div>
                      <div className="text-[11px] text-slate-500">{p.category_name} · {p.grade_specs || "-"} · {p.pack_size || ""}</div>
                    </TableCell>
                    <TableCell className="text-right"><Input type="number" value={v.mrp} onChange={e => patch(p.id, { mrp: e.target.value })} className="h-8 w-24 text-right" /></TableCell>
                    <TableCell className="text-right"><Input type="number" value={v.dlp} onChange={e => patch(p.id, { dlp: e.target.value })} className="h-8 w-24 text-right font-semibold" /></TableCell>
                    <TableCell><Input type="number" value={v.margin} onChange={e => patch(p.id, { margin: e.target.value })} className="h-8 w-16" /></TableCell>
                    <TableCell><Input value={v.cash_coupon} onChange={e => patch(p.id, { cash_coupon: e.target.value })} className="h-8 w-32" /></TableCell>
                    <TableCell><Input value={v.foc_benefits} onChange={e => patch(p.id, { foc_benefits: e.target.value })} className="h-8 w-24" /></TableCell>
                    <TableCell><Input value={v.monthly_gift} onChange={e => patch(p.id, { monthly_gift: e.target.value })} className="h-8 w-24" /></TableCell>
                    <TableCell><Input value={v.trade_discount} onChange={e => patch(p.id, { trade_discount: e.target.value })} className="h-8 w-28" /></TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
        {filtered.length === 0 && <div className="p-8 text-center text-sm text-slate-500">No products match your filter</div>}
      </Card>

      <div className="mt-4 text-xs text-slate-500 bg-[#faf6e6] border border-[#c9a227]/25 rounded-lg p-3">
        💡 <b>Tip:</b> Values are pre-filled from the previous circular. Change any DLP and check the box to include that product in the new batch. Distributors will see <b>Old ₹X → New ₹Y</b> next time they order. Full pricing history is always preserved.
      </div>
    </div>
  );
}

// ============================================================================
// Settings — GST % + company name
// ============================================================================
export function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    gst_pct: 0, company_name: "", invoice_terms: "", invoice_message: "",
    company_gstin: "", company_address: "", company_state: "", company_state_code: "",
    company_phone: "", company_email: "", company_logo_url: "",
    company_bank_name: "", company_bank_account: "", company_bank_ifsc: "", company_bank_branch: "",
    company_upi_id: "", company_upi_name: "", invoice_signatory: "",
    invoice_show_acknowledgement: false,
  });
  const [fyLockDate, setFyLockDate] = useState("");
  const [fyBusy, setFyBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const s = await dms.getSettings();
      setSettings(s);
      setForm({
        gst_pct: s.gst_pct || 0,
        company_name: s.company_name || "GO OIL Lubricants",
        invoice_terms: s.invoice_terms || "",
        invoice_message: s.invoice_message || "",
        company_gstin: s.company_gstin || "",
        company_address: s.company_address || "",
        company_state: s.company_state || "",
        company_state_code: s.company_state_code || "",
        company_phone: s.company_phone || "",
        company_email: s.company_email || "",
        company_logo_url: s.company_logo_url || "",
        company_bank_name: s.company_bank_name || "",
        company_bank_account: s.company_bank_account || "",
        company_bank_ifsc: s.company_bank_ifsc || "",
        company_bank_branch: s.company_bank_branch || "",
        company_upi_id: s.company_upi_id || "",
        company_upi_name: s.company_upi_name || "",
        invoice_signatory: s.invoice_signatory || "",
        invoice_show_acknowledgement: !!s.invoice_show_acknowledgement,
      });
    })();
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const s = await dms.updateSettings({
        ...form,
        gst_pct: Number(form.gst_pct),
      });
      setSettings(s);
      toast.success("Settings updated");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    } finally { setSaving(false); }
  };

  const doFyClose = async () => {
    if (!fyLockDate) return toast.error("Pick a lock date");
    if (!window.confirm(`Close (lock) the financial year up to ${fyLockDate}? Transactions on or before this date will be immutable.`)) return;
    setFyBusy(true);
    try {
      const r = await dms.fyClose(fyLockDate);
      toast.success(`Financial year locked up to ${r.fy_lock_date}`);
      const s = await dms.getSettings();
      setSettings(s);
      setFyLockDate("");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    setFyBusy(false);
  };

  if (!settings) return <div className="p-8 text-center text-sm text-slate-500">Loading…</div>;

  return (
    <div>
      <PageHeader title="Settings" subtitle="Global configuration for GO OIL DMS" />
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="p-6 border-[#c9a227]/20 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[#faf0cf] to-[#c9a227]/25 flex items-center justify-center"><TrendingUp size={20} className="text-[#a67c00]" /></div>
            <div>
              <div className="font-display font-bold text-slate-900">Tax Configuration</div>
              <div className="text-xs text-slate-500">GST % applied on all orders (default 0%)</div>
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <Label>GST %</Label>
              <Input type="number" min={0} max={100} step="0.01" value={form.gst_pct} onChange={e => setForm({ ...form, gst_pct: e.target.value })} data-testid="setting-gst-input" />
              <div className="text-[11px] text-slate-500 mt-1">Applied on order subtotals across Primary + Secondary sales. Set to 0 to disable.</div>
            </div>
          </div>
        </Card>

        <Card className="p-6 border-[#c9a227]/20 shadow-sm md:col-span-2">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[#faf0cf] to-[#c9a227]/25 flex items-center justify-center"><FileText size={20} className="text-[#a67c00]" /></div>
            <div>
              <div className="font-display font-bold text-slate-900">Company Profile (Invoice)</div>
              <div className="text-xs text-slate-500">Seller details printed on the primary e-Bill header</div>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <Label>Company Name</Label>
              <Input value={form.company_name} onChange={e => setForm({ ...form, company_name: e.target.value })} data-testid="setting-company-input" />
            </div>
            <div>
              <Label>GSTIN</Label>
              <Input value={form.company_gstin} onChange={e => setForm({ ...form, company_gstin: e.target.value })} placeholder="07ABCDE1234F1Z5" data-testid="setting-company-gstin" />
            </div>
            <div className="md:col-span-2">
              <Label>Address</Label>
              <textarea rows={2} value={form.company_address} onChange={e => setForm({ ...form, company_address: e.target.value })} className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 text-sm" placeholder="Registered office address" data-testid="setting-company-address" />
            </div>
            <div>
              <Label>State</Label>
              <Input value={form.company_state} onChange={e => setForm({ ...form, company_state: e.target.value })} placeholder="Delhi" />
            </div>
            <div>
              <Label>State Code</Label>
              <Input value={form.company_state_code} onChange={e => setForm({ ...form, company_state_code: e.target.value })} placeholder="07" />
            </div>
            <div>
              <Label>Phone</Label>
              <Input value={form.company_phone} onChange={e => setForm({ ...form, company_phone: e.target.value })} />
            </div>
            <div>
              <Label>Email</Label>
              <Input value={form.company_email} onChange={e => setForm({ ...form, company_email: e.target.value })} />
            </div>
            <div className="md:col-span-2">
              <Label>Company Logo</Label>
              <div className="flex items-center gap-3 mt-1">
                {form.company_logo_url ? <img src={form.company_logo_url} alt="logo" className="h-12 w-12 object-contain border rounded" /> : <div className="h-12 w-12 border rounded flex items-center justify-center text-[10px] text-slate-400">No logo</div>}
                <input type="file" accept="image/*" data-testid="setting-company-logo" onChange={(e) => {
                  const f = e.target.files?.[0]; if (!f) return;
                  const rd = new FileReader(); rd.onload = () => setForm(v => ({ ...v, company_logo_url: rd.result })); rd.readAsDataURL(f);
                }} className="text-xs" />
                {form.company_logo_url && <Button variant="outline" size="sm" onClick={() => setForm(v => ({ ...v, company_logo_url: "" }))}>Remove</Button>}
              </div>
            </div>
            <div>
              <Label>Bank Name</Label>
              <Input value={form.company_bank_name} onChange={e => setForm({ ...form, company_bank_name: e.target.value })} data-testid="setting-company-bank" />
            </div>
            <div>
              <Label>Account No.</Label>
              <Input value={form.company_bank_account} onChange={e => setForm({ ...form, company_bank_account: e.target.value })} />
            </div>
            <div>
              <Label>IFSC</Label>
              <Input value={form.company_bank_ifsc} onChange={e => setForm({ ...form, company_bank_ifsc: e.target.value })} />
            </div>
            <div>
              <Label>Branch</Label>
              <Input value={form.company_bank_branch} onChange={e => setForm({ ...form, company_bank_branch: e.target.value })} />
            </div>
            <div>
              <Label>UPI ID (for QR)</Label>
              <Input value={form.company_upi_id} onChange={e => setForm({ ...form, company_upi_id: e.target.value })} placeholder="gooil@hdfcbank" data-testid="setting-company-upi" />
              <div className="text-[11px] text-slate-500 mt-1">A UPI QR is auto-generated on invoices from this ID.</div>
            </div>
            <div>
              <Label>UPI Payee Name</Label>
              <Input value={form.company_upi_name} onChange={e => setForm({ ...form, company_upi_name: e.target.value })} />
            </div>
            <div className="md:col-span-2">
              <Label>Authorized Signatory (label)</Label>
              <Input value={form.invoice_signatory} onChange={e => setForm({ ...form, invoice_signatory: e.target.value })} placeholder="For GO OIL Lubricants" />
            </div>
          </div>
        </Card>

        {/* Acknowledgement toggle (Vyapar-style) */}
        <Card className="p-6 border-[#c9a227]/20 shadow-sm md:col-span-2">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[#faf0cf] to-[#c9a227]/25 flex items-center justify-center"><FileText size={20} className="text-[#a67c00]" /></div>
              <div>
                <div className="font-display font-bold text-slate-900">Print Acknowledgement</div>
                <div className="text-xs text-slate-500">When ON, an Acknowledgement / receiver-sign section is printed at the bottom of every invoice.</div>
              </div>
            </div>
            <label className="inline-flex items-center gap-2 cursor-pointer select-none">
              <span className="text-sm text-slate-700">{form.invoice_show_acknowledgement ? "ON" : "OFF"}</span>
              <input
                type="checkbox"
                checked={!!form.invoice_show_acknowledgement}
                onChange={(e) => setForm({ ...form, invoice_show_acknowledgement: e.target.checked })}
                data-testid="setting-ack-toggle"
                className="h-5 w-9 appearance-none rounded-full bg-slate-300 checked:bg-[#a67c00] relative cursor-pointer transition-colors before:content-[''] before:absolute before:top-0.5 before:left-0.5 before:h-4 before:w-4 before:rounded-full before:bg-white before:transition-transform checked:before:translate-x-4"
              />
            </label>
          </div>
        </Card>

        {/* Phase 2A: Invoice Customization */}
        <Card className="p-6 border-[#c9a227]/20 shadow-sm md:col-span-2">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[#faf0cf] to-[#c9a227]/25 flex items-center justify-center"><FileText size={20} className="text-[#a67c00]" /></div>
            <div>
              <div className="font-display font-bold text-slate-900">Invoice Customization</div>
              <div className="text-xs text-slate-500">Custom message and terms shown on every invoice / bill PDF</div>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <Label>Invoice Message</Label>
              <textarea rows={3} value={form.invoice_message} onChange={e => setForm({ ...form, invoice_message: e.target.value })} className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 text-sm" placeholder="e.g. Thank you for your business!" data-testid="setting-invoice-message" />
            </div>
            <div>
              <Label>Terms &amp; Conditions</Label>
              <textarea rows={3} value={form.invoice_terms} onChange={e => setForm({ ...form, invoice_terms: e.target.value })} className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-200 text-sm" placeholder="e.g. Goods once sold will not be taken back. Payment due within 30 days." data-testid="setting-invoice-terms" />
            </div>
          </div>
        </Card>

        {/* Phase 2A: Financial Year Close */}
        <Card className="p-6 border-rose-200 shadow-sm md:col-span-2">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-10 w-10 rounded-xl bg-rose-50 text-rose-700 flex items-center justify-center"><Lock size={20} /></div>
            <div>
              <div className="font-display font-bold text-slate-900">Financial Year Close</div>
              <div className="text-xs text-slate-500">Lock all transactions on or before the chosen date. This is irreversible via UI (contact support to unlock).</div>
            </div>
          </div>
          <div className="grid md:grid-cols-3 gap-3">
            <div>
              <Label>Current FY Lock</Label>
              <div className="mt-1 h-10 px-3 rounded-lg border border-slate-200 bg-slate-50 text-sm flex items-center">
                {settings.fy_lock_date || <span className="text-slate-400">Not locked</span>}
              </div>
            </div>
            <div>
              <Label>New Lock Date</Label>
              <Input type="date" value={fyLockDate} onChange={e => setFyLockDate(e.target.value)} data-testid="fy-lock-date" />
            </div>
            <div className="flex items-end">
              <Button disabled={fyBusy || !fyLockDate} className="w-full bg-rose-700 hover:bg-rose-800 text-white" onClick={doFyClose} data-testid="fy-lock-btn">
                <Lock size={14} className="mr-2" /> Close Financial Year
              </Button>
            </div>
          </div>
        </Card>

        {/* Phase 2B: Stop Sale on Negative Stock */}
        <Card className="p-6 border-amber-200 shadow-sm md:col-span-2">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center"><Lock size={20} /></div>
              <div>
                <div className="font-display font-bold text-slate-900">Stop Sale on Negative Stock</div>
                <div className="text-xs text-slate-500">When ON, primary-order fulfillment and secondary dispatch are blocked if they would push stock below zero.</div>
              </div>
            </div>
            <label className="inline-flex items-center gap-2 cursor-pointer select-none">
              <span className="text-sm text-slate-700">{settings.stop_sale_on_negative === false ? "OFF" : "ON"}</span>
              <input
                type="checkbox"
                checked={settings.stop_sale_on_negative !== false}
                onChange={async (e) => {
                  try {
                    await dms.toggleStopSale(e.target.checked);
                    const s = await dms.getSettings(); setSettings(s);
                    toast.success(`Stop-Sale ${e.target.checked ? "enabled" : "disabled"}`);
                  } catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
                }}
                data-testid="stop-sale-toggle"
                className="h-5 w-9 appearance-none rounded-full bg-slate-300 checked:bg-amber-600 relative cursor-pointer transition-colors before:content-[''] before:absolute before:top-0.5 before:left-0.5 before:h-4 before:w-4 before:rounded-full before:bg-white before:transition-transform checked:before:translate-x-4"
              />
            </label>
          </div>
        </Card>
      </div>

      <div className="mt-6 flex justify-end">
        <Button onClick={save} disabled={saving} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white shadow-sm" data-testid="save-settings-btn">
          {saving ? "Saving…" : "Save Settings"}
        </Button>
      </div>

      <div className="mt-4 text-xs text-slate-500">
        Last updated: {settings.updated_at ? niceDate(settings.updated_at) : "—"}
      </div>
    </div>
  );
}
