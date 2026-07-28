import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import StatusPill from "@/components/common/StatusPill";
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
import { CreditCard, Wallet, Gift, Ticket, TicketCheck, ShoppingCart, ScrollText, GitCompareArrows, CheckCircle2, XCircle, RotateCcw, Plus, Loader2 } from "lucide-react";

// ==========================================================
// PAYMENTS
// ==========================================================
export function PaymentsFinancePage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [reload, setReload] = useState(0);

  const load = () => {
    setLoading(true);
    api.get("/collections/payments").then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [reload]);

  const reverse = async (id) => {
    try {
      await api.post(`/finance/payments/${id}/reverse`, { reason: "Reversal" });
      toast.success("Payment reversed — outstanding restored");
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Finance", "Payments"]}
        title="Payments"
        subtitle="Record, allocate and reverse payments — auto-updates outstanding + double-entry ledger"
        actions={
          <RecordPaymentDialog open={open} onOpenChange={setOpen} onDone={() => setReload((v) => v + 1)} />
        }
      />
      <DataTable
        data={rows}
        loading={loading}
        testId="payments-table"
        pageSize={12}
        columns={[
          { key: "payment_no", label: "Payment" },
          { key: "party_name", label: "Party" },
          { key: "party_type", label: "Type", type: "chip" },
          { key: "mode", label: "Method", type: "chip" },
          { key: "reference", label: "Reference" },
          { key: "amount", label: "Amount", type: "currency", align: "right" },
          { key: "allocations", label: "Allocations", render: (r) => (
            <span className="text-xs text-ink-muted">
              {(r.allocations || []).length} invoice{(r.allocations || []).length === 1 ? "" : "s"}
              {r.unallocated > 0 && <span className="text-amber-700 ml-1">· ${r.unallocated?.toLocaleString()} unallocated</span>}
            </span>
          ) },
          { key: "status", label: "Status", type: "status" },
          { key: "received_on", label: "Received", type: "date" },
          { key: "actions", label: "", render: (r) => (
            r.status !== "Reversed" ? (
              <Button size="sm" variant="outline" className="h-8 border-rose-200 text-rose-700 hover:bg-rose-50"
                onClick={() => reverse(r.id)} data-testid={`reverse-${r.id}`}>
                <RotateCcw size={13} className="mr-1" /> Reverse
              </Button>
            ) : <span className="text-xs text-ink-muted">Reversed</span>
          )},
        ]}
      />
    </div>
  );
}

