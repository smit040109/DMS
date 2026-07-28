import React from "react";
import { TrendingUp, TrendingDown, Gauge } from "lucide-react";

export default function KpiCard({ label, value, delta, trend = "up", accent = false, icon: Icon = Gauge, testId }) {
  const positive = trend === "up";
  return (
    <div
      className={`bg-white rounded-xl border ${accent ? "border-gold/30" : "border-[#E5E7EB]"} card-soft p-5 transition hover:shadow-card`}
      data-testid={testId || `kpi-${(label || "").toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="text-[11px] uppercase tracking-[0.18em] text-ink-muted font-semibold">{label}</div>
        <Icon size={18} className="text-ink-muted/70" strokeWidth={1.5} />
      </div>
      <div className="mt-3 font-display font-extrabold text-ink tracking-tight text-3xl">{value}</div>
      <div className="mt-3 flex items-center gap-2 text-xs">
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-semibold ${
            positive ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"
          }`}
        >
          {positive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {delta}
        </span>
      </div>
    </div>
  );
}
