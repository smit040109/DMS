import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { dms, niceDate } from "./api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "./OwnerPages";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Plus, KeyRound, LogIn, Search, Users, ShieldCheck } from "lucide-react";

const ROLE_OPTIONS = [
  { value: "owner_accountant",       label: "Owner Accountant" },
  { value: "distributor",            label: "Distributor" },
  { value: "distributor_accountant", label: "Distributor Accountant" },
  { value: "retailer",               label: "Retailer" },
  { value: "salesperson",            label: "Salesperson" },
  { value: "team_leader",            label: "Team Leader" },
  { value: "regional_manager",       label: "Regional Manager" },
];

const ROLE_LABEL = ROLE_OPTIONS.reduce((a, r) => (a[r.value] = r.label, a), {
  owner: "Company Owner", super_admin: "Super Admin",
});

const ROLE_BADGE = {
  owner:                  "bg-teal-100 text-teal-800",
  owner_accountant:       "bg-emerald-100 text-emerald-800",
  distributor:            "bg-blue-100 text-blue-800",
  distributor_accountant: "bg-indigo-100 text-indigo-800",
  retailer:               "bg-amber-100 text-amber-800",
  salesperson:            "bg-fuchsia-100 text-fuchsia-800",
  team_leader:            "bg-purple-100 text-purple-800",
  regional_manager:       "bg-rose-100 text-rose-800",
  super_admin:            "bg-slate-800 text-white",
};