function RecordPaymentDialog({ open, onOpenChange, onDone }) {
  const [parties, setParties] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [form, setForm] = useState({
    party_type: "distributor", party_id: "", amount: 0, method: "Bank Transfer",
    reference: "", transaction_no: "", notes: "", invoice_ids: [],
  });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    const coll = form.party_type === "distributor" ? "distributors" : (form.party_type === "retailer" ? "retailers" : "customers");
    api.get(`/collections/${coll}?limit=200`).then((r) => setParties(r.data.data || []));
  }, [open, form.party_type]);

  useEffect(() => {
    if (!form.party_id) { setInvoices([]); return; }
    api.get(`/collections/invoices?limit=200`).then((r) => {
      const all = r.data.data || [];
      setInvoices(all.filter((i) => i.party_id === form.party_id && (i.paid || 0) < (i.total || 0)));
    });
  }, [form.party_id]);

  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/finance/payments", {
        party_id: form.party_id, party_type: form.party_type,
        amount: parseFloat(form.amount), method: form.method,
        reference: form.reference, transaction_no: form.transaction_no, notes: form.notes,
        invoice_ids: form.invoice_ids,
      });
      toast.success("Payment recorded — allocated + ledger posted");
      onOpenChange(false);
      setForm({ ...form, amount: 0, reference: "", notes: "", invoice_ids: [] });
      onDone?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="record-payment-open">
          <Plus size={15} className="mr-2" /> Record payment
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Record Payment</DialogTitle>
          <DialogDescription>Allocates to invoices (oldest first if none selected), posts to ledger, updates outstanding.</DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Party type</Label>
            <Select value={form.party_type} onValueChange={(v) => setForm({ ...form, party_type: v, party_id: "" })}>
              <SelectTrigger data-testid="pay-party-type"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="distributor">Distributor</SelectItem>
                <SelectItem value="retailer">Retailer</SelectItem>
                <SelectItem value="customer">Customer</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Party</Label>
            <Select value={form.party_id} onValueChange={(v) => setForm({ ...form, party_id: v })}>
              <SelectTrigger data-testid="pay-party"><SelectValue placeholder="Select party..." /></SelectTrigger>
              <SelectContent>
                {parties.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Amount (USD)</Label>
            <Input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} data-testid="pay-amount" />
          </div>
          <div>
            <Label>Method</Label>
            <Select value={form.method} onValueChange={(v) => setForm({ ...form, method: v })}>
              <SelectTrigger data-testid="pay-method"><SelectValue /></SelectTrigger>
              <SelectContent>
                {["Cash", "UPI", "Bank Transfer", "Cheque", "Card", "Wallet"].map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Reference</Label>
            <Input value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} placeholder="NEFT / UPI ref" data-testid="pay-reference" />
          </div>
          <div>
            <Label>Transaction No</Label>
            <Input value={form.transaction_no} onChange={(e) => setForm({ ...form, transaction_no: e.target.value })} data-testid="pay-txn" />
          </div>
          <div className="col-span-2">
            <Label>Allocate to invoices (optional — auto-allocates oldest first)</Label>
            <div className="max-h-40 overflow-y-auto border border-[#E5E7EB] rounded-lg p-2 mt-1 space-y-1">
              {invoices.length === 0 && <div className="text-xs text-ink-muted p-2">No unpaid invoices for this party.</div>}
              {invoices.map((i) => (
                <label key={i.id} className="flex items-center gap-2 text-sm rounded p-1.5 hover:bg-canvas cursor-pointer">
                  <input type="checkbox" checked={form.invoice_ids.includes(i.id)}
                    onChange={(e) => {
                      const set = new Set(form.invoice_ids);
                      e.target.checked ? set.add(i.id) : set.delete(i.id);
                      setForm({ ...form, invoice_ids: [...set] });
                    }}
                    data-testid={`pay-inv-${i.id}`}
                  />
                  <span className="font-medium">{i.invoice_no}</span>
                  <span className="text-ink-muted text-xs">${(i.total - (i.paid || 0)).toLocaleString()} due</span>
                </label>
              ))}
            </div>
          </div>
          <div className="col-span-2">
            <Label>Notes</Label>
            <Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} data-testid="pay-notes" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="bg-gold hover:bg-gold-dark text-white" disabled={busy || !form.party_id || !(form.amount > 0)} onClick={submit} data-testid="pay-submit">
            {busy ? <Loader2 size={14} className="animate-spin" /> : "Record Payment"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==========================================================
// OUTSTANDING (view)
// ==========================================================
export function OutstandingPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scope, setScope] = useState("distributor");

  const load = (s) => {
    setLoading(true);
    api.get(`/finance/outstanding?party_type=${s}`).then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  };
  useEffect(() => { load(scope); }, [scope]);

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Finance", "Outstanding"]}
        title="Outstanding Management"
        subtitle="Live receivables per party, aged and utilization-adjusted"
        actions={
          <Tabs value={scope} onValueChange={setScope}>
            <TabsList className="bg-canvas border border-[#E5E7EB]">
              <TabsTrigger value="distributor" data-testid="os-distributor">Distributors</TabsTrigger>
              <TabsTrigger value="retailer" data-testid="os-retailer">Retailers</TabsTrigger>
              <TabsTrigger value="customer" data-testid="os-customer">Customers</TabsTrigger>
            </TabsList>
          </Tabs>
        }
      />
      <DataTable
        data={rows}
        loading={loading}
        testId="outstanding-table"
        pageSize={15}
        columns={[
          { key: "party_name", label: "Party", render: (r) => r.party_name || r.party_id },
          { key: "outstanding", label: "Outstanding", type: "currency", align: "right" },
          { key: "overdue", label: "Overdue", type: "currency", align: "right" },
          { key: "overdue_days_max", label: "Aged (days)", align: "right" },
          { key: "credit_limit", label: "Credit Limit", type: "currency", align: "right" },
          { key: "credit_utilization", label: "Utilization", align: "right", render: (r) => (
            <div className="flex items-center gap-2 w-32 justify-end">
              <div className="h-1.5 bg-slate-100 rounded-full w-16 overflow-hidden">
                <div className={`h-full ${r.credit_utilization > 90 ? "bg-rose-500" : r.credit_utilization > 70 ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${Math.min(100, r.credit_utilization)}%` }} />
              </div>
              <span className="text-xs tabular-nums">{r.credit_utilization}%</span>
            </div>
          )},
          { key: "collection_status", label: "Status", type: "status" },
        ]}
      />
    </div>
  );
}

