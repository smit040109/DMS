/**
 * VayuERP — Platform & Tenant Admin module pages.
 *
 * Uses the SAME primitives (PageHeader / DataTable / KpiCard / Dialog / Card)
 * as the rest of the app so the SaaS chrome inherits the existing design.
 */
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import KpiCard from "@/components/common/KpiCard";
import StatusPill from "@/components/common/StatusPill";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { useTenant } from "@/context/TenantContext";
import { useAuth } from "@/context/AuthContext";
import {
  Building, Building2, Sparkles, KeyRound, Webhook, Palette, Crown, LayoutGrid, Megaphone, Flag,
  DatabaseBackup, Repeat, CreditCard, LineChart, Copy, Check, Trash2, Plus, ArrowRight,
} from "lucide-react";

const CURRENCIES = ["USD", "EUR", "GBP", "INR", "AED", "NGN", "ZAR", "KES", "PKR", "SGD", "JPY", "CNY"];
const TIMEZONES = ["UTC", "Africa/Lagos", "Asia/Kolkata", "Asia/Dubai", "America/New_York", "Europe/London", "Asia/Singapore", "Asia/Tokyo", "Australia/Sydney"];
const COUNTRIES = ["Nigeria", "India", "United Arab Emirates", "United Kingdom", "United States", "Kenya", "South Africa", "Singapore", "Pakistan", "Ghana", "Egypt"];
const INDUSTRIES = ["distribution", "lubricants", "fmcg", "chemicals", "paint", "pharma", "automotive", "manufacturing"];

