import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectTrigger, SelectContent, SelectItem, SelectValue,
} from "@/components/ui/select";
import { Sparkles, UserPlus, Shield, Database, Bell, Settings2, BadgeCheck, Search } from "lucide-react";
import StatusPill from "@/components/common/StatusPill";
import { ROLE_LABELS } from "@/lib/nav";
import { useAuth } from "@/context/AuthContext";

// ---------- Users ----------
export function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", name: "", role: "sales_executive", password: "GoOil@2026" });
  const { register } = useAuth();

  const load = () => {
    setLoading(true);
    api.get("/admin/users").then((r) => setUsers(r.data.data || [])).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const create = async () => {
    const r = await register(form);
    if (r.ok) { setOpen(false); load(); }
  };

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Administration", "User Management"]}
        title="User Management"
        subtitle="Provision users across all 8 roles with full audit trail"
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="user-invite">
                <UserPlus size={15} className="mr-2" /> Invite user
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader><DialogTitle>Invite a new user</DialogTitle></DialogHeader>
              <div className="space-y-4">
                <div><Label>Full name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="user-name" /></div>
                <div><Label>Email</Label><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="user-email" /></div>
                <div><Label>Temporary password</Label><Input value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} data-testid="user-password" /></div>
                <div>
                  <Label>Role</Label>
                  <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                    <SelectTrigger data-testid="user-role"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(ROLE_LABELS).map(([k, v]) => (
                        <SelectItem key={k} value={k}>{v}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                <Button onClick={create} className="bg-gold hover:bg-gold-dark text-white" data-testid="user-create">Send invitation</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />
      <DataTable
        data={users}
        loading={loading}
        columns={[
          { key: "avatar", label: "", width: "56px",
            render: (r) => <div className="h-8 w-8 rounded-full bg-gold/20 text-gold-dark flex items-center justify-center font-semibold text-xs">{r.avatar || r.name?.[0]}</div>,
          },
          { key: "name", label: "Name" },
          { key: "email", label: "Email" },
          { key: "role", label: "Role", render: (r) => ROLE_LABELS[r.role] || r.role, type: "chip" },
          { key: "branch_id", label: "Branch" },
          { key: "title", label: "Title" },
        ]}
        testId="users-table"
      />
    </div>
  );
}