// ==========================================================
// DOUBLE-ENTRY LEDGER
// ==========================================================
export function DoubleLedgerPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [account, setAccount] = useState("");
  const [partyType, setPartyType] = useState("");

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (account) params.set("account", account);
    if (partyType) params.set("party_type", partyType);
    api.get(`/finance/ledger?${params.toString()}`).then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [account, partyType]);

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Finance", "Ledger"]}
        title="Double-Entry Ledger"
        subtitle="Every financial action creates balanced Dr/Cr entries with full audit trail"
        actions={
          <div className="flex gap-2">
            <Select value={account || "all"} onValueChange={(v) => setAccount(v === "all" ? "" : v)}>
              <SelectTrigger className="w-40 h-10 border-[#E5E7EB]" data-testid="ledger-account"><SelectValue placeholder="Account" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All accounts</SelectItem>
                {["AR", "CASH", "SALES", "TAX_OUT", "DISCOUNT", "CASHBACK_EXP", "CASHBACK_LIAB"].map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={partyType || "all"} onValueChange={(v) => setPartyType(v === "all" ? "" : v)}>
              <SelectTrigger className="w-40 h-10 border-[#E5E7EB]" data-testid="ledger-party-type"><SelectValue placeholder="Party type" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All parties</SelectItem>
                {["distributor", "retailer", "customer"].map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        }
      />
      <DataTable
        data={rows}
        loading={loading}
        testId="double-ledger-table"
        pageSize={20}
        columns={[
          { key: "timestamp", label: "When", type: "date" },
          { key: "account", label: "Account", type: "chip" },
          { key: "party_name", label: "Party" },
          { key: "debit", label: "Debit", align: "right", render: (r) => r.debit > 0 ? <span className="tabular-nums font-semibold text-ink">${r.debit.toLocaleString()}</span> : <span className="text-ink-muted">—</span> },
          { key: "credit", label: "Credit", align: "right", render: (r) => r.credit > 0 ? <span className="tabular-nums font-semibold text-ink">${r.credit.toLocaleString()}</span> : <span className="text-ink-muted">—</span> },
          { key: "reference_type", label: "Ref", type: "chip" },
          { key: "narration", label: "Narration" },
        ]}
      />
    </div>
  );
}

