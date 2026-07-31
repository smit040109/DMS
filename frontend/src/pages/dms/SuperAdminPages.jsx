import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { dms, inr } from "./api";
import { PageHeader } from "./OwnerPages";
import { useAuth } from "@/context/AuthContext";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { UserCog, LogIn, ShieldCheck, Search } from "lucide-react";
import api from "@/lib/api";

const ROLE_COLORS = {
  super_admin: "bg-purple-100 text-purple-800",
  owner: "bg-teal-100 text-teal-800",
  owner_accountant: "bg-teal-50 text-teal-700",
  distributor: "bg-blue-100 text-blue-800",
  distributor_accountant: "bg-blue-50 text-blue-700",
  retailer: "bg-amber-100 text-amber-800",
  salesperson: "bg-indigo-100 text-indigo-800",
  team_leader: "bg-fuchsia-100 text-fuchsia-800",
  regional_manager: "bg-rose-100 text-rose-800",
};

export function SuperAdminDashboardPage() {
  const [kpis, setKpis] = useState(null);
  const nav = useNavigate();
  useEffect(() => { dms.superAdminDashboard().then(d => setKpis(d.kpis)); }, []);
  const cards = [
    { label: "Owners", value: kpis?.owners },
    { label: "Team Leaders", value: kpis?.team_leaders },
    { label: "Salespersons", value: kpis?.salespersons },
    { label: "Distributors", value: kpis?.distributors },
    { label: "Retailers", value: kpis?.retailers },
    { label: "Primary Orders", value: kpis?.primary_orders },
    { label: "Secondary Orders", value: kpis?.secondary_orders },
  ];
  return (
    <div>
      <PageHeader title="Super Admin Control Panel" subtitle="Full visibility across the DMS"
        action={<Button onClick={() => nav("/dms/admin/users")} className="bg-purple-700 hover:bg-purple-800"><UserCog size={16} className="mr-1" /> Manage Users & Impersonate</Button>} />
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {cards.map(c => (
          <Card key={c.label} className="p-4">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">{c.label}</div>
            <div className="mt-1 text-xl font-bold">{c.value ?? "—"}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}

export function SuperAdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const nav = useNavigate();
  useEffect(() => { dms.adminUsers().then(d => setUsers(d.data)); }, []);

  const impersonate = async (u) => {
    if (!window.confirm(`Sign in as ${u.name} (${u.role})? Your super admin session will be replaced.`)) return;
    try {
      const r = await dms.impersonate(u.id);
      // swap token
      localStorage.setItem("go_oil_token", r.token);
      // set cookie too via login redirect
      // A cleaner approach: reload to /dms and rely on new bearer token; also set cookie via a fake login endpoint
      toast.success(`Now viewing as ${u.name}`);
      // Reload the page to reboot AuthContext with new token
      window.location.href = "/dms";
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    }
  };

  const filtered = users.filter(u => {
    if (roleFilter && u.role !== roleFilter) return false;
    if (q && !(u.name.toLowerCase().includes(q.toLowerCase()) || u.email.toLowerCase().includes(q.toLowerCase()))) return false;
    return true;
  });

  const roles = [...new Set(users.map(u => u.role))].sort();

  return (
    <div>
      <PageHeader title="All Users" subtitle="Login as any user to preview their view" back="/dms" />
      <Card className="p-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input value={q} onChange={e => setQ(e.target.value)} placeholder="Search by name or email…" className="pl-8" data-testid="admin-search" />
          </div>
          <select value={roleFilter} onChange={e => setRoleFilter(e.target.value)} className="h-10 px-3 rounded-lg border border-slate-200 text-sm" data-testid="admin-role-filter">
            <option value="">All Roles</option>
            {roles.map(r => <option key={r} value={r}>{r.replace(/_/g, " ")}</option>)}
          </select>
        </div>
      </Card>
      <Card>
        <Table>
          <TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Email</TableHead><TableHead>Role</TableHead><TableHead>Tenant</TableHead><TableHead className="w-32"></TableHead></TableRow></TableHeader>
          <TableBody>
            {filtered.map(u => (
              <TableRow key={u.id}>
                <TableCell className="font-medium">{u.name}</TableCell>
                <TableCell className="text-sm text-slate-600">{u.email}</TableCell>
                <TableCell><span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded ${ROLE_COLORS[u.role] || "bg-slate-100 text-slate-700"}`}>{u.role?.replace(/_/g, " ")}</span></TableCell>
                <TableCell className="text-xs text-slate-500 font-mono">{u.tenant_id || "—"}</TableCell>
                <TableCell className="text-right">
                  <Button size="sm" variant="outline" onClick={() => impersonate(u)} data-testid={`impersonate-${u.id}`}><LogIn size={12} className="mr-1" /> Login as</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {filtered.length === 0 && <div className="p-8 text-center text-sm text-slate-500">No users match</div>}
      </Card>
    </div>
  );
}