// ============================================================================
// Owner — Master Login Management Panel
// ============================================================================
export function OwnerUsersPage() {
  const nav = useNavigate();
  const { user: me, startImpersonation } = useAuth();
  const [users, setUsers] = useState([]);
  const [roleFilter, setRoleFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  // dialogs
  const [createOpen, setCreateOpen] = useState(false);
  const [resetTarget, setResetTarget] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const d = await dms.ownerListUsers();
      setUsers(d.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const filtered = users.filter(u => {
    if (roleFilter !== "all" && u.role !== roleFilter) return false;
    if (search) {
      const s = search.toLowerCase();
      if (!(u.name || "").toLowerCase().includes(s)
        && !(u.email || "").toLowerCase().includes(s)) return false;
    }
    return true;
  });

  const onImpersonate = async (u) => {
    if (u.id === me?.id) return;
    setBusyId(u.id);
    const r = await startImpersonation(u.id);
    setBusyId(null);
    if (!r.ok) {
      toast.error(r.error || "Failed to impersonate");
      return;
    }
    toast.success(`Signed in as ${u.name}`);
    nav("/dms");
  };

  // group counts for filter tabs
  const counts = users.reduce((a, u) => { a[u.role] = (a[u.role] || 0) + 1; return a; }, {});

  return (
    <div>
      <PageHeader
        title="User Management"
        subtitle="Create users, reset passwords, and log in as any user in the system"
        action={
          <Button onClick={() => setCreateOpen(true)} className="bg-teal-700 hover:bg-teal-800" data-testid="new-user-btn">
            <Plus size={16} className="mr-2" /> New User
          </Button>
        }
      />

      {/* Filter chips */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <button
          onClick={() => setRoleFilter("all")}
          className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${roleFilter === "all" ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-700 border-slate-200"}`}
        >
          All ({users.length})
        </button>
        {ROLE_OPTIONS.map(r => (
          <button
            key={r.value}
            onClick={() => setRoleFilter(r.value)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${roleFilter === r.value ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-700 border-slate-200"}`}
          >
            {r.label} ({counts[r.value] || 0})
          </button>
        ))}
        <div className="flex-1" />
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search name or email"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-8 w-64"
            data-testid="user-search"
          />
        </div>
      </div>

      {/* Table */}
      <Card className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Login ID (Email)</TableHead>
              <TableHead>Login Status</TableHead>
              <TableHead>Last Login</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && (
              <TableRow><TableCell colSpan={6} className="text-center py-10 text-slate-400">Loading…</TableCell></TableRow>
            )}
            {!loading && filtered.length === 0 && (
              <TableRow><TableCell colSpan={6} className="text-center py-10 text-slate-400">No users match</TableCell></TableRow>
            )}
            {filtered.map(u => {
              const isMe = u.id === me?.id;
              return (
                <TableRow key={u.id} data-testid={`user-row-${u.email}`}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 rounded-full bg-teal-100 text-teal-800 text-xs font-bold flex items-center justify-center">
                        {(u.avatar || u.name || "?").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-medium text-slate-900">{u.name}{isMe && <span className="ml-2 text-xs text-teal-700">(You)</span>}</div>
                        {u.phone && <div className="text-xs text-slate-500">{u.phone}</div>}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${ROLE_BADGE[u.role] || "bg-slate-100 text-slate-700"}`}>
                      {ROLE_LABEL[u.role] || u.role}
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-slate-700">{u.email}</TableCell>
                  <TableCell>
                    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${u.online ? "text-emerald-700" : "text-slate-500"}`}>
                      <span className={`h-2 w-2 rounded-full ${u.online ? "bg-emerald-500 animate-pulse" : "bg-slate-300"}`} />
                      {u.online ? "Online" : "Offline"}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-slate-500">
                    {u.last_login_at ? niceDate(u.last_login_at) : "Never"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setResetTarget(u)}
                        data-testid={`reset-pw-${u.email}`}
                      >
                        <KeyRound size={14} className="mr-1" /> Reset
                      </Button>
                      <Button
                        size="sm"
                        disabled={isMe || u.role === "owner" || busyId === u.id}
                        onClick={() => onImpersonate(u)}
                        className="bg-slate-900 hover:bg-slate-800"
                        data-testid={`impersonate-${u.email}`}
                      >
                        <LogIn size={14} className="mr-1" />
                        {busyId === u.id ? "Opening…" : "Login As"}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Card>

      <CreateUserDialog open={createOpen} onClose={() => setCreateOpen(false)} onCreated={refresh} />
      <ResetPasswordDialog user={resetTarget} onClose={() => setResetTarget(null)} />
    </div>
  );
}

// ============================================================================
// Create user dialog
// ============================================================================
function CreateUserDialog({ open, onClose, onCreated }) {
  const empty = { name: "", email: "", phone: "", role: "salesperson", password: "Demo@2026" };
  const [form, setForm] = useState(empty);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (open) setForm(empty); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    if (!form.name || !form.email || !form.password) {
      toast.error("Name, email and password are required");
      return;
    }
    setBusy(true);
    try {
      await dms.ownerCreateUser(form);
      toast.success(`User ${form.email} created`);
      onCreated?.();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to create user");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>New User</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Role</Label>
            <Select value={form.role} onValueChange={v => setForm({ ...form, role: v })}>
              <SelectTrigger data-testid="cu-role"><SelectValue /></SelectTrigger>
              <SelectContent>
                {ROLE_OPTIONS.map(r => (
                  <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Full Name</Label>
            <Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="cu-name" />
          </div>
          <div>
            <Label>Login ID / Email</Label>
            <Input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} data-testid="cu-email" />
          </div>
          <div>
            <Label>Phone (optional)</Label>
            <Input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} data-testid="cu-phone" />
          </div>
          <div>
            <Label>Temporary Password</Label>
            <Input type="text" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} data-testid="cu-pw" />
            <div className="text-[11px] text-slate-500 mt-1">User can be forced to change on first login later.</div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={busy} className="bg-teal-700 hover:bg-teal-800" data-testid="cu-submit">
            {busy ? "Creating…" : "Create User"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// Reset password dialog
// ============================================================================
function ResetPasswordDialog({ user, onClose }) {
  const [pw, setPw] = useState("Demo@2026");
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (user) setPw("Demo@2026"); }, [user]);

  const submit = async () => {
    if (pw.length < 6) { toast.error("Password must be at least 6 characters"); return; }
    setBusy(true);
    try {
      await dms.ownerResetPassword(user.id, pw);
      toast.success(`Password reset for ${user.email}`);
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={!!user} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><ShieldCheck size={18} /> Reset Password</DialogTitle>
        </DialogHeader>
        {user && (
          <div className="space-y-3">
            <div className="text-sm text-slate-600">
              For <span className="font-medium">{user.name}</span> ({user.email})
            </div>
            <div>
              <Label>New Password</Label>
              <Input value={pw} onChange={e => setPw(e.target.value)} data-testid="rp-input" />
            </div>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={busy} className="bg-teal-700 hover:bg-teal-800" data-testid="rp-submit">
            {busy ? "Saving…" : "Reset Password"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// Impersonation banner — global
// ============================================================================
export function ImpersonationBanner() {
  const { impersonation, exitImpersonation, user } = useAuth();
  if (!impersonation) return null;
  return (
    <div className="bg-amber-500 text-white text-sm px-4 py-2 flex items-center justify-center gap-3 sticky top-0 z-40 shadow-md">
      <Users size={16} />
      <span>
        Logged in as <b>{user?.name}</b> ({ROLE_LABEL[user?.role] || user?.role}) — originally{" "}
        <b>{impersonation.owner_user?.name || "Owner"}</b>
      </span>
      <button
        onClick={exitImpersonation}
        className="ml-2 bg-white/20 hover:bg-white/30 px-3 py-1 rounded-md text-xs font-semibold"
        data-testid="exit-impersonation"
      >
        Exit &amp; return to Owner
      </button>
    </div>
  );
}