// ==========================================================
// CASHBACK (rules + approvals + wallet-lookup)
// ==========================================================
export function CashbackEnginePage() {
  const [rules, setRules] = useState([]);
  const [pending, setPending] = useState([]);
  const [ruleOpen, setRuleOpen] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    api.get("/finance/cashback-rules").then((r) => setRules(r.data.data || []));
    api.get("/collections/cashback").then((r) => setPending(r.data.data || []));
  }, [reload]);

  const approve = async (id) => {
    try {
      await api.post(`/finance/cashback/${id}/approve`);
      toast.success("Cashback approved → wallet credited");
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const reject = async (id) => {
    try {
      await api.post(`/finance/cashback/${id}/reject`, { reason: "Rejected" });
      toast.success("Rejected");
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Rewards", "Cashback"]}
        title="Cashback Engine"
        subtitle="Rule-based cashback with wallet, daily/monthly caps and approval workflow"
        actions={<CashbackRuleDialog open={ruleOpen} onOpenChange={setRuleOpen} onDone={() => setReload((v) => v + 1)} />}
      />
      <Tabs defaultValue="rules" className="mb-4">
        <TabsList className="bg-canvas border border-[#E5E7EB]">
          <TabsTrigger value="rules" data-testid="cb-tab-rules">Rules ({rules.length})</TabsTrigger>
          <TabsTrigger value="pending" data-testid="cb-tab-pending">Pending / History ({pending.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="rules" className="mt-4">
          <DataTable
            data={rules}
            testId="cashback-rules-table"
            columns={[
              { key: "name", label: "Name" },
              { key: "scope", label: "Scope", type: "chip" },
              { key: "party_type", label: "For", type: "chip" },
              { key: "type", label: "Type", type: "chip" },
              { key: "value", label: "Value", align: "right", render: (r) => r.type === "percent" ? `${r.value}%` : `$${r.value}` },
              { key: "max_cashback", label: "Max", align: "right", render: (r) => r.max_cashback ? `$${r.max_cashback.toLocaleString()}` : "—" },
              { key: "daily_limit", label: "Daily Cap", align: "right", render: (r) => r.daily_limit ? `$${r.daily_limit.toLocaleString()}` : "—" },
              { key: "approval_required", label: "Approval", render: (r) => r.approval_required ? "Required" : "Auto" },
            ]}
          />
        </TabsContent>
        <TabsContent value="pending" className="mt-4">
          <DataTable
            data={pending}
            testId="cashback-txn-table"
            columns={[
              { key: "id", label: "Ref" },
              { key: "party_name", label: "Party", render: (r) => r.party_name || r.retailer_name || r.retailer_id },
              { key: "campaign", label: "Campaign", type: "chip" },
              { key: "earned", label: "Earned", type: "currency", align: "right" },
              { key: "status", label: "Status", type: "status" },
              { key: "issued_on", label: "Issued", type: "date" },
              { key: "actions", label: "", render: (r) => (
                r.status === "Pending" ? (
                  <div className="flex gap-1">
                    <Button size="sm" className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => approve(r.id)} data-testid={`cb-approve-${r.id}`}>
                      <CheckCircle2 size={13} className="mr-1" /> Approve
                    </Button>
                    <Button size="sm" variant="outline" className="h-8 border-rose-200 text-rose-700" onClick={() => reject(r.id)} data-testid={`cb-reject-${r.id}`}>
                      <XCircle size={13} className="mr-1" /> Reject
                    </Button>
                  </div>
                ) : <span className="text-xs text-ink-muted">—</span>
              )},
            ]}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function CashbackRuleDialog({ open, onOpenChange, onDone }) {
  const [form, setForm] = useState({
    name: "", scope: "sku", scope_id: "", type: "percent", value: 2,
    max_cashback: 0, daily_limit: 0, monthly_limit: 0,
    party_type: "retailer", approval_required: false,
  });
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/finance/cashback-rules", form);
      toast.success("Cashback rule created");
      onOpenChange(false); onDone?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="cb-rule-open">
          <Plus size={15} className="mr-2" /> New rule
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle>New Cashback Rule</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2"><Label>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="cb-name" /></div>
          <div><Label>Scope</Label>
            <Select value={form.scope} onValueChange={(v) => setForm({ ...form, scope: v })}>
              <SelectTrigger data-testid="cb-scope"><SelectValue /></SelectTrigger>
              <SelectContent>{["sku", "product", "category", "distributor", "retailer", "customer", "campaign"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div><Label>Scope ID (optional)</Label><Input value={form.scope_id} onChange={(e) => setForm({ ...form, scope_id: e.target.value })} data-testid="cb-scope-id" /></div>
          <div><Label>Type</Label>
            <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}>
              <SelectTrigger data-testid="cb-type"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="percent">Percent</SelectItem><SelectItem value="flat">Flat</SelectItem></SelectContent>
            </Select>
          </div>
          <div><Label>Value</Label><Input type="number" value={form.value} onChange={(e) => setForm({ ...form, value: parseFloat(e.target.value) })} data-testid="cb-value" /></div>
          <div><Label>Max cashback</Label><Input type="number" value={form.max_cashback} onChange={(e) => setForm({ ...form, max_cashback: parseFloat(e.target.value) })} data-testid="cb-max" /></div>
          <div><Label>Daily cap</Label><Input type="number" value={form.daily_limit} onChange={(e) => setForm({ ...form, daily_limit: parseFloat(e.target.value) })} data-testid="cb-daily" /></div>
          <div><Label>For</Label>
            <Select value={form.party_type} onValueChange={(v) => setForm({ ...form, party_type: v })}>
              <SelectTrigger data-testid="cb-partytype"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="retailer">Retailer</SelectItem><SelectItem value="customer">Customer</SelectItem><SelectItem value="distributor">Distributor</SelectItem></SelectContent>
            </Select>
          </div>
          <div className="col-span-2 flex items-center gap-2 mt-2">
            <input id="cb-req" type="checkbox" checked={form.approval_required} onChange={(e) => setForm({ ...form, approval_required: e.target.checked })} data-testid="cb-approval" />
            <Label htmlFor="cb-req" className="text-sm">Requires approval before wallet credit</Label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="bg-gold hover:bg-gold-dark text-white" disabled={busy || !form.name} onClick={submit} data-testid="cb-submit">
            {busy ? <Loader2 size={14} className="animate-spin" /> : "Create rule"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==========================================================
// COUPONS (create + validate)
// ==========================================================
export function CouponsEnginePage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [validateOpen, setValidateOpen] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    setLoading(true);
    api.get("/collections/coupons").then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  }, [reload]);

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Rewards", "Coupons"]}
        title="Coupon Engine"
        subtitle="Create, validate and track redemptions with fraud checks and usage limits"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setValidateOpen(true)} className="border-[#E5E7EB] h-10" data-testid="coupon-validate-open">
              <TicketCheck size={15} className="mr-2" /> Validate
            </Button>
            <CouponCreateDialog open={open} onOpenChange={setOpen} onDone={() => setReload((v) => v + 1)} />
          </div>
        }
      />
      <DataTable
        data={rows}
        loading={loading}
        testId="coupons-engine-table"
        columns={[
          { key: "code", label: "Code" },
          { key: "campaign", label: "Campaign", type: "chip" },
          { key: "discount_type", label: "Type", type: "chip" },
          { key: "value", label: "Value", align: "right", render: (r) => r.discount_type === "Percent" ? `${r.value}%` : `$${r.value}` },
          { key: "max_discount", label: "Max", align: "right", render: (r) => r.max_discount ? `$${r.max_discount}` : "—" },
          { key: "min_order", label: "Min order", align: "right", render: (r) => r.min_order ? `$${r.min_order}` : "—" },
          { key: "usage", label: "Used", align: "right", render: (r) => `${r.usage || 0} / ${r.limit || "∞"}` },
          { key: "valid_till", label: "Expires", type: "date" },
          { key: "status", label: "Status", type: "status" },
        ]}
      />
      <CouponValidateDialog open={validateOpen} onOpenChange={setValidateOpen} />
    </div>
  );
}

function CouponCreateDialog({ open, onOpenChange, onDone }) {
  const [form, setForm] = useState({
    code: "", campaign: "", discount_type: "Percent", value: 10,
    max_discount: 500, min_order: 1000, limit: 100,
  });
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/finance/coupons/create", form);
      toast.success("Coupon created");
      onOpenChange(false); onDone?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="coupon-create-open">
          <Plus size={15} className="mr-2" /> New coupon
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle>Create Coupon</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-4">
          <div><Label>Code</Label><Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} data-testid="cpn-code" /></div>
          <div><Label>Campaign</Label><Input value={form.campaign} onChange={(e) => setForm({ ...form, campaign: e.target.value })} data-testid="cpn-campaign" /></div>
          <div><Label>Type</Label>
            <Select value={form.discount_type} onValueChange={(v) => setForm({ ...form, discount_type: v })}>
              <SelectTrigger data-testid="cpn-type"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="Percent">Percent</SelectItem><SelectItem value="Flat">Flat</SelectItem></SelectContent>
            </Select>
          </div>
          <div><Label>Value</Label><Input type="number" value={form.value} onChange={(e) => setForm({ ...form, value: parseFloat(e.target.value) })} data-testid="cpn-value" /></div>
          <div><Label>Max discount</Label><Input type="number" value={form.max_discount} onChange={(e) => setForm({ ...form, max_discount: parseFloat(e.target.value) })} data-testid="cpn-max" /></div>
          <div><Label>Min order</Label><Input type="number" value={form.min_order} onChange={(e) => setForm({ ...form, min_order: parseFloat(e.target.value) })} data-testid="cpn-min" /></div>
          <div><Label>Usage limit</Label><Input type="number" value={form.limit} onChange={(e) => setForm({ ...form, limit: parseInt(e.target.value) })} data-testid="cpn-limit" /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="bg-gold hover:bg-gold-dark text-white" disabled={busy || !form.code} onClick={submit} data-testid="cpn-submit">
            {busy ? <Loader2 size={14} className="animate-spin" /> : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CouponValidateDialog({ open, onOpenChange }) {
  const [form, setForm] = useState({ code: "GOFLEET50", order_total: 5000, party_id: "cust-300", party_type: "customer" });
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const check = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/finance/coupons/validate", { ...form, order_total: parseFloat(form.order_total) });
      setResult(data);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Validate coupon</DialogTitle><DialogDescription>Test coupon eligibility without redeeming</DialogDescription></DialogHeader>
        <div className="space-y-3">
          <div><Label>Code</Label><Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} data-testid="val-code" /></div>
          <div><Label>Order total</Label><Input type="number" value={form.order_total} onChange={(e) => setForm({ ...form, order_total: e.target.value })} data-testid="val-total" /></div>
          <Button onClick={check} disabled={busy} className="w-full bg-gold hover:bg-gold-dark text-white" data-testid="val-check">
            {busy ? "Checking…" : "Check"}
          </Button>
          {result && (
            <div className={`rounded-lg border p-3 ${result.ok ? "border-emerald-200 bg-emerald-50" : "border-rose-200 bg-rose-50"}`}>
              {result.ok ? (
                <>
                  <div className="font-semibold text-emerald-800">✓ Valid coupon</div>
                  <div className="text-sm mt-1">Discount: <b>${result.discount}</b></div>
                </>
              ) : (
                <div className="text-rose-800"><b>✗ Invalid</b>: {result.reason}</div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ==========================================================
// CUSTOMER ORDERS
// ==========================================================
export function CustomerOrdersPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    setLoading(true);
    api.get("/collections/customers").then(() => {});
    // Fetch from customer_orders collection via a dedicated resource
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/finance/audit-log?entity_type=customer_order&limit=200`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("go_oil_token")}` }
    }).catch(() => {});
    // Use existing collections endpoint by loading customer_orders via new resource shortcut
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/collections/customer-orders?limit=200`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("go_oil_token")}` }
    }).then((r) => r.json()).then((d) => setRows(d.data || []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [reload]);

  const act = async (id, verb) => {
    try {
      await api.post(`/finance/customer-orders/${id}/${verb}`);
      toast.success(`Order ${verb}`);
      setReload((v) => v + 1);
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Sales", "Customer Orders"]}
        title="Customer Orders"
        subtitle="Retailer → Customer sales — auto-deducts retailer inventory + validates coupon + earns cashback"
        actions={<NewCustomerOrderDialog open={open} onOpenChange={setOpen} onDone={() => setReload((v) => v + 1)} />}
      />
      <DataTable
        data={rows}
        loading={loading}
        testId="customer-orders-table"
        pageSize={12}
        columns={[
          { key: "order_no", label: "Order" },
          { key: "customer_name", label: "Customer" },
          { key: "retailer_name", label: "Retailer" },
          { key: "line_items", label: "Items", align: "right" },
          { key: "subtotal", label: "Subtotal", type: "currency", align: "right" },
          { key: "discount", label: "Discount", type: "currency", align: "right" },
          { key: "total", label: "Total", type: "currency", align: "right" },
          { key: "coupon_code", label: "Coupon", type: "chip" },
          { key: "status", label: "Status", type: "status" },
          { key: "actions", label: "", render: (r) => (
            r.status === "confirmed" ? (
              <div className="flex gap-1">
                <Button size="sm" variant="outline" className="h-8" onClick={() => act(r.id, "pack")} data-testid={`co-pack-${r.id}`}>Pack</Button>
                <Button size="sm" className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => act(r.id, "deliver")} data-testid={`co-deliver-${r.id}`}>Deliver</Button>
              </div>
            ) : r.status === "packed" ? (
              <Button size="sm" className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => act(r.id, "deliver")} data-testid={`co-deliver-${r.id}`}>Deliver</Button>
            ) : <span className="text-xs text-ink-muted">—</span>
          )},
        ]}
      />
    </div>
  );
}

