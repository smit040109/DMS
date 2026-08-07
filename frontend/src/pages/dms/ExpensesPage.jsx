import React, { useEffect, useMemo, useState } from "react";
import { dms, inr, niceDate } from "./api";
import { PageHeader } from "./OwnerPages";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { Plus, Trash2, Edit, Receipt, Search, Filter as FilterIcon, IndianRupee, Lock } from "lucide-react";

// ============================================================================
// Expenses Page — Phase 2A
// Accessible for ALL roles except Retailer.
// ============================================================================
export function ExpensesPage() {
  const { user } = useAuth();
  const role = user?.role;
  const canDelete = ["owner", "owner_accountant", "super_admin"].includes(role);
  const isSalesperson = role === "salesperson";
  const isRsm = role === "regional_manager";
  const isOwnerSide = ["owner", "owner_accountant", "super_admin"].includes(role);

  const STATUS_META = {
    submitted: { label: "Pending RSM Review", cls: "bg-amber-100 text-amber-700" },
    rsm_approved: { label: "Pending Owner Approval", cls: "bg-sky-100 text-sky-700" },
    approved: { label: "Approved", cls: "bg-emerald-100 text-emerald-700" },
    Approved: { label: "Approved", cls: "bg-emerald-100 text-emerald-700" },
    rejected: { label: "Rejected", cls: "bg-rose-100 text-rose-700" },
    Pending: { label: "Pending", cls: "bg-amber-100 text-amber-700" },
    Reimbursed: { label: "Reimbursed", cls: "bg-slate-100 text-slate-600" },
  };
  const statusBadge = (s) => {
    const m = STATUS_META[s] || { label: s || "—", cls: "bg-slate-100 text-slate-600" };
    return <span className={`text-[11px] px-2 py-0.5 rounded-full ${m.cls}`}>{m.label}</span>;
  };

  const doAction = async (e, action) => {
    let note = "";
    if (action === "reject") {
      note = window.prompt("Reason for rejection (optional):") || "";
    }
    try {
      await dms.expenseAction(e.id, action, note);
      toast.success(action === "approve" ? "Expense approved" : "Expense rejected");
      load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
  };

  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [cats, setCats] = useState([]);
  const [filters, setFilters] = useState({ start: "", end: "", category: "" });
  const [search, setSearch] = useState("");
  const [openForm, setOpenForm] = useState(false);
  const [editing, setEditing] = useState(null); // expense obj or null
  const [form, setForm] = useState({
    category: "",
    amount: "",
    date: new Date().toISOString().slice(0, 10),
    description: "",
    vendor: "",
    receipt_url: "",
    status: "Approved",
  });

  const load = async () => {
    try {
      const params = {};
      if (filters.start) params.start = filters.start;
      if (filters.end) params.end = filters.end;
      if (filters.category) params.category = filters.category;
      const d = await dms.listExpenses(params);
      setRows(d.data || []);
      setTotal(d.total || 0);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed to load expenses"); }
  };

  useEffect(() => { load(); dms.expenseCategories().then(d => setCats(d.data || [])); /* eslint-disable-next-line */ }, [filters.start, filters.end, filters.category]);

  const openNew = () => {
    setEditing(null);
    setForm({ category: "", amount: "", date: new Date().toISOString().slice(0, 10), description: "", vendor: "", receipt_url: "", status: "Approved" });
    setOpenForm(true);
  };
  const openEdit = (e) => {
    setEditing(e);
    setForm({
      category: e.category || "",
      amount: String(e.amount || ""),
      date: e.date || new Date().toISOString().slice(0, 10),
      description: e.description || "",
      vendor: e.vendor || "",
      receipt_url: e.receipt_url || "",
      status: e.status || "Approved",
    });
    setOpenForm(true);
  };

  const submit = async () => {
    if (!form.category.trim() || !form.amount || Number(form.amount) <= 0) {
      toast.error("Category and Amount are required");
      return;
    }
    setBusy(true);
    try {
      const body = {
        category: form.category.trim(),
        amount: Number(form.amount),
        date: form.date,
        description: form.description,
        vendor: form.vendor,
        receipt_url: form.receipt_url,
        status: form.status,
      };
      if (editing) {
        await dms.updateExpense(editing.id, body);
        toast.success("Expense updated");
      } else {
        await dms.createExpense(body);
        toast.success("Expense added");
      }
      setOpenForm(false);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    setBusy(false);
  };

  const doDelete = async (e) => {
    if (!window.confirm(`Delete expense ${e.expense_no}?`)) return;
    try {
      await dms.deleteExpense(e.id);
      toast.success("Expense deleted");
      load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
  };

  const filteredRows = useMemo(() => {
    const n = search.trim().toLowerCase();
    if (!n) return rows;
    return rows.filter(r =>
      (r.expense_no || "").toLowerCase().includes(n) ||
      (r.category || "").toLowerCase().includes(n) ||
      (r.vendor || "").toLowerCase().includes(n) ||
      (r.description || "").toLowerCase().includes(n),
    );
  }, [rows, search]);

  return (
    <div>
      <PageHeader
        title="Expenses"
        subtitle={`${filteredRows.length} of ${rows.length} · Total ${inr(total)}`}
        action={<Button onClick={openNew} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="exp-add-btn"><Plus size={16} className="mr-1" /> Add Expense</Button>}
      />

      {/* Filters */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
        <div className="relative col-span-2 md:col-span-2">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search expense# / vendor / description" className="pl-9" data-testid="exp-search" />
        </div>
        <div>
          <Input type="date" value={filters.start} onChange={e => setFilters({ ...filters, start: e.target.value })} data-testid="exp-start-date" />
        </div>
        <div>
          <Input type="date" value={filters.end} onChange={e => setFilters({ ...filters, end: e.target.value })} data-testid="exp-end-date" />
        </div>
        <Select value={filters.category || "__all__"} onValueChange={v => setFilters({ ...filters, category: v === "__all__" ? "" : v })}>
          <SelectTrigger data-testid="exp-cat-filter"><SelectValue placeholder="Any category" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All categories</SelectItem>
            {cats.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <Card className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Exp #</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Vendor</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Created By</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredRows.length === 0 && (
              <TableRow><TableCell colSpan={9} className="text-center py-8 text-slate-400">No expenses match filters</TableCell></TableRow>
            )}
            {filteredRows.map(e => (
              <TableRow key={e.id} data-testid={`exp-row-${e.id}`}>
                <TableCell className="font-mono text-xs">{e.expense_no}</TableCell>
                <TableCell className="text-xs">{e.date}</TableCell>
                <TableCell>{e.category}</TableCell>
                <TableCell className="text-slate-600">{e.vendor || "—"}</TableCell>
                <TableCell className="text-xs text-slate-500 max-w-xs truncate">{e.description || "—"}</TableCell>
                <TableCell className="text-xs">{e.created_by_name || "—"}<div className="text-[10px] text-slate-400">{e.created_by_role || ""}</div></TableCell>
                <TableCell>{statusBadge(e.status)}</TableCell>
                <TableCell className="text-right font-semibold">{inr(e.amount)}</TableCell>
                <TableCell className="text-right">
                  <div className="flex gap-1 justify-end flex-wrap">
                    {isRsm && e.status === "submitted" && (
                      <>
                        <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white h-7 px-2" onClick={() => doAction(e, "approve")} data-testid={`exp-approve-${e.id}`}>Approve</Button>
                        <Button size="sm" variant="outline" className="text-rose-700 border-rose-200 hover:bg-rose-50 h-7 px-2" onClick={() => doAction(e, "reject")} data-testid={`exp-reject-${e.id}`}>Reject</Button>
                      </>
                    )}
                    {isOwnerSide && e.status === "rsm_approved" && (
                      <>
                        <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white h-7 px-2" onClick={() => doAction(e, "approve")} data-testid={`exp-approve-${e.id}`}>Approve</Button>
                        <Button size="sm" variant="outline" className="text-rose-700 border-rose-200 hover:bg-rose-50 h-7 px-2" onClick={() => doAction(e, "reject")} data-testid={`exp-reject-${e.id}`}>Reject</Button>
                      </>
                    )}
                    {!(isSalesperson && ["rsm_approved", "approved", "rejected"].includes(e.status)) && (
                      <Button size="sm" variant="outline" onClick={() => openEdit(e)} data-testid={`exp-edit-${e.id}`}><Edit size={12} /></Button>
                    )}
                    {canDelete && <Button size="sm" variant="outline" className="text-rose-700 border-rose-200 hover:bg-rose-50" onClick={() => doDelete(e)} data-testid={`exp-del-${e.id}`}><Trash2 size={12} /></Button>}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={openForm} onOpenChange={setOpenForm}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? `Edit Expense ${editing.expense_no}` : "New Expense"}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Category *</Label>
                <Input list="expense-cats" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} data-testid="exp-form-category" />
                <datalist id="expense-cats">{cats.map(c => <option key={c} value={c} />)}</datalist>
              </div>
              <div>
                <Label>Date *</Label>
                <Input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} data-testid="exp-form-date" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Amount (₹) *</Label>
                <div className="relative">
                  <IndianRupee size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <Input type="number" step="0.01" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} className="pl-8" data-testid="exp-form-amount" />
                </div>
              </div>
              {!isSalesperson && (
                <div>
                  <Label>Status</Label>
                  <Select value={form.status} onValueChange={v => setForm({ ...form, status: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Approved">Approved</SelectItem>
                      <SelectItem value="Pending">Pending</SelectItem>
                      <SelectItem value="Reimbursed">Reimbursed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
            <div>
              <Label>Vendor</Label>
              <Input value={form.vendor} onChange={e => setForm({ ...form, vendor: e.target.value })} placeholder="Optional" data-testid="exp-form-vendor" />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea rows={2} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} data-testid="exp-form-desc" />
            </div>
            {!isSalesperson && (
              <div>
                <Label>Receipt URL (optional)</Label>
                <Input value={form.receipt_url} onChange={e => setForm({ ...form, receipt_url: e.target.value })} placeholder="https://…" />
              </div>
            )}
            {isSalesperson && (
              <div className="text-xs text-slate-500 bg-slate-50 rounded-lg p-2.5">
                Your expense will be sent to your Regional Manager for review, then to the Owner for final approval.
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenForm(false)}>Cancel</Button>
            <Button className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" disabled={busy} onClick={submit} data-testid="exp-form-save">{editing ? "Save Changes" : "Add Expense"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
