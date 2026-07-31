import React from "react";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "./OwnerPages";
import { Card } from "@/components/ui/card";
import { Sparkles } from "lucide-react";

export function ComingSoonPage({ title, features }) {
  return (
    <div>
      <PageHeader title={title} subtitle="Iteration 2 — coming after Primary Sales sign-off" />
      <Card className="p-8 text-center">
        <div className="h-14 w-14 mx-auto rounded-full bg-teal-50 text-teal-700 flex items-center justify-center mb-3">
          <Sparkles size={22} />
        </div>
        <div className="font-semibold text-slate-900 text-lg">{title}</div>
        <div className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
          The Primary Sales flow (Owner ↔ Distributor) is now live. Once you sign off on it, we&apos;ll build the following for this role in the next iteration.
        </div>
        <ul className="mt-4 text-sm text-slate-600 max-w-md mx-auto text-left space-y-1.5">
          {features.map(f => (
            <li key={f} className="flex items-start gap-2"><span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-teal-500" /> <span>{f}</span></li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

export function RetailerDashboardPage() {
  return <ComingSoonPage title="Retailer Dashboard" features={[
    "Browse products your distributor allows you to order",
    "Place orders (box only, or box + PCS)",
    "See order dispatch status and download bills",
    "View pending vs new order quantities",
  ]} />;
}

export function SalespersonDashboardPage() {
  return <ComingSoonPage title="Salesperson Dashboard" features={[
    "Daily punch in / punch out with GPS",
    "Assigned distributors and their stock",
    "Assigned retailers with locations",
    "Create retailer orders on the go",
    "Onboard new retailers with photo & location",
  ]} />;
}

export function TeamLeaderDashboardPage() {
  return <ComingSoonPage title="Team Leader Dashboard" features={[
    "Assigned distributors overview",
    "Assign distributors to salespersons",
    "Monitor daily sales & salesperson activity",
    "Track distributor performance",
  ]} />;
}

export function RegionalManagerDashboardPage() {
  return <ComingSoonPage title="Regional Manager Dashboard" features={[
    "Monitor Team Leader performance",
    "Region-level daily sales roll-up",
    "Salesperson activity across the region",
    "Distributor scorecards",
  ]} />;
}

export function DistAcctDashboardPage() {
  return <ComingSoonPage title="Distributor Accountant" features={[
    "Retailer ledger + outstanding (secondary sales)",
    "Mark payments as received",
    "Attach invoice copies to dispatches",
  ]} />;
}
