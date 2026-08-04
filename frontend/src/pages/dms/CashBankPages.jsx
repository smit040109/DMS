import React, { useEffect, useMemo, useState } from "react";
import { dms, inr, niceDate } from "./api";
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
import {
  Plus, Trash2, Edit, Search, Landmark, Coins, FileSignature, PiggyBank, ArrowLeftRight, IndianRupee,
} from "lucide-react";

// helpers
const today = () => new Date().toISOString().slice(0, 10);
const canWrite = (role) => ["owner", "owner_accountant", "super_admin"].includes(role);
const canDelete = (role) => ["owner", "super_admin"].includes(role);

// =====================================================================
// 1. Bank Accounts Page
// =====================================================================
export function BankAccountsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", account_number: "", ifsc: "", branch: "", opening_balance: 0, notes: "" });

  const load = async () => {
    try { const d = await dms.listBankAccounts(); setRows(d.data || []); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed to load"); }
  };
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm({ name: "", account_number: "", ifsc: "", branch: "", opening_balance: 0, notes: "" }); setOpen(true); };
  const openEdit = (r) => { setEditing(r); setForm({ ...r }); setOpen(true); };
  const save = async () => {
    if (!form.name?.trim()) return toast.error("Bank name required");
    try {
      if (editing) await dms.updateBankAccount(editing.id, form);
      else await dms.createBankAccount(form);
      setOpen(false); toast.success("Saved"); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };
  const del = async (r) => {
    if (!window.confirm(`Delete ${r.name}?`)) return;
    try { await dms.deleteBankAccount(r.id); toast.success("Deleted"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Delete failed"); }
  };

  const totalBalance = rows.reduce((s, r) => s + (r.current_balance || 0), 0);

  return (
    <div className="space-y-4">
      <PageHeader title="Bank Accounts" subtitle="Standalone register — not linked to payment flows"
        action={canWrite(user?.role) && <Button onClick={openNew} className="bg-amber-600 hover:bg-amber-700"><Plus className="w-4 h-4 mr-2" />New Account</Button>} />

      <Card className="p-4 border-amber-200">
        <div className="flex items-center gap-3">
          <Landmark className="w-8 h-8 text-amber-600" />
          <div>
            <div className="text-xs uppercase text-slate-500">Total Cash In Bank</div>
            <div className="text-2xl font-bold text-slate-900">{inr(totalBalance)}</div>
            <div className="text-xs text-slate-500">Across {rows.length} account(s)</div>
          </div>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead><TableHead>Account No.</TableHead><TableHead>IFSC</TableHead><TableHead>Branch</TableHead>
              <TableHead className="text-right">Opening</TableHead><TableHead className="text-right">Current</TableHead>
              <TableHead>Status</TableHead><TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow><TableCell colSpan={8} className="text-center text-slate-500 py-8">No bank accounts yet.</TableCell></TableRow>
            ) : rows.map(r => (
              <TableRow key={r.id}>
                <TableCell className="font-medium">{r.name}</TableCell>
                <TableCell className="font-mono text-xs">{r.account_number || "—"}</TableCell>
                <TableCell className="font-mono text-xs">{r.ifsc || "—"}</TableCell>
                <TableCell>{r.branch || "—"}</TableCell>
                <TableCell className="text-right">{inr(r.opening_balance)}</TableCell>
                <TableCell className="text-right font-semibold">{inr(r.current_balance)}</TableCell>
                <TableCell><Badge variant={r.active ? "default" : "secondary"} className={r.active ? "bg-emerald-600" : ""}>{r.active ? "Active" : "Inactive"}</Badge></TableCell>
                <TableCell className="text-right">
                  {canWrite(user?.role) && <Button size="sm" variant="outline" onClick={() => openEdit(r)}><Edit className="w-3 h-3" /></Button>}
                  {canDelete(user?.role) && <Button size="sm" variant="outline" className="ml-1 text-rose-600" onClick={() => del(r)}><Trash2 className="w-3 h-3" /></Button>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editing ? "Edit Bank Account" : "New Bank Account"}</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3 py-2">
            <div className="col-span-2"><Label>Bank / Account Name*</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="HDFC Current" /></div>
            <div><Label>Account Number</Label><Input value={form.account_number} onChange={e => setForm({ ...form, account_number: e.target.value })} /></div>
            <div><Label>IFSC</Label><Input value={form.ifsc} onChange={e => setForm({ ...form, ifsc: e.target.value })} /></div>
            <div><Label>Branch</Label><Input value={form.branch} onChange={e => setForm({ ...form, branch: e.target.value })} /></div>
            {!editing && <div><Label>Opening Balance</Label><Input type="number" value={form.opening_balance} onChange={e => setForm({ ...form, opening_balance: e.target.value })} /></div>}
            <div className="col-span-2"><Label>Notes</Label><Textarea rows={2} value={form.notes || ""} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button className="bg-amber-600 hover:bg-amber-700" onClick={save}>{editing ? "Update" : "Create"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// =====================================================================
// 2. Bank Transactions Page
// =====================================================================
export function BankTransactionsPage() {
  const { user } = useAuth();
  const [accts, setAccts] = useState([]);
  const [rows, setRows] = useState([]);
  const [filters, setFilters] = useState({ account_id: "", start: "", end: "", type: "" });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ bank_account_id: "", date: today(), type: "deposit", amount: "", reference: "", notes: "" });

  const load = async () => {
    try {
      const params = {};
      Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
      const d = await dms.listBankTxns(params); setRows(d.data || []);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed to load"); }
  };
  useEffect(() => { dms.listBankAccounts().then(d => setAccts(d.data || [])); }, []);
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filters]);

  const save = async () => {
    if (!form.bank_account_id) return toast.error("Select a bank account");
    if (!(Number(form.amount) > 0)) return toast.error("Amount must be > 0");
    try { await dms.createBankTxn(form); toast.success("Recorded"); setOpen(false); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };
  const del = async (r) => {
    if (!window.confirm(`Delete this ${r.type}? Balance will be reversed.`)) return;
    try { await dms.deleteBankTxn(r.id); toast.success("Deleted"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Delete failed"); }
  };

  return (
    <div className="space-y-4">
      <PageHeader title="Bank Transactions" subtitle="Deposits and withdrawals per account"
        action={canWrite(user?.role) && <Button onClick={() => { setForm({ bank_account_id: accts[0]?.id || "", date: today(), type: "deposit", amount: "", reference: "", notes: "" }); setOpen(true); }} className="bg-amber-600 hover:bg-amber-700"><Plus className="w-4 h-4 mr-2" />New Entry</Button>} />

      <Card className="p-3">
        <div className="flex flex-wrap gap-2 items-end">
          <div><Label className="text-xs">Account</Label>
            <Select value={filters.account_id || "all"} onValueChange={v => setFilters({ ...filters, account_id: v === "all" ? "" : v })}>
              <SelectTrigger className="w-56"><SelectValue placeholder="All" /></SelectTrigger>
              <SelectContent><SelectItem value="all">All accounts</SelectItem>{accts.map(a => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}</SelectContent>
            </Select></div>
          <div><Label className="text-xs">Type</Label>
            <Select value={filters.type || "all"} onValueChange={v => setFilters({ ...filters, type: v === "all" ? "" : v })}>
              <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="all">All</SelectItem><SelectItem value="deposit">Deposit</SelectItem><SelectItem value="withdrawal">Withdrawal</SelectItem></SelectContent>
            </Select></div>
          <div><Label className="text-xs">From</Label><Input type="date" value={filters.start} onChange={e => setFilters({ ...filters, start: e.target.value })} /></div>
          <div><Label className="text-xs">To</Label><Input type="date" value={filters.end} onChange={e => setFilters({ ...filters, end: e.target.value })} /></div>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow><TableHead>Date</TableHead><TableHead>Account</TableHead><TableHead>Type</TableHead><TableHead>Reference</TableHead><TableHead className="text-right">Amount</TableHead><TableHead className="text-right">Balance After</TableHead><TableHead className="text-right"></TableHead></TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? <TableRow><TableCell colSpan={7} className="text-center text-slate-500 py-8">No transactions.</TableCell></TableRow>
              : rows.map(r => (
                <TableRow key={r.id}>
                  <TableCell>{r.date}</TableCell>
                  <TableCell>{r.bank_account_name}</TableCell>
                  <TableCell><Badge className={r.type === "deposit" ? "bg-emerald-600" : "bg-rose-600"}>{r.type}</Badge></TableCell>
                  <TableCell className="text-xs">{r.reference || "—"}</TableCell>
                  <TableCell className={"text-right font-medium " + (r.type === "deposit" ? "text-emerald-700" : "text-rose-700")}>
                    {r.type === "deposit" ? "+" : "−"} {inr(r.amount)}
                  </TableCell>
                  <TableCell className="text-right">{inr(r.balance_after)}</TableCell>
                  <TableCell className="text-right">{canDelete(user?.role) && <Button size="sm" variant="outline" className="text-rose-600" onClick={() => del(r)}><Trash2 className="w-3 h-3" /></Button>}</TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent><DialogHeader><DialogTitle>New Bank Transaction</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3 py-2">
            <div className="col-span-2"><Label>Account*</Label>
              <Select value={form.bank_account_id} onValueChange={v => setForm({ ...form, bank_account_id: v })}>
                <SelectTrigger><SelectValue placeholder="Choose account" /></SelectTrigger>
                <SelectContent>{accts.map(a => <SelectItem key={a.id} value={a.id}>{a.name} • {inr(a.current_balance)}</SelectItem>)}</SelectContent>
              </Select></div>
            <div><Label>Type*</Label>
              <Select value={form.type} onValueChange={v => setForm({ ...form, type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="deposit">Deposit</SelectItem><SelectItem value="withdrawal">Withdrawal</SelectItem></SelectContent>
              </Select></div>
            <div><Label>Date*</Label><Input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} /></div>
            <div className="col-span-2"><Label>Amount*</Label><Input type="number" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} /></div>
            <div className="col-span-2"><Label>Reference</Label><Input value={form.reference} onChange={e => setForm({ ...form, reference: e.target.value })} placeholder="Cheque no. / UTR / etc." /></div>
            <div className="col-span-2"><Label>Notes</Label><Textarea rows={2} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button className="bg-amber-600 hover:bg-amber-700" onClick={save}>Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// =====================================================================
// 3. Cash Register Page
// =====================================================================
export function CashRegisterPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [balance, setBalance] = useState(0);
  const [filters, setFilters] = useState({ start: "", end: "", type: "" });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ date: today(), type: "in", amount: "", reference: "", notes: "" });

  const load = async () => {
    try {
      const params = {}; Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
      const d = await dms.listCashRegister(params);
      setRows(d.data || []); setBalance(d.current_balance || 0);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed to load"); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filters]);

  const save = async () => {
    if (!(Number(form.amount) > 0)) return toast.error("Amount must be > 0");
    try { await dms.createCashEntry(form); toast.success("Recorded"); setOpen(false); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };
  const del = async (r) => {
    if (!window.confirm("Delete this entry?")) return;
    try { await dms.deleteCashEntry(r.id); toast.success("Deleted"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Delete failed"); }
  };

  return (
    <div className="space-y-4">
      <PageHeader title="Cash in Hand" subtitle="Standalone cash register"
        action={canWrite(user?.role) && <Button onClick={() => { setForm({ date: today(), type: "in", amount: "", reference: "", notes: "" }); setOpen(true); }} className="bg-amber-600 hover:bg-amber-700"><Plus className="w-4 h-4 mr-2" />New Entry</Button>} />

      <Card className="p-4 border-amber-200">
        <div className="flex items-center gap-3">
          <Coins className="w-8 h-8 text-amber-600" />
          <div>
            <div className="text-xs uppercase text-slate-500">Cash in Hand</div>
            <div className="text-2xl font-bold text-slate-900">{inr(balance)}</div>
          </div>
        </div>
      </Card>

      <Card className="p-3">
        <div className="flex flex-wrap gap-2 items-end">
          <div><Label className="text-xs">Type</Label>
            <Select value={filters.type || "all"} onValueChange={v => setFilters({ ...filters, type: v === "all" ? "" : v })}>
              <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="all">All</SelectItem><SelectItem value="in">In</SelectItem><SelectItem value="out">Out</SelectItem></SelectContent>
            </Select></div>
          <div><Label className="text-xs">From</Label><Input type="date" value={filters.start} onChange={e => setFilters({ ...filters, start: e.target.value })} /></div>
          <div><Label className="text-xs">To</Label><Input type="date" value={filters.end} onChange={e => setFilters({ ...filters, end: e.target.value })} /></div>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <Table>
          <TableHeader><TableRow><TableHead>Date</TableHead><TableHead>Type</TableHead><TableHead>Reference</TableHead><TableHead className="text-right">Amount</TableHead><TableHead className="text-right">Balance After</TableHead><TableHead>By</TableHead><TableHead></TableHead></TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 ? <TableRow><TableCell colSpan={7} className="text-center text-slate-500 py-8">No cash entries.</TableCell></TableRow>
              : rows.map(r => (
                <TableRow key={r.id}>
                  <TableCell>{r.date}</TableCell>
                  <TableCell><Badge className={r.type === "in" ? "bg-emerald-600" : "bg-rose-600"}>{r.type === "in" ? "Cash In" : "Cash Out"}</Badge></TableCell>
                  <TableCell className="text-xs">{r.reference || "—"}</TableCell>
                  <TableCell className={"text-right font-medium " + (r.type === "in" ? "text-emerald-700" : "text-rose-700")}>{r.type === "in" ? "+" : "−"} {inr(r.amount)}</TableCell>
                  <TableCell className="text-right">{inr(r.balance_after)}</TableCell>
                  <TableCell className="text-xs">{r.created_by_name || "—"}</TableCell>
                  <TableCell className="text-right">{canDelete(user?.role) && <Button size="sm" variant="outline" className="text-rose-600" onClick={() => del(r)}><Trash2 className="w-3 h-3" /></Button>}</TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent><DialogHeader><DialogTitle>New Cash Entry</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3 py-2">
            <div><Label>Type*</Label>
              <Select value={form.type} onValueChange={v => setForm({ ...form, type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="in">Cash In</SelectItem><SelectItem value="out">Cash Out</SelectItem></SelectContent>
              </Select></div>
            <div><Label>Date*</Label><Input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} /></div>
            <div className="col-span-2"><Label>Amount*</Label><Input type="number" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} /></div>
            <div className="col-span-2"><Label>Reference</Label><Input value={form.reference} onChange={e => setForm({ ...form, reference: e.target.value })} /></div>
            <div className="col-span-2"><Label>Notes</Label><Textarea rows={2} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button className="bg-amber-600 hover:bg-amber-700" onClick={save}>Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// =====================================================================
// 4. Cheques Page
// =====================================================================
export function ChequesPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [filters, setFilters] = useState({ direction: "", status: "", start: "", end: "" });
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ cheque_no: "", date: today(), direction: "received", party_name: "", amount: "", bank_name: "", status: "pending", notes: "" });

  const load = async () => {
    try {
      const params = {}; Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v; });
      const d = await dms.listCheques(params); setRows(d.data || []);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed to load"); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filters]);

  const openNew = () => { setEditing(null); setForm({ cheque_no: "", date: today(), direction: "received", party_name: "", amount: "", bank_name: "", status: "pending", notes: "" }); setOpen(true); };
  const openEdit = (r) => { setEditing(r); setForm({ ...r }); setOpen(true); };
  const save = async () => {
    if (!form.cheque_no?.trim()) return toast.error("Cheque no. required");
    if (!(Number(form.amount) > 0)) return toast.error("Amount must be > 0");
    try {
      if (editing) await dms.updateCheque(editing.id, form);
      else await dms.createCheque(form);
      toast.success("Saved"); setOpen(false); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };
  const del = async (r) => {
    if (!window.confirm(`Delete cheque ${r.cheque_no}?`)) return;
    try { await dms.deleteCheque(r.id); toast.success("Deleted"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Delete failed"); }
  };

  const statusColor = { pending: "bg-amber-500", cleared: "bg-emerald-600", bounced: "bg-rose-600", cancelled: "bg-slate-500" };

  return (
    <div className="space-y-4">
      <PageHeader title="Cheques" subtitle="Received and issued cheques register"
        action={canWrite(user?.role) && <Button onClick={openNew} className="bg-amber-600 hover:bg-amber-700"><Plus className="w-4 h-4 mr-2" />New Cheque</Button>} />

      <Card className="p-3">
        <div className="flex flex-wrap gap-2 items-end">
          <div><Label className="text-xs">Direction</Label>
            <Select value={filters.direction || "all"} onValueChange={v => setFilters({ ...filters, direction: v === "all" ? "" : v })}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="all">All</SelectItem><SelectItem value="received">Received</SelectItem><SelectItem value="issued">Issued</SelectItem></SelectContent>
            </Select></div>
          <div><Label className="text-xs">Status</Label>
            <Select value={filters.status || "all"} onValueChange={v => setFilters({ ...filters, status: v === "all" ? "" : v })}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="all">All</SelectItem><SelectItem value="pending">Pending</SelectItem><SelectItem value="cleared">Cleared</SelectItem><SelectItem value="bounced">Bounced</SelectItem><SelectItem value="cancelled">Cancelled</SelectItem></SelectContent>
            </Select></div>
          <div><Label className="text-xs">From</Label><Input type="date" value={filters.start} onChange={e => setFilters({ ...filters, start: e.target.value })} /></div>
          <div><Label className="text-xs">To</Label><Input type="date" value={filters.end} onChange={e => setFilters({ ...filters, end: e.target.value })} /></div>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <Table>
          <TableHeader><TableRow><TableHead>Cheque No.</TableHead><TableHead>Date</TableHead><TableHead>Direction</TableHead><TableHead>Party</TableHead><TableHead>Bank</TableHead><TableHead className="text-right">Amount</TableHead><TableHead>Status</TableHead><TableHead></TableHead></TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 ? <TableRow><TableCell colSpan={8} className="text-center text-slate-500 py-8">No cheques.</TableCell></TableRow>
              : rows.map(r => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono">{r.cheque_no}</TableCell>
                  <TableCell>{r.date}</TableCell>
                  <TableCell><Badge variant={r.direction === "received" ? "default" : "secondary"} className={r.direction === "received" ? "bg-emerald-600" : ""}>{r.direction}</Badge></TableCell>
                  <TableCell>{r.party_name || "—"}</TableCell>
                  <TableCell>{r.bank_name || "—"}</TableCell>
                  <TableCell className="text-right font-medium">{inr(r.amount)}</TableCell>
                  <TableCell><Badge className={statusColor[r.status] || "bg-slate-500"}>{r.status}</Badge></TableCell>
                  <TableCell className="text-right">
                    {canWrite(user?.role) && <Button size="sm" variant="outline" onClick={() => openEdit(r)}><Edit className="w-3 h-3" /></Button>}
                    {canDelete(user?.role) && <Button size="sm" variant="outline" className="ml-1 text-rose-600" onClick={() => del(r)}><Trash2 className="w-3 h-3" /></Button>}
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent><DialogHeader><DialogTitle>{editing ? "Edit Cheque" : "New Cheque"}</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3 py-2">
            <div><Label>Cheque No.*</Label><Input value={form.cheque_no} onChange={e => setForm({ ...form, cheque_no: e.target.value })} /></div>
            <div><Label>Date*</Label><Input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} /></div>
            <div><Label>Direction*</Label>
              <Select value={form.direction} onValueChange={v => setForm({ ...form, direction: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="received">Received</SelectItem><SelectItem value="issued">Issued</SelectItem></SelectContent>
              </Select></div>
            <div><Label>Amount*</Label><Input type="number" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} /></div>
            <div className="col-span-2"><Label>Party Name</Label><Input value={form.party_name} onChange={e => setForm({ ...form, party_name: e.target.value })} /></div>
            <div className="col-span-2"><Label>Bank Name</Label><Input value={form.bank_name} onChange={e => setForm({ ...form, bank_name: e.target.value })} /></div>
            <div className="col-span-2"><Label>Status</Label>
              <Select value={form.status} onValueChange={v => setForm({ ...form, status: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="pending">Pending</SelectItem><SelectItem value="cleared">Cleared</SelectItem><SelectItem value="bounced">Bounced</SelectItem><SelectItem value="cancelled">Cancelled</SelectItem></SelectContent>
              </Select></div>
            <div className="col-span-2"><Label>Notes</Label><Textarea rows={2} value={form.notes || ""} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button className="bg-amber-600 hover:bg-amber-700" onClick={save}>{editing ? "Update" : "Create"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// =====================================================================
// 5. Loan Accounts Page (with drill-down to transactions)
// =====================================================================
export function LoanAccountsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", lender_name: "", principal: "", interest_rate: "", start_date: today(), tenure_months: 12, notes: "" });
  const [txnOpen, setTxnOpen] = useState(false);
  const [txnLoan, setTxnLoan] = useState(null);
  const [txns, setTxns] = useState([]);
  const [txnForm, setTxnForm] = useState({ date: today(), type: "repayment", amount: "", notes: "" });

  const load = async () => {
    try { const d = await dms.listLoans(); setRows(d.data || []); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed to load"); }
  };
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm({ name: "", lender_name: "", principal: "", interest_rate: "", start_date: today(), tenure_months: 12, notes: "" }); setOpen(true); };
  const openEdit = (r) => { setEditing(r); setForm({ ...r }); setOpen(true); };
  const save = async () => {
    if (!form.name?.trim()) return toast.error("Loan name required");
    if (!editing && !(Number(form.principal) > 0)) return toast.error("Principal must be > 0");
    try {
      if (editing) await dms.updateLoan(editing.id, form);
      else await dms.createLoan(form);
      toast.success("Saved"); setOpen(false); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };
  const del = async (r) => {
    if (!window.confirm(`Delete loan ${r.name}?`)) return;
    try { await dms.deleteLoan(r.id); toast.success("Deleted"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Delete failed"); }
  };

  const openTxns = async (r) => {
    setTxnLoan(r);
    setTxnForm({ date: today(), type: "repayment", amount: "", notes: "" });
    try { const d = await dms.listLoanTxns(r.id); setTxns(d.data || []); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    setTxnOpen(true);
  };
  const saveTxn = async () => {
    if (!(Number(txnForm.amount) > 0)) return toast.error("Amount must be > 0");
    try {
      await dms.createLoanTxn({ ...txnForm, loan_account_id: txnLoan.id });
      toast.success("Recorded");
      const d = await dms.listLoanTxns(txnLoan.id); setTxns(d.data || []);
      setTxnForm({ date: today(), type: "repayment", amount: "", notes: "" });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };

  const totalOutstanding = rows.reduce((s, r) => s + (r.outstanding || 0), 0);

  return (
    <div className="space-y-4">
      <PageHeader title="Loan Accounts" subtitle="Standalone loan register — disbursement, repayment, interest"
        action={canWrite(user?.role) && <Button onClick={openNew} className="bg-amber-600 hover:bg-amber-700"><Plus className="w-4 h-4 mr-2" />New Loan</Button>} />

      <Card className="p-4 border-amber-200">
        <div className="flex items-center gap-3">
          <PiggyBank className="w-8 h-8 text-amber-600" />
          <div>
            <div className="text-xs uppercase text-slate-500">Total Outstanding</div>
            <div className="text-2xl font-bold text-slate-900">{inr(totalOutstanding)}</div>
            <div className="text-xs text-slate-500">Across {rows.length} loan(s)</div>
          </div>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <Table>
          <TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Lender</TableHead><TableHead className="text-right">Principal</TableHead><TableHead className="text-right">Rate %</TableHead><TableHead>Start</TableHead><TableHead className="text-right">Outstanding</TableHead><TableHead className="text-right"></TableHead></TableRow></TableHeader>
          <TableBody>
            {rows.length === 0 ? <TableRow><TableCell colSpan={7} className="text-center text-slate-500 py-8">No loans yet.</TableCell></TableRow>
              : rows.map(r => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell>{r.lender_name || "—"}</TableCell>
                  <TableCell className="text-right">{inr(r.principal)}</TableCell>
                  <TableCell className="text-right">{r.interest_rate || 0}%</TableCell>
                  <TableCell>{r.start_date}</TableCell>
                  <TableCell className="text-right font-semibold">{inr(r.outstanding)}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="outline" onClick={() => openTxns(r)}>Ledger</Button>
                    {canWrite(user?.role) && <Button size="sm" variant="outline" className="ml-1" onClick={() => openEdit(r)}><Edit className="w-3 h-3" /></Button>}
                    {canDelete(user?.role) && <Button size="sm" variant="outline" className="ml-1 text-rose-600" onClick={() => del(r)}><Trash2 className="w-3 h-3" /></Button>}
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent><DialogHeader><DialogTitle>{editing ? "Edit Loan" : "New Loan"}</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3 py-2">
            <div className="col-span-2"><Label>Loan Name*</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
            <div className="col-span-2"><Label>Lender</Label><Input value={form.lender_name} onChange={e => setForm({ ...form, lender_name: e.target.value })} /></div>
            {!editing && <>
              <div><Label>Principal*</Label><Input type="number" value={form.principal} onChange={e => setForm({ ...form, principal: e.target.value })} /></div>
              <div><Label>Start Date</Label><Input type="date" value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} /></div>
            </>}
            <div><Label>Interest Rate %</Label><Input type="number" value={form.interest_rate} onChange={e => setForm({ ...form, interest_rate: e.target.value })} /></div>
            <div><Label>Tenure (months)</Label><Input type="number" value={form.tenure_months} onChange={e => setForm({ ...form, tenure_months: e.target.value })} /></div>
            <div className="col-span-2"><Label>Notes</Label><Textarea rows={2} value={form.notes || ""} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button className="bg-amber-600 hover:bg-amber-700" onClick={save}>{editing ? "Update" : "Create"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={txnOpen} onOpenChange={setTxnOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader><DialogTitle>{txnLoan?.name} — Ledger (Outstanding: {inr(txnLoan?.outstanding)})</DialogTitle></DialogHeader>
          <div className="space-y-3 max-h-[70vh] overflow-y-auto">
            {canWrite(user?.role) && (
              <div className="p-3 border rounded bg-slate-50">
                <div className="grid grid-cols-4 gap-2 items-end">
                  <div><Label className="text-xs">Date</Label><Input type="date" value={txnForm.date} onChange={e => setTxnForm({ ...txnForm, date: e.target.value })} /></div>
                  <div><Label className="text-xs">Type</Label>
                    <Select value={txnForm.type} onValueChange={v => setTxnForm({ ...txnForm, type: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent><SelectItem value="repayment">Repayment</SelectItem><SelectItem value="disbursement">Disbursement</SelectItem><SelectItem value="interest">Interest</SelectItem></SelectContent>
                    </Select></div>
                  <div><Label className="text-xs">Amount</Label><Input type="number" value={txnForm.amount} onChange={e => setTxnForm({ ...txnForm, amount: e.target.value })} /></div>
                  <Button className="bg-amber-600 hover:bg-amber-700" onClick={saveTxn}>Add Entry</Button>
                </div>
              </div>
            )}
            <Table>
              <TableHeader><TableRow><TableHead>Date</TableHead><TableHead>Type</TableHead><TableHead className="text-right">Amount</TableHead><TableHead className="text-right">Outstanding After</TableHead><TableHead>Notes</TableHead></TableRow></TableHeader>
              <TableBody>
                {txns.map(t => (
                  <TableRow key={t.id}>
                    <TableCell>{t.date}</TableCell>
                    <TableCell><Badge className={t.type === "repayment" ? "bg-emerald-600" : "bg-amber-500"}>{t.type}</Badge></TableCell>
                    <TableCell className={"text-right font-medium " + (t.type === "repayment" ? "text-emerald-700" : "text-rose-700")}>{t.type === "repayment" ? "−" : "+"} {inr(t.amount)}</TableCell>
                    <TableCell className="text-right">{inr(t.outstanding_after)}</TableCell>
                    <TableCell className="text-xs">{t.notes || "—"}</TableCell>
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
