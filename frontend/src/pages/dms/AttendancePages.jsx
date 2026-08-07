import React, { useEffect, useState, useMemo } from "react";
import { dms, niceDate, inr } from "./api";
import { PageHeader } from "./OwnerPages";
import { useAuth } from "@/context/AuthContext";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LogIn, LogOut, Unlock, Search, MapPin } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";

const getGps = () => new Promise((resolve) => {
  if (!("geolocation" in navigator)) return resolve({});
  navigator.geolocation.getCurrentPosition(
    pos => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
    () => resolve({}),
  );
});

const workingHrs = (p) => {
  if (!p?.in_at) return "—";
  const a = new Date(p.in_at); const b = p.out_at ? new Date(p.out_at) : new Date();
  return ((b - a) / 3600000).toFixed(2) + " h";
};

const ROLE_LABEL = { salesperson: "Salesperson", team_leader: "Team Leader", regional_manager: "Regional Manager" };

// ── Punch card (own) — works for salesperson & team leader ──
function PunchCard({ role, onChange }) {
  const [today, setToday] = useState(null);
  const [canPunchIn, setCanPunchIn] = useState(true);
  const isTL = role === "team_leader";
  const refresh = () => dms.punchToday().then(d => {
    setToday(d.punch || null);
    setCanPunchIn(!!d.can_punch_in);
  }).catch(() => {});
  useEffect(() => { refresh(); }, []);

  const doIn = async () => {
    const g = await getGps();
    try { await (isTL ? dms.tlPunchIn(g) : dms.punchIn(g)); toast.success("Punched in"); }
    catch (e) { toast.error(e?.response?.data?.detail || "Punch-in not allowed"); }
    refresh(); onChange && onChange();
  };
  const doOut = async () => {
    const g = await getGps();
    try { await (isTL ? dms.tlPunchOut(g) : dms.punchOut(g)); toast.success("Punched out"); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    refresh(); onChange && onChange();
  };

  const punchedIn = today?.in_at && !today?.out_at;
  return (
    <Card className="p-5 mb-4">
      <div className="flex items-center gap-4 flex-wrap">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Today</div>
          <div className="text-lg font-bold text-slate-900">
            {today?.in_at ? `In at ${niceDate(today.in_at)}` : "Not punched in"}
            {today?.out_at && <span className="ml-2 text-slate-500">— Out at {niceDate(today.out_at)}</span>}
          </div>
          <div className="text-sm text-slate-600 mt-0.5">Working: <b>{workingHrs(today)}</b></div>
        </div>
        <div className="flex-1" />
        {!punchedIn && canPunchIn && (
          <Button onClick={doIn} className="bg-emerald-600 hover:bg-emerald-700" data-testid="sp-punch-in"><LogIn size={16} className="mr-2" /> Punch In</Button>
        )}
        {!punchedIn && !canPunchIn && !isTL && (
          <div className="text-sm text-rose-600 font-medium">Punch-in closed for today. Ask the Owner to allow again.</div>
        )}
        {punchedIn && (
          <Button onClick={doOut} className="bg-rose-600 hover:bg-rose-700" data-testid="sp-punch-out"><LogOut size={16} className="mr-2" /> Punch Out</Button>
        )}
      </div>
    </Card>
  );
}

export function AttendancePage() {
  const { user } = useAuth();
  const role = user?.role;
  const isOwner = role === "owner" || role === "super_admin" || role === "owner_accountant";
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    dms.attendance().then(d => setRows(d.data || [])).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, []);

  const doReopen = async (spId, name) => {
    try { await dms.reopenPunch(spId); toast.success(`Punch-in re-enabled for ${name}`); refresh(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return rows;
    return rows.filter(r => (r.name || "").toLowerCase().includes(term) || (ROLE_LABEL[r.role] || r.role || "").toLowerCase().includes(term));
  }, [rows, q]);

  const subtitle = role === "salesperson" ? "Your attendance history"
    : role === "team_leader" ? "Your attendance + all assigned salespersons"
    : role === "regional_manager" ? "Your attendance + Team Leaders + Salespersons"
    : "All field staff attendance — allow Punch In when needed";

  return (
    <div>
      <PageHeader title="Attendance" subtitle={subtitle} />
      {(role === "salesperson" || role === "team_leader") && <PunchCard role={role} onChange={refresh} />}

      <Card className="p-3 mb-3">
        <div className="relative max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input value={q} onChange={e => setQ(e.target.value)} placeholder="Search name or role…" className="pl-9" data-testid="attendance-search" />
        </div>
      </Card>

      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            {role !== "salesperson" && <TableHead>Name</TableHead>}
            {role !== "salesperson" && <TableHead>Role</TableHead>}
            <TableHead>Date</TableHead>
            <TableHead>In</TableHead>
            <TableHead>Out</TableHead>
            <TableHead>Working</TableHead>
            {isOwner && <TableHead className="text-right">Action</TableHead>}
          </TableRow></TableHeader>
          <TableBody>
            {loading && <TableRow><TableCell colSpan={7} className="text-center py-6 text-slate-400">Loading…</TableCell></TableRow>}
            {!loading && filtered.length === 0 && <TableRow><TableCell colSpan={7} className="text-center py-6 text-slate-400">No attendance records</TableCell></TableRow>}
            {filtered.map((p, i) => (
              <TableRow key={p.punch_id || i} className={p.is_today ? "bg-amber-50/40" : ""}>
                {role !== "salesperson" && <TableCell className="font-medium">{p.name}</TableCell>}
                {role !== "salesperson" && <TableCell className="text-xs text-slate-500">{ROLE_LABEL[p.role] || p.role}</TableCell>}
                <TableCell>{p.date}</TableCell>
                <TableCell className="text-xs">{p.in_at ? niceDate(p.in_at) : "—"}</TableCell>
                <TableCell className="text-xs">{p.out_at ? niceDate(p.out_at) : <span className="text-emerald-600">In progress…</span>}</TableCell>
                <TableCell className="text-xs font-semibold">{workingHrs(p)}</TableCell>
                {isOwner && (
                  <TableCell className="text-right">
                    {role !== "salesperson" && p.role === "salesperson" && p.can_reopen && (
                      <Button size="sm" variant="outline" onClick={() => doReopen(p.user_id, p.name)} data-testid={`reopen-${p.user_id}`} className="border-amber-400 text-amber-700 hover:bg-amber-50">
                        <Unlock size={14} className="mr-1" /> Allow Punch In
                      </Button>
                    )}
                    {p.reopen_granted && <span className="text-xs text-emerald-600 font-medium">Punch-in re-enabled</span>}
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ── Regional Manager: My Retailers (all under RM's TLs & SPs) ──
export function RmRetailersPage() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    dms.rmRetailers().then(d => setRows(d.data || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);
  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return rows;
    return rows.filter(r => (r.name || "").toLowerCase().includes(term)
      || (r.distributor_name || "").toLowerCase().includes(term)
      || (r.phone || "").includes(term));
  }, [rows, q]);
  return (
    <div>
      <PageHeader title="My Retailers" subtitle="All retailers under your Team Leaders & Salespersons" />
      <Card className="p-3 mb-3">
        <div className="relative max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input value={q} onChange={e => setQ(e.target.value)} placeholder="Search retailer / distributor…" className="pl-9" data-testid="rm-retailer-search" />
        </div>
      </Card>
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            <TableHead>Retailer</TableHead>
            <TableHead>Distributor</TableHead>
            <TableHead>Onboarded By</TableHead>
            <TableHead>Phone</TableHead>
            <TableHead className="text-right">Outstanding</TableHead>
            <TableHead>Last Order</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {loading && <TableRow><TableCell colSpan={6} className="text-center py-6 text-slate-400">Loading…</TableCell></TableRow>}
            {!loading && filtered.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-6 text-slate-400">No retailers found</TableCell></TableRow>}
            {filtered.map(r => (
              <TableRow key={r.id}>
                <TableCell className="font-medium">
                  {r.name}
                  {r.region && <div className="text-xs text-slate-400 flex items-center gap-1"><MapPin size={11} />{r.region}</div>}
                </TableCell>
                <TableCell className="text-sm">{r.distributor_name || "—"}</TableCell>
                <TableCell className="text-xs text-slate-500">{r.onboarded_by_name || "—"}</TableCell>
                <TableCell className="text-xs">{r.phone || "—"}</TableCell>
                <TableCell className="text-right font-semibold">{inr(r.outstanding || 0)}</TableCell>
                <TableCell className="text-xs">{r.last_order_at ? niceDate(r.last_order_at) : "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ── Owner: Retailer Login Access (per-retailer ON/OFF) ──
export function RetailerAccessPage() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const load = () => {
    setLoading(true);
    dms.listRetailers().then(d => setRows(d.data || [])).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);
  const toggle = async (r, enabled) => {
    try {
      await dms.setRetailerLoginAccess(r.id, enabled);
      toast.success(`${r.name}: login ${enabled ? "enabled" : "disabled"}`);
      setRows(prev => prev.map(x => x.id === r.id ? { ...x, login_enabled: enabled } : x));
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return rows;
    return rows.filter(r => (r.name || "").toLowerCase().includes(term) || (r.phone || "").includes(term));
  }, [rows, q]);
  return (
    <div>
      <PageHeader title="Retailer Login Access" subtitle="Enable or disable login for each retailer" />
      <Card className="p-3 mb-3">
        <div className="relative max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input value={q} onChange={e => setQ(e.target.value)} placeholder="Search retailer…" className="pl-9" data-testid="retailer-access-search" />
        </div>
      </Card>
      <Card className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow>
            <TableHead>Retailer</TableHead>
            <TableHead>Phone</TableHead>
            <TableHead>Has Login</TableHead>
            <TableHead className="text-right">Login Access</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {loading && <TableRow><TableCell colSpan={4} className="text-center py-6 text-slate-400">Loading…</TableCell></TableRow>}
            {!loading && filtered.length === 0 && <TableRow><TableCell colSpan={4} className="text-center py-6 text-slate-400">No retailers</TableCell></TableRow>}
            {filtered.map(r => (
              <TableRow key={r.id}>
                <TableCell className="font-medium">{r.name}</TableCell>
                <TableCell className="text-xs">{r.phone || "—"}</TableCell>
                <TableCell className="text-xs">{r.has_login ? <span className="text-emerald-600">Yes</span> : <span className="text-slate-400">No login account</span>}</TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center gap-2 justify-end">
                    <span className={`text-xs font-medium ${r.login_enabled ? "text-emerald-600" : "text-rose-600"}`}>{r.login_enabled ? "Enabled" : "Disabled"}</span>
                    <Switch checked={!!r.login_enabled} onCheckedChange={(v) => toggle(r, v)} disabled={!r.has_login} data-testid={`retailer-login-toggle-${r.id}`} />
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
