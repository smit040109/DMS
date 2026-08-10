import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { ArrowRight, Loader2, Droplet, Users, ShoppingCart, TrendingUp } from "lucide-react";
import ThemeToggle from "@/components/common/ThemeToggle";

const DEMO = [
  { role: "owner",                   email: "owner@gooil.com",          label: "Company Owner",           tag: "Owner"       },
  { role: "owner_accountant",        email: "accountant@gooil.com",     label: "Owner Accountant",        tag: "Accounts"    },
  { role: "distributor",             email: "distributor1@gooil.com",   label: "Distributor — Delhi",     tag: "Distributor" },
  { role: "distributor",             email: "distributor2@gooil.com",   label: "Distributor — Mumbai",    tag: "Distributor" },
  { role: "distributor_accountant",  email: "distacct@gooil.com",       label: "Distributor Accountant",  tag: "Accounts"    },
  { role: "retailer",                email: "retailer1@gooil.com",      label: "Retailer — Sharma Auto",  tag: "Retailer"    },
  { role: "retailer",                email: "retailer2@gooil.com",      label: "Retailer — Verma Motors", tag: "Retailer"    },
  { role: "salesperson",             email: "salesperson@gooil.com",    label: "Salesperson",             tag: "Field"       },
  { role: "team_leader",             email: "teamleader@gooil.com",     label: "Team Leader",             tag: "Sales Mgmt"  },
  { role: "regional_manager",        email: "regionalmgr@gooil.com",    label: "Regional Manager",        tag: "Regional"    },
];

const DEMO_PASSWORD = "GoOil@2026";

export default function Login() {
  const { user, login, error } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("owner@gooil.com");
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/dms" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const r = await login(email, password);
    setBusy(false);
    if (r.ok) nav("/dms");
  };

  const quick = async (u) => {
    setBusy(true);
    const r = await login(u.email, DEMO_PASSWORD);
    setBusy(false);
    if (r.ok) nav("/dms");
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-5 bg-[#fafaf8] relative" data-testid="login-page">
      <div className="absolute top-4 right-4 z-20"><ThemeToggle /></div>
      {/* Left brand — premium White + Gold */}
      <div className="relative hidden lg:flex lg:col-span-2 flex-col justify-between p-10 bg-gradient-to-br from-white via-[#faf6e6] to-[#f2e6b8] overflow-hidden">
        <div className="absolute -top-24 -right-24 h-96 w-96 rounded-full bg-[#c9a227]/20 blur-3xl" />
        <div className="absolute -bottom-20 -left-20 h-80 w-80 rounded-full bg-[#a67c00]/10 blur-3xl" />
        <div className="relative z-10 flex items-center gap-3">
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-[#c9a227] to-[#a67c00] flex items-center justify-center shadow-lg shadow-[#c9a227]/30">
            <Droplet size={22} className="text-white" />
          </div>
          <div>
            <div className="font-display font-extrabold text-2xl leading-none text-slate-900">GO OIL</div>
            <div className="text-[11px] uppercase tracking-[0.3em] text-[#a67c00] mt-1 font-semibold">Distributor Management</div>
          </div>
        </div>
        <div className="relative z-10">
          <h1 className="font-display font-bold text-4xl xl:text-5xl leading-tight tracking-tight text-slate-900">
            Simple. Premium. <span className="text-[#a67c00]">Distributor management</span> for lubricants.
          </h1>
          <p className="mt-4 text-slate-600 text-base max-w-md leading-relaxed">
            Product Master, monthly Price Circulars, and full pricing history — in one clean workflow.
          </p>
          <div className="mt-8 grid grid-cols-2 gap-3 max-w-md">
            {[
              { icon: ShoppingCart, label: "Primary Sales",    sub: "Owner → Distributor"   },
              { icon: Users,        label: "Secondary Sales",  sub: "Distributor → Retailer"},
              { icon: TrendingUp,   label: "Price Circular",   sub: "Monthly batches + history"},
              { icon: Droplet,      label: "Field Ready",      sub: "GPS, punch, retailer visits"},
            ].map(f => (
              <div key={f.label} className="rounded-xl bg-white/70 backdrop-blur border border-[#c9a227]/25 px-4 py-3 shadow-sm">
                <f.icon size={16} className="text-[#a67c00]" />
                <div className="mt-2 text-sm font-semibold text-slate-900">{f.label}</div>
                <div className="text-[11px] text-slate-500">{f.sub}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="relative z-10 text-xs text-slate-500">© {new Date().getFullYear()} GO OIL DMS</div>
      </div>

      {/* Right form */}
      <div className="lg:col-span-3 flex items-center justify-center p-6 md:p-10 bg-white">
        <div className="w-full max-w-lg">
          <div className="lg:hidden mb-6 flex items-center gap-2">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[#c9a227] to-[#a67c00] flex items-center justify-center">
              <Droplet size={20} className="text-white" />
            </div>
            <div>
              <div className="font-display font-extrabold text-slate-900">GO OIL</div>
              <div className="text-[10px] uppercase tracking-widest text-[#a67c00] font-semibold">DMS</div>
            </div>
          </div>
          <h2 className="font-display font-bold text-3xl text-slate-900">Sign in</h2>
          <p className="mt-1.5 text-sm text-slate-500">Choose a demo role below, or enter your own credentials.</p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <div><Label htmlFor="email">Email</Label><Input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1.5" required data-testid="login-email" /></div>
            <div><Label htmlFor="pw">Password</Label><Input id="pw" type="password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1.5" required data-testid="login-password" /></div>
            {error && <div className="text-sm text-rose-600" data-testid="login-error">{error}</div>}
            <Button type="submit" disabled={busy} className="w-full h-11 bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white font-semibold shadow-md shadow-[#c9a227]/25" data-testid="login-submit">
              {busy ? <><Loader2 size={14} className="mr-2 animate-spin" /> Signing in…</> : <>Sign in <ArrowRight size={15} className="ml-2" /></>}
            </Button>
          </form>

          <div className="mt-6">
            <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-semibold mb-3">Try any role — password is <span className="text-slate-900 font-bold">GoOil@2026</span></div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {DEMO.map(u => (
                <button key={u.email} onClick={() => quick(u)} disabled={busy}
                  className="text-left text-xs rounded-lg border border-slate-200 px-3 py-2.5 hover:border-[#c9a227] hover:bg-[#faf6e6]/60 transition disabled:opacity-50 flex items-center justify-between"
                  data-testid={`quick-login-${u.role}-${u.email.split('@')[0]}`}>
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-900 truncate">{u.label}</div>
                    <div className="text-slate-500 mt-0.5 truncate">{u.email}</div>
                  </div>
                  <span className="text-[9px] uppercase tracking-wider bg-[#faf0cf] text-[#8a6600] px-1.5 py-0.5 rounded shrink-0 ml-2 font-semibold">{u.tag}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
