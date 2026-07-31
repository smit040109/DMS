import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { ArrowRight, Loader2, Droplet, Users, ShoppingCart, TrendingUp } from "lucide-react";

const DEMO = [
  { role: "owner",                  email: "owner@dms.com",     label: "Company Owner",           tag: "Super Admin"  },
  { role: "owner_accountant",       email: "acct@dms.com",      label: "Owner Accountant",        tag: "Accounts"     },
  { role: "distributor",            email: "dist1@dms.com",     label: "Distributor — Amit",      tag: "Distributor"  },
  { role: "distributor",            email: "dist2@dms.com",     label: "Distributor — Priya",     tag: "Distributor"  },
  { role: "distributor_accountant", email: "distacct@dms.com",  label: "Distributor Accountant",  tag: "Accounts"     },
  { role: "salesperson",            email: "sales@dms.com",     label: "Salesperson",             tag: "Field"        },
  { role: "team_leader",            email: "tl@dms.com",        label: "Team Leader",             tag: "Sales Mgmt"   },
  { role: "regional_manager",       email: "rm@dms.com",        label: "Regional Manager",        tag: "Regional"     },
  { role: "retailer",               email: "retailer1@dms.com", label: "Retailer — Sharma Auto",  tag: "Retailer"     },
];

const DEMO_PASSWORD = "Demo@2026";

export default function Login() {
  const { user, login, error } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("owner@dms.com");
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
    <div className="min-h-screen grid lg:grid-cols-5 bg-slate-50" data-testid="login-page">
      {/* Left brand */}
      <div className="relative hidden lg:flex lg:col-span-2 flex-col justify-between p-10 bg-gradient-to-br from-teal-800 via-teal-900 to-slate-900 text-white overflow-hidden">
        <div className="absolute -top-20 -right-20 h-80 w-80 rounded-full bg-teal-500/20 blur-3xl" />
        <div className="absolute -bottom-16 -left-16 h-72 w-72 rounded-full bg-amber-500/10 blur-3xl" />
        <div className="relative z-10 flex items-center gap-2">
          <div className="h-11 w-11 rounded-xl bg-white/10 backdrop-blur border border-white/20 flex items-center justify-center"><Droplet size={22} className="text-amber-300" /></div>
          <div>
            <div className="font-bold text-xl leading-none">Bharat Oil</div>
            <div className="text-[11px] uppercase tracking-[0.28em] text-white/60 mt-1">Distribution Management</div>
          </div>
        </div>
        <div className="relative z-10">
          <h1 className="font-bold text-4xl xl:text-5xl leading-tight tracking-tight">
            Simple, fast <span className="text-amber-300">distribution management</span> for oil & lubricants.
          </h1>
          <p className="mt-4 text-white/70 text-base max-w-md leading-relaxed">
            Two workflows. Zero clutter. Every role sees only what they need.
          </p>
          <div className="mt-8 grid grid-cols-2 gap-3 max-w-md">
            {[
              { icon: ShoppingCart, label: "Primary Sales", sub: "Owner → Distributor" },
              { icon: Users,        label: "Secondary Sales", sub: "Distributor → Retailer" },
              { icon: TrendingUp,   label: "Live Ledger", sub: "Auto e-Bills, batches" },
              { icon: Droplet,      label: "Mobile-Ready", sub: "GPS, punch in/out" },
            ].map(f => (
              <div key={f.label} className="rounded-xl bg-white/8 backdrop-blur border border-white/10 px-4 py-3">
                <f.icon size={16} className="text-amber-300" />
                <div className="mt-2 text-sm font-semibold">{f.label}</div>
                <div className="text-[11px] text-white/60">{f.sub}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="relative z-10 text-xs text-white/40">© {new Date().getFullYear()} Bharat Oil DMS</div>
      </div>

      {/* Right form */}
      <div className="lg:col-span-3 flex items-center justify-center p-6 md:p-10">
        <div className="w-full max-w-lg">
          <div className="lg:hidden mb-6 flex items-center gap-2">
            <div className="h-10 w-10 rounded-xl bg-teal-700 flex items-center justify-center"><Droplet size={20} className="text-amber-300" /></div>
            <div><div className="font-bold text-slate-900">Bharat Oil</div><div className="text-[10px] uppercase tracking-widest text-slate-500">DMS</div></div>
          </div>
          <h2 className="font-bold text-3xl text-slate-900">Sign in</h2>
          <p className="mt-1.5 text-sm text-slate-500">Choose a demo role below, or enter your own credentials.</p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <div><Label htmlFor="email">Email</Label><Input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1.5" required data-testid="login-email" /></div>
            <div><Label htmlFor="pw">Password</Label><Input id="pw" type="password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1.5" required data-testid="login-password" /></div>
            {error && <div className="text-sm text-rose-600" data-testid="login-error">{error}</div>}
            <Button type="submit" disabled={busy} className="w-full h-11 bg-teal-700 hover:bg-teal-800 font-semibold" data-testid="login-submit">
              {busy ? <><Loader2 size={14} className="mr-2 animate-spin" /> Signing in…</> : <>Sign in <ArrowRight size={15} className="ml-2" /></>}
            </Button>
          </form>

          <div className="mt-6">
            <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-semibold mb-3">Try any role — password is <span className="text-slate-900">Demo@2026</span></div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {DEMO.map(u => (
                <button key={u.email} onClick={() => quick(u)} disabled={busy}
                  className="text-left text-xs rounded-lg border border-slate-200 px-3 py-2.5 hover:border-teal-500 hover:bg-teal-50/50 transition disabled:opacity-50 flex items-center justify-between"
                  data-testid={`quick-login-${u.role}-${u.email.split('@')[0]}`}>
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-900 truncate">{u.label}</div>
                    <div className="text-slate-500 mt-0.5 truncate">{u.email}</div>
                  </div>
                  <span className="text-[9px] uppercase tracking-wider bg-teal-100 text-teal-800 px-1.5 py-0.5 rounded shrink-0 ml-2">{u.tag}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