// ---------- Roles ----------
export function RolesPage() {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.get("/collections/roles").then((r) => setRoles(r.data.data || [])).finally(() => setLoading(false));
  }, []);
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Administration", "Roles"]}
        title="Role Management"
        subtitle="Fine-grained roles with permission scopes across every module"
      />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {loading && <div className="text-ink-muted">Loading roles…</div>}
        {roles.map((r) => (
          <div key={r.id} className="bg-white rounded-xl border border-[#E5E7EB] card-soft p-5 hover:shadow-card transition" data-testid={`role-card-${r.key}`}>
            <div className="flex items-center gap-2">
              <div className="h-10 w-10 rounded-lg bg-gold/15 text-gold-dark flex items-center justify-center">
                <Shield size={17} />
              </div>
              <div>
                <div className="font-display font-bold text-ink">{r.name}</div>
                <div className="text-[11px] text-ink-muted">{r.key}</div>
              </div>
            </div>
            <p className="mt-4 text-sm text-ink-muted leading-relaxed">{r.description}</p>
            <div className="mt-5 grid grid-cols-2 gap-3 text-center">
              <div className="rounded-lg border border-[#E5E7EB] py-2">
                <div className="font-display font-bold text-lg text-ink">{r.permission_count}</div>
                <div className="text-[11px] text-ink-muted uppercase tracking-wider">Permissions</div>
              </div>
              <div className="rounded-lg border border-[#E5E7EB] py-2">
                <div className="font-display font-bold text-lg text-ink">{r.user_count}</div>
                <div className="text-[11px] text-ink-muted uppercase tracking-wider">Users</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Master Data ----------
export function MasterDataPage() {
  const [data, setData] = useState({});
  useEffect(() => { api.get("/master-data").then((r) => setData(r.data)); }, []);
  const sections = [
    { key: "tax_rates", title: "Tax Rates" },
    { key: "uoms", title: "Units of Measure" },
    { key: "payment_terms", title: "Payment Terms" },
    { key: "regions", title: "Regions" },
  ];
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Administration", "Master Data"]}
        title="Master Data"
        subtitle="Reference data that powers every workflow across the platform"
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {sections.map((s) => (
          <div key={s.key} className="bg-white rounded-xl border border-[#E5E7EB] card-soft overflow-hidden">
            <div className="px-5 py-4 border-b border-[#E5E7EB] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database size={16} className="text-gold-dark" />
                <div className="font-display font-bold text-ink">{s.title}</div>
              </div>
              <span className="text-xs text-ink-muted">{(data[s.key] || []).length} entries</span>
            </div>
            <ul className="divide-y divide-[#F1F5F9]">
              {(data[s.key] || []).map((row) => (
                <li key={row.id} className="px-5 py-3 flex items-center justify-between text-sm">
                  <div className="font-medium text-ink">{row.name || row.code}</div>
                  <div className="text-ink-muted text-xs">
                    {row.rate ? `${row.rate}%` : row.days !== undefined ? `${row.days} days` : row.type || row.code || "—"}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Reports ----------
export function ReportsPage() {
  const REPORTS = [
    { key: "sales-summary", name: "Sales Summary", desc: "Region & branch level revenue with YoY comparison", icon: BadgeCheck },
    { key: "receivables", name: "Receivables Aging", desc: "0-30, 31-60, 61-90 and 90+ ageing buckets", icon: Bell },
    { key: "stock-position", name: "Stock Position", desc: "SKU-wise stock across all warehouses", icon: Database },
    { key: "dispatch-sla", name: "Dispatch SLA", desc: "SLA compliance for primary & secondary dispatches", icon: Sparkles },
    { key: "gst", name: "GST Filing", desc: "Consolidated GSTR-1/3B export", icon: BadgeCheck },
    { key: "trade-scheme", name: "Trade Scheme Utilization", desc: "Cashback & coupon burn analysis", icon: Bell },
  ];
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Insights", "Reports"]}
        title="Reports"
        subtitle="Board-ready operational and financial reports"
        actions={<Button className="bg-gold hover:bg-gold-dark text-white h-10" data-testid="reports-schedule">Schedule report</Button>}
      />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {REPORTS.map((r) => (
          <div key={r.key} className="bg-white rounded-xl border border-[#E5E7EB] card-soft p-5 hover:shadow-card transition group" data-testid={`report-${r.key}`}>
            <div className="flex items-start justify-between">
              <div className="h-10 w-10 rounded-lg bg-gold/15 text-gold-dark flex items-center justify-center">
                <r.icon size={17} />
              </div>
              <StatusPill value="Active" size="sm" />
            </div>
            <div className="mt-4 font-display font-bold text-ink">{r.name}</div>
            <p className="mt-1.5 text-xs text-ink-muted leading-relaxed">{r.desc}</p>
            <div className="mt-4 flex gap-2">
              <Button variant="outline" size="sm" className="border-[#E5E7EB] h-8" data-testid={`report-${r.key}-view`}>View</Button>
              <Button variant="outline" size="sm" className="border-[#E5E7EB] h-8" data-testid={`report-${r.key}-export`}>Export</Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Analytics ----------
export function AnalyticsPage() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/dashboard/analytics").then((r) => setData(r.data)); }, []);
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Insights", "Analytics"]}
        title="Analytics"
        subtitle="Cross-module business intelligence for decision makers"
      />
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl border border-[#E5E7EB] card-soft p-5">
          <div className="font-display font-bold text-ink">Top SKUs by revenue</div>
          <p className="text-xs text-ink-muted mb-4">Trailing 30 days</p>
          <DataTable
            data={(data?.top_skus) || []}
            searchable={false}
            columns={[
              { key: "sku", label: "SKU" },
              { key: "product", label: "Product" },
              { key: "units", label: "Units", align: "right", render: (r) => r.units?.toLocaleString() },
              { key: "revenue", label: "Revenue", type: "currency", align: "right" },
            ]}
            pageSize={8}
            testId="analytics-top-skus"
          />
        </div>
        <div className="bg-white rounded-xl border border-[#E5E7EB] card-soft p-5">
          <div className="font-display font-bold text-ink">Branch health</div>
          <p className="text-xs text-ink-muted mb-4">On-track vs at-risk workflows</p>
          <DataTable
            data={(data?.branch_health) || []}
            searchable={false}
            columns={[
              { key: "branch", label: "Branch" },
              { key: "on_track", label: "On track", align: "right" },
              { key: "at_risk", label: "At risk", align: "right" },
              { key: "blocked", label: "Blocked", align: "right" },
            ]}
            pageSize={8}
            testId="analytics-branch-health"
          />
        </div>
      </div>
    </div>
  );
}

// ---------- AI Assistant page ----------
export function AiAssistantPage() {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);

  const send = async () => {
    const msg = prompt.trim();
    if (!msg) return;
    setMessages((m) => [...m, { role: "user", text: msg }]);
    setPrompt("");
    setBusy(true);
    try {
      const { data } = await api.post("/ai/ask", { prompt: msg });
      setMessages((m) => [...m, { role: "assistant", text: data.reply || "…" }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: "⚠️ AI service unavailable." }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "AI Assistant"]}
        title="AI Copilot"
        subtitle="Ask the GO OIL DMS Copilot about your business. Powered by Claude Sonnet 4.5."
      />
      <div className="bg-white rounded-xl border border-[#E5E7EB] card-soft p-6 min-h-[420px] flex flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto max-h-[60vh]">
          {messages.length === 0 && (
            <div className="text-sm text-ink-muted">
              Start a conversation. The AI is grounded on your live product, order, and invoice counts.
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
              <span className={`inline-block max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                m.role === "user" ? "bg-ink text-white" : "bg-canvas border border-[#E5E7EB] text-ink whitespace-pre-wrap"
              }`}>{m.text}</span>
            </div>
          ))}
          {busy && <div className="text-xs text-ink-muted">Thinking…</div>}
        </div>
        <div className="mt-4 flex items-center gap-2">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
            <Input value={prompt} onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Ask about orders, KPIs, inventory..."
              className="pl-9 bg-canvas border-[#E5E7EB] h-11"
              data-testid="ai-page-input"
            />
          </div>
          <Button onClick={send} disabled={busy} className="bg-gold hover:bg-gold-dark text-white h-11" data-testid="ai-page-send">
            <Sparkles size={15} className="mr-1.5" /> Ask
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---------- Settings ----------
export function SettingsPage() {
  const [saved, setSaved] = useState(false);
  const { user } = useAuth();
  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={["Dashboard", "Settings"]}
        title="Settings"
        subtitle="Preferences, integrations and audit configuration"
      />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <div className="bg-white rounded-xl border border-[#E5E7EB] card-soft p-6">
            <div className="flex items-center gap-2 mb-4">
              <Settings2 size={16} className="text-gold-dark" />
              <div className="font-display font-bold text-ink">Profile</div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div><Label>Full name</Label><Input defaultValue={user?.name} data-testid="settings-name" /></div>
              <div><Label>Email</Label><Input defaultValue={user?.email} data-testid="settings-email" /></div>
              <div><Label>Title</Label><Input defaultValue={user?.title} data-testid="settings-title" /></div>
              <div><Label>Role</Label><Input defaultValue={ROLE_LABELS[user?.role]} disabled /></div>
            </div>
            <div className="mt-5 flex items-center gap-3">
              <Button className="bg-gold hover:bg-gold-dark text-white" data-testid="settings-save" onClick={() => { setSaved(true); setTimeout(() => setSaved(false), 2000); }}>
                Save changes
              </Button>
              {saved && <span className="text-xs text-emerald-700">Saved</span>}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-[#E5E7EB] card-soft p-6">
            <div className="font-display font-bold text-ink mb-4">Integrations</div>
            <ul className="divide-y divide-[#F1F5F9]">
              {[
                { name: "Claude Sonnet 4.5", desc: "AI Copilot", status: "Connected" },
                { name: "GSTN e-invoicing", desc: "Auto e-invoice submission", status: "Pending" },
                { name: "SAP ERP core", desc: "Financial GL sync", status: "Connected" },
                { name: "Twilio SMS", desc: "Delivery notifications", status: "Paused" },
              ].map((it) => (
                <li key={it.name} className="py-3 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-ink">{it.name}</div>
                    <div className="text-xs text-ink-muted">{it.desc}</div>
                  </div>
                  <StatusPill value={it.status} size="sm" />
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-[#E5E7EB] card-soft p-6">
          <div className="font-display font-bold text-ink mb-3">System</div>
          <ul className="text-sm space-y-3">
            <li className="flex justify-between"><span className="text-ink-muted">Version</span><span className="font-semibold text-ink">v4.2.18</span></li>
            <li className="flex justify-between"><span className="text-ink-muted">Last sync</span><span className="font-semibold text-ink">2 mins ago</span></li>
            <li className="flex justify-between"><span className="text-ink-muted">Database</span><span className="font-semibold text-ink">MongoDB</span></li>
            <li className="flex justify-between"><span className="text-ink-muted">Region</span><span className="font-semibold text-ink">ap-south-1</span></li>
          </ul>
        </div>
      </div>
    </div>
  );
}