// ============================================================================
// ONBOARDING WIZARD — 5-step guided flow
// ============================================================================
export function TenantOnboardingPage() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    name: "",
    slug: "",
    industry: "distribution",
    country: "Nigeria",
    currency: "USD",
    timezone: "UTC",
    tax: { tax_name: "VAT", tax_percent: 7.5, tax_number: "" },
    brand_colors: { primary: "#0F172A", secondary: "#F59E0B", accent: "#10B981" },
    logo_url: "",
    address: { line1: "", city: "", state: "", country: "", postal_code: "" },
    contact: { email: "", phone: "", website: "" },
    admin: { email: "", name: "", password: "" },
    plan: "starter",
  });

  const [plans, setPlans] = useState([]);
  useEffect(() => { api.get("/platform/plans").then((r) => setPlans(r.data.data || [])); }, []);

  const setField = (path, v) => {
    setForm((f) => {
      const next = { ...f };
      const keys = path.split(".");
      let cur = next;
      for (let i = 0; i < keys.length - 1; i++) {
        cur[keys[i]] = { ...cur[keys[i]] };
        cur = cur[keys[i]];
      }
      cur[keys[keys.length - 1]] = v;
      return next;
    });
  };

  const steps = ["Company", "Region & Currency", "Tax & Contact", "Branding", "Admin & Plan"];

  const canNext = () => {
    if (step === 0) return form.name && form.name.length >= 2;
    if (step === 1) return form.country && form.currency && form.timezone;
    if (step === 2) return form.tax.tax_name && form.contact.email;
    if (step === 4) return form.admin.email && form.admin.name && form.admin.password.length >= 8;
    return true;
  };

  const submit = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/platform/tenants", form);
      toast.success(`Tenant "${data.tenant.name}" created`);
      nav("/app/platform/tenants");
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="max-w-3xl mx-auto py-6">
      <PageHeader
        eyebrow="VayuERP · Platform"
        title="Onboard a new tenant"
        subtitle="Guided setup — brand, region, tax, admin. Complete data isolation, ready in seconds."
      />
      <Card className="p-6 mt-6">
        {/* Stepper */}
        <div className="flex items-center gap-2 mb-8">
          {steps.map((s, i) => (
            <React.Fragment key={s}>
              <div className={`flex items-center gap-2 ${i <= step ? "text-ink" : "text-ink-muted"}`}>
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${i < step ? "bg-emerald-500 text-white" : i === step ? "bg-ink text-white" : "bg-canvas border border-[#E5E7EB]"}`}>
                  {i < step ? <Check size={12} /> : i + 1}
                </div>
                <span className="text-xs font-semibold hidden md:inline">{s}</span>
              </div>
              {i < steps.length - 1 && <div className={`flex-1 h-px ${i < step ? "bg-emerald-500" : "bg-[#E5E7EB]"}`} />}
            </React.Fragment>
          ))}
        </div>

        {step === 0 && (
          <div className="space-y-4">
            <div>
              <Label>Company Name *</Label>
              <Input value={form.name} onChange={(e) => setField("name", e.target.value)} placeholder="Acme Corporation" className="mt-1.5" data-testid="onboard-name" />
            </div>
            <div>
              <Label>URL Slug (optional)</Label>
              <Input value={form.slug} onChange={(e) => setField("slug", e.target.value)} placeholder="acme (auto-generated if empty)" className="mt-1.5" />
              <p className="text-xs text-ink-muted mt-1">Used for tenant identification. Auto-derived from name if left blank.</p>
            </div>
            <div>
              <Label>Industry *</Label>
              <Select value={form.industry} onValueChange={(v) => setField("industry", v)}>
                <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {INDUSTRIES.map((i) => <SelectItem key={i} value={i}>{i.charAt(0).toUpperCase() + i.slice(1)}</SelectItem>)}
                </SelectContent>
              </Select>
              <p className="text-xs text-ink-muted mt-1">Determines default labels: SKU → Grade/Shade/Part etc., unit → litre/kg/unit.</p>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Country *</Label>
              <Select value={form.country} onValueChange={(v) => setField("country", v)}>
                <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                <SelectContent>{COUNTRIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label>Currency *</Label>
              <Select value={form.currency} onValueChange={(v) => setField("currency", v)}>
                <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                <SelectContent>{CURRENCIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="md:col-span-2">
              <Label>Timezone *</Label>
              <Select value={form.timezone} onValueChange={(v) => setField("timezone", v)}>
                <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                <SelectContent>{TIMEZONES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Tax Name *</Label>
              <Input value={form.tax.tax_name} onChange={(e) => setField("tax.tax_name", e.target.value)} className="mt-1.5" />
            </div>
            <div>
              <Label>Tax %</Label>
              <Input type="number" step="0.01" value={form.tax.tax_percent} onChange={(e) => setField("tax.tax_percent", parseFloat(e.target.value || "0"))} className="mt-1.5" />
            </div>
            <div className="md:col-span-2">
              <Label>Tax Registration Number</Label>
              <Input value={form.tax.tax_number} onChange={(e) => setField("tax.tax_number", e.target.value)} className="mt-1.5" />
            </div>
            <div>
              <Label>Contact Email *</Label>
              <Input type="email" value={form.contact.email} onChange={(e) => setField("contact.email", e.target.value)} className="mt-1.5" />
            </div>
            <div>
              <Label>Contact Phone</Label>
              <Input value={form.contact.phone} onChange={(e) => setField("contact.phone", e.target.value)} className="mt-1.5" />
            </div>
            <div className="md:col-span-2">
              <Label>Website</Label>
              <Input value={form.contact.website} onChange={(e) => setField("contact.website", e.target.value)} className="mt-1.5" />
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <div>
              <Label>Logo URL</Label>
              <Input value={form.logo_url} onChange={(e) => setField("logo_url", e.target.value)} placeholder="https://..." className="mt-1.5" />
            </div>
            <div className="grid grid-cols-3 gap-3">
              {["primary", "secondary", "accent"].map((k) => (
                <div key={k}>
                  <Label className="capitalize">{k}</Label>
                  <div className="flex items-center gap-2 mt-1.5">
                    <Input type="color" value={form.brand_colors[k]} onChange={(e) => setField(`brand_colors.${k}`, e.target.value)} className="w-14 h-10 p-1" />
                    <Input value={form.brand_colors[k]} onChange={(e) => setField(`brand_colors.${k}`, e.target.value)} className="flex-1" />
                  </div>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-[#E5E7EB] p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl" style={{ background: `linear-gradient(135deg, ${form.brand_colors.secondary} 0%, ${form.brand_colors.primary} 100%)` }} />
              <div>
                <div className="font-display font-extrabold text-lg" style={{ color: form.brand_colors.primary }}>{form.name || "Company Name"}</div>
                <div className="text-xs uppercase tracking-widest text-ink-muted">Brand preview</div>
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Initial Admin Name *</Label>
                <Input value={form.admin.name} onChange={(e) => setField("admin.name", e.target.value)} className="mt-1.5" data-testid="onboard-admin-name" />
              </div>
              <div>
                <Label>Admin Email *</Label>
                <Input type="email" value={form.admin.email} onChange={(e) => setField("admin.email", e.target.value)} className="mt-1.5" data-testid="onboard-admin-email" />
              </div>
              <div className="md:col-span-2">
                <Label>Password (min 8 chars) *</Label>
                <Input type="password" value={form.admin.password} onChange={(e) => setField("admin.password", e.target.value)} className="mt-1.5" data-testid="onboard-admin-password" />
              </div>
            </div>
            <div>
              <Label>Subscription Plan</Label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
                {plans.map((p) => (
                  <button
                    key={p.key}
                    type="button"
                    onClick={() => setField("plan", p.key)}
                    className={`text-left rounded-xl border-2 p-4 transition ${form.plan === p.key ? "border-gold bg-gold/5" : "border-[#E5E7EB] hover:border-gold/40"}`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-semibold">{p.name}</div>
                        <div className="text-xs text-ink-muted mt-0.5">
                          ${p.price_monthly}/mo · ${p.price_yearly}/yr
                        </div>
                      </div>
                      {p.trial_days > 0 && <Badge className="bg-emerald-100 text-emerald-700">{p.trial_days}d trial</Badge>}
                    </div>
                    <div className="mt-2 text-xs text-ink-muted">
                      Users: {p.limits?.users === -1 ? "Unlimited" : p.limits?.users || "—"} · Storage: {p.limits?.storage_gb === -1 ? "Unlimited" : `${p.limits?.storage_gb || 0} GB`}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Buttons */}
        <div className="flex justify-between mt-8 pt-6 border-t border-[#E5E7EB]">
          <Button variant="outline" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>Back</Button>
          {step < steps.length - 1 ? (
            <Button onClick={() => setStep(step + 1)} disabled={!canNext()} className="bg-gold hover:bg-gold-dark text-white" data-testid="onboard-next">
              Continue <ArrowRight size={14} className="ml-2" />
            </Button>
          ) : (
            <Button onClick={submit} disabled={!canNext() || busy} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="onboard-submit">
              {busy ? "Creating..." : "Create Tenant"}
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}

// ============================================================================
// PLATFORM: TENANTS LIST
// ============================================================================
export function PlatformTenantsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  const load = () => {
    setLoading(true);
    api.get("/platform/tenants").then((r) => setRows(r.data.data || [])).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const toggleStatus = async (t, status) => {
    try {
      await api.put(`/platform/tenants/${t.id}/status`, { status });
      toast.success(`Tenant ${status}`);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="VayuERP · Platform"
        title="Tenants"
        subtitle="Every company using VayuERP is a tenant with fully isolated data."
        actions={<Button onClick={() => nav("/app/platform/onboard")} className="bg-gold hover:bg-gold-dark text-white"><Plus size={14} className="mr-1.5" /> Onboard Tenant</Button>}
      />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
        <KpiCard label="Total tenants" value={rows.length} />
        <KpiCard label="Active" value={rows.filter((r) => r.status === "active").length} />
        <KpiCard label="Suspended" value={rows.filter((r) => r.status === "suspended").length} />
        <KpiCard label="Total users" value={rows.reduce((s, r) => s + (r.user_count || 0), 0)} />
      </div>
      <div className="mt-6">
        <DataTable
          loading={loading}
          columns={[
            { key: "name", label: "Tenant", render: (r) => (
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold" style={{ background: `linear-gradient(135deg, ${r.brand_colors?.secondary || "#F59E0B"}, ${r.brand_colors?.primary || "#0F172A"})` }}>{(r.name || "?").charAt(0)}</div>
                <div>
                  <div className="font-semibold text-ink">{r.name}</div>
                  <div className="text-xs text-ink-muted">{r.slug} · {r.industry}</div>
                </div>
              </div>
            )},
            { key: "country", label: "Region", render: (r) => `${r.country} · ${r.currency}` },
            { key: "user_count", label: "Users" },
            { key: "plan", label: "Plan", render: (r) => <Badge className="capitalize">{r.plan || "—"}</Badge> },
            { key: "subscription", label: "Subscription", render: (r) => r.subscription ? <StatusPill status={r.subscription.status} /> : <span className="text-ink-muted text-xs">none</span> },
            { key: "status", label: "Status", render: (r) => <StatusPill status={r.status} /> },
            { key: "actions", label: "", render: (r) => (
              <div className="flex gap-1.5">
                {r.status === "active" ? (
                  <Button size="sm" variant="outline" onClick={() => toggleStatus(r, "suspended")}>Suspend</Button>
                ) : (
                  <Button size="sm" variant="outline" onClick={() => toggleStatus(r, "active")}>Activate</Button>
                )}
              </div>
            )},
          ]}
          data={rows}
        />
      </div>
    </div>
  );
}

// ============================================================================
// PLATFORM ANALYTICS
// ============================================================================
export function PlatformAnalyticsPage() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/platform/analytics").then((r) => setData(r.data)); }, []);
  const t = data?.totals || {};
  const rev = data?.revenue || {};
  return (
    <div>
      <PageHeader eyebrow="VayuERP · Platform" title="Platform Analytics" subtitle="Revenue, tenants, subscriptions rollup" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        <KpiCard label="Tenants" value={t.tenants ?? "—"} />
        <KpiCard label="Active" value={t.active_tenants ?? "—"} />
        <KpiCard label="Suspended" value={t.suspended_tenants ?? "—"} />
        <KpiCard label="Total users" value={t.users ?? "—"} />
        <KpiCard label="Active subs" value={t.active_subscriptions ?? "—"} />
        <KpiCard label="Trials" value={t.trial_subscriptions ?? "—"} />
        <KpiCard label="MRR" value={rev.mrr ? `$${rev.mrr.toLocaleString()}` : "—"} />
        <KpiCard label="ARR" value={rev.arr ? `$${rev.arr.toLocaleString()}` : "—"} />
      </div>
      {data && (
        <Card className="p-4 mt-6 text-xs text-ink-muted">Generated at {data.generated_at}</Card>
      )}
    </div>
  );
}

// ============================================================================
// PLATFORM PLANS
// ============================================================================
export function PlatformPlansPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/platform/plans").then((r) => setRows(r.data.data || [])); }, []);
  return (
    <div>
      <PageHeader eyebrow="VayuERP · Platform" title="Subscription Plans" subtitle="Starter · Professional · Enterprise · Custom" />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
        {rows.map((p) => (
          <Card key={p.key} className="p-5">
            <div className="flex justify-between items-start">
              <div>
                <div className="text-xs uppercase tracking-widest text-ink-muted">{p.key}</div>
                <div className="font-display font-extrabold text-2xl mt-1">{p.name}</div>
              </div>
              {p.trial_days > 0 && <Badge className="bg-emerald-100 text-emerald-700">{p.trial_days}d trial</Badge>}
            </div>
            <div className="mt-4">
              <div className="text-3xl font-bold">${p.price_monthly}<span className="text-sm font-normal text-ink-muted">/mo</span></div>
              <div className="text-xs text-ink-muted">or ${p.price_yearly}/year</div>
            </div>
            <div className="mt-4 space-y-1 text-xs">
              <div>👥 Users: {p.limits?.users === -1 ? "Unlimited" : p.limits?.users}</div>
              <div>💾 Storage: {p.limits?.storage_gb === -1 ? "Unlimited" : `${p.limits?.storage_gb} GB`}</div>
              <div>🔌 API: {p.limits?.api_calls_per_day === -1 ? "Unlimited" : `${(p.limits?.api_calls_per_day || 0).toLocaleString()}/day`}</div>
              <div>🏬 Warehouses: {p.limits?.warehouses === -1 ? "Unlimited" : p.limits?.warehouses}</div>
              <div>📦 Modules: {p.limits?.modules === -1 ? "All" : p.limits?.modules}</div>
            </div>
            <div className="mt-4 pt-4 border-t border-[#E5E7EB] text-xs text-ink-muted">
              {p.features?.join(" · ")}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// PLATFORM SUBSCRIPTIONS
// ============================================================================
export function PlatformSubscriptionsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const load = () => { setLoading(true); api.get("/platform/subscriptions").then((r) => setRows(r.data.data || [])).finally(() => setLoading(false)); };
  useEffect(load, []);
  const doAction = async (id, action, body) => {
    try {
      await api.post(`/platform/subscriptions/${id}/${action}`, body || {});
      toast.success(`Subscription ${action}d`);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  return (
    <div>
      <PageHeader eyebrow="VayuERP · Platform" title="Subscriptions" subtitle="All tenant subscriptions and their lifecycle" />
      <div className="mt-6">
        <DataTable
          loading={loading}
          columns={[
            { key: "tenant_id", label: "Tenant" },
            { key: "plan_key", label: "Plan", render: (r) => <Badge className="capitalize">{r.plan_key}</Badge> },
            { key: "billing_cycle", label: "Cycle" },
            { key: "status", label: "Status", render: (r) => <StatusPill status={r.status} /> },
            { key: "starts_on", label: "Starts", render: (r) => (r.starts_on || "").slice(0, 10) },
            { key: "ends_on", label: "Ends", render: (r) => (r.ends_on || "").slice(0, 10) },
            { key: "actions", label: "", render: (r) => (
              <div className="flex gap-1.5">
                <Button size="sm" variant="outline" onClick={() => doAction(r.id, "renew", { billing_cycle: r.billing_cycle })}>Renew</Button>
                {r.status !== "cancelled" && <Button size="sm" variant="outline" onClick={() => doAction(r.id, "cancel")}>Cancel</Button>}
              </div>
            )},
          ]}
          data={rows}
        />
      </div>
    </div>
  );
}

// ============================================================================
// PLATFORM MODULES
// ============================================================================
export function PlatformModulesPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/platform/modules").then((r) => setRows(r.data.data || [])); }, []);
  return (
    <div>
      <PageHeader eyebrow="VayuERP · Platform" title="Modules Catalogue" subtitle="App marketplace — modules available to tenants" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        {rows.map((m) => (
          <Card key={m.key} className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-semibold">{m.name}</div>
                <div className="text-xs text-ink-muted mt-0.5 capitalize">{m.category}</div>
              </div>
              {m.default_enabled && <Badge className="bg-emerald-100 text-emerald-700">Default</Badge>}
            </div>
            <div className="mt-2 text-xs text-ink-muted">{m.description}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// PLATFORM BILLING
// ============================================================================
export function PlatformBillingPage() {
  const [rows, setRows] = useState([]);
  const load = () => api.get("/platform/me/billing/invoices").then((r) => setRows(r.data.data || []));
  useEffect(() => { load(); }, []);
  const pay = async (id) => {
    try { await api.post(`/platform/platform-invoices/${id}/pay`); toast.success("Marked paid (mock)"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  return (
    <div>
      <PageHeader eyebrow="VayuERP · Platform" title="Platform Billing" subtitle="Subscription invoices and payments (mock provider — Stripe/Razorpay-ready)" />
      <div className="mt-6">
        <DataTable
          columns={[
            { key: "id", label: "Invoice ID" },
            { key: "tenant_id", label: "Tenant" },
            { key: "period_start", label: "From", render: (r) => (r.period_start || "").slice(0,10) },
            { key: "period_end", label: "To", render: (r) => (r.period_end || "").slice(0,10) },
            { key: "total", label: "Amount", render: (r) => `${r.currency} ${(r.total || 0).toLocaleString()}` },
            { key: "status", label: "Status", render: (r) => <StatusPill status={r.status} /> },
            { key: "actions", label: "", render: (r) => r.status !== "paid" && <Button size="sm" onClick={() => pay(r.id)}>Mark Paid</Button> },
          ]}
          data={rows}
        />
      </div>
    </div>
  );
}

// ============================================================================
// PLATFORM ANNOUNCEMENTS
// ============================================================================
export function PlatformAnnouncementsPage() {
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: "", body: "", severity: "info", audience: "all" });
  const load = () => api.get("/platform/announcements").then((r) => setRows(r.data.data || []));
  useEffect(() => { load(); }, []);
  const submit = async () => {
    try { await api.post("/platform/announcements", form); toast.success("Announcement posted"); setOpen(false); load(); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  return (
    <div>
      <PageHeader
        eyebrow="VayuERP · Platform"
        title="Announcements"
        subtitle="Broadcast to all tenants, a plan, or one tenant"
        actions={<Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild><Button className="bg-gold hover:bg-gold-dark text-white"><Plus size={14} className="mr-1.5" /> New announcement</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>New announcement</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div><Label>Title</Label><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
              <div><Label>Body</Label><Textarea rows={4} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label>Severity</Label>
                  <Select value={form.severity} onValueChange={(v) => setForm({ ...form, severity: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{["info", "warn", "critical"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                  </Select></div>
                <div><Label>Audience</Label><Input value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value })} placeholder="all | plan:pro | tenant:tnt-x" /></div>
              </div>
            </div>
            <DialogFooter><Button onClick={submit}>Post</Button></DialogFooter>
          </DialogContent>
        </Dialog>}
      />
      <div className="mt-6 space-y-3">
        {rows.map((r) => (
          <Card key={r.id} className="p-4">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-semibold">{r.title}</div>
                <div className="text-sm text-ink-muted mt-1">{r.body}</div>
                <div className="text-xs text-ink-muted mt-2">Audience: <span className="font-mono">{r.audience}</span></div>
              </div>
              <Badge className={r.severity === "critical" ? "bg-rose-100 text-rose-700" : r.severity === "warn" ? "bg-amber-100 text-amber-700" : "bg-sky-100 text-sky-700"}>{r.severity}</Badge>
            </div>
          </Card>
        ))}
        {!rows.length && <div className="text-sm text-ink-muted">No announcements yet.</div>}
      </div>
    </div>
  );
}

// ============================================================================
// PLATFORM FEATURE FLAGS
// ============================================================================
export function PlatformFlagsPage() {
  const [data, setData] = useState({ data: [], resolved: {} });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ key: "", value: "true", scope: "global" });
  const load = () => api.get("/platform/feature-flags").then((r) => setData(r.data));
  useEffect(() => { load(); }, []);
  const submit = async () => {
    let val = form.value;
    try { val = JSON.parse(form.value); } catch { /* keep string */ }
    try { await api.post("/platform/feature-flags", { ...form, value: val }); setOpen(false); load(); toast.success("Flag saved"); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  return (
    <div>
      <PageHeader
        eyebrow="VayuERP · Platform"
        title="Feature Flags"
        subtitle="Enable/disable features globally, per plan, or per tenant"
        actions={<Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild><Button className="bg-gold hover:bg-gold-dark text-white"><Plus size={14} className="mr-1.5" /> New flag</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>New / update flag</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div><Label>Key</Label><Input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} placeholder="e.g. beta_ai_forecasting" /></div>
              <div><Label>Value (JSON)</Label><Input value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} placeholder='true / "beta" / 42' /></div>
              <div><Label>Scope</Label><Input value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value })} placeholder="global | plan:pro | tenant:tnt-x" /></div>
            </div>
            <DialogFooter><Button onClick={submit}>Save</Button></DialogFooter>
          </DialogContent>
        </Dialog>}
      />
      <div className="mt-6">
        <DataTable
          columns={[
            { key: "key", label: "Key" },
            { key: "value", label: "Value", render: (r) => <span className="font-mono text-xs">{JSON.stringify(r.value)}</span> },
            { key: "scope", label: "Scope" },
            { key: "updated_at", label: "Updated", render: (r) => (r.updated_at || "").slice(0, 19) },
          ]}
          data={data.data}
        />
      </div>
    </div>
  );
}

// ============================================================================
// PLATFORM BACKUPS
// ============================================================================
export function PlatformBackupsPage() {
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const { user } = useAuth();
  const load = () => api.get("/platform/backups").then((r) => setRows(r.data.data || []));
  useEffect(() => { load(); }, []);
  const create = async () => {
    setBusy(true);
    try { await api.post("/platform/backups", { kind: "manual" }); toast.success("Backup queued (mock)"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  const restore = async (id) => {
    try { await api.post(`/platform/backups/${id}/restore`); toast.success("Restore complete (mock)"); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  return (
    <div>
      <PageHeader
        eyebrow={user?.role === "platform_owner" ? "VayuERP · Platform" : "Tenant Admin"}
        title="Backups"
        subtitle="Automated daily/weekly + on-demand tenant restores (mock provider)"
        actions={<Button disabled={busy} onClick={create} className="bg-gold hover:bg-gold-dark text-white"><DatabaseBackup size={14} className="mr-1.5" /> New backup</Button>}
      />
      <div className="mt-6">
        <DataTable
          columns={[
            { key: "id", label: "Backup ID" },
            { key: "tenant_id", label: "Tenant" },
            { key: "kind", label: "Type" },
            { key: "size_bytes", label: "Size", render: (r) => `${((r.size_bytes || 0) / 1024).toFixed(0)} KB` },
            { key: "status", label: "Status", render: (r) => <StatusPill status={r.status} /> },
            { key: "created_at", label: "Created", render: (r) => (r.created_at || "").slice(0, 19) },
            { key: "actions", label: "", render: (r) => user?.role === "platform_owner" && <Button size="sm" variant="outline" onClick={() => restore(r.id)}>Restore</Button> },
          ]}
          data={rows}
        />
      </div>
    </div>
  );
}

// ============================================================================
// TENANT BRANDING (self-service white label)
// ============================================================================
export function TenantBrandingPage() {
  const { tenant, refresh } = useTenant();
  const [form, setForm] = useState({
    logo_url: tenant?.logo_url || "",
    brand_colors: tenant?.brand_colors || { primary: "#0F172A", secondary: "#F59E0B", accent: "#10B981" },
    display_name: tenant?.display_name || tenant?.name || "",
    email_footer: tenant?.email_footer || "",
    invoice_footer: tenant?.invoice_footer || "",
    support_email: tenant?.support_email || tenant?.contact?.email || "",
    support_phone: tenant?.support_phone || tenant?.contact?.phone || "",
  });
  useEffect(() => {
    if (tenant) setForm((f) => ({
      ...f,
      logo_url: tenant.logo_url || "",
      brand_colors: tenant.brand_colors || f.brand_colors,
      display_name: tenant.display_name || tenant.name || "",
    }));
  }, [tenant]);

  const save = async () => {
    try { await api.put("/platform/me/tenant/branding", form); toast.success("Branding saved"); refresh(); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  return (
    <div>
      <PageHeader eyebrow="Tenant Admin" title="Branding & Theme" subtitle="Logo, colours and support info that appear across the app, invoices and emails." />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        <Card className="p-5 space-y-4">
          <div><Label>Display name</Label><Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} className="mt-1.5" /></div>
          <div><Label>Logo URL</Label><Input value={form.logo_url} onChange={(e) => setForm({ ...form, logo_url: e.target.value })} className="mt-1.5" placeholder="https://..." /></div>
          <div className="grid grid-cols-3 gap-3">
            {["primary","secondary","accent"].map((k) => (
              <div key={k}>
                <Label className="capitalize">{k}</Label>
                <div className="flex items-center gap-2 mt-1.5">
                  <Input type="color" value={form.brand_colors[k]} onChange={(e) => setForm({ ...form, brand_colors: { ...form.brand_colors, [k]: e.target.value } })} className="w-12 h-10 p-1" />
                  <Input value={form.brand_colors[k]} onChange={(e) => setForm({ ...form, brand_colors: { ...form.brand_colors, [k]: e.target.value } })} className="flex-1" />
                </div>
              </div>
            ))}
          </div>
          <div><Label>Support email</Label><Input value={form.support_email} onChange={(e) => setForm({ ...form, support_email: e.target.value })} className="mt-1.5" /></div>
          <div><Label>Support phone</Label><Input value={form.support_phone} onChange={(e) => setForm({ ...form, support_phone: e.target.value })} className="mt-1.5" /></div>
          <div><Label>Invoice footer</Label><Textarea rows={2} value={form.invoice_footer} onChange={(e) => setForm({ ...form, invoice_footer: e.target.value })} className="mt-1.5" /></div>
          <div><Label>Email footer</Label><Textarea rows={2} value={form.email_footer} onChange={(e) => setForm({ ...form, email_footer: e.target.value })} className="mt-1.5" /></div>
          <Button onClick={save} className="bg-gold hover:bg-gold-dark text-white">Save changes</Button>
        </Card>
        <Card className="p-5">
          <div className="text-xs uppercase tracking-widest text-ink-muted">Live preview</div>
          <div className="mt-3 rounded-2xl p-6 text-white" style={{ background: `linear-gradient(135deg, ${form.brand_colors.primary} 0%, ${form.brand_colors.secondary} 100%)` }}>
            {form.logo_url ? <img src={form.logo_url} alt="logo" className="h-10 mb-3" /> : <div className="w-10 h-10 rounded-xl bg-white/20 mb-3" />}
            <div className="font-display font-extrabold text-2xl">{form.display_name || "Your Company"}</div>
            <div className="text-xs opacity-80 mt-1">Invoice · Statement · Email header</div>
          </div>
          <div className="mt-4 flex gap-2">
            {["primary","secondary","accent"].map((k) => (
              <div key={k} className="flex-1 text-center">
                <div className="h-14 rounded-lg" style={{ background: form.brand_colors[k] }} />
                <div className="text-[10px] uppercase tracking-widest mt-1">{k}</div>
                <div className="text-[10px] font-mono">{form.brand_colors[k]}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ============================================================================
// TENANT SETTINGS (currency/timezone/tax/labels)
// ============================================================================
export function TenantSettingsPage() {
  const { tenant, refresh } = useTenant();
  const [form, setForm] = useState({});
  useEffect(() => {
    if (tenant) setForm({
      industry: tenant.industry,
      currency: tenant.currency,
      timezone: tenant.timezone,
      tax: tenant.tax || { tax_name: "VAT", tax_percent: 0 },
      contact: tenant.contact || {},
      address: tenant.address || {},
      labels: tenant.labels || {},
    });
  }, [tenant]);
  const save = async () => {
    try { await api.put("/platform/me/tenant/settings", form); toast.success("Settings saved"); refresh(); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  if (!form || !form.tax) return <div className="p-8">Loading...</div>;
  return (
    <div>
      <PageHeader eyebrow="Tenant Admin" title="Company Settings" subtitle="Industry, region, tax and productisation labels" />
      <Card className="p-5 mt-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div><Label>Industry</Label>
            <Select value={form.industry} onValueChange={(v) => setForm({ ...form, industry: v })}>
              <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
              <SelectContent>{INDUSTRIES.map((i) => <SelectItem key={i} value={i}>{i}</SelectItem>)}</SelectContent>
            </Select></div>
          <div><Label>Currency</Label>
            <Select value={form.currency} onValueChange={(v) => setForm({ ...form, currency: v })}>
              <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
              <SelectContent>{CURRENCIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select></div>
          <div><Label>Timezone</Label>
            <Select value={form.timezone} onValueChange={(v) => setForm({ ...form, timezone: v })}>
              <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
              <SelectContent>{TIMEZONES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
            </Select></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div><Label>Tax name</Label><Input value={form.tax.tax_name} onChange={(e) => setForm({ ...form, tax: { ...form.tax, tax_name: e.target.value } })} className="mt-1.5" /></div>
          <div><Label>Tax %</Label><Input type="number" step="0.01" value={form.tax.tax_percent} onChange={(e) => setForm({ ...form, tax: { ...form.tax, tax_percent: parseFloat(e.target.value || "0") } })} className="mt-1.5" /></div>
          <div><Label>Tax number</Label><Input value={form.tax.tax_number || ""} onChange={(e) => setForm({ ...form, tax: { ...form.tax, tax_number: e.target.value } })} className="mt-1.5" /></div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-widest text-ink-muted mb-2">Productisation labels</div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {["unit","sku_word","product_word","batch_word"].map((k) => (
              <div key={k}><Label className="capitalize">{k.replace("_"," ")}</Label>
                <Input value={form.labels?.[k] || ""} onChange={(e) => setForm({ ...form, labels: { ...(form.labels||{}), [k]: e.target.value } })} className="mt-1.5" />
              </div>
            ))}
          </div>
        </div>
        <Button onClick={save} className="bg-gold hover:bg-gold-dark text-white">Save settings</Button>
      </Card>
    </div>
  );
}

// ============================================================================
// TENANT API KEYS
// ============================================================================
export function TenantApiKeysPage() {
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [issued, setIssued] = useState(null);
  const [form, setForm] = useState({ name: "", scopes: ["read"], expires_days: 365 });
  const load = () => api.get("/platform/me/api-keys").then((r) => setRows(r.data.data || []));
  useEffect(() => { load(); }, []);
  const create = async () => {
    try { const { data } = await api.post("/platform/me/api-keys", form); setIssued(data); load(); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const revoke = async (id) => {
    try { await api.delete(`/platform/me/api-keys/${id}`); toast.success("Revoked"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const copy = (v) => { navigator.clipboard.writeText(v); toast.success("Copied"); };
  return (
    <div>
      <PageHeader
        eyebrow="Tenant Admin"
        title="API Keys"
        subtitle="Machine-to-machine credentials for your VayuERP API integration"
        actions={<Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setIssued(null); }}>
          <DialogTrigger asChild><Button className="bg-gold hover:bg-gold-dark text-white"><KeyRound size={14} className="mr-1.5" /> New API key</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Issue new API key</DialogTitle></DialogHeader>
            {!issued ? (
              <div className="space-y-3">
                <div><Label>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. mobile-integration" /></div>
                <div><Label>Expires in days</Label><Input type="number" value={form.expires_days} onChange={(e) => setForm({ ...form, expires_days: parseInt(e.target.value || "365") })} /></div>
                <div><Label>Scopes (comma-separated)</Label><Input value={form.scopes.join(",")} onChange={(e) => setForm({ ...form, scopes: e.target.value.split(",").map(s => s.trim()) })} /></div>
                <DialogFooter><Button onClick={create}>Generate</Button></DialogFooter>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs">
                  ⚠️ Copy this key now — it will NOT be shown again.
                </div>
                <div><Label>Full key</Label>
                  <div className="mt-1.5 flex items-center gap-2">
                    <Input readOnly value={issued.full_key} className="font-mono text-xs" />
                    <Button size="sm" onClick={() => copy(issued.full_key)}><Copy size={14} /></Button>
                  </div>
                </div>
                <DialogFooter><Button onClick={() => { setOpen(false); setIssued(null); }}>Done</Button></DialogFooter>
              </div>
            )}
          </DialogContent>
        </Dialog>}
      />
      <div className="mt-6">
        <DataTable
          columns={[
            { key: "name", label: "Name" },
            { key: "prefix", label: "Prefix", render: (r) => <span className="font-mono text-xs">{r.prefix}</span> },
            { key: "scopes", label: "Scopes", render: (r) => (r.scopes || []).join(", ") },
            { key: "created_at", label: "Created", render: (r) => (r.created_at || "").slice(0,10) },
            { key: "expires_at", label: "Expires", render: (r) => (r.expires_at || "").slice(0,10) },
            { key: "revoked", label: "Status", render: (r) => r.revoked ? <StatusPill status="revoked" /> : <StatusPill status="active" /> },
            { key: "actions", label: "", render: (r) => !r.revoked && <Button size="sm" variant="outline" onClick={() => revoke(r.id)}><Trash2 size={14} /></Button> },
          ]}
          data={rows}
        />
      </div>
    </div>
  );
}

// ============================================================================
// TENANT WEBHOOKS
// ============================================================================
export function TenantWebhooksPage() {
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", url: "", events: ["order.created"] });
  const load = () => api.get("/platform/me/webhooks").then((r) => setRows(r.data.data || []));
  useEffect(() => { load(); }, []);
  const create = async () => {
    try { await api.post("/platform/me/webhooks", form); toast.success("Webhook added"); setOpen(false); load(); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const del = async (id) => {
    try { await api.delete(`/platform/me/webhooks/${id}`); toast.success("Webhook removed"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  return (
    <div>
      <PageHeader
        eyebrow="Tenant Admin"
        title="Webhooks"
        subtitle="Push VayuERP events to your systems"
        actions={<Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild><Button className="bg-gold hover:bg-gold-dark text-white"><Webhook size={14} className="mr-1.5" /> New webhook</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>New webhook</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div><Label>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
              <div><Label>URL</Label><Input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://your-endpoint.example.com/hook" /></div>
              <div><Label>Events (comma-separated)</Label><Input value={form.events.join(",")} onChange={(e) => setForm({ ...form, events: e.target.value.split(",").map(s => s.trim()) })} /></div>
            </div>
            <DialogFooter><Button onClick={create}>Save</Button></DialogFooter>
          </DialogContent>
        </Dialog>}
      />
      <div className="mt-6">
        <DataTable
          columns={[
            { key: "name", label: "Name" },
            { key: "url", label: "URL", render: (r) => <span className="text-xs font-mono">{r.url}</span> },
            { key: "events", label: "Events", render: (r) => (r.events || []).join(", ") },
            { key: "active", label: "Status", render: (r) => <StatusPill status={r.active ? "active" : "paused"} /> },
            { key: "actions", label: "", render: (r) => <Button size="sm" variant="outline" onClick={() => del(r.id)}><Trash2 size={14} /></Button> },
          ]}
          data={rows}
        />
      </div>
    </div>
  );
}

// ============================================================================
// TENANT MARKETPLACE (module enable/disable)
// ============================================================================
export function TenantMarketplacePage() {
  const [rows, setRows] = useState([]);
  const load = () => api.get("/platform/me/modules").then((r) => setRows(r.data.data || []));
  useEffect(() => { load(); }, []);
  const toggle = async (m) => {
    try {
      if (m.enabled) await api.post(`/platform/me/modules/${m.key}/disable`);
      else await api.post(`/platform/me/modules/${m.key}/enable`);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const byCat = useMemo(() => {
    const g = {};
    for (const r of rows) { (g[r.category] = g[r.category] || []).push(r); }
    return g;
  }, [rows]);
  return (
    <div>
      <PageHeader eyebrow="Tenant Admin" title="App Marketplace" subtitle="Enable modules for your company — CRM · HRMS · Payroll · Manufacturing · Transport · Assets · Projects · Visitor · AI" />
      <div className="mt-6 space-y-8">
        {Object.entries(byCat).map(([cat, items]) => (
          <div key={cat}>
            <div className="text-xs uppercase tracking-widest text-ink-muted mb-2 capitalize">{cat}</div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {items.map((m) => (
                <Card key={m.key} className={`p-4 ${m.enabled ? "border-emerald-400 bg-emerald-50/30" : ""}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold">{m.name}</div>
                      <div className="text-xs text-ink-muted mt-1">{m.description}</div>
                    </div>
                    <Switch checked={!!m.enabled} onCheckedChange={() => toggle(m)} />
                  </div>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
