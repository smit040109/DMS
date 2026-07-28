import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { ArrowRight, ShieldCheck, TrendingUp, Zap, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import GoldLogo from "@/components/common/GoldLogo";
import { ROLE_LABELS } from "@/lib/nav";

const QUICK_LOGINS = [
  { role: "company_admin", email: "company@gooil.com", label: "Company Admin" },
  { role: "regional_manager", email: "regional@gooil.com", label: "Regional Manager" },
  { role: "sales_executive", email: "sales@gooil.com", label: "Sales Executive" },
  { role: "distributor", email: "distributor@gooil.com", label: "Distributor" },
  { role: "retailer", email: "retailer@gooil.com", label: "Retailer" },
  { role: "customer", email: "customer@gooil.com", label: "Customer" },
];

const DEMO_PASSWORD = "GoOil@2026";

export default function Login() {
  const { user, login, register, error } = useAuth();
  const nav = useNavigate();
  const [tab, setTab] = useState("login");
  const [email, setEmail] = useState("company@gooil.com");
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [name, setName] = useState("");
  const [role, setRole] = useState("customer");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/app" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const r = tab === "login" ? await login(email, password) : await register({ email, password, name, role });
    setBusy(false);
    if (r.ok) nav("/app");
  };

  const quick = async (u) => {
    setBusy(true);
    const r = await login(u.email, DEMO_PASSWORD);
    setBusy(false);
    if (r.ok) nav("/app");
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-canvas" data-testid="login-page">
      {/* Left — brand hero */}
      <div className="relative hidden lg:flex flex-col justify-between p-12 overflow-hidden bg-ink text-white">
        <div className="absolute inset-0 opacity-70"
          style={{
            backgroundImage: `linear-gradient(120deg, rgba(31,41,55,0.85) 0%, rgba(31,41,55,0.55) 55%, rgba(166,124,0,0.35) 100%), url('https://images.unsplash.com/photo-1777195148867-68a6f0e9aa8f?crop=entropy&cs=srgb&fm=jpg&w=1600&q=80')`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <div className="relative z-10">
          <GoldLogo size={40} className="[&_div]:text-white [&_span]:text-white/70" />
        </div>

        <div className="relative z-10">
          <div className="text-[11px] uppercase tracking-[0.32em] text-gold/90 font-semibold mb-4">
            Enterprise Distribution Management
          </div>
          <h1 className="font-display font-extrabold text-4xl xl:text-5xl leading-tight tracking-tight">
            The command layer for <span className="text-gold">GO OIL</span> operations.
          </h1>
          <p className="mt-4 text-white/70 text-base max-w-md leading-relaxed">
            Primary & secondary orders, warehouse, dispatch, GRN, invoicing, ledger and AI insights — unified across every branch, distributor and retailer.
          </p>

          <div className="mt-10 grid grid-cols-2 gap-4 max-w-md">
            {[
              { icon: TrendingUp, label: "Real-time KPIs", sub: "97.1% fill rate" },
              { icon: ShieldCheck, label: "Role-based access", sub: "8 personas" },
              { icon: Zap, label: "AI Copilot", sub: "Claude Sonnet" },
              { icon: ArrowRight, label: "28 modules", sub: "Unified" },
            ].map((f) => (
              <div key={f.label} className="rounded-xl bg-white/8 backdrop-blur border border-white/10 px-4 py-3">
                <f.icon size={16} className="text-gold" />
                <div className="mt-2 text-sm font-semibold">{f.label}</div>
                <div className="text-[11px] text-white/60">{f.sub}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 text-xs text-white/50">
          © {new Date().getFullYear()} GO OIL Holdings. Trusted enterprise ERP.
        </div>
      </div>

      {/* Right — auth panel */}
      <div className="flex items-center justify-center p-6 md:p-10">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-6"><GoldLogo /></div>

          <h2 className="font-display font-extrabold text-3xl text-ink">Sign in to your command center</h2>
          <p className="mt-1.5 text-sm text-ink-muted">
            {tab === "login" ? "Use one of the demo roles or your own credentials." : "Create an account to explore the DMS."}
          </p>

          <Tabs value={tab} onValueChange={setTab} className="mt-6">
            <TabsList className="grid grid-cols-2 bg-canvas border border-[#E5E7EB]">
              <TabsTrigger value="login" data-testid="tab-login">Sign in</TabsTrigger>
              <TabsTrigger value="register" data-testid="tab-register">Create account</TabsTrigger>
            </TabsList>

            <TabsContent value="login" className="mt-6">
              <form onSubmit={submit} className="space-y-4">
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="login-email" className="mt-1.5" />
                </div>
                <div>
                  <Label htmlFor="password">Password</Label>
                  <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required data-testid="login-password" className="mt-1.5" />
                </div>
                {error && <div className="text-sm text-rose-600" data-testid="login-error">{error}</div>}
                <Button type="submit" disabled={busy} className="w-full h-11 bg-gold hover:bg-gold-dark text-white font-semibold" data-testid="login-submit">
                  {busy ? <><Loader2 size={14} className="mr-2 animate-spin" /> Signing in…</> : <>Sign in <ArrowRight size={15} className="ml-2" /></>}
                </Button>
              </form>

              <div className="mt-6">
                <div className="text-[11px] uppercase tracking-[0.22em] text-ink-muted font-semibold mb-3">One-click demo</div>
                <div className="grid grid-cols-2 gap-2">
                  {QUICK_LOGINS.map((u) => (
                    <button
                      key={u.role}
                      onClick={() => quick(u)}
                      disabled={busy}
                      className="text-left text-xs rounded-lg border border-[#E5E7EB] px-3 py-2.5 hover:border-gold hover:bg-gold/5 transition disabled:opacity-50"
                      data-testid={`quick-login-${u.role}`}
                    >
                      <div className="font-semibold text-ink">{u.label}</div>
                      <div className="text-ink-muted mt-0.5 truncate">{u.email}</div>
                    </button>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="register" className="mt-6">
              <form onSubmit={submit} className="space-y-4">
                <div>
                  <Label htmlFor="name">Full name</Label>
                  <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required data-testid="register-name" className="mt-1.5" />
                </div>
                <div>
                  <Label htmlFor="email-r">Email</Label>
                  <Input id="email-r" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="register-email" className="mt-1.5" />
                </div>
                <div>
                  <Label htmlFor="password-r">Password</Label>
                  <Input id="password-r" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required data-testid="register-password" className="mt-1.5" />
                </div>
                <div>
                  <Label>Role</Label>
                  <Select value={role} onValueChange={setRole}>
                    <SelectTrigger className="mt-1.5" data-testid="register-role"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(ROLE_LABELS).map(([k, v]) => (
                        <SelectItem key={k} value={k}>{v}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {error && <div className="text-sm text-rose-600" data-testid="register-error">{error}</div>}
                <Button type="submit" disabled={busy} className="w-full h-11 bg-gold hover:bg-gold-dark text-white font-semibold" data-testid="register-submit">
                  {busy ? "Creating…" : "Create account"}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
