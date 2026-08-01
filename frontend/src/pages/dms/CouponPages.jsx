import React, { useEffect, useState, useCallback } from "react";
import { dms, niceDate } from "./api";
import { PageHeader } from "./OwnerPages";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Ticket, Plus, Shield, ShieldAlert, ScanLine, CheckCircle2, XCircle, Trophy, Users, Store, Award, RefreshCw } from "lucide-react";

// ============================================================================
// Owner — Coupon Management
// ============================================================================
export function OwnerCouponsPage() {
  const [coupons, setCoupons] = useState([]);
  const [products, setProducts] = useState([]);
  const [dists, setDists] = useState([]);
  const [filters, setFilters] = useState({ status: "", product_id: "", distributor_id: "" });
  const [genOpen, setGenOpen] = useState(false);
  const [summary, setSummary] = useState(null);
  const [batches, setBatches] = useState([]);

  const load = useCallback(() => {
    const p = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
    dms.ownerListCoupons({ ...p, limit: 500 }).then(d => setCoupons(d.data || [])).catch(() => {});
    dms.ownerCouponSummary().then(setSummary).catch(() => {});
    dms.ownerCouponBatches().then(d => setBatches(d.data || [])).catch(() => {});
  }, [filters]);

  useEffect(() => {
    load();
    dms.listProducts().then(d => setProducts(d.data || [])).catch(() => {});
    dms.listDistributors().then(d => setDists(d.data || [])).catch(() => {});
  }, [load]);

  const totals = summary?.totals || {};
  return (
    <div>
      <PageHeader
        title="Coupon Management"
        subtitle="Generate coupons, view assignments, and monitor redemptions"
        action={
          <Button className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" onClick={() => setGenOpen(true)} data-testid="gen-coupons-btn">
            <Plus size={16} className="mr-2" /> Generate Coupons
          </Button>
        }
      />

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
        <Kpi label="Total"    value={totals.total ?? 0}   tint="bg-slate-100 text-slate-700" icon={Ticket} />
        <Kpi label="Unused"   value={totals.unused ?? 0}  tint="bg-blue-50 text-blue-700"    icon={Ticket} />
        <Kpi label="Assigned" value={totals.assigned ?? 0}tint="bg-amber-50 text-amber-700"  icon={Shield} />
        <Kpi label="Redeemed" value={totals.redeemed ?? 0}tint="bg-emerald-50 text-emerald-700" icon={CheckCircle2} />
        <Kpi label="Fraud"    value={totals.fraud_attempts ?? 0} tint="bg-rose-50 text-rose-700" icon={ShieldAlert} />
      </div>

      {/* Batches */}
      {batches.length > 0 && (
        <Card className="mb-4 overflow-x-auto">
          <div className="px-4 py-3 border-b border-slate-100 font-semibold text-slate-900">Coupon Batches</div>
          <Table>
            <TableHeader><TableRow>
              <TableHead>Batch</TableHead><TableHead>Product</TableHead>
              <TableHead className="text-right">Count</TableHead>
              <TableHead>Range</TableHead>
              <TableHead>Created</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {batches.map(b => (
                <TableRow key={b.id}>
                  <TableCell className="font-mono text-xs">{b.id}</TableCell>
                  <TableCell>{b.product_name}</TableCell>
                  <TableCell className="text-right font-semibold">{b.count.toLocaleString()}</TableCell>
                  <TableCell className="font-mono text-xs">{b.start_code} → {b.end_code}</TableCell>
                  <TableCell className="text-xs text-slate-500">{niceDate(b.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Filters */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-3">
        <Filter placeholder="Any status" value={filters.status} onChange={v => setFilters({ ...filters, status: v })} options={[
          { v: "", label: "All statuses" }, { v: "unused", label: "Unused" }, { v: "assigned", label: "Assigned" }, { v: "redeemed", label: "Redeemed" },
        ]} />
        <Filter placeholder="Any product" value={filters.product_id} onChange={v => setFilters({ ...filters, product_id: v })} options={[
          { v: "", label: "All products" }, ...products.map(p => ({ v: p.id, label: `${p.name} · ${p.sku_code}` })),
        ]} />
        <Filter placeholder="Any distributor" value={filters.distributor_id} onChange={v => setFilters({ ...filters, distributor_id: v })} options={[
          { v: "", label: "All distributors" }, ...dists.map(d => ({ v: d.id, label: d.name })),
        ]} />
      </div>

      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            <TableHead>Coupon</TableHead><TableHead>Product</TableHead>
            <TableHead>Assigned Distributor</TableHead><TableHead>Assigned On</TableHead>
            <TableHead>Status</TableHead><TableHead>Redeemed By</TableHead>
            <TableHead className="text-right">Points</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {coupons.length === 0 && <TableRow><TableCell colSpan={7} className="text-center py-8 text-slate-400">No coupons yet</TableCell></TableRow>}
            {coupons.map(c => (
              <TableRow key={c.id}>
                <TableCell className="font-mono font-semibold">{c.coupon_code}</TableCell>
                <TableCell className="text-xs">{c.product_name}</TableCell>
                <TableCell className="text-xs">{c.assigned_distributor_name || <span className="text-slate-400">—</span>}</TableCell>
                <TableCell className="text-xs text-slate-500">{c.assigned_on ? niceDate(c.assigned_on) : "—"}</TableCell>
                <TableCell><StatusChip s={c.status} /></TableCell>
                <TableCell className="text-xs">{c.redeemed_by_retailer_name || <span className="text-slate-400">—</span>}<div className="text-[10px] text-slate-500">{c.redeemed_at ? niceDate(c.redeemed_at) : ""}</div></TableCell>
                <TableCell className="text-right font-medium">{c.points_value}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <GenerateDialog open={genOpen} onClose={() => setGenOpen(false)} products={products} onDone={load} />
    </div>
  );
}

function GenerateDialog({ open, onClose, products, onDone }) {
  const [pid, setPid] = useState("");
  const [count, setCount] = useState(1000);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (open) { setPid(products[0]?.id || ""); setCount(1000); } }, [open, products]);
  const submit = async () => {
    if (!pid || count <= 0) { toast.error("Pick a product and enter a positive count"); return; }
    setBusy(true);
    try {
      const r = await dms.ownerGenerateCoupons(pid, count);
      toast.success(`Generated ${r.count} coupons (${r.start_code} → ${r.end_code})`);
      onDone?.(); onClose();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle>Generate Coupons</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Product</Label>
            <Select value={pid} onValueChange={setPid}>
              <SelectTrigger data-testid="gen-product"><SelectValue /></SelectTrigger>
              <SelectContent>{products.map(p => <SelectItem key={p.id} value={p.id}>{p.name} · {p.sku_code}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div>
            <Label>Count</Label>
            <Input type="number" min={1} max={100000} value={count} onChange={e => setCount(Number(e.target.value) || 0)} data-testid="gen-count" />
            <div className="text-[11px] text-slate-500 mt-1">Codes will be sequential (e.g. CPN000001 → CPN00XXXX). Max 100,000 per batch.</div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={busy} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="gen-submit">{busy ? "Generating…" : "Generate"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// Owner — Coupon Reports (Fraud + History)
// ============================================================================
export function OwnerCouponReportsPage() {
  const [tab, setTab] = useState("summary");
  const [summary, setSummary] = useState(null);
  const [fraud, setFraud] = useState([]);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    dms.ownerCouponSummary().then(setSummary).catch(() => {});
    dms.ownerCouponFraud().then(d => setFraud(d.data || [])).catch(() => {});
    dms.ownerCouponHistory().then(d => setHistory(d.data || [])).catch(() => {});
  }, []);

  const tabs = [
    { id: "summary", label: "Distributor / Retailer Summary" },
    { id: "history", label: "Redemption History" },
    { id: "fraud", label: `Fraud Attempts${fraud.length > 0 ? ` (${fraud.length})` : ""}` },
  ];

  return (
    <div>
      <PageHeader title="Coupon Reports" subtitle="Assignments, redemptions and fraud attempt logs" />
      <div className="flex gap-1 border-b border-slate-200 mb-4">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2 text-sm font-semibold border-b-2 ${tab === t.id ? "border-[#a67c00] text-[#8a6600]" : "border-transparent text-slate-500 hover:text-slate-800"}`}>{t.label}</button>
        ))}
      </div>

      {tab === "summary" && summary && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <div className="px-4 py-3 border-b border-slate-100 font-semibold text-slate-900 flex items-center gap-2"><Users size={16} /> Distributor-wise</div>
            <Table>
              <TableHeader><TableRow>
                <TableHead>Distributor</TableHead>
                <TableHead className="text-right">Assigned</TableHead>
                <TableHead className="text-right">Redeemed</TableHead>
                <TableHead className="text-right">Points</TableHead>
              </TableRow></TableHeader>
              <TableBody>
                {summary.by_distributor.length === 0 && <TableRow><TableCell colSpan={4} className="text-center py-6 text-slate-400">No assignments yet</TableCell></TableRow>}
                {summary.by_distributor.map(r => (
                  <TableRow key={r.distributor_id}>
                    <TableCell>{r.distributor_name}</TableCell>
                    <TableCell className="text-right">{r.assigned.toLocaleString()}</TableCell>
                    <TableCell className="text-right font-semibold text-emerald-700">{r.redeemed.toLocaleString()}</TableCell>
                    <TableCell className="text-right">{r.points_redeemed.toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>

          <Card>
            <div className="px-4 py-3 border-b border-slate-100 font-semibold text-slate-900 flex items-center gap-2"><Store size={16} /> Retailer-wise</div>
            <Table>
              <TableHeader><TableRow>
                <TableHead>Retailer</TableHead>
                <TableHead className="text-right">Redeemed</TableHead>
                <TableHead className="text-right">Points</TableHead>
              </TableRow></TableHeader>
              <TableBody>
                {summary.by_retailer.length === 0 && <TableRow><TableCell colSpan={3} className="text-center py-6 text-slate-400">No redemptions yet</TableCell></TableRow>}
                {summary.by_retailer.map((r, i) => (
                  <TableRow key={r.retailer_id}>
                    <TableCell>{i === 0 && <Trophy size={12} className="inline mr-1 text-amber-500" />}{r.retailer_name}</TableCell>
                    <TableCell className="text-right font-semibold">{r.redeemed.toLocaleString()}</TableCell>
                    <TableCell className="text-right">{r.points.toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}

      {tab === "history" && (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>Coupon</TableHead><TableHead>Product</TableHead>
              <TableHead>Distributor</TableHead><TableHead>Retailer</TableHead>
              <TableHead className="text-right">Points</TableHead>
              <TableHead>Redeemed At</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {history.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-8 text-slate-400">No redemptions yet</TableCell></TableRow>}
              {history.map(h => (
                <TableRow key={h.id}>
                  <TableCell className="font-mono font-semibold">{h.coupon_code}</TableCell>
                  <TableCell className="text-xs">{h.product_name}</TableCell>
                  <TableCell className="text-xs">{h.assigned_distributor_name}</TableCell>
                  <TableCell className="text-xs">{h.redeemed_by_retailer_name}</TableCell>
                  <TableCell className="text-right font-medium">{h.points_value}</TableCell>
                  <TableCell className="text-xs text-slate-500">{niceDate(h.redeemed_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {tab === "fraud" && (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>Coupon</TableHead><TableHead>Retailer</TableHead>
              <TableHead>Retailer's Distributor</TableHead><TableHead>Coupon Owner Distributor</TableHead>
              <TableHead>Reason</TableHead><TableHead>Attempted At</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {fraud.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-8 text-slate-400">✓ No fraud attempts logged</TableCell></TableRow>}
              {fraud.map(f => (
                <TableRow key={f.id} className="bg-rose-50/30">
                  <TableCell className="font-mono">{f.coupon_code}</TableCell>
                  <TableCell>{f.attempted_by_retailer_name}</TableCell>
                  <TableCell className="text-xs font-mono">{f.attempted_by_retailer_distributor_id || "—"}</TableCell>
                  <TableCell className="text-xs font-mono">{f.coupon_owner_distributor_id || "—"}</TableCell>
                  <TableCell><span className="text-xs px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 font-semibold">{f.reason}</span></TableCell>
                  <TableCell className="text-xs text-slate-500">{niceDate(f.at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}

// ============================================================================
// Retailer — Coupon Scanner
// ============================================================================
export function RetailerScanCouponPage() {
  return <ScanCouponPageBase role="retailer" />;
}

export function DistributorScanCouponPage() {
  return <ScanCouponPageBase role="distributor" />;
}

function ScanCouponPageBase({ role }) {
  const [code, setCode] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState({ data: [], total_points: 0 });

  const loadHist = () => {
    if (role !== "retailer") return;
    dms.retailerCouponHistory().then(setHistory).catch(() => {});
  };
  useEffect(() => { loadHist(); }, []);

  const scan = async () => {
    const c = (code || "").trim().toUpperCase();
    if (!c) return;
    setBusy(true); setResult(null);
    try {
      const r = role === "distributor" ? await dms.scanCouponDistributor(c) : await dms.retailerScanCoupon(c);
      setResult({ ok: true, ...r });
      toast.success(r.message);
      setCode("");
      loadHist();
    } catch (e) {
      setResult({ ok: false, message: e?.response?.data?.detail || "Failed" });
    } finally { setBusy(false); }
  };

  const subtitle = role === "distributor"
    ? "Scan a coupon assigned to you — credit will reflect in your Primary Ledger against Owner"
    : "Enter or scan a coupon code — credit will reflect in your ledger against your distributor";

  return (
    <div>
      <PageHeader title="Scan Coupon" subtitle={subtitle} />
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3 text-slate-900 font-semibold"><ScanLine size={18} /> Redeem</div>
          <Label>Coupon Code</Label>
          <div className="flex gap-2 mt-1">
            <Input value={code} onChange={e => setCode(e.target.value.toUpperCase())} placeholder="e.g. CPN000123" onKeyDown={e => e.key === "Enter" && scan()} data-testid="scan-input" />
            <Button onClick={scan} disabled={busy || !code.trim()} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="scan-btn">{busy ? "Scanning…" : "Scan"}</Button>
          </div>
          {result && (
            <div className={`mt-4 p-4 rounded-lg border ${result.ok ? "bg-emerald-50 border-emerald-200" : "bg-rose-50 border-rose-200"}`} data-testid="scan-result">
              <div className="flex items-start gap-2">
                {result.ok ? <CheckCircle2 size={22} className="text-emerald-600 mt-0.5" /> : <XCircle size={22} className="text-rose-600 mt-0.5" />}
                <div>
                  <div className={`font-semibold ${result.ok ? "text-emerald-900" : "text-rose-900"}`}>{result.ok ? "Redeemed" : "Rejected"}</div>
                  {result.ok && result.coupon_code && (
                    <div className="text-sm mt-1">
                      <span className="font-mono font-semibold">{result.coupon_code}</span> · {result.product_name} ·{" "}
                      <b className="text-emerald-700">+₹{(result.credit_amount ?? result.points_value ?? 0).toLocaleString()} ledger credit</b>
                    </div>
                  )}
                  {result.message && <div className="text-sm text-slate-700 mt-1">{result.message}</div>}
                </div>
              </div>
            </div>
          )}
          <div className="mt-4 text-xs text-slate-500 bg-slate-50 rounded p-3">
            💡 The coupon amount is added as a <b className="text-emerald-700">credit</b> to your ledger — it directly reduces your outstanding {role === "distributor" ? "with the Company" : "with your distributor"}.
          </div>
        </Card>

        {role === "retailer" && (
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-slate-900 font-semibold"><Award size={18} /> My Redemptions</div>
              <div className="text-2xl font-bold text-[#8a6600]">₹{history.total_points.toLocaleString()}</div>
            </div>
            <div className="text-xs text-slate-500 mb-3">Last {history.data.length} redemptions</div>
            <div className="max-h-72 overflow-y-auto space-y-1">
              {history.data.length === 0 && <div className="text-center py-6 text-sm text-slate-400">No redemptions yet</div>}
              {history.data.map(c => (
                <div key={c.id} className="flex items-center justify-between text-sm py-1.5 border-b border-slate-50">
                  <div>
                    <div className="font-mono font-semibold text-slate-900">{c.coupon_code}</div>
                    <div className="text-[11px] text-slate-500">{c.product_name} · {niceDate(c.redeemed_at)}</div>
                  </div>
                  <div className="text-emerald-700 font-semibold">+₹{(c.points_value || 0).toLocaleString()}</div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

// ── helpers ──
function Kpi({ label, value, tint, icon: Icon }) {
  return (
    <Card className="p-4">
      <div className={`inline-flex h-9 w-9 rounded-lg items-center justify-center mb-2 ${tint}`}><Icon size={18} /></div>
      <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">{label}</div>
      <div className="text-xl font-bold text-slate-900 mt-1">{value.toLocaleString ? value.toLocaleString() : value}</div>
    </Card>
  );
}

function StatusChip({ s }) {
  const map = {
    unused:   "bg-blue-100 text-blue-800",
    assigned: "bg-amber-100 text-amber-800",
    redeemed: "bg-emerald-100 text-emerald-800",
  };
  return <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${map[s] || "bg-slate-100 text-slate-700"}`}>{s}</span>;
}

function Filter({ value, onChange, placeholder, options }) {
  return (
    <Select value={value || "__all__"} onValueChange={v => onChange(v === "__all__" ? "" : v)}>
      <SelectTrigger><SelectValue placeholder={placeholder} /></SelectTrigger>
      <SelectContent>{options.map(o => <SelectItem key={o.v || "__all__"} value={o.v || "__all__"}>{o.label}</SelectItem>)}</SelectContent>
    </Select>
  );
}