function NewCustomerOrderDialog({ open, onOpenChange, onDone }) {
  const [retailers, setRetailers] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [form, setForm] = useState({
    retailer_id: "", customer_id: "",
    sku_id: "", qty: 2,
    coupon_code: "", payment_method: "Cash",
  });
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    if (!open) return;
    api.get("/collections/retailers?limit=200").then((r) => setRetailers(r.data.data || []));
    api.get("/collections/customers?limit=200").then((r) => setCustomers(r.data.data || []));
  }, [open]);
  useEffect(() => {
    if (!form.retailer_id) { setInventory([]); return; }
    api.get(`/workflow/inventory/retailer/${form.retailer_id}`).then((r) => setInventory((r.data.data || []).filter((x) => x.available > 0)));
  }, [form.retailer_id]);

  const chosen = inventory.find((i) => i.sku_id === form.sku_id);
  const price = chosen ? 1000 : 0;

  const submit = async () => {
    setBusy(true);
    try {
      const payload = {
        retailer_id: form.retailer_id, customer_id: form.customer_id,
        lines: [{ sku_id: form.sku_id, qty: parseInt(form.qty) }],
        coupon_code: form.coupon_code || undefined,
        payment_method: form.payment_method,
      };
      const { data } = await api.post("/finance/customer-orders", payload);
      setPreview(data);
      toast.success(`Order ${data.order_no} — invoice ${data.invoice_no} generated`);
      onDone?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) setPreview(null); }}>
      <DialogTrigger asChild>
        <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="co-new-open">
          <Plus size={15} className="mr-2" /> New order
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle>New Customer Order</DialogTitle><DialogDescription>Deducts retailer inventory, validates coupon, earns cashback.</DialogDescription></DialogHeader>
        {preview ? (
          <div className="space-y-3">
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm">
              <div className="font-semibold text-emerald-800">Order created ✓</div>
              <ul className="mt-2 space-y-1 text-emerald-900">
                <li>Order No: <b>{preview.order_no}</b></li>
                <li>Invoice: <b>{preview.invoice_no}</b></li>
                <li>Subtotal: ${preview.subtotal}</li>
                <li>Discount: ${preview.discount} {preview.coupon_code && `(${preview.coupon_code})`}</li>
                <li>Total: <b>${preview.total}</b></li>
                <li>Cashback earned: ${preview.cashback_estimated}</li>
              </ul>
            </div>
            <Button onClick={() => { onOpenChange(false); setPreview(null); }} className="w-full">Done</Button>
          </div>
        ) : (
          <div className="space-y-3">
            <div><Label>Retailer</Label>
              <Select value={form.retailer_id} onValueChange={(v) => setForm({ ...form, retailer_id: v, sku_id: "" })}>
                <SelectTrigger data-testid="co-retailer"><SelectValue placeholder="Select..." /></SelectTrigger>
                <SelectContent>{retailers.map((r) => <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><Label>Customer</Label>
              <Select value={form.customer_id} onValueChange={(v) => setForm({ ...form, customer_id: v })}>
                <SelectTrigger data-testid="co-customer"><SelectValue placeholder="Select..." /></SelectTrigger>
                <SelectContent>{customers.slice(0, 50).map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><Label>SKU (from retailer inventory)</Label>
              <Select value={form.sku_id} onValueChange={(v) => setForm({ ...form, sku_id: v })}>
                <SelectTrigger data-testid="co-sku"><SelectValue placeholder={inventory.length ? "Select..." : "No stock"} /></SelectTrigger>
                <SelectContent>{inventory.slice(0, 30).map((i) => <SelectItem key={i.id} value={i.sku_id}>{i.sku_code} — avail {i.available}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Qty</Label><Input type="number" value={form.qty} onChange={(e) => setForm({ ...form, qty: e.target.value })} data-testid="co-qty" /></div>
              <div><Label>Coupon (optional)</Label><Input value={form.coupon_code} onChange={(e) => setForm({ ...form, coupon_code: e.target.value.toUpperCase() })} data-testid="co-coupon" placeholder="GOFLEET50" /></div>
            </div>
            <div><Label>Payment method</Label>
              <Select value={form.payment_method} onValueChange={(v) => setForm({ ...form, payment_method: v })}>
                <SelectTrigger data-testid="co-payment"><SelectValue /></SelectTrigger>
                <SelectContent>{["Cash", "UPI", "Card", "Wallet"].map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button className="bg-gold hover:bg-gold-dark text-white" disabled={busy || !form.retailer_id || !form.customer_id || !form.sku_id} onClick={submit} data-testid="co-submit">
                {busy ? <Loader2 size={14} className="animate-spin" /> : "Place order"}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ==========================================================
// WALLET
// ==========================================================
export function WalletsPage() {
  const [pt, setPt] = useState("customer");
  const [parties, setParties] = useState([]);
  const [pid, setPid] = useState("");
  const [wallet, setWallet] = useState(null);
  const [txns, setTxns] = useState([]);

  useEffect(() => {
    const c = pt === "customer" ? "customers" : (pt === "retailer" ? "retailers" : "distributors");
    api.get(`/collections/${c}?limit=200`).then((r) => {
      const list = r.data.data || [];
      setParties(list);
      if (list[0]) setPid(list[0].id);
    });
  }, [pt]);
  useEffect(() => {
    if (!pid) return;
    api.get(`/finance/wallets/${pt}/${pid}`).then((r) => {
      setWallet(r.data.wallet); setTxns(r.data.transactions || []);
    });
  }, [pt, pid]);

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Rewards", "Wallets"]}
        title="Cashback Wallets"
        subtitle="Party-level cashback balance with full earn/redeem history"
        actions={
          <div className="flex gap-2">
            <Select value={pt} onValueChange={setPt}>
              <SelectTrigger className="w-40 h-10 border-[#E5E7EB]" data-testid="wallet-pt"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="customer">Customer</SelectItem><SelectItem value="retailer">Retailer</SelectItem><SelectItem value="distributor">Distributor</SelectItem></SelectContent>
            </Select>
            <Select value={pid} onValueChange={setPid}>
              <SelectTrigger className="w-64 h-10 border-[#E5E7EB]" data-testid="wallet-party"><SelectValue /></SelectTrigger>
              <SelectContent>{parties.slice(0, 60).map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        }
      />
      {wallet && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white border border-[#E5E7EB] rounded-xl card-soft p-5">
            <div className="text-[11px] uppercase tracking-[0.22em] text-ink-muted font-semibold">Balance</div>
            <div className="mt-2 font-display font-extrabold text-3xl text-gold-dark">${(wallet.balance || 0).toLocaleString()}</div>
          </div>
          <div className="bg-white border border-[#E5E7EB] rounded-xl card-soft p-5">
            <div className="text-[11px] uppercase tracking-[0.22em] text-ink-muted font-semibold">Lifetime Earned</div>
            <div className="mt-2 font-display font-extrabold text-3xl text-emerald-700">${(wallet.lifetime_earned || 0).toLocaleString()}</div>
          </div>
          <div className="bg-white border border-[#E5E7EB] rounded-xl card-soft p-5">
            <div className="text-[11px] uppercase tracking-[0.22em] text-ink-muted font-semibold">Lifetime Redeemed</div>
            <div className="mt-2 font-display font-extrabold text-3xl text-slate-700">${(wallet.lifetime_redeemed || 0).toLocaleString()}</div>
          </div>
        </div>
      )}
      <DataTable
        data={txns}
        testId="wallet-txn-table"
        columns={[
          { key: "timestamp", label: "When", type: "date" },
          { key: "type", label: "Type", type: "chip" },
          { key: "amount", label: "Amount", type: "currency", align: "right", render: (r) => (
            <span className={`tabular-nums font-semibold ${r.type === "credit" ? "text-emerald-700" : "text-rose-700"}`}>
              {r.type === "credit" ? "+" : "-"}${r.amount.toLocaleString()}
            </span>
          )},
          { key: "reason", label: "Reason" },
        ]}
      />
    </div>
  );
}

// ==========================================================
// RECONCILIATION
// ==========================================================
export function ReconciliationPage() {
  const [reports, setReports] = useState([]);
  const [current, setCurrent] = useState(null);
  const [busy, setBusy] = useState(false);
  const [pt, setPt] = useState("distributor");

  const load = () => api.get("/finance/reconciliation/reports").then((r) => setReports(r.data.data || []));
  useEffect(() => { load(); }, []);

  const run = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/finance/reconciliation/run", { party_type: pt });
      setCurrent(data);
      toast.success(`Reconciliation complete: ${data.summary.balanced} balanced, ${data.summary.variance} variance`);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  const active = current || reports[0];

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Finance", "Reconciliation"]}
        title="Reconciliation"
        subtitle="Automatic invoice vs payment reconciliation with variance detection"
        actions={
          <div className="flex gap-2">
            <Select value={pt} onValueChange={setPt}>
              <SelectTrigger className="w-40 h-10 border-[#E5E7EB]" data-testid="rec-scope"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="distributor">Distributors</SelectItem><SelectItem value="retailer">Retailers</SelectItem><SelectItem value="customer">Customers</SelectItem></SelectContent>
            </Select>
            <Button onClick={run} disabled={busy} className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="rec-run">
              {busy ? <Loader2 size={14} className="animate-spin" /> : <><GitCompareArrows size={15} className="mr-2" /> Run</>}
            </Button>
          </div>
        }
      />
      {active && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white border border-[#E5E7EB] rounded-xl card-soft p-5">
            <div className="text-[11px] uppercase tracking-[0.22em] text-ink-muted font-semibold">Total parties</div>
            <div className="mt-2 font-display font-extrabold text-3xl text-ink">{active.summary.total_parties}</div>
          </div>
          <div className="bg-white border border-[#E5E7EB] rounded-xl card-soft p-5">
            <div className="text-[11px] uppercase tracking-[0.22em] text-ink-muted font-semibold">Balanced</div>
            <div className="mt-2 font-display font-extrabold text-3xl text-emerald-700">{active.summary.balanced}</div>
          </div>
          <div className="bg-white border border-[#E5E7EB] rounded-xl card-soft p-5">
            <div className="text-[11px] uppercase tracking-[0.22em] text-ink-muted font-semibold">With Variance</div>
            <div className="mt-2 font-display font-extrabold text-3xl text-rose-700">{active.summary.variance}</div>
          </div>
        </div>
      )}
      <DataTable
        data={active?.rows || []}
        testId="reconciliation-table"
        columns={[
          { key: "party_name", label: "Party" },
          { key: "total_billed", label: "Billed", type: "currency", align: "right" },
          { key: "total_paid_invoices", label: "Paid (invoices)", type: "currency", align: "right" },
          { key: "total_payments_recv", label: "Payments recv", type: "currency", align: "right" },
          { key: "variance", label: "Variance", type: "currency", align: "right" },
          { key: "outstanding", label: "Outstanding", type: "currency", align: "right" },
          { key: "status", label: "Status", type: "status" },
        ]}
      />
    </div>
  );
}

// ==========================================================
// AUDIT LOG
// ==========================================================
export function AuditLogPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.get("/finance/audit-log?limit=300").then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  }, []);
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Administration", "Audit Log"]}
        title="Audit Log"
        subtitle="Immutable trail of every financial and administrative action"
      />
      <DataTable
        data={rows}
        loading={loading}
        testId="audit-log-table"
        pageSize={20}
        columns={[
          { key: "timestamp", label: "When", type: "date" },
          { key: "actor", label: "Actor" },
          { key: "action", label: "Action", type: "chip" },
          { key: "entity_type", label: "Entity", type: "chip" },
          { key: "entity_id", label: "ID", render: (r) => <span className="font-mono text-xs text-ink-muted">{r.entity_id}</span> },
          { key: "meta", label: "Details", render: (r) => (
            <span className="text-xs text-ink-muted">{JSON.stringify(r.meta || {}).slice(0, 60)}</span>
          )},
        ]}
      />
    </div>
  );
}
