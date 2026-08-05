/**
 * GO OIL — Enterprise Coupon & Reward Engine (Frontend)
 * ─────────────────────────────────────────────────────
 *
 *  Owner       → Batches / Coupons / Redemptions / Credit Notes / Dispatch Advices /
 *                Reports / Audit Log
 *  Accountant  → Redemptions / Credit Notes (approval flow)
 *  Sales Off.  → Retailer picker + Scan flow (camera + manual)
 *  Retailer    → Cash Wallet + Reward Wallet + History (VIEW ONLY — no scan)
 *  Distributor → Retailer wallets + Credit Notes + Dispatch Advices (VIEW ONLY)
 *  Team Leader → Salesperson performance reports (VIEW ONLY)
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { dms, niceDate, inr } from "./api";
import { PageHeader } from "./OwnerPages";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  Ticket, Plus, Shield, ShieldAlert, ScanLine, CheckCircle2, XCircle, Trophy,
  Users, Store, Award, RefreshCw, PackageCheck, Printer, FileSpreadsheet,
  FileText, Wallet, Coins, Truck, Search, ArrowRight, ChevronLeft, ChevronRight,
  Play, PauseCircle, Copy, AlertTriangle, ClipboardList, Activity, TrendingUp,
} from "lucide-react";

// ═════════════════════════ shared bits ══════════════════════════════════════
const GOLD_BTN = "bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white";

function Kpi({ label, value, tint = "bg-slate-100 text-slate-700", icon: Icon = Ticket, suffix }) {
  const display = typeof value === "number" ? value.toLocaleString("en-IN") : (value ?? 0);
  return (
    <Card className="p-4">
      <div className={`inline-flex h-9 w-9 rounded-lg items-center justify-center mb-2 ${tint}`}>
        <Icon size={18} />
      </div>
      <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">{label}</div>
      <div className="text-xl font-bold text-slate-900 mt-1">
        {display}{suffix && <span className="text-sm text-slate-500 ml-1">{suffix}</span>}
      </div>
    </Card>
  );
}

const STATUS_STYLES = {
  generated: "bg-slate-100 text-slate-700",
  activated: "bg-blue-100 text-blue-800",
  printed: "bg-indigo-100 text-indigo-800",
  issued_to_production: "bg-violet-100 text-violet-800",
  unused: "bg-emerald-50 text-emerald-800 border border-emerald-200",
  claimed: "bg-amber-100 text-amber-800",
  redemption_pending: "bg-orange-100 text-orange-800",
  redeemed: "bg-emerald-100 text-emerald-800",
  expired: "bg-slate-200 text-slate-600",
  cancelled: "bg-rose-100 text-rose-800",
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-rose-100 text-rose-800",
  dispatched: "bg-indigo-100 text-indigo-800",
  issued: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
};
function StatusChip({ s }) {
  return (
    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${STATUS_STYLES[s] || "bg-slate-100 text-slate-700"}`}>
      {(s || "").replace(/_/g, " ")}
    </span>
  );
}

function Tabs({ tabs, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-1 border-b border-slate-200 mb-4">
      {tabs.map(t => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`px-4 py-2 text-sm font-semibold border-b-2 whitespace-nowrap ${
            value === t.id
              ? "border-[#a67c00] text-[#8a6600]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          {t.label}{t.badge != null && (
            <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
              {t.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

// ═════════════════════════ OWNER: Coupon Dashboard (Batches + KPIs) ═════════
export function OwnerCouponsPage() {
  const [summary, setSummary] = useState(null);
  const [batches, setBatches] = useState([]);
  const [busy, setBusy] = useState(false);
  const [genOpen, setGenOpen] = useState(false);
  const nav = useNavigate();

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [s, b] = await Promise.all([
        dms.cpnReportsSummary().catch(() => null),
        dms.cpnListBatches().catch(() => ({ data: [] })),
      ]);
      setSummary(s); setBatches(b.data || []);
    } finally { setBusy(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const t = summary?.totals || {};
  const cash = summary?.by_type?.cash || {};
  const reward = summary?.by_type?.reward || {};
  const cashValueUnused = cash?.unused?.value || 0;
  const rewardValueUnused = reward?.unused?.value || 0;

  return (
    <div>
      <PageHeader
        title="Coupon Management"
        subtitle="Generate batches, activate, print sheets and monitor lifecycle end-to-end"
        action={
          <div className="flex gap-2">
            <Button variant="outline" onClick={load} disabled={busy} data-testid="cpn-refresh">
              <RefreshCw size={14} className={busy ? "animate-spin" : ""} />
            </Button>
            <Button className={GOLD_BTN} onClick={() => setGenOpen(true)} data-testid="cpn-gen-btn">
              <Plus size={16} className="mr-2" /> Generate Batch
            </Button>
          </div>
        }
      />

      {/* Life-cycle KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-5">
        <Kpi label="Generated"  value={t.generated || 0}          tint="bg-slate-100 text-slate-700"       icon={Ticket} />
        <Kpi label="Unused"     value={t.unused || 0}             tint="bg-emerald-50 text-emerald-700"    icon={PackageCheck} />
        <Kpi label="Claimed"    value={t.claimed || 0}            tint="bg-amber-50 text-amber-700"        icon={ScanLine} />
        <Kpi label="Pending"    value={t.redemption_pending || 0} tint="bg-orange-50 text-orange-700"      icon={Activity} />
        <Kpi label="Redeemed"   value={t.redeemed || 0}           tint="bg-emerald-100 text-emerald-800"   icon={CheckCircle2} />
        <Kpi label="Expired"    value={t.expired || 0}            tint="bg-slate-200 text-slate-700"       icon={PauseCircle} />
        <Kpi label="Fraud"      value={summary?.fraud_attempts || 0} tint="bg-rose-50 text-rose-700"       icon={ShieldAlert} />
      </div>

      {/* Type breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Coins className="text-emerald-700" size={18} />
            <h3 className="font-bold text-slate-900">Cash Coupons</h3>
          </div>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <Stat label="Unused" v={cash?.unused?.count} sub={inr(cash?.unused?.value)} />
            <Stat label="Claimed" v={cash?.claimed?.count} sub={inr(cash?.claimed?.value)} />
            <Stat label="Redeemed" v={cash?.redeemed?.count} sub={inr(cash?.redeemed?.value)} />
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Award className="text-[#a67c00]" size={18} />
            <h3 className="font-bold text-slate-900">Reward Points Coupons</h3>
          </div>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <Stat label="Unused" v={reward?.unused?.count} sub={`${reward?.unused?.value || 0} pts`} />
            <Stat label="Claimed" v={reward?.claimed?.count} sub={`${reward?.claimed?.value || 0} pts`} />
            <Stat label="Redeemed" v={reward?.redeemed?.count} sub={`${reward?.redeemed?.value || 0} pts`} />
          </div>
        </Card>
      </div>

      {/* Batches Table */}
      <Card className="overflow-x-auto">
        <div className="px-4 py-3 border-b border-slate-100 font-semibold text-slate-900 flex items-center gap-2">
          <Ticket size={16} /> Coupon Batches
          <span className="ml-auto text-xs text-slate-500">{batches.length} total</span>
        </div>
        <Table>
          <TableHeader><TableRow>
            <TableHead>Batch</TableHead><TableHead>Title</TableHead>
            <TableHead>Type</TableHead><TableHead className="text-right">Value</TableHead>
            <TableHead className="text-right">Count</TableHead>
            <TableHead>Status</TableHead><TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {batches.length === 0 && (
              <TableRow><TableCell colSpan={8} className="text-center py-10 text-slate-400">
                No batches yet — click Generate Batch to create your first
              </TableCell></TableRow>
            )}
            {batches.map(b => (
              <TableRow key={b.id} className="hover:bg-amber-50/30">
                <TableCell className="font-mono text-xs font-semibold">{b.batch_label}</TableCell>
                <TableCell>{b.title}</TableCell>
                <TableCell>
                  {b.coupon_type === "cash"
                    ? <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-emerald-50 text-emerald-800"><Coins size={12} /> Cash</span>
                    : <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-800"><Award size={12} /> Reward</span>}
                </TableCell>
                <TableCell className="text-right font-semibold">
                  {b.coupon_type === "cash" ? inr(b.coupon_value) : `${b.coupon_value} pts`}
                </TableCell>
                <TableCell className="text-right">{b.count?.toLocaleString?.() || b.count}</TableCell>
                <TableCell><StatusChip s={b.status} /></TableCell>
                <TableCell className="text-xs text-slate-500">{niceDate(b.created_at)}</TableCell>
                <TableCell className="text-right">
                  <Button size="sm" variant="outline" onClick={() => nav(`/dms/owner/coupons/batches/${b.id}`)}
                          data-testid={`cpn-batch-view-${b.batch_no}`}>
                    Open <ArrowRight size={14} className="ml-1" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <GenerateBatchDialog open={genOpen} onClose={() => setGenOpen(false)} onDone={(bid) => { load(); nav(`/dms/owner/coupons/batches/${bid}`); }} />
    </div>
  );
}

function Stat({ label, v, sub }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3 border border-slate-100">
      <div className="text-[10px] uppercase text-slate-500 font-semibold">{label}</div>
      <div className="text-lg font-bold text-slate-900">{(v || 0).toLocaleString("en-IN")}</div>
      {sub && <div className="text-[11px] text-slate-500 mt-0.5">{sub}</div>}
    </div>
  );
}

// ═════════════════════════ OWNER: Generate Batch Dialog ═════════════════════
function GenerateBatchDialog({ open, onClose, onDone }) {
  const [type, setType] = useState("cash");
  const [value, setValue] = useState(20);
  const [count, setCount] = useState(100);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [mode, setMode] = useState("prefix_sequential"); // or "random_secure"
  const [prefix, setPrefix] = useState("ABC");
  const [serialStart, setSerialStart] = useState(1);
  const [serialPad, setSerialPad] = useState(3);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setType("cash"); setValue(20); setCount(100); setTitle(""); setNotes("");
      setMode("prefix_sequential"); setPrefix("ABC");
      setSerialStart(1); setSerialPad(3);
    }
  }, [open]);

  // Auto-bump padding when serial count grows
  useEffect(() => {
    if (mode !== "prefix_sequential") return;
    const maxSerial = Number(serialStart) + Number(count) - 1;
    const needed = String(Math.max(1, maxSerial)).length;
    if (needed > Number(serialPad)) setSerialPad(needed);
  }, [count, serialStart, mode, serialPad]);

  const suggested = useMemo(() => {
    const unit = type === "cash" ? "₹" : "";
    const suffix = type === "cash" ? "" : " pts";
    if (mode === "prefix_sequential") {
      return `${type.toUpperCase()} ${prefix} × ${count}`;
    }
    return `${type.toUpperCase()} ${unit}${value}${suffix} × ${count}`;
  }, [type, value, count, mode, prefix]);

  const serialPreview = useMemo(() => {
    if (mode !== "prefix_sequential") return null;
    const pfx = (prefix || "").toUpperCase();
    const pad = Math.max(1, Number(serialPad) || 3);
    const start = Number(serialStart) || 1;
    const cnt = Math.max(1, Number(count) || 1);
    const first = `${pfx}${String(start).padStart(pad, "0")}`;
    const second = `${pfx}${String(start + 1).padStart(pad, "0")}`;
    const last = `${pfx}${String(start + cnt - 1).padStart(pad, "0")}`;
    return { first, second, last };
  }, [prefix, serialStart, serialPad, count, mode]);

  const submit = async () => {
    const v = Number(value);
    const c = Math.floor(Number(count));
    if (!v || v <= 0) { toast.error("Value must be > 0"); return; }
    if (!c || c <= 0 || c > 100000) { toast.error("Count must be 1 – 100,000"); return; }
    if (mode === "prefix_sequential") {
      const pfx = (prefix || "").trim().toUpperCase();
      if (!/^[A-Z0-9]{1,10}$/.test(pfx)) {
        toast.error("Prefix must be 1-10 chars: A-Z or 0-9 only");
        return;
      }
      const maxSerial = Number(serialStart) + c - 1;
      if (String(maxSerial).length > Number(serialPad)) {
        toast.error(`Padding ${serialPad} too small for serial ${maxSerial}`);
        return;
      }
    }
    setBusy(true);
    try {
      const body = {
        coupon_type: type, coupon_value: v, count: c,
        title: (title || suggested).trim(), notes: notes.trim(),
        serial_mode: mode,
      };
      if (mode === "prefix_sequential") {
        body.prefix = (prefix || "").toUpperCase();
        body.serial_start = Number(serialStart) || 1;
        body.serial_pad = Number(serialPad) || 3;
      }
      const r = await dms.cpnCreateBatch(body);
      toast.success(`Batch ${r.batch.batch_label} created — ${c.toLocaleString()} coupons`);
      onDone?.(r.batch.id); onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to generate batch");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={o => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>Generate Coupon Batch</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Coupon Type</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger data-testid="gen-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="cash">Cash (₹)</SelectItem>
                  <SelectItem value="reward">Reward Points</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{type === "cash" ? "Coupon Value (₹)" : "Points per Coupon"}</Label>
              <Input type="number" min={1} value={value} onChange={e => setValue(e.target.value)} data-testid="gen-value" />
            </div>
          </div>

          <div>
            <Label>Serial Mode</Label>
            <Select value={mode} onValueChange={setMode}>
              <SelectTrigger data-testid="gen-mode"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="prefix_sequential">Prefix + Sequential (e.g. ABC001, ABC002…)</SelectItem>
                <SelectItem value="random_secure">Random Secure (legacy, non-sequential)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {mode === "prefix_sequential" && (
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label>Prefix</Label>
                <Input value={prefix} maxLength={10}
                       onChange={e => setPrefix(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))}
                       data-testid="gen-prefix" />
              </div>
              <div>
                <Label>Start #</Label>
                <Input type="number" min={0} value={serialStart}
                       onChange={e => setSerialStart(e.target.value)} data-testid="gen-start" />
              </div>
              <div>
                <Label>Padding</Label>
                <Input type="number" min={1} max={10} value={serialPad}
                       onChange={e => setSerialPad(e.target.value)} data-testid="gen-pad" />
              </div>
            </div>
          )}

          <div>
            <Label>Number of Coupons</Label>
            <Input type="number" min={1} max={100000} value={count} onChange={e => setCount(e.target.value)} data-testid="gen-count" />
            {mode === "prefix_sequential" && serialPreview ? (
              <p className="text-[11px] text-slate-600 mt-1">
                Preview: <span className="font-mono font-semibold text-slate-800">
                  {serialPreview.first}, {serialPreview.second}, … {serialPreview.last}
                </span>
              </p>
            ) : (
              <p className="text-[11px] text-slate-500 mt-1">
                Codes will be non-sequential secure random (e.g. QSRD-9X7K-LA82-MPQ4). Max 100,000 per batch.
              </p>
            )}
          </div>

          <div>
            <Label>Title <span className="text-slate-400 text-xs">(optional)</span></Label>
            <Input value={title} placeholder={suggested} onChange={e => setTitle(e.target.value)} />
          </div>
          <div>
            <Label>Notes <span className="text-slate-400 text-xs">(optional)</span></Label>
            <Textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} />
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-900">
            <b>Security:</b> Every coupon gets an independent UUID v4 hidden ID + AES-256 encrypted QR payload + HMAC-SHA256 signature.<br/>
            <b>Next steps:</b> Coupons start <b>inactive</b>. Activate a single coupon, a range, or the entire batch before printing.
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={busy} className={GOLD_BTN} data-testid="gen-submit">
            {busy ? "Generating…" : "Generate Batch"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ═════════════════════════ OWNER: Batch Detail ══════════════════════════════
export function OwnerCouponBatchDetailPage() {
  const { bid } = useParams();
  const nav = useNavigate();
  const [batch, setBatch] = useState(null);
  const [coupons, setCoupons] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [rangeOpen, setRangeOpen] = useState(false);

  const load = useCallback(async () => {
    if (!bid) return;
    setBusy(true);
    try {
      const [b, list] = await Promise.all([
        dms.cpnGetBatch(bid),
        dms.cpnListCoupons({ batch_id: bid, limit: 500, status: statusFilter || undefined }),
      ]);
      setBatch(b); setCoupons(list.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load batch");
    } finally { setBusy(false); }
  }, [bid, statusFilter]);

  useEffect(() => { load(); }, [load]);

  const doAction = async (fn, msg) => {
    setBusy(true);
    try { await fn(); toast.success(msg); await load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  if (!batch) {
    return <div className="p-10 text-center text-slate-400">{busy ? "Loading…" : "Batch not found"}</div>;
  }

  const cnt = batch.counts_by_status || {};
  const usable = ["generated"].includes(batch.status);
  const canActivate = batch.status === "generated";
  const canPrint = batch.active;

  return (
    <div>
      <PageHeader
        title={`Batch ${batch.batch_label}`}
        subtitle={
          <span className="flex items-center gap-2">
            {batch.title} <StatusChip s={batch.status} />
            {batch.active && <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">ACTIVE</span>}
          </span>
        }
        action={
          <Button variant="outline" onClick={() => nav("/dms/owner/coupons")}>
            <ChevronLeft size={14} /> Back
          </Button>
        }
      />

      {/* Meta + counts */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        <Card className="p-4">
          <div className="text-[11px] uppercase text-slate-500 font-semibold">Type</div>
          <div className="font-bold text-slate-900 flex items-center gap-2 mt-1">
            {batch.coupon_type === "cash"
              ? <><Coins size={16} className="text-emerald-700" /> Cash Coupon</>
              : <><Award size={16} className="text-[#a67c00]" /> Reward Points</>}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-[11px] uppercase text-slate-500 font-semibold">Value / Coupon</div>
          <div className="text-lg font-bold text-slate-900 mt-1">
            {batch.coupon_type === "cash" ? inr(batch.coupon_value) : `${batch.coupon_value} pts`}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-[11px] uppercase text-slate-500 font-semibold">Total Value</div>
          <div className="text-lg font-bold text-slate-900 mt-1">
            {batch.coupon_type === "cash"
              ? inr(batch.total_value)
              : `${(batch.total_value || 0).toLocaleString("en-IN")} pts`}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-[11px] uppercase text-slate-500 font-semibold">Total Coupons</div>
          <div className="text-lg font-bold text-slate-900 mt-1">
            {(batch.count || 0).toLocaleString("en-IN")}
          </div>
        </Card>
      </div>

      {/* Actions */}
      <Card className="p-4 mb-5">
        <div className="flex items-center gap-2 flex-wrap">
          {canActivate && (
            <Button className={GOLD_BTN} disabled={busy}
                    onClick={() => doAction(() => dms.cpnActivateBatch(bid), "Batch activated")}
                    data-testid="batch-activate">
              <Play size={14} className="mr-1" /> Activate Batch
            </Button>
          )}
          {canPrint && (
            <>
              <Button variant="outline" disabled={busy}
                      onClick={() => dms.cpnExportPdf(bid, `${batch.batch_label}_coupons.pdf`).catch(e => toast.error("Failed"))}
                      data-testid="batch-pdf">
                <Printer size={14} className="mr-1" /> Export PDF (Printing Press)
              </Button>
              <Button variant="outline" disabled={busy}
                      onClick={() => dms.cpnExportXlsx(bid, `${batch.batch_label}_manifest.xlsx`).catch(e => toast.error("Failed"))}
                      data-testid="batch-xlsx">
                <FileSpreadsheet size={14} className="mr-1" /> Export Excel (Audit)
              </Button>
              <Button variant="outline" disabled={busy}
                      onClick={() => doAction(() => dms.cpnMarkPrinted(bid), "Marked as printed")}>
                Mark Printed
              </Button>
              <Button variant="outline" disabled={busy}
                      onClick={() => doAction(() => dms.cpnIssueToProd(bid), "Issued to production")}>
                <Truck size={14} className="mr-1" /> Issue to Production
              </Button>
            </>
          )}
          {batch.active && (
            <Button variant="outline" className="text-rose-700 border-rose-200 hover:bg-rose-50" disabled={busy}
                    onClick={() => {
                      if (!window.confirm("Deactivate this batch? All unused coupons will be cancelled.")) return;
                      doAction(() => dms.cpnDeactivateBatch(bid), "Batch deactivated");
                    }}>
              Deactivate
            </Button>
          )}
        </div>
      </Card>

      {/* Coupon lifecycle counts */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-5">
        <Kpi label="Generated" value={cnt.generated || 0} />
        <Kpi label="Unused" value={cnt.unused || 0} tint="bg-emerald-50 text-emerald-700" icon={PackageCheck} />
        <Kpi label="Claimed" value={cnt.claimed || 0} tint="bg-amber-50 text-amber-700" icon={ScanLine} />
        <Kpi label="Redeem Pending" value={cnt.redemption_pending || 0} tint="bg-orange-50 text-orange-700" icon={Activity} />
        <Kpi label="Redeemed" value={cnt.redeemed || 0} tint="bg-emerald-100 text-emerald-800" icon={CheckCircle2} />
        <Kpi label="Expired" value={cnt.expired || 0} tint="bg-slate-200 text-slate-700" />
        <Kpi label="Cancelled" value={cnt.cancelled || 0} tint="bg-rose-50 text-rose-700" />
      </div>

      {/* Coupons list */}
      <Card className="overflow-x-auto">
        <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-slate-900">Coupons in this batch</span>
          <div className="ml-auto flex items-center gap-2 flex-wrap">
            <Select value={statusFilter || "__all__"} onValueChange={v => setStatusFilter(v === "__all__" ? "" : v)}>
              <SelectTrigger className="w-48"><SelectValue placeholder="All statuses" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All statuses</SelectItem>
                {["generated", "unused", "claimed", "redemption_pending", "redeemed", "expired", "cancelled"]
                  .map(s => <SelectItem key={s} value={s}>{s.replace(/_/g, " ")}</SelectItem>)}
              </SelectContent>
            </Select>
            {batch.serial_mode === "prefix_sequential" && (
              <Button variant="outline" size="sm"
                      onClick={() => setRangeOpen(true)} data-testid="open-range-dialog">
                <Play size={14} className="mr-1" /> Activate Range
              </Button>
            )}
          </div>
        </div>
        <Table>
          <TableHeader><TableRow>
            <TableHead>Visible Serial</TableHead><TableHead>Status</TableHead>
            <TableHead>Active</TableHead>
            <TableHead>Retailer</TableHead><TableHead>Distributor</TableHead>
            <TableHead>Claimed On</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {coupons.length === 0 && (
              <TableRow><TableCell colSpan={7} className="text-center py-8 text-slate-400">
                No coupons match this filter
              </TableCell></TableRow>
            )}
            {coupons.map(c => {
              const canAct = ["generated", "unused"].includes(c.status) && !c.active;
              const canDeact = ["generated", "unused"].includes(c.status) && c.active;
              return (
                <TableRow key={c.id}>
                  <TableCell className="font-mono font-semibold text-xs">{c.visible_serial || c.coupon_code}</TableCell>
                  <TableCell><StatusChip s={c.status} /></TableCell>
                  <TableCell>
                    {c.active
                      ? <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">ACTIVE</span>
                      : <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">INACTIVE</span>}
                  </TableCell>
                  <TableCell className="text-xs">{c.retailer_name || <span className="text-slate-400">—</span>}</TableCell>
                  <TableCell className="text-xs">{c.distributor_name || <span className="text-slate-400">—</span>}</TableCell>
                  <TableCell className="text-xs text-slate-500">{c.claim_timestamp ? niceDate(c.claim_timestamp) : "—"}</TableCell>
                  <TableCell className="text-right">
                    {canAct && (
                      <Button size="sm" variant="outline" className="h-7 px-2 text-xs" disabled={busy}
                              onClick={() => doAction(() => dms.cpnActivateCoupon(c.id), "Coupon activated")}
                              data-testid={`activate-${c.id}`}>
                        Activate
                      </Button>
                    )}
                    {canDeact && (
                      <Button size="sm" variant="outline" className="h-7 px-2 text-xs text-rose-700 border-rose-200 hover:bg-rose-50" disabled={busy}
                              onClick={() => doAction(() => dms.cpnDeactivateCoupon(c.id), "Coupon deactivated")}>
                        Deactivate
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Card>

      {/* Activate Range dialog */}
      <ActivateRangeDialog open={rangeOpen} onClose={() => setRangeOpen(false)}
                            batch={batch} onDone={load} />
    </div>
  );
}

function ActivateRangeDialog({ open, onClose, batch, onDone }) {
  const [fromN, setFromN] = useState("");
  const [toN, setToN] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open) {
      setFromN(batch?.serial_start ?? 1);
      setToN(batch?.serial_end ?? "");
    }
  }, [open, batch]);
  const preview = useMemo(() => {
    if (!batch?.prefix) return null;
    const pad = batch.serial_pad || 3;
    const fs = `${batch.prefix}${String(fromN || batch.serial_start || 1).padStart(pad, "0")}`;
    const ts = `${batch.prefix}${String(toN || batch.serial_end || fromN).padStart(pad, "0")}`;
    return { fs, ts };
  }, [batch, fromN, toN]);

  const submit = async () => {
    const f = Number(fromN), t = Number(toN);
    if (!f || !t) { toast.error("From and To required"); return; }
    setBusy(true);
    try {
      const r = await dms.cpnActivateRange({
        batch_id: batch.id, from_number: f, to_number: t,
      });
      toast.success(`Activated ${r.activated} of ${r.matched} in range ${r.from_serial} – ${r.to_serial}`);
      onDone?.(); onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to activate range");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={o => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle>Activate Coupon Range</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>From #</Label>
              <Input type="number" value={fromN} onChange={e => setFromN(e.target.value)} data-testid="range-from" />
            </div>
            <div>
              <Label>To #</Label>
              <Input type="number" value={toN} onChange={e => setToN(e.target.value)} data-testid="range-to" />
            </div>
          </div>
          {preview && (
            <div className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded p-2 font-mono">
              Range: <b>{preview.fs}</b> … <b>{preview.ts}</b>
            </div>
          )}
          <div className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-900">
            Only coupons currently <b>generated</b> or <b>unused-inactive</b> will be activated.
            Claimed / redeemed / cancelled coupons are protected and skipped.
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={busy} className={GOLD_BTN} data-testid="range-submit">
            {busy ? "Activating…" : "Activate Range"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ═════════════════════════ OWNER: All Coupons list (across batches) ═════════
export function OwnerCouponsListPage() {
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const r = await dms.cpnListCoupons({
        status: status || undefined,
        coupon_type: type || undefined,
        code: q.trim() ? q.trim().toUpperCase() : undefined,
        limit: 500,
      });
      setRows(r.data || []);
    } finally { setBusy(false); }
  }, [status, type, q]);

  useEffect(() => { const h = setTimeout(load, 250); return () => clearTimeout(h); }, [load]);

  return (
    <div>
      <PageHeader title="All Coupons" subtitle="Search across all batches — filter by type, status or exact code" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div>
          <Label>Type</Label>
          <Select value={type || "__all__"} onValueChange={v => setType(v === "__all__" ? "" : v)}>
            <SelectTrigger><SelectValue placeholder="All types" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All types</SelectItem>
              <SelectItem value="cash">Cash</SelectItem>
              <SelectItem value="reward">Reward</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Status</Label>
          <Select value={status || "__all__"} onValueChange={v => setStatus(v === "__all__" ? "" : v)}>
            <SelectTrigger><SelectValue placeholder="All statuses" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All statuses</SelectItem>
              {["generated", "unused", "claimed", "redemption_pending", "redeemed", "expired", "cancelled"]
                .map(s => <SelectItem key={s} value={s}>{s.replace(/_/g, " ")}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="md:col-span-2">
          <Label>Coupon Code (exact)</Label>
          <Input value={q} onChange={e => setQ(e.target.value)} placeholder="e.g. QSRD-9X7K-LA82-MPQ4" />
        </div>
      </div>
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            <TableHead>Code</TableHead><TableHead>Batch</TableHead>
            <TableHead>Type</TableHead><TableHead className="text-right">Value</TableHead>
            <TableHead>Status</TableHead><TableHead>Retailer</TableHead>
            <TableHead>Distributor</TableHead><TableHead>Claimed On</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow><TableCell colSpan={8} className="text-center py-10 text-slate-400">
                {busy ? "Loading…" : "No coupons match"}
              </TableCell></TableRow>
            )}
            {rows.map(c => (
              <TableRow key={c.id}>
                <TableCell className="font-mono text-xs font-semibold">{c.coupon_code}</TableCell>
                <TableCell className="text-xs">{c.batch_label}</TableCell>
                <TableCell><StatusChip s={c.coupon_type} /></TableCell>
                <TableCell className="text-right">
                  {c.coupon_type === "cash" ? inr(c.coupon_value) : `${c.coupon_value} pts`}
                </TableCell>
                <TableCell><StatusChip s={c.status} /></TableCell>
                <TableCell className="text-xs">{c.retailer_name || "—"}</TableCell>
                <TableCell className="text-xs">{c.distributor_name || "—"}</TableCell>
                <TableCell className="text-xs text-slate-500">{c.claim_timestamp ? niceDate(c.claim_timestamp) : "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ═════════════════════════ OWNER / ACCOUNTANT: Redemptions ══════════════════
export function OwnerRedemptionsPage() {
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("pending");
  const [wtype, setWtype] = useState("");
  const [busy, setBusy] = useState(false);
  const [detail, setDetail] = useState(null);
  const [newOpen, setNewOpen] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const r = await dms.cpnListRedemptions({
        status: status || undefined,
        wallet_type: wtype || undefined,
      });
      setRows(r.data || []);
    } finally { setBusy(false); }
  }, [status, wtype]);
  useEffect(() => { load(); }, [load]);

  const approve = async (r) => {
    if (!window.confirm(
      r.wallet_type === "cash"
        ? `Approve ${r.redemption_no}? A Credit Note will be issued for ${inr(r.amount)} and the distributor's outstanding will reduce.`
        : `Approve ${r.redemption_no}? A Dispatch Advice will be issued for ${r.amount} points.`,
    )) return;
    try { await dms.cpnApproveRedemption(r.id); toast.success("Redemption approved"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const reject = async (r) => {
    const reason = window.prompt("Reason for rejection:", "");
    if (reason == null) return;
    try { await dms.cpnRejectRedemption(r.id, reason); toast.success("Rejected"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div>
      <PageHeader
        title="Redemption Requests"
        subtitle="Approve cash → Credit Note, or points → Dispatch Advice. Distributor outstanding reduces only after approval."
        action={
          <Button className={GOLD_BTN} onClick={() => setNewOpen(true)} data-testid="new-red-btn">
            <Plus size={14} className="mr-1" /> New Redemption
          </Button>
        }
      />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div>
          <Label>Status</Label>
          <Select value={status || "__all__"} onValueChange={v => setStatus(v === "__all__" ? "" : v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Type</Label>
          <Select value={wtype || "__all__"} onValueChange={v => setWtype(v === "__all__" ? "" : v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All</SelectItem>
              <SelectItem value="cash">Cash</SelectItem>
              <SelectItem value="reward">Reward</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            <TableHead>Redemption</TableHead><TableHead>Retailer</TableHead>
            <TableHead>Distributor</TableHead><TableHead>Type</TableHead>
            <TableHead className="text-right">Amount</TableHead>
            <TableHead>Status</TableHead><TableHead>Requested</TableHead>
            <TableHead>CN / DA</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow><TableCell colSpan={9} className="text-center py-10 text-slate-400">No requests</TableCell></TableRow>
            )}
            {rows.map(r => (
              <TableRow key={r.id}>
                <TableCell className="font-mono text-xs font-semibold">{r.redemption_no}</TableCell>
                <TableCell>{r.retailer_name}</TableCell>
                <TableCell className="text-xs">{r.distributor_name}</TableCell>
                <TableCell>
                  {r.wallet_type === "cash"
                    ? <span className="text-xs bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded">Cash</span>
                    : <span className="text-xs bg-amber-50 text-amber-800 px-2 py-0.5 rounded">Reward</span>}
                </TableCell>
                <TableCell className="text-right font-semibold">
                  {r.wallet_type === "cash" ? inr(r.amount) : `${r.amount} pts`}
                </TableCell>
                <TableCell><StatusChip s={r.status} /></TableCell>
                <TableCell className="text-xs text-slate-500">{niceDate(r.created_at)}</TableCell>
                <TableCell className="text-xs font-mono">
                  {r.credit_note_no || r.dispatch_advice_no || "—"}
                </TableCell>
                <TableCell className="text-right">
                  {r.status === "pending" ? (
                    <div className="flex gap-1 justify-end">
                      <Button size="sm" className={GOLD_BTN} onClick={() => approve(r)} data-testid={`red-approve-${r.redemption_no}`}>
                        <CheckCircle2 size={14} className="mr-1" /> Approve
                      </Button>
                      <Button size="sm" variant="outline" className="text-rose-700" onClick={() => reject(r)}>
                        Reject
                      </Button>
                    </div>
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => setDetail(r)}>View</Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={!!detail} onOpenChange={o => !o && setDetail(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Redemption {detail?.redemption_no}</DialogTitle></DialogHeader>
          {detail && (
            <div className="space-y-2 text-sm">
              <div><b>Retailer:</b> {detail.retailer_name}</div>
              <div><b>Distributor:</b> {detail.distributor_name}</div>
              <div><b>Type:</b> {detail.wallet_type}</div>
              <div><b>Amount:</b> {detail.wallet_type === "cash" ? inr(detail.amount) : `${detail.amount} pts`}</div>
              <div><b>Status:</b> <StatusChip s={detail.status} /></div>
              {detail.credit_note_no && <div><b>Credit Note:</b> {detail.credit_note_no}</div>}
              {detail.dispatch_advice_no && <div><b>Dispatch Advice:</b> {detail.dispatch_advice_no}</div>}
              {detail.notes && <div className="bg-slate-50 rounded p-2"><b>Notes:</b> {detail.notes}</div>}
              {detail.rejected_reason && <div className="bg-rose-50 rounded p-2"><b>Rejected:</b> {detail.rejected_reason}</div>}
              <div className="text-xs text-slate-500">Created {niceDate(detail.created_at)} · Actioned {niceDate(detail.approved_at)}</div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <NewRedemptionDialog open={newOpen} onClose={() => setNewOpen(false)} onDone={load} />
    </div>
  );
}

function NewRedemptionDialog({ open, onClose, onDone }) {
  const [retailers, setRetailers] = useState([]);
  const [rid, setRid] = useState("");
  const [wtype, setWtype] = useState("cash");
  const [amount, setAmount] = useState("");
  const [notes, setNotes] = useState("");
  const [walletCheck, setWalletCheck] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setRid(""); setWtype("cash"); setAmount(""); setNotes(""); setWalletCheck(null);
      dms.cpnReportsWalletSummary().then(r => setRetailers(r.data || [])).catch(() => setRetailers([]));
    }
  }, [open]);

  useEffect(() => {
    if (!rid) { setWalletCheck(null); return; }
    const row = retailers.find(r => r.retailer_id === rid && r.wallet_type === wtype);
    setWalletCheck(row || { balance: 0 });
  }, [rid, wtype, retailers]);

  const retList = useMemo(() => {
    const seen = new Set(); const out = [];
    retailers.forEach(r => {
      if (!seen.has(r.retailer_id)) { seen.add(r.retailer_id); out.push(r); }
    });
    return out.sort((a, b) => (a.retailer_name || "").localeCompare(b.retailer_name || ""));
  }, [retailers]);

  const submit = async () => {
    if (!rid) { toast.error("Pick a retailer"); return; }
    const v = Number(amount);
    if (!v || v <= 0) { toast.error("Enter amount"); return; }
    setBusy(true);
    try {
      await dms.cpnCreateRedemption({
        retailer_id: rid, wallet_type: wtype,
        amount: v, notes: notes.trim(),
      });
      toast.success("Redemption request created (pending approval)");
      onDone?.(); onClose();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={o => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle>New Redemption Request</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Retailer</Label>
            <Select value={rid} onValueChange={setRid}>
              <SelectTrigger data-testid="new-red-retailer"><SelectValue placeholder="Pick retailer" /></SelectTrigger>
              <SelectContent className="max-h-72">
                {retList.map(r => (
                  <SelectItem key={r.retailer_id} value={r.retailer_id}>
                    {r.retailer_name} <span className="text-xs text-slate-500 ml-1">({r.distributor_name})</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Wallet</Label>
              <Select value={wtype} onValueChange={setWtype}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="cash">Cash</SelectItem>
                  <SelectItem value="reward">Reward</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Amount</Label>
              <Input type="number" min={1} value={amount} onChange={e => setAmount(e.target.value)} data-testid="new-red-amount" />
            </div>
          </div>
          {walletCheck && (
            <div className="text-xs bg-slate-50 rounded p-2">
              Available balance:{" "}
              <b>{wtype === "cash" ? inr(walletCheck.balance) : `${walletCheck.balance} pts`}</b>
            </div>
          )}
          <div>
            <Label>Notes</Label>
            <Textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={busy} className={GOLD_BTN} data-testid="new-red-submit">
            {busy ? "Creating…" : "Create Request"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ═════════════════════════ OWNER: Credit Notes + Dispatch Advices ═══════════
export function OwnerCreditNotesPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => { dms.cpnCreditNotes().then(r => setRows(r.data || [])); }, []);
  return (
    <div>
      <PageHeader title="Credit Notes" subtitle="Issued on cash coupon redemption approval — automatically reduces distributor outstanding" />
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            <TableHead>CN No.</TableHead><TableHead>Redemption</TableHead>
            <TableHead>Retailer</TableHead><TableHead>Distributor</TableHead>
            <TableHead className="text-right">Amount</TableHead>
            <TableHead>Issued</TableHead><TableHead>By</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={7} className="text-center py-10 text-slate-400">No credit notes yet</TableCell></TableRow>}
            {rows.map(r => (
              <TableRow key={r.id}>
                <TableCell className="font-mono text-xs font-semibold">{r.cn_no}</TableCell>
                <TableCell className="font-mono text-xs">{r.redemption_no}</TableCell>
                <TableCell>{r.retailer_name}</TableCell>
                <TableCell className="text-xs">{r.distributor_name}</TableCell>
                <TableCell className="text-right font-semibold">{inr(r.amount)}</TableCell>
                <TableCell className="text-xs text-slate-500">{niceDate(r.issued_at)}</TableCell>
                <TableCell className="text-xs">{r.issued_by_name}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

export function OwnerDispatchAdvicesPage() {
  const [rows, setRows] = useState([]);
  const load = () => dms.cpnDispatchAdvices().then(r => setRows(r.data || []));
  useEffect(() => { load(); }, []);
  const markSent = async (id) => {
    if (!window.confirm("Mark this Dispatch Advice as dispatched?")) return;
    try { await dms.cpnMarkDispatched(id); toast.success("Marked dispatched"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  return (
    <div>
      <PageHeader title="Dispatch Advices" subtitle="Issued on reward points redemption — free stock to be sent to distributor" />
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            <TableHead>DA No.</TableHead><TableHead>Redemption</TableHead>
            <TableHead>Retailer</TableHead><TableHead>Distributor</TableHead>
            <TableHead className="text-right">Points</TableHead>
            <TableHead>Status</TableHead><TableHead>Issued</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={8} className="text-center py-10 text-slate-400">No dispatch advices</TableCell></TableRow>}
            {rows.map(r => (
              <TableRow key={r.id}>
                <TableCell className="font-mono text-xs font-semibold">{r.da_no}</TableCell>
                <TableCell className="font-mono text-xs">{r.redemption_no}</TableCell>
                <TableCell>{r.retailer_name}</TableCell>
                <TableCell className="text-xs">{r.distributor_name}</TableCell>
                <TableCell className="text-right font-semibold">{r.points} pts</TableCell>
                <TableCell><StatusChip s={r.status} /></TableCell>
                <TableCell className="text-xs text-slate-500">{niceDate(r.issued_at)}</TableCell>
                <TableCell className="text-right">
                  {r.status === "issued" && (
                    <Button size="sm" className={GOLD_BTN} onClick={() => markSent(r.id)}>
                      <Truck size={14} className="mr-1" /> Mark Dispatched
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ═════════════════════════ OWNER: Reports + Audit Log ═══════════════════════
export function OwnerCouponReportsPage() {
  const [tab, setTab] = useState("wallets");
  const [wallets, setWallets] = useState([]);
  const [sp, setSp] = useState([]);
  const [fraud, setFraud] = useState([]);
  const [dup, setDup] = useState([]);

  useEffect(() => {
    dms.cpnReportsWalletSummary().then(r => setWallets(r.data || []));
    dms.cpnReportsSalesperson().then(r => setSp(r.data || []));
    dms.cpnReportsFraud().then(r => setFraud(r.data || []));
    dms.cpnReportsDuplicate().then(r => setDup(r.data || []));
  }, []);

  const tabs = [
    { id: "wallets", label: "Retailer Wallets" },
    { id: "salesperson", label: "Sales Officer Performance" },
    { id: "duplicate", label: `Duplicate Scans${dup.length ? ` (${dup.length})` : ""}` },
    { id: "fraud", label: `Fraud Attempts${fraud.length ? ` (${fraud.length})` : ""}` },
  ];

  return (
    <div>
      <PageHeader title="Coupon Reports" subtitle="Wallet summary, Sales Officer performance, and fraud logs" />
      <Tabs tabs={tabs} value={tab} onChange={setTab} />

      {tab === "wallets" && (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>Retailer</TableHead><TableHead>Distributor</TableHead>
              <TableHead>Wallet</TableHead><TableHead className="text-right">Balance</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {wallets.length === 0 && <TableRow><TableCell colSpan={4} className="text-center py-10 text-slate-400">No wallets yet</TableCell></TableRow>}
              {wallets.map((w, i) => (
                <TableRow key={i}>
                  <TableCell>{w.retailer_name}</TableCell>
                  <TableCell className="text-xs">{w.distributor_name}</TableCell>
                  <TableCell>
                    {w.wallet_type === "cash"
                      ? <span className="text-xs bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded">Cash</span>
                      : <span className="text-xs bg-amber-50 text-amber-800 px-2 py-0.5 rounded">Reward</span>}
                  </TableCell>
                  <TableCell className="text-right font-bold">
                    {w.wallet_type === "cash" ? inr(w.balance) : `${w.balance} pts`}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {tab === "salesperson" && (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>Sales Officer</TableHead>
              <TableHead className="text-right">Total Scans</TableHead>
              <TableHead className="text-right">Cash Value</TableHead>
              <TableHead className="text-right">Reward Points</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {sp.length === 0 && <TableRow><TableCell colSpan={4} className="text-center py-10 text-slate-400">No scans yet</TableCell></TableRow>}
              {sp.map((r, i) => (
                <TableRow key={r.salesperson_id}>
                  <TableCell>{i === 0 && <Trophy size={12} className="inline mr-1 text-amber-500" />}{r.salesperson_name}</TableCell>
                  <TableCell className="text-right font-semibold">{r.scans}</TableCell>
                  <TableCell className="text-right">{inr(r.cash_value)}</TableCell>
                  <TableCell className="text-right">{r.reward_points} pts</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {tab === "duplicate" && <FraudTable rows={dup} />}
      {tab === "fraud" && <FraudTable rows={fraud} />}
    </div>
  );
}

function FraudTable({ rows }) {
  return (
    <Card className="overflow-x-auto">
      <Table>
        <TableHeader><TableRow>
          <TableHead>When</TableHead><TableHead>Coupon</TableHead>
          <TableHead>Reason</TableHead><TableHead>By</TableHead>
          <TableHead>Retailer</TableHead><TableHead>Distributor</TableHead>
        </TableRow></TableHeader>
        <TableBody>
          {rows.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-slate-400">✓ No entries</TableCell></TableRow>}
          {rows.map(f => (
            <TableRow key={f.id} className="bg-rose-50/20">
              <TableCell className="text-xs text-slate-500">{niceDate(f.at)}</TableCell>
              <TableCell className="font-mono text-xs">{f.coupon_code}</TableCell>
              <TableCell>
                <span className="text-xs px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 font-semibold">
                  {f.reason.replace(/_/g, " ")}
                </span>
              </TableCell>
              <TableCell className="text-xs">{f.actor_name} <span className="text-slate-400">({f.actor_role})</span></TableCell>
              <TableCell className="text-xs font-mono">{f.retailer_id || "—"}</TableCell>
              <TableCell className="text-xs font-mono">{f.distributor_id || "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

export function OwnerCouponAuditLogPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => { dms.cpnAuditLog().then(r => setRows(r.data || [])); }, []);
  return (
    <div>
      <PageHeader title="Coupon Audit Log" subtitle="Immutable audit trail — every state change is recorded" />
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            <TableHead>When</TableHead><TableHead>Event</TableHead>
            <TableHead>Entity</TableHead><TableHead>Actor</TableHead>
            <TableHead>Details</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={5} className="text-center py-10 text-slate-400">No entries</TableCell></TableRow>}
            {rows.map(r => (
              <TableRow key={r.id}>
                <TableCell className="text-xs text-slate-500 whitespace-nowrap">{niceDate(r.at)}</TableCell>
                <TableCell className="text-xs font-semibold">{r.event}</TableCell>
                <TableCell className="text-xs">{r.entity_type} <span className="font-mono text-slate-500">{(r.entity_id || "").slice(0, 12)}</span></TableCell>
                <TableCell className="text-xs">{r.actor_name} <span className="text-slate-400">({r.actor_role})</span></TableCell>
                <TableCell className="text-[11px] text-slate-600">
                  <pre className="whitespace-pre-wrap font-mono">{JSON.stringify(r.details || {}, null, 0)}</pre>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ═════════════════════════ SALES OFFICER: Scan Flow ═════════════════════════
export function SalesOfficerScanPage() {
  const [retailers, setRetailers] = useState([]);
  const [selectedRid, setSelectedRid] = useState("");
  const [code, setCode] = useState("");
  const [qrPayload, setQrPayload] = useState("");
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState(null);
  const [search, setSearch] = useState("");
  const [gps, setGps] = useState(null);   // { lat, lng }

  useEffect(() => {
    dms.cpnSoRetailers().then(r => setRetailers(r.data || []))
      .catch(() => toast.error("Failed to load retailers"));
    // best-effort geolocation on mount — permission handled by browser
    if (typeof navigator !== "undefined" && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => setGps({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => setGps(null),
        { maximumAge: 60_000, timeout: 5_000, enableHighAccuracy: false },
      );
    }
  }, []);

  // stable device fingerprint stored in localStorage
  const deviceId = useMemo(() => {
    try {
      let d = window.localStorage.getItem("gooil_device_id");
      if (!d) {
        d = "dev-" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
        window.localStorage.setItem("gooil_device_id", d);
      }
      return d;
    } catch { return null; }
  }, []);

  const selectedRet = useMemo(
    () => retailers.find(r => r.id === selectedRid),
    [retailers, selectedRid],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return retailers;
    return retailers.filter(r =>
      (r.name || "").toLowerCase().includes(q)
      || (r.phone || "").includes(q)
      || (r.city || "").toLowerCase().includes(q)
      || (r.shop_name || "").toLowerCase().includes(q),
    );
  }, [retailers, search]);

  const scan = async (payloadOverride) => {
    if (!selectedRid) { toast.error("Select a retailer first"); return; }
    const cCode = (code || "").trim().toUpperCase();
    const qr = (payloadOverride ?? qrPayload).trim();
    if (!qr && !cCode) { toast.error("Enter coupon code or paste QR"); return; }
    setBusy(true); setLast(null);
    try {
      const r = await dms.cpnScan({
        retailer_id: selectedRid,
        qr_payload: qr || undefined,
        coupon_code: cCode || undefined,
        gps_lat: gps?.lat,
        gps_lng: gps?.lng,
        device_id: deviceId,
      });
      setLast({ ok: true, ...r });
      toast.success(r.message);
      setCode(""); setQrPayload("");
    } catch (e) {
      const msg = e?.response?.data?.detail || "Scan failed";
      setLast({ ok: false, message: msg });
      toast.error(msg);
    } finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader
        title="Scan Coupon"
        subtitle="Select retailer → distributor auto-fetched → scan QR or type code. Balance credits to retailer's wallet."
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* LEFT: Retailer picker */}
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <Store className="text-[#a67c00]" size={18} />
            <h3 className="font-bold text-slate-900">Step 1 · Select Retailer</h3>
          </div>
          <div className="relative mb-3">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search retailer" className="pl-9" data-testid="so-search" />
          </div>
          <div className="max-h-80 overflow-y-auto rounded border border-slate-100 divide-y divide-slate-50">
            {filtered.length === 0 && (
              <div className="p-6 text-center text-sm text-slate-400">
                No retailers assigned. Ask Owner/TL to assign you a distributor.
              </div>
            )}
            {filtered.map(r => (
              <button key={r.id}
                      onClick={() => setSelectedRid(r.id)}
                      className={`w-full text-left px-3 py-2 hover:bg-amber-50/50 flex items-center gap-2 ${selectedRid === r.id ? "bg-amber-50" : ""}`}
                      data-testid={`so-ret-${r.id}`}>
                <div className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold ${selectedRid === r.id ? "bg-[#c9a227] text-white" : "bg-slate-100 text-slate-700"}`}>
                  {(r.name || "?")[0]?.toUpperCase()}
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-sm text-slate-900">{r.name}</div>
                  <div className="text-[11px] text-slate-500">{r.shop_name} · {r.city} · {r.phone}</div>
                </div>
                <div className="text-[10px] text-slate-500 text-right">
                  <div>Distributor</div>
                  <div className="font-semibold">{r.distributor_name || "—"}</div>
                </div>
              </button>
            ))}
          </div>

          {selectedRet && (
            <div className="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded text-sm">
              <div className="font-semibold text-emerald-900 flex items-center gap-1"><CheckCircle2 size={14} /> Selected</div>
              <div><b>{selectedRet.name}</b> — {selectedRet.shop_name || "Retailer"}</div>
              <div className="text-xs text-slate-600">Distributor auto-fetched: <b>{selectedRet.distributor_name}</b></div>
            </div>
          )}
        </Card>

        {/* RIGHT: Scan */}
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <ScanLine className="text-[#a67c00]" size={18} />
            <h3 className="font-bold text-slate-900">Step 2 · Scan / Enter Coupon</h3>
          </div>

          <Label>QR Payload (paste from scanner)</Label>
          <div className="flex gap-2 mt-1 mb-3">
            <Input value={qrPayload} onChange={e => setQrPayload(e.target.value)}
                   placeholder="GOOIL:XXXX-XXXX-XXXX-XXXX:token:signature"
                   onKeyDown={e => e.key === "Enter" && scan()}
                   data-testid="so-qr-input" />
            <Button className={GOLD_BTN} disabled={busy || !selectedRid || !qrPayload.trim()}
                    onClick={() => scan()} data-testid="so-qr-scan">
              {busy ? "…" : "Scan"}
            </Button>
          </div>

          <div className="relative flex items-center py-2">
            <div className="flex-grow border-t border-slate-200"></div>
            <span className="mx-3 text-xs text-slate-400">OR enter manually</span>
            <div className="flex-grow border-t border-slate-200"></div>
          </div>

          <Label>Coupon Code</Label>
          <div className="flex gap-2 mt-1">
            <Input value={code} onChange={e => setCode(e.target.value.toUpperCase())}
                   placeholder="XXXX-XXXX-XXXX-XXXX"
                   onKeyDown={e => e.key === "Enter" && scan()}
                   data-testid="so-code-input" className="font-mono" />
            <Button className={GOLD_BTN} disabled={busy || !selectedRid || !code.trim()}
                    onClick={() => scan()} data-testid="so-code-scan">
              Scan
            </Button>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Manual entry skips signature check. QR path is the secure default.
          </p>

          {last && (
            <div className={`mt-4 p-4 rounded-lg border ${last.ok ? "bg-emerald-50 border-emerald-300" : "bg-rose-50 border-rose-300"}`}
                 data-testid="so-result">
              <div className="flex items-start gap-2">
                {last.ok
                  ? <CheckCircle2 size={22} className="text-emerald-600 mt-0.5" />
                  : <XCircle size={22} className="text-rose-600 mt-0.5" />}
                <div className="flex-1">
                  <div className={`font-semibold ${last.ok ? "text-emerald-900" : "text-rose-900"}`}>
                    {last.ok ? "Coupon Claimed" : "Scan Rejected"}
                  </div>
                  {last.ok && (
                    <div className="text-sm mt-1 space-y-1">
                      <div><span className="font-mono font-bold">{last.coupon_code}</span></div>
                      <div>
                        {last.coupon_type === "cash" ? (
                          <>+<b className="text-emerald-700">{inr(last.coupon_value)}</b> to Cash Wallet</>
                        ) : (
                          <>+<b className="text-emerald-700">{last.coupon_value} pts</b> to Reward Wallet</>
                        )}
                      </div>
                      <div className="text-xs text-slate-600">Retailer: {last.retailer_name} · Distributor: {last.distributor_name}</div>
                      <div className="text-xs">New {last.wallet_type} balance: <b>{last.wallet_type === "cash" ? inr(last.new_balance) : `${last.new_balance} pts`}</b></div>
                    </div>
                  )}
                  {!last.ok && <div className="text-sm text-slate-700 mt-1">{last.message}</div>}
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

// ═════════════════════════ RETAILER: Wallet & History (view-only) ═══════════
export function RetailerWalletPage() {
  const [wallet, setWallet] = useState(null);
  const [tab, setTab] = useState("cash");
  const [txs, setTxs] = useState([]);
  const [coupons, setCoupons] = useState([]);
  const [reds, setReds] = useState([]);

  const load = useCallback(() => {
    dms.cpnRetailerWallet().then(setWallet).catch(() => {});
    dms.cpnRetailerTransactions().then(r => setTxs(r.data || []));
    dms.cpnRetailerCoupons().then(r => setCoupons(r.data || []));
    dms.cpnRetailerRedemptions().then(r => setReds(r.data || []));
  }, []);
  useEffect(() => { load(); }, [load]);

  const wCash = wallet?.cash_wallet || {};
  const wRew = wallet?.reward_wallet || {};

  return (
    <div>
      <PageHeader
        title="My Wallets & Coupons"
        subtitle="Cash & Reward wallets are credited when a Sales Officer scans a coupon for you"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        <Card className="p-5 bg-gradient-to-br from-emerald-50 to-white border-emerald-200">
          <div className="flex items-center gap-2 mb-3">
            <Coins className="text-emerald-700" size={20} />
            <h3 className="font-bold text-slate-900">Cash Wallet</h3>
          </div>
          <div className="text-3xl font-bold text-emerald-800">{inr(wCash.balance || 0)}</div>
          {wCash.pending_redemptions > 0 && (
            <div className="text-xs text-amber-800 mt-2">
              {wCash.pending_redemptions} redemption(s) pending approval
            </div>
          )}
          <div className="text-xs text-slate-500 mt-3">Redeemed as Credit Note against your distributor&apos;s outstanding — approved by Owner/Accountant.</div>
        </Card>

        <Card className="p-5 bg-gradient-to-br from-amber-50 to-white border-amber-200">
          <div className="flex items-center gap-2 mb-3">
            <Award className="text-[#a67c00]" size={20} />
            <h3 className="font-bold text-slate-900">Reward Points Wallet</h3>
          </div>
          <div className="text-3xl font-bold text-[#8a6600]">{(wRew.balance || 0).toLocaleString("en-IN")} <span className="text-lg font-normal">pts</span></div>
          {wRew.pending_redemptions > 0 && (
            <div className="text-xs text-amber-800 mt-2">
              {wRew.pending_redemptions} redemption(s) pending approval
            </div>
          )}
          <div className="text-xs text-slate-500 mt-3">Redeemed as free stock via Dispatch Advice — approved by Owner.</div>
        </Card>
      </div>

      <Tabs
        tabs={[
          { id: "cash", label: "Cash Transactions", badge: txs.filter(t => t.wallet_type === "cash").length },
          { id: "reward", label: "Reward Transactions", badge: txs.filter(t => t.wallet_type === "reward").length },
          { id: "coupons", label: "My Coupons", badge: coupons.length },
          { id: "redemptions", label: "Redemptions", badge: reds.length },
        ]}
        value={tab} onChange={setTab}
      />

      {(tab === "cash" || tab === "reward") && (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>When</TableHead><TableHead>Type</TableHead>
              <TableHead>Coupon / Reference</TableHead>
              <TableHead>By</TableHead>
              <TableHead className="text-right">Amount</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {txs.filter(t => t.wallet_type === tab).length === 0 && (
                <TableRow><TableCell colSpan={5} className="text-center py-10 text-slate-400">No transactions</TableCell></TableRow>
              )}
              {txs.filter(t => t.wallet_type === tab).map(t => (
                <TableRow key={t.id}>
                  <TableCell className="text-xs text-slate-500 whitespace-nowrap">{niceDate(t.at)}</TableCell>
                  <TableCell>
                    {t.kind === "credit_coupon"
                      ? <span className="text-xs bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded">CREDIT · Coupon</span>
                      : <span className="text-xs bg-rose-50 text-rose-800 px-2 py-0.5 rounded">DEBIT · Redemption</span>}
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {t.coupon_code || t.credit_note_no || t.dispatch_advice_no || "—"}
                  </TableCell>
                  <TableCell className="text-xs">{t.created_by_name}</TableCell>
                  <TableCell className={`text-right font-bold ${t.amount >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                    {t.wallet_type === "cash"
                      ? `${t.amount >= 0 ? "+" : ""}${inr(Math.abs(t.amount))}`
                      : `${t.amount >= 0 ? "+" : "-"}${Math.abs(t.amount)} pts`}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {tab === "coupons" && (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>Code</TableHead><TableHead>Type</TableHead>
              <TableHead className="text-right">Value</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Claimed On</TableHead><TableHead>By</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {coupons.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-slate-400">No coupons yet</TableCell></TableRow>}
              {coupons.map(c => (
                <TableRow key={c.id}>
                  <TableCell className="font-mono text-xs">{c.coupon_code}</TableCell>
                  <TableCell><StatusChip s={c.coupon_type} /></TableCell>
                  <TableCell className="text-right font-semibold">
                    {c.coupon_type === "cash" ? inr(c.coupon_value) : `${c.coupon_value} pts`}
                  </TableCell>
                  <TableCell><StatusChip s={c.status} /></TableCell>
                  <TableCell className="text-xs text-slate-500">{niceDate(c.claim_timestamp)}</TableCell>
                  <TableCell className="text-xs">{c.claimed_by_user_name}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {tab === "redemptions" && (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>Redemption</TableHead><TableHead>Type</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>CN / DA</TableHead>
              <TableHead>Requested</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {reds.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-slate-400">No redemptions</TableCell></TableRow>}
              {reds.map(r => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono text-xs">{r.redemption_no}</TableCell>
                  <TableCell><StatusChip s={r.wallet_type} /></TableCell>
                  <TableCell className="text-right font-semibold">
                    {r.wallet_type === "cash" ? inr(r.amount) : `${r.amount} pts`}
                  </TableCell>
                  <TableCell><StatusChip s={r.status} /></TableCell>
                  <TableCell className="font-mono text-xs">{r.credit_note_no || r.dispatch_advice_no || "—"}</TableCell>
                  <TableCell className="text-xs text-slate-500">{niceDate(r.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}

// ═════════════════════════ DISTRIBUTOR: Wallets + CN + DA (view-only) ═══════
export function DistributorCouponsPage() {
  const [summary, setSummary] = useState(null);
  const [tab, setTab] = useState("retailers");
  const [cns, setCns] = useState([]);
  const [das, setDas] = useState([]);
  const [reds, setReds] = useState([]);

  useEffect(() => {
    dms.cpnDistSummary().then(setSummary).catch(() => {});
    dms.cpnDistCreditNotes().then(r => setCns(r.data || []));
    dms.cpnDistDispatchAdvices().then(r => setDas(r.data || []));
    dms.cpnListRedemptions().then(r => setReds(r.data || []));
  }, []);

  return (
    <div>
      <PageHeader title="Coupon Rewards" subtitle="View retailer wallets, credit notes and dispatch advices for your network" />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <Kpi label="Retailers" value={summary?.retailers?.length || 0} icon={Store} />
        <Kpi label="Credit Notes" value={summary?.credit_notes_count || 0} icon={FileText} />
        <Kpi label="Redemption Pending" value={summary?.pending_redemptions || 0} tint="bg-amber-50 text-amber-700" icon={Activity} />
        <Kpi label="Approved" value={summary?.approved_redemptions || 0} tint="bg-emerald-50 text-emerald-700" icon={CheckCircle2} />
      </div>

      <Tabs tabs={[
        { id: "retailers", label: "Retailer Wallets" },
        { id: "redemptions", label: "Redemptions" },
        { id: "credit", label: "Credit Notes" },
        { id: "dispatch", label: "Dispatch Advices" },
      ]} value={tab} onChange={setTab} />

      {tab === "retailers" && (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>Retailer</TableHead>
              <TableHead className="text-right">Cash Wallet</TableHead>
              <TableHead className="text-right">Reward Wallet</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {(summary?.retailers || []).length === 0
                && <TableRow><TableCell colSpan={3} className="text-center py-10 text-slate-400">No retailers</TableCell></TableRow>}
              {(summary?.retailers || []).map(r => (
                <TableRow key={r.retailer_id}>
                  <TableCell className="font-semibold">{r.retailer_name}</TableCell>
                  <TableCell className="text-right font-semibold text-emerald-700">{inr(r.cash_balance)}</TableCell>
                  <TableCell className="text-right font-semibold text-[#8a6600]">{r.reward_balance} pts</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {tab === "redemptions" && (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>Redemption</TableHead><TableHead>Retailer</TableHead>
              <TableHead>Type</TableHead><TableHead className="text-right">Amount</TableHead>
              <TableHead>Status</TableHead><TableHead>CN / DA</TableHead>
              <TableHead>When</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {reds.length === 0 && <TableRow><TableCell colSpan={7} className="text-center py-10 text-slate-400">No redemptions</TableCell></TableRow>}
              {reds.map(r => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono text-xs">{r.redemption_no}</TableCell>
                  <TableCell>{r.retailer_name}</TableCell>
                  <TableCell><StatusChip s={r.wallet_type} /></TableCell>
                  <TableCell className="text-right font-semibold">
                    {r.wallet_type === "cash" ? inr(r.amount) : `${r.amount} pts`}
                  </TableCell>
                  <TableCell><StatusChip s={r.status} /></TableCell>
                  <TableCell className="font-mono text-xs">{r.credit_note_no || r.dispatch_advice_no || "—"}</TableCell>
                  <TableCell className="text-xs text-slate-500">{niceDate(r.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {tab === "credit" && (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>CN No.</TableHead><TableHead>Retailer</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Issued</TableHead><TableHead>Redemption</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {cns.length === 0 && <TableRow><TableCell colSpan={5} className="text-center py-10 text-slate-400">No credit notes</TableCell></TableRow>}
              {cns.map(r => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono text-xs font-semibold">{r.cn_no}</TableCell>
                  <TableCell>{r.retailer_name}</TableCell>
                  <TableCell className="text-right font-bold text-emerald-700">{inr(r.amount)}</TableCell>
                  <TableCell className="text-xs text-slate-500">{niceDate(r.issued_at)}</TableCell>
                  <TableCell className="font-mono text-xs">{r.redemption_no}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {tab === "dispatch" && (
        <Card className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow>
              <TableHead>DA No.</TableHead><TableHead>Retailer</TableHead>
              <TableHead className="text-right">Points</TableHead>
              <TableHead>Status</TableHead><TableHead>Issued</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {das.length === 0 && <TableRow><TableCell colSpan={5} className="text-center py-10 text-slate-400">No dispatch advices</TableCell></TableRow>}
              {das.map(r => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono text-xs font-semibold">{r.da_no}</TableCell>
                  <TableCell>{r.retailer_name}</TableCell>
                  <TableCell className="text-right font-bold text-[#8a6600]">{r.points} pts</TableCell>
                  <TableCell><StatusChip s={r.status} /></TableCell>
                  <TableCell className="text-xs text-slate-500">{niceDate(r.issued_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}


// ═════════════════════════ OWNER: Fraud Detection Dashboard ═════════════════
const FRAUD_REASON_LABELS = {
  invalid_code: "Invalid Code (unknown QR)",
  invalid_signature: "Wrong Digital Signature",
  invalid_encryption: "Invalid Encryption / Tampered",
  invalid_hidden_id: "Invalid Hidden Secure ID",
  modified_payload: "Modified / Malformed Payload",
  wrong_version: "Unsupported / Wrong Version",
  wrong_campaign: "QR from Another Campaign",
  online_generator_suspected: "Online Generator (Fake QR)",
  inactive_batch: "QR from Inactive Batch",
  already_claimed: "Already Claimed",
  race_lost: "Race Condition (Concurrent)",
  cancelled: "Coupon Cancelled",
  expired: "Coupon Expired",
  coupon_inactive: "Coupon Inactive",
  so_not_assigned_to_distributor: "SO not assigned to Distributor",
  batch_inactive: "Batch Inactive (legacy)",
  malformed_qr: "Malformed QR (legacy)",
  invalid_token: "Invalid Token (legacy)",
};

export function OwnerFraudDashboardPage() {
  const [dash, setDash] = useState(null);
  const [rows, setRows] = useState([]);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [d, list] = await Promise.all([
        dms.cpnFraudDashboard(),
        dms.cpnReportsFraudFiltered(reason ? { reason } : {}),
      ]);
      setDash(d); setRows(list.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load fraud dashboard");
    } finally { setBusy(false); }
  }, [reason]);

  useEffect(() => { load(); }, [load]);

  const k = dash?.kpis || {};
  const byReason = dash?.by_reason || {};
  const byDist = dash?.by_distributor || [];
  const byActor = dash?.by_actor || [];

  return (
    <div>
      <PageHeader
        title="Fraud Detection Dashboard"
        subtitle="Real-time monitoring of failed coupon scans and suspicious QR activity"
        action={<Button variant="outline" onClick={load} disabled={busy}><RefreshCw size={14} className="mr-1" /> Refresh</Button>}
      />

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <Kpi label="Today" value={k.today || 0} tint="bg-rose-100 text-rose-800" icon={ShieldAlert} />
        <Kpi label="Last 7 days" value={k.last7 || 0} tint="bg-orange-100 text-orange-800" icon={AlertTriangle} />
        <Kpi label="Last 30 days" value={k.last30 || 0} tint="bg-amber-100 text-amber-800" icon={Activity} />
        <Kpi label="All-time Total" value={k.total || 0} tint="bg-slate-200 text-slate-800" icon={Shield} />
      </div>

      {/* By reason + By distributor + By actor */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-5">
        <Card className="p-4">
          <div className="text-xs uppercase text-slate-500 font-semibold mb-3">By Reason</div>
          {Object.keys(byReason).length === 0 ? (
            <div className="text-sm text-slate-400 py-4 text-center">No fraud attempts recorded</div>
          ) : (
            <div className="space-y-1.5">
              {Object.entries(byReason).map(([r, n]) => {
                const max = Math.max(...Object.values(byReason));
                const pct = max ? Math.round((n / max) * 100) : 0;
                return (
                  <div key={r}>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-700">{FRAUD_REASON_LABELS[r] || r}</span>
                      <span className="font-semibold text-slate-900">{n}</span>
                    </div>
                    <div className="h-1.5 bg-slate-100 rounded overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-rose-400 to-rose-600"
                           style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="p-4">
          <div className="text-xs uppercase text-slate-500 font-semibold mb-3">Top Distributors (fraud attempts)</div>
          {byDist.length === 0 ? (
            <div className="text-sm text-slate-400 py-4 text-center">No distributor data</div>
          ) : (
            <div className="space-y-1.5">
              {byDist.slice(0, 8).map(r => (
                <div key={r.distributor_id} className="flex items-center justify-between text-xs">
                  <span className="text-slate-700">{r.distributor_name || r.distributor_id}</span>
                  <span className="font-semibold text-slate-900">{r.count}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-4">
          <div className="text-xs uppercase text-slate-500 font-semibold mb-3">Top Actors (fraud attempts)</div>
          {byActor.length === 0 ? (
            <div className="text-sm text-slate-400 py-4 text-center">No actor data</div>
          ) : (
            <div className="space-y-1.5">
              {byActor.slice(0, 8).map(r => (
                <div key={r.actor_id} className="flex items-center justify-between text-xs">
                  <span className="text-slate-700">
                    {r.actor_name || r.actor_id} <span className="text-slate-400">({r.actor_role || "—"})</span>
                  </span>
                  <span className="font-semibold text-slate-900">{r.count}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Recent fraud attempts table */}
      <Card className="overflow-x-auto">
        <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-slate-900">All Fraud Attempts</span>
          <div className="ml-auto flex items-center gap-2">
            <Select value={reason || "__all__"} onValueChange={v => setReason(v === "__all__" ? "" : v)}>
              <SelectTrigger className="w-64"><SelectValue placeholder="All reasons" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All reasons</SelectItem>
                {Object.entries(FRAUD_REASON_LABELS).map(([v, l]) => (
                  <SelectItem key={v} value={v}>{l}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>When</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Coupon / Serial</TableHead>
              <TableHead>Actor</TableHead>
              <TableHead>Retailer</TableHead>
              <TableHead>Distributor</TableHead>
              <TableHead>IP</TableHead>
              <TableHead>GPS</TableHead>
              <TableHead>Device</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow><TableCell colSpan={9} className="text-center py-10 text-slate-400">
                No fraud attempts {reason ? `matching this reason` : `on record`}
              </TableCell></TableRow>
            )}
            {rows.map(r => (
              <TableRow key={r.id}>
                <TableCell className="text-xs text-slate-500">{niceDate(r.at)}</TableCell>
                <TableCell>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 font-semibold">
                    {FRAUD_REASON_LABELS[r.reason] || r.reason}
                  </span>
                </TableCell>
                <TableCell className="font-mono text-xs">{r.coupon_code || "—"}</TableCell>
                <TableCell className="text-xs">
                  {r.actor_name || "—"} <span className="text-slate-400">({r.actor_role || "—"})</span>
                </TableCell>
                <TableCell className="text-xs">{r.retailer_id || "—"}</TableCell>
                <TableCell className="text-xs">{r.distributor_id || "—"}</TableCell>
                <TableCell className="text-xs font-mono">{r.ip_address || "—"}</TableCell>
                <TableCell className="text-xs">
                  {r.gps_lat && r.gps_lng ? `${Number(r.gps_lat).toFixed(3)}, ${Number(r.gps_lng).toFixed(3)}` : "—"}
                </TableCell>
                <TableCell className="text-xs font-mono">{r.device_id ? String(r.device_id).slice(0, 12) : "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
